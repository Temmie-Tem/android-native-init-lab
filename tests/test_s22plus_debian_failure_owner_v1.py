"""Reachable supervised profile, independent channels and unchanged owner limits."""
import hashlib
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import test_s22plus_debian_failure_v1 as fixtures
import s22plus_debian_failure_profile_v1 as profile
import s22plus_debian_early_profile_v1 as early
import s22plus_debian_file_qualification_v1 as cache
import s22plus_native_adapter_v3 as adapter
import s22plus_native_root_inspect_session_v1 as owner
import s22plus_native_task_v3 as task_owner
from s22plus_native_records_v3 import pin,publish,verify


class FailureOwner(unittest.TestCase):
    def primary(self,boot=None,valid=True):
        f=fixtures.Diagnostics();boot=boot or f.boot;body=b'FYG8_H0 seq=1 BEGIN'
        tag=profile.protocol.tag(f.key,f.run_id,hashlib.sha256(boot).digest(),240,1,body,domain=profile.protocol.DOMAIN)
        return b'S22USB1 run='+f.run_id.hex().encode()+b' boot='+boot+b' seq=1 mac='+\
            (tag.hex().encode() if valid else b'0'*64)+b' '+body+b'\n'

    def project(self,raw):
        f=fixtures.Diagnostics();return profile.decode_retained(raw,key=f.key,run=f.run_id)

    def test_bad_primary_does_not_hide_authenticated_diagnostic(self):
        value=self.project(self.primary(valid=False)+fixtures.Diagnostics().record())
        self.assertIn('primary',value['parse_errors'])
        self.assertEqual(value['status'],'AUTHENTICATED_FAILURE_DIAGNOSTICS')
        self.assertTrue(value['initial_debian_pid1_measured'])

    def test_bad_diagnostic_does_not_hide_authenticated_primary(self):
        broken=re.sub(rb'mac=[0-9a-f]{64}',b'mac='+b'0'*64,fixtures.Diagnostics().record())
        value=self.project(broken+self.primary())
        self.assertEqual(value['status'],'AUTHENTICATED_PRIMARY_PREFIX_ONLY')
        self.assertFalse(value['initial_debian_pid1_measured'])

    def test_two_authenticated_boots_are_not_joined(self):
        value=self.project(self.primary(b'22345678-1234-1234-1234-123456789abc')+fixtures.Diagnostics().record())
        self.assertEqual(value['status'],'MIXED_AUTHENTICATED_BOOTS')
        self.assertFalse(value['authenticated_boot_consistent']);self.assertFalse(value['initial_debian_pid1_measured'])

    def test_both_empty_remains_unknown_without_replay(self):
        value=self.project(b'')
        self.assertEqual(value['status'],'NO_AUTHENTICATED_OUTCOME')
        self.assertFalse(value['nonexecution_proved']);self.assertFalse(value['replay_authorized'])

    def test_existing_window_and_exact_attended_budget(self):
        self.assertIs(early.window_profile(dict(profile=profile.PROFILE)),profile)
        self.assertEqual(profile.PENDING,'AWAITING_OFFLINE_FILE_RECORD')
        with self.assertRaises(ValueError):early.wire_protocol(dict(profile=profile.PROFILE))
        task=dict(N=dict(profile=profile.PROFILE),operations=['debian-early'],E=None,admission=None,
            prior_terminal=None,recovery_mode='attended',operation_budget=1,seconds=1800,
            reentry=False,hud=False,usb_reconnect=False,target={},A={})
        with mock.patch.object(adapter,'image_valid') as validate,mock.patch.object(owner,'android_basis_for_image'):
            owner.validate_task(task);validate.assert_called_once_with(task['N'])
            for change in (dict(seconds=1799),dict(operation_budget=2),dict(recovery_mode='deferred-physical')):
                with self.assertRaises(ValueError):owner.validate_task(dict(task,**change))
        grant=dict(opened_ns=0,deadline_ns=1200_000_000_001)
        profile.before_transfer(grant,0)
        with self.assertRaises(ValueError):profile.before_transfer(grant,1)

    def test_adapter_selects_cache_and_actual_archive_binding(self):
        image=dict(profile=profile.PROFILE)
        with mock.patch.object(cache,'binding',return_value={'artifact':True}) as bound,\
                mock.patch.object(adapter.integrated,'archive_binding') as archive:
            adapter.image_valid(image,artifact_bytes=True)
            bound.assert_called_once_with(image,early.image_binding);archive.assert_called_once_with(image,{'artifact':True})

    def test_cache_tracks_new_raw_reader_and_generated_fault_dependencies(self):
        cache._cache.clear()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);raw=root/'raw';raw.write_bytes(b'original')
            fault=root/'fault.c';fault.write_bytes(b'fault');reader=root/'reader.json';reader.write_bytes(b'{}')
            helper=publish(root/'helper.json',dict(construction=dict(fault_sources=[pin(fault)])))
            tested=publish(root/'vm.json',dict(cases=[dict(helper_request=helper,raw=pin(raw),file_retrieval=dict(retrieval=pin(reader)))]))
            built=publish(root/'build.json',{});artifact=publish(root/'artifact.json',dict(build=built,vm=tested))
            qualified=publish(root/'qualification.json',dict(vm=tested))
            image=dict(profile=profile.PROFILE,early_boot=artifact,qualification=qualified)
            wanted=pin(fault);validate=mock.Mock(side_effect=lambda image:(verify(wanted),{'ok':True})[1])
            receipts={r['path'] for r in cache._inputs(image)}
            self.assertTrue({str(raw),str(reader),str(fault)}<=receipts)
            cache.binding(image,validate);cache.binding(image,validate);self.assertEqual(validate.call_count,1)
            fault.write_bytes(b'other')
            with self.assertRaises(ValueError):cache.binding(image,validate)

    def test_virtual_counterpart_rejects_other_shell_or_initial_owner(self):
        import s22plus_debian_file_first_profile_v1 as shared
        with tempfile.TemporaryDirectory() as temporary:
            receipt=publish(Path(temporary)/'helper.json',dict(construction={}))
            expected=dict(shell_sha256='a'*64,init_sha256='b'*64)
            for field in expected:
                changed=dict(expected);changed[field]='c'*64
                with self.assertRaisesRegex(ValueError,'virtual shell or initial owner differs'):
                    shared.virtual_artifact(dict(helper_request=receipt,expected=changed),dict(measured=expected),{},diagnostic=True)

    def test_capability_selects_declared_variant_review(self):
        value=dict(schema='s22plus-native-session-v3-review',verdict='PASS_GO',scope='V3_REACHABLE_CAPABILITY',
            sources=[],runtime_sources={'workspace/public/src/fixture.c':dict(size=1,sha256='0'*64)},reviewer={},findings=[])
        with mock.patch.object(task_owner,'source_paths',return_value=[]),mock.patch.object(task_owner,'read',return_value=value) as read,\
                mock.patch.object(task_owner,'unchanged'),mock.patch.object(task_owner,'pin',return_value={'receipt':True}):
            task_owner.capability(Path('/fixture'),profile=profile.PROFILE)
            read.assert_called_once_with(Path('/fixture')/task_owner.DEBIAN_FAILURE_CAPABILITY)



if __name__=='__main__':unittest.main()
