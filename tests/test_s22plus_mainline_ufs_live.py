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
        completed_failure=version in (6,7,8,9,10,11) and (case.startswith(('handoff-','ack-','cfg1-')) or case in ('load-error','read-error'))
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
                    if version in (6,7,8,9,10,11):
                        if case=='missing-arm':return
                        armed=wire.recovery_packet(fixture.key,fixture.identity,fixture.nonce,fixture.nonce,boot)
                        if case=='wrong-arm':armed=armed[:-1]+bytes([armed[-1]^1])
                        c.sendall(armed)
                    q=exact(c,168)
                    if not q:return
                    n1=wire.HEADER.unpack_from(q)[3];t1=t0+301000
                    self.assertGreaterEqual(clock()-start,300*10**9)
                    if version in (6,7,8,9,10,11):
                        live=wire.recovery_packet(fixture.key,fixture.identity,fixture.nonce,n1,boot,late=True)
                        if case=='wrong-live':live=live[:-1]+bytes([live[-1]^1])
                        c.sendall(live)
                    c.sendall(wire.frame(b'G030WIT1',17,fixture.key,fixture.identity,fixture.nonce,n1,boot,t0,t1))
                    go=exact(c,168)
                    if not go:return
                    observed.append('GO');self.assertEqual(go,wire.frame(b'G030GO01',18,fixture.key,fixture.identity,fixture.nonce,n1,boot,t0,t1))
                    body=b'G030RES1'+go[8:wire.HEADER.size]
                    numbers=b'0 6 1073741824 1 6 1 8 1024 0 9 1 3 7 7 7 0 0 1 1\n'
                    if version>=2:numbers=numbers[:-1]+b' 132352 0\n'
                    if version==3:numbers=numbers[:-1]+b' 0 2047\n'
                    if version==4:numbers=numbers[:-1]+b' 1073741824 2047\n'
                    if version==5:numbers=numbers[:-1]+b' 1342177280 2047 1 0 0 0 0 0 0\n'
                    if version in (6,7,8,9,10,11):numbers=numbers[:-1]+f' {version << 28} {2047 | ((8 << 22) if version in (8,9,10,11) else 0) | (0xf0000000 if version in (9,10,11) else 0)} 2113535 1 271 1024 0 0 0\n'.encode()
                    if version in (10,11):numbers=numbers[:-1]+b' 3 0 1\n'
                    if case=='usb-rejection':numbers=b'-16 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 65554 1\n'
                    if case=='stage2-rejection':
                        from test_s22plus_stage2_diagnostics import compile_stage_fixture
                        exe=compile_stage_fixture(directory/'stage2-producer',snapshot=version==5)
                        numbers=subprocess.check_output([exe,'0','1','-16','1','0'],stderr=subprocess.DEVNULL,timeout=5)
                    if case.startswith('handoff-'):
                        from test_s22plus_stage2_diagnostics import compile_stage_fixture
                        exe=compile_stage_fixture(directory/'handoff-producer',handoff=True,reset_config=version in (7,8,9,10,11),disabled_ucrdy=version in (8,9,10,11),stale_uccs_ack=version in (9,10,11),cfg1_diagnostics=version in (10,11),cfg1_ordered_selection=version==11)
                        guard=3 if case=='handoff-ucrdy-next' else 2 if case=='handoff-post-rejection' else 0
                        scenario={'handoff-refusal':2,'handoff-post-rejection':1,'handoff-timeout':11,'handoff-config-refusal':8,'handoff-latch-refusal':9,'handoff-ucrdy-next':22}[case]
                        numbers=subprocess.check_output([exe,'0',str(guard),'-16','1','0',str(scenario)],
                                                        stderr=subprocess.DEVNULL,timeout=5)
                    if case.startswith('ack-'):
                        from test_s22plus_stage2_diagnostics import compile_stage_fixture
                        exe=compile_stage_fixture(directory/'ack-producer',handoff=True,reset_config=True,disabled_ucrdy=True,stale_uccs_ack=True,cfg1_diagnostics=version in (10,11),cfg1_ordered_selection=version==11)
                        scenario={'ack-zero':1,'ack-drift':7,'ack-nonzero':9,'ack-late-zero':11}[case]
                        numbers=subprocess.check_output([exe,*map(str,(0,0,-16,8,0,22,0,0,0,scenario))],stderr=subprocess.DEVNULL,timeout=5)
                    if case.startswith('cfg1-'):
                        from test_s22plus_cfg1_diagnostics import compile_cfg1
                        exe=compile_cfg1(directory/'cfg1-producer',ordered_selection=version==11)
                        post,expiry={'cfg1-readback':(0,0),'cfg1-budget':(1,1),'cfg1-budget-clear':(0,1),'cfg1-passed':(1,0)}[case]
                        numbers=subprocess.check_output([exe,*map(str,(8,8,8,0,0,1,0,post,expiry))],stderr=subprocess.DEVNULL,timeout=5)
                    if case.startswith('pre-effect-'):
                        from test_s22plus_pre_effect_return import compile_pre_effect, module_report
                        exe=compile_pre_effect(directory/'pre-effect-producer',snapshot=version==5,handoff=version in (6,7,8,9,10,11),reset_config=version in (7,8,9,10,11),disabled_ucrdy=version in (8,9,10,11),stale_uccs_ack=version in (9,10,11),cfg1_diagnostics=version in (10,11),cfg1_ordered_selection=version==11)
                        numbers=module_report(exe,'stage2' if case=='pre-effect-stage2' else 'refuse')
                        guest=compile_pre_effect(directory/'pre-effect-guest',guest=True,snapshot=version==5,handoff=version in (6,7,8,9,10,11),reset_config=version in (7,8,9,10,11),disabled_ucrdy=version in (8,9,10,11),stale_uccs_ack=version in (9,10,11),cfg1_diagnostics=version in (10,11),cfg1_ordered_selection=version==11)
                        gate=int(subprocess.check_output([guest],input=numbers,timeout=5))
                        self.assertEqual(gate==0,case!='pre-effect-stage2')
                    load=5 if case=='load-error' else 0;read=5 if case=='read-error' else 0
                    if load or read:numbers=b''
                    if case=='malformed-result':numbers=b'bad\n'
                    body+=struct.pack('<III',load,read,len(numbers))+numbers.ljust(256,b'\0')
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
            if case in ('missing-arm','wrong-arm','wrong-live'):
                self.assertIsNotNone(error)
                self.assertFalse((folder/'permit-intent.json').exists())
                self.assertNotIn('GO',observed);self.assertNotIn('Download',observed)
                return
            if case in ('success','pre-effect-success') or completed_failure:
                self.assertIsNone(error)
                self.assertEqual(value,download.rederive(adapter,request))
                records.publish(directory/(profile.SELECTION+'.json'),value)
                ready=download.return_request(adapter,request,create=True)
                self.assertEqual(ready['requested_ns'],records.read(folder/'control-intent.json')['requested_ns'])
                with mock.patch.object(link,'host_boot',return_value='later-host'):
                    self.assertEqual(link.rederive_link(adapter,request)['result']['status'],
                                     'NO_PROOF' if case=='pre-effect-success' or completed_failure else 'UFS_LINK_COMPLETED')
            else:self.assertIsNotNone(error)
            independent=prior.session.link_fact(adapter,request,{'status':'NO_PROOF'})
            self.assertTrue(independent['five_minute_same_boot'])
            if case in ('before-permit','intent-only','expired-at-permit','partial-result','malformed-result'):
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
                if version==5:
                    self.assertEqual(fact['hci_snapshot_captured'],63)
                    self.assertEqual(fact['hci_snapshot']['HCE'],1)
                    self.assertEqual(fact['hci_snapshot']['HCS'],1)
                self.assertFalse(fact['normal_return'])
                self.assertFalse((folder/'control-intent.json').exists())
            if case.startswith('handoff-'):
                fact=link.rederive_link(adapter,request)['result']
                self.assertEqual(fact['hce_handoff']['status'],{
                    'handoff-refusal':'REFUSED','handoff-post-rejection':'STOP_COMPLETE',
                    'handoff-timeout':'STOP_TIMEOUT','handoff-config-refusal':'REFUSED','handoff-latch-refusal':'REFUSED','handoff-ucrdy-next':'STOP_COMPLETE'}[case])
                self.assertFalse(fact['normal_return'])
                self.assertTrue(fact['recovery_return'])
                self.assertTrue((folder/'control-intent.json').exists())
                self.assertIn('Download',observed)
                self.assertEqual(independent['status'],'NO_PROOF')
            if case.startswith('cfg1-'):
                fact=link.rederive_link(adapter,request)['result']
                self.assertEqual(fact['cfg1']['outcome'],{'cfg1-readback':'BIT_CLEAR_BUDGET_PASS' if version==11 else 'READBACK_BIT_CLEAR',
                    'cfg1-budget':'BUDGET_EXPIRED','cfg1-budget-clear':'BUDGET_EXPIRED',
                    'cfg1-passed':'BIT_SET_BUDGET_PASS' if version==11 else 'CHECK_PASSED'}[case])
                self.assertFalse(fact['normal_return']);self.assertTrue(fact['recovery_return'])
                self.assertEqual(consumed,['permit']);self.assertIn('Download',observed)

            if case.startswith('ack-'):
                fact=link.rederive_link(adapter,request)['result']
                self.assertEqual(fact['initial_uccs_ack']['status'],{'ack-zero':'ZERO_OBSERVED_IN_TIME','ack-drift':'DRIFT','ack-nonzero':'NONZERO_READBACK','ack-late-zero':'DEADLINE'}[case])
                self.assertFalse(fact['normal_return']);self.assertTrue(fact['recovery_return'])
                self.assertTrue((folder/'control-intent.json').exists());self.assertIn('Download',observed)
                self.assertEqual(independent['status'],'NO_PROOF')
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
        self.assertEqual(observed.count('Download'),int(case in ('success','bad-ack','pre-effect-success','pre-effect-bad-ack') or completed_failure))

    def test_expiry_at_actual_permit_capture(self):self.run_case('expired-at-permit')
    def test_expiry_after_durable_return_intent(self):self.run_case('expired-at-return')

    def test_full_success_and_rederived_late_return(self):self.run_case('success')
    def test_diagnostic_success_and_rederived_late_return(self):self.run_case('success',version=2)
    def test_stage2_schema_success_keeps_original_return_conditions(self):self.run_case('success',version=3)
    def test_actual_stage2_report_preserves_raw_and_stops_return(self):self.run_case('stage2-rejection',version=3)
    def test_snapshot_actual_report_preserves_raw_and_stops_return(self):self.run_case('stage2-rejection',version=5)
    def test_snapshot_success_keeps_original_return(self):self.run_case('success',version=5)
    def test_snapshot_pre_effect_certificate_and_return(self):self.run_case('pre-effect-success',version=5)
    def test_snapshot_stage2_never_returns(self):self.run_case('pre-effect-stage2',version=5)
    def test_handoff_success_keeps_result_bound_return(self):self.run_case('success',version=6)
    def test_handoff_complete_link_survives_failed_ack(self):self.run_case('bad-ack',version=6)
    def test_handoff_pre_effect_certificate_and_return(self):self.run_case('pre-effect-success',version=6)
    def test_handoff_admission_returns_without_link_proof(self):self.run_case('handoff-refusal',version=6)
    def test_handoff_post_guard_returns_without_link_proof(self):self.run_case('handoff-post-rejection',version=6)
    def test_handoff_timeout_returns_without_link_proof(self):self.run_case('handoff-timeout',version=6)
    def test_v6_load_error_returns(self):self.run_case('load-error',version=6)
    def test_v6_read_error_returns(self):self.run_case('read-error',version=6)
    def test_v6_partial_result_retains_raw_without_control(self):self.run_case('partial-result',version=6)
    def test_v6_malformed_result_retains_raw_without_control(self):self.run_case('malformed-result',version=6)
    def test_missing_arm_blocks_permit(self):self.run_case('missing-arm',version=6)
    def test_wrong_arm_blocks_permit(self):self.run_case('wrong-arm',version=6)
    def test_wrong_live_child_blocks_permit(self):self.run_case('wrong-live',version=6)
    def test_handoff_return_deadline_not_extended(self):self.run_case('expired-at-return',version=6)
    def test_v7_actual_producer_socket_return_and_failure_paths(self):
        for case in ('success','bad-ack','pre-effect-success','handoff-config-refusal',
                     'handoff-latch-refusal','handoff-post-rejection','handoff-timeout',
                     'load-error','read-error','partial-result','malformed-result',
                     'missing-arm','wrong-arm','wrong-live','expired-at-return'):
            with self.subTest(case=case):self.run_case(case,version=7)
    def test_v8_actual_producer_socket_return_and_failure_paths(self):
        for case in ('success','bad-ack','pre-effect-success','handoff-config-refusal',
                     'handoff-latch-refusal','handoff-ucrdy-next','handoff-post-rejection','handoff-timeout',
                     'load-error','read-error','partial-result','malformed-result',
                     'missing-arm','wrong-arm','wrong-live','expired-at-return'):
            with self.subTest(case=case):self.run_case(case,version=8)
    def test_v9_actual_producer_socket_return_and_failures(self):
        for case in ('success','bad-ack','pre-effect-success','ack-zero','ack-drift','ack-nonzero','ack-late-zero',
                     'load-error','read-error','partial-result','malformed-result','missing-arm','wrong-live','expired-at-return'):
            with self.subTest(case=case):self.run_case(case,version=9)
    def test_v10_actual_producer_socket_return_and_failures(self):
        for case in ('success','bad-ack','pre-effect-success','ack-zero','ack-nonzero','cfg1-readback',
                     'cfg1-budget','cfg1-passed','load-error','read-error','partial-result',
                     'malformed-result','missing-arm','wrong-live','expired-at-return'):
            with self.subTest(case=case):self.run_case(case,version=10)
    def test_v11_actual_producer_socket_return_and_failures(self):
        for case in ('success','bad-ack','pre-effect-success','ack-zero','ack-nonzero','cfg1-readback',
                     'cfg1-budget','cfg1-budget-clear','cfg1-passed','load-error','read-error','partial-result',
                     'malformed-result','missing-arm','wrong-live','expired-at-return'):
            with self.subTest(case=case):self.run_case(case,version=11)
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
