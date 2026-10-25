"""Cron source/phase joins and narrow candidate selection; ARM64 tests are separate."""
import hashlib
import hmac
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_cron_v1 as cron
import s22plus_debian_autoboot_profile_v1 as profile


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.key=b'K'*32;self.run='01'*16;self.boot='02'*32;self.nonce=b'N'*32;self.hook='03'*32
        self.programs={name:dict(size=100+i,sha256=hashlib.sha256(name.encode()).hexdigest())
            for i,name in enumerate(('cron','sshd'))}
        self.patch=patch.object(cron,'programs',return_value=self.programs);self.patch.start();self.addCleanup(self.patch.stop)

    def record(self,**changes):
        data=bytearray(cron.SIZE);data[:8]=b'S22CR01\0';struct.pack_into('<II',data,8,1,cron.SIZE)
        data[16:32]=bytes.fromhex(self.run);data[32:64]=bytes.fromhex(self.boot);data[64:96]=self.nonce
        values=dict(root_device=123,phase=1,baseline=22,installed_count=24,armed_ms=12000,job_ms=40000,
            hash_completed_ms=40010,initial_pid=100,started_pid=101,restarted_pid=102,job_pid=110,parent_pid=109,
            restarted_ticks=120,cron_size=100,sshd_size=101,stop_ms=10000,start_ms=11000,restart_ms=12000,
            ancestor_count=2,initial_ticks=100,started_ticks=110)
        values.update(changes)
        for name,offset,kind in cron.FIELDS:struct.pack_into('<'+kind,data,offset,values[name])
        data[192:224]=bytes.fromhex(self.programs['cron']['sha256']);data[224:256]=bytes.fromhex(self.programs['sshd']['sha256'])
        data[256:288]=bytes.fromhex(self.hook)
        return self.sign(data)

    def sign(self,data):
        data=bytearray(data);data[480:]=hmac.digest(self.key,cron.DOMAIN+b'\x01'+data[:480],'sha256');return bytes(data)

    def decode(self,data,**overrides):
        args=dict(key=self.key,run=self.run,boot=self.boot,nonce=self.nonce,root_device=dict(major=0,minor=123),hook_sha256=self.hook,baseline=22)
        args.update(overrides);return cron.decode(data,**args)

    def test_authenticated_workload_binds_first_boot_not_second_phase(self):
        result=self.decode(self.record());self.assertEqual(result['status'],'PASS_CRON_WORKLOAD')
        self.assertFalse(result['persistent_configuration_proved']);self.assertFalse(result['package_installation_proved'])
        for change in ({'phase':2},{'installed_count':26},{'baseline':23},{'root_device':124}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.decode(self.record(**change))

    def test_valid_tag_does_not_replace_lifecycle_and_deadline_semantics(self):
        for change in ({'initial_pid':101},{'job_pid':102},{'parent_pid':1},{'restarted_ticks':0},
                {'ancestor_count':0},{'ancestor_count':7},{'hash_completed_ms':300000},{'start_ms':5000},{'armed_ms':50000}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.decode(self.record(**change))

    def test_cross_source_nonce_boot_key_and_hook_are_rejected(self):
        for change in ({'run':'04'*16},{'boot':'05'*32},{'nonce':b'X'*32},{'key':b'X'*32},{'hook_sha256':'06'*32}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.decode(self.record(),**change)
        for device in (123,{'major':0,'minor':124},{'major':False,'minor':123}):
            with self.subTest(device=device),self.assertRaises(ValueError):self.decode(self.record(),root_device=device)

    def test_noncanonical_or_partial_output_is_rejected(self):
        original=self.record()
        for data in (original[:-1],original+b'X',original[:-1]+bytes([original[-1]^1])):
            with self.assertRaises(ValueError):self.decode(data)
        for index in (116,332,352,479,192):
            data=bytearray(original);data[index]^=1
            with self.subTest(index=index),self.assertRaises(ValueError):self.decode(self.sign(data))

    def test_retained_p458_selection_is_not_relabelled_as_cron(self):
        old=dict(transition_observer=profile.REBOOT_OBSERVER)
        self.assertTrue(profile.reboot_selected(old));self.assertFalse(profile.cron_selected(old))
        selected=dict(transition_observer=profile.CRON_OBSERVER)
        self.assertTrue(profile.reboot_selected(selected));self.assertTrue(profile.cron_selected(selected))
        self.assertEqual(cron.declaration(self.run)['maximum_disk_creations'],1)
        self.assertNotEqual(profile.CRON_OBSERVER,profile.REBOOT_OBSERVER)


class FactoryTests(unittest.TestCase):
    def test_ordinary_task_entry_loads_frozen_corpus_decoder_without_build_path(self):
        script = '''
from pathlib import Path
import importlib, socket, subprocess, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
def deny(*args, **kwargs): raise AssertionError('import/decoder test cannot acquire effects')
with patch.object(subprocess, 'Popen', deny), patch.object(socket, 'socket', deny):
    import s22plus_native_task_v3 as task
    import device_action_raw_capture_v1 as raw
    with patch.object(raw, 'acquire_command', deny):
        import cron_vm_faults
        assert Path(cron_vm_faults.__file__).resolve() == Path(sys.argv[2])
        before = list(sys.path)
        importlib.reload(task)
        assert sys.path == before
        assert cron_vm_faults.validate_serial(
            b'CRON_RAM_REVOKE claim_errno=0 ready_errno=0 schedule_errno=0\\n'
            b'DHVM_HOOK_PARK errno=2\\n', 'cron-no-job')
'''
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([sys.executable, '-I', '-c', script,
                str(ROOT/'workspace/public/src/scripts/revalidation'),
                str(ROOT/'workspace/public/src/debian/s22plus_initramfs_h0/cron_vm_faults.py')],
                cwd=temporary, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_actual_two_boot_constructor_and_fixed_steps(self):
        import s22plus_debian_access_v1 as access
        import s22plus_debian_reboot_access_v1 as reboot_access
        import s22plus_native_session_v3 as owner
        from s22plus_native_records_v3 import pin,publish
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run='07'*16
            publish(root/'grant.json',dict(fixture=True))
            for namespace,observer in (('p458',profile.REBOOT_OBSERVER),('p459',profile.CRON_OBSERVER)):
                built=dict(run_id=run,transition_observer=observer,reboot=cron.reboot.declaration(run,22))
                publish(root/(namespace+'-build.json'),built)
                publish(root/(namespace+'-artifact.json'),dict(build=pin(root/(namespace+'-build.json'))))
                request=dict(operation='debian-autoboot',N=dict(namespace=namespace,version='fixture',
                    run_id_hex=run,autoboot_boot=pin(root/(namespace+'-artifact.json'))),grant=pin(root/'grant.json'))
                adapter=types.SimpleNamespace(configuration=lambda request:dict(debian_access={}))
                steps=owner.operation_steps(request)
                self.assertEqual([s.name for s in steps],['android-download','install-native-first',
                    'debian-health','debian-reboot','debian-health-second','debian-shutdown','install-android','android-final'])
                for step,phase in (('debian-health',1),('debian-reboot',1),('debian-health-second',2),('debian-shutdown',2)):
                    with self.subTest(namespace=namespace,step=step):
                        selected=access.access_for(adapter,request,step)
                        self.assertIsInstance(selected,reboot_access.Access)
                        self.assertEqual(selected.reboot_phase,phase)
                        self.assertEqual(selected.health_step,'debian-health' if phase==1 else 'debian-health-second')
                for phase in (0,3,True,None):
                    with self.assertRaises(ValueError):reboot_access.Access(adapter,request,phase=phase)


if __name__=='__main__':unittest.main()
