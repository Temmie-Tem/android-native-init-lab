"""One native session owner, with explicit bootstrap, N/E/N and A recovery.

The target adapter owns fixed I/O and raw proof. This owner owns order, original
budgets, durable intent, global exclusion and no replay. It imports no legacy
live owner. V3 remains dormant until its policy and implementation are adopted.
"""
from dataclasses import dataclass
from pathlib import Path
import re

import consumed_candidate_registry_v1 as registry
from device_action_raw_capture_v1 import RawCaptureError
from s22plus_native_records_v3 import (SCHEMA, Journal, SessionError, canonical,
    clock, digest, host_boot, pin, private_path, publish, read, require, verify)

OPERATIONS = ('bootstrap','experiment','android-exit','storage-census','gpt-reserve','native-ext4')


class ResultPublicationError(SessionError):
    def __init__(self, step):
        super().__init__('raw-proved step needs H0 result publication')
        self.step=step


@dataclass(frozen=True)
class Step:
    name: str
    action: str
    role: str
    ending: str | None = None
    hud: bool = False


def steps(operation, *, reentry=False, hud=False, native_bootstrap=False):
    require(operation in OPERATIONS and type(reentry) is bool and type(hud) is bool
        and type(native_bootstrap) is bool,
        'native operation selection differs')
    require(operation=='experiment' or not (reentry or hud),'optional observations belong to E')
    require(operation=='bootstrap' or not native_bootstrap,'native bootstrap origin belongs to bootstrap')
    if operation=='native-ext4':
        from s22plus_native_ext4_session_v1 import normal_steps
        return normal_steps()
    if operation=='gpt-reserve':
        from s22plus_native_gpt_session_v1 import normal_steps
        return normal_steps()
    if operation=='storage-census':
        return (Step('native-storage','observe','N','detach'),)
    if operation=='bootstrap':
        return (
            Step('native-bootstrap-start','observe','S','download') if native_bootstrap
                else Step('android-download','download','A'),
            Step('install-native-first','transfer','N'),
            Step('native-first-1','observe','N','detach'),
            Step('native-first-2','observe','N','download'),
            Step('install-native-second','transfer','N'),
            Step('native-second-1','observe','N','detach'),
            Step('native-second-2','observe','N','detach'))
    start=(Step('native-start','observe','N','download'),)
    if operation=='android-exit':
        return start+(Step('install-android','transfer','A'),Step('android-final','health','A'))
    experiment=(Step('experiment-first','observe','E','detach'),) if reentry else ()
    return start+(Step('install-experiment','transfer','E'),)+experiment+(
        Step('experiment-final','observe','E','download',hud),
        Step('restore-native','transfer','N'),Step('native-final','observe','N','detach'))


def operation_steps(request):
    return steps(request['operation'],reentry=request['reentry'],hud=request['hud'],
        native_bootstrap=request.get('S') is not None)


def live_grant(grant, *, recovery=False):
    require(grant['schema']==SCHEMA and grant['host_boot']==host_boot(),'native grant host epoch differs')
    require(type(grant['opened_ns']) is int and type(grant['deadline_ns']) is int
        and grant['opened_ns']<grant['deadline_ns'],'native grant clock range differs')
    if not recovery:
        require(grant['opened_ns']<=clock()<grant['deadline_ns'],'original native task grant expired')


class Session:
    """A fresh operation cannot execute again; only H0 close or original A resumes."""
    def __init__(self, root, directory, adapter):
        self.root=Path(root).resolve(strict=True)
        self.directory=private_path(self.root,directory)
        self.request=read(self.directory/'operation.json')
        self.binding=pin(self.directory/'operation.json')['sha256']
        self.grant_path=verify(self.request['grant'])
        self.grant=read(self.grant_path)
        self.journal=Journal(self.directory/'journal')
        self.adapter=adapter

    def check(self, *, recovery=False):
        require(pin(self.directory/'operation.json')['sha256']==self.binding,'operation identity changed')
        verify(self.request['grant']); live_grant(self.grant,recovery=recovery)
        require(not (self.grant_path.parent/'closed.json').exists() or recovery,'native task grant is closed')
        self.adapter.check(self.request,recovery=recovery)

    def rows(self):
        return self.journal.rows()

    def has_effect(self):
        return any(row['event']=='effect-intent' for row in self.rows())

    def has_recovery_basis(self):
        return self.has_effect() or self.adapter.native_attempt_started(self.request)

    def consumed(self):
        path=self.directory/'consumed.json'
        if not path.exists(): return None
        value=read(path)
        require(value==dict(schema=SCHEMA,operation_sha256=self.binding,grant=self.request['grant']),
            'native operation consumption differs')
        return value

    def unused(self):
        path=self.directory/'unused.json'
        if not path.exists(): return False
        rows=self.rows(); value=read(path)
        require(not self.has_effect() and value==dict(schema=SCHEMA,operation_sha256=self.binding,
            journal_rows=len(rows),journal_tail=pin(self.journal.directory/f'{len(rows)-1:04d}.json') if rows else None),
            'unused native operation no longer matches its closed journal')
        return True

    def close_unused(self):
        require(not self.has_recovery_basis(),'an effect or uncertain native attempt requires terminal closure')
        rows=self.rows()
        if not self.unused():
            publish(self.directory/'unused.json',dict(schema=SCHEMA,operation_sha256=self.binding,
                journal_rows=len(rows),journal_tail=pin(self.journal.directory/f'{len(rows)-1:04d}.json') if rows else None))
        sentinel=self.root/registry.F1_OWNER
        if sentinel.exists():
            registry.require_f1_owner(self.root,self.directory,self.binding)
            registry.retire_f1_owner(self.root,self.directory,self.binding)
        return dict(state='STOPPED_BEFORE_EFFECT',operation_consumed=False,
            native_health='UNPROVED' if self.request['operation']!='bootstrap' else 'NOT_MEASURED')

    def consume(self):
        if self.consumed() is not None:
            registry.require_f1_owner(self.root,self.directory,self.binding)
            return
        self.check()
        # Callers hold the same global target lease as every other F1 owner.
        # A successful preflight alone has not occupied operation capacity.
        siblings=list(self.grant_path.parent.glob('operation-*/consumed.json'))
        charged=0
        for path in siblings:
            other=Session(self.root,path.parent,self.adapter)
            require(other.request['grant']==self.request['grant'],'sibling operation uses a different grant')
            other.consumed()
            if not other.unused(): charged+=1
        require(charged<self.grant['operation_budget'],'native task operation budget exhausted')
        if (self.root/registry.F1_OWNER).exists():
            registry.require_f1_owner(self.root,self.directory,self.binding)
        else:
            registry.begin_f1_owner(self.root,self.directory,self.binding)
        publish(self.directory/'consumed.json',dict(schema=SCHEMA,operation_sha256=self.binding,grant=self.request['grant']))

    def intent(self, step, *, recovery=False, detail=None):
        self.check(recovery=recovery)
        require(not self.unused(),'unused operation is closed')
        rows=self.rows()
        require(not any(row['event']=='effect-intent' and row['data']['step']==step.name for row in rows),
            'native effect already has an intent; replay forbidden')
        if recovery:
            registry.require_f1_owner(self.root,self.directory,self.binding)
            require(self.has_recovery_basis(),'no original effect or native attempt exists to recover')
        else:
            require(not any(row['event']=='stopped' for row in rows),'research effects are closed')
            self.consume()
        if step.action=='transfer':
            self.adapter.claim(step,self.request,self.binding)
        if step.name in ('gpt-apply','gpt-restore'):
            from s22plus_native_gpt_session_v1 import claim_effect
            claim_effect(self.adapter,step,self.request)
        if self.request['operation']=='native-ext4' and step.name=='experiment-first':
            from s22plus_native_ext4_session_v1 import claim_effect
            claim_effect(self.adapter,step,self.request)
        return self.journal.append('effect-intent',step=step.name,action=step.action,
            role=step.role,ending=step.ending,recovery=recovery,detail=detail or {})

    def result(self, step, value):
        self.adapter.validate_result(step,value,self.request)
        try:
            path=self.directory/(step.name+'.json')
            if path.exists():
                require(read(path)==value,'existing step result differs from raw proof'); receipt=pin(path)
            else:
                receipt=publish(path,value)
            matches=[row for row in self.rows() if row['event']=='step-complete' and row['data']['step']==step.name]
            require(len(matches)<=1,'duplicate native step completion')
            if matches:
                require(matches[0]['data']['result']==receipt,'native completion receipt differs')
            else:
                self.journal.append('step-complete',step=step.name,result=receipt)
        except Exception as error:
            raise ResultPublicationError(step) from error
        return value

    def perform(self, step, *, recovery=False):
        self.check(recovery=recovery)
        require(not (self.directory/(step.name+'.json')).exists(),'native step result already exists')
        self.journal.append('step-start',step=step.name,action=step.action,role=step.role)
        guard=lambda:self.check(recovery=recovery)
        dispatch=lambda detail=None:self.intent(step,recovery=recovery,detail=detail)
        if step.action=='download':
            value=self.adapter.android_download(step,self.request,guard=guard,before_dispatch=dispatch)
        elif step.action=='reboot':
            value=self.adapter.android_reboot(step,self.request,guard=guard,before_dispatch=dispatch)
        elif step.action=='transfer':
            value=self.adapter.transfer(step,self.request,guard=guard,before_launch=dispatch)
        elif step.action=='observe':
            # OPEN and health retain their own attempt evidence. Operation
            # capacity normally starts at CONTROL; the fixed read-only census
            # uses one operation when its unique native attempt starts.
            options=dict(consume_observation=self.consume) if step.name=='native-storage' else {}
            if step.name in ('gpt-apply','gpt-restore'):options['before_extra']=dispatch
            if self.request['operation']=='native-ext4' and step.name=='experiment-first':
                options['before_extra']=dispatch
            value=self.adapter.observe(step,self.request,guard=guard,
                before_terminal=dispatch if step.ending=='download' else guard,**options)
        elif step.action=='health':
            value=self.adapter.android_health(step,self.request,guard=guard)
        else:
            raise SessionError('unknown native step')
        return self.result(step,value)

    def completed(self, selected_steps):
        rows=self.rows(); values=[]
        for step in selected_steps:
            matches=[row for row in rows if row['event']=='step-complete' and row['data']['step']==step.name]
            require(len(matches)==1,'native operation has no unique completed step')
            receipt=matches[0]['data']['result']; verify(receipt)
            require(Path(receipt['path'])==self.directory/(step.name+'.json'),'native step receipt belongs elsewhere')
            value=read(Path(receipt['path']))
            self.adapter.validate_result(step,value,self.request)
            values.append(value)
        self.adapter.validate_sequence(selected_steps,values,self.request)
        return values

    def close(self, selected_steps, *, recovered=False):
        values=self.completed(selected_steps)
        if self.request['operation']=='storage-census' and not recovered:
            require(self.consumed() is not None,'storage census has no original operation consumption')
        effects=[row['data'] for row in self.rows() if row['event']=='effect-intent']
        if recovered:
            covered=effects and effects[-1]['role']=='A' and effects[-1]['action']=='transfer' \
                and effects[-1]['step']==selected_steps[0].name
            if not covered and self.request['operation']=='gpt-reserve':
                from s22plus_native_gpt_session_v1 import recovery_terminal_covers_effects
                recovery_terminal_covers_effects(self.adapter,self.request,selected_steps,effects)
            else:require(covered,'recovery terminal does not cover the latest effect')
        else:
            expected=[step.name for step in selected_steps if step.action in ('download','transfer','physical','reboot')
                or step.action=='observe' and step.ending=='download' or step.name in ('gpt-apply','gpt-restore')
                or self.request['operation']=='native-ext4' and step.name=='experiment-first']
            require([effect['step'] for effect in effects]==expected,
                'normal terminal omits or differs from a durable effect')
        terminal_path=self.directory/'terminal.json'
        terminal=self.adapter.terminal(selected_steps,values,self.request,recovered=recovered)
        terminal.update(schema=SCHEMA,operation_sha256=self.binding,grant=self.request['grant'],
            recovered=recovered,research_closed=True)
        if terminal_path.exists():
            require(read(terminal_path)==terminal,'native terminal differs from retained evidence')
        else:
            publish(terminal_path,terminal)
        # Admission publication and release are idempotent H0; never I/O replay.
        if self.request['operation']=='bootstrap' and not recovered:
            self.adapter.admit(self.request,pin(terminal_path))
        registry.retire_f1_owner(self.root,self.directory,self.binding)
        return terminal

    def execute(self, *, attended):
        if self.request['operation']=='gpt-reserve':
            from s22plus_native_gpt_session_v1 import Coordinator
            return Coordinator(self).execute(attended=attended)
        with registry.target_session_lease(self.root):
            require(not self.rows() and not self.unused(),'native operation already started; use H0 close or recovery')
            self.check()
            require(attended or self.request['operation']!='bootstrap' and self.grant['recovery_mode']=='deferred',
                'this native operation requires actual attendance')
            registry.require_no_f1_owner(self.root)
            plan=operation_steps(self.request)
            try:
                # Original raw preflight remains separate and is used only as
                # initial health. Failures here create no F1 owner/consumption.
                self.adapter.preflight(self.request,guard=lambda:self.check())
                self.journal.append('preflight-complete')
                for step in plan: self.perform(step)
            except Exception as error:
                if isinstance(error,ResultPublicationError) and error.step==plan[-1]:
                    # The final fixed health/close is already validated. Disk
                    # publication failure cannot turn it into an A transfer.
                    raise
                if getattr(error,'protocol_completed',False) and step==plan[-1]:
                    raise
                self.journal.append('stopped',error_type=type(error).__name__,effect_intended=self.has_effect())
                if not self.has_recovery_basis():
                    # Owner creation and the consumption file precede dispatch.
                    # Under the global lease, an absent intent proves this cut
                    # never reached an effect; release only our own sentinel.
                    return dict(self.close_unused(),failure_type=type(error).__name__)
                if self.grant['recovery_mode']=='deferred' or not attended:
                    return dict(state='AWAITING_ATTENDED_RECOVERY',recovery_required=True,device_activity='UNKNOWN')
                return self._recover(attended=attended)
            # Close failures are reporting/admission work, outside the recovery
            # catch: final raw-proved health must not dispatch another image.
            return self.close(plan)

    def _recover(self, *, attended):
        if self.request['operation']=='gpt-reserve':
            from s22plus_native_gpt_session_v1 import Coordinator
            return Coordinator(self).recover(attended=attended)
        return self._recover_android(attended=attended)

    def _recover_android(self, *, attended):
        require(attended is True,'original A recovery requires actual attendance')
        require(not (self.directory/'terminal.json').exists(),'terminal already published; only H0 close repair remains')
        normal=operation_steps(self.request)
        android=[row for row in self.rows() if row['event']=='effect-intent'
            and row['data']['action']=='transfer' and row['data']['role']=='A']
        require(len(android)<=1,'multiple Android transfer intents')
        later_android=bool(android and not any(step.name==android[0]['data']['step']
            and step.action=='transfer' and step.role=='A' for step in normal))
        final_recorded=(self.directory/(normal[-1].name+'.json')).exists() or any(
            row['event']=='step-complete' and row['data']['step']==normal[-1].name for row in self.rows())
        final_recorded=final_recorded or self.adapter.final_protocol_completed(normal[-1],self.request)
        try:
            # Raw proofs may survive even when their result or terminal file
            # does not. Only a complete normal sequence selects this branch.
            require(not later_android,'a later Android intent takes precedence over native proof')
            values=[self.adapter.recover_step_result(step,self.request) for step in normal]
            for step,value in zip(normal,values): self.adapter.validate_result(step,value,self.request)
            self.adapter.validate_sequence(normal,values,self.request)
        except (ValueError,OSError,KeyError,RawCaptureError):
            if final_recorded and not later_android:
                raise SessionError('recorded final proof needs H0 repair; read failure does not authorize A')
        else:
            for step,value in zip(normal,values): self.result(step,value)
            return self.close(normal)
        self.check(recovery=True)
        registry.require_f1_owner(self.root,self.directory,self.binding)
        require(self.has_recovery_basis(),'there is no original effect or native attempt to recover')
        # A may already have been dispatched by a deliberate Android exit.
        name=android[0]['data']['step'] if android else 'recover-android'
        transfer=Step(name,'transfer','A')
        final=Step('recovery-health','health','A')
        if android:
            # A completed transfer can be reconstructed from raw evidence when
            # its result publication failed. An uncertain dispatch never retries.
            self.result(transfer,self.adapter.recover_transfer_result(transfer,self.request))
        else:
            self.perform(transfer,recovery=True)
        if not (self.directory/(final.name+'.json')).exists():
            self.perform(final,recovery=True)
        return self.close((transfer,final),recovered=True)

    def recover(self, *, attended):
        with registry.target_session_lease(self.root):
            return self._recover(attended=attended)

    def repair_close(self):
        """Reopen exact raw proofs only; this method performs no device action."""
        with registry.target_session_lease(self.root):
            if self.request['operation']=='gpt-reserve':
                from s22plus_native_gpt_session_v1 import Coordinator
                return Coordinator(self).repair()
            if not self.has_recovery_basis(): return self.close_unused()
            plan=operation_steps(self.request)
            recovered=False
            android=[row for row in self.rows() if row['event']=='effect-intent'
                and row['data']['action']=='transfer' and row['data']['role']=='A']
            require(len(android)<=1,'multiple Android transfer intents')
            try:
                require(not android or any(s.action=='transfer' and s.role=='A' and
                    s.name==android[0]['data']['step'] for s in plan),
                    'a later A intent selects recovery closure')
                values=[self.adapter.recover_step_result(step,self.request) for step in plan]
                for step,value in zip(plan,values): self.adapter.validate_result(step,value,self.request)
                self.adapter.validate_sequence(plan,values,self.request)
            except (ValueError,OSError,KeyError,RawCaptureError):
                require(len(android)==1,'no completed normal sequence or unique A recovery')
                plan=(Step(android[0]['data']['step'],'transfer','A'),Step('recovery-health','health','A'))
                values=[self.adapter.recover_step_result(step,self.request) for step in plan]
                for step,value in zip(plan,values): self.adapter.validate_result(step,value,self.request)
                self.adapter.validate_sequence(plan,values,self.request)
                recovered=True
            for step,value in zip(plan,values): self.result(step,value)
            return self.close(plan,recovered=recovered)

    def resume(self, *, attended, operator_statement=None):
        require(self.request['operation']=='gpt-reserve','only the phased GPT operation has an attended continuation')
        from s22plus_native_gpt_session_v1 import Coordinator
        return Coordinator(self).resume(attended=attended,operator_statement=operator_statement)


def prepare_operation(root, grant_path, *, operation, adapter, reentry=False, hud=False):
    """Select a new private operation without reserving effect capacity."""
    steps(operation,reentry=reentry,hud=hud)
    grant_path=private_path(root,grant_path); grant=read(grant_path); live_grant(grant)
    with registry.target_session_lease(Path(root)):
        registry.require_no_f1_owner(Path(root))
        require(not (grant_path.parent/'closed.json').exists(),'native task grant is closed')
        existing=list(grant_path.parent.glob('operation-*'))
        require(len(existing)<10000,'native task selection count exceeds bound')
        directory=grant_path.parent/f'operation-{len(existing)+1:04d}'
        directory.mkdir(mode=0o700)
        value=adapter.prepare(operation,grant,reentry=reentry,hud=hud)
        value.update(schema=SCHEMA,operation=operation,reentry=reentry,hud=hud,grant=pin(grant_path))
        publish(directory/'operation.json',value)
        return directory
