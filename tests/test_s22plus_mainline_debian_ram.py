"""Distinct Debian wire proof, fixed RAM package boundary and real raw capture."""
import copy
import hashlib
from pathlib import Path
import struct
import subprocess
import unittest

import test_s22plus_mainline_canary_h0 as canary
import test_s22plus_mainline_live_v1 as live
import debian_ram
import verify


class DebianWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        canary.CanaryTests.setUpClass()
        cls.fixture=canary.CanaryTests()
        cls.codec=cls.fixture.base/'debian-codec'
        subprocess.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-DCANARY_DEBIAN_RAM',
            canary.ROOT/'tests/s22plus_mainline_protocol_fixture.c','-o',cls.codec],check=True)

    @classmethod
    def tearDownClass(cls):
        canary.CanaryTests.tearDownClass()

    def manifest(self):
        value=copy.deepcopy(self.fixture.manifest)
        value['debian_ram']=dict(schema=debian_ram.SCHEMA,
            observer={'sha256':hashlib.sha256(b'fixture-child').hexdigest()},
            inittab_sha256=hashlib.sha256(debian_ram.INITTAB).hexdigest())
        return value

    def body(self):
        body=self.fixture.body()+bytearray(96);body[:8]=b'G0QDRS1\0'
        struct.pack_into('<IIIII',body,256,52,1,1,ord('2'),ord('N'))
        body[288:320]=bytes.fromhex(self.manifest()['debian_ram']['observer']['sha256'])
        body[320:352]=hashlib.sha256(debian_ram.INITTAB).digest()
        return body

    def raw(self,body=None):
        body=self.body() if body is None else body
        signed=subprocess.run(['qemu-aarch64',self.codec,'response'],input=body,capture_output=True,check=True).stdout
        self.assertEqual(signed[-32:],verify.tag(self.fixture.key,self.fixture.identity,1,body,manifest=self.manifest()))
        return signed+self.fixture.live.read_bytes()

    def test_actual_arm64_new_domain_and_strict_bidirectional_profile_separation(self):
        f=self.fixture;old=verify.request(f.key,f.identity,f.nonce)
        new=verify.request(f.key,f.identity,f.nonce,manifest=self.manifest())
        for codec,packet,expected in [(self.codec,new,0),(self.codec,old,1),(f.codec,new,1)]:
            self.assertEqual(subprocess.run(['qemu-aarch64',codec,'request'],input=packet).returncode,expected)
        proof=f.check(self.raw(),manifest=self.manifest())
        self.assertEqual(proof['status'],'AUTHENTICATED_DEBIAN_SYSVINIT_RAM_OBSERVATION')
        self.assertEqual((proof['pid'],proof['responder_pid'],proof['responder_ppid']),(1,52,1))
        with self.assertRaises(ValueError):f.check(self.raw())
        with self.assertRaises(ValueError):f.check(f.raw(),manifest=self.manifest())
        wrong=self.manifest();wrong['debian_ram']['schema']='unknown'
        with self.assertRaises(ValueError):f.check(self.raw(),manifest=wrong)

    def test_authenticated_wrong_debian_claims_truncation_and_identity_rejected(self):
        for offset,value in [(256,1),(260,2),(264,0),(268,ord('3')),(272,ord('2')),(276,1)]:
            body=self.body();struct.pack_into('<I',body,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                self.fixture.check(self.raw(body),manifest=self.manifest())
        for offset in (120,288,320):
            body=self.body();body[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                self.fixture.check(self.raw(body),manifest=self.manifest())
        data=self.raw()
        for wrong in (data[:288],data[:-1],data+data,data[:352]+bytes(32)+data[384:]):
            with self.assertRaises(ValueError):self.fixture.check(wrong,manifest=self.manifest())

    def test_real_socket_producer_selects_debian_request_and_seals_full_response(self):
        import tempfile,socket,threading
        from unittest import mock
        import device_action_raw_capture_v1 as raw
        import s22plus_native_records_v3 as records
        import s22plus_mainline_access_v1 as access
        manifest=self.manifest();manifest.update(network={'host_ip':'127.0.0.1','device_ip':'127.0.0.1'},port=1)
        packet=self.raw();requests=[];errors=[]
        with tempfile.TemporaryDirectory(dir=self.fixture.base) as temp:
            folder=Path(temp)
            server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(3)
            address=server.getsockname()
            def serve():
                try:
                    with server.accept()[0] as client:
                        value=b''
                        while len(value)<72:
                            more=client.recv(72-len(value))
                            if not more:break
                            value+=more
                        requests.append(value);client.sendall(packet)
                except Exception as error:errors.append(error)
                finally:server.close()
            worker=threading.Thread(target=serve);worker.start()
            try:
                with mock.patch.object(access.secrets,'token_bytes',return_value=self.fixture.nonce):
                    handle=access.capture_connection(folder,manifest,{'interface':'lo'},guard=lambda:None,
                        deadline_ns=records.clock()+3_000_000_000,connect=lambda client:client.connect(address))
            finally:worker.join(4)
            self.assertFalse(worker.is_alive());self.assertFalse(errors)
            self.assertEqual(requests,[verify.request(self.fixture.key,self.fixture.identity,self.fixture.nonce,manifest=manifest)])
            self.assertEqual(raw.read_stdout(handle,maximum=verify.response_size(manifest)+verify.FDT_LIMIT),packet)
            self.assertEqual(verify.verify_capture(handle,manifest,self.fixture.nonce)['responder_ppid'],1)

    def test_fixed_inittab_excludes_shell_and_newc_has_only_fixed_nodes(self):
        import stat
        import s22plus_boot_verify as boot
        files={n:b'fixture' for n in debian_ram.MEMBERS}
        files[debian_ram.OBSERVER]=b'fixture';files['etc/inittab']=debian_ram.INITTAB
        physical=debian_ram.pack(files,False);vm=debian_ram.pack(files,True)
        rows={r.name:r for r in boot.parse_newc(physical)}
        self.assertEqual(rows['init'].data,b'usr/sbin/init')
        self.assertTrue(stat.S_ISLNK(rows['init'].mode))
        self.assertEqual(rows['etc/inittab'].data.splitlines(),
                         [b'id:2:initdefault:',b'r2:2:once:@/usr/libexec/g0q-ram-observer'])
        self.assertEqual({n for n,r in rows.items() if stat.S_ISCHR(r.mode)},{'dev/console','dev/null'})
        self.assertNotIn('dev/ttyAMA0',rows)
        self.assertIn('dev/ttyAMA0',{r.name for r in boot.parse_newc(vm)})
        files['bin/sh']=b'forbidden'
        with self.assertRaises(ValueError):debian_ram.pack(files,False)


class DebianOwnerTests(unittest.TestCase):
    setUp=live.harness.OwnerTests.setUp
    operation=live.OwnerTests.operation

    def test_missing_candidate_validator_preserves_original_a_only_recovery(self):
        import builtins
        from unittest import mock
        import s22plus_mainline_task_v1 as task
        import s22plus_mainline_profile_v1 as profile
        session,device=self.operation()
        self.assertEqual(session.execute(attended=True)['state'],'AWAITING_PHYSICAL_DOWNLOAD')
        device.mode='Download'
        original=builtins.__import__;recover=device.recover_step_result;attempts=[]
        def missing(name,globals=None,locals=None,fromlist=(),level=0):
            if name=='mainline.s22plus_canary_h0' and 'debian_ram' in fromlist:
                attempts.append(name);raise ImportError('candidate validator absent')
            return original(name,globals,locals,fromlist,level)
        def recover_proof(step,request):
            if step.name==profile.SELECTION:profile.debian_ram_binding({}, {}, {}, {})
            return recover(step,request)
        with mock.patch.object(task,'capability',return_value={'fixture':True}), \
             mock.patch('builtins.__import__',side_effect=missing), \
             mock.patch.object(device,'recover_step_result',side_effect=recover_proof):
            result=session.recover(attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED')
        self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('mainline-request-once'),1)
        self.assertEqual(len(attempts),1)

    def test_debian_terminal_meaning_and_failed_proof_remain_separate(self):
        from unittest import mock
        import s22plus_mainline_session_v1 as mainline
        import s22plus_mainline_access_v1 as access
        request={'N':{'debian_ram':{'fixture':True}}}
        with mock.patch.object(access,'rederive',return_value={'proof':{'status':'AUTHENTICATED_DEBIAN_SYSVINIT_RAM_OBSERVATION'}}):
            result=mainline.terminal(object(),request,recovered=False)
        self.assertEqual(result['status'],'PASS_DEBIAN_SYSVINIT_RAM_PID1')
        self.assertTrue(result['authenticated_usb']);self.assertFalse(result['native_admitted'])
        self.assertFalse(result['automatic_recovery_proved'])
        with mock.patch.object(access,'rederive',side_effect=ValueError('raw proof incomplete')):
            result=mainline.terminal(object(),request,recovered=True)
        self.assertEqual(result['status'],'NO_PROOF')
        self.assertFalse(result['authenticated_usb']);self.assertFalse(result['replay_authorized'])


if __name__=='__main__':unittest.main()
