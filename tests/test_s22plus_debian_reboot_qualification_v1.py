"""Rejection semantics and actual zero-exit fixture diagnostic failures."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
for relative in ('workspace/public/src/scripts/revalidation','workspace/public/src/scripts/analysis',
        'workspace/public/src/debian/s22plus_initramfs_h0'):
    sys.path.insert(0,str(ROOT/relative))
import s22plus_debian_reboot_qualification_v1 as qualification
import reboot_vm_faults as faults

class RejectionTests(unittest.TestCase):
    def test_dirty_observation_completion_is_not_root_admission(self):
        dirty=b'JR1_SKIP clean=0\r\nRI1_RESULT complete=1 stage=10 errno=0 cleanup_errno=0 partition_ro=1 clean=0 mounted=0 unmounted=0\r\n'
        self.assertTrue(qualification.rejection(dirty,'dirty'))
        for data in (dirty.replace(b'clean=0',b'clean=1'),dirty.replace(b'partition_ro=1',b'partition_ro=0'),
                dirty.replace(b'mounted=0',b'mounted=1'),dirty+dirty):
            with self.assertRaises(ValueError):qualification.rejection(data,'dirty')
        with self.assertRaises(ValueError):qualification.rejection(dirty,'prior-runtime-incomplete')
    def test_error_requires_complete_terminal_and_protected_cleanup(self):
        error=b'RI1_RESULT complete=0 stage=8 errno=71 cleanup_errno=0 partition_ro=1 clean=1 mounted=1 unmounted=1\n'
        self.assertTrue(qualification.rejection(error,'prior-runtime-incomplete'))
        for data in (error.replace(b'errno=71',b'errno=0'),error.replace(b'cleanup_errno=0',b'cleanup_errno=5'),
                error.replace(b'unmounted=1',b'unmounted=0'),error[:-2]):
            with self.assertRaises(ValueError):qualification.rejection(data,'prior-runtime-incomplete')
    def test_zero_exit_debugfs_diagnostic_is_not_a_successful_fixture(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name)
            def run(native,out,label,command):
                (out/(label+'.stderr')).write_bytes(b'debugfs 1.47.2 (1-Jan-2025)\nValue exceeds field mode maximum\n')
            with mock.patch.object(faults.automatic.vm.fixture,'debug',side_effect=run),self.assertRaises(ValueError):
                faults.debug(out/'regular.img',out,'bad-mode','set_inode_field /marker mode 100644')
    def test_only_exact_absence_is_allowed_for_expected_lookup(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name)
            def run(native,out,label,command):
                (out/(label+'.stderr')).write_bytes(b'debugfs 1.47.2 (1-Jan-2025)\nrm: File not found by ext2_lookup while trying to resolve filename\n')
            with mock.patch.object(faults.automatic.vm.fixture,'debug',side_effect=run):
                faults.debug(out/'regular.img',out,'absent','rm /marker')
                with self.assertRaises(ValueError):faults.debug(out/'regular.img',out,'writer','write file /marker')

if __name__=='__main__':unittest.main()
