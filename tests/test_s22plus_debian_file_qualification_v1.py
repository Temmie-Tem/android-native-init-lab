"""Qualification reuse must invalidate on nested bytes, paths or metadata."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_file_qualification_v1 as cache
from s22plus_native_records_v3 import pin,publish,verify


class QualificationCache(unittest.TestCase):
    def setUp(self):
        cache._cache.clear();temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.payload=self.root/'payload';self.payload.write_bytes(b'original')
        self.expected=pin(self.payload)
        helper=publish(self.root/'helper.json',dict(construction=dict(helper=self.expected)))
        tested=publish(self.root/'vm.json',dict(cases=[dict(helper_request=helper)]))
        built=publish(self.root/'build.json',dict(helper=self.expected))
        artifact=publish(self.root/'artifact.json',dict(build=built,vm=tested))
        qualified=publish(self.root/'qualification.json',dict(vm=tested))
        self.image=dict(profile='debian-file-first-v1',early_boot=artifact,qualification=qualified)
        self.validate=mock.Mock(side_effect=lambda image:(verify(self.expected),dict(validated=True))[1])

    def test_unchanged_inputs_reuse_only_qualification(self):
        first=cache.binding(self.image,self.validate);first['validated']=False
        self.assertEqual(cache.binding(self.image,self.validate),dict(validated=True))
        self.validate.assert_called_once()

    def test_nested_payload_change_with_restored_mtime_is_rejected(self):
        cache.binding(self.image,self.validate);before=self.payload.stat()
        self.payload.write_bytes(b'modified');os.utime(self.payload,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaises(ValueError):cache.binding(self.image,self.validate)
        self.assertEqual(self.validate.call_count,2)

    def test_equal_bytes_replacement_requires_validation_again(self):
        cache.binding(self.image,self.validate);replacement=self.root/'replacement';replacement.write_bytes(b'original')
        replacement.replace(self.payload);cache.binding(self.image,self.validate)
        self.assertEqual(self.validate.call_count,2)

    def test_symlink_replacement_cannot_use_cached_proof(self):
        cache.binding(self.image,self.validate);other=self.root/'other';self.payload.rename(other);self.payload.symlink_to(other)
        with self.assertRaises(ValueError):cache.binding(self.image,self.validate)

    def test_other_profile_cannot_select_cache(self):
        with self.assertRaises(ValueError):cache.binding(dict(self.image,profile='other'),self.validate)
        self.validate.assert_not_called()

    def test_changed_image_or_qualification_cannot_hit_existing_key(self):
        cache.binding(self.image,self.validate)
        cache.binding(dict(self.image,version='new'),self.validate)
        self.assertEqual(self.validate.call_count,2)
        p=Path(self.image['qualification']['path']);p.chmod(0o600);p.write_bytes(b'{}')
        with self.assertRaises(ValueError):cache.binding(self.image,self.validate)
