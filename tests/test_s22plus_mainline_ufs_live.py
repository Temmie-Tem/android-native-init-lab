"""Actual ML030 host consumer over one socket with a modeled device and clock."""
import contextlib
import copy
import hashlib
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import test_s22plus_mainline_download_ram as prior
import s22plus_mainline_ufs_access_v1 as link
from mainline.s22plus_ufs_link_h0 import link_wire as wire

raw=prior.raw
records=prior.records
profile=prior.profile
access=prior.access
download=prior.download
attach=prior.attach
codec=prior.codec


class Ml030WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.DownloadWireTests.setUpClass()
        cls.helper=prior.DownloadWireTests(methodName='runTest')

    @classmethod
    def tearDownClass(cls):
        prior.DownloadWireTests.tearDownClass()

    def run_case(self,case,version=1):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        directory=Path(temp.name);folder=directory/('io-'+profile.SELECTION)
        fixture=self.helper.fixture;manifest=self.helper.manifest()
        manifest=copy.deepcopy(manifest);manifest['debian_ram']['schema']=profile.codec.LINK_SCHEMA
        manifest.update(network={'host_ip':'127.0.0.1','device_ip':'127.0.0.1'},port=1)
        response=self.helper.raw();t0=struct.unpack_from('<Q',response,216)[0];boot=response[72:88]
        current=[records.clock()]
        start=current[0]
        def clock():
            current[0]+=10000
            return current[0]
        def sleep(seconds):current[0]+=round(seconds*1e9)
        records.publish(directory/'operation.json',{'fixture':'ML030'})
        grant=records.publish(directory/'grant.json',{'deadline_ns':start+1800*10**9,'host_boot':records.host_boot()})
        window=dict(operation=records.pin(directory/'operation.json'),candidate_launch={'fixture':'original N'},
                    host_boot=records.host_boot(),opened_ns=start,deadline_ns=start+120*10**9)
        request={'operation':'mainline-ram','N':{'ufs_link':True,'debian_ram':{},'download_return':{}},'grant':grant}
        class Adapter:
            def folder(self,name,create=False):
                if create:folder.mkdir()
                return folder
            def configuration(self,req):return {'mainline_access':{}}
        adapter=Adapter();adapter.directory=directory
        found={'interface':'lo'}
        def endpoint_capture(dest,name):
            if (case=='expired-at-permit' and name=='usb-before-permit' or
                    case in ('expired-at-return','pre-effect-expired-at-return') and name=='usb-before-control'):
                current[0]=start+540*10**9
            return raw.publish_captured_bytes(dest,name,stdout=b'fixture USB',stderr=b'')
        def configure(plan,m,endpoint,dest,guard,deadline_ns):
            guard();records.publish(dest/'endpoint.json',endpoint)
            for name in ('network-create','network-up'):raw.publish_captured_bytes(dest,name,stdout=b'fixture',stderr=b'')
            return endpoint
        journal=records.Journal(directory/'journal')
        journal.append('effect-intent',step='install-native-first',action='transfer',role='N',ending=None,recovery=False,detail={})
        session=prior.owner.Session.__new__(prior.owner.Session)
        session.directory=directory;session.journal=journal;session.root=directory;session.request=request
        session.grant={'opened_ns':start,'schema':records.SCHEMA,'deadline_ns':start+1800*10**9,'host_boot':records.host_boot(),'recovery_mode':'attended'}
        session.check=lambda **kw: self.assertLess(clock(),start+1800*10**9)
        session.consume=lambda: None
        session.unused=lambda: None
        consumed=[]
        def before_permit(detail):
            if case=='before-permit':raise ValueError('H0 failed current scope')
            prior.owner.Session.intent(session,prior.owner.Step(profile.SELECTION,download.ACTION,'N'),detail=detail)
            consumed.append('permit')
            if case=='intent-only':raise ValueError('H0 stop after durable intent')
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(3)
        real_socket=socket.socket;address=listener.getsockname();observed=[];errors=[]
        def exact(c,size):
            data=b''
            while len(data)<size:
                chunk=c.recv(size-len(data))
                if not chunk:return data
                data+=chunk
            return data
        def device():
            try:
                with listener.accept()[0] as c:
                    c.settimeout(3);q=exact(c,72);observed.append('W0');self.assertEqual(q[8:40],fixture.nonce)
                    c.sendall(response)
                    q=exact(c,168)
                    if not q:return
                    n1=wire.HEADER.unpack_from(q)[3];t1=t0+301000
                    self.assertGreaterEqual(clock()-start,300*10**9)
                    c.sendall(wire.frame(b'G030WIT1',17,fixture.key,fixture.identity,fixture.nonce,n1,boot,t0,t1))
                    go=exact(c,168)
                    if not go:return
                    observed.append('GO');self.assertEqual(go,wire.frame(b'G030GO01',18,fixture.key,fixture.identity,fixture.nonce,n1,boot,t0,t1))
                    body=b'G030RES1'+go[8:wire.HEADER.size]
                    numbers=b'0 6 1073741824 1 6 1 8 1024 0 9 1 3 7 7 7 0 0 1 1\n'
                    if version>=2:numbers=numbers[:-1]+b' 132352 0\n'
                    if version==3:numbers=numbers[:-1]+b' 0 2047\n'
                    if version==4:numbers=numbers[:-1]+b' 1073741824 2047\n'
                    if case=='usb-rejection':numbers=b'-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 65554 1\n'
                    if case=='stage2-rejection':
                        from test_s22plus_stage2_diagnostics import compile_stage_fixture
                        exe=compile_stage_fixture(directory/'stage2-producer')
                        numbers=subprocess.check_output([exe,'0','1','-16','1','0'],stderr=subprocess.DEVNULL,timeout=5)
                    if case.startswith('pre-effect-'):
                        from test_s22plus_pre_effect_return import compile_pre_effect, module_report
                        exe=compile_pre_effect(directory/'pre-effect-producer')
                        numbers=module_report(exe,'stage2' if case=='pre-effect-stage2' else 'refuse')
                        guest=compile_pre_effect(directory/'pre-effect-guest',guest=True)
                        gate=int(subprocess.check_output([guest],input=numbers,timeout=5))
                        self.assertEqual(gate==0,case!='pre-effect-stage2')
                    body+=struct.pack('<III',0,0,len(numbers))+numbers.ljust(256,b'\0')
                    result=body+wire.tag(fixture.key,fixture.identity,20,body)
                    if case=='partial-result':c.sendall(result[:90]);return
                    c.sendall(result)
                    control=exact(c,88)
                    if not control:return
                    observed.append('Download')
                    nonce=hashlib.sha256(result).digest()
                    self.assertEqual(control,codec.control(fixture.key,fixture.identity,nonce,str(__import__('uuid').UUID(bytes=boot))))
                    head=codec.ACK_MAGIC+fixture.identity+nonce+boot
                    ack=head+codec.tag(fixture.key,fixture.identity,3,head)
                    if case in ('bad-ack','pre-effect-bad-ack'):ack=ack[:-1]+bytes([ack[-1]^1])
                    c.sendall(ack);c.shutdown(socket.SHUT_WR);c.recv(1)
            except (BrokenPipeError,ConnectionResetError):pass
            except Exception as error:errors.append(error)
            finally:listener.close()
        thread=threading.Thread(target=device);thread.start()
        class Connected:
            def __init__(self,*args,**kwargs):self.sock=real_socket(*args,**kwargs)
            def __enter__(self):return self
            def __exit__(self,*args):self.sock.close()
            def connect(self,target):self.sock.connect(address)
            def __getattr__(self,name):return getattr(self.sock,name)
        with contextlib.ExitStack() as stack:
            for obj,name,value in ((profile,'image_binding',lambda *a,**k:manifest),(access,'window_for',lambda *a:window),
                (access,'capture_endpoint',endpoint_capture),(access,'endpoint',lambda *a:found),
                (access,'configure',configure),(access,'require_host',lambda h:raw.require_success(h)),
                (download.socket,'socket',Connected),(download.secrets,'token_bytes',mock.Mock(side_effect=[fixture.nonce,b'z'*32])),
                (link,'report_version_for',lambda image:version),
                (link.time,'sleep',sleep)):
                stack.enter_context(mock.patch.object(obj,name,value))
            for module in (link,download,attach,records,prior.owner):stack.enter_context(mock.patch.object(module,'clock',clock))
            error=None
            try:value=link.observe(adapter,request,session.check,before_permit)
            except (ValueError,OSError,raw.RawCaptureError) as e:error=e
            thread.join(4);self.assertFalse(thread.is_alive());self.assertFalse(errors)
            if case in ('success','pre-effect-success'):
                self.assertIsNone(error)
                self.assertEqual(value,download.rederive(adapter,request))
                records.publish(directory/(profile.SELECTION+'.json'),value)
                ready=download.return_request(adapter,request,create=True)
                self.assertEqual(ready['requested_ns'],records.read(folder/'control-intent.json')['requested_ns'])
                with mock.patch.object(link,'host_boot',return_value='later-host'):
                    self.assertEqual(link.rederive_link(adapter,request)['result']['status'],
                                     'NO_PROOF' if case=='pre-effect-success' else 'UFS_LINK_COMPLETED')
            else:self.assertIsNotNone(error)
            independent=prior.session.link_fact(adapter,request,{'status':'NO_PROOF'})
            self.assertTrue(independent['five_minute_same_boot'])
            if case in ('before-permit','intent-only','expired-at-permit','partial-result'):
                self.assertNotIn('ufs_link_completed',independent)
            if case in ('success','bad-ack','expired-at-return'):
                self.assertEqual(link.rederive_link(adapter,request)['result']['status'],'UFS_LINK_COMPLETED')
                facts=prior.session.link_fact(adapter,request,{'status':'NO_PROOF','automatic_download_return_proved':False})
                self.assertTrue(facts['ufs_link_completed'])
            if case in ('bad-ack','pre-effect-bad-ack'):
                with self.assertRaises(ValueError):download.rederive(adapter,request)
            if case=='usb-rejection':
                fact=link.rederive_link(adapter,request)['result']
                self.assertEqual(fact['usb_reason'],'BCM_UNKNOWN')
                self.assertEqual(fact['usb_detail'],1)
                self.assertFalse(fact['normal_return'])
                self.assertFalse((folder/'control-intent.json').exists())
            if case=='stage2-rejection':
                fact=link.rederive_link(adapter,request)['result']
                self.assertEqual(fact['stage2_failure'],{'component':'HCI','operation':'QUIESCENT'})
                self.assertEqual(fact['stage2_conditions']['HCE'],'FAIL')
                self.assertEqual(fact['stage2_conditions']['HCS'],'UNOBSERVED')
                self.assertFalse(fact['normal_return'])
                self.assertFalse((folder/'control-intent.json').exists())
            if case.startswith('pre-effect-'):
                fact=link.rederive_link(adapter,request)['result']
                self.assertEqual(fact['normal_return'],case!='pre-effect-stage2')
                self.assertEqual(fact['status'],'NO_PROOF')
                final=prior.session.link_fact(adapter,request,{'status':'PASS_MAINLINE_DOWNLOAD_RAM'})
                self.assertFalse(final['ufs_link_completed'])
                if case!='pre-effect-stage2':
                    self.assertEqual(final['status'],'NO_PROOF')
                    self.assertTrue(final['ufs_pre_effect_rejection'])
                else:self.assertFalse((folder/'control-intent.json').exists())
            if case=='partial-result':
                handle=raw.load_handle(folder/'link.capture.json')
                self.assertEqual(len(raw.read_stdout(handle,maximum=436)),90)
                with self.assertRaises((ValueError,OSError)):link.rederive_link(adapter,request)
            intents=[r for r in journal.rows() if r['event']=='effect-intent' and r['data']['step']==profile.SELECTION]
            self.assertEqual(len(intents),int(case!='before-permit'))
            if intents:
                with self.assertRaises(ValueError):prior.owner.Session.intent(session,prior.owner.Step(profile.SELECTION,download.ACTION,'N'),detail={})
            with self.assertRaises(FileExistsError):link.observe(adapter,request,session.check,before_permit)
        self.assertEqual(observed.count('GO'),int(case not in ('before-permit','intent-only','expired-at-permit')))
        self.assertEqual(observed.count('Download'),int(case in ('success','bad-ack','pre-effect-success','pre-effect-bad-ack')))

    def test_expiry_at_actual_permit_capture(self):self.run_case('expired-at-permit')
    def test_expiry_after_durable_return_intent(self):self.run_case('expired-at-return')

    def test_full_success_and_rederived_late_return(self):self.run_case('success')
    def test_diagnostic_success_and_rederived_late_return(self):self.run_case('success',version=2)
    def test_stage2_schema_success_keeps_original_return_conditions(self):self.run_case('success',version=3)
    def test_actual_stage2_report_preserves_raw_and_stops_return(self):self.run_case('stage2-rejection',version=3)
    def test_pre_effect_actual_guest_host_return(self):self.run_case('pre-effect-success',version=4)
    def test_pre_effect_failed_ack_does_not_prove_return(self):self.run_case('pre-effect-bad-ack',version=4)
    def test_pre_effect_does_not_extend_return_deadline(self):self.run_case('pre-effect-expired-at-return',version=4)
    def test_pre_effect_stage2_remains_excluded(self):self.run_case('pre-effect-stage2',version=4)
    def test_diagnostic_rejection_preserves_raw_and_stops_return(self):self.run_case('usb-rejection',version=2)
    def test_scope_failure_before_permit(self):self.run_case('before-permit')
    def test_durable_permit_without_send_never_replays(self):self.run_case('intent-only')
    def test_partial_result_is_sealed_and_stops_return(self):self.run_case('partial-result')
    def test_complete_link_survives_failed_return(self):self.run_case('bad-ack')


if __name__=='__main__':unittest.main()
