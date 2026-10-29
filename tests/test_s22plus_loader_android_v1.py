"""Fixed raw Android evidence and one-shot loader-control interruption paths."""
import copy
from contextlib import ExitStack
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest import mock

import test_s22plus_native_session_v3 as harness
import test_s22plus_native_target_io_v3 as target_harness
import test_s22plus_mainline_live_v1 as mainline_tests
import s22plus_loader_android_access_v1 as access
import s22plus_loader_android_profile_v1 as profile
import s22plus_loader_android_session_v1 as control
import s22plus_mainline_task_v1 as tasks
import s22plus_native_adapter_v3 as adapter_module
import s22plus_native_session_v3 as owner
import s22plus_native_records_v3 as records
import s22plus_native_target_io_v3 as target
import device_action_raw_capture_v1 as raw


class ProofTests(unittest.TestCase):
    def setUp(self):
        if hasattr(self,'_stack'):self._stack.close()
        self.fixture=target_harness.TargetTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.base=self.fixture.directory
        self.task=dict(target=self.fixture.binding,A=copy.deepcopy(self.fixture.android),adb={'fixture':True},
            N=dict(profile=profile.PROFILE,boot_sha256='b'*64,marker_sha256='c'*64,
                   kernel_release=self.fixture.properties['kernel_release']))
        self.request=dict(operation=profile.OPERATION,N=self.task['N'],A=self.task['A'])
        self.request['grant']=records.publish(self.base/'grant.json',dict(host_boot=records.host_boot(),
            deadline_ns=records.clock()+600_000_000_000))
        records.publish(self.base/'operation.json',self.request)
        self.launch=records.publish(self.base/'launch.json',dict(boottime_ns=records.clock()-1_000_000_000))
        self.preflight=self.base/'io-preflight';self.preflight.mkdir()
        records.publish(self.preflight/'health.json',dict(boot_id_sha256='0'*64))
        outer=self
        class Adapter:
            directory=outer.base
            def configuration(self,request):return outer.task
            def folder(self,name,create=False):
                p=outer.base/('io-'+name)
                if create:p.mkdir()
                return p
            def recover_transfer_result(self,step,request):return {'launch':outer.launch}
        self.adapter=Adapter();self.commands=[];self.changed={};self.last_changed={};self.root_changed={}
        self.stderr=b'';self.failed=False;self.generation='fixture-generation'
        stack=ExitStack();self._stack=stack;self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(profile,'image_binding',return_value={}))
        stack.enter_context(mock.patch.object(access.CandidateAndroid,'command',autospec=True,side_effect=self.command))
        stack.enter_context(mock.patch.object(target,'usb_snapshot',side_effect=lambda topology,folder:
            dict(topology=topology,identity={'generation':self.generation},boottime_ns=records.clock())))

    def command(self,client,arguments,name,*,timeout,before_launch=None):
        client.guard()
        if before_launch:before_launch()
        self.commands.append(arguments)
        properties=dict(self.fixture.properties,**self.changed)
        root=dict(root='uid=0(root) gid=0(root)',**access.candidate_artifact(self.task)['partition_sha256'],
                  loader_marker=self.task['N']['marker_sha256'])
        root.update(self.root_changed)
        if name.endswith('-inventory'):text=self.fixture.inventory
        elif name.endswith('-boot'):text='boot_completed=1\nbootanim=stopped'
        else:
            index=int(name[:2])
            if index in (0,4):text=self.fixture.inventory
            elif index in (1,5):text=self.fixture.binding['topology']
            elif index==3:
                self.assertEqual(arguments,['-s',self.fixture.binding['serial'],'shell',
                    'su -c '+shlex.quote(access.CandidateAndroid.ROOT_COMMAND)])
                text='\n'.join(k+'='+v for k,v in root.items())
            else:
                if index==6:properties.update(self.last_changed)
                text='\n'.join(k+'='+v for k,v in properties.items())
        return raw.publish_captured_bytes(client.directory,name,stdout=text.encode(),
            stderr=self.stderr if name=='03-health' else b'',
            returncode=1 if self.failed and name=='03-health' else 0)

    def observe(self):return access.observe(self.adapter,self.request,lambda:None)

    def test_real_command_producer_and_raw_projection_then_offline_rederivation(self):
        value=self.observe()
        self.assertEqual(value['status'],'PASS_LOADER_FYG8_ANDROID')
        self.assertEqual(value['health']['partition_sha256']['boot'],'b'*64)
        self.assertEqual(value['health']['loader_marker_sha256'],'c'*64)
        before=list(self.commands)
        with mock.patch.object(access.CandidateAndroid,'command',side_effect=AssertionError('new read')):
            self.assertEqual(access.rederive(self.adapter,self.request),value)
        self.assertEqual(self.commands,before)
        for receipt in value['health']['captures']:
            handle=raw.load_handle(Path(receipt['path']))
            self.assertEqual(handle.stdout_path.stat().st_mode&0o777,0o400)

    def test_exact_marker_kernel_root_and_partitions_are_required(self):
        for group,key,value in [('root','loader_marker','d'*64),('root','boot','1'*64),
            ('root','vendor_boot','d'*64),('root','root','uid=1000 gid=1000'),
            ('properties','kernel_release','different-kernel')]:
            with self.subTest(key=key):
                self.setUp()
                (self.root_changed if group=='root' else self.changed)[key]=value
                with self.assertRaises(ValueError):self.observe()
                self.assertTrue((self.adapter.folder(profile.SELECTION)/'proof/03-health.capture.json').exists())
                self.assertFalse((self.adapter.folder(profile.SELECTION)/'proof/complete.json').exists())

    def test_changed_boot_and_root_stderr_do_not_become_health(self):
        self.last_changed['boot_id']='87654321-1234-1234-1234-123456789abc'
        with self.assertRaises(ValueError):self.observe()
        self.setUp();self.stderr=b'sha256sum: missing marker\n'
        with self.assertRaises(raw.RawCaptureError):self.observe()
        path=self.adapter.folder(profile.SELECTION)/'proof/03-health.capture.json'
        self.assertEqual(raw.read_stderr(raw.load_handle(path),maximum=16384),self.stderr)

    def test_failed_producer_preserves_raw_and_has_no_success_publication(self):
        self.failed=True
        with self.assertRaises(raw.RawCaptureError):self.observe()
        path=self.adapter.folder(profile.SELECTION)/'proof/03-health.capture.json'
        handle=raw.load_handle(path);self.assertEqual(handle.returncode,1)
        self.assertIn(b'loader_marker=',raw.read_stdout(handle,maximum=16384))
        self.assertFalse((path.parent/'complete.json').exists())

    def test_initial_boot_reuse_missing_raw_and_late_proof_reject(self):
        self.changed['boot_id']='00000000-0000-0000-0000-000000000000'
        path=self.preflight/'health.json';path.unlink()
        records.publish(path,dict(boot_id_sha256=records.digest(self.changed['boot_id'].encode())))
        with self.assertRaises(ValueError):self.observe()
        self.setUp();value=self.observe();Path(value['health']['captures'][3]['path']).unlink()
        with self.assertRaises((ValueError,OSError,raw.RawCaptureError)):access.rederive(self.adapter,self.request)
        self.setUp()
        with mock.patch.object(access,'clock',return_value=records.read(self.base/'grant.json')['deadline_ns']+1):
            with self.assertRaises(ValueError):self.observe()
        self.assertEqual(self.commands,[])

    def test_return_requires_same_boot_and_current_usb_generation(self):
        value=self.observe();folder=self.adapter.folder(profile.RETURN,create=True)
        receipt=access.before_return(self.adapter,self.request,folder,lambda:None)
        self.assertEqual(access.return_proof(self.adapter,self.request,receipt)['boot_id_sha256'],
                         value['health']['boot_id_sha256'])
        with self.assertRaises(ValueError):access.return_proof(self.adapter,self.request,receipt,
            current_usb={'identity':{'generation':'new'}})
        self.setUp();self.observe();self.changed['boot_id']='87654321-1234-1234-1234-123456789abc'
        with self.assertRaises(ValueError):access.before_return(self.adapter,self.request,
            self.adapter.folder(profile.RETURN,create=True),lambda:None)

    def test_reattachment_during_full_bracket_is_not_control_evidence(self):
        generations=iter(('first','second'))
        with mock.patch.object(target,'usb_snapshot',side_effect=lambda topology,folder:
                dict(topology=topology,identity={'generation':next(generations)},boottime_ns=records.clock())):
            with self.assertRaises(ValueError):self.observe()
        self.assertFalse((self.adapter.folder(profile.SELECTION)/'proof/complete.json').exists())

    def test_historical_rederivation_survives_host_reboot_but_live_paths_do_not(self):
        value=self.observe();folder=self.adapter.folder(profile.RETURN,create=True)
        receipt=access.before_return(self.adapter,self.request,folder,lambda:None)
        before=list(self.commands);window=access.window_for(self.adapter,self.request)
        with mock.patch.object(access,'host_boot',return_value='different-host-boot'):
            self.assertEqual(access.rederive(self.adapter,self.request),value)
            access.return_proof(self.adapter,self.request,receipt)
            with self.assertRaises(ValueError):access.return_proof(self.adapter,self.request,receipt,
                current_usb={'identity':{'generation':self.generation}})
            with self.assertRaises(ValueError):access.capture_health(self.adapter,self.request,
                self.base/'new-live-proof',lambda:None,window,wait=False)
        self.assertEqual(self.commands,before)
        grant=dict(records.read(records.verify(self.request['grant'])),schema=owner.SCHEMA,
                   opened_ns=window['opened_ns'])
        with mock.patch.object(owner,'host_boot',return_value='different-host-boot'):
            for recovery in (False,True):
                with self.assertRaises(ValueError):owner.live_grant(grant,recovery=recovery)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp

    def operation(self):
        class Device(harness.DeviceFixture):
            def android_download(device,step,request,*,guard,before_dispatch):
                guard();device.assert_mode('N' if step.name==profile.RETURN else 'A')
                device.effect(step,before_dispatch);return device.proof(step)
        device=Device();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        def observe(adapter,request,guard):
            guard();adapter.assert_mode('N');adapter.actions.append('candidate-proof-once')
            if adapter.fail_after=='observation':raise OSError('partial candidate proof')
            return adapter.proof(control.normal_steps()[2])
        patch=mock.patch.object(access,'observe',observe);patch.start();self.addCleanup(patch.stop)
        return owner.Session(self.root,directory,device),device

    def test_normal_graph_returns_a_without_physical_pause_and_cannot_replay(self):
        session,device=self.operation();result=session.execute(attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED');self.assertFalse(result['recovered'])
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count(profile.RETURN),1)
        self.assertEqual(device.actions.count('candidate-proof-once'),1);self.assertIsNone(self.f1)
        before=list(device.actions);session.repair_close();self.assertEqual(device.actions,before)
        with self.assertRaises(ValueError):session.execute(attended=True)

    def test_candidate_or_return_fault_only_preserves_original_a_recovery(self):
        for point in ('install-native-first','observation',profile.RETURN):
            with self.subTest(point=point):
                self.setUp();session,device=self.operation();device.fail_after=point
                self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
                before=list(device.actions);device.fail_after=None;session.recover(attended=True)
                self.assertEqual(device.installed,['N','A'])
                self.assertEqual(device.actions.count('candidate-proof-once'),before.count('candidate-proof-once'))
                self.assertEqual(device.actions.count(profile.RETURN),before.count(profile.RETURN))

    def test_uncertain_a_never_repeats_and_complete_a_health_is_separate(self):
        session,device=self.operation();device.fail_after='install-android'
        self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        with self.assertRaises((ValueError,KeyError)):session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])
        self.setUp();session,device=self.operation();device.health_failure=True
        session.execute(attended=True);device.health_failure=False;session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])

    def test_result_publication_fault_stops_and_recovery_never_repeats_observation(self):
        session,device=self.operation();original=owner.publish
        def fail(path,value):
            if path.name==profile.SELECTION+'.json':raise OSError('publication fault')
            return original(path,value)
        with mock.patch.object(owner,'publish',side_effect=fail):
            self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        self.assertTrue(any(r['event']=='stopped' for r in session.rows()))
        session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('candidate-proof-once'),1)

    def test_final_publication_fault_is_closed_from_raw_without_another_a(self):
        session,device=self.operation();original=owner.publish
        def fail(path,value):
            if path.name=='android-final.json':raise OSError('publication fault')
            return original(path,value)
        with mock.patch.object(owner,'publish',side_effect=fail):session.execute(attended=True)
        before=list(device.actions);session.recover(attended=True)
        self.assertEqual(device.actions,before);self.assertEqual(device.installed,['N','A'])

    def test_stop_after_a_intent_never_asks_operator_to_enter_download(self):
        session,device=self.operation();device.health_failure=True
        value=session.execute(attended=True)
        self.assertTrue(value['original_a_transfer_intended'])
        self.assertIn('Do not enter Download or repeat',value['next_action'])
        self.assertIn('health-only',value['next_action'])
        self.setUp();session,device=self.operation();device.fail_after='install-android'
        value=session.execute(attended=True)
        self.assertTrue(value['original_a_transfer_intended'])
        self.assertIn('Reconcile its retained raw completion',value['next_action'])

    def test_expiry_cannot_renew_candidate_or_normal_return(self):
        session,device=self.operation();device.fail_after='observation';session.execute(attended=True)
        with mock.patch.object(owner,'clock',return_value=session.grant['deadline_ns']+1):
            with self.assertRaises(ValueError):session.execute(attended=True)
            session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])


class ScopeTests(mainline_tests.ScopeTests):
    def setUp(self):
        super().setUp()
        self.value.update(schema=profile.TASK_SCHEMA,operations=[profile.OPERATION])
        self.value['N']['profile']=profile.PROFILE;del self.value['mainline_access']
        patch=mock.patch.object(profile,'image_binding',return_value={});patch.start();self.addCleanup(patch.stop)

    test_scope_changes_reject_and_recovery_does_not_need_candidate_or_network_tools=None

    def test_scope_exactness_and_candidate_independent_recovery(self):
        tasks.validate_task(self.root,self.value)
        for key,value in [('schema','s22plus-mainline-task-v1'),('operations',['mainline-ram']),
                          ('seconds',1801),('operation_budget',2),('recovery_mode','deferred'),('hud',True),
                          ('E',{}),('mainline_access',{})]:
            invalid=copy.deepcopy(self.value);invalid[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):tasks.validate_task(self.root,invalid)
        with mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError):
            tasks.validate_task(self.root,self.value,recovery=True)
            with self.assertRaises(FileNotFoundError):tasks.validate_task(self.root,self.value)
        text=tasks.tasks.approval_text(self.value,{'sha256':'a'*64})
        self.assertTrue(text.startswith('APPROVE S22PLUS LOADER ANDROID V1 '))


class ReturnDeadlineTests(unittest.TestCase):
    def test_journal_delay_crossing_original_window_never_spawns_download(self):
        with tempfile.TemporaryDirectory() as name:
            directory=Path(name);folder=directory/profile.RETURN;folder.mkdir()
            now=[100];spawned=[]
            class Android:
                def download(self,*,before_dispatch):
                    before_dispatch();spawned.append(True);return {}
            adapter=mock.Mock();adapter.folder.return_value=folder;adapter.android.return_value=Android()
            def delayed(detail):detail();now[0]=201
            with mock.patch.object(access,'before_return',return_value={'fixture':True}), \
                 mock.patch.object(access,'window_for',return_value={'deadline_ns':200}), \
                 mock.patch.object(access,'return_proof'), \
                 mock.patch.object(adapter_module,'clock',side_effect=lambda:now[0]), \
                 mock.patch.object(target,'usb_snapshot',return_value={'fixture':True}):
                with self.assertRaisesRegex(ValueError,'original loader window expired'):
                    adapter_module.Adapter.android_download(adapter,owner.Step(profile.RETURN,'download','N'),
                        {'operation':profile.OPERATION},guard=lambda:None,before_dispatch=delayed)
            self.assertEqual(spawned,[]);self.assertTrue((folder/'departure-before.json').exists())

    def test_a_uses_candidate_download_intent_and_not_initial_entry_window(self):
        with tempfile.TemporaryDirectory() as name:
            directory=Path(name);journal=records.Journal(directory/'journal')
            adapter=type('Adapter',(),{'directory':directory})()
            journal.append('effect-intent',step='android-download',action='download',role='A',
                           detail={'departure_deadline_ns':30})
            self.assertEqual(control.arrival_deadline(adapter,owner.Step('install-native-first','transfer','N'),{}),
                             60_000_000_030)
            with self.assertRaises(ValueError):control.arrival_deadline(adapter,owner.Step('install-android','transfer','A'),{})
            journal.append('effect-intent',step='install-native-first',action='transfer',role='N',detail={})
            journal.append('effect-intent',step=profile.RETURN,action='download',role='N',
                           detail={'departure_deadline_ns':900})
            self.assertEqual(control.arrival_deadline(adapter,owner.Step('install-android','transfer','A'),{}),
                             60_000_000_900)


class CandidateReadinessTests(unittest.TestCase):
    def test_boot_complete_waits_for_stopped_animation_without_reusing_a_health_prefix(self):
        fixture=target_harness.TargetTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        task=dict(adb={},target=fixture.binding,A=fixture.android,N={'boot_sha256':'a'*64})
        client=access.CandidateAndroid(task,fixture.directory,guard=lambda:None)
        outputs=iter([fixture.inventory,'boot_completed=1\nbootanim=running\n',
                      fixture.inventory,'boot_completed=1\nbootanim=stopped\n'])
        calls=[]
        def command(arguments,name,**options):
            options['before_launch']();calls.append(arguments)
            return raw.publish_captured_bytes(fixture.directory,name,stdout=next(outputs).encode())
        with mock.patch.object(client,'command',side_effect=command),mock.patch.object(target.time,'sleep'):
            client.wait_ready(deadline_ns=records.clock()+60_000_000_000)
        self.assertEqual(calls[1][-1],client.READY_COMMAND);self.assertEqual(calls[3][-1],client.READY_COMMAND)
        self.assertEqual(len(list(fixture.directory.glob('*.capture.json'))),4)
        self.assertFalse((fixture.directory/'health.json').exists())
        self.assertFalse(client.readiness_complete('boot_completed=\nbootanim='))
        with self.assertRaises(ValueError):client.readiness_complete('boot_completed=1\nbootanim=invalid')


class HistoricalReadinessTests(unittest.TestCase):
    def test_historical_grant_joins_original_epoch_and_cannot_become_fresh_readiness(self):
        fixture=target_harness.TargetTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        base=fixture.directory;now=records.clock();original_boot=records.host_boot()
        task=dict(target=fixture.binding,A=fixture.android,N={'profile':profile.PROFILE},
                  seconds=1800,operation_budget=1,recovery_mode='attended')
        task_pin=records.publish(base/'task.json',task);folder=base/'ready-1';folder.mkdir()
        health=records.publish(folder/'health.json',target.health_projection(
            fixture.captures(),fixture.binding,fixture.android))
        ready=records.publish(folder/'ready.json',dict(schema='s22plus-mainline-ready-v1',task=task_pin,
            host_boot=original_boot,observed_ns=now,health=health,network_permissions=None,
            device_controls=0,partition_transfers=0))
        records.Journal(base/'journal').append('readiness-complete',result=ready)
        grant=dict(schema=records.SCHEMA,task=task_pin,directory=str(base),host_boot=original_boot,
            opened_ns=now+1,deadline_ns=now+1+1800_000_000_000,operation_budget=1,recovery_mode='attended',
            operator_statement='fixture',returned_approval=tasks.tasks.approval_text(task,task_pin),preapproval=ready)
        with mock.patch.object(tasks,'host_boot',return_value='different-host-boot'):
            tasks.tasks.validate_grant(task,grant,base/'grant.json')
            with self.assertRaises(ValueError):tasks.validate_readiness(task,ready,task_pin,fresh=True)
            with self.assertRaises(ValueError):tasks.tasks.validate_grant(task,
                dict(grant,host_boot='different-host-boot'),base/'grant.json')


class CloseTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp

    def prepare_closed(self):
        task_path=self.task/'task.json'
        task_pin=records.publish(task_path,dict(N={'profile':profile.PROFILE},review={'fixture':True}))
        records.publish(self.task/'source-snapshot.json',dict(task=task_pin,sources=[]))
        class Device(harness.DeviceFixture):
            def prepare(device,operation,grant,**options):return dict(task=task_pin)
            def android_download(device,step,request,*,guard,before_dispatch):
                guard();device.assert_mode('N' if step.name==profile.RETURN else 'A')
                device.effect(step,before_dispatch);return device.proof(step)
            def terminal(device,steps,values,request,*,recovered):
                return dict(terminal_state='ANDROID_CLOSED_HEALTHY',terminal_step=steps[-1].name,
                            loader_android={'status':'PASS_LOADER_FYG8_ANDROID'})
        device=Device()
        directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        def observe(adapter,request,guard):
            guard();adapter.assert_mode('N');return adapter.proof(control.normal_steps()[2])
        session=owner.Session(self.root,directory,device)
        with mock.patch.object(access,'observe',observe):session.execute(attended=True)
        for module,name,value in [(tasks,'validate_task',None),(tasks.tasks,'validate_grant',None),
                                  (adapter_module,'Adapter',device)]:
            patch=mock.patch.object(module,name,return_value=value);patch.start();self.addCleanup(patch.stop)
        self.failed_raw=raw.publish_captured_bytes(directory,'preserved-failure',stdout=b'partial',
                                                  stderr=b'closed',returncode=1)
        return task_path,session,device

    def test_close_and_each_publication_interruption_never_reacquire_or_rewrite(self):
        for stop in (None,'raw-index.json','timeline.json','closed.json'):
            with self.subTest(stop=stop):
                self.setUp();path,session,device=self.prepare_closed()
                before=list(device.actions);journal=[records.pin(p) for p in sorted(session.journal.directory.glob('*.json'))]
                original=tasks.publish
                def interrupt(destination,value):
                    result=original(destination,value)
                    if destination.name==stop:raise OSError('after durable publication')
                    return result
                if stop:
                    with mock.patch.object(tasks,'publish',side_effect=interrupt):
                        with self.assertRaises(OSError):tasks.close_task(self.root,path)
                retained=[records.pin(p) for p in self.task.glob('*.json')]
                receipt=tasks.close_task(self.root,path);self.assertEqual(tasks.close_task(self.root,path),receipt)
                for item in retained:self.assertEqual(records.pin(Path(item['path'])),item)
                self.assertEqual(device.actions,before)
                self.assertEqual([records.pin(p) for p in sorted(session.journal.directory.glob('*.json'))],journal)
                closed=records.read(Path(receipt['path']))
                self.assertEqual((closed['original_N_transfers_total'],closed['original_A_transfers_total']),(1,1))
                self.assertEqual(closed['device_actions_by_closure'],0)
                captures=records.read(records.verify(closed['raw_captures']))['captures']
                self.assertEqual([x['returncode'] for x in captures],[1])

    def test_tampered_raw_or_missing_health_never_retries_device(self):
        path,session,device=self.prepare_closed();before=list(device.actions)
        self.failed_raw.stderr_path.unlink()
        with self.assertRaises((OSError,ValueError,raw.RawCaptureError)):tasks.close_task(self.root,path)
        self.assertEqual(device.actions,before);self.assertFalse((self.task/'closed.json').exists())
        self.setUp();path,session,device=self.prepare_closed();before=list(device.actions)
        del device.proofs['android-final']
        with self.assertRaises((OSError,ValueError,KeyError)):tasks.close_task(self.root,path)
        self.assertEqual(device.actions,before);self.assertFalse((self.task/'closed.json').exists())


if __name__=='__main__':unittest.main()
