"""Actual codec and raw-producer tests for fixed Debian RAM SSH admission."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import test_s22plus_mainline_debian_ram as debian_tests
import test_s22plus_mainline_live_v1 as live
import s22plus_mainline_access_v1 as access
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_session_v1 as session
import s22plus_mainline_task_v1 as task
import s22plus_native_records_v3 as records
import device_action_raw_capture_v1 as raw
import debian_ram
import ssh_ram
import verify
from mainline.s22plus_canary_h0 import ssh_ram as live_ssh

BOOT='00000000-0000-4000-8000-000000000001'
OUTPUT=('G0Q_SSH_RAM_V1\nboot_id='+BOOT+'\nUid: 1000\t1000\t1000\t1000\n'
        'Gid: 1000\t1000\t1000\t1000\nGroups: 1000\nCapEff: 0000000000000000\n').encode()


class SSHWireTests(debian_tests.DebianWireTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.codec=cls.fixture.base/'ssh-codec'
        subprocess.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-DCANARY_DEBIAN_RAM','-DCANARY_DEBIAN_SSH',
            debian_tests.canary.ROOT/'tests/s22plus_mainline_protocol_fixture.c','-o',cls.codec],check=True)
        subprocess.run(['file',cls.codec],check=True,stdout=subprocess.DEVNULL)

    def manifest(self):
        value=super().manifest();value['debian_ram'].update(schema=ssh_ram.SCHEMA,
            inittab_sha256=hashlib.sha256(ssh_ram.INITTAB).hexdigest())
        return value

    def body(self):
        body=super().body();body[:8]=b'G0QSRS1\0';struct.pack_into('<I',body,276,1)
        body[320:352]=hashlib.sha256(ssh_ram.INITTAB).digest();return body

    def test_authenticated_wrong_debian_claims_truncation_and_identity_rejected(self):
        for offset,value in [(256,1),(260,2),(264,0),(268,ord('3')),(272,ord('2')),(276,2),(280,1)]:
            body=self.body();struct.pack_into('<I',body,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                self.fixture.check(self.raw(body),manifest=self.manifest())
        body=self.body();struct.pack_into('<I',body,276,0)
        proof=self.fixture.check(self.raw(body),manifest=self.manifest())
        self.assertFalse(proof['ssh_ready']);self.assertEqual(proof['pid'],1)
        with self.assertRaises(ValueError):self.fixture.check(self.raw()[:-1],manifest=self.manifest())

    def test_fixed_inittab_excludes_shell_and_newc_has_only_fixed_nodes(self):
        files={name:b'fixture' for name in ssh_ram.specification()[0]};files[debian_ram.OBSERVER]=b'fixture'
        files['etc/inittab']=ssh_ram.INITTAB;data=debian_ram.pack(files,False,specification=ssh_ram.specification())
        # Independent narrow newc decode includes the canonical root entry;
        # the generic firmware parser deliberately excludes '.' path aliases.
        rows={};at=0
        while data[at:at+6]==b'070701':
            fields=[int(data[at+6+i*8:at+14+i*8],16) for i in range(13)]
            name=data[at+110:at+110+fields[11]-1].decode();start=(at+110+fields[11]+3)&~3
            body=data[start:start+fields[6]];at=(start+fields[6]+3)&~3
            if name=='TRAILER!!!':break
            self.assertNotIn(name,rows);rows[name]=(fields,body)
        self.assertEqual(rows['.'][0][1:4],[stat.S_IFDIR|0o755,0,0])
        self.assertEqual(rows['etc/ssh/ssh_host_ed25519_key'][0][1],stat.S_IFREG|0o600)
        self.assertEqual(rows['dev/urandom'][0][9:11],[1,9])
        self.assertEqual(rows['etc/inittab'][1],ssh_ram.INITTAB)
        for name in ('etc/ssh/sshrc','etc/nologin','usr/lib/openssh/sftp-server','bin/sh'):
            self.assertNotIn(name,rows)
        files['etc/ssh/sshrc']=b'bad'
        with self.assertRaises(ValueError):debian_ram.pack(files,False,specification=ssh_ram.specification())


class SSHContractTests(unittest.TestCase):
    def test_same_boot_uid_groups_capabilities_and_complete_output(self):
        self.assertEqual(ssh_ram.parse_stdout(OUTPUT,BOOT)['uid'],1000)
        for bad in (OUTPUT.replace(b'Uid: 1000',b'Uid: 0'),OUTPUT.replace(b'Groups: 1000',b'Groups: 0 1000'),
                    OUTPUT.replace(b'CapEff: 0000000000000000',b'CapEff: 0000000000000001'),
                    OUTPUT.replace(BOOT.encode(),b'00000000-0000-4000-8000-000000000002'),OUTPUT[:-1],OUTPUT+OUTPUT):
            with self.subTest(output=bad),self.assertRaises(ValueError):ssh_ram.parse_stdout(bad,BOOT)

    def test_client_ignores_configuration_agent_and_extra_session_features(self):
        argv=ssh_ram.command({'keys':{'client-key':{'path':'/private/client-key'}}},'/usr/bin/ssh',
            '/private/known','192.0.2.2',source='192.0.2.1')
        self.assertEqual(argv[:4],['/usr/bin/ssh','-F','/dev/null','-T'])
        for option in ('ConnectionAttempts=1','IdentityAgent=none','StrictHostKeyChecking=yes',
                       'ControlMaster=no','ControlPath=none','ProxyCommand=none','ProxyJump=none',
                       'ClearAllForwardings=yes','PasswordAuthentication=no','KbdInteractiveAuthentication=no'):
            self.assertIn(option,argv)
        self.assertEqual(argv[-2:],['probe@192.0.2.2','g0q-ram-probe-v1'])
        self.assertNotIn('-B',argv);self.assertEqual(argv[argv.index('-b')+1],'192.0.2.1')

    def test_missing_ssh_candidate_validator_does_not_gain_recovery_dependency(self):
        import builtins
        original=builtins.__import__
        def missing(name,globals=None,locals=None,fromlist=(),level=0):
            if 'ssh_ram' in (fromlist or ()):raise ImportError('SSH checker absent')
            return original(name,globals,locals,fromlist,level)
        with mock.patch.object(task,'capability',return_value={}),mock.patch('builtins.__import__',side_effect=missing):
            with self.assertRaisesRegex(ValueError,'validator is unavailable'):
                profile.debian_ram_binding({}, {'debian_ram':{'schema':ssh_ram.SCHEMA}}, {}, {})
        self.assertTrue(task.marker_only('workspace/public/src/mainline/s22plus_canary_h0/ssh_ram.py'))

    def test_failed_ssh_keeps_independent_base_proof_but_cannot_claim_ssh(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'qualification.json';path.write_text('{"ssh":{}}\n')
            request={'N':{'debian_ram':records.pin(path)}}
            base={'proof':{'runtime_schema':ssh_ram.SCHEMA,'ssh_ready':True}}
            with (mock.patch.object(access,'rederive',side_effect=raw.RawCaptureError('partial SSH')),
                  mock.patch.object(access,'rederive_base',return_value=base)):
                result=session.terminal(object(),request,recovered=True)
            self.assertEqual(result['status'],'NO_PROOF');self.assertTrue(result['mainline_pid1'])
            self.assertTrue(result['authenticated_usb']);self.assertFalse(result['ssh_proved'])
            self.assertFalse(result['replay_authorized'])


class SSHCaptureTests(unittest.TestCase):
    setUp=live.USBTests.setUp
    device=live.USBTests.device
    interface=live.USBTests.interface
    capture=live.USBTests.capture
    def setup_ssh(self,program):
        node=self.device();self.interface(node)
        self.manifest['network'].update(host_ip='192.0.2.1',device_ip='192.0.2.2')
        self.manifest['debian_ram']={'schema':ssh_ram.SCHEMA,'keys':{}}
        found=access.endpoint(self.capture('selected'),self.manifest)
        plan={'ssh':records.pin(Path(sys.executable).resolve(),maximum=32*1024*1024)}
        capture=access.capture_endpoint
        self.capture_patch=mock.patch.object(access,'capture_endpoint',
            side_effect=lambda folder,label:capture(folder,label,usb_root=self.usb,net_root=self.net))
        self.capture_patch.start();self.addCleanup(self.capture_patch.stop)
        patch=mock.patch.object(live_ssh,'known_hosts',return_value=b'fixed-fixture-host-key\n');patch.start();self.addCleanup(patch.stop)
        patch=mock.patch.object(live_ssh,'command',return_value=[plan['ssh']['path'],'-c',program]);patch.start();self.addCleanup(patch.stop)
        def route(plan,tool,args,folder,label):
            self.assertEqual(tool,'ip');self.assertNotIn('oif',args)
            return raw.publish_captured_bytes(folder,label,stdout=json.dumps([
                {'dev':found['interface'],'from':'192.0.2.1'}]).encode())
        patch=mock.patch.object(access,'host_command',side_effect=route);patch.start();self.addCleanup(patch.stop)
        return found,plan

    def run_ssh(self,found,plan,*,seconds=7,guard=lambda:None):
        return access.capture_ssh(self.out,self.manifest,plan,found,{'ssh_ready':True,'boot_id':BOOT},
            deadline_ns=records.clock()+int(seconds*1e9),guard=guard)

    def test_success_is_sealed_before_parse_and_second_invocation_never_spawns(self):
        counter=self.base/'count'
        program=f'from pathlib import Path;import sys;Path({str(counter)!r}).write_text("once");sys.stdout.buffer.write({OUTPUT!r})'
        found,plan=self.setup_ssh(program)
        real=live_ssh.parse_stdout
        def parsed(data,boot):
            self.assertTrue((self.out/'ssh-complete.json').exists())
            raw.require_success(raw.load_handle(self.out/'ssh.capture.json'))
            return real(data,boot)
        with mock.patch.object(live_ssh,'parse_stdout',side_effect=parsed):result=self.run_ssh(found,plan)
        self.assertEqual(result['uid'],1000);before=counter.stat().st_mtime_ns
        with self.assertRaises((raw.RawCaptureError,FileExistsError)):self.run_ssh(found,plan)
        self.assertEqual(counter.stat().st_mtime_ns,before)

    def test_partial_failure_and_timeout_keep_complete_raw_status_without_replay(self):
        found,plan=self.setup_ssh('import sys,time;sys.stdout.write("partial");sys.stdout.flush();time.sleep(5)')
        with self.assertRaises(raw.RawCaptureError):self.run_ssh(found,plan,seconds=4.4)
        handle=raw.load_handle(self.out/'ssh.capture.json');self.assertTrue(handle.timed_out)
        self.assertEqual(raw.read_stdout(handle,maximum=1024),b'partial')
        self.assertTrue((self.out/'ssh-intent.json').exists());self.assertTrue((self.out/'ssh-complete.json').exists())
        self.assertFalse((self.out/'usb-after-ssh.capture.json').exists())

    def test_effect_time_guard_failure_is_durable_and_does_not_start_client(self):
        found,plan=self.setup_ssh('raise RuntimeError("must not run")')
        guard=mock.Mock(side_effect=[None,records.SessionError('scope stopped')])
        with mock.patch.object(raw.subprocess,'Popen') as spawn:
            with self.assertRaises(raw.RawCaptureError):self.run_ssh(found,plan,guard=guard)
        spawn.assert_not_called()
        handle=raw.load_handle(self.out/'ssh.capture.json')
        self.assertIsNone(handle.returncode);self.assertEqual(handle.producer_error_type,'SessionError')
        self.assertEqual(raw.read_stdout(handle,maximum=1024),b'')

    def test_base_ready_false_never_creates_an_ssh_attempt(self):
        found,plan=self.setup_ssh('raise RuntimeError("must not run")')
        with mock.patch.object(raw,'acquire_command') as acquire,self.assertRaises(ValueError):
            access.capture_ssh(self.out,self.manifest,plan,found,{'ssh_ready':False,'boot_id':BOOT},
                deadline_ns=records.clock()+10_000_000_000,guard=lambda:None)
        acquire.assert_not_called();self.assertFalse((self.out/'ssh-intent.json').exists())

    def test_guard_consumes_window_without_starting_an_expired_client(self):
        found,plan=self.setup_ssh('raise RuntimeError("must not run")')
        original=time.clock_gettime_ns;offset=0;calls=0
        def guard():
            nonlocal offset,calls
            calls+=1
            if calls==2:offset=3_000_000_000
        with mock.patch.object(time,'clock_gettime_ns',side_effect=lambda clock:original(clock)+offset), \
             mock.patch.object(raw.subprocess,'Popen') as spawn:
            with self.assertRaises(raw.RawCaptureError):self.run_ssh(found,plan,seconds=6,guard=guard)
        spawn.assert_not_called();self.assertEqual(calls,2)
        handle=raw.load_handle(self.out/'ssh.capture.json')
        self.assertIsNone(handle.returncode);self.assertEqual(handle.producer_error_type,'RawCaptureError')
        self.assertEqual(raw.read_stdout(handle,maximum=1024),b'')
        self.assertTrue((self.out/'ssh-complete.json').exists())

    def test_delayed_guard_clips_acquisition_to_absolute_deadline(self):
        found,plan=self.setup_ssh('import signal,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                                  'sys.stdout.write("partial");sys.stdout.flush();time.sleep(5)')
        original=time.clock_gettime_ns;offset=0;calls=0;started=time.monotonic()
        def guard():
            nonlocal offset,calls
            calls+=1
            if calls==2:offset=21_750_000_000
        with mock.patch.object(time,'clock_gettime_ns',side_effect=lambda clock:original(clock)+offset):
            with self.assertRaises(raw.RawCaptureError):self.run_ssh(found,plan,seconds=26.502,guard=guard)
        self.assertLess(time.monotonic()-started,4);self.assertEqual(calls,2)
        self.assertEqual(records.read(self.out/'ssh-intent.json')['timeout_seconds'],20.0)
        handle=raw.load_handle(self.out/'ssh.capture.json');self.assertTrue(handle.timed_out)
        self.assertEqual(handle.returncode,-9);self.assertIsNone(handle.producer_error_type)
        self.assertEqual(raw.read_stdout(handle,maximum=1024),b'partial')
        self.assertFalse((self.out/'usb-after-ssh.capture.json').exists())
        with mock.patch.object(raw.subprocess,'Popen') as spawn:
            with self.assertRaises((raw.RawCaptureError,FileExistsError)):self.run_ssh(found,plan)
        spawn.assert_not_called()

    def test_shorter_intent_budget_survives_more_than_initial_margin(self):
        found,plan=self.setup_ssh(f'import sys;sys.stdout.buffer.write({OUTPUT!r})')
        original=time.clock_gettime_ns;offset=0;calls=0
        def guard():
            nonlocal offset,calls
            calls+=1
            if calls==2:offset=500_000_000
        with mock.patch.object(time,'clock_gettime_ns',side_effect=lambda clock:original(clock)+offset):
            result=self.run_ssh(found,plan,seconds=14,guard=guard)
        self.assertEqual(result['uid'],1000);self.assertEqual(calls,2)
        timeout=records.read(self.out/'ssh-intent.json')['timeout_seconds']
        self.assertLess(timeout,10);self.assertGreater(timeout,9)

    def test_delayed_guard_real_producer_to_offline_rederivation_and_endpoint_tamper(self):
        found,plan=self.setup_ssh(f'import sys;sys.stdout.buffer.write({OUTPUT!r})')
        opened=records.clock();deadline=opened+26_502_000_000
        proof={'ssh_ready':True,'boot_id':BOOT}
        records.publish(self.out/'window.json',dict(host_boot=records.host_boot(),deadline_ns=deadline))
        records.publish(self.out/'endpoint.json',found)
        records.publish(self.out/'connection.json',dict(finished_ns=opened))
        original=time.clock_gettime_ns;offset=0;calls=0
        def guard():
            nonlocal offset,calls
            calls+=1
            if calls==2:offset=3_558_000_000
        with mock.patch.object(time,'clock_gettime_ns',side_effect=lambda clock:original(clock)+offset):
            access.capture_ssh(self.out,self.manifest,plan,found,proof,deadline_ns=deadline,guard=guard)
        self.assertEqual(calls,2)
        self.assertEqual(records.read(self.out/'ssh-intent.json')['timeout_seconds'],20.0)
        adapter=mock.Mock();adapter.folder.return_value=self.out;adapter.configuration.return_value={'mainline_access':plan}
        with mock.patch.object(access,'rederive_base',return_value={'proof':proof}), \
             mock.patch.object(profile,'image_binding',return_value=self.manifest), \
             mock.patch.object(raw,'acquire_command',side_effect=AssertionError('offline must not acquire')):
            value=access.rederive(adapter,{'N':{}})
            self.assertEqual(value['ssh']['uid'],1000)
            self.assertEqual(value['ssh_capture'],records.pin(self.out/'ssh.capture.json'))
            path=self.out/'ssh-intent.json';data=json.loads(path.read_text());data['endpoint']['ifindex']+=1
            path.chmod(0o600);path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):access.rederive(adapter,{'N':{}})


class SSHRecoveryTests(unittest.TestCase):
    setUp=live.harness.OwnerTests.setUp
    operation=live.OwnerTests.operation

    def test_missing_ssh_candidate_dependency_still_recovers_original_a_once(self):
        import builtins
        owner,device=self.operation()
        self.assertEqual(owner.execute(attended=True)['state'],'AWAITING_PHYSICAL_DOWNLOAD')
        device.mode='Download';original=builtins.__import__;recover=device.recover_step_result;attempts=[]
        def missing(name,globals=None,locals=None,fromlist=(),level=0):
            if 'ssh_ram' in (fromlist or ()):attempts.append(name);raise ImportError('SSH checker absent')
            return original(name,globals,locals,fromlist,level)
        def recover_proof(step,request):
            if step.name==profile.SELECTION:
                profile.debian_ram_binding({}, {'debian_ram':{'schema':ssh_ram.SCHEMA}}, {}, {})
            return recover(step,request)
        with mock.patch.object(task,'capability',return_value={}), \
             mock.patch('builtins.__import__',side_effect=missing), \
             mock.patch.object(device,'recover_step_result',side_effect=recover_proof):
            result=owner.recover(attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED');self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('mainline-request-once'),1);self.assertEqual(len(attempts),1)


if __name__=='__main__':unittest.main()
