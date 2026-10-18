"""Automatic transfer ownership, exact scope and original-return failures."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_s22plus_debian_handoff_v1 as previous
import s22plus_debian_autoboot_access_v1 as automatic_access
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_autoboot_session_v1 as automatic_session


class Device(previous.harness.DeviceFixture):
    def transfer(self,step,request,*,guard,before_launch):
        value=super().transfer(step,request,guard=guard,before_launch=before_launch)
        if step.role=='N':
            self.actions.append('automatic-start');self.mode='Debian'
        return value


class OwnerTests(unittest.TestCase):
    setUp=previous.harness.OwnerTests.setUp

    def operation(self,device=None):
        device=device or Device()
        directory=previous.owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        for module in (automatic_access,previous.access):
            patch=mock.patch.object(module,'Access',previous.FixtureAccess);patch.start();self.addCleanup(patch.stop)
        return previous.owner.Session(self.root,directory,device),device

    def test_start_is_owned_only_by_transfer_then_one_shutdown_and_one_a(self):
        session,device=self.operation()
        self.assertEqual(session.execute(attended=True)['state'],'AWAITING_PHYSICAL_DOWNLOAD')
        self.assertEqual(device.installed,['N']);self.assertEqual(device.actions.count('automatic-start'),1)
        self.assertEqual([r['data']['step'] for r in session.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','debian-shutdown'])
        self.assertFalse(any(step.action in ('observe','integrated-start') for step in automatic_session.normal_steps()))
        device.mode='Download';session.resume(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)
        with self.assertRaises(ValueError):session.execute(attended=True)

    def test_failed_read_or_uncertain_shutdown_keeps_original_recovery_only(self):
        for fault in ('ssh-health','shutdown'):
            with self.subTest(fault=fault):
                self.setUp();device=Device();device.fail_after=fault;session,device=self.operation(device)
                result=session.execute(attended=True)
                self.assertEqual(result['state'],'AWAITING_ATTENDED_RECOVERY');self.assertIsNotNone(self.f1)
                starts=device.actions.count('automatic-start');shutdowns=device.actions.count('shutdown-once')
                session.recover(attended=True)
                self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)
                self.assertEqual(device.actions.count('automatic-start'),starts)
                self.assertEqual(device.actions.count('shutdown-once'),shutdowns)

    def test_uncertain_n_transfer_never_reinstalls_or_starts_a_second_n(self):
        device=Device();device.fail_after='install-native-first';session,device=self.operation(device)
        self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])

    def test_transfer_diagnostics_survive_owner_stop_and_cleanup_failure(self):
        session,device=self.operation()
        failure=previous.records.publish(session.directory/'fixture-failure.json',dict(message='endpoint deadline'))
        error=ValueError('endpoint deadline');error.transfer_failure=failure
        coordinator=automatic_session.Coordinator(session)
        with mock.patch.object(session,'has_recovery_basis',return_value=True),\
                mock.patch.object(coordinator,'cleanup',side_effect=OSError('cleanup cut')):
            with self.assertRaisesRegex(OSError,'cleanup cut'):coordinator.stopped(error)
        stopped=[row['data'] for row in session.rows() if row['event']=='stopped']
        self.assertEqual(len(stopped),1)
        self.assertEqual(stopped[0]['error_message'],'endpoint deadline')
        self.assertEqual(stopped[0]['transfer_failure'],failure)

    def test_completed_a_then_failed_health_continues_health_only(self):
        session,device=self.operation();session.execute(attended=True);device.mode='Download';device.health_failure=True
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        device.health_failure=False;session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('automatic-start'),1)

    def test_attendance_and_uncertain_a_do_not_gain_another_transfer(self):
        session,device=self.operation()
        with self.assertRaises(ValueError):session.execute(attended=False)
        self.assertEqual(device.installed,[])
        session.execute(attended=True);device.mode='Download';device.fail_after='install-android'
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        with self.assertRaises((ValueError,KeyError)):session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])


class ScopeTests(unittest.TestCase):
    def test_late_grant_stops_preflight_before_any_device_read_or_effect(self):
        import s22plus_native_adapter_v3 as adapter
        with tempfile.TemporaryDirectory() as tmp:
            grant=previous.records.publish(Path(tmp)/'grant.json',dict(opened_ns=0,deadline_ns=3600_000_000_000))
            request=dict(N=dict(profile=profile.PROFILE),grant=grant)
            selected=adapter.Adapter.__new__(adapter.Adapter)
            with mock.patch.object(selected,'configuration',return_value={}),\
                    mock.patch.object(adapter,'clock',return_value=3500_000_000_000),\
                    mock.patch.object(adapter,'image_valid',side_effect=AssertionError('past budget reached image validation')):
                with self.assertRaisesRegex(ValueError,'remaining transfer'):
                    selected.preflight(request,guard=lambda:None)
            adapter.before_window_transfer(request['N'],previous.records.read(Path(tmp)/'grant.json'),1)

    def test_only_one_attended_3600_second_android_origin_operation(self):
        task=previous.root.ScopeTests().task();task.update(N=dict(profile=profile.PROFILE,run_id_hex='1'*32),
            seconds=3600,operations=[profile.OPERATION],debian_access=dict.fromkeys(
                ('link','client_key','known_hosts','nmcli','ssh','root_run_id','network_uuid')))
        with mock.patch.object(profile,'image_binding'),mock.patch.object(previous.scope,'android_basis_for_image'),\
                mock.patch.object(previous.access,'inputs',return_value=task['debian_access']):
            previous.scope.validate_task(task)
            for name,value in (('seconds',1800),('seconds',3601),('recovery_mode','deferred'),('operation_budget',2),
                    ('E',{}),('admission',{}),('reentry',True),('operations',['debian-integrated']),('hud',True)):
                changed=copy.deepcopy(task);changed[name]=value
                with self.assertRaises(ValueError):previous.scope.validate_task(changed)
        with mock.patch.object(previous.scope,'android_basis_for_image'),\
                mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),\
                mock.patch.object(previous.access,'inputs',side_effect=FileNotFoundError):
            previous.scope.validate_task(task,recovery=True)


if __name__=='__main__':unittest.main()
