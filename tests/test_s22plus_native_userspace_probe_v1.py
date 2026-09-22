"""Userspace proof needs real child semantics and the original one-shot owner."""
import struct
import unittest
from unittest import mock
from types import SimpleNamespace

import test_s22plus_native_root_inspect_v1 as root
import test_s22plus_native_session_v3 as harness
import s22plus_native_userspace_probe_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as protected
import s22plus_native_session_v3 as owner
import s22plus_native_adapter_v3 as adapter
import s22plus_native_records_v3 as records
import test_s22plus_native_adapter_v3 as adapter_harness

BINDING = root.BINDING


def fixture(*, output=profile.EXPECTED_STDOUT, stderr=b'', setup=struct.pack('<II',100,0),
            status=0, adopted=0, eligible=True, clean=True, complete=1):
    base = root.fixture(clean=clean, complete=complete).replace(b'entries=6 files=3', b'entries=7 files=4')
    proved = eligible and clean and not adopted and not status and setup == struct.pack('<II',100,0) and output == profile.EXPECTED_STDOUT and not stderr
    extra = []
    if clean:
        extra = [f'UP1_ELIGIBLE exact={int(eligible)}']
        if eligible:
            for name, data in (('stdout',output),('stderr',stderr),('setup',setup)):
                extra.append(f'UP1_OUTPUT stream={name} bytes={len(data)} hex={data.hex() or "-"}')
            stage, error = struct.unpack('<II',setup[-8:]) if len(setup) in (8,16) else (0,0)
            extra += [f'UP1_CHILD attempted=1 reaped=1 adopted={adopted} settled=1 status={status} '
                f'setup_stage={stage} setup_errno={error} error=0 proved={int(proved)}',
                'UP1_PARENT readonly=1 noexec=1 partition_ro=1']
        base = base.replace(b'RI1_UNMOUNT', ('\n'.join(extra)+'\n').encode()+b'RI1_UNMOUNT',1)
    return base + f'UP1_RESULT complete=1 attempted={int(eligible and clean)} proved={int(proved)} error=0\n'.encode()


class EvidenceTests(unittest.TestCase):
    def test_exact_shell_libc_wait_and_exit_evidence_is_userspace_only(self):
        result = profile.decode(fixture(),b'',BINDING)
        self.assertEqual(result['verdict'],'PROVED_FIXED_DEBIAN_USERSPACE')
        self.assertTrue(result['userspace_proved']); self.assertTrue(result['chroot_proved'])
        self.assertFalse(result['debian_boot_proved']); self.assertFalse(result['persistent_writes'])

    def test_zero_exit_wrong_output_and_setup_failures_are_completed_negatives(self):
        cases = [dict(output=b''),dict(output=b'wrong\n'),dict(stderr=b'error\n'),dict(status=23<<8),
            dict(setup=struct.pack('<II',7,1),status=126<<8,output=b''),
            dict(setup=struct.pack('<IIII',100,0,101,2),status=126<<8,output=b''),dict(adopted=1)]
        for case in cases:
            with self.subTest(case=case):
                value=profile.decode(fixture(**case),b'',BINDING)
                self.assertEqual(value['status'],'PASS_PROBE_COMPLETED')
                self.assertEqual(value['verdict'],'WORKLOAD_NOT_PROVED')
                self.assertFalse(value['userspace_proved'])

    def test_ineligible_and_unclean_roots_never_execute(self):
        value=profile.decode(fixture(eligible=False,complete=0),b'',BINDING)
        self.assertEqual(value['verdict'],'SKIPPED_ROOT_NOT_EXACT')
        value=profile.decode(fixture(clean=False),b'',BINDING)
        self.assertEqual(value['verdict'],'SKIPPED_UNCLEAN_ROOT')
        with self.assertRaises(ValueError): profile.decode(fixture(complete=0),b'',BINDING)

    def test_false_claims_truncation_unsettled_children_and_missing_mount_guards_reject(self):
        good=fixture()
        cases=[good.replace(b'settled=1',b'settled=0'),good.replace(b'reaped=1',b'reaped=0'),
            good.replace(b'UP1_PARENT readonly=1 noexec=1',b'UP1_PARENT readonly=1 noexec=0'),
            good.replace(b'RI1_UNMOUNT complete=1\n',b''),good[:-1],good+b'extra\n',
            good.replace(b'UP1_RESULT complete=1',b'UP1_RESULT complete=0'),
            fixture(output=b'wrong\n').replace(b'proved=0',b'proved=1'),fixture(setup=b'partial'),
            fixture(setup=b'',output=b''),
            good.replace(f'stream=stdout bytes={len(profile.EXPECTED_STDOUT)}'.encode(),b'stream=stdout bytes=0',1)]
        # Every malformed fixture must actually differ; avoid an accidental no-op mutation.
        self.assertTrue(all(body!=good for body in cases))
        for body in cases:
            with self.subTest(body=body):
                with self.assertRaises((ValueError,IndexError)): profile.decode(body,b'',BINDING)

    def test_outer_success_cannot_replace_inner_execution_or_output_accounting(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING):
            selected=profile.Profile(dict(run_id_hex='2'*32))
        good=fixture(); terminal=(5,0,0,0,len(good),0,0)
        self.assertTrue(selected.project(good,b'',terminal,requested=True)['userspace_proved'])
        negative=fixture(output=b'')
        self.assertFalse(selected.project(negative,b'',(5,0,0,0,len(negative),0,0),requested=True)['userspace_proved'])
        for body,end in [(good,(5,1,0,0,len(good),0,0)),(good,(5,0,0,0,len(good)-1,0,0)),
                (good,(5,0,0,0,len(good),1,0)),(good[:-1],(5,0,0,0,len(good)-1,0,0))]:
            self.assertEqual(selected.project(body,b'',end,requested=True)['status'],'NO_PROOF')


class ScopeTests(root.ScopeTests):
    def task(self):
        value=super().task(); value['N']['profile']=profile.PROFILE; value['operations']=[profile.OPERATION]
        return value

    def test_single_operation_profile_cannot_gain_admission_or_broader_scope(self):
        with mock.patch.object(profile,'image_binding'),mock.patch.object(protected,'android_basis_for_image'):
            protected.validate_task(self.task())
            for field,value in [('operations',['root-inspect']),('operations',['bootstrap']),('E',{}),
                    ('admission',{}),('prior_terminal',{}),('seconds',1801),('operation_budget',2),
                    ('reentry',True),('hud',True),('usb_reconnect',True),('recovery_mode','deferred')]:
                task=self.task();task[field]=value
                with self.subTest(field=field,value=value):
                    with self.assertRaises(ValueError):protected.validate_task(task)

    def test_original_recovery_does_not_need_inspector_payload(self):
        with mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),mock.patch.object(protected,'android_basis_for_image'):
            with self.assertRaises(FileNotFoundError):protected.validate_task(self.task())
            protected.validate_task(self.task(),recovery=True)


class ProbeDevice(harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        if step.name==profile.SELECTION:
            guard();self.assert_mode('N');self.actions.append('health:'+step.name)
            if not callable(before_extra):raise ValueError('no pre-EXEC owner')
            before_extra(dict(mode='fixed-extra',sequence=5));self.actions.append('userspace-once')
            if self.fail_after==step.name:raise OSError('probe result uncertain after EXEC')
            before_terminal();return self.proof(step)
        return super().observe(step,request,guard=guard,before_terminal=before_terminal,consume_observation=consume_observation)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp

    def operation(self):
        device=ProbeDevice();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        return owner.Session(self.root,directory,device),device

    def test_one_n_one_probe_one_a_and_no_admission_or_replay(self):
        session,device=self.operation();value=session.execute(attended=True)
        self.assertEqual(value['state'],'ANDROID_CLOSED');self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('userspace-once'),1);self.assertEqual(device.admitted,0)
        self.assertEqual([r['data']['step'] for r in session.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','userspace-probe','inspector-return','install-android'])
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)

    def test_uncertain_probe_only_recovers_original_a(self):
        session,device=self.operation();device.fail_after=profile.SELECTION
        value=session.execute(attended=True)
        self.assertTrue(value['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('userspace-once'),1);self.assertIsNone(self.f1)

    def test_health_only_recovery_never_resends_a_or_probe(self):
        session,device=self.operation();original=device.android_health
        def fail_once(*args,**kwargs):
            device.android_health=original;raise ValueError('root read failed after A')
        device.android_health=fail_once;value=session.execute(attended=True)
        self.assertTrue(value['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('userspace-once'),1);self.assertIsNone(self.f1)


class AdapterRoutingTests(unittest.TestCase):
    setUp=adapter_harness.AdapterTests.setUp

    def test_android_origin_prepares_without_admission_and_checks_fresh_n_and_android(self):
        directory=self.private/'task';directory.mkdir()
        native=dict(self.image,profile=profile.PROFILE,namespace='p999',run_id_hex='3'*32)
        value=dict(operations=[profile.OPERATION],N=native,A=self.image,admission=None,prior_terminal=None,
            reentry=False,hud=False,usb_reconnect=False,lane={})
        grant=dict(task=records.publish(directory/'task.json',value),directory=str(directory))
        with mock.patch.object(self.client,'admission',side_effect=AssertionError('no native admission')), \
                mock.patch.object(self.client,'tail',side_effect=AssertionError('no prior native tail')):
            prepared=self.client.prepare(profile.OPERATION,grant)
        self.assertIsNone(prepared['admission']);self.assertIsNone(prepared['prior_terminal'])
        request=dict(prepared,operation=profile.OPERATION,reentry=False,hud=False)
        records.publish(self.directory/'operation.json',request)
        adapter.registry.initialize(self.root)
        health=mock.Mock(side_effect=lambda:records.publish(self.client.folder('preflight')/'health.json',dict(fixture='fresh Android health')))
        holders=mock.Mock()
        with mock.patch.object(self.client,'configuration',return_value=value), \
                mock.patch.object(adapter,'image_valid'),mock.patch.object(adapter.target.lane,'revalidate_binding'), \
                mock.patch.object(adapter.registry,'preflight_candidate',wraps=adapter.registry.preflight_candidate) as claim_check, \
                mock.patch.object(self.client,'native_host',return_value=SimpleNamespace(holders=holders)), \
                mock.patch.object(self.client,'android',return_value=SimpleNamespace(health=health)), \
                mock.patch.object(self.client,'admission',side_effect=AssertionError('no admitted N origin')):
            self.client.preflight(request,guard=lambda:None)
        health.assert_called_once_with();holders.assert_called_once_with(expected_run=None)
        claim_check.assert_called_once();self.assertEqual(claim_check.call_args.args[1]['candidate_ap_sha256'],native['ap']['sha256'])

    def test_original_android_basis_failure_stops_before_any_transfer_preparation(self):
        request=dict(self.request,operation=profile.OPERATION)
        with mock.patch.object(protected,'android_basis',side_effect=ValueError('wrong Android32 basis')), \
                self.assertRaisesRegex(ValueError,'wrong Android32 basis'):
            self.client.transfer(owner.Step('recover-android','transfer','A'),request,guard=lambda:None,before_launch=lambda value:None)
        self.assertFalse(self.client.folder('recover-android').exists())


if __name__=='__main__':unittest.main()
