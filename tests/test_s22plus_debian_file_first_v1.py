"""Checked historical boundaries, distinct formats and the fixed owner route."""
import hashlib
import struct
import unittest
from unittest import mock
from test_s22plus_debian_file_v1 import FileRecords,FileRetrieval
import s22plus_debian_file_first_protocol_v1 as protocol
import s22plus_debian_file_first_profile_v1 as profile
import s22plus_debian_file_protocol_v1 as old
import s22plus_debian_early_profile_v1 as early
import s22plus_native_root_inspect_session_v1 as owner
import s22plus_native_adapter_v3 as adapter


class Fixture:
    key=FileRecords.key;candidate=FileRecords.candidate;expected=FileRecords.expected;boot=FileRecords.boot
    names=['sec_log_buf',*(f'base_{i}' for i in range(66)),'qcom_spmi_pmic',
        *(f'ufs_{i}' for i in range(8)),*protocol.CLIENTS]

    def make(self,*,error_phase=None,skip_phase=None):
        boot=hashlib.sha256(self.boot).digest()
        events=[b'BEGIN run='+self.candidate.hex().encode()+b' boot='+self.boot+b' parent=1',b'TARGET_GUARD_OK']
        for i,name in enumerate(self.names[:76],1):
            events.append(f'MODULE_BEGIN ordinal={i} name={name}'.encode())
            if name=='sec_log_buf':events.append(b'LOGGER_BIND phase=0 error=0')
            events.append(f'MODULE_DONE ordinal={i} name={name}'.encode())
            if name=='qcom_spmi_pmic':events += [b'PROVIDERS_BEGIN',b'PROVIDERS_READY mask=7']
        events.append(b'TERMINAL result=STORAGE_READY error=0')
        log=b''.join(f'FYG8_H0 seq={i} '.encode()+e+b'\n' for i,e in enumerate(events,1))
        proof=struct.pack('<4I',1,42,0,len(log))+boot+bytes.fromhex(self.expected['shell_sha256'])+\
            bytes.fromhex(self.expected['init_sha256'])+hashlib.sha256(log).digest()+bytes.fromhex(self.expected['helper_sha256'])
        header=b'S22FL02\0'+struct.pack('<II',2,256)+self.candidate+proof+struct.pack('<Q',100)+bytes(8)
        tag=old.common.tag(self.key,self.candidate,boot,0,0,header,domain=protocol.DOMAIN)
        raw=header+tag+log;start=len(raw)
        steps=[(1,0),*((k,p) for p in range(1,7) if p!=skip_phase for k in (2,3)),(4,0)]
        for seq,(kind,phase) in enumerate(steps):
            error=5 if kind==3 and phase==error_phase else 0
            body=b'S22FLR2\0'+struct.pack('<IIQII',seq,kind,seq,phase,error)+bytes(32)+tag
            tag=old.common.tag(self.key,self.candidate,boot,kind,seq,body,domain=protocol.DOMAIN)
            raw+=body+tag
            if error:break
        return raw,start

    def decode(self,data,**kwargs):
        return protocol.decode(data,key=self.key,run=self.candidate,expected=self.expected,module_names=self.names,**kwargs)


class FirstRecords(unittest.TestCase):
    def test_complete_scope_remains_pre_unmount_and_no_usb(self):
        f=Fixture();raw,_=f.make();p=f.decode(raw)
        self.assertEqual((p['preparation_module_completions'],p['client_return_records'],len(p['records'])),(76,6,14))
        self.assertTrue(p['pre_unmount_complete'])
        for key in ('live_usb_proved','unmount_return_proved','clean_filesystem_proved','replay_authorized'):
            self.assertFalse(p[key])

    def test_format_and_domain_cannot_cross_promote_old_pilot(self):
        f=Fixture();raw,_=f.make()
        with self.assertRaises(ValueError):old.decode(raw,key=f.key,run=f.candidate,expected=f.expected,module_names=f.names)
        with self.assertRaises(ValueError):f.decode(FileRecords().fixture()[0])

    def test_client_failure_is_authenticated_and_stops_success(self):
        f=Fixture();raw,_=f.make(error_phase=3)
        with self.assertRaises(ValueError):f.decode(raw)
        p=f.decode(raw,allow_prefix=True)
        self.assertEqual(p['client_error'],dict(name='i2c_msm_geni',error=5))
        self.assertEqual(p['client_return_records'],2)
        self.assertFalse(p['pre_unmount_complete'])

    def test_ready_begin_and_torn_prefixes_never_prove_call_return(self):
        f=Fixture();raw,start=f.make()
        for size,attempted in ((start+128,0),(start+256,1),(start+300,1)):
            p=f.decode(raw[:size],allow_prefix=True)
            self.assertEqual(p['client_attempt_records'],attempted)
            self.assertEqual(p['client_return_records'],0)
            self.assertFalse(p['pre_unmount_complete'])

    def test_validly_authenticated_skipped_phase_rejected(self):
        f=Fixture()
        with self.assertRaises(ValueError):f.decode(f.make(skip_phase=2)[0])

    def test_storage_profile_uses_only_existing_fixed_window(self):
        self.assertIs(early.window_profile(dict(profile=profile.PROFILE)),profile)
        with self.assertRaises(ValueError):early.wire_protocol(dict(profile=profile.PROFILE))
        task=dict(N=dict(profile=profile.PROFILE),operations=['debian-early'],E=None,admission=None,
            prior_terminal=None,recovery_mode='attended',operation_budget=1,seconds=1800,
            reentry=False,hud=False,usb_reconnect=False,target={},A={})
        with mock.patch.object(adapter,'image_valid'),mock.patch.object(owner,'android_basis_for_image'):
            owner.validate_task(task)
            task['seconds']=1799
            with self.assertRaises(ValueError):owner.validate_task(task)

    def test_later_collector_selects_exact_new_decoder(self):
        f=Fixture();result=FileRetrieval.project(self,f.make()[0],fixture=f,storage_first=True)
        self.assertEqual(result['status'],'PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT')
        self.assertEqual(result['proof']['client_return_records'],6)
