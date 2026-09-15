"""Phased GPT reservation within the existing V3 owner and its one journal.

Physical reboot/reset and fresh Android setup are explicit attended stages.
The global F1 owner remains held across every pending stage. No new research
effect resumes after a stop; recovery is exact N, original GPT, and exact A.
"""
from pathlib import Path

import s22plus_native_gpt_profile_v1 as gpt
import s22plus_native_session_v3 as owner
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import (SCHEMA, Journal, SessionError, canonical,
    clock, digest, pin, publish, read, require, verify)

OPERATION='gpt-reserve'
PHYSICAL={'gpt-restart':'restart-native','factory-reset':'stock-factory-reset',
    'recovery-factory-reset':'stock-factory-reset-original'}
MUTATING={'gpt-apply','gpt-restore'}


def normal_steps():
    return (owner.Step('gpt-apply','observe','N','detach'),
        owner.Step('gpt-restart','physical','N'),
        owner.Step('gpt-proposed','observe','N','detach'),
        owner.Step('factory-reset','physical','N'),
        owner.Step('gpt-after-reset','observe','N','detach'),
        owner.Step('gpt-android-start','observe','N','download'),
        owner.Step('install-android','transfer','A'),owner.Step('android-initial','health','A'),
        owner.Step('android-reboot','reboot','A'),owner.Step('android-final','health','A'))


def journal(adapter):
    return Journal(adapter.directory/'journal').rows()


def intents(adapter, name=None):
    return [row['data'] for row in journal(adapter) if row['event']=='effect-intent'
        and (name is None or row['data']['step']==name)]


def gpt_intended(adapter):
    return bool(intents(adapter,'gpt-apply'))


def reset_intended(adapter):
    return bool(intents(adapter,'factory-reset'))


def recovery_steps(adapter):
    choices=[row['data'] for row in journal(adapter) if row['event']=='gpt-recovery-selected']
    require(len(choices)==1,'GPT recovery has no unique selected path')
    choice=choices[0]
    if choice['basis']=='initialized-proposed':
        return (owner.Step(choice['android_step'],'transfer','A'),owner.Step('recovery-health','health','A'))
    require(choice['basis']=='restore-original','unknown GPT recovery path')
    prefix=(owner.Step('recover-native','transfer','N'),owner.Step('gpt-restore','observe','N','detach'))
    if reset_intended(adapter):
        prefix+=(owner.Step('recovery-factory-reset','physical','N'),
            owner.Step('gpt-after-original-reset','observe','N','detach'))
    return prefix+(owner.Step('gpt-recovery-download','observe','N','download'),
        owner.Step('recover-android','transfer','A'),owner.Step('recovery-health','health','A'))


def plan_for_step(adapter,step,request):
    normal=normal_steps()
    return normal if step in normal else recovery_steps(adapter)


def profile_for(step,image):
    if step.name in gpt.SELECTIONS:return step.name
    if step.name=='native-second-2' and image.get('profile')==gpt.PROFILE:return 'gpt-original'
    return 'storage-census' if step.name=='native-storage' else 'health'


def claim_path(adapter,request):
    task=adapter.configuration(request)
    key=digest(canonical(dict(target=task['target'],proposal_sha256=request['N']['gpt']['proposal']['sha256'])))
    return adapter.root/'workspace/private/runs/s22plus-native-gpt-v1/claims'/(key+'.json')


def claim_effect(adapter,step,request):
    require(request['operation']==OPERATION and step.name in MUTATING,'unselected GPT effect')
    path=claim_path(adapter,request)
    operation=pin(adapter.directory/'operation.json')
    if step.name=='gpt-apply':
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        publish(path,dict(schema='s22plus-native-gpt-claim-v1',operation=operation,
            proposal=request['N']['gpt']['proposal'],N=request['N']['ap'],boottime_ns=clock()))
    else:
        value=read(path)
        require(value['schema']=='s22plus-native-gpt-claim-v1' and value['operation']==operation
            and value['proposal']==request['N']['gpt']['proposal'] and value['N']==request['N']['ap']
            and gpt_intended(adapter),'GPT restore has no original one-shot apply claim')


def preflight(adapter,request):
    require(request['N']['profile']==gpt.PROFILE,'GPT operation has no qualified GPT image')
    require(not claim_path(adapter,request).exists(),'this target/proposal already has a GPT attempt; replay forbidden')
    admission=adapter.admission(request['admission'],request['N'],adapter.configuration(request))
    terminal=read(verify(admission['terminal']))
    operation=read(verify(terminal['operation_record']))
    other=type(adapter)(adapter.root,Path(terminal['operation_record']['path']).parent)
    step=owner.operation_steps(operation)[-1]
    result=other.recover_step_result(step,operation)
    other.validate_result(step,result,operation)
    require(result['proof']['gpt']['status']=='PASS_EXACT_GPT'
        and result['proof']['gpt']['selection']=='gpt-original',
        'new native endpoint lacks its actual complete read-only qualification')


def validate_command_intent(adapter,step,value,request):
    require(value['proof']['gpt']['status']=='PASS_EXACT_GPT','fixed GPT command has no exact successful proof')
    if step.name not in MUTATING:return
    rows=intents(adapter,step.name);require(len(rows)==1,'GPT command has no unique pre-EXEC intent')
    detail=rows[0]['detail'];proof=value['proof'];selected=gpt.Profile(request['N'],step.name)
    require(detail['mode']=='fixed-extra' and detail['sequence']==5
        and detail['body_sha256']==digest(selected.BODY)
        and detail['run_id_hex']==request['N']['run_id_hex']
        and detail['nonce_sha256']==proof['nonce_sha256']
        and detail['kernel_boot_identity_sha256']==proof['kernel_boot_identity_sha256'],
        'GPT raw session does not join its original pre-EXEC intent')
    claim=read(claim_path(adapter,request))
    require(claim['operation']==pin(adapter.directory/'operation.json')
        and claim['proposal']==request['N']['gpt']['proposal'],'GPT command belongs to another one-shot claim')


def physical_result(adapter,step,request):
    folder=adapter.folder(step.name)
    rows=intents(adapter,step.name);require(len(rows)==1,'physical action has no unique original intent')
    reconstructed=dict(action='physical',context=rows[0]['detail']['physical'],
        operator=pin(folder/'operator.json'),departure=pin(folder/'departure.json'))
    value=read(folder/'result.json') if (folder/'result.json').exists() else reconstructed
    require(value==reconstructed,'physical aggregate differs from retained component records')
    context=read(verify(rows[0]['detail']['physical']))
    require(context['step']==step.name and context['action']==PHYSICAL[step.name]
        and context['operation']==pin(adapter.directory/'operation.json')
        and value['action']=='physical' and value['context']==rows[0]['detail']['physical'],
        'physical action belongs to another operation')
    departure=read(verify(value['departure']))
    statement=read(verify(value['operator']))
    require(statement['context']==value['context'] and type(statement['statement']) is str
        and 0<len(statement['statement'].strip())<=4096
        and departure['before']==context['before'] and departure['departed'] is True
        and departure['deadline_ns']==context['deadline_ns']
        and context['started_ns']<=departure['observed_ns']<context['deadline_ns'],
        'physical action lacks bounded departure and operator completion')
    return value


def _proved(adapter,request,name):
    path=adapter.directory/(name+'.json')
    require(path.exists(),'required GPT phase is not complete: '+name)
    step=next(step for step in (*normal_steps(),*recovery_steps(adapter)) if step.name==name) \
        if any(row['event']=='gpt-recovery-selected' for row in journal(adapter)) \
        else next(step for step in normal_steps() if step.name==name)
    value=read(path);adapter.validate_result(step,value,request)
    return value


def android_basis(adapter,request):
    """Every A effect after GPT must pass this, including recovery branches."""
    if not gpt_intended(adapter):return dict(layout='original',initialization='unchanged')
    if intents(adapter,'recover-native') or intents(adapter,'gpt-restore'):
        restored=_proved(adapter,request,'gpt-restore')['proof']['gpt']
        require(restored['final_pair']=='original','restoration did not prove complete original GPT')
        if reset_intended(adapter):
            _proved(adapter,request,'recovery-factory-reset')
            geometry=_proved(adapter,request,'gpt-after-original-reset')['proof']['gpt']
            require(geometry['filesystem']['status']=='PASS_GEOMETRY_ONLY','original userdata reset is unproved')
            return dict(layout='original',initialization='restorative-reset',geometry=geometry['filesystem'])
        return dict(layout='original',initialization='unchanged',restoration=restored['full_metadata'])
    _proved(adapter,request,'factory-reset')
    geometry=_proved(adapter,request,'gpt-after-reset')['proof']['gpt']
    require(geometry['final_pair']=='proposed' and geometry['filesystem']['status']=='PASS_GEOMETRY_ONLY',
        'reduced userdata initialization is unproved')
    return dict(layout='proposed',initialization='stock-reset',geometry=geometry['filesystem'])


def recovery_terminal_covers_effects(adapter,request,selected,effects):
    """Fresh A health may close a stopped ordinary reboot without replaying it.

    This does not qualify reboot persistence when its raw request/departure
    proof is incomplete. No partition/control effect may follow that reboot.
    """
    require(request['operation']==OPERATION and len(selected)==2
        and selected[0].action=='transfer' and selected[0].role=='A'
        and selected[1].action=='health' and selected[1].role=='A',
        'GPT recovery terminal roles differ')
    android=[i for i,row in enumerate(effects) if row['action']=='transfer' and row['role']=='A']
    require(len(android)==1 and effects[android[0]]['step']==selected[0].name
        and len(effects)==android[0]+2
        and (effects[-1]['step'],effects[-1]['action'],effects[-1]['role'])==('android-reboot','reboot','A'),
        'fresh Android health does not cover the latest GPT operation effect')
    android_basis(adapter,request)


class Coordinator:
    def __init__(self,session):
        self.session=session;self.adapter=session.adapter
        require(session.request['operation']==OPERATION,'GPT coordinator operation differs')

    def recovering(self):
        return any(row['event']=='gpt-recovery-selected' for row in self.session.rows())

    def pending(self,step):
        return dict(state='AWAITING_OPERATOR_ACTION',action=PHYSICAL.get(step.name,'android-setup'),
            step=step.name,operation_directory=str(self.session.directory),owner_retained=True,
            partition_or_control_replay_permitted=False)

    def begin_physical(self,step,*,recovery):
        session=self.session;session.check(recovery=recovery)
        folder=self.adapter.folder(step.name,create=True)
        before=target.usb_snapshot(target.lane.CANDIDATE_TOPOLOGY,folder)
        started=clock();deadline=started+900_000_000_000 if recovery else session.grant['deadline_ns']
        require(started<deadline,'physical action has no remaining original grant time')
        context=publish(folder/'context.json',dict(schema='s22plus-native-gpt-physical-v1',
            operation=pin(session.directory/'operation.json'),step=step.name,action=PHYSICAL[step.name],
            before=before,started_ns=started,deadline_ns=deadline,recovery=recovery))
        session.intent(step,recovery=recovery,detail=dict(physical=context))

    def finish_physical(self,step,statement,*,recovery):
        session=self.session;folder=self.adapter.folder(step.name)
        rows=intents(self.adapter,step.name);require(len(rows)==1,'physical action was not prepared exactly once')
        context=read(verify(rows[0]['detail']['physical']))
        require(type(statement) is str and 0<len(statement.strip())<=4096,'actual operator completion is required')
        if (folder/'operator.json').exists():
            operator=pin(folder/'operator.json');old=read(verify(operator))
            require(old['context']==rows[0]['detail']['physical'] and old['statement']==statement,
                'physical completion statement changed')
        else:
            try:operator=publish(folder/'operator.json',dict(context=rows[0]['detail']['physical'],
                statement=statement,reported_ns=clock()))
            except OSError as error:raise owner.ResultPublicationError(step) from error
        if (folder/'departure.json').exists():departure_receipt=pin(folder/'departure.json')
        else:
            departure=target.wait_departure(context['before'],folder,deadline_ns=context['deadline_ns'],
                guard=lambda:session.check(recovery=recovery))
            try:departure_receipt=publish(folder/'departure.json',departure)
            except OSError as error:raise owner.ResultPublicationError(step) from error
        value=dict(action='physical',context=rows[0]['detail']['physical'],operator=operator,departure=departure_receipt)
        if not (folder/'result.json').exists():
            try:publish(folder/'result.json',value)
            except OSError as error:raise owner.ResultPublicationError(step) from error
        session.result(step,value)

    def walk(self,plan,*,recovery,statement=None):
        session=self.session
        for step in plan:
            session.check(recovery=recovery)
            path=session.directory/(step.name+'.json')
            if path.exists():
                self.adapter.validate_result(step,read(path),session.request);continue
            if step.action=='physical':
                if not intents(self.adapter,step.name):
                    self.begin_physical(step,recovery=recovery);return self.pending(step)
                if statement is None:return self.pending(step)
                self.finish_physical(step,statement,recovery=recovery);statement=None;continue
            if step.action=='health' and (reset_intended(self.adapter)
                    or intents(self.adapter,'recovery-factory-reset')):
                setup=session.directory/'android-setup.json'
                if not setup.exists():
                    if statement is None:return self.pending(step)
                    publish(setup,dict(operation=pin(session.directory/'operation.json'),
                        statement=statement,reported_ns=clock()));statement=None
                require(read(setup)['operation']==pin(session.directory/'operation.json'),
                    'Android setup belongs to another operation')
            started=any(row['event']=='step-start' and row['data']['step']==step.name for row in session.rows())
            if started and step.action!='health':
                # A reporting cut never replays an authenticated EXEC/transfer.
                session.result(step,self.adapter.recover_step_result(step,session.request))
            else:session.perform(step,recovery=recovery)
        return None

    def close(self,plan,*,recovery):
        self.session.completed(plan)
        return self.session.close(plan[-2:] if recovery else plan,recovered=recovery)

    def stopped(self,error,*,recovery,attended):
        if isinstance(error,owner.ResultPublicationError) or getattr(error,'protocol_completed',False):raise error
        session=self.session
        session.journal.append('stopped',error_type=type(error).__name__,effect_intended=session.has_effect())
        if not session.has_recovery_basis():return session.close_unused()
        if not gpt_intended(self.adapter):return session._recover_android(attended=attended)
        return dict(state='GPT_RECOVERY_STOPPED' if recovery else 'AWAITING_GPT_RECOVERY',
            recovery_required=True,owner_retained=True,device_activity='UNKNOWN',
            next_action='H0 diagnosis or exact preauthorized recovery; no effect replay')

    def execute(self,*,attended):
        session=self.session
        with owner.registry.target_session_lease(session.root):
            require(attended is True,'GPT reservation requires actual attendance')
            require(not session.rows() and not session.unused(),'GPT operation already started')
            session.check();owner.registry.require_no_f1_owner(session.root)
            try:
                self.adapter.preflight(session.request,guard=lambda:session.check())
                session.journal.append('preflight-complete')
                pending=self.walk(normal_steps(),recovery=False)
            except Exception as error:return self.stopped(error,recovery=False,attended=attended)
            return pending if pending is not None else self.close(normal_steps(),recovery=False)

    def resume(self,*,attended,operator_statement=None):
        session=self.session
        with owner.registry.target_session_lease(session.root):
            require(attended is True,'GPT continuation requires actual attendance')
            require(operator_statement is None or type(operator_statement) is str
                and 0<len(operator_statement.strip())<=4096,'operator completion statement differs')
            require(not (session.directory/'terminal.json').exists(),'GPT operation is already terminal')
            recovery=self.recovering();session.check(recovery=recovery)
            owner.registry.require_f1_owner(session.root,session.directory,session.binding)
            require(recovery or not any(row['event']=='stopped' for row in session.rows()),
                'normal GPT work is stopped; select original recovery')
            plan=recovery_steps(self.adapter) if recovery else normal_steps()
            try:pending=self.walk(plan,recovery=recovery,statement=operator_statement)
            except Exception as error:return self.stopped(error,recovery=recovery,attended=attended)
            return pending if pending is not None else self.close(plan,recovery=recovery)

    def recover(self,*,attended):
        session=self.session
        require(attended is True,'GPT recovery requires actual attendance')
        require(not (session.directory/'terminal.json').exists(),'terminal already exists; repair H0 only')
        if not gpt_intended(self.adapter):return session._recover_android(attended=attended)
        if not self.recovering():
            # A complete normal raw sequence always wins over recovery effects.
            try:
                values=[self.adapter.recover_step_result(step,session.request) for step in normal_steps()]
                for step,value in zip(normal_steps(),values):self.adapter.validate_result(step,value,session.request)
                self.adapter.validate_sequence(normal_steps(),values,session.request)
            except (ValueError,OSError,KeyError):
                require(not self.adapter.final_protocol_completed(normal_steps()[-1],session.request),
                    'recorded final proof requires H0 repair, not GPT restoration')
            else:
                for step,value in zip(normal_steps(),values):session.result(step,value)
                return self.close(normal_steps(),recovery=False)
            android=[row for row in intents(self.adapter) if row['action']=='transfer' and row['role']=='A']
            require(len(android)<=1,'multiple original A intents')
            try:basis=android_basis(self.adapter,session.request)
            except (ValueError,OSError,KeyError):basis=None
            if android:
                require(basis is not None,'A has an intent but its GPT safety proof is unavailable; H0 only')
                # This must rederive the original dispatch; an uncertain A is
                # never repeated or overwritten by a recovery-native install.
                step=owner.Step(android[0]['step'],'transfer','A')
                session.result(step,self.adapter.recover_transfer_result(step,session.request))
            session.journal.append('gpt-recovery-selected',
                basis='initialized-proposed' if basis and basis['layout']=='proposed' else 'restore-original',
                android_step=android[0]['step'] if android else 'recover-android')
        plan=recovery_steps(self.adapter)
        try:pending=self.walk(plan,recovery=True)
        except Exception as error:return self.stopped(error,recovery=True,attended=attended)
        return pending if pending is not None else self.close(plan,recovery=True)

    def repair(self):
        """Reconstruct retained results only; no wait, control or device read."""
        session=self.session
        if not session.has_recovery_basis():return session.close_unused()
        recovery=self.recovering();plan=recovery_steps(self.adapter) if recovery else normal_steps()
        for step in plan:
            try:
                value=self.adapter.recover_step_result(step,session.request)
                self.adapter.validate_result(step,value,session.request)
            except (ValueError,OSError,KeyError):
                return dict(state='H0_REPAIRED_PREFIX',next_step=step.name,owner_retained=True)
            session.result(step,value)
        return self.close(plan,recovery=recovery)
