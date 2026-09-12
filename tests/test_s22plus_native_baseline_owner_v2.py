"""Real resident C/PTY, owner, raw readers, registry and APs with fake hardware."""
from contextlib import contextmanager, ExitStack
import copy
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tarfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_native_baseline_owner_v1 as previous
import s22plus_resident_adoption_h0_support as support
import s22plus_native_baseline_v2_candidates as candidates

live,owner = previous.live,previous.owner


def make_ap(path, payload):
    frame = b'\x04\x22\x4d\x18'+bytes([0x60,0x40,0])+struct.pack('<I',0x80000000|len(payload))+payload+bytes(4)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        member=tarfile.TarInfo('boot.img.lz4');member.size=len(frame);member.mode=0o644
        archive.addfile(member,io.BytesIO(frame))
    prefix=stream.getvalue();path.write_bytes(prefix+hashlib.md5(prefix).hexdigest().encode()+b'  AP.tar\n')
    path.chmod(0o400)
    with live.core.pin_boot_only_ap(path,label='V2 synthetic AP',expected_size=path.stat().st_size,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),require_deterministic_metadata=True) as pinned:
        return dict(pinned.receipt(),member=dict(name='boot.img.lz4',size=len(frame),sha256=hashlib.sha256(frame).hexdigest()))


class Backend(previous.Backend):
    def start_peer(self, phase):
        self.test.current_prefix = 'p388' if phase == 'experiment' else 'p387'
        super().start_peer(phase)


class OwnerV2Tests(unittest.TestCase):
    exercise_native = previous.backend_checks.BackendTests.exercise
    execute = previous.OwnerTests.execute

    @classmethod
    def setUpClass(cls):
        cls.resources={}
        for prefix,declaration in candidates.DECLARATIONS.items():
            resource=type('NativeFixture_'+prefix,(unittest.TestCase,),{})
            support.compile_components(resource,declaration)
            cls.addClassCleanup(resource.doClassCleanups)
            cls.resources[prefix]=resource
        cls.binary=cls.resources['p387'].binary

    @contextmanager
    def running(self,case='normal'):
        with support.Fixture.running(self.resources[self.current_prefix],case) as peer:
            yield peer

    def fixture(self, *, fault=None):
        self.current_prefix='p387'
        value=previous.OwnerTests.fixture(self,fault=fault,backend_type=Backend)
        original=value.prepared
        for name in ('AGENTS.md','docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
            'docs/operations/S22PLUS_NATIVE_BASELINE_V2.md','docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md',owner.PROFILE):
            path=original.root/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((owner.ROOT/name).read_bytes())
        bundles={};manifests={}
        for prefix in candidates.DECLARATIONS:
            bundle=copy.deepcopy(original.bundle)
            variant=live.typed_evidence.SHELL_VARIANTS[prefix]
            bundle.manifest.update(manifest_id=prefix+'-owner-v2-fixture',run_id=prefix+'-owner-v2-fixture')
            bundle.manifest['observation']=dict(timeout_sec=5,acceptance=variant.adapter.acceptance_fixture(),
                candidate_observer=live.typed_evidence._shell_observer_spec(prefix),
                **{live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE})
            receipt=make_ap(original.root/(prefix+'.tar.md5'),(prefix+'-different-native-boot').encode())
            bundle.manifest['candidate_ap']={k:v for k,v in receipt.items() if k!='member'}
            bundle.receipt['candidate_ap']=receipt
            bundle=replace(bundle,sha256=live.core.json_sha256(bundle.receipt))
            path=original.root/(prefix+'-manifest.json');owner.publish(path,bundle.manifest)
            bundles[prefix]=bundle;manifests[prefix]=path
        value.prepared=replace(original,bundle=bundles['p387'])
        value.manifest=manifests['p387'];value.experiment_manifest=manifests['p388'];value.bundles=bundles
        stack=ExitStack();self.addCleanup(stack.close)
        def bound_bundle(root,path,**kwargs):
            return next(bundles[prefix] for prefix,p in manifests.items() if Path(path)==p)
        stack.enter_context(mock.patch.object(live.core,'verify_bundle',side_effect=bound_bundle))
        def current_static(bundle=None):
            prefix=live._shell_definition(bundle).prefix
            declared=candidates.DECLARATIONS[prefix]
            declaration=SimpleNamespace(IDENTITY=declared.IDENTITY,observer=declared.observer,
                artifact=SimpleNamespace(auth_key_identity=lambda:dict(size=32,sha256=previous.KEY_SHA256)))
            return SimpleNamespace(declaration=declaration,builder=SimpleNamespace(
                source_receipts=lambda:{'native_fixture':owner.pin(original.root/'native-source-fixture.c')},
                native_selection=lambda:dict(namespace=prefix,run_id=declared.IDENTITY.run_id_hex)))
        stack.enter_context(mock.patch.object(owner,'current_static',side_effect=current_static))
        return value

    def grant(self, fixture, *, operations=None, reservations=1, seconds=600):
        operations=operations or ['bootstrap']
        folder=fixture.prepared.root/owner.V2_BASE/str(time.monotonic_ns())
        result=owner.prepare_request(live,fixture.prepared.root,folder,manifest=fixture.manifest,
            experiment_manifest=fixture.experiment_manifest if 'experiment' in operations else None,
            target_file=fixture.target_file,operations=operations,reservations=reservations,seconds=seconds,policy=owner.V2_POLICY)
        owner.open_grant(live,fixture.prepared.root,Path(result['request']['path']),result['approval'],attended=True)
        return folder/'grant.json'

    def bootstrap(self, fixture):
        grant=self.grant(fixture)
        result=self.execute(fixture,grant)
        self.assertEqual(result['state'],'NATIVE_CLOSED',result)
        return grant.parent/'operation-01'/'terminal.json',result

    def test_real_N_E_N_then_A_and_both_permanent_content_claims(self):
        fixture=self.fixture();prior,first=self.bootstrap(fixture)
        # A fresh grant can reattach after the former V1 service ceiling. Only
        # the native clock advances here; authority is independently bounded.
        support.Fixture.advance(fixture.backend.peer,1801000)
        grant=self.grant(fixture,operations=['experiment','android-exit'],reservations=2)
        result=self.execute(fixture,grant,'experiment','native',prior)
        self.assertEqual(result['state'],'NATIVE_CLOSED',result)
        operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
        experiment=owner.experiment_outcome(live,operation)
        self.assertEqual(len({first['proof']['kernel_boot_identity_sha256'],experiment['kernel_boot_identity_sha256'],
                              result['proof']['kernel_boot_identity_sha256']}),3)
        self.assertIsNone(result['native_expiry_boottime_ns'])
        self.assertEqual(result['proof']['remaining_authentications'],2**64-3)
        self.assertEqual(owner.native_terminal(live,fixture.prepared.root,operation.directory),result)
        owner.admission(live,fixture.prepared.root,result['native'])
        identity=live._bound_candidate_registry_identity(owner.primary_prepared(live,operation))
        self.assertIsNotNone(owner.registry.active_claim(fixture.prepared.root,identity['candidate_key']))
        returned=operation.directory/'terminal.json'
        final=self.execute(fixture,grant,'android-exit','native',returned)
        self.assertEqual(final['state'],'ANDROID_CLOSED',final)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),4)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)
        self.assertEqual([session.namespace for _,session in fixture.backend.raw_observers],
                         ['p387','p387','p387','p388','p387','p387'])

    def test_equal_N_E_rejected_before_any_grant_or_effect(self):
        fixture=self.fixture()
        for field in ('run','ap','member'):
            with self.subTest(field=field):
                request=owner.request_value(live,fixture.prepared.root,fixture.bundles['p387'],
                    target={'serial':'H0_UNBOUND','topology':live.p324_typec_lane.SOURCE_TOPOLOGY},
                    manifest_receipt=owner.pin(fixture.manifest),review_receipt={'H0_ONLY':True},
                    operations=['experiment'],reservations=1,seconds=600,policy=owner.V2_POLICY,
                    experiment=dict(manifest=owner.pin(fixture.experiment_manifest),bundle=owner.bundle_snapshot(fixture.bundles['p388']),
                        native=owner.native_identity(fixture.bundles['p388']),closure={}))
                request=copy.deepcopy(request)
                if field=='run':request['experiment']['native']['run_id']=request['native']['run_id']
                elif field=='ap':request['experiment']['native']['candidate']=request['native']['candidate']
                else:
                    request['experiment']['native']['candidate']['member']=request['native']['candidate']['member']
                    request['experiment']['bundle']['sha256']=live.core.json_sha256(request['experiment']['bundle']['receipt'])
                with self.assertRaises(owner.BaselineError):owner.validate_native_roles(request)
        self.assertEqual(fixture.backend.calls,[])

    def test_full_native_source_terminal_reopens_through_the_actual_reader(self):
        fixture=self.fixture()
        complete={prefix:candidates.static(prefix).builder.source_receipts() for prefix in candidates.DECLARATIONS}
        selections={prefix:candidates.static(prefix).builder.native_selection() for prefix in candidates.DECLARATIONS}
        original=owner.current_static
        def full_sources(bundle=None):
            selected=original(bundle);prefix=selected.declaration.IDENTITY.namespace
            selected.builder.source_receipts=lambda:complete[prefix]
            selected.builder.native_selection=lambda:selections[prefix]
            return selected
        with mock.patch.object(owner,'current_static',side_effect=full_sources):
            prior,_=self.bootstrap(fixture)
            grant=self.grant(fixture,operations=['experiment'])
            result=self.execute(fixture,grant,'experiment','native',prior)
            directory=grant.parent/'operation-01'
            self.assertEqual(result['state'],'NATIVE_CLOSED',result)
            self.assertEqual(owner.native_terminal(live,fixture.prepared.root,directory),result)
            self.assertEqual(result['native']['native_sources'],complete['p387'])
            size=(directory/'terminal.json').stat().st_size
            self.assertLess(size,owner.core.MAX_JSON)
            print(json.dumps(dict(full_native_terminal_bytes=size,native_source_count=len(complete['p387']))))

    def test_consumed_E_cannot_leave_N_again_under_new_grant(self):
        fixture=self.fixture();prior,_=self.bootstrap(fixture)
        grant=self.grant(fixture,operations=['experiment'])
        result=self.execute(fixture,grant,'experiment','native',prior)
        self.assertEqual(result['state'],'NATIVE_CLOSED',result)
        count=len(fixture.backend.raw_observers)
        again=self.grant(fixture,operations=['experiment'])
        with self.assertRaises(owner.registry.RegistryError):
            self.execute(fixture,again,'experiment','native',grant.parent/'operation-01'/'terminal.json')
        self.assertFalse((again.parent/'01-reserved.json').exists())
        self.assertFalse((grant.parent/'operation-01'/'next-operation.json').exists())
        self.assertEqual(len(fixture.backend.raw_observers),count)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),4)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),0)

    def test_E_failure_or_returned_N_failure_uses_only_A(self):
        for fault in ('experiment-health','experiment-transfer','native-final-health','native-final-transfer','same-boot'):
            with self.subTest(fault=fault):
                fixture=self.fixture();prior,_=self.bootstrap(fixture)
                fixture.backend.fault=fault
                grant=self.grant(fixture,operations=['experiment'])
                result=self.execute(fixture,grant,'experiment','native',prior)
                self.assertEqual(result['state'],'ANDROID_CLOSED',result)
                expected=4 if fault.startswith('native-final') or fault=='same-boot' else 3
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),expected)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)

    def test_missing_native_inputs_after_E_intent_do_not_block_bound_A(self):
        fixture=self.fixture();prior,_=self.bootstrap(fixture)
        grant=self.grant(fixture,operations=['experiment']);journal=owner.journal
        def interrupted(operation,action=None,**details):
            result=journal(operation,action,**details)
            if action=='experiment-transfer-intent':raise KeyboardInterrupt('after E intent')
            return result
        with mock.patch.object(owner,'journal',side_effect=interrupted),self.assertRaises(KeyboardInterrupt):
            self.execute(fixture,grant,'experiment','native',prior)
        for bundle in fixture.bundles.values():Path(bundle.receipt['candidate_ap']['path']).unlink()
        operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
        original=live._closure
        def closure(root,bundle=None):
            if bundle is not None:raise OSError('native build/source unavailable')
            return original(root)
        with mock.patch.object(live,'_closure',side_effect=closure),owner.registry.target_session_lease(fixture.prepared.root):
            result=owner.recover(live,operation,fixture.backend,attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED',result)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),2)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)

    def test_completed_A_needs_only_health_when_old_AP_is_unavailable(self):
        fixture=self.fixture();prior,_=self.bootstrap(fixture)
        fixture.backend.fault='experiment-health'
        grant=self.grant(fixture,operations=['experiment']);journal=owner.journal
        def interrupted(operation,action=None,**details):
            result=journal(operation,action,**details)
            if action=='android-exit-transfer-result':raise KeyboardInterrupt('after completed A result')
            return result
        with mock.patch.object(owner,'journal',side_effect=interrupted),self.assertRaises(KeyboardInterrupt):
            self.execute(fixture,grant,'experiment','native',prior)
        Path(fixture.bundles['p387'].receipt['rollback_ap']['path']).unlink()
        operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
        with owner.registry.target_session_lease(fixture.prepared.root):
            result=owner.recover(live,operation,fixture.backend,attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED',result)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)

    def test_each_E_N_A_publication_cut_never_replays_a_native_role(self):
        cuts=[(phase,kind+'-attempt-01.'+suffix+'.json',when)
            for phase,kind in (('experiment',owner.TRANSFER_NATIVE),('native-final',owner.TRANSFER_NATIVE),
                                ('android-exit',owner.TRANSFER_ANDROID))
            for suffix in ('start','delivery','result') for when in ('before','after')]
        cuts += [('native-final','candidate-observer.json','after'),
                 ('operation-01','terminal.json','before'),('operation-01','terminal.json','after')]
        for phase,name,when in cuts:
            with self.subTest(phase=phase,name=name,when=when):
                fixture=self.fixture();prior,_=self.bootstrap(fixture)
                if phase=='android-exit':fixture.backend.fault='experiment-health'
                grant=self.grant(fixture,operations=['experiment']);hit=[]
                def intercept(writer):
                    def write(path,value,*args,**kwargs):
                        selected=Path(path).parent.name==phase and Path(path).name==name and not hit
                        if selected and when=='before':hit.append(True);raise KeyboardInterrupt('before durable boundary')
                        result=writer(path,value,*args,**kwargs)
                        if selected and when=='after':hit.append(True);raise KeyboardInterrupt('after durable boundary')
                        return result
                    return write
                with mock.patch.object(live.core,'_write_exclusive',side_effect=intercept(live.core._write_exclusive)), \
                        mock.patch.object(owner.records,'_write_exclusive',side_effect=intercept(owner.records._write_exclusive)), \
                        self.assertRaises(KeyboardInterrupt):
                    self.execute(fixture,grant,'experiment','native',prior)
                self.assertEqual(hit,[True])
                operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
                retained={p:p.read_bytes() for p in operation.directory.rglob('*') if p.is_file()
                    and (p.name.endswith('.raw') or p.name.endswith('.delivery.json'))}
                before=fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE)
                with owner.registry.target_session_lease(fixture.prepared.root), \
                        mock.patch.object(fixture.backend,'candidate_observer_session',side_effect=AssertionError('native observation replay')):
                    if phase=='android-exit' and not (name.endswith('.start.json') and when=='before'
                            or name.endswith('.result.json') and when=='after'):
                        with self.assertRaisesRegex(owner.BaselineError,'consumed'):
                            owner.recover(live,operation,fixture.backend,attended=True)
                    else:
                        result=owner.recover(live,operation,fixture.backend,attended=True)
                        expected='NATIVE_CLOSED' if name in ('terminal.json','candidate-observer.json') else 'ANDROID_CLOSED'
                        self.assertEqual(result['state'],expected,result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),before)
                self.assertLessEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)
                for path,raw in retained.items():self.assertEqual(path.read_bytes(),raw)
                fixture.backend.stop_peer()

    def test_expiry_during_E_and_changed_recovery_sources_fail_closed(self):
        for fault in ('grant-expiry','recovery-source'):
            with self.subTest(fault=fault):
                fixture=self.fixture();prior,_=self.bootstrap(fixture)
                grant=self.grant(fixture,operations=['experiment'])
                observing=fixture.backend.observe_candidate
                policy=fixture.prepared.root/'docs/operations/S22PLUS_NATIVE_BASELINE_V2.md'
                original=policy.read_bytes()
                def observe(prepared,*args,**kwargs):
                    if prepared.native_baseline_context['phase']=='experiment':
                        operation=owner.load_operation(live,prepared.root,prepared.native_parent)
                        if fault=='recovery-source':
                            policy.write_bytes(original+b'\nfixture changed recovery authority\n')
                            raise OSError('fixture native observation stopped')
                        with mock.patch.object(owner.protocol,'host_now_ns',return_value=operation.grant['deadline_boottime_ns']):
                            return observing(prepared,*args,**kwargs)
                    return observing(prepared,*args,**kwargs)
                with mock.patch.object(fixture.backend,'observe_candidate',side_effect=observe):
                    result=self.execute(fixture,grant,'experiment','native',prior)
                self.assertEqual(result['state'],'ANDROID_CLOSED' if fault=='grant-expiry' else 'PARKED',result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),3)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1 if fault=='grant-expiry' else 0)
                if fault=='recovery-source':
                    self.assertFalse((grant.parent/'operation-01/android-exit'/
                        (owner.TRANSFER_ANDROID+'-attempt-01.start.json')).exists())
                    policy.write_bytes(original)
                    operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
                    with owner.registry.target_session_lease(fixture.prepared.root):
                        result=owner.recover(live,operation,fixture.backend,attended=True)
                    self.assertEqual(result['state'],'ANDROID_CLOSED',result)
                    self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)


class NativeIdentityTests(unittest.TestCase):
    def test_review_binds_common_effect_sources_and_selected_candidate_sources(self):
        routes=[]
        for prefix,declared in candidates.DECLARATIONS.items():
            bundle=SimpleNamespace(manifest=dict(observation=dict(
                acceptance=declared.adapter.acceptance_fixture(),
                candidate_observer=live.typed_evidence._shell_observer_spec(prefix),
                **{live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
                   live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE})))
            routes.append(live._closure(candidates.ROOT,bundle))
        reviewed={pin['path']:pin for pin in candidates.review_sources().values()}
        for closure in routes:
            for pin in closure['sources'].values():
                path=str(Path(pin['path']).relative_to(candidates.ROOT))
                self.assertEqual(reviewed[path],dict(pin,path=path))
        for prefix in candidates.DECLARATIONS:
            for pin in candidates.static(prefix).source_receipts().values():
                self.assertEqual(reviewed[pin['path']],pin)
        changed=copy.deepcopy(routes[0])
        health=next(pin for pin in changed['sources'].values() if pin['path'].endswith('/s22plus_final_target_health_v1.py'))
        health['sha256']='a'*64
        with mock.patch.object(live,'_closure',return_value=changed):
            current={pin['path']:pin for pin in candidates.review_sources().values()}
            path=str(Path(health['path']).relative_to(candidates.ROOT))
            self.assertNotEqual(current[path],reviewed[path])

    def test_unrelated_E_catalog_edit_preserves_N_admission_identity(self):
        import s22plus_native_baseline_v2_build as build
        declaration=candidates.DECLARATIONS['p387']
        bundle=SimpleNamespace(manifest={'observation':{'acceptance':{'run_id':declaration.IDENTITY.run_id_hex}}},
            receipt={'candidate_ap':dict(path='H0_ONLY',size=1,sha256='a'*64)})
        before=owner.native_identity(bundle)
        stable=build.packaging.stable
        def changed(path,*args,**kwargs):
            raw=stable(path,*args,**kwargs)
            # Model an edit to the separate E row without mutating repository
            # files; selected N data and its real native byte sources stay fixed.
            if Path(path)==Path(candidates.__file__):
                raw=raw.replace(b'c751faa0c8580d07bc3c355985fc0c25',b'00000000000000000000000000000001')
            return raw
        replacement=candidates.declaration('p388','00000000000000000000000000000001','v0.2.0-rc.6','b'*64)
        with mock.patch.dict(candidates.DECLARATIONS,p388=replacement),mock.patch.object(build.packaging,'stable',side_effect=changed):
            self.assertEqual(owner.native_identity(bundle),before)
        self.assertIn(str(Path(candidates.__file__)),{str(p) for p in candidates.static('p387').SOURCE_FILES.values()})


if __name__ == '__main__':unittest.main()
