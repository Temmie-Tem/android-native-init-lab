"""Exact resident routing/budgets and retained-artifact compatibility; host only."""
import copy
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import test_device_action_f1_live_v2 as generic
import device_action_f1_live_v2 as live
import s22plus_fyg8_p386_candidate as candidate
import s22plus_fyg8_p386_process_v2_candidate_static as static
import s22plus_native_resident_backend_v1 as backend


class Bindings(unittest.TestCase):
    def prepared(self):
        factory=generic.DeviceActionF1LiveV2Test();factory.module=live
        temporary,value=factory.prepared();self.addCleanup(temporary.cleanup)
        value.bundle.manifest['observation']=dict(timeout_sec=2100,acceptance=candidate.adapter.acceptance_fixture(),
            candidate_observer=live.typed_evidence._shell_observer_spec('p386'),
            **{live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE})
        return value

    def test_resident_timeout_is_exact_and_other_profiles_keep_their_caps(self):
        prepared=self.prepared();profile=json.loads((static.ROOT/'workspace/public/src/device-action/profiles/s22plus_fyg8.json').read_text())
        manifest=dict(schema=live.core.MANIFEST_SCHEMA,manifest_id='p386-timeout-fixture',run_id='p386-timeout-run',
            status='draft-host-only',target_profile='workspace/public/src/device-action/profiles/s22plus_fyg8.json',
            candidate_ap=dict(path='workspace/private/fixture/AP.tar.md5',size=100,sha256='a'*64),
            rollback_ap=profile['rollback']['ap'],allowed_member=profile['transport']['allowed_member'],
            observation=prepared.bundle.manifest['observation'],final_health_profile='s22plus-fyg8-magisk',runner_version=live.core.RUNNER_VERSION)
        live.core.validate_manifest(manifest,profile)
        for timeout in (True,600,1800,2099,2101,7200):
            changed=copy.deepcopy(manifest);changed['observation']['timeout_sec']=timeout
            with self.subTest(timeout=timeout),self.assertRaises(live.core.F1V2Error):live.core.validate_manifest(changed,profile)
        for prefix in ('p384','p385'):
            variant=live.typed_evidence.SHELL_VARIANTS[prefix]
            changed=copy.deepcopy(manifest);changed['observation'].update(acceptance=variant.adapter.acceptance_fixture(),
                candidate_observer=live.typed_evidence._shell_observer_spec(prefix),timeout_sec=2100)
            with self.subTest(prefix=prefix),self.assertRaises(live.core.F1V2Error):live.core.validate_manifest(changed,profile)
        self.assertFalse(live.native_roundtrip.selected(prepared.bundle))
        self.assertFalse(live.typed_evidence.SHELL_VARIANTS['p386'].native_baseline)

    def test_guard_uses_existing_timeout_inputs_without_renewing_a_session(self):
        prepared=self.prepared();value=backend.guard_derivation(live,prepared.bundle)
        self.assertEqual(value['max_sec'],3000)
        self.assertEqual(value['inputs']['candidate_observation_sec'],2100)
        self.assertLessEqual(value['max_sec'],live.cdc_acm_observer.GUARD_MAX_SEC_LIMIT)
        prepared.bundle.manifest['observation']['timeout_sec']=2099
        with self.assertRaises(live.F1LiveError):backend.guard_derivation(live,prepared.bundle)
        # This operation has no reviewed/active preparation or device authority;
        # an unbound guard must fail before the privileged guard is invoked.
        prepared.bundle.manifest['observation']['timeout_sec']=2100
        with (mock.patch.object(live.p325_guard_adapter,'observer_session',side_effect=AssertionError('guard dispatch')),
              self.assertRaises(live.F1LiveError)):
            with backend.observer_session(live,prepared):pass

    def test_current_fixed_key_reader_route_and_full_host_source_roots(self):
        prepared=self.prepared();pin=dict(candidate.AUTH_KEY_IDENTITY)
        prepared.prepared.update(p328_auth_key_identity=pin,approval_binding=dict(p328_auth_key_identity=pin))
        key,digest=live._p328_read_auth_key(prepared)
        self.assertEqual(len(key),32);self.assertEqual(hashlib.sha256(key).hexdigest(),pin['sha256']);self.assertEqual(digest,pin['sha256'])
        paths=set(static.SOURCE_FILES.values())
        for name in ('s22plus_native_resident_observer_v1.py','s22plus_native_resident_backend_v1.py',
                     's22plus_native_resident_protocol_v1.py','s22plus_native_baseline_protocol_v1.py',
                     's22plus_fyg8_p328_auth_acm_observer.py','s22plus_fyg8_p363_return_host.py'):
            self.assertIn(static.REVALIDATION/name,paths)
        # Native H0 artifacts still match their original closed input map. The
        # host coordinator changes do not become reasons to rebuild native ELF.
        before=json.loads((static.builder.RETAINED/'result.json').read_text())['source_inputs']
        for path,pin in before.items():
            raw=(static.ROOT/path).read_bytes()
            self.assertEqual(dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest()),pin,path)

    def test_full_prepare_and_reopen_preserve_unique_sources_within_existing_bound(self):
        # Real declaration/closure/binding/producer/writer/reader. Only AP
        # verification and connected D0/Type-C observations are H0 fixtures.
        prepared=self.prepared();root,bundle=prepared.root,prepared.bundle
        bundle.manifest['status']='ready-for-f1-approval'
        bundle.manifest['observation']['acceptance']['contract']={name:dict(
            path='workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.4/h0-review-fixture/'+file,
            size=65000,sha256='a'*64) for name,file in (
                ('candidate_static','candidate-static.json'),('run_manifest','run-manifest.json'),
                ('static_check','static-check-result.json'))}
        with mock.patch.object(backend,'selected',return_value=False):
            before=live._closure(root,bundle)
        after=live._closure(root,bundle)
        def by_path(closure):
            return {pin['path']:(pin['size'],pin['sha256']) for pin in closure['sources'].values()}
        self.assertEqual(by_path(before),by_path(after))
        self.assertEqual(len(after['sources']),len(by_path(after)))
        for name in ('adapter','f1_core','typed_evidence','raw_capture','usbfs_identity','final_target_health'):
            self.assertEqual(after['sources'][name],before['sources'][name])
        self.assertLess(len(live.core.canonical(after)),len(live.core.canonical(before)))
        run=live.allocate_run_dir(root,None)
        serial,topology='RFCT0000000','usb:1-2'
        target=live.d0._target_evidence(bundle,dict(model='SM-S906N',device='g0q',incremental='S906NKSS7FYG8'),serial,topology)
        d0_result=dict(target_evidence=target)
        client=SimpleNamespace(one_serial=lambda:serial,topology=lambda _:topology)
        def collect(_bundle,destination,*_):
            live._write_exclusive(destination/'result.json',d0_result);return d0_result
        def lane(_bundle,destination,*_,**__):
            path=destination/live.P324_TYPEC_LANE_NAME
            live._write_exclusive(path,dict(h0_fixture='no connected endpoint'))
            return live._receipt(path,'fixture lane')
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(live.d0,'collect_connected',side_effect=collect))
            stack.enter_context(mock.patch.object(live.d0,'validate_result',return_value=d0_result))
            stack.enter_context(mock.patch.object(live,'_prepare_p324_typec_lane',side_effect=lane))
            stack.enter_context(mock.patch.object(live.core,'verify_bundle',return_value=bundle))
            value=live.prepare_connected(root,bundle,run,client)
            stack.enter_context(mock.patch.object(live,'_p324_typec_lane_value',return_value=({},value['p324_typec_lane_binding'])))
            reopened=live.load_prepared(root,root/'fixture-manifest.json',run)
        self.assertEqual(reopened.prepared,value)
        self.assertEqual(value['execution_closure'],after)
        self.assertEqual(value['approval_binding']['base_binding']['observation'],bundle.manifest['observation'])
        self.assertLessEqual((run/'prepared.json').stat().st_size,live.core.MAX_RESULT_RECORD)
        self.assertFalse(value['f1_authorized']);self.assertFalse(value['live_authorized'])
        # The actual producer failed at this writer before deduplication. Keep
        # that counterexample and prove the same bound still rejects it.
        old=copy.deepcopy(value);old['execution_closure']=before
        with self.assertRaises(live.F1LiveError):live._write_prepared_record(bundle,run/'oversized-fixture.json',old)
        self.assertFalse((run/'oversized-fixture.json').exists())
        print(json.dumps(dict(h0_full_prepared_bytes=(run/'prepared.json').stat().st_size,
            unchanged_limit_bytes=live.core.MAX_RESULT_RECORD,unique_source_set_preserved=True),sort_keys=True))


if __name__=='__main__':unittest.main()
