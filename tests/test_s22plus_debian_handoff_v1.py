"""Fixed B protocol, scope and compound-owner behavioral failure cases."""
import copy
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import test_s22plus_switch_root_v1 as predecessor
import test_s22plus_native_session_v3 as harness
import test_s22plus_native_root_inspect_v1 as root
import s22plus_debian_handoff_protocol_v1 as wire
import s22plus_debian_handoff_profile_v1 as profile
import s22plus_debian_handoff_session_v1 as handoff
import s22plus_debian_access_v1 as access
import s22plus_native_root_inspect_session_v1 as scope
import s22plus_native_records_v3 as records
import s22plus_native_session_v3 as owner

KEY,RUN,NONCE,BOOT=predecessor.KEY,predecessor.RUN,predecessor.NONCE,predecessor.BOOT
WITNESS=predecessor.WITNESS;INIT='66'*32;HOOK='77'*32


def transcript(*,pid=1,boot=BOOT,acm=0,state=0,init=bytes.fromhex(INIT),hook=bytes.fromhex(HOOK)):
    rows=[]
    for stage in range(1,9):
        body=wire.base.LABELS[stage] if stage<8 else struct.pack('<4I',1,8,41,7)+BOOT+bytes.fromhex(WITNESS)+b'm'*32+bytes(8)
        rows.append(wire.encode(KEY,RUN,NONCE,wire.base.RECORD,1023+stage,struct.pack('<2I',stage,0)+body))
    rows+=[wire.encode(KEY,RUN,NONCE,wire.CONTINUE_ACK,6,struct.pack('<I',1)),
        wire.encode(KEY,RUN,NONCE,wire.INIT_PROOF,7,struct.pack('<3I',pid,8,41)+boot+init+hook+struct.pack('<2I',acm,state)),
        wire.encode(KEY,RUN,NONCE,wire.RELEASE_ACK,7,struct.pack('<I',1))]
    return rows


class RecordsTests(unittest.TestCase):
    def reader(self):return wire.Records(KEY,RUN,NONCE,BOOT,WITNESS,INIT,HOOK)
    def accept(self,r,rows):
        for row in rows:r.accept(wire.frames.decode_frame(row))

    def test_installed_init_is_separate_from_writable_witness_release_and_access(self):
        r=self.reader();rows=transcript();self.accept(r,rows[:8])
        self.assertIsNotNone(r.proof);self.assertIsNone(r.init_proof)
        self.assertTrue(r.projection()['persistent_writes']);self.assertFalse(r.proof['partition_readonly'])
        self.accept(r,rows[8:10]);self.assertIsNotNone(r.init_proof);self.assertFalse(r.released)
        self.accept(r,rows[10:]);self.assertTrue(r.released)
        self.assertFalse(r.projection()['ssh_access_proved']);self.assertFalse(r.projection()['clean_shutdown_proved'])

    def test_wrong_pid_boot_init_hook_or_inherited_fd_cannot_prove(self):
        for change in (dict(pid=2),dict(boot=b'x'*32),dict(init=b'x'*32),dict(hook=b'x'*32),dict(acm=1),dict(state=1)):
            with self.subTest(change=change):
                r=self.reader()
                with self.assertRaises(ValueError):self.accept(r,transcript(**change))
                self.assertIsNone(r.init_proof)

    def test_readonly_profile_cannot_be_promoted_to_writable_debian(self):
        r=self.reader()
        with self.assertRaises(ValueError):self.accept(r,predecessor.transcript())
        self.assertIsNone(r.proof)
        old=wire.base.Records(KEY,RUN,NONCE,BOOT,WITNESS)
        with self.assertRaises(ValueError):self.accept(old,transcript())
        self.assertIsNone(old.proof)

    def test_skipped_repeated_and_stale_phases_reject(self):
        good=transcript()
        variants=[good[:8]+good[9:],good[:9]+[good[8]]+good[9:],good[:10]+[good[-1],good[-1]],
            [wire.encode(KEY,RUN,b'x'*32,wire.base.RECORD,1024,struct.pack('<2I',1,0)+wire.base.LABELS[1])]]
        for rows in variants:
            with self.assertRaises(ValueError):self.accept(self.reader(),rows)


class ScopeTests(unittest.TestCase):
    def test_scope_is_exact_one_attended_android_origin_and_recovery_does_not_need_ssh(self):
        task=root.ScopeTests().task();task.update(N=dict(profile=profile.PROFILE,run_id_hex='1'*32),
            seconds=3600,operations=[profile.OPERATION],debian_access=dict.fromkeys(
                ('link','client_key','known_hosts','nmcli','ssh','root_run_id','network_uuid')))
        with mock.patch.object(profile,'image_binding'),mock.patch.object(scope,'android_basis_for_image'),\
                mock.patch.object(access,'inputs',return_value=task['debian_access']):
            scope.validate_task(task)
            for k,v in [('seconds',3601),('operation_budget',2),('recovery_mode','deferred'),('reentry',True),
                    ('operations',['debian-handoff','bootstrap']),('E',{}),('admission',{})]:
                invalid=copy.deepcopy(task);invalid[k]=v
                with self.assertRaises(ValueError):scope.validate_task(invalid)
        with mock.patch.object(scope,'android_basis_for_image'),mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),\
                mock.patch.object(access,'inputs',side_effect=FileNotFoundError):scope.validate_task(task,recovery=True)


class Device(harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        self.assert_mode('N');guard();before_extra(dict(mode='debian-handoff',sequence=5))
        self.actions.append('rw-init-once')
        if self.fail_after=='rw-init':raise OSError('RW/init effect uncertain')
        before_terminal(dict(mode='debian-init-continue'));before_terminal(dict(mode='debian-acm-release'))
        self.actions.append('acm-release-once');self.mode='Debian'
        if self.fail_after=='acm-release':raise OSError('release ACK lost')
        return self.proof(step)


class FixtureAccess:
    def __init__(self,device,request):self.device=device
    def cleanup(self):return dict(status='NOT_CREATED')
    def health(self,step,guard):
        guard();self.device.assert_mode('Debian');self.device.actions.append('ssh-health')
        if self.device.fail_after=='ssh-health':raise OSError('SSH read failed')
        return self.device.proof(step)
    def shutdown(self,step,guard,before):
        guard();self.device.assert_mode('Debian');before(dict(fixed='shutdown'))
        self.device.actions.append('shutdown-once');self.device.mode='Off'
        if self.device.fail_after=='shutdown':raise OSError('shutdown delivered; ACK lost')
        return self.device.proof(step)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp
    def operation(self,device=None):
        device=device or Device();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        patch=mock.patch.object(access,'Access',FixtureAccess);patch.start();self.addCleanup(patch.stop)
        return owner.Session(self.root,directory,device),device

    def test_normal_path_pauses_for_physical_return_then_one_a(self):
        session,device=self.operation();pending=session.execute(attended=True)
        self.assertEqual(pending['state'],'AWAITING_PHYSICAL_DOWNLOAD');self.assertEqual(device.installed,['N'])
        self.assertEqual(device.actions.count('rw-init-once'),1);self.assertEqual(device.actions.count('shutdown-once'),1)
        device.mode='Download';result=session.resume(attended=True)
        self.assertFalse(result['recovered']);self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)
        self.assertEqual([r['data']['step'] for r in session.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','debian-handoff','debian-shutdown','install-android'])
        with self.assertRaises(ValueError):session.execute(attended=True)

    def test_uncertainty_stops_for_original_recovery_without_native_or_ssh_replay(self):
        for fault in ('rw-init','acm-release','ssh-health','shutdown'):
            with self.subTest(fault=fault):
                self.setUp();device=Device();device.fail_after=fault;session,device=self.operation(device)
                self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
                before=list(device.actions);result=session.recover(attended=True)
                self.assertTrue(result['recovered']);self.assertEqual(device.installed,['N','A'])
                self.assertEqual(device.actions.count('rw-init-once'),before.count('rw-init-once'))
                self.assertEqual(device.actions.count('shutdown-once'),before.count('shutdown-once'))

    def test_completed_a_then_failed_health_never_retransfers(self):
        class Interrupted(Device):
            calls=0
            def android_health(self,step,request,*,guard):
                self.calls+=1
                if self.calls==1:raise OSError('health read unavailable')
                return super().android_health(step,request,guard=guard)
        session,device=self.operation(Interrupted());session.execute(attended=True);device.mode='Download'
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        self.assertEqual(device.installed,['N','A']);session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.calls,2)

    def test_unattended_and_uncertain_a_do_not_gain_a_second_transfer(self):
        session,device=self.operation()
        with self.assertRaises(ValueError):session.execute(attended=False)
        session.execute(attended=True);device.mode='Download';device.fail_after='install-android'
        self.assertEqual(session.resume(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        with self.assertRaises((ValueError,KeyError)):session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])

    def test_malformed_host_cleanup_does_not_mask_successful_android_recovery(self):
        session,device=self.operation();device.fail_after='rw-init'
        self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        with mock.patch.object(FixtureAccess,'cleanup',side_effect=KeyError('malformed host-only receipt')):
            result=session.recover(attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED');self.assertEqual(device.installed,['N','A'])
        self.assertIsNone(self.f1)


if __name__=='__main__':unittest.main()
