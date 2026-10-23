"""Protocol joins and the actual H0 no-replay dispatch boundary.

These synthetic negative inputs complement the separate real ARM64 producers.
They do not qualify a physical root or the device-action coordinator.
"""
import hashlib
import hmac
from contextlib import chdir
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/debian/s22plus_reboot_h0'))
import reboot_vm as vm
import reboot_checks as checks


class Decoder(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.key=b'K'*32;self.run='01'*16
        path=Path(self.tmp.name)/'key';path.write_bytes(self.key)
        self.built=dict(run=self.run,key=vm.pin(path))

    def record(self,p,role,base,boot,ms,early=None,previous=None):
        r=bytearray(256);r[:8]=b'S22RBH0\0'
        struct.pack_into('<6I',r,8,1,role,p,base,base+2*p-(role==1),0)
        struct.pack_into('<Q',r,32,ms);r[40:72]=boot
        if early:r[72:104]=hashlib.sha256(early).digest()
        if previous:r[104:136]=hashlib.sha256(previous).digest()
        if role>=3:struct.pack_into('<3Q',r,136,1,20,30)
        r[160:176]=bytes.fromhex(self.run);r[224:]=hmac.digest(self.key,vm.DOMAIN+r[:224],'sha256')
        return bytes(r)

    def body(self,*,base1=7,base2=7,boot2=b'B'*32,intent=True):
        lines=[]
        for p,base,boot in ((1,base1,b'A'*32),(2,base2,boot2)):
            e=self.record(p,1,base,boot,10)
            r=self.record(p,2,base,boot,20,early=e)
            last=self.record(p,3,base,boot,120020,early=e,previous=r);r+=last
            if p==1 and intent:r+=self.record(p,4,base,boot,120021,early=e,previous=last)
            lines += [f'P458_FILE phase={p} kind=early data={e.hex()}',
                      f'P458_FILE phase={p} kind=runtime data={r.hex()}']
        return (f'P458_HEALTH phase=2 base={base2} boot={boot2.hex()} uptime_ms=120050 init_pid=1 cron_pid=20 sshd_pid=30\n'+
                '\n'.join(lines)+'\n').encode()

    def test_valid_two_phase_join(self):
        result=vm.parse_health(self.body(),self.built)
        self.assertEqual(result['phase'],2)
        self.assertEqual(result['records']['b1-runtime'][-1]['role'],4)

    def test_phase_relationship_rejections(self):
        cases=[self.body(base2=8),self.body(boot2=b'A'*32),self.body(intent=False),self.body(base1=65532,base2=65532)]
        for body in cases:
            with self.subTest(body=hashlib.sha256(body).hexdigest()),self.assertRaises(ValueError):
                vm.parse_health(body,self.built)

    def test_live_summary_is_not_an_independent_authority(self):
        cases={b'base=7':b'base=999',b'uptime_ms=120050':b'uptime_ms=300000',
               b'uptime_ms=120050 ':b'uptime_ms=1 ',b'cron_pid=20':b'cron_pid=0',
               b'sshd_pid=30':b'sshd_pid=20',b'cron_pid=20 sshd_pid=30':b'cron_pid=020 sshd_pid=20',
               b'cron_pid=20 ':b'cron_pid=21 '}
        for old,new in cases.items():
            with self.subTest(new=new),self.assertRaises(ValueError):
                vm.parse_health(self.body().replace(old,new,1),self.built)

    def test_corrupt_partial_and_duplicate_file_rejected(self):
        body=self.body();lines=body.splitlines();file=lines[1]
        corrupt=file[:-1]+(b'0' if file[-1:]!=b'0' else b'1')
        cases=[body.replace(file,corrupt,1),body.replace(file,file[:-2],1),body+file+b'\n',body+lines[0]+b'\n']
        for data in cases:
            with self.subTest(length=len(data)),self.assertRaises(ValueError):vm.parse_health(data,self.built)


class Control(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)

    def test_uncertain_command_is_not_retransmitted(self):
        class Guest:
            calls=0
            def ssh(self,*args,**kwargs):self.calls+=1;raise TimeoutError('transport uncertain')
        guest=Guest()
        with self.assertRaises(TimeoutError):vm.once_control(guest,self.out,'reboot','test-boot')
        self.assertEqual(json.loads((self.out/'reboot-intent.json').read_text())['command'],'reboot')
        with self.assertRaises(FileExistsError):vm.once_control(guest,self.out,'reboot','test-boot')
        self.assertEqual(guest.calls,1)

    def test_parent_sync_failure_prevents_transmission(self):
        class Guest:
            calls=0
            def ssh(self,*args,**kwargs):self.calls+=1
        guest=Guest();real=vm.shared.os.fsync;calls=[]
        def fail_directory(fd):
            calls.append(fd)
            if len(calls)==2:raise OSError('injected directory fsync failure')
            return real(fd)
        with patch.object(vm.shared.os,'fsync',side_effect=fail_directory),self.assertRaises(OSError):
            vm.once_control(guest,self.out,'shutdown','test-boot')
        self.assertEqual(guest.calls,0)
        self.assertTrue((self.out/'shutdown-intent.json').is_file())
        with self.assertRaises(FileExistsError):vm.once_control(guest,self.out,'shutdown','test-boot')
        self.assertEqual(guest.calls,0)

    def test_unselected_control_has_no_intent(self):
        with self.assertRaises(ValueError):vm.once_control(None,self.out,'arbitrary','test-boot')
        self.assertEqual(list(self.out.iterdir()),[])

    def test_failed_diagnostic_preserves_primary_failure(self):
        with patch.object(vm,'superblock',side_effect=OSError('unreadable disk')):
            failure=vm.failure_diagnostic(ValueError('primary parser failure'),self.out/'disk')
        vm.save(self.out/'failure.json',failure)
        reopened=json.loads((self.out/'failure.json').read_text())
        self.assertEqual(reopened['error'],'primary parser failure')
        self.assertIsNone(reopened['final_super'])
        self.assertEqual(reopened['super_diagnostic_error']['type'],'OSError')

    def test_actual_ssh_factory_supplies_string_arguments(self):
        fake=self.out/'pinned';fake.write_bytes(b'fixture')
        receipt=vm.pin(fake)
        guest=object.__new__(vm.Guest)
        guest.out=self.out;guest.ordinal=0;guest.port=12345
        guest.built={'plan':dict(ssh=receipt,client_key=receipt,known_hosts=receipt,
                                link=dict(ssh_address='192.0.2.1'))}
        def capture(args,*positional,**keyword):
            self.assertTrue(all(isinstance(arg,str) for arg in args))
            self.assertEqual(args[-2:],["root@127.0.0.1","health"])
            return 'captured-without-execution'
        with patch.object(vm.raw,'acquire_command',side_effect=capture):
            self.assertEqual(guest.ssh('health','factory'),'captured-without-execution')

    def test_relative_pin_roundtrips_through_original_consumer(self):
        fake=self.out/'pinned';fake.write_bytes(b'fixture')
        with chdir(self.out):
            receipt=vm.pin(Path('pinned'))
        self.assertEqual(receipt['path'],str(fake))
        self.assertEqual(vm.verify(receipt),fake)

    def test_debugfs_version_stderr_is_accepted_but_error_is_not(self):
        for ordinal,stderr in enumerate((b'debugfs 1.47.2 (1-Jan-2025)\n',
                b'debugfs 1.47.2 (1-Jan-2025)\nwrite: File not found\n')):
            handle=vm.raw.publish_captured_bytes(self.out,'debug-'+str(ordinal),
                stdout=b'',stderr=stderr,returncode=0)
            with patch.object(checks,'regular'),patch.object(checks.raw,'acquire_command',return_value=handle):
                if ordinal:
                    with self.assertRaisesRegex(ValueError,'diagnostics differ'):
                        checks.debug('disk',self.out,'debug','unused')
                else:self.assertEqual(checks.debug('disk',self.out,'debug','unused'),vm.pin(handle.receipt_path))


if __name__=='__main__':unittest.main()
