"""Preflight record faults and the one-transfer automatic-measurement owner."""
import copy
import ctypes
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_preflight_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as protected
import s22plus_native_session_v3 as owner
import test_s22plus_native_session_v3 as harness

RUN='12'*16
BOOT=b'12345678-1234-4567-89ab-123456789abc\n'


def fixture(*,run=RUN,complete=True,**changes):
    fields=dict(zip(profile.KEYS,(0x31504642,1,212,0,12,0,0,1,81,8,8,6,0,0,0,0,1,1,1,1,1,1,0,2)))
    stop=b''
    if not complete:
        fields.update(stage=6,error=71,complete=0,children_started=1,children_reaped=1,
            children_executed=1,child_status=4<<8,root_mounts=0)
        stop=b'preflight-child-result'
    fields.update(changes)
    return struct.pack('<24I',*(fields[k] for k in profile.KEYS))+bytes.fromhex(run)+BOOT+stop.ljust(63,b'\0')


class RecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temporary.cleanup)
        folder=Path(cls.temporary.name)
        (folder/'reader.c').write_text('#include "preflight_record.h"\n'
            'int check(const void *p,const unsigned char *r) {return bp_valid(p,r,0);}\n')
        subprocess.run(['cc','-shared','-fPIC','-O2','-I',str(ROOT/'workspace/public/src/debian/s22plus_v1/device'),
            str(folder/'reader.c'),'-o',str(folder/'check.so')],check=True,capture_output=True)
        cls.library=ctypes.CDLL(str(folder/'check.so'));cls.library.check.argtypes=(ctypes.c_void_p,ctypes.c_void_p)

    def test_completed_and_located_rejection_are_different_scientific_outcomes(self):
        for complete,outcome in ((True,'PREFLIGHT_COMPLETED'),(False,'BOOTSTRAP_STOPPED')):
            body=fixture(complete=complete)
            self.assertEqual(self.library.check(body,bytes.fromhex(RUN)),1)
            proof=profile.decode(body,b'',RUN)
            self.assertEqual(proof['outcome'],outcome)
            self.assertFalse(proof['debian_boot_proved']);self.assertFalse(proof['pid1_handoff'])

    def test_both_consumers_reject_unsafe_or_unsettled_handover(self):
        changes=({'mounts_released':0},{'descriptors_closed':0},{'children_settled':0},
            {'super_unchanged':0},{'gpt_unchanged':0},{'partition_ro':0},
            {'timed_out':1},{'output_exceeded':1},{'modules_completed':80},
            {'children_reaped':7},{'children_executed':5},{'root_mounts':1},{'virtual_board':1},
            {'complete':2},{'cleanup_error':5},{'child_status':9})
        for mutation in changes:
            body=bytearray(fixture())
            for key,value in mutation.items():struct.pack_into('<I',body,profile.KEYS.index(key)*4,value)
            body=bytes(body)
            with self.subTest(mutation=mutation):
                self.assertEqual(self.library.check(body,bytes.fromhex(RUN)),0)
                with self.assertRaises(ValueError):profile.decode(body,b'',RUN)
        body=fixture(complete=False,super_unchanged=0,gpt_unchanged=0)
        self.assertEqual(self.library.check(body,bytes.fromhex(RUN)),0)
        with self.assertRaises(ValueError):profile.decode(body,b'',RUN)

    def test_framing_run_and_outer_exit_cannot_substitute_for_measurement(self):
        with mock.patch.object(profile,'image_binding',return_value={}):
            selected=profile.Profile(dict(run_id_hex=RUN))
        good=fixture();terminal=(5,0,0,0,len(good),0,0)
        self.assertEqual(selected.project(good,b'',terminal,requested=True)['status'],'PASS_PREFLIGHT_OBSERVED')
        for body,err,end in ((good[:-1],b'',terminal),(good+b'x',b'',terminal),
            (fixture(run='34'*16),b'',terminal),(good,b'error',terminal),
            (good,b'',(5,0,0,0,len(good)-1,0,0)),(good,b'',(5,0,0,0,len(good),1,0)),
            (good,b'',(5,0,9,0,len(good),0,0))):
            self.assertEqual(selected.project(body,err,end,requested=True)['status'],'NO_PROOF')


class Device(harness.DeviceFixture):
    def transfer(self,step,request,**kwargs):
        value=super().transfer(step,request,**kwargs)
        if step.role=='N':self.actions.append('automatic-preflight')
        return value

    def observe(self,step,request,*,before_extra=None,**kwargs):
        if before_extra is not None:raise AssertionError('a result read acquired an effect callback')
        if step.name==profile.SELECTION:
            self.actions.append('record-read')
            if self.fail_after==step.name:raise OSError('record read failed')
        return super().observe(step,request,**kwargs)


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp

    def operation(self):
        device=Device();directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        return owner.Session(self.root,directory,device),device

    def test_one_automatic_measurement_no_read_effect_and_no_admission_or_replay(self):
        session,device=self.operation();value=session.execute(attended=True)
        self.assertEqual(value['state'],'ANDROID_CLOSED');self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('automatic-preflight'),1)
        self.assertEqual(device.actions.count('record-read'),1);self.assertEqual(device.admitted,0)
        self.assertEqual([r['data']['step'] for r in session.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','inspector-return','install-android'])
        with self.assertRaises(ValueError):session.execute(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)

    def test_lost_record_recovers_without_restarting_measurement(self):
        session,device=self.operation();device.fail_after=profile.SELECTION
        self.assertTrue(session.execute(attended=True)['recovered'])
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('automatic-preflight'),1)

    def test_health_only_continuation_never_retransfers_either_image(self):
        session,device=self.operation();original=device.android_health
        def fail_once(*a,**kw):
            device.android_health=original;raise OSError('read failed after A')
        device.android_health=fail_once
        self.assertTrue(session.execute(attended=True)['recovered'])
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('automatic-preflight'),1)


class ScopeTests(unittest.TestCase):
    def test_one_attended_operation_is_not_an_admission_or_reusable_task(self):
        task=dict(N=dict(profile=profile.PROFILE),E=None,operations=[profile.OPERATION],admission=None,
            prior_terminal=None,recovery_mode='attended',operation_budget=1,seconds=1800,
            reentry=False,hud=False,usb_reconnect=False,target={},A={})
        with mock.patch.object(profile,'image_binding'),mock.patch.object(protected,'android_basis_for_image'):
            protected.validate_task(task)
            for key,val in (('operations',['root-inspect']),('operations',['bootstrap']),('E',{}),
                ('admission',{}),('prior_terminal',{}),('seconds',1801),('operation_budget',2),
                ('reentry',True),('hud',True),('usb_reconnect',True),('recovery_mode','deferred')):
                changed=copy.deepcopy(task);changed[key]=val
                with self.subTest(key=key),self.assertRaises(ValueError):protected.validate_task(changed)


if __name__=='__main__':unittest.main()
