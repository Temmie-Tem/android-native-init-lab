"""Prospective file candidates are declarative input, validated before build I/O."""
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/debian/s22plus_initramfs_h0'),
    str(ROOT/'workspace/public/src/scripts/revalidation'),str(ROOT/'workspace/public/src/scripts/analysis')]
import file_log


class FileIdentity(unittest.TestCase):
    def test_invalid_or_partial_identity_rejects_before_file_preparation(self):
        invalid=((None,'v0.8.0-rc.1'),('p987',None),('../p987','v0.8.0-rc.1'),
            ('p987','bad'),('p98','v0.8.0-rc.1'),('p987','v0.8.0-rc.1\n'),
            ('p987\n','v0.8.0-rc.1'),(987,'v0.8.0-rc.1'),('p987',1))
        for entry in (file_log.prepare,file_log.build):
            for namespace,version in invalid:
                with self.subTest(entry=entry.__name__,namespace=namespace,version=version), \
                        mock.patch.object(file_log.h0,'private',side_effect=AssertionError('file work before identity validation')):
                    with self.assertRaises(ValueError):entry(None,None,None,namespace=namespace,version=version)

    def test_existing_defaults_and_new_identity_reach_normal_preparation(self):
        for entry in (file_log.prepare,file_log.build):
            for identity in ({},dict(namespace='p987',version='v0.8.0-rc.1')):
                with self.subTest(entry=entry.__name__,identity=identity), \
                        mock.patch.object(file_log.h0,'private',side_effect=RuntimeError('normal preparation entry')):
                    with self.assertRaisesRegex(RuntimeError,'normal preparation entry'):entry(None,None,None,**identity)


if __name__=='__main__':unittest.main()
