"""LOGM diagnostics remain distinct from current Android health and authority."""
from contextlib import contextmanager
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_loader_android_v1 as harness
import s22plus_loader_android_access_v1 as access
import s22plus_loader_android_profile_v1 as profile
import s22plus_native_records_v3 as records
import device_action_raw_capture_v1 as raw


def report(config,*,status='READBACK_MATCH',idx=400):
    value=bytearray.fromhex(config['report_seed_hex'])
    code=profile.LOGM_STATES[status]
    struct.pack_into('>I',value,12,code)
    struct.pack_into('>II',value,48,4,0)
    before=(7,0x4d474f4c,idx,19)
    if status=='SKIP_MAGIC':before=(7,0,idx,19)
    if code>=3:struct.pack_into('>IIII',value,64,*before)
    if code>=5:
        cursor=idx%profile.LOGM_PAYLOAD
        struct.pack_into('>I',value,56,cursor-256 if cursor>=256 else profile.LOGM_PAYLOAD-256)
        struct.pack_into('>IIII',value,80,*(before if code!=5 else (8,*before[1:])))
    if code>=6:
        struct.pack_into('>I',value,60,1 if code==6 else 0)
        struct.pack_into('>IIII',value,96,*before)
    struct.pack_into('>I',value,112,{1:0,2:0,3:129,4:129,5:143,6:255,7:255}[code])
    return bytes(value)


class CodecTests(unittest.TestCase):
    def setUp(self):self.config=profile.logm_configuration('d'*64,bytes(range(32)))

    def test_snapshot_match_any_offset_is_separate_from_same_attempt_and_health(self):
        frame=bytes.fromhex(self.config['frame_hex'])
        value=profile.logm_projection(report(self.config),b'x'*23+frame+b'end',self.config)
        self.assertEqual(value['matching_frame_offsets'],[23])
        self.assertEqual(value['status'],'READBACK_AND_SNAPSHOT_OBSERVED')
        for key in ('same_attempt_frame_proved','reset_retention_proved','mainline_boot_proved','missing_frame_cause_proved'):
            self.assertFalse(value[key])
        self.assertNotIn('rooted_android_health',value)

    def test_negative_writer_outcomes_remain_diagnostics_even_with_old_candidate_frame(self):
        frame=bytes.fromhex(self.config['frame_hex'])
        for status,idx in [('SKIP_FDT',400),('SKIP_MAGIC',400),('SKIP_INDEX',255),
                          ('HEADER_CHANGED',400),('READBACK_MISMATCH',400)]:
            with self.subTest(status=status):
                value=profile.logm_projection(report(self.config,status=status,idx=idx),frame,self.config)
                self.assertEqual(value['status'],'DIAGNOSTIC_ONLY')
                self.assertEqual(value['matching_frame_offsets'],[0])
                self.assertFalse(value['same_attempt_frame_proved'])

    def test_malformed_or_inconsistent_report_never_supplies_writer_evidence(self):
        original=report(self.config)
        for offset,data in [(0,b'badmagic'),(12,bytes(4)),(16,bytes(32)),(56,bytes(4)),
                            (60,b'\0\0\0\1'),(80,bytes(4)),(112,bytes(4)),(116,b'\1')]:
            with self.subTest(offset=offset):
                bad=bytearray(original);bad[offset:offset+len(data)]=data
                with self.assertRaises(ValueError):profile.logm_report(bytes(bad),self.config)
        for bad in (original[:-1],original+b'x'):
            with self.assertRaises(ValueError):profile.logm_report(bad,self.config)

    def test_torn_and_foreign_frames_do_not_count(self):
        frame=bytes.fromhex(self.config['frame_hex']);foreign=bytearray(frame);foreign[16]^=1
        torn=bytearray(frame);torn[-1]^=1
        value=profile.logm_projection(report(self.config),bytes(foreign)+bytes(torn)+frame[:32],self.config)
        self.assertEqual(value['matching_frame_offsets'],[])
        self.assertEqual(value['foreign_candidates'],1);self.assertEqual(value['damaged_candidates'],2)

    def test_impossible_el_and_unread_sctlr_are_rejected(self):
        value=bytearray.fromhex(self.config['report_seed_hex'])
        struct.pack_into('>I',value,12,profile.LOGM_STATES['SKIP_STATE'])
        for el,state,valid in [(0,0,True),(12,0,True),(16,0,False),(12,0x12345678,False)]:
            struct.pack_into('>II',value,48,el,state)
            if valid:self.assertEqual(profile.logm_report(bytes(value),self.config)['status'],'SKIP_STATE')
            else:
                with self.assertRaises(ValueError):profile.logm_report(bytes(value),self.config)


class CaptureTests(harness.ProofTests):
    # Reuse the actual fixed Android producer harness without inheriting its
    # old-profile tests (which correctly expect no new diagnostic captures).
    def setUp(self):
        super().setUp()
        self.config=profile.logm_configuration('d'*64,bytes(range(32)))
        self.task['N']['logm_control']={'configuration':self.config,'key':{'fixture':True}}
        self.task['adb']={'path':'/fixture/adb','size':1,'sha256':'a'*64}
        self.report=report(self.config);self.snapshot=b'prefix'+bytes.fromhex(self.config['frame_hex'])
        self.reads=[];self.read_error=False;self.read_stderr=b'';self.change_boot=False;self.change_usb=False
        outer=self
        @contextmanager
        def tool(*args,**kwargs):yield SimpleNamespace(path=Path('/fixture/adb'))
        def acquire(argv,directory,name,**kwargs):
            self.assertEqual(argv[:4],['/fixture/adb','-s',self.fixture.binding['serial'],'shell'])
            self.assertEqual(argv[4],'-T');kwargs['before_spawn']();self.reads.append(name)
            self.assertGreater(kwargs['timeout'],0);self.assertLessEqual(kwargs['timeout'],30)
            data=self.report if name=='report' else self.snapshot
            result=raw.publish_captured_bytes(directory,name,stdout=data,stderr=self.read_stderr,
                returncode=1 if self.read_error else 0)
            if name=='last-kmsg':
                if self.change_boot:self.changed['boot_id']='87654321-1234-1234-1234-123456789abc'
                if self.change_usb:self.generation='new-generation'
            return result
        self._stack.enter_context(mock.patch.object(access.transport,'pin_regular_file',side_effect=tool))
        self._stack.enter_context(mock.patch.object(access.raw,'acquire_command',side_effect=acquire))

    def command(self,client,arguments,name,**kwargs):
        if name=='features':
            if kwargs.get('before_launch'):kwargs['before_launch']()
            return raw.publish_captured_bytes(client.directory,name,stdout=b'shell_v2\n',stderr=b'',returncode=0)
        return super().command(client,arguments,name,**kwargs)

    def test_logm_complete_capture_offline_rederives_and_returns_with_negative_diagnosis(self):
        self.report=report(self.config,status='SKIP_INDEX',idx=255);self.snapshot=b''
        value=self.observe()
        self.assertEqual(value['status'],'PASS_LOADER_FYG8_ANDROID')
        self.assertEqual(value['logm_control']['writer']['status'],'SKIP_INDEX')
        self.assertEqual(self.reads,['report','last-kmsg'])
        with mock.patch.object(access.raw,'acquire_command',side_effect=AssertionError('new IO')):
            self.assertEqual(access.rederive(self.adapter,self.request),value)
            returned=access.before_return(self.adapter,self.request,self.adapter.folder(profile.RETURN,create=True),lambda:None)
            access.return_proof(self.adapter,self.request,returned)
        self.assertEqual(self.reads,['report','last-kmsg'])

    def test_logm_read_failure_preserves_raw_before_stopping(self):
        self.read_error=True
        with self.assertRaises(raw.RawCaptureError):self.observe()
        folder=self.adapter.folder(profile.SELECTION)/'logm'
        self.assertEqual(raw.read_stdout(raw.load_handle(folder/'report.capture.json'),maximum=128),self.report)
        self.assertFalse((folder/'complete.json').exists());self.assertEqual(self.reads,['report'])

    def test_logm_report_failure_keeps_complete_raw_and_has_no_success(self):
        self.report=b'bad'
        with self.assertRaises(ValueError):self.observe()
        folder=self.adapter.folder(profile.SELECTION)
        self.assertTrue((folder/'logm/last-kmsg.capture.json').exists())
        self.assertFalse((folder/'result.json').exists())

    def test_logm_changed_boot_or_usb_does_not_reuse_prior_health(self):
        for key in ('change_boot','change_usb'):
            self.setUp();setattr(self,key,True)
            with self.assertRaises(ValueError):self.observe()
            self.assertFalse((self.adapter.folder(profile.SELECTION)/'result.json').exists())

    def test_logm_wrong_raw_result_is_not_accepted(self):
        self.read_stderr=b'producer diagnostic'
        with self.assertRaises(raw.RawCaptureError):self.observe()
        self.assertEqual(self.reads,['report'])


# Inherit fixture methods only, not the original profile's test methods.
for _name in dir(harness.ProofTests):
    if _name.startswith('test_') and _name not in CaptureTests.__dict__:
        setattr(CaptureTests,_name,None)


if __name__=='__main__':unittest.main()
