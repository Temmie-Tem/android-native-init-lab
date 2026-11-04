"""Real ARM64 control code, framed sockets, cue races and one-shot Session cuts."""
import copy
import builtins
import json
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

import test_s22plus_mainline_debian_ram as debian_tests
import test_s22plus_mainline_live_v1 as live
import s22plus_mainline_access_v1 as access
import s22plus_mainline_attach_v1 as attach
import s22plus_mainline_download_access_v1 as download
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_session_v1 as session
import s22plus_native_records_v3 as records
import s22plus_native_session_v3 as owner
import device_action_raw_capture_v1 as raw
from mainline.s22plus_canary_h0 import download_ram as codec
from mainline.s22plus_canary_h0 import download_vm

ROOT=Path(__file__).resolve().parents[1]


class VMEventTests(unittest.TestCase):
    def test_actual_reset_event_is_distinct_from_host_termination_or_missing_event(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);(folder/'qmp-command.json').write_bytes(b'{"execute":"qmp_capabilities"}\n')
            prefix=[{'QMP':{'version':{'qemu':{'major':10}}}},{'return':{}}]
            def save(rows):(folder/'qmp.raw').write_bytes(b''.join(json.dumps(row).encode()+b'\r\n' for row in rows))
            reset={'event':'SHUTDOWN','data':{'guest':True,'reason':'guest-reset'}}
            stopped={'event':'SHUTDOWN','data':{'guest':False,'reason':'host-signal'}}
            save(prefix+[reset]);self.assertEqual(download_vm.reset_event(folder,expected=True),[reset])
            save(prefix+[stopped]);self.assertEqual(download_vm.reset_event(folder,expected=False),[])
            for rows in (prefix,prefix+[stopped],prefix+[reset,reset],prefix+[{'event':'SHUTDOWN','data':{'guest':True,'reason':'guest-panic'}}]):
                save(rows)
                with self.assertRaises(ValueError):download_vm.reset_event(folder,expected=True)
            save(prefix+[reset])
            with self.assertRaises(ValueError):download_vm.reset_event(folder,expected=False)
            (folder/'qmp-command.json').write_bytes(b'{"execute":"system_reset"}\n')
            with self.assertRaises(ValueError):download_vm.reset_event(folder,expected=True)


class ActualControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.out=Path(cls.tmp.name)
        seal='\n'.join('static const unsigned char canary_'+name+'[32]={'+','.join(str(i+offset) for i in range(32))+'};'
                       for name,offset in (('key',0),('id',32)))+'\n#define CANARY_PORT 47649\n'
        for name,value in dict(device_ip='192.0.2.2',host_ip='192.0.2.1',netmask='255.255.255.252',
                device_mac='02:00:00:00:00:01',host_mac='02:00:00:00:00:02',serial='fixture',udc='fixture').items():
            seal+='static const char canary_'+name+'[]='+json.dumps(value)+';\n'
        (cls.out/'seal.h').write_text(seal)
        cls.exe=cls.out/'fixture'
        subprocess.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-unused-const-variable','-ffunction-sections','-fdata-sections',
            '-Wl,--gc-sections','-I',cls.out,ROOT/'tests/s22plus_mainline_download_fixture.c','-o',cls.exe],check=True)
        assert b'ARM aarch64' in subprocess.check_output(['file',cls.exe])

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def run_case(self,case,modes=b'recovery bootloader download\n\0'):
        path=self.out/'modes';path.write_bytes(modes)
        result=subprocess.run(['qemu-aarch64',self.exe,case,path],capture_output=True,check=True,timeout=3)
        return dict((key,int(value)) for key,value in (part.split('=') for part in result.stdout.decode().split()))

    def test_exact_physical_readiness_format_and_links(self):
        self.assertEqual(self.run_case('ready-valid'),{'ready':1})
        for case in ('missing-modes','missing-link','wrong-driver','wrong-node'):
            with self.subTest(case=case):self.assertEqual(self.run_case('ready-'+case),{'ready':0})
        for modes in (b'recovery bootloader download\n',b'recovery bootloader\n\0',
                      b'recovery download bootloader\n\0',b'recovery bootloader download extra\n\0',b''):
            with self.subTest(modes=modes):self.assertEqual(self.run_case('ready-valid',modes),{'ready':0})

    def test_valid_control_ack_and_exactly_one_returning_restart_syscall(self):
        self.assertEqual(self.run_case('positive'),dict(error=5,resets=1,ack=120,reads=2))

    def test_rejected_authenticated_bindings_and_deadlines_never_reset(self):
        for case,error in {'wrong-auth':13,'wrong-boot':13,'wrong-nonce':13,'legacy-command':13,
                'partial-control':32,'extra-tail':71,'missing-eof':110,'expired':110,
                'expired-after-eof':110,'expired-during-binding':110,'binding-lost':19}.items():
            with self.subTest(case=case):
                result=self.run_case(case);self.assertEqual(result['error'],error);self.assertEqual(result['resets'],0)


class AttachTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.op=Path(self.tmp.name)
        operation=records.publish(self.op/'operation.json',{'fixture':'one'})
        now=records.clock()
        self.window=records.publish(self.op/'window.json',dict(operation=operation,host_boot=records.host_boot(),
            opened_ns=now,deadline_ns=now+3_000_000_000))

    def issue(self):return attach.issue(self.op,self.window,evidence={'fixed_census':'fixture'},check=lambda:None)

    def test_no_issued_cue_closes_without_an_operator_gate_and_late_issue_is_rejected(self):
        closure=attach.close_issuance(self.op,self.window,guard=lambda:None)
        self.assertIsNone(records.read(records.verify(closure))['cue'])
        with self.assertRaises(ValueError):self.issue()
        self.assertEqual(attach.rederive(self.op,self.window),closure)
        with mock.patch.object(attach,'host_boot',return_value='a-different-current-host-boot'):
            self.assertEqual(attach.rederive(self.op,self.window),closure)
            with self.assertRaises(ValueError):attach.binding(self.op,self.window)

    def test_only_actual_completed_or_cancelled_cue_resolves(self):
        cue=self.issue()
        for resolution in ('timeout','assumed',''):
            with self.assertRaises(ValueError):attach.resolve(self.op,self.window,cue=cue,
                resolution=resolution,operator_statement='fixture actual response')
        with self.assertRaises(ValueError):attach.resolve(self.op,self.window,cue=cue,
            resolution='completed',operator_statement=' ')
        for bad in ({},dict(cue,sha256='0'*64)):
            with self.assertRaises(ValueError):attach.resolve(self.op,self.window,cue=bad,
                resolution='completed',operator_statement='done')
        attach.resolve(self.op,self.window,cue=cue,resolution='cancelled',operator_statement='actual cancellation')
        with self.assertRaises((ValueError,OSError)):attach.resolve(self.op,self.window,cue=cue,
            resolution='completed',operator_statement='duplicate')
        closure=attach.close_issuance(self.op,self.window,guard=lambda:None)
        self.assertEqual(records.read(records.verify(closure))['cue'],cue)

    def test_publisher_control_race_waits_for_the_issued_cue(self):
        inside=threading.Event();release=threading.Event();waiting=threading.Event();result=[];errors=[]
        def check():inside.set();self.assertTrue(release.wait(2))
        def publish_cue():
            try:result.append(attach.issue(self.op,self.window,evidence={},check=check))
            except Exception as error:errors.append(error)
        publisher=threading.Thread(target=publish_cue);publisher.start();self.assertTrue(inside.wait(1))
        def control():
            try:attach.close_issuance(self.op,self.window,guard=waiting.set)
            except Exception as error:errors.append(error)
        controller=threading.Thread(target=control);controller.start();self.assertTrue(waiting.wait(1))
        release.set();publisher.join(1);self.assertEqual(len(result),1)
        self.assertFalse((self.op/'mainline-attach-closed.json').exists())
        attach.resolve(self.op,self.window,cue=result[0],resolution='completed',operator_statement='reconnected')
        controller.join(2);self.assertFalse(controller.is_alive());self.assertFalse(errors)
        self.assertEqual(records.read(records.verify(attach.rederive(self.op,self.window)))['cue'],result[0])

    def test_expiry_never_cancels_or_renews_an_unresolved_cue(self):
        cue=self.issue();deadline=records.read(records.verify(self.window))['deadline_ns']
        with mock.patch.object(attach,'clock',return_value=deadline),self.assertRaises(ValueError):
            attach.close_issuance(self.op,self.window,guard=lambda:None)
        self.assertFalse((self.op/'mainline-attach-closed.json').exists())
        self.assertFalse((self.op/'mainline-attach-resolution.json').exists())
        with mock.patch.object(attach,'clock',return_value=deadline+1):
            response=attach.resolve(self.op,self.window,cue=cue,resolution='completed',operator_statement='actual late report')
            self.assertEqual(records.read(records.verify(response))['resolved_ns'],deadline+1)
            with self.assertRaises(ValueError):attach.close_issuance(self.op,self.window,guard=lambda:None)
        self.assertFalse((self.op/'mainline-attach-closed.json').exists())

    def test_stalled_publisher_lock_is_bounded_by_original_deadline(self):
        import fcntl
        with (self.op/'mainline-attach.lock').open('w') as held:
            fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
            now=records.clock();window=records.read(records.verify(self.window))
            path=self.op/'short-window.json';window['deadline_ns']=now+30_000_000
            short=records.publish(path,window);started=time.monotonic()
            with self.assertRaises(ValueError):attach.close_issuance(self.op,short,guard=lambda:None)
            self.assertLess(time.monotonic()-started,.2)
        self.assertFalse((self.op/'mainline-attach-closed.json').exists())


class DownloadWireTests(debian_tests.DebianWireTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.codec=cls.fixture.base/'download-codec'
        subprocess.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-DCANARY_DEBIAN_RAM','-DCANARY_DOWNLOAD_RAM',
            ROOT/'tests/s22plus_mainline_protocol_fixture.c','-o',cls.codec],check=True)

    def manifest(self):
        value=super().manifest();value['debian_ram'].update(schema=codec.SCHEMA,download_return=codec.declaration())
        return value

    def body(self):
        body=super().body();body[:8]=b'G0QNRS1\0';struct.pack_into('<I',body,276,1);return body

    def test_authenticated_wrong_debian_claims_truncation_and_identity_rejected(self):
        for offset,value in ((256,1),(260,2),(264,0),(268,ord('3')),(272,ord('2')),(276,2),(280,1)):
            body=self.body();struct.pack_into('<I',body,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ValueError):self.fixture.check(self.raw(body),manifest=self.manifest())
        body=self.body();struct.pack_into('<I',body,276,0)
        self.assertFalse(self.fixture.check(self.raw(body),manifest=self.manifest())['download_ready'])

    def exchange(self,*,base=None,bad_ack=False,late=False,no_eof=False):
        tmp=tempfile.TemporaryDirectory(dir=self.fixture.base);self.addCleanup(tmp.cleanup);folder=Path(tmp.name)
        manifest=self.manifest();manifest.update(network={'host_ip':'127.0.0.1','device_ip':'127.0.0.1'},port=1)
        base=self.raw() if base is None else base;requests=[];controls=[];intents=[];errors=[]
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(2)
        address=listener.getsockname()
        def serve():
            try:
                with listener.accept()[0] as client:
                    client.settimeout(2);query=b''
                    while len(query)<72:
                        chunk=client.recv(72-len(query))
                        if not chunk:break
                        query+=chunk
                    requests.append(query);client.sendall(base)
                    if len(base)<384:client.shutdown(socket.SHUT_WR)
                    control=b''
                    while len(control)<codec.CONTROL_SIZE:
                        chunk=client.recv(codec.CONTROL_SIZE-len(control))
                        if not chunk:break
                        control+=chunk
                    controls.append(control)
                    if control:
                        head=codec.ACK_MAGIC+self.fixture.identity+self.fixture.nonce+base[72:88]
                        ack=head+codec.tag(self.fixture.key,self.fixture.identity,3,head)
                        if bad_ack:ack=ack[:-1]+bytes([ack[-1]^1])
                        client.sendall(ack)
                        if no_eof:time.sleep(.3)
                        else:client.shutdown(socket.SHUT_WR);client.recv(1)
            except (ConnectionResetError,BrokenPipeError):pass
            except Exception as error:errors.append(error)
            finally:listener.close()
        thread=threading.Thread(target=serve);thread.start()
        duration=100_000_000 if no_eof else 2_000_000_000
        deadline=records.clock()+duration
        def intent(proof,packet):
            # These are real durable raw receipts while the same socket is open.
            self.assertTrue((folder/'base-complete.json').exists())
            self.assertFalse((folder/'connection.json').exists())
            self.assertEqual(proof['pid'],1);intents.append(packet)
            if late:raise ValueError('fresh Session binding failed')
        error=None
        with mock.patch.object(download.secrets,'token_bytes',return_value=self.fixture.nonce):
            try:download.capture_connection(folder,manifest,{'interface':'lo'},deadline_ns=deadline,
                guard=lambda phase:None,before_control=intent,connect=lambda client:client.connect(address))
            except (ValueError,raw.RawCaptureError,OSError) as failure:error=failure
        thread.join(3);self.assertFalse(thread.is_alive());self.assertFalse(errors)
        self.assertEqual(len(requests),1)
        return folder,error,controls,intents

    def test_same_connection_raw_first_base_then_unique_control_ack_and_close(self):
        folder,error,controls,intents=self.exchange();self.assertIsNone(error)
        self.assertEqual(len(intents),1);self.assertEqual(len(controls),1)
        proof=self.fixture.check(self.raw(),manifest=self.manifest())
        self.assertEqual(controls[0],codec.control(self.fixture.key,self.fixture.identity,self.fixture.nonce,proof['boot_id']))
        base=records.read(folder/'base-complete.json');self.assertEqual(base['framing'],'length')
        self.assertNotIn('eof',base);self.assertNotIn('descriptor_closed',base)
        final=records.read(folder/'connection.json');self.assertTrue(final['descriptor_closed']);self.assertTrue(final['eof'])

    def test_bad_base_and_partial_prefix_cannot_dispatch_control_and_preserve_raw(self):
        good=self.raw()
        for value in (good[:100],good[:352]+bytes(32)+good[384:]):
            # A short fixture closes its write half so the framed receiver can
            # fail immediately. Use the bounded socket timeout for this cut.
            folder,error,controls,intents=self.exchange(base=value)
            self.assertIsNotNone(error);self.assertFalse(intents);self.assertFalse(any(controls))
            prefix=raw.read_stdout(raw.load_handle(folder/'prefix.capture.json'),maximum=384)
            self.assertEqual(prefix,value[:384])

    def test_guard_failure_has_no_control_and_ack_failure_keeps_consumed_intent(self):
        folder,error,controls,intents=self.exchange(late=True)
        self.assertIsNotNone(error);self.assertEqual(len(intents),1);self.assertFalse(any(controls))
        for options in ({'bad_ack':True},{'no_eof':True}):
            folder,error,controls,intents=self.exchange(**options)
            self.assertIsNotNone(error);self.assertEqual(len(intents),1);self.assertEqual(len(controls[0]),codec.CONTROL_SIZE)
            self.assertTrue((folder/'base-complete.json').exists());self.assertTrue((folder/'ack.capture.json').exists())

    def test_complete_raw_rederivation_intent_join_and_immutable_return_deadline(self):
        folder,error,controls,intents=self.exchange();self.assertIsNone(error)
        operation=folder/'operation';operation.mkdir();attempt=records.read(folder/'attempt.json')
        complete=records.read(folder/'base-complete.json');final=records.read(folder/'connection.json')
        found={'interface':'lo'};manifest=self.manifest()
        manifest.update(network={'host_ip':'127.0.0.1','device_ip':'127.0.0.1'},port=1)
        grant=records.publish(operation/'grant.json',dict(host_boot=attempt['host_boot'],deadline_ns=attempt['deadline_ns']+1_000_000_000))
        request=dict(operation='mainline-ram',N={'download_return':{'fixture':True},'debian_ram':{'fixture':True}},grant=grant)
        op=records.publish(operation/'operation.json',request)
        window=dict(operation=op,host_boot=attempt['host_boot'],opened_ns=attempt['opened_ns']-1,deadline_ns=attempt['deadline_ns'])
        window_pin=records.publish(folder/'window.json',window);records.publish(folder/'endpoint.json',found)
        for label in ('network-create','network-up','usb-before-connect','usb-after-connect','usb-before-control'):
            raw.publish_captured_bytes(folder,label,stdout=b'fixture',stderr=b'')
        adapter=mock.Mock();adapter.directory=operation;adapter.folder.return_value=folder
        requested=complete['finished_ns']+2;self.assertLess(requested,final['finished_ns'])
        with mock.patch.object(profile,'image_binding',return_value=manifest),mock.patch.object(access,'window_for',return_value=window),\
             mock.patch.object(access,'endpoint',return_value=found),mock.patch.object(access,'capture_endpoint',side_effect=AssertionError('offline read')):
            base=download.rederive_base(adapter,request)
            with mock.patch.object(attach,'clock',return_value=requested-1):
                closure=attach.close_issuance(operation,window_pin,guard=lambda:None)
            intent=dict(operation=op,base=base,control=intents[0],attach=closure,boot_id=base['proof']['boot_id'],
                candidate_id=manifest['candidate_id'],requested_ns=requested,
                deadline_ns=records.read(records.verify(grant))['deadline_ns'],observation_deadline_ns=window['deadline_ns'],
                host_boot=attempt['host_boot'])
            intent_pin=records.publish(folder/'control-intent.json',intent)
            journal=records.Journal(operation/'journal')
            journal.append('effect-intent',step='install-native-first',action='transfer',role='N',ending=None,recovery=False,detail={})
            journal.append('effect-intent',step=profile.SELECTION,action=download.ACTION,
                role='N',ending=None,recovery=False,detail=intent)
            value=download.rederive(adapter,request);self.assertEqual(value['control'],intent_pin)
            from s22plus_native_adapter_v3 import Adapter
            adapter.recover_step_result.side_effect=lambda *_:download.rederive(adapter,request)
            Adapter.validate_result(adapter,owner.Step(profile.SELECTION,download.ACTION,'N'),value,request)
            records.publish(operation/(profile.SELECTION+'.json'),value)
            ready=download.return_request(adapter,request,create=True)
            self.assertEqual(ready['deadline_ns'],intent['deadline_ns'])
            with mock.patch.object(attach,'host_boot',return_value='different-current-host'):
                self.assertEqual(download.rederive(adapter,request),value)
                self.assertEqual(download.return_request(adapter,request,create=True),ready)
            launch=records.publish(operation/'launch.json',dict(arrival_deadline_ns=ready['deadline_ns'],
                boottime_ns=final['finished_ns']+1,ticket={'fixture':'Download ticket'},revalidation={'fixture':'exact A dispatch'}))
            adapter.recover_transfer_result.return_value=dict(launch=launch,completed=True)
            self.assertEqual(session.terminal(adapter,request,recovered=False)['status'],'PASS_MAINLINE_DOWNLOAD_RAM')
            self.assertEqual(session.terminal(adapter,request,recovered=True)['status'],'PASS_MAINLINE_DOWNLOAD_RAM')
            adapter.recover_transfer_result.side_effect=OSError('physical recovery cannot supply install-android evidence')
            result=session.terminal(adapter,request,recovered=True)
            self.assertEqual(result['status'],'NO_PROOF');self.assertTrue(result['mainline_pid1'])
            self.assertFalse(result['automatic_download_return_proved'])
            path=folder/'control-intent.json';changed=copy.deepcopy(intent);changed['deadline_ns']+=1
            path.chmod(0o600);path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):download.rederive(adapter,request)


class DownloadOwnerTests(unittest.TestCase):
    setUp=live.harness.OwnerTests.setUp

    def operation(self,*,fault=None):
        device=live.harness.DeviceFixture()
        with mock.patch.object(device,'prepare',return_value={'N':{'download_return':{'fixture':'admitted'}}}):
            directory=owner.prepare_operation(self.root,self.grant,operation='mainline-ram',adapter=device)
        device.folder=lambda name:directory/('io-'+name)
        def observe(adapter,request,guard,before_control):
            guard();adapter.assert_mode('N');adapter.actions.append('base-frame')
            if fault=='before-intent':raise ValueError('base proof failed')
            before_control(lambda:{'fixed':'original control'})
            adapter.actions.append('download-control-once');adapter.mode='Download'
            if fault=='after-control':raise OSError('ACK uncertain')
            return adapter.proof(session.normal_steps(request)[2])
        for obj,name,value in ((download,'observe',observe),(download,'return_request',lambda *a,**k:{})):
            patch=mock.patch.object(obj,name,value);patch.start();self.addCleanup(patch.stop)
        return owner.Session(self.root,directory,device),device

    def test_normal_control_automatic_original_a_no_physical_pause_and_no_replay(self):
        current,device=self.operation();result=current.execute(attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED');self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('download-control-once'),1)
        effects=[r['data']['action'] for r in current.rows() if r['event']=='effect-intent']
        self.assertEqual(effects,['download','transfer','mainline-download','transfer'])
        before=list(device.actions);current.repair_close();self.assertEqual(device.actions,before)
        with self.assertRaises(ValueError):current.execute(attended=True)

    def test_uncertainty_recovery_only_a_never_resends_the_control(self):
        for fault,expected in (('before-intent',0),('after-control',1)):
            self.setUp();current,device=self.operation(fault=fault)
            self.assertEqual(current.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
            self.assertEqual(current.recover(attended=True)['state'],'ANDROID_CLOSED')
            self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('download-control-once'),expected)

    def test_missing_or_broken_candidate_checker_cannot_block_original_a(self):
        for error in (ImportError('missing Download VM checker'),SyntaxError('broken Download VM checker')):
            self.setUp();current,device=self.operation(fault='after-control')
            self.assertEqual(current.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
            original=builtins.__import__;recover=device.recover_step_result;attempts=[]
            def missing(name,globals=None,locals=None,fromlist=(),level=0):
                if 'download_vm' in (fromlist or ()):attempts.append(name);raise error
                return original(name,globals,locals,fromlist,level)
            def rederive(step,request):
                if step.name==profile.SELECTION:profile.download_return_binding({}, {}, {}, {}, {})
                return recover(step,request)
            with mock.patch('builtins.__import__',side_effect=missing),mock.patch.object(device,'recover_step_result',side_effect=rederive):
                result=current.recover(attended=True)
            self.assertEqual(result['state'],'ANDROID_CLOSED');self.assertEqual(device.installed,['N','A'])
            self.assertEqual(device.actions.count('download-control-once'),1);self.assertEqual(len(attempts),1)


if __name__=='__main__':unittest.main()
