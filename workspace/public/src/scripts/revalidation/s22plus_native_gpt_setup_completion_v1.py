"""Finish the original G2 Android checks after its proved setup-only read failure.

No original source, approval or journal row is replaced. This separate fixed
entry requires its own exact incident/source review and the original live grant.
It can read Android health and issue only the original first ordinary reboot.
"""
import argparse
from pathlib import Path

import device_action_raw_capture_v1 as raw
import s22plus_native_gpt_session_v1 as gpt
import s22plus_native_session_v3 as owner
import s22plus_native_target_io_v3 as target
import s22plus_native_task_v3 as task_owner
from s22plus_native_adapter_v3 import Adapter
from s22plus_native_records_v3 import canonical, digest, pin, publish, read, require, verify

SCHEMA='s22plus-native-gpt-setup-completion-v1'
POLICY='docs/operations/S22PLUS_NATIVE_GPT_SETUP_COMPLETION_V1.md'
PLAN=gpt.normal_steps()
PREFIX=PLAN[:7]
SU_MISSING=b'/system/bin/sh: su: inaccessible or not found\n'


def missing_su(receipt):
    handle=raw.load_handle(verify(receipt))
    require(handle.returncode==127 and not handle.timed_out and not handle.output_exceeded
        and handle.producer_error_type is None
        and raw.read_stdout(handle,maximum=16384)==b''
        and raw.read_stderr(handle,maximum=16384)==SU_MISSING,
        'incident is not the completed missing-su read')


def derive_incident(session,failed_root,post_setup_health):
    require(session.request['operation']=='gpt-reserve','completion is outside G2')
    rows=session.rows();require(len(rows)>=20,'original setup stop is incomplete')
    require(rows[18]['event']=='step-start' and rows[18]['data']==dict(
        step='android-initial',action='health',role='A')
        and rows[19]['event']=='stopped' and rows[19]['data']==dict(
            effect_intended=True,error_type='RawCaptureError'),
        'original setup stop differs')
    require(not any(row['event']=='stopped' for row in rows[:19]),'an earlier stop is unresolved')
    failed=verify(failed_root)
    expected=session.adapter.folder('android-initial')
    require(failed.name=='03-health.capture.json' and failed.parent.name=='before'
        and failed.parent.parent.name.startswith('attempt-') and failed.parent.parent.parent==expected,
        'failed root capture belongs elsewhere')
    missing_su(failed_root)
    task=session.adapter.configuration(session.request)
    earlier=[raw.load_handle(failed.parent/f'{i:02d}-health.capture.json') for i in range(3)]
    texts=[raw.decode_success_stdout(handle,maximum=16384) for handle in earlier]
    require(all(not raw.read_stderr(handle,maximum=16384) for handle in earlier),
        'pre-root identity reads have diagnostics')
    target.select_android(texts[0],task['target'])
    require(texts[1]==task['target']['topology'],'failed read physical target differs')
    properties=target.fields(texts[2],target.PROPERTY_FIELDS)
    require(properties['model']=='SM-S906N' and properties['device']=='g0q'
        and properties['bootloader']==properties['incremental']=='S906NKSS7FYG8'
        and properties['boot_completed']=='1','failed read is not booted FYG8 Android')
    completed=[]
    for step in PREFIX:
        receipt=pin(session.directory/(step.name+'.json'))
        session.adapter.validate_result(step,read(verify(receipt)),session.request)
        completed.append(receipt)
    require(gpt.android_basis(session.adapter,session.request)['layout']=='proposed',
        'initialized proposed GPT is not proved')
    health=read(verify(post_setup_health))
    require(verify(post_setup_health).is_relative_to(session.directory)
        and target.health_projection(health['captures'],task['target'],session.request['A'])==health,
        'post-setup numeric root and original A are not proved')
    return dict(schema=SCHEMA,operation=pin(session.directory/'operation.json'),
        task=session.request['task'],grant=session.request['grant'],original_review=task['review'],
        journal_prefix=[pin(session.journal.directory/f'{i:04d}.json') for i in range(20)],
        completed_prefix=completed,failed_root=failed_root,post_setup_health=post_setup_health,
        setup_boot_changed=health['boot_id_sha256']!=digest(properties['boot_id'].encode()))


def prepare(root,directory,output,*,failed_root,post_setup_health):
    session=owner.Session(root,directory,Adapter(root,directory))
    require(len(session.rows())==20 and not gpt.intents(session.adapter,'android-reboot')
        and not (session.directory/'terminal.json').exists(),'incident already has later work')
    return publish(output,derive_incident(session,failed_root,post_setup_health))


def verify_binding(session,incident,review,*,full=True):
    value=read(verify(incident));qualified=read(verify(review))
    require(set(qualified)=={'schema','verdict','scope','incident','sources','reviewer','findings'}
        and qualified['schema']==SCHEMA and qualified['verdict']=='PASS_GO'
        and qualified['scope']=='EXACT_SETUP_READ_COMPLETION' and qualified['incident']==incident
        and qualified['findings']==[],'exact setup-completion review is absent')
    sources=[pin(Path(__file__).resolve()),pin(session.root/POLICY)]
    require(qualified['sources']==sources,'setup-completion source changed')
    require(task_owner.capability(session.root)==value['original_review'],
        'original reviewed host machinery changed')
    for receipt in (*value['journal_prefix'],*value['completed_prefix']):verify(receipt)
    if full:
        require(value==derive_incident(session,value['failed_root'],value['post_setup_health']),
            'original setup incident evidence changed')
    return value


class Completion:
    def __init__(self,session,incident,review):
        self.session=session;self.adapter=session.adapter
        self.incident=incident;self.review=review
        self.folder=session.directory/'setup-completion'

    def check(self,*,live=True,full=False):
        session=self.session;verify_binding(session,self.incident,self.review,full=full)
        rows=session.rows();extra=rows[20:]
        require(not any(row['event'] in ('stopped','gpt-recovery-selected','setup-completion-stopped')
            for row in extra),'completion has a later unresolved stop/recovery')
        allowed={step.name for step in PLAN[7:]}
        require(all(row['event'] in ('setup-completion-admitted','step-start','step-complete','effect-intent')
            and (row['event']=='setup-completion-admitted' or row['data'].get('step') in allowed)
            for row in extra),'completion journal contains another action')
        if extra:
            admissions=[row for row in extra if row['event']=='setup-completion-admitted']
            path=self.folder/'admission.json'
            require(len(admissions)==1 and extra[0]==admissions[0]
                and admissions[0]['data']==dict(admission=pin(path)),
                'completion admission provenance is missing or changed')
            admission=read(path)
            require(set(admission)=={'incident','review','operator_statement'}
                and admission['incident']==self.incident and admission['review']==self.review
                and type(admission['operator_statement']) is str
                and 0<len(admission['operator_statement'].strip())<=4096,
                'completion admission does not match the exact reviewed incident')
        effects=[row['data'] for row in extra if row['event']=='effect-intent']
        require(len(effects)<=1 and all(row['step']=='android-reboot' and row['action']=='reboot'
            and row['role']=='A' and row['ending'] is None and row['recovery'] is False for row in effects),
            'completion contains another effect or a replay')
        require(session.consumed() is not None,'original operation capacity is absent')
        if live:
            session.check()  # Original deadline, host boot, target, A and 54/155 source checks.
            owner.registry.require_f1_owner(session.root,session.directory,session.binding)
            require(not (session.directory/'terminal.json').exists(),'terminal requires H0 repair only')

    def admit(self,statement):
        self.check(full=True);require(type(statement) is str and 0<len(statement.strip())<=4096,
            'actual operator setup/root-request statement is required')
        self.folder.mkdir(mode=0o700,exist_ok=True)
        value=dict(incident=self.incident,review=self.review,operator_statement=statement)
        path=self.folder/'admission.json'
        if path.exists():require(read(path)==value,'completion admission changed')
        else:publish(path,value)
        matches=[row for row in self.session.rows() if row['event']=='setup-completion-admitted']
        require(len(matches)<=1,'completion was admitted twice')
        if matches:require(matches[0]['data']==dict(admission=pin(path)),'completion journal admission changed')
        else:self.session.journal.append('setup-completion-admitted',admission=pin(path))

    def started(self,step):
        rows=[row for row in self.session.rows() if row['event']=='step-start' and row['data']['step']==step.name]
        require(len(rows)<=1,'completion step has duplicate starts')
        if not rows:self.session.journal.append('step-start',step=step.name,action=step.action,role=step.role)

    def reboot_intent(self,detail=None):
        self.check(full=True);session=self.session
        require(not gpt.intents(self.adapter,'android-reboot'),'ordinary reboot already intended; replay forbidden')
        initial=PLAN[7]
        self.adapter.validate_result(initial,read(session.directory/(initial.name+'.json')),session.request)
        admission=read(self.folder/'admission.json')
        require(admission['incident']==self.incident and admission['review']==self.review,
            'reboot lacks its exact continuation admission')
        # Named, independently reviewed specialization of the unconditional
        # stopped gate: this exact remaining effect has never been intended.
        self.check()
        row=session.journal.append('effect-intent',step='android-reboot',action='reboot',role='A',
            ending=None,recovery=False,detail=detail or {})
        self.check()
        return row

    def execute(self,*,attended,operator_statement):
        session=self.session
        with owner.registry.target_session_lease(session.root):
            require(attended is True,'setup completion is attended')
            self.admit(operator_statement)
            try:
                for step in PLAN[7:]:
                    self.check();self.started(step)
                    if (session.directory/(step.name+'.json')).exists():
                        value=self.adapter.recover_step_result(step,session.request)
                    elif step.action=='health':
                        value=self.adapter.android_health(step,session.request,guard=self.check)
                    elif gpt.intents(self.adapter,'android-reboot'):
                        value=self.adapter.recover_step_result(step,session.request)
                    else:
                        value=self.adapter.android_reboot(step,session.request,guard=self.check,
                            before_dispatch=self.reboot_intent)
                    session.result(step,value)
            except Exception as error:
                if isinstance(error,owner.ResultPublicationError) or getattr(error,'protocol_completed',False):raise
                session.journal.append('setup-completion-stopped',error_type=type(error).__name__)
                raise
            self.check(live=False,full=True)
            return session.close(PLAN)

    def repair(self):
        """Only retained raw results and terminal publication; no device reads."""
        with owner.registry.target_session_lease(self.session.root):
            self.check(live=False,full=True)
            for step in PLAN[7:]:
                try:value=self.adapter.recover_step_result(step,self.session.request)
                except (ValueError,OSError,KeyError):
                    return dict(state='H0_REPAIRED_PREFIX',next_step=step.name,owner_retained=True)
                self.session.result(step,value)
            return self.session.close(PLAN)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('execute','repair'));parser.add_argument('incident',type=Path)
    parser.add_argument('review',type=Path);parser.add_argument('--attended',action='store_true')
    parser.add_argument('--operator-statement');args=parser.parse_args()
    root=Path(__file__).resolve().parents[5];incident=read(args.incident)
    directory=verify(incident['operation']).parent
    session=owner.Session(root,directory,Adapter(root,directory))
    completion=Completion(session,pin(args.incident),pin(args.review))
    value=completion.execute(attended=args.attended,operator_statement=args.operator_statement) \
        if args.command=='execute' else completion.repair()
    print(canonical(value).decode(),end='')


if __name__=='__main__':main()
