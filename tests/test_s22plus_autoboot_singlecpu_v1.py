"""Actual ARM64 sampling, exact boot arguments and authenticated proof limits."""
import errno
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from test_s22plus_autoboot_watchdog_selection import IdleHeader,boot_image
import s22plus_boot_verify as boot
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_evidence_v1 as evidence
import test_s22plus_debian_evidence_v1 as fixture
import s22plus_debian_autoboot_access_v1 as access

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/name) for name in (
    'workspace/public/src/debian/s22plus_initramfs_h0','workspace/public/src/scripts/analysis')]


class SingleCPUHeader(IdleHeader):
    def setUp(self):
        super().setUp()
        self.selected['transition_observer']=profile.SINGLECPU_OBSERVER
        self.selected['cpu_policy']=profile.SINGLECPU_POLICY

    def test_only_selected_command_line_bytes_change(self):
        original=boot_image('console=tty0');actual=self.select(original)
        self.assertEqual(actual[:44]+actual[1580:],original[:44]+original[1580:])
        self.assertEqual(boot.parse_boot_v4(actual).header['cmdline'],
            'console=tty0 cpuidle.off=1 maxcpus=1')

    def test_default_and_legacy_carriers_are_byte_identical(self):
        # The new candidate has one fixed idle/CPU choice, not a new matrix.
        with self.assertRaises(ValueError):
            self.select(boot_image(),dict(self.selected,idle_policy='retained-default'))
        self.assertEqual(profile.boot_carrier(boot_image(),{}),boot_image())

    def test_conflicting_cpu_options_and_init_separator_reject(self):
        for token in ('maxcpus=0','maxcpus=1','maxcpus=8','nr_cpus=1','nosmp','--'):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):self.select(boot_image(token))
                with self.assertRaises(ValueError):self.select(boot_image(),vendor=token)
        for invalid in ('maxcpus-8','nosmp'):
            with self.assertRaises(ValueError):self.select(boot_image(),dict(self.selected,cpu_policy=invalid))
        with self.assertRaises(ValueError):
            self.select(boot_image(),dict(self.selected,transition_observer=profile.PHASE_OBSERVER))

    def test_current_history_is_selected_without_phase_instrumentation(self):
        with mock.patch.object(profile,'history',return_value={'path':'old'}), \
             mock.patch.object(profile,'additional_history',return_value={'path':'second'}), \
             mock.patch.object(profile,'runtime_history',return_value={'path':'runtime'}), \
             mock.patch.object(profile,'watchdog_history',return_value=[{'path':'p437e'},{'path':'p437r'}]), \
             mock.patch.object(profile,'phase_history',return_value=[{'path':'p441e'},{'path':'p441r'}]):
            history=profile.histories(True,True,True,False,True)
            self.assertEqual([r['path'] for r in history],['old','second','runtime','p437e','p437r','p441e','p441r'])
            self.assertFalse(profile.phase_selected(self.selected))
            self.assertTrue(profile.singlecpu_selected(self.selected))
            with self.assertRaises(ValueError):profile.histories(True,True,True,True,True)

    def test_maxcpus_is_a_kernel_argument(self):
        import autoboot_vm
        kernel,initial=autoboot_vm.kernel_command_line(self.selected).split(' -- ',1)
        self.assertEqual(kernel.split().count('maxcpus=1'),1)
        self.assertEqual(initial,autoboot_vm.vm.KERNEL_COMMAND_LINE.split(' -- ',1)[1])


class ActualARM64Sampler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temporary.cleanup)
        cls.binary=Path(cls.temporary.name)/'sampler'
        subprocess.run(['aarch64-linux-gnu-gcc','-static','-Os','-Wall','-Wextra','-Werror',
            '-I',str(ROOT/'workspace/public/src/native-init'),
            str(ROOT/'tests/s22plus_autoboot_singlecpu_harness.c'),'-o',str(cls.binary)],check=True,capture_output=True)
        cls.file=subprocess.check_output(['file',cls.binary],text=True)

    def observe(self,first='0\n',disable='0\n',last='0\n'):
        return tuple(map(int,subprocess.check_output(
            ['qemu-aarch64',self.binary,first,disable,last],text=True,timeout=5).split()))

    def test_real_compiled_parser_records_software_state_only(self):
        self.assertIn('ARM aarch64',self.file)
        self.assertEqual(self.observe(),(0,257,2))

    def test_hotplug_at_either_end_and_unarmed_watchdog_are_rejected(self):
        for changed in (dict(first='0-7\n'),dict(first='1\n'),dict(last='0-1\n'),
                dict(disable='1\n')):
            with self.subTest(changed=changed):
                error,value,_=self.observe(**changed)
                self.assertEqual((error,value),(errno.EPROTO,0))

    def test_missing_and_malformed_driver_attributes_never_pass(self):
        for key in ('first','disable','last'):
            with self.subTest(key=key):
                self.assertEqual(self.observe(**{key:'MISSING'})[:2],(errno.ENOENT,0))
        for value in ('','00\n','0','0\nx','-1\n','1\n','9999999\n'):
            with self.subTest(value=value):
                error,record,_=self.observe(disable=value)
                self.assertNotEqual(error,0);self.assertEqual(record,0)


def encoded(rows,revision=6):
    header=bytearray(fixture.header());struct.pack_into('<QQI',header,96,0,300000,revision)
    header[224:]=evidence.tag(fixture.KEY,header[:224],autoboot=True)
    raw=bytearray(header);previous=bytes(header[224:])
    for seq,row in enumerate(rows):
        r=bytearray(128);r[:8]=b'S22DER1\0'
        kind,elapsed,phase,event,a,b,c=row
        struct.pack_into('<IIQIIQQQII',r,8,seq,kind,elapsed,phase,event,a,b,c,0,0)
        r[64:96]=previous;r[96:]=evidence.tag(fixture.KEY,r[:96],autoboot=True)
        previous=bytes(r[96:]);raw+=r
    return bytes(raw)


class DurableSelection(unittest.TestCase):
    def rows(self):
        return [r[:-1]+(257,) if r[0]==evidence.PROGRESS else r
            for r in fixture.events() if r[0]!=evidence.RELEASE]

    def decode(self,data,**kw):
        return evidence.decode(data,fixture.KEY,fixture.EXPECTED,autoboot=True,single_cpu=True,**kw)

    def test_full_realistic_chain_preserves_proof_limits(self):
        result=self.decode(encoded(self.rows()))
        self.assertTrue(result['local_runtime_proved'])
        self.assertEqual(result['single_cpu']['sample_count'],15)
        self.assertTrue(result['single_cpu']['service_window_120_seconds'])
        self.assertFalse(result['single_cpu']['hardware_pet_proved'])
        self.assertFalse(result['single_cpu']['continuous_cpu_online_proved'])

    def test_missing_disabled_or_reserved_sensor_bits_fail_authenticated_chain(self):
        for bad in (0,1,256,258,65537,(11000<<32)|257):
            rows=self.rows();rows[2]=rows[2][:-1]+(bad,)
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.decode(encoded(rows))

    def test_revision_downgrade_or_incomplete_tail_cannot_claim_success(self):
        with self.assertRaises(ValueError):self.decode(encoded(self.rows(),5))
        with self.assertRaises(ValueError):
            evidence.decode(encoded(self.rows()),fixture.KEY,fixture.EXPECTED,autoboot=True)
        result=self.decode(encoded(self.rows()[:-1]))
        self.assertFalse(result['local_runtime_proved'])
        self.assertFalse(result['single_cpu']['service_window_120_seconds'])

    def test_later_online_mask_change_is_not_one_stable_configuration(self):
        rows=self.rows()
        index=next(i for i,row in enumerate(rows) if row[0]==evidence.PROGRESS and row[2]==2)
        rows[index]=rows[index][:-1]+(259,)
        with self.assertRaises(ValueError):self.decode(encoded(rows))

    def test_post_return_reader_selects_the_new_revision_explicitly(self):
        import s22plus_debian_autoboot_retrieval_v1 as retrieval
        selected=dict(run_id=fixture.RUN.hex(),installed_init={'sha256':fixture.EXPECTED['init_sha256']},
            hook={'sha256':fixture.EXPECTED['hook_sha256']},transition_observer=profile.SINGLECPU_OBSERVER,
            cpu_policy=profile.SINGLECPU_POLICY,idle_policy='cpuidle-off')
        proof=retrieval.runtime_prefix(encoded(self.rows()),fixture.KEY,selected)['proof']
        self.assertTrue(proof['single_cpu']['service_window_120_seconds'])
        self.assertFalse(proof['ssh_access_proved'])


class SSHInterval(unittest.TestCase):
    def pair(self,first,last,count=3,online=b'S22_SINGLECPU_ONLINE 0\n'):
        first=online+first;last=online+last
        a=SimpleNamespace(output=first,count=3);b=SimpleNamespace(output=last,count=count)
        def health(handle,plan,**kwargs):
            self.assertEqual(kwargs,dict(boot_sha256='same-boot',autoboot=True))
            return dict(boot_count=handle.count,capture={'sha256':'bound'})
        with mock.patch.object(access.access,'health_projection',side_effect=health), \
             mock.patch.object(access.access.raw,'read_stdout',side_effect=lambda h,**kw:h.output):
            return access.singlecpu_health_pair(a,b,{},'same-boot')

    def test_two_sampled_responses_are_not_a_continuous_connection(self):
        result=self.pair(b'S22_SINGLECPU_UPTIME 12.34\n',b'S22_SINGLECPU_UPTIME 132.34\n')
        self.assertEqual(result['status'],'PASS_SAME_BOOT_SSH_120_SECONDS')
        self.assertFalse(result['continuous_connection_proved'])

    def test_short_missing_duplicate_out_of_deadline_or_changed_count_rejects(self):
        first=b'S22_SINGLECPU_UPTIME 12.34\n'
        for bad in (b'S22_SINGLECPU_UPTIME 132.33\n',b'',b'S22_SINGLECPU_UPTIME 132.34\n'*2,
                b'S22_SINGLECPU_UPTIME 300.00\n',b'S22_SINGLECPU_UPTIME 132.3\n'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.pair(first,bad)
        with self.assertRaises(ValueError):
            self.pair(first,b'S22_SINGLECPU_UPTIME 132.34\n',count=4)
        for online in (b'',b'S22_SINGLECPU_ONLINE 0-1\n',b'S22_SINGLECPU_ONLINE 0\n'*2):
            with self.subTest(online=online),self.assertRaises(ValueError):
                self.pair(first,b'S22_SINGLECPU_UPTIME 132.34\n',online=online)


if __name__=='__main__':unittest.main()
