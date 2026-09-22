"""Stage-2 result accounting, restricted scope and one-shot owner behavior."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_root_inspect_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as inspection
import s22plus_native_session_v3 as owner
import s22plus_native_records_v3 as records
import device_action_raw_capture_v1 as raw
import test_s22plus_native_session_v3 as owner_harness

BINDING = dict(table_count=3, boot_count=2, max_hashed_bytes=512*1024*1024)


def fixture(*, clean=True, start=1, complete=1, changed=False):
    rows = ['RI1_BEGIN version=1', 'RI1_BIND exact=1', 'RI1_BLOCK_RO partition=1',
        f'RI1_SUPER clean={int(clean)} state=1 recover={int(not clean)} orphan=0']
    if clean:
        rows += ['RI1_MOUNT readonly=1 noload=1 nodev=1 noexec=1 nosuid=1',
            f'RI1_MARKERS start={start} complete={complete} witness=1',
            'RI1_TREE entries=6 files=3 dirs=2 links=1 other=0 bytes=600 sha256='+'a'*64]
        if changed: rows += ['RI1_FINDING path_sha256='+'b'*64+' kind=content']
        rows += [f'RI1_COMPARE expected=3 matched={2 if changed else 3} missing=0 metadata=0 content={int(changed)} '
            f'boot_expected=2 boot_missing=0 boot_metadata=0 boot_content={int(changed)} hashed_bytes=600 findings={int(changed)}',
            'RI1_UNMOUNT complete=1']
    rows += ['RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1',
        f'RI1_RESULT complete=1 stage=10 errno=0 cleanup_errno=0 partition_ro=1 clean={int(clean)} mounted={int(clean)} unmounted={int(clean)}']
    return ('\n'.join(rows)+'\n').encode()


class ResultTests(unittest.TestCase):
    def test_complete_comparison_proves_neither_chroot_nor_debian_boot(self):
        value=profile.decode(fixture(),b'',BINDING)
        self.assertEqual(value['root_state'],'COMPLETE_RECORD_BOOT_INPUTS_MATCH')
        self.assertTrue(value['partition_ro']); self.assertTrue(value['mounted']); self.assertTrue(value['unmounted'])
        self.assertFalse(value['persistent_writes']); self.assertFalse(value['chroot_proved']); self.assertFalse(value['debian_boot_proved'])

    def test_partial_missing_and_changed_records_remain_distinct_observations(self):
        for options, expected in [({'start':1,'complete':0},'INCOMPLETE_INSTALLATION_RECORD'),
                ({'start':0,'complete':0},'NO_INSTALLATION_RECORDS'),
                ({'start':0,'complete':1},'MARKER_OR_WITNESS_MISMATCH'),
                ({'changed':True},'COMPLETE_RECORD_FILES_DIFFER')]:
            with self.subTest(options=options):
                value=profile.decode(fixture(**options),b'',BINDING)
                self.assertEqual(value['status'],'PASS_INSPECTION_COMPLETED')
                self.assertEqual(value['root_state'],expected)

    def test_unclean_state_does_not_claim_a_mount(self):
        value=profile.decode(fixture(clean=False),b'',BINDING)
        self.assertEqual(value['root_state'],'MOUNT_SKIPPED_UNCLEAN')
        self.assertFalse(value['mounted']); self.assertIsNone(value['comparison'])

    def test_rejects_missing_protection_cleanup_corrupt_counts_and_trailing_data(self):
        good=fixture()
        bad=[good.replace(b'partition=1',b'partition=0'),good.replace(b'noload=1',b'noload=0'),
            good.replace(b'RI1_UNMOUNT complete=1\n',b''), good.replace(b'matched=3',b'matched=2'),
            good.replace(b'partition_ro=1',b'partition_ro=0'), good.replace(b'cleanup_errno=0',b'cleanup_errno=5'),
            good+b'extra\n',good[:-1],good.replace(b'clean=1 state=1 recover=0',b'clean=1 state=1 recover=1')]
        for body in bad:
            with self.subTest(body=body):
                with self.assertRaises((ValueError,IndexError)): profile.decode(body,b'',BINDING)
        with self.assertRaises(ValueError): profile.decode(good,b'error\n',BINDING)

    def test_zero_exit_without_complete_semantic_result_is_not_pass(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING):
            selected=profile.Profile(dict(run_id_hex='1'*32))
        self.assertTrue(selected.MUTATES)
        body=fixture(); terminal=(5,0,0,0,len(body),0,0)
        self.assertEqual(selected.project(body,b'',terminal,requested=True)['status'],'PASS_INSPECTION_COMPLETED')
        for text, end in [(body[:-1],(5,0,0,0,len(body)-1,0,0)),(body,(5,1,0,0,len(body),0,0)),
                (body,(5,0,0,0,len(body),1,0)),(body,(5,0,0,0,len(body)-1,0,0))]:
            self.assertEqual(selected.project(text,b'',end,requested=True)['status'],'NO_PROOF')
        self.assertEqual(selected.project(b'',b'',None,requested=False)['status'],'NO_PROOF')


class ScopeTests(unittest.TestCase):
    def task(self):
        return dict(N=dict(profile=profile.PROFILE),E=None,operations=[profile.OPERATION],admission=None,
            prior_terminal=None,recovery_mode='attended',operation_budget=1,seconds=1800,
            reentry=False,hud=False,usb_reconnect=False,target={},A={})

    def test_single_operation_profile_cannot_gain_admission_or_broader_scope(self):
        with mock.patch.object(profile,'image_binding'),mock.patch.object(inspection,'android_basis_for_image'):
            inspection.validate_task(self.task())
            for field,value in [('operations',['bootstrap']),('operations',['root-inspect','android-exit']),
                    ('admission',{}),('prior_terminal',{}),('E',{}),('reentry',True),('hud',True),
                    ('usb_reconnect',True),('operation_budget',2),('seconds',1801),('recovery_mode','deferred'),
                    ('bootstrap_start',{})]:
                selected=self.task(); selected[field]=value
                with self.subTest(field=field,value=value):
                    with self.assertRaises(ValueError): inspection.validate_task(selected)

    def test_original_recovery_does_not_need_inspector_payload(self):
        with mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),mock.patch.object(inspection,'android_basis_for_image'):
            with self.assertRaises(FileNotFoundError): inspection.validate_task(self.task())
            inspection.validate_task(self.task(),recovery=True)


class InspectionDevice(owner_harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        if step.name=='root-inspection':
            guard(); self.assert_mode('N'); self.actions.append('health:'+step.name)
            if self.health_failure: raise ValueError('native health unavailable')
            if self.fail_before==step.name: raise ValueError('before RO dispatch')
            if not callable(before_extra): raise ValueError('missing durable pre-EXEC callback')
            before_extra(dict(mode='fixed-extra',sequence=5))
            self.actions.append('partition-ro')
            if self.fail_after==step.name: raise OSError('RO control occurred; observation lost')
            before_terminal(); return self.proof(step)
        return super().observe(step,request,guard=guard,before_terminal=before_terminal,
            consume_observation=consume_observation)


class InspectionOwnerTests(unittest.TestCase):
    setUp = owner_harness.OwnerTests.setUp

    def operation(self,kind=profile.OPERATION,**options):
        self.assertEqual(kind,profile.OPERATION)
        device=InspectionDevice()
        directory=owner.prepare_operation(self.root,self.grant,operation=kind,adapter=device,**options)
        return owner.Session(self.root,directory,device),device

    def test_stage2_transfers_once_each_and_never_admits_native(self):
        session,device=self.operation(profile.OPERATION)
        result=session.execute(attended=True)
        self.assertEqual(device.installed,['N','A']); self.assertEqual(device.admitted,0)
        self.assertEqual(device.actions.count('partition-ro'),1); self.assertIsNone(self.f1)
        self.assertEqual([r['data']['step'] for r in session.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','root-inspection','inspector-return','install-android'])
        self.assertEqual(result['state'],'ANDROID_CLOSED')
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['N','A'])

    def test_lost_ro_result_recovers_a_and_never_reexecutes_inspection(self):
        session,device=self.operation(profile.OPERATION);device.fail_after='root-inspection'
        result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('partition-ro'),1);self.assertEqual(device.admitted,0)

    def test_post_a_health_continuation_does_not_reflash(self):
        session,device=self.operation(profile.OPERATION)
        original=device.android_health
        def fail_once(*args,**kwargs):
            device.android_health=original
            raise ValueError('first final health failed')
        device.android_health=fail_once
        result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('partition-ro'),1)

    def test_corrupt_inspection_raw_cannot_block_proved_a_recovery_close(self):
        session,device=self.operation(profile.OPERATION);device.fail_after='root-inspection'
        broken=session.directory/'broken.capture.json';broken.write_text('{invalid')
        original_recover=device.recover_step_result
        def recover(step,request):
            if step.name=='root-inspection':return raw.load_handle(broken)
            return original_recover(step,request)
        original_terminal=device.terminal
        def terminal(selected,values,request,*,recovered):
            value=original_terminal(selected,values,request,recovered=recovered)
            value['root_inspection']=inspection.terminal(device,request,recovered=recovered)
            return value
        device.recover_step_result=recover;device.terminal=terminal
        result=session.execute(attended=True)
        self.assertEqual(result['root_inspection']['status'],'NO_PROOF')
        self.assertEqual(result['root_inspection']['evidence_error']['type'],'RawCaptureError')
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)
        self.assertEqual(device.actions.count('partition-ro'),1)


if __name__=='__main__':unittest.main()
