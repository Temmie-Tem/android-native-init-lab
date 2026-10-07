"""USB-only evidence must not acquire the old metadata result's meaning."""
import hashlib
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_early_protocol_v1 as old
import s22plus_debian_usb_protocol_v1 as usb
import s22plus_debian_early_profile_v1 as profile
import s22plus_native_root_inspect_session_v1 as scope
import test_s22plus_native_root_inspect_v1 as inspection_tests


class USBFirstEvidence(unittest.TestCase):
    key=bytes(range(32));candidate=bytes(range(16));nonce=bytes(range(1,33))
    boot=b'12345678-1234-1234-1234-123456789abc'

    def marker(self,seq,event,*,run=None,boot=None):
        run=self.candidate if run is None else run;boot=self.boot if boot is None else boot
        signature=old.tag(self.key,run,hashlib.sha256(boot).digest(),240,seq,event,domain=usb.DOMAIN)
        return b'[    0.123] task: S22USB1 run='+run.hex().encode()+b' boot='+boot+b' seq='+str(seq).encode()+b' mac='+signature.hex().encode()+b' '+event+b'\n'

    def test_old_challenge_domain_rejected(self):
        frame=old.frames.decode_frame(usb.request(self.key,self.candidate,self.nonce))
        with self.assertRaises(ValueError):old.payload(frame,self.key,self.candidate,self.nonce)

    def test_foreign_candidate_is_absent_not_nonexecution(self):
        value=usb.retained(self.marker(1,b'BEGIN',run=b'x'*16),key=self.key,run=self.candidate)
        self.assertEqual(value['records'],[]);self.assertFalse(value['nonexecution_proved'])

    def test_valid_partial_records_keep_partial_meaning(self):
        raw=self.marker(1,b'FYG8_H0 seq=1 BEGIN')+self.marker(200,b'USBSTAGE OBSERVER_BEGIN')
        value=usb.retained(raw,key=self.key,run=self.candidate)
        self.assertEqual(value['status'],'AUTHENTICATED_PARTIAL_RECORDS')
        self.assertEqual([r['sequence'] for r in value['records']],[1,200])
        self.assertNotIn('debian_early_pid1',value)

    def test_altered_marker_rejected(self):
        raw=self.marker(200,b'USBSTAGE OBSERVER_BEGIN').replace(b'OBSERVER_BEGIN',b'OBSERVER_READY')
        with self.assertRaises(ValueError):usb.retained(raw,key=self.key,run=self.candidate)

    def test_duplicate_reversed_and_mixed_boot_rejected(self):
        a=self.marker(1,b'BEGIN');b=self.marker(2,b'TARGET')
        for raw in (a+a,b+a,a+self.marker(2,b'TARGET',boot=b'22345678-1234-1234-1234-123456789abc')):
            with self.subTest(raw=raw),self.assertRaises(ValueError):usb.retained(raw,key=self.key,run=self.candidate)

    def test_usb_log_rejects_storage_stage_and_missing_module(self):
        events=[b'BEGIN run='+self.candidate.hex().encode()+b' boot='+self.boot+b' parent=1',b'TARGET_GUARD_OK',
            b'MODULE_BEGIN ordinal=1 name=sec_log_buf',b'MODULE_DONE ordinal=1 name=sec_log_buf',
            b'MODULE_SET_READY count=1',b'LOGGER_BOUND retention_after_reboot=unproved',
            b'TERMINAL result=PLATFORM_READY error=0']
        def encode(items):return b''.join(b'FYG8_H0 seq='+str(i).encode()+b' '+e+b'\n' for i,e in enumerate(items,1))
        kwargs=(self.candidate,['sec_log_buf'],hashlib.sha256(self.boot).digest())
        result=usb.parse_log(encode(events),*kwargs)
        self.assertFalse(result['storage_accessed']);self.assertEqual(result['metadata_state'],'not_observed')
        self.assertFalse(result['retention_after_reboot'])
        for changed in (events[:-1]+[b'STORAGE_BOUND',events[-1]],events[:3]+events[4:],events[:-1]):
            with self.subTest(changed=changed),self.assertRaises(ValueError):usb.parse_log(encode(changed),*kwargs)

    def test_usb_profile_keeps_one_attended_original_a_scope(self):
        task=inspection_tests.ScopeTests().task()
        task.update(N=dict(profile=profile.USB_PROFILE,run_id_hex='1'*32),seconds=1800,operations=[profile.OPERATION])
        with mock.patch.object(profile,'image_binding'),mock.patch.object(scope,'android_basis_for_image'):
            scope.validate_task(task)
            for key,value in (('seconds',1801),('operation_budget',2),('recovery_mode','deferred'),
                    ('reentry',True),('operations',['debian-early','bootstrap']),('E',{})):
                bad=copy.deepcopy(task);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):scope.validate_task(bad)
        with mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),mock.patch.object(scope,'android_basis_for_image'):
            scope.validate_task(task,recovery=True)

    def test_profile_selects_one_authentication_domain(self):
        self.assertIs(profile.wire_protocol(dict(profile=profile.USB_PROFILE)),usb)
        self.assertIs(profile.wire_protocol(dict(profile=profile.PROFILE)),old)
        with self.assertRaises(ValueError):profile.wire_protocol(dict(profile='unknown'))


if __name__=='__main__':unittest.main()
