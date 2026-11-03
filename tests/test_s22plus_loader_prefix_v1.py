"""Current prefix facts remain distinct from static readback and full boot."""
from contextlib import contextmanager
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_loader_android_v1 as harness
import s22plus_loader_android_access_v1 as access
import s22plus_loader_android_profile_v1 as profile
import s22plus_loader_prefix_v1 as prefix
import device_action_raw_capture_v1 as raw

ENTRY=0x80ba01000


def report(config,*,state='RETURNED',idx=400,mismatch=0):
    value=bytearray.fromhex(config['report_seed_hex'])
    struct.pack_into('>I',value,12,prefix.STATES[state])
    struct.pack_into('>QQ',value,48,4,1 if state=='SKIP_STATE' else 0)
    if state=='RETURNED':
        struct.pack_into('>QQQQ',value,64,ENTRY,4,0,prefix.COOKIE)
        header=(7,0x4d474f4c,idx,19)
        for i in range(2):
            struct.pack_into('>IIIIIIII',value,96+48*i,*header,*header)
            if idx>=256:
                c=idx%prefix.PAYLOAD;slot=(c-256 if c>=256 else prefix.PAYLOAD-256)+128*i
                struct.pack_into('>IIII',value,128+48*i,slot,mismatch,1,0)
    return bytes(value)


class CodecTests(unittest.TestCase):
    def setUp(self):self.config=prefix.configuration('d'*64,bytes(range(32)))

    def test_prefix_return_has_no_current_store_full_boot_or_retention_claim(self):
        for idx in (0,255,256,257,prefix.PAYLOAD,0xffffffff):
            for mismatch in (0,128):
                value=prefix.report(report(self.config,idx=idx,mismatch=mismatch),self.config,ENTRY)
                self.assertTrue(value['mainline_prefix_return_proved'])
                for key in ('current_attempt_store_proved','mainline_boot_proved','reset_retention_proved',
                            'historical_failure_cause_proved'):self.assertFalse(value[key])

    def test_skips_are_explicit_without_prefix_evidence(self):
        for state in ('SKIP_STATE','SKIP_FDT'):
            value=prefix.report(report(self.config,state=state),self.config,ENTRY)
            self.assertEqual(value['status'],state);self.assertFalse(value['mainline_prefix_return_proved'])
            self.assertEqual(value['observations'],[])

    def test_malformed_unfinalized_bad_return_or_unobserved_fields_fail(self):
        good=report(self.config)
        for offset,data in ((0,b'badmagic'),(12,bytes(4)),(16,bytes(32)),(64,bytes(8)),
            (72,bytes(8)),(80,b'\0'*7+b'\1'),(88,bytes(8)),(128,bytes(4)),
            (136,bytes(4)),(140,b'\0\0\0\1'),(192,b'\1')):
            value=bytearray(good);value[offset:offset+len(data)]=data
            with self.subTest(offset=offset),self.assertRaises(ValueError):prefix.report(bytes(value),self.config,ENTRY)
        for value in (good[:-1],good+b'x',bytes.fromhex(self.config['report_seed_hex'])):
            with self.assertRaises(ValueError):prefix.report(value,self.config,ENTRY)


class CaptureTests(harness.ProofTests):
    def setUp(self):
        super().setUp();self.config=prefix.configuration('d'*64,bytes(range(32)))
        self.task['N']['prefix_control']={'configuration':self.config,'entry_offset':ENTRY-0x80ba00000}
        self.task['adb']={'path':'/fixture/adb','size':1,'sha256':'a'*64}
        self.report=report(self.config);self.reads=[];self.read_error=False;self.change_boot=False;self.change_usb=False
        @contextmanager
        def tool(*args,**kwargs):yield SimpleNamespace(path=Path('/fixture/adb'))
        def acquire(argv,directory,name,**kwargs):
            self.assertEqual(name,'report');self.assertEqual(kwargs['stdout_maximum'],256)
            self.assertIn('codex,uniloader-prefix-v1',argv[-1]);self.assertEqual(argv[4],'-T')
            kwargs['before_spawn']();self.reads.append(name)
            result=raw.publish_captured_bytes(directory,name,stdout=self.report,stderr=b'',returncode=int(self.read_error))
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

    def test_single_report_rederives_without_new_io_and_allows_diagnostic_skip_return(self):
        self.report=report(self.config,state='SKIP_FDT');value=self.observe()
        self.assertEqual(value['prefix_control']['status'],'SKIP_FDT');self.assertEqual(self.reads,['report'])
        with mock.patch.object(access.raw,'acquire_command',side_effect=AssertionError('new IO')):
            self.assertEqual(access.rederive(self.adapter,self.request),value)
            returned=access.before_return(self.adapter,self.request,self.adapter.folder(profile.RETURN,create=True),lambda:None)
            access.return_proof(self.adapter,self.request,returned)

    def test_raw_failure_is_preserved_before_parse_or_stop(self):
        self.read_error=True
        with self.assertRaises(raw.RawCaptureError):self.observe()
        folder=self.adapter.folder(profile.SELECTION)/'prefix'
        self.assertEqual(raw.read_stdout(raw.load_handle(folder/'report.capture.json'),maximum=256),self.report)
        self.assertFalse((folder/'complete.json').exists())

    def test_truncated_report_cannot_create_success(self):
        self.report=self.report[:-1]
        with self.assertRaises(ValueError):self.observe()
        folder=self.adapter.folder(profile.SELECTION)
        self.assertTrue((folder/'prefix/report.capture.json').exists());self.assertFalse((folder/'result.json').exists())

    def test_changed_boot_or_usb_blocks_prefix_attribution(self):
        for field in ('change_boot','change_usb'):
            self.setUp();setattr(self,field,True)
            with self.assertRaises(ValueError):self.observe()


for _name in dir(harness.ProofTests):
    if _name.startswith('test_') and _name not in CaptureTests.__dict__:setattr(CaptureTests,_name,None)

if __name__=='__main__':unittest.main()
