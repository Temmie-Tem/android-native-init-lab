import base64
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_stage_protocol_v1 as protocol
import s22plus_debian_stage_profile_v1 as profile
import s22plus_debian_early_profile_v1 as early
import s22plus_debian_file_window_v1 as window
import s22plus_native_records_v3 as records
import s22plus_native_root_inspect_session_v1 as scope
import s22plus_debian_usb_retention_v1 as retention
import s22plus_debian_file_retrieval_v1 as retrieval


class StageRecords(unittest.TestCase):
    def setUp(self):
        self.key=bytes(range(32));self.run=bytes(range(16));self.boot=bytes(range(16,32))
        self.expected=dict(shell_sha256='11'*32,init_sha256='22'*32,helper_sha256='33'*32)
        self.logger='44'*32

    def frame(self,event,*,sequence=None,value=None,detail=None,boot=None,run=None):
        if detail is None:detail=bytes.fromhex({2:'11'*32,3:'22'*32,4:'33'*32,5:self.logger}.get(event,'00'*32))
        return protocol.encode(key=self.key,run=run or self.run,boot=boot or self.boot,
            sequence=sequence or event,event=event,value=(73 if event==1 else 0) if value is None else value,detail=detail)

    def decode(self,raw):
        return protocol.retained(raw,key=self.key,run=self.run,expected=self.expected,logger_sha256=self.logger)

    def complete(self):return b'\n'.join(self.frame(i) for i in range(1,9))

    def test_complete_is_only_the_emitted_milestone(self):
        result=self.decode(self.complete())
        self.assertEqual(result['status'],'PASS_RETAINED_EARLY_STAGE')
        self.assertTrue(result['debian_early_pid1']);self.assertTrue(result['logger_bound'])
        for field in ('final_ring_readback_proved','helper_return_proved','park_proved','installed_debian_pid1',
                'live_usb_proved','absence_proves_nonexecution','stopped_at_last_stage','replay_authorized'):
            self.assertFalse(result[field])
        self.assertEqual(len(self.frame(1)),153)

    def test_damaged_frame_cannot_mask_later_contiguous_frame(self):
        raw=self.frame(1)[:30]+b'old interleaved text '+self.frame(2)+b'\r\n'+self.frame(3)
        result=self.decode(raw)
        self.assertEqual(result['status'],'PARTIAL_RETAINED_STAGE')
        self.assertEqual([r['event'] for r in result['records']],[2,3])
        self.assertEqual(result['records'][0]['offset'],raw.index(self.frame(2)))
        self.assertEqual(len(result['damaged_candidates']),1)
        self.assertFalse(result['debian_early_pid1'])

    def test_valid_frames_plus_bad_authentication_remain_partial(self):
        data=bytearray(base64.b64decode(self.frame(1)[8:-1]));data[-1]^=1
        bad=protocol.PREFIX+base64.b64encode(data)+b']'
        result=self.decode(bad+self.complete())
        self.assertEqual(result['status'],'PARTIAL_RETAINED_STAGE')
        self.assertEqual(result['damaged_candidates'][0]['reason'],'BAD_AUTHENTICATION')

    def test_gap_retains_only_surviving_stages(self):
        result=self.decode(b''.join(self.frame(i) for i in (1,2,3,4,6,7,8)))
        self.assertEqual(result['status'],'PARTIAL_RETAINED_STAGE')
        self.assertFalse(result['complete']);self.assertFalse(result['logger_bound'])

    def test_wrong_parent_measurement_is_not_pid1_proof(self):
        raw=b''.join(self.frame(i,detail=b'X'*32) if i==2 else self.frame(i) for i in range(1,9))
        result=self.decode(raw);self.assertFalse(result['debian_early_pid1']);self.assertFalse(result['complete'])
        self.assertEqual(result['damaged_candidates'][0]['reason'],'MEASUREMENT_MISMATCH')

    def test_module_return_error_is_rejection(self):
        result=self.decode(b''.join(self.frame(i) for i in range(1,6))+self.frame(6,value=5))
        self.assertEqual(result['status'],'RETAINED_STAGE_REJECTED');self.assertFalse(result['logger_bound'])

    def test_explicit_rejection_is_never_complete(self):
        result=self.decode(self.frame(1)+self.frame(9,sequence=2,value=71))
        self.assertEqual(result['status'],'RETAINED_STAGE_REJECTED');self.assertFalse(result['debian_early_pid1'])

    def test_foreign_run_does_not_supply_a_missing_record(self):
        result=self.decode(self.frame(1,run=b'F'*16)+self.frame(2))
        self.assertEqual(result['foreign_frames'],1);self.assertFalse(result['debian_early_pid1'])

    def test_duplicates_reversed_and_mixed_boots_reject(self):
        for raw in (self.frame(1)*2,self.frame(2)+self.frame(1),self.frame(1)+self.frame(2,boot=b'B'*16)):
            with self.subTest(raw=raw[:8]),self.assertRaises(ValueError):self.decode(raw)

    def test_absence_and_truncation_do_not_prove_nonexecution(self):
        for raw in (b'kernel text',self.frame(1)[:-1]):
            result=self.decode(raw);self.assertEqual(result['status'],'NO_AUTHENTICATED_STAGE')
            self.assertFalse(result['absence_proves_nonexecution'])

    def test_bounds_are_finite(self):
        for raw in (b'x'*(protocol.MAXIMUM+1),protocol.PREFIX*513):
            with self.assertRaises(ValueError):self.decode(raw)


class StageOwner(unittest.TestCase):
    def test_remaining_budget_and_exact_scope(self):
        grant=dict(opened_ns=1,deadline_ns=1800*10**9)
        profile.before_transfer(grant,2)
        for now in (0,870*10**9,1799*10**9):
            with self.assertRaises(ValueError):profile.before_transfer(grant,now)
        self.assertEqual(early.window_profile(dict(profile=profile.PROFILE)),profile)
        with self.assertRaises(ValueError):early.window_profile(dict(profile=early.USB_PROFILE))

    def test_original_transfer_window_has_no_live_proof_or_journal_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary).resolve()
            grant=records.publish(directory/'grant.json',dict(host_boot='fixed-host-boot',opened_ns=10**9,deadline_ns=1800*10**9))
            request=dict(N=dict(profile=profile.PROFILE),grant=grant);records.publish(directory/'operation.json',request)
            transfer=dict(action='transfer',fixed_fixture=True);receipt=records.publish(directory/'install-native-first.json',transfer)
            with mock.patch.object(records,'clock',side_effect=[100*10**9,101*10**9]):
                journal=records.Journal(directory/'journal')
                journal.append('effect-intent',step='install-native-first',action='transfer',role='N')
                journal.append('step-complete',step='install-native-first',result=receipt)
            class Adapter:
                def folder(self,name):return self.directory/('io-'+name)
                def recover_transfer_result(self,step,operation):return transfer
            adapter=Adapter();adapter.directory=directory
            before={p.name:p.read_bytes() for p in (directory/'journal').iterdir() if p.is_file()}
            with mock.patch.object(profile,'image_binding'),mock.patch.object(window,'clock',side_effect=[101*10**9,101*10**9,191*10**9,191*10**9]),mock.patch.object(window.time,'sleep'):
                value=window.observe(adapter,request,guard=lambda:None)
                with self.assertRaises(FileExistsError):window.observe(adapter,request,guard=lambda:None)
            self.assertEqual(value,window.rederive(adapter,request))
            self.assertEqual(value['proof']['status'],profile.PENDING)
            self.assertFalse(value['proof']['debian_early_pid1']);self.assertEqual(value['proof']['device_activity'],'UNKNOWN')
            self.assertEqual({p.name:p.read_bytes() for p in (directory/'journal').iterdir() if p.is_file()},before)
            self.assertEqual(records.read(adapter.folder('debian-early-evidence')/'open.json')['basis']['window_end_ns'],191*10**9)

    def test_policy_name_and_status_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);policy=root/profile.POLICY;policy.parent.mkdir(parents=True);policy.write_text('Status: **REVIEW_GATED_CAPABILITY**')
            target=root/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md';target.parent.mkdir();target.write_text(Path(profile.POLICY).name)
            profile.validate_adoption(root,Path(profile.POLICY).name.encode())
            with self.assertRaises(ValueError):profile.validate_adoption(root,b'unrelated-policy')
            policy.write_text('DRAFT')
            with self.assertRaises(ValueError):profile.validate_adoption(root,Path(profile.POLICY).name.encode())


class StageProjection(unittest.TestCase):
    def project(self,*,changed_boot=False,duplicate=False):
        fixture=StageRecords();fixture.setUp();fixture.logger=early.LOGGER['sha256']
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();taskdir=root/'task';taskdir.mkdir();directory=root/'capture';directory.mkdir()
            operation=taskdir/'operation-0001';operation.mkdir()
            key=records.publish(root/'unused.json',dict(fixture=True))
            (root/'key').write_bytes(fixture.key);key=records.pin(root/'key')
            task=dict(N=dict(profile=profile.PROFILE,key=key,run_id_hex=fixture.run.hex()),target={},A={})
            task_receipt=records.publish(taskdir/'task.json',task)
            operation_receipt=records.publish(operation/'operation.json',dict(fixture=True))
            returned=records.publish(root/'returned.json',dict(boot_id_sha256='a'*64))
            final=records.publish(root/'final.json',dict(health=returned))
            terminal=records.publish(operation/'terminal.json',dict(operation_record=operation_receipt,terminal_result=final))
            closed=records.publish(taskdir/'closed.json',dict(current_android_terminal=terminal))
            records.publish(directory/'started.json',dict(schema='s22plus-stage-retention-d0-v1',task=task_receipt,closed=closed,device_effects=0))
            healths={}
            for side in ('before','after'):
                (directory/side).mkdir()
                boot='b'*64 if side=='after' and changed_boot else 'a'*64
                healths[side]=dict(properties=dict(boot=boot),boot_id_sha256=boot,captures=[side])
                records.publish(directory/side/'health.json',healths[side])
            (directory/'transport').mkdir()
            retention.raw.publish_captured_bytes(directory/'transport','features',stdout=b'shell_v2\n')
            raw=fixture.complete()+(fixture.frame(8) if duplicate else b'')
            handle=retention.raw.publish_captured_bytes(directory,'last-kmsg',stdout=raw)
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            def denied(*args,**kwargs):raise AssertionError('offline projection attempted device/process acquisition')
            with mock.patch.object(retention,'private_path',side_effect=lambda base,p,**kw:Path(p)),\
                    mock.patch.object(retrieval,'closed_operation',return_value=dict(task=task,closed=closed)),\
                    mock.patch.object(early,'image_binding',return_value=dict(expected=fixture.expected)),\
                    mock.patch.object(retention.target,'health_projection',side_effect=lambda captures,*args:healths[captures[0]]),\
                    mock.patch.object(retention.raw,'acquire_command',side_effect=denied),\
                    mock.patch.object(subprocess,'run',side_effect=denied),mock.patch.object(subprocess,'Popen',side_effect=denied):
                if changed_boot or duplicate:
                    with self.assertRaisesRegex(ValueError,'same original-A returned boot' if changed_boot else 'duplicate'):
                        retention.stage_projection(directory,taskdir)
                    result=None
                else:result=retention.stage_projection(directory,taskdir)
            self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
            self.assertEqual(retention.raw.read_stdout(handle,maximum=4*1024**2),raw)
            return result

    def test_same_returned_boot_projects_saved_raw_only(self):
        result=self.project();self.assertEqual(result['status'],'PASS_RETAINED_EARLY_STAGE')
        self.assertTrue(result['same_returned_android_boot']);self.assertEqual(result['device_effects'],0)

    def test_changed_boot_is_rejected(self):self.project(changed_boot=True)

    def test_parser_rejection_preserves_raw_and_prior_records(self):self.project(duplicate=True)


if __name__=='__main__':unittest.main()
