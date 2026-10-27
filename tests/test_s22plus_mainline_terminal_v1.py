"""Fixed connector readiness and mainline dispatch; harmless subprocess fixtures."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

import test_s22plus_approved_terminal_persistent_v1 as prior
import s22plus_mainline_terminal_v1 as entry
import s22plus_mainline_task_v1 as mainline
import s22plus_approved_terminal_tasks_v1 as backend
import s22plus_approved_terminal_persistent_v1 as transport
import s22plus_native_records_v3 as records

save=prior.previous.save


def fixture(root,ordinal=1):
    base=root/f'workspace/private/outputs/s22plus-mainline-fixture-h0-20261028-{ordinal}'
    directory=base/'task-1';directory.mkdir(parents=True)
    task=save(directory/'task.json',dict(schema='s22plus-mainline-task-v1',
        N=dict(profile=mainline.profile.PROFILE,namespace=mainline.profile.NAMESPACE,version=mainline.profile.VERSION),
        operations=['mainline-ram'],seconds=1800,operation_budget=1,recovery_mode='attended',E=None,
        review={'fixture':'capability'},target={'fixture':'owned-S22'},A={'fixture':'original-A'}))
    proposal=save(directory/'proposal.json',dict(task=task,
        approval=mainline.tasks.approval_text(records.read(Path(task['path'])),task),grants_device_authority=False))
    previous_task=save(base/'predecessor/task.json',dict(target={'fixture':'owned-S22'},A={'fixture':'original-A'}))
    terminal=save(base/'predecessor/terminal.json',dict(terminal_state='ANDROID_CLOSED_HEALTHY',research_closed=True))
    closed=save(base/'predecessor/closed.json',dict(terminal_state='ANDROID_CLOSED_HEALTHY',task=previous_task,current_android_terminal=terminal))
    save(base/'connector-preparation.json',dict(schema='s22plus-mainline-connector-preparation-v1',
        status='PREPARED_H0_NOT_RUN_APPROVAL',task=task,proposal=proposal,review={'fixture':'capability'},preceding_closed=closed))
    records.Journal(directory/'journal')
    helper=root/entry.ENTRY;helper.parent.mkdir(parents=True,exist_ok=True)
    helper.write_text("from pathlib import Path\nimport sys,time\nassert sys.argv[1]=='start' and len(sys.argv)==3\np=Path(sys.argv[2]).parent\n(p/'fixture-start').write_text('once')\ntime.sleep(.2)\n")
    cli=root/'workspace/public/src/scripts/revalidation/s22plus_mainline_task_v1.py';cli.parent.mkdir(parents=True,exist_ok=True)
    cli.write_text("from pathlib import Path\nimport sys,time\nassert sys.argv[1]=='--root' and sys.argv[3]=='ready' and len(sys.argv)==5\np=Path(sys.argv[4]).parent\n(p/'fixture-ready').write_text('read only')\ntime.sleep(.35)\nprint('fixture D0 complete')\n")
    return base


class TerminalTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.base=fixture(self.root);self.directory=self.base/'task-1'
        self.controller=backend.Controller(self.root,bridge_check=lambda root:{'fixture':'bridge'})
        patch=mock.patch.object(mainline,'validate_task');patch.start();self.addCleanup(patch.stop)
        patch=mock.patch.object(backend.registry,'require_no_f1_owner');patch.start();self.addCleanup(patch.stop)
        self.addCleanup(self.settle)

    def settle(self):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            pending=[p for p in self.base.rglob('spawned.json') if not (p.parent/'result.json').exists()]
            if not pending:return
            time.sleep(.01)
        self.fail('fixture result owner did not settle')

    def approve(self):
        bound=self.controller.bundle(str(self.base))
        return save(self.base/'operator-approval.json',dict(task=bound['task'],entry=bound['entry'],
            preceding_closed=bound['preceding_closed'],selected_returned_approval=records.read(self.directory/'proposal.json')['approval'],
            actual_user_text='fixture explicit finite approval and attendance',attended=True))

    def ready_for_f1(self,base=None):
        directory=(base or self.base)/'task-1'
        result=save(directory/'fixture-ready.json',{'fixture':True})
        records.Journal(directory/'journal').append('readiness-complete',result=result)
        patch=mock.patch.object(mainline,'validate_readiness',return_value={'observed_ns':records.clock()})
        patch.start();self.addCleanup(patch.stop)

    def test_readiness_is_explicit_async_and_does_not_create_grant_or_approval(self):
        result=self.controller.check_readiness(str(self.base));self.assertTrue(result['dispatched'])
        repeated=self.controller.check_readiness(str(self.base));self.assertFalse(repeated['dispatched'])
        self.settle()
        self.assertEqual(len(list((self.base/backend.READINESS).glob('attempt-*'))),1)
        self.assertEqual(self.controller.status(str(self.base))['readiness']['returncode'],0)
        self.assertIn('fixture D0 complete',self.controller.log(str(self.base),stream='readiness')['text'])
        for name in ('grant.json','operator-approval.json','operation-0001'):
            self.assertFalse((self.directory/name).exists());self.assertFalse((self.base/name).exists())
        self.assertFalse((self.directory/'fixture-start').exists())
        with mock.patch.object(backend.subprocess,'Popen',side_effect=AssertionError('status dispatched')):
            self.controller.status(str(self.base));self.controller.log(str(self.base),stream='readiness')

    def test_f1_still_requires_actual_approval_and_exact_fixed_argv(self):
        with self.assertRaises(OSError):self.controller.start(str(self.base))
        self.assertFalse((self.base/backend.DISPATCH/'intent.json').exists())
        self.approve();self.ready_for_f1();result=self.controller.start(str(self.base));self.assertTrue(result['dispatched']);self.settle()
        self.assertFalse(self.controller.start(str(self.base))['dispatched'])
        intent=records.read(self.base/backend.DISPATCH/'intent.json')
        self.assertEqual(intent['command'],['/usr/bin/python3',str(self.root/entry.ENTRY),'start',str(self.directory/'task.json')])
        self.assertTrue((self.directory/'fixture-start').exists());self.assertFalse((self.directory/'fixture-ready').exists())

    def test_wrong_scope_or_unattended_record_cannot_spawn(self):
        self.approve();approval=self.base/'operator-approval.json';value=records.read(approval);value['attended']=False;save(approval,value)
        with self.assertRaises(ValueError):self.controller.start(str(self.base))
        task=records.read(self.directory/'task.json');task['operations']=['bootstrap'];save(self.directory/'task.json',task)
        with self.assertRaises(ValueError):self.controller.check_readiness(str(self.base))
        self.assertFalse((self.base/backend.DISPATCH/'intent.json').exists())

    def test_running_or_uncertain_readiness_blocks_f1_and_is_not_retried(self):
        self.approve();self.controller.check_readiness(str(self.base))
        with self.assertRaises(ValueError):self.controller.start(str(self.base))
        self.settle();attempt=next((self.base/backend.READINESS).glob('attempt-*'));(attempt/'result.json').unlink()
        self.assertEqual(self.controller.status(str(self.base))['readiness']['state'],'DISPATCH_UNCERTAIN')
        self.assertFalse(self.controller.check_readiness(str(self.base))['dispatched'])
        with self.assertRaises(ValueError):self.controller.start(str(self.base))
        # Restore only the fixture result so cleanup can settle; production
        # evidence never gets synthesized this way.
        value=records.read(attempt/'spawned.json');save(attempt/'result.json',dict(intent=value['intent'],state='PROCESS_EXITED',returncode=0,process=value['process']))

    def test_ready_after_grant_or_existing_dispatch_is_rejected(self):
        for name in ('grant.json','operation-0001'):
            path=self.directory/name;path.touch()
            with self.assertRaises(ValueError):self.controller.check_readiness(str(self.base))
            path.unlink()
        self.approve();self.ready_for_f1();self.controller.start(str(self.base));self.settle()
        with self.assertRaises(ValueError):self.controller.check_readiness(str(self.base))

    def test_recent_raw_validated_readiness_is_reused_without_new_process(self):
        result=save(self.directory/'fixture-ready.json',{'fixture':True})
        records.Journal(self.directory/'journal').append('readiness-complete',result=result)
        with mock.patch.object(mainline,'validate_readiness'),mock.patch.object(backend.subprocess,'Popen') as spawn:
            value=self.controller.check_readiness(str(self.base));self.assertFalse(value['dispatched'])
            self.assertEqual(value['reused_readiness'],result);spawn.assert_not_called()

    def test_settled_failed_d0_can_create_fresh_evidence_without_erasing_old(self):
        self.controller.check_readiness(str(self.base));self.settle()
        first={p:p.read_bytes() for p in (self.base/backend.READINESS).rglob('*') if p.is_file()}
        self.assertTrue(self.controller.check_readiness(str(self.base))['dispatched']);self.settle()
        self.assertEqual(len(list((self.base/backend.READINESS).glob('attempt-*'))),2)
        for p,data in first.items():self.assertEqual(p.read_bytes(),data)

    def test_missing_or_stale_readiness_rejects_before_f1_dispatch_and_can_refresh(self):
        self.approve()
        with self.assertRaises(ValueError):self.controller.start(str(self.base))
        self.assertFalse((self.base/backend.DISPATCH/'intent.json').exists())
        self.assertTrue(self.controller.check_readiness(str(self.base))['dispatched']);self.settle()
        self.ready_for_f1()
        with mock.patch.object(mainline,'validate_readiness',side_effect=ValueError('stale readiness')):
            with self.assertRaises(ValueError):self.controller.start(str(self.base))
            self.assertFalse((self.base/backend.DISPATCH/'intent.json').exists())
            self.assertTrue(self.controller.check_readiness(str(self.base))['dispatched']);self.settle()

    def test_prior_closed_task_readiness_does_not_block_next_f1(self):
        self.controller.check_readiness(str(self.base));self.settle()
        terminal=save(self.base/'closed-terminal.json',dict(terminal_state='ANDROID_CLOSED_HEALTHY',research_closed=True))
        save(self.directory/'closed.json',dict(task=records.pin(self.directory/'task.json'),
            terminal_state='ANDROID_CLOSED_HEALTHY',current_android_terminal=terminal))
        old=self.base;self.base=fixture(self.root,2);self.directory=self.base/'task-1'
        self.approve();self.ready_for_f1()
        self.assertTrue(self.controller.start(str(self.base))['dispatched']);self.settle()
        self.assertEqual(self.controller.status(str(old))['readiness']['state'],'CLOSED_BY_ORIGINAL_OWNER')

    def test_eight_tool_schema_keeps_status_readonly_and_readiness_separate(self):
        tools={row['name']:row for row in transport.tools()}
        self.assertIn('check_task_readiness',tools);self.assertTrue(tools['check_task_readiness']['annotations']['readOnlyHint'])
        self.assertNotIn('command',tools['check_task_readiness']['inputSchema']['properties'])
        self.assertFalse(tools['check_task_readiness']['inputSchema']['additionalProperties'])
        self.assertIn('readiness',tools['task_log']['inputSchema']['properties']['stream']['enum'])
        self.assertEqual(tools['task_status']['inputSchema']['properties'].keys(),{'preparation_directory'})


class EntryTests(unittest.TestCase):
    setUp=TerminalTests.setUp
    settle=TerminalTests.settle
    approve=TerminalTests.approve

    def dispatch(self):
        self.approve();bound=self.controller.bundle(str(self.base),current=True,approval=True)
        return save(self.base/backend.DISPATCH/'intent.json',dict(task=bound['task'],entry=bound['entry'],
            approval=bound['approval'],entry_review=bound['review'],bridge_review={'fixture':'bridge'},
            command=['/usr/bin/python3',str(self.root/entry.ENTRY),'start',str(self.directory/'task.json')]))

    def test_actual_entry_joins_dispatch_and_runs_one_grant_operation_execute(self):
        from s22plus_native_session_v3 import Session
        import s22plus_native_session_v3 as session
        from s22plus_native_adapter_v3 import Adapter
        self.dispatch();calls=[]
        def grant(*args,**kwargs):
            calls.append('grant');self.assertEqual(kwargs['returned_approval'],records.read(self.directory/'proposal.json')['approval'])
            return save(self.directory/'grant.json',{'fixture':True})
        def operation(*args,**kwargs):
            calls.append('operation');self.assertEqual(kwargs['operation'],'mainline-ram')
            path=self.directory/'operation-0001';path.mkdir();return path
        def execute(instance,*,attended):
            calls.append('execute');self.assertTrue(attended);return {'fixture':'awaiting original physical A'}
        with mock.patch.object(backend,'verify_bridge') as bridge,\
             mock.patch.object(mainline,'open_grant',side_effect=grant) as opened,\
             mock.patch.object(session,'prepare_operation',side_effect=operation),\
             mock.patch.object(Adapter,'__init__',return_value=None),\
             mock.patch.object(Session,'__init__',return_value=None),\
             mock.patch.object(Session,'execute',autospec=True,side_effect=execute):
            result=entry.start(self.root,self.directory/'task.json')
            self.assertEqual(result,{'fixture':'awaiting original physical A'})
            self.assertEqual(calls,['grant','operation','execute']);self.assertEqual(opened.call_count,1)
            bridge.assert_called_with(self.root,expected={'fixture':'bridge'})
            with self.assertRaises(ValueError):entry.start(self.root,self.directory/'task.json')
            self.assertEqual(calls,['grant','operation','execute'])
        self.assertTrue((self.base/'mainline-entry-intent.json').exists());self.assertTrue((self.base/'opened-grant.json').exists())

    def test_grant_failure_consumes_exclusive_entry_and_never_calls_grant_twice(self):
        self.dispatch()
        with mock.patch.object(backend,'verify_bridge'),mock.patch.object(mainline,'open_grant',side_effect=ValueError('fixture stale')) as grant:
            with self.assertRaises(ValueError):entry.start(self.root,self.directory/'task.json')
            with self.assertRaises(FileExistsError):entry.start(self.root,self.directory/'task.json')
            self.assertEqual(grant.call_count,1)
        self.assertTrue((self.base/'mainline-entry-intent.json').exists());self.assertFalse((self.directory/'grant.json').exists())
        self.assertFalse(list(self.directory.glob('operation-*')))

    def test_wrong_dispatch_command_rejects_before_entry_or_grant(self):
        self.dispatch();path=self.base/backend.DISPATCH/'intent.json';value=records.read(path)
        value['command'][-1]=str(self.directory/'different.json');save(path,value)
        with mock.patch.object(mainline,'open_grant') as grant:
            with self.assertRaises(ValueError):entry.start(self.root,self.directory/'task.json')
            grant.assert_not_called()
        self.assertFalse((self.base/'mainline-entry-intent.json').exists())


class MainlineContinuationTests(TerminalTests):
    def setUp(self):
        super().setUp();self.approve();self.ready_for_f1();self.controller.start(str(self.base));self.settle()
        from s22plus_native_adapter_v3 import Adapter
        from s22plus_mainline_session_v1 import normal_steps
        self.operation=self.directory/'operation-0001';self.operation.mkdir(mode=0o700)
        selected=records.read(self.directory/'task.json');task_pin=records.pin(self.directory/'task.json');now=records.clock()
        preapproval=save(self.directory/'fixture-preapproval.json',{'fixture':True})
        grant=save(self.directory/'grant.json',dict(schema=records.SCHEMA,task=task_pin,directory=str(self.directory),
            host_boot=records.host_boot(),opened_ns=now,deadline_ns=now+1800_000_000_000,operation_budget=1,
            recovery_mode='attended',operator_statement='fixture',returned_approval=records.read(self.directory/'proposal.json')['approval'],
            preapproval=preapproval))
        request=dict(schema=records.SCHEMA,operation='mainline-ram',task=task_pin,grant=grant,N=selected['N'],A=selected['A'],
            E=None,reentry=False,hud=False,usb_reconnect=False,admission=None,prior_terminal=None)
        operation=save(self.operation/'operation.json',request)
        save(self.operation/'consumed.json',dict(schema=records.SCHEMA,operation_sha256=operation['sha256'],grant=grant))
        self.journal=records.Journal(self.operation/'journal')
        for step in normal_steps()[:-2]:
            value=save(self.operation/(step.name+'.json'),dict(action=step.action,role=step.role))
            self.journal.append('step-start',step=step.name,action=step.action,role=step.role)
            if step.action in ('download','transfer'):self.journal.append('effect-intent',step=step.name,action=step.action,role=step.role)
            self.journal.append('step-complete',step=step.name,result=value)
        save(self.operation/'mainline-return-ready.json',dict(operation=operation,
            observation=records.pin(self.operation/'mainline-evidence.json'),requested_ns=now,deadline_ns=now+600_000_000_000))
        backend.registry.initialize(self.root);backend.registry.begin_f1_owner(self.root,self.operation,operation['sha256'])
        cli=self.root/'workspace/public/src/scripts/revalidation/s22plus_native_task_v3.py'
        cli.write_text("import sys\nfrom pathlib import Path\nassert len(sys.argv)==6 and sys.argv[1]=='--root' and sys.argv[5]=='--attended'\nassert sys.argv[3] in ('continue','recover')\np=Path(sys.argv[4])\nwith (p/('fixture-'+sys.argv[3])).open('x') as f:f.write('once')\n")
        for obj,name,options in [(Adapter,'check',{}),(Adapter,'validate_result',{}),
            (Adapter,'recover_transfer_result',{'return_value':{'completed':True}}),
            (mainline,'validate_readiness',{'return_value':{'observed_ns':now}})]:
            patch=mock.patch.object(obj,name,**options);mocked=patch.start();self.addCleanup(patch.stop)
            if name=='recover_transfer_result':self.raw=mocked

    # Only the continuation cases below use this effect-bearing fixture.
    test_readiness_is_explicit_async_and_does_not_create_grant_or_approval=None
    test_f1_still_requires_actual_approval_and_exact_fixed_argv=None
    test_wrong_scope_or_unattended_record_cannot_spawn=None
    test_running_or_uncertain_readiness_blocks_f1_and_is_not_retried=None
    test_ready_after_grant_or_existing_dispatch_is_rejected=None
    test_recent_raw_validated_readiness_is_reused_without_new_process=None
    test_settled_failed_d0_can_create_fresh_evidence_without_erasing_old=None
    test_eight_tool_schema_keeps_status_readonly_and_readiness_separate=None
    test_missing_or_stale_readiness_rejects_before_f1_dispatch_and_can_refresh=None
    test_prior_closed_task_readiness_does_not_block_next_f1=None

    def test_normal_physical_return_uses_original_observation_and_grant(self):
        value=self.controller.continue_task(str(self.base),'continue_approved_task');self.assertTrue(value['dispatched']);self.settle()
        self.assertTrue((self.operation/'fixture-continue').exists())
        self.assertFalse(self.controller.continue_task(str(self.base),'continue_approved_task')['dispatched'])
        self.raw.assert_not_called()

    def test_interrupted_mainline_without_stopped_row_only_selects_original_a_recovery(self):
        # Host interruption can occur before it appends stopped. The settled
        # original launch and durable effect owner remain the recovery basis.
        value=self.controller.continue_task(str(self.base),'recover_approved_task');self.assertTrue(value['dispatched']);self.settle()
        self.assertTrue((self.operation/'fixture-recover').exists());self.raw.assert_not_called()
        intent=records.read(self.base/backend.CONTINUATIONS['recover_approved_task'][0]/'intent.json')
        self.assertFalse(intent['remaining_health_only'])

    def test_uncertain_a_cannot_dispatch_and_complete_a_is_health_only(self):
        self.journal.append('effect-intent',step='install-android',action='transfer',role='A')
        self.journal.append('stopped',error_type='fixture')
        self.raw.side_effect=ValueError('uncertain transfer')
        with self.assertRaises(ValueError):self.controller.continue_task(str(self.base),'recover_approved_task')
        self.assertFalse((self.base/backend.CONTINUATIONS['recover_approved_task'][0]/'intent.json').exists())
        self.raw.side_effect=None;self.controller.continue_task(str(self.base),'resume_approved_health');self.settle()
        intent=records.read(self.base/backend.CONTINUATIONS['resume_approved_health'][0]/'intent.json')
        self.assertTrue(intent['remaining_health_only']);self.assertEqual(self.raw.call_args.args[0].name,'install-android')


if __name__=='__main__':unittest.main()
