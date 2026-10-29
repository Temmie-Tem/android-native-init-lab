"""Fixed collector through real raw/health consumers, with a synthetic closed owner."""
from contextlib import ExitStack,nullcontext
from pathlib import Path
import unittest
from unittest import mock
import hashlib
import json
import tempfile

import test_s22plus_native_target_io_v3 as health_fixture
import s22plus_mainline_retention_v1 as retention
from s22plus_native_records_v3 import pin,publish,read
import s22plus_native_adapter_v3 as adapters
import s22plus_native_session_v3 as sessions

class RetentionTests(unittest.TestCase):
    setUp=health_fixture.TargetTests.setUp
    captures=health_fixture.TargetTests.captures

    def setup_owner(self,version=1):
        self.root=self.directory;self.private=self.root/'workspace/private';self.private.mkdir(parents=True)
        self.owner=self.private/'task';self.owner.mkdir();key=self.owner/'key';key.write_bytes(bytes(range(32)))
        self.candidate='12'*32
        config=publish(self.owner/'config.json',retention.marker.configuration(self.candidate,key.read_bytes(),version=version))
        qualified=publish(self.owner/'marker-qualification.json',dict(config=config))
        self.task=dict(target=self.binding,A=self.android,N={'key':pin(key),'retained_marker':qualified},
            adb=pin(Path('/usr/bin/adb').resolve(),maximum=32*1024**2))
        self.bound=dict(task=self.task,task_receipt=publish(self.owner/'task.json',self.task),
            closed=publish(self.owner/'closed.json',dict(synthetic_owner=True)),
            terminal=publish(self.owner/'terminal.json',dict(synthetic_owner=True)),
            returned=retention.target.health_projection(self.captures(),self.binding,self.android),
            manifest={'candidate_id':self.candidate})
        self.review=publish(self.owner/'review.json',dict(synthetic_review=True))
        self.calls=[]

    def run_capture(self,name,*,failed=False,changed_after=False,data=None):
        if data is None:data=retention.marker.frame(self.candidate,bytes(range(32)),1)
        def acquire(arguments,folder,label,**options):
            self.calls.append((arguments,folder,label,options))
            rc=0
            if label=='features':out=b'shell_v2\n'
            elif label=='last-kmsg':out=data;rc=1 if failed else 0
            else:
                index=int(label[:2]);props=dict(self.properties)
                if changed_after and Path(folder).name=='after':props['boot_id']='87654321-1234-1234-1234-123456789abc'
                health=dict(root='uid=0(root) gid=0(root)',**self.android['partition_sha256'])
                lines=[self.inventory,self.binding['topology'],'\n'.join(k+'='+v for k,v in props.items()),
                       '\n'.join(k+'='+v for k,v in health.items()),self.inventory,self.binding['topology'],
                       '\n'.join(k+'='+v for k,v in props.items())]
                out=lines[index].encode()
            return retention.raw.publish_captured_bytes(folder,label,stdout=out,returncode=rc)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(retention,'closed_binding',return_value=self.bound))
            stack.enter_context(mock.patch.object(retention.registry,'target_session_lease',return_value=nullcontext()))
            stack.enter_context(mock.patch.object(retention.registry,'require_no_f1_owner'))
            stack.enter_context(mock.patch.object(retention.tasks,'capability',return_value=self.review))
            stack.enter_context(mock.patch.object(retention.raw,'acquire_command',side_effect=acquire))
            return retention.capture(self.root,self.private/name,self.owner)

    def test_fixed_command_raw_health_projection_and_offline_reopen(self):
        self.setup_owner();result=self.run_capture('capture')
        value=read(Path(result['path']));self.assertEqual(value['observed_stages'],['loader-handoff'])
        self.assertFalse(value['mainline_pid1']);self.assertFalse(value['same_boot_pair_proved'])
        self.assertEqual(len(self.calls),16)
        calls=[x for x in self.calls if x[2]=='last-kmsg'];self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0][1:],['-s','FIXTURE123','shell','-T',"su -c 'cat /proc/last_kmsg'"])
        self.assertEqual(calls[0][3],dict(timeout=30,stdout_maximum=4*1024**2,stderr_maximum=16384))
        with mock.patch.object(retention,'closed_binding',return_value=self.bound),\
             mock.patch.object(retention.raw,'acquire_command',side_effect=AssertionError('device replay')):
            self.assertEqual(retention.projection(self.root,self.private/'capture',self.owner),value)

    def test_failed_read_seals_bytes_and_new_invocation_does_not_modify_old(self):
        self.setup_owner()
        with self.assertRaises(retention.raw.RawCaptureError):self.run_capture('failed',failed=True,data=b'partial')
        handle=retention.raw.load_handle(self.private/'failed/last-kmsg.capture.json')
        self.assertEqual(retention.raw.read_stdout(handle,maximum=100),b'partial')
        stop=pin(self.private/'failed/stopped.json');self.assertFalse((self.private/'failed/result.json').exists())
        self.assertEqual(len(self.calls),9)
        self.run_capture('fresh');self.assertEqual(pin(self.private/'failed/stopped.json'),stop)

    def test_v2_projects_only_qualified_mmu_stages(self):
        self.setup_owner(version=2)
        data=b''.join(retention.marker.frame(self.candidate,bytes(range(32)),stage,version=2) for stage in (3,4))
        value=read(Path(self.run_capture('v2',data=data)['path']))
        self.assertEqual(value['observed_stages'],['early-c','pre-mmu'])
        self.assertFalse(value['same_boot_pair_proved']);self.assertFalse(value['mainline_pid1'])
    def test_v3_later_marker_is_positive_without_first(self):
        self.setup_owner(version=3)
        data=retention.marker.frame(self.candidate,bytes(range(32)),6,version=3)
        value=read(Path(self.run_capture('v3',data=data)['path']))
        self.assertEqual(value['observed_stages'],['post-paging'])
        self.assertEqual(value['status'],'RETAINED_STAGE_OBSERVED')
        self.assertFalse(value['reset_cause_proved']);self.assertFalse(value['mainline_pid1'])

    def test_v4_uses_its_qualified_domain_and_preserves_later_only_evidence(self):
        self.setup_owner(version=4)
        key=bytes(range(32))
        data=retention.marker.frame(self.candidate,key,6,version=3)+retention.marker.frame(self.candidate,key,8,version=4)
        value=read(Path(self.run_capture('v4',data=data)['path']))
        self.assertEqual(value['observed_stages'],['post-time-init'])
        self.assertEqual(value['status'],'RETAINED_STAGE_OBSERVED')
        self.assertFalse(value['reset_cause_proved']);self.assertFalse(value['mainline_pid1'])
        self.assertFalse(value['same_boot_pair_proved']);self.assertFalse(value['replay_authorized'])

    def test_changed_return_boot_keeps_raw_but_never_proves_stage(self):
        self.setup_owner()
        with self.assertRaisesRegex(ValueError,'Android changed'):self.run_capture('changed',changed_after=True)
        self.assertTrue((self.private/'changed/last-kmsg.capture.json').exists())
        self.assertFalse((self.private/'changed/result.json').exists())

    def test_v5_projection_keeps_older_records_and_missing_first_non_authoritative(self):
        self.setup_owner(version=5)
        key=bytes(range(32))
        data=retention.marker.frame(self.candidate,key,8,version=4)+retention.marker.frame(self.candidate,key,10,version=5)
        value=read(Path(self.run_capture('v5',data=data)['path']))
        self.assertEqual(value['observed_stages'],['pre-rest-init'])
        self.assertEqual(value['status'],'RETAINED_STAGE_OBSERVED')
        self.assertFalse(value['same_boot_pair_proved']);self.assertFalse(value['mainline_pid1'])
        self.assertFalse(value['replay_authorized']);self.assertFalse(value['stopped_at_last_record'])

    def test_fresh_same_target_health_required_before_proc_read(self):
        self.setup_owner();self.bound['returned']=dict(self.bound['returned'],boot_id_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'rebooted since'):self.run_capture('wrong-boot')
        self.assertEqual(len(self.calls),7)

    def test_partial_or_unmarked_owner_is_not_collectable(self):
        self.root=self.directory;self.owner=self.root/'workspace/private/task';self.owner.mkdir(parents=True)
        publish(self.owner/'task.json',dict(schema=retention.profile.TASK_SCHEMA,N={'profile':retention.profile.PROFILE},operations=[retention.profile.OPERATION]))
        publish(self.owner/'closed.json',dict(terminal_state='ANDROID_CLOSED_HEALTHY'))
        with self.assertRaisesRegex(ValueError,'not an instrumented'):retention.closed_binding(self.root,self.owner)

    def test_marker_inputs_are_not_recovery_hash_prerequisites(self):
        self.root=self.directory;paths=[]
        for relative in ('workspace/public/src/scripts/revalidation/s22plus_mainline_task_v1.py',
                         'workspace/public/src/mainline/s22plus_canary_h0/retained_marker.py',
                         'workspace/public/src/scripts/revalidation/s22plus_mainline_retention_v1.py'):
            p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(relative);paths.append(p)
        paths.sort();selected=retention.profile;review=self.root/selected.REVIEW;review.parent.mkdir(parents=True)
        publish(review,dict(schema=selected.REVIEW_SCHEMA,verdict='PASS_GO',scope=selected.REVIEW_SCOPE,
            sources=[dict(pin(p),path=str(p.relative_to(self.root))) for p in paths],reviewer='TEST FIXTURE',findings=[]))
        with mock.patch.object(retention.tasks,'source_paths',return_value=paths):
            retention.tasks.capability(self.root)
            for p in paths:
                if retention.tasks.marker_only(str(p.relative_to(self.root))):p.unlink()
            retention.tasks.capability(self.root,recovery=True)
            with self.assertRaises(OSError):retention.tasks.capability(self.root)
            next(p for p in paths if p.exists()).write_text('changed recovery owner')
            with self.assertRaises(ValueError):retention.tasks.capability(self.root,recovery=True)

class MarkerAdmissionTests(unittest.TestCase):
    def test_explicit_producer_receipts_must_match_package_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);package=root/'package';loader=root/'loader'
            tests=root/'chosen-loader-tests';entry=root/'chosen-entry-tests'
            for p in (package,loader,tests,entry):p.mkdir()
            a=publish(tests/'result.json',dict(fixture='loader'))
            e=publish(entry/'result.json',dict(fixture='entry'))
            publish(loader/'result.json',{})
            publish(package/'result.json',dict(qualification_sha256=a['sha256'],entry_vm_sha256='00'*32))
            output=root/'workspace/private/output'
            with mock.patch.object(retention.profile,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'explicit test receipts'):
                    retention.profile.qualify(package,loader,output,loader_qualification=tests,entry_vm=entry)
                self.assertFalse(output.exists())
                # Resolving an explicit missing receipt must also leave no output.
                with self.assertRaises(OSError):
                    retention.profile.qualify(package,loader,output,loader_qualification=root/'missing',entry_vm=entry)
                self.assertFalse(output.exists())

    def qualify(self,version,change=lambda value:None):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);key=base/'key';key.write_bytes(bytes(range(32)))
            manifest={'candidate_id':'12'*32};manifest_pin=publish(base/'init.json',manifest)
            cfg=publish(base/'config.json',retention.marker.configuration(manifest['candidate_id'],key.read_bytes(),version=version))
            stages=list(retention.marker.c_stages(read(Path(cfg['path']))))
            common=dict(config=cfg,loader_sha256='34'*32,kernel_sha256='56'*32,
                        device_actions=0,physical_retention_proved=False)
            tests=publish(base/'tests.json',dict(common,status='PASS_H0_ACTUAL_RETAINED_MARKERS',
                mmu_on=dict(status='PASS_H0_ACTUAL_EARLY_C',kernel_sha256=common['kernel_sha256'],qualified_c_stages=stages)))
            vm=dict(common,status='PASS_H0_ACTUAL_EL_RETAINED_MARKERS',qualification_sha256=tests['sha256'],
                mmu_on=dict(status='PASS_H0_ACTUAL_KERNEL_MMU_MARKERS',kernel_sha256=common['kernel_sha256'],
                            qualified_c_stages=stages,post_paging_no_linear_alias_proved=True))
            if version in (4,5):
                vm['mmu_on'].update(late_fixmap_proved=True,cases=[dict(case=name,actual_c_el=el,
                    late_context_stages=stages,no_linear_alias_stages=stages,late_fixmap_proved=True,
                    first_c_returned=True,mapping_slots_restored=True,temporary_mapping_attribute_stages=stages)
                    for name,el in (('normal',2),('normal-el1',1))])
            if version==5:
                vm['mmu_on']['bootstrap_context_proved']=True
                for row in vm['mmu_on']['cases']:
                    row['bootstrap_contexts']=[dict(stage=s,initial_task=True,boot_cpu=0,online_cpus=1,
                                                   preempt_count_low32=1,irq_masked=s==9) for s in stages]
            change(vm)
            vm_pin=publish(base/'vm.json',vm)
            qualified=publish(base/'qualified.json',dict(schema='s22plus-mainline-marker-qualification-v1',
                status='PASS_H0_MAINLINE_RETAINED_MARKER',config=cfg,tests=tests,entry_vm=vm_pin,device_actions=0))
            source=publish(base/'source.json',dict(config=cfg,init_manifest=manifest_pin))
            image=dict(retained_marker=qualified,key=pin(key),runtime_sources={
                'loader':{'sha256':common['loader_sha256']},'kernel':{'sha256':common['kernel_sha256']}})
            loader=dict(retained_marker=dict(config=cfg,kernel_source=source),initramfs_manifest=manifest_pin['path'])
            with mock.patch.object(retention.profile,'marker_codec',return_value=retention.marker):
                return retention.profile.marker_binding(image,manifest,loader)

    def test_v3_keeps_original_requirements_and_v4_accepts_complete_proof(self):
        for version in (3,4,5):self.assertEqual(self.qualify(version)['status'],'PASS_H0_MAINLINE_RETAINED_MARKER')

    def test_v5_rejects_missing_or_changed_bootstrap_context(self):
        changes=[lambda v:v['mmu_on'].pop('bootstrap_context_proved'),
                 lambda v:v['mmu_on']['cases'][0].pop('bootstrap_contexts'),
                 lambda v:v['mmu_on']['cases'][0]['bootstrap_contexts'][0].update(irq_masked=False),
                 lambda v:v['mmu_on']['cases'][1]['bootstrap_contexts'][1].update(irq_masked=True),
                 lambda v:v['mmu_on']['cases'][0]['bootstrap_contexts'][1].update(initial_task=False),
                 lambda v:v['mmu_on']['cases'][0]['bootstrap_contexts'][1].update(preempt_count_low32=0),
                 lambda v:v['mmu_on']['cases'][0]['bootstrap_contexts'][1].update(online_cpus=2),
                 lambda v:v['mmu_on']['cases'][0]['bootstrap_contexts'][1].update(boot_cpu=1)]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):self.qualify(5,change)

    def test_v4_rejects_missing_late_context_cleanup_alias_or_actual_el(self):
        changes=[lambda v:v['mmu_on'].pop('late_fixmap_proved'),
                 lambda v:v['mmu_on']['cases'].clear(),
                 lambda v:v['mmu_on']['cases'][0].update(late_context_stages=[8]),
                 lambda v:v['mmu_on']['cases'][0].update(no_linear_alias_stages=[7]),
                 lambda v:v['mmu_on']['cases'][0].update(mapping_slots_restored=False),
                 lambda v:v['mmu_on']['cases'][1].update(actual_c_el=2),
                 lambda v:v['mmu_on']['cases'][1].update(temporary_mapping_attribute_stages=[8])]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):self.qualify(4,change)

class ClosedBindingTests(unittest.TestCase):
    setUp=health_fixture.TargetTests.setUp
    captures=health_fixture.TargetTests.captures

    def fixture(self,recovered):
        root=self.directory;folder=root/'workspace/private/task';folder.mkdir(parents=True)
        (folder/'journal').mkdir()
        review=publish(folder/'review.json',dict(synthetic_review=True))
        task=dict(schema=retention.profile.TASK_SCHEMA,N={'profile':retention.profile.PROFILE,'retained_marker':{'fixture':True}},
            operations=[retention.profile.OPERATION],target=self.binding,A=self.android,review=review)
        task_pin=publish(folder/'task.json',task);grant=publish(folder/'grant.json',dict(schema=sessions.SCHEMA,task=task_pin))
        op=folder/'operation-0001';op.mkdir()
        request=dict(schema=sessions.SCHEMA,task=task_pin,grant=grant,N=task['N'],A=task['A'],
            operation=retention.profile.OPERATION,reentry=False,hud=False,usb_reconnect=False)
        operation=publish(op/'operation.json',request)
        publish(op/'consumed.json',dict(schema=sessions.SCHEMA,operation_sha256=operation['sha256'],grant=grant))
        returned=retention.target.health_projection(self.captures(),self.binding,self.android)
        previous=self.properties['boot_id'];self.properties['boot_id']='87654321-1234-1234-1234-123456789abc'
        initial=retention.target.health_projection(self.captures(),self.binding,self.android);self.properties['boot_id']=previous
        (op/'io-preflight').mkdir();publish(op/'io-preflight/health.json',initial)
        hp=publish(op/'returned-health.json',returned)
        journal=retention.Journal(op/'journal');a_step='recover-android' if recovered else 'install-android'
        effects=[dict(step='android-download',action='download',role='A'),
                 dict(step='install-native-first',action='transfer',role='N'),dict(step=a_step,action='transfer',role='A')]
        for effect in effects:journal.append('effect-intent',**effect)
        plan=(sessions.Step('install-native-first','transfer','N'),sessions.Step(a_step,'transfer','A'),
              sessions.Step('recovery-health','health','A')) if recovered else sessions.operation_steps(request)
        truth={}
        for step in plan:
            value=dict(action=step.action,step=step.name,health=hp if step.action=='health' else None)
            truth[step.name]=value;result=publish(op/(step.name+'.json'),value)
            journal.append('step-complete',step=step.name,result=result)
        projected=dict(terminal_state='ANDROID_CLOSED_HEALTHY',terminal_step=plan[-1].name,
            terminal_result=pin(op/(plan[-1].name+'.json')),operation_record=operation,operation=retention.profile.OPERATION)
        terminal=publish(op/'terminal.json',dict(projected,schema=sessions.SCHEMA,operation_sha256=operation['sha256'],
            grant=grant,recovered=recovered,research_closed=True))
        identity=dict(schema='FIXTURE',candidate_key='fixture-key',content='fixture-content')
        claim=dict(candidate_key=identity['candidate_key'],record={k:v for k,v in identity.items() if k!='schema'})
        publish(op/'claim-N.json',claim)
        rows=journal.rows();closed=dict(schema='s22plus-comparison-task-closed-v1',task=task_pin,grant=grant,operation=operation,
            current_android_terminal=terminal,terminal_state='ANDROID_CLOSED_HEALTHY',original_N_transfers_total=1,
            original_A_transfers_total=1,source_binding=review,journal_rows=len(rows),journal_tail=pin(journal.directory/f'{len(rows)-1:04d}.json'))
        publish(folder/'closed.json',closed)
        class Adapter:
            def validate_result(self,step,value,request):
                if value!=truth[step.name]:raise ValueError('synthetic underlying proof differs')
            def validate_sequence(self,steps,values,request):
                if [v['step'] for v in values]!=[s.name for s in steps]:raise ValueError('synthetic proof order differs')
            def terminal(self,*_,**__):return projected
        return folder,op,journal,claim,identity,Adapter

    def evaluate(self,fixture):
        folder,op,journal,claim,identity,Adapter=fixture
        with mock.patch.object(retention.profile,'image_binding',return_value={'candidate_id':'12'*32}),\
             mock.patch.object(retention.tasks.tasks,'validate_grant'),\
             mock.patch.object(adapters,'Adapter',return_value=Adapter()),\
             mock.patch.object(adapters,'image_identity',return_value=identity),\
             mock.patch.object(retention.registry,'active_claim',return_value=claim['record']):
            return retention.closed_binding(self.directory,folder)

    def test_normal_closed_owner_joins_real_journal_and_raw_health_without_writes(self):
        fixture=self.fixture(False)
        def state():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.directory.rglob('*') if p.is_file()}
        before=state();bound=self.evaluate(fixture);self.assertEqual(state(),before)
        self.assertEqual(bound['task_receipt'],pin(fixture[0]/'task.json'))

    def test_recovered_closed_owner_joins_a_and_final_health(self):
        self.assertTrue(self.evaluate(self.fixture(True))['returned']['rooted_android_health'])

    def test_mismatched_journal_is_rejected(self):
        fixture=self.fixture(True);fixture[2].append('unexpected-new-row')
        with self.assertRaisesRegex(ValueError,'journal differ'):self.evaluate(fixture)

    def test_missing_task_journal_is_not_created_by_rederivation(self):
        fixture=self.fixture(True);path=fixture[0]/'journal';path.rmdir()
        with self.assertRaisesRegex(ValueError,'task journal missing'):self.evaluate(fixture)
        self.assertFalse(path.exists())

    def test_mismatched_claim_is_rejected(self):
        fixture=self.fixture(False);path=fixture[1]/'claim-N.json'
        value=read(path);value['candidate_key']='other';path.chmod(0o600);path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'claim differs'):self.evaluate(fixture)

    def test_mismatched_terminal_receipt_is_rejected(self):
        fixture=self.fixture(False);path=fixture[1]/'terminal.json';value=read(path)
        value['operation_sha256']='0'*64;path.chmod(0o600);path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):self.evaluate(fixture)

if __name__=='__main__':unittest.main()
