"""Replay proof accounting, protected ordering and consumed owner failures."""
import struct
import unittest
from unittest import mock
import test_s22plus_native_root_inspect_v1 as root
import test_s22plus_native_session_v3 as harness
import s22plus_native_journal_recovery_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as protected
import s22plus_native_session_v3 as owner

BINDING=root.BINDING


def child(out,err=b'',status=0,proved=1):
    rows=[]
    for name,data in (('stdout',out),('stderr',err),('setup',struct.pack('<II',100,0))):
        rows.append(f'UP1_OUTPUT stream={name} bytes={len(data)} hex={data.hex() or "-"}')
    rows.append(f'UP1_CHILD attempted=1 reaped=1 adopted=0 settled=1 status={status} setup_stage=100 setup_errno=0 error=0 proved={proved}')
    return rows


def fixture(*,already_clean=False,negative=False,writer=None,checker=True):
    base=root.fixture(clean=not negative).decode().splitlines()
    base=[s.replace('entries=6 files=3','entries=7 files=4') for s in base]
    rows=base[:3]+[f'RI1_SUPER clean={int(already_clean)} state=1 recover={int(not already_clean)} orphan=0',
        'JR1_BEFORE sha256='+'a'*64]
    if already_clean:rows.append('JR1_SKIP clean=1')
    else:
        rows.append('JR1_BLOCK_RW partition=1')
        writer=writer or (b'S22_JOURNAL_REPLAY_V1 stage=1 writes=0 bytes=0 error=22 io_error=0 complete=0\n' if negative else
            b'S22_JOURNAL_REPLAY_V1 stage=5 writes=3 bytes=9216 error=0 io_error=0 complete=1\n')
        rows+=child(writer,status=2048 if negative else 0,proved=int(not negative))
        rows+=['JR1_BLOCK_RO partition=1 settled=1',
            f'JR1_AFTER clean={int(not negative)} state=1 recover={int(negative)} orphan=0']
    if not negative:
        rows.append('JR1_CHECKER begin=1')
        rows+=child(b''.join(f'Pass {i}: fixed\n'.encode() for i in range(1,6)),
            b'e2fsck 1.47.2 (1-Jan-2025)\n',status=0 if checker else 1024,proved=int(checker))
    if negative:rows+=base[4:]
    elif not checker:
        rows+=base[-2:-1]+[base[-1].replace('mounted=1 unmounted=1','mounted=0 unmounted=0')]
    else:rows+=base[4:-3]+['JR1_ROOT exact=1 extra=0']+base[-3:]
    rows.append(f'JR1_RESULT complete=1 attempted={int(not already_clean)} writer_complete={int(not already_clean and not negative)} checker_complete={int(not negative and checker)} root_match={int(not negative and checker)} stopped={int(negative or not checker)} io_error=0')
    return ('\n'.join(rows)+'\n').encode()


class EvidenceTests(unittest.TestCase):
    def test_replayed_root_and_already_clean_skip_are_distinct(self):
        for clean in (False,True):
            result=profile.decode(fixture(already_clean=clean),b'',BINDING)
            self.assertTrue(result['recovery_proved'])
            self.assertEqual(result['persistent_write_attempted'],not clean)
            self.assertEqual(result['persistent_writes'],not clean)
            self.assertFalse(result['pid1_handoff']);self.assertFalse(result['debian_boot_proved'])

    def test_settled_writer_or_checker_negative_does_not_mount(self):
        for body in (fixture(negative=True),fixture(checker=False)):
            result=profile.decode(body,b'',BINDING)
            self.assertFalse(result['recovery_proved']);self.assertFalse(result['root_inspection']['mounted'])

    def test_impossible_success_or_negative_accounting_rejects(self):
        for writer in (b'S22_JOURNAL_REPLAY_V1 stage=5 writes=0 bytes=0 error=0 io_error=0 complete=1\n',
                       b'S22_JOURNAL_REPLAY_V1 stage=5 writes=3 bytes=12288 error=0 io_error=0 complete=1\n',
                       b'S22_JOURNAL_REPLAY_V1 stage=5 writes=3 bytes=9216 error=0 io_error=5 complete=1\n'):
            with self.subTest(writer=writer),self.assertRaises(ValueError):profile.decode(fixture(writer=writer),b'',BINDING)
        bad=b'S22_JOURNAL_REPLAY_V1 stage=0 writes=0 bytes=0 error=0 io_error=0 complete=0\n'
        with self.assertRaises(ValueError):profile.decode(fixture(negative=True,writer=bad),b'',BINDING)

    def test_missing_settlement_protection_and_order_reject(self):
        good=fixture()
        cases=[good.replace(b'settled=1',b'settled=0',1),good.replace(b'adopted=0',b'adopted=1',1),
            good.replace(b'JR1_BLOCK_RO partition=1 settled=1\n',b''),
            good.replace(b'JR1_BLOCK_RW partition=1',b'JR1_SKIP clean=1'),
            good.replace(b'JR1_CHECKER begin=1\n',b''),good.replace(b'cleanup_errno=0',b'cleanup_errno=5'),
            good.replace(b'JR1_ROOT exact=1 extra=0',b'JR1_ROOT exact=1 extra=1'),
            good+b'unknown\n',good[:-1]]
        for body in cases:
            with self.subTest(body=body),self.assertRaises((ValueError,IndexError,KeyError)):
                profile.decode(body,b'',BINDING)

    def test_zero_outer_exit_does_not_replace_proof(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING):p=profile.Profile(dict(run_id_hex='1'*32))
        raw=fixture();self.assertTrue(p.project(raw,b'',(5,0,0,0,len(raw),0,0),requested=True)['recovery_proved'])
        for terminal in (None,(5,1,0,0,len(raw),0,0),(5,0,0,0,len(raw)-1,0,0)):
            self.assertEqual(p.project(raw,b'',terminal,requested=True)['status'],'NO_PROOF')


class ScopeTests(unittest.TestCase):
    def test_one_attended_fresh_operation_has_no_handoff_or_reentry(self):
        task=root.ScopeTests().task();task['N']['profile']=profile.PROFILE;task['operations']=[profile.OPERATION]
        with mock.patch.object(profile,'image_binding'),mock.patch.object(protected,'android_basis_for_image'):
            protected.validate_task(task)
            for key,value in [('operations',['debian-handoff']),('operations',[profile.OPERATION,'android-exit']),
                ('E',{}),('admission',{}),('prior_terminal',{}),('operation_budget',2),('seconds',1801),
                ('recovery_mode','deferred'),('reentry',True),('hud',True),('usb_reconnect',True)]:
                with self.subTest(key=key),self.assertRaises(ValueError):protected.validate_task(dict(task,**{key:value}))


class Device(harness.DeviceFixture):
    def observe(self,step,request,*,guard,before_terminal,consume_observation=None,before_extra=None):
        if step.name==profile.SELECTION:
            guard();self.assert_mode('N')
            if not callable(before_extra):raise ValueError('writer has no durable intent')
            before_extra(dict(mode='fixed-extra',sequence=5));self.actions.append('writer-once')
            if self.fail_after==step.name:raise OSError('writer response lost after EXEC')
            before_terminal();return self.proof(step)
        return super().observe(step,request,guard=guard,before_terminal=before_terminal,consume_observation=consume_observation)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp
    def test_uncertain_writer_has_one_a_return_and_never_replays(self):
        device=Device();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        session=owner.Session(self.root,directory,device);device.fail_after=profile.SELECTION
        result=session.execute(attended=True)
        self.assertTrue(result['recovered']);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('writer-once'),1);self.assertEqual(device.admitted,0)
        self.assertIsNone(self.f1)
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['N','A'])
