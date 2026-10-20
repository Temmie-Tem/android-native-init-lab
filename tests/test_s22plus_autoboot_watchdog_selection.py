"""Exact idle header and closed historical-file selection; no device calls."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_boot_verify as boot
import s22plus_debian_autoboot_profile_v1 as profile
from s22plus_native_records_v3 import pin


def boot_image(command=''):
    data=bytearray(8192);data[:8]=b'ANDROID!'
    struct.pack_into('<4I',data,8,16,0,0,1584)
    struct.pack_into('<I',data,40,4)
    data[44:1580]=command.encode().ljust(1536,b'\0')
    data[4096:4112]=bytes(range(16))
    return bytes(data)


def vendor_image(command=''):
    data=bytearray(4096);data[:8]=b'VNDRBOOT'
    struct.pack_into('<5I',data,8,4,4096,0,0,0)
    data[28:2076]=command.encode().ljust(2048,b'\0')
    struct.pack_into('<I',data,2096,2128)
    struct.pack_into('<4I',data,2112,0,0,108,0)
    return bytes(data)


class IdleHeader(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.folder=Path(temp.name)
        self.selected=dict(transition_observer=profile.WATCHDOG_OBSERVER,idle_policy='cpuidle-off')

    def select(self,original,selected=None,vendor=''):
        path=self.folder/'vendor.img';path.write_bytes(vendor_image(vendor))
        with mock.patch.object(profile,'IDLE_VENDOR_BOOT',pin(path)):
            return profile.boot_carrier(original,self.selected if selected is None else selected)

    def test_only_selected_command_line_bytes_change(self):
        for command in ('','console=tty0'):
            original=boot_image(command);actual=self.select(original)
            self.assertEqual(actual[:44]+actual[1580:],original[:44]+original[1580:])
            self.assertEqual(boot.parse_boot_v4(actual).header['cmdline'],
                command+(' ' if command else '')+'cpuidle.off=1')
            self.assertEqual(boot.parse_boot_v4(actual).kernel,boot.parse_boot_v4(original).kernel)

    def test_default_and_legacy_carriers_are_byte_identical(self):
        original=boot_image()
        self.assertEqual(self.select(original,dict(self.selected,idle_policy='retained-default')),original)
        self.assertEqual(profile.boot_carrier(original,{}),original)
        self.assertEqual(profile.boot_carrier(original,dict(transition_observer=profile.RCS_OBSERVER)),original)

    def test_conflicting_boot_and_vendor_idle_options_are_rejected(self):
        for command in ('cpuidle.off=0','cpuidle.off=1','cpuidle.governor=menu','idle=poll'):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):self.select(boot_image(command))
                with self.assertRaises(ValueError):self.select(boot_image(),vendor=command)

    def test_padding_overflow_or_arbitrary_policy_is_rejected(self):
        original=bytearray(boot_image());original[100]=1
        with self.assertRaises(ValueError):self.select(bytes(original))
        with self.assertRaises(ValueError):self.select(boot_image('x'*1530))
        with self.assertRaises(ValueError):self.select(boot_image(),dict(self.selected,idle_policy='idle=poll'))

    def test_legacy_cannot_smuggle_idle_or_history_selection(self):
        for extra in (dict(idle_policy='cpuidle-off'),dict(watchdog_history=[])):
            with self.assertRaises(ValueError):profile.boot_carrier(boot_image(),extra)

    def test_vm_kernel_argument_does_not_change_init_arguments(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('workspace/public/src/debian/s22plus_initramfs_h0','workspace/public/src/scripts/analysis'):
            sys.path.insert(0,str(root/name))
        import autoboot_vm
        original=autoboot_vm.vm.KERNEL_COMMAND_LINE
        self.assertIn(' -- ',original)
        command=autoboot_vm.kernel_command_line(self.selected)
        kernel,initial=command.split(' -- ',1)
        self.assertIn('cpuidle.off=1',kernel.split())
        self.assertEqual(initial,original.split(' -- ',1)[1])
        self.assertEqual(autoboot_vm.kernel_command_line({}),original)


class ClosedPair(unittest.TestCase):
    receipt_name='WATCHDOG_RETRIEVAL'
    select_pair=staticmethod(profile.watchdog_history)

    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.folder=Path(temp.name);self.run='8'*32
        closed=self.save('closed.json',dict(terminal_state='ANDROID_CLOSED_HEALTHY'))
        self.proof=dict(join=dict(status='MATCH',boot_matches=True,nonce_matches=True))
        self.acquired=dict(partition_readonly=True,mounted=False,persistent_writes=False,files=[])
        raw={}
        for kind,prefix,size in (('early','s22-early-',10972),('runtime','s22-evidence-',1024)):
            data=(b'E' if kind=='early' else b'R')*size
            path=self.folder/(kind+'.bin');path.write_bytes(data);raw[kind]=pin(path)
            digest=hashlib.sha256(data).hexdigest()
            proof=dict(raw=dict(size=size,sha256=digest),valid_prefix_bytes=size,
                run_id_hex=self.run,tail_error=None)
            proof.update(dict(pre_unmount_complete=True) if kind=='early' else
                dict(local_init_observed=True,automatic_start=True,complete_framing=True))
            self.proof[kind]=dict(status='AUTHENTICATED',proof=proof)
            self.acquired['files'].append(dict(path='var/lib/lab/'+prefix+self.run,status='READ',
                mode=0o100600,uid=0,gid=0,links=1,size=size,captured=size,offset=0,error=0,
                sha256=digest,raw_hex=data.hex()))
        self.result=dict(schema='s22plus-debian-autoboot-retrieval-h0-v1',
            status='PASS_AUTHENTICATED_LOCAL_PROGRESS',reader_android_healthy=True,
            writer_android_healthy=True,writer_closed=closed,reader_closed=closed,raw=raw)

    def save(self,name,value):
        path=self.folder/name;path.write_text(json.dumps(value));return pin(path)

    def select(self,*,proof=None,acquired=None,result=None):
        value=copy.deepcopy(self.result if result is None else result)
        value['proof']=self.proof if proof is None else proof
        value['reader_result']=self.save('reader.json',dict(proof=dict(
            root_evidence=self.acquired if acquired is None else acquired)))
        with mock.patch.object(profile,self.receipt_name,self.save('retrieval.json',value)):
            return self.select_pair()

    def test_closed_complete_pair_yields_exact_immutable_rows(self):
        rows=self.select()
        self.assertEqual([r['size'] for r in rows],[10972,1024])
        self.assertEqual([r['mode'] for r in rows],[0o100600,0o100600])
        self.assertEqual([r['source'] for r in rows],[self.result['raw'][k] for k in ('early','runtime')])

    def test_metadata_mismatch_or_partial_capture_is_rejected(self):
        for index in range(2):
            for field,value in (('mode',0o100644),('uid',1),('gid',1),('links',2),
                    ('offset',1),('error',5),('captured',100),('path','var/lib/lab/foreign')):
                acquired=copy.deepcopy(self.acquired);acquired['files'][index][field]=value
                with self.subTest(index=index,field=field),self.assertRaises(ValueError):
                    self.select(acquired=acquired)

    def test_boot_join_incomplete_record_and_unhealthy_closure_reject(self):
        for field in ('boot_matches','nonce_matches'):
            proof=copy.deepcopy(self.proof);proof['join'][field]=False
            with self.assertRaises(ValueError):self.select(proof=proof)
        for kind,field,value in (('early','tail_error','truncated'),
                ('runtime','complete_framing',False),('runtime','run_id_hex','9'*32)):
            proof=copy.deepcopy(self.proof);proof[kind]['proof'][field]=value
            with self.assertRaises(ValueError):self.select(proof=proof)
        result=copy.deepcopy(self.result)
        result['reader_closed']=self.save('bad-close.json',dict(terminal_state='AWAITING_ATTENDED_RECOVERY'))
        with self.assertRaises(ValueError):self.select(result=result)

    def test_changed_bytes_cannot_inherit_old_proof_or_acquisition(self):
        for kind in ('early','runtime'):
            path=Path(self.result['raw'][kind]['path']);original=path.read_bytes()
            path.write_bytes(original[:-1]+b'X')
            result=copy.deepcopy(self.result);result['raw'][kind]=pin(path)
            with self.assertRaises(ValueError):self.select(result=result)
            path.write_bytes(original)


class PhaseClosedPair(ClosedPair):
    receipt_name='PHASE_RETRIEVAL'
    select_pair=staticmethod(profile.phase_history)


if __name__=='__main__':unittest.main()
