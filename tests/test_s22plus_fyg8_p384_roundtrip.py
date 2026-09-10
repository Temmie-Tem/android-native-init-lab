"""V2 three-role owner with real C/raw/USB inventory; hardware/AP are fixtures."""
import contextlib
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_fyg8_p384_lifecycle as ordinary
import test_s22plus_fyg8_p383_lifecycle as first
import test_s22plus_fyg8_p384_observer as integration

live = ordinary.live
owner = live.native_roundtrip


class Backend(first.Backend):
    def __init__(self, prepared, case, budget, **kwargs):
        self.case, self.budget = case, budget
        super().__init__(prepared, Roundtrip.binary, **kwargs)
        self.arrival_race = True

    @contextlib.contextmanager
    def candidate_observer_session(self, prepared):
        case = self.case if prepared.native_parent is not None or self.case.startswith('first-') else 'normal'
        case = case.removeprefix('first-')
        fixture = ordinary.Receipt(prepared, self.binary, case, self.budget)
        fixture.arm()
        try: yield fixture
        finally:
            live.cdc_acm_observer.persist_json(prepared.run_dir/'candidate-observer-guard-release.json',
                dict(schema=live.cdc_acm_observer.GUARD_SCHEMA, status='released', instance_sha256='5'*64,
                     released=True, returncode=0))


class Roundtrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = integration.local.source
        def source(*args, **kwargs):
            value = original(*args, **kwargs)
            old = 'const char*u="01234567-89ab-4cde-8fab-0123456789ab\\n";'
            assert value.count(old) == 1
            value = value.replace(old, 'const char*u=getenv("NB1_UUID");if(!u)u="01234567-89ab-4cde-8fab-0123456789ab\\n";')
            old = 'static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){'
            assert value.count(old) == 1
            return value.replace(old, old+'\nif(nr==278&&getenv("NB2_FIXED_NONCE")){memset((void*)a,82,b);return b;}')
        with mock.patch.object(integration.local, 'source', side_effect=source):
            integration.ObserverTests.setUpClass.__func__(cls)

    def prepared(self):
        prepared = ordinary.Lifecycle.prepared(self)
        prepared.bundle.manifest['manifest_id'] = owner.FOLLOWUP_MANIFEST
        rollback = prepared.bundle.receipt['rollback_ap']
        with live.core.pin_boot_only_ap(Path(rollback['path']), label='V2 fixture Android fallback',
                expected_size=rollback['size'], expected_sha256=rollback['sha256'],
                require_deterministic_metadata=False) as pinned:
            prepared.bundle.receipt['rollback_ap'] = pinned.receipt()
        # H0 archives have real parsers/claims but synthetic small bytes. The
        # actual fixed P384 AP/member were independently bound in the H0 bundle.
        pin = prepared.bundle.receipt['candidate_ap']
        for name, value in (('FOLLOWUP_AP', {k:pin[k] for k in ('size','sha256')}),
                            ('FOLLOWUP_MEMBER', pin['member']),
                            ('FOLLOWUP_ANDROID', {k:rollback[k] for k in ('size','sha256')})):
            patch = mock.patch.object(owner, name, value); patch.start(); self.addCleanup(patch.stop)
        prepared.prepared['approval_binding']['native_roundtrip'] = owner.prepare_plan(prepared.bundle)
        path = prepared.root/owner.CLAIM; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'opaque consumed V1 claim fixture\n')
        return prepared

    def patches(self, prepared):
        stack = first.Lifecycle.patches(self, prepared)
        stack.enter_context(mock.patch.dict(os.environ, HUD_RENDERER=str(self.real_renderer),
            METRICS_COLLECTOR=str(self.collector), LOCAL_CLOCK_RATE='1'))
        return stack

    def test_complete_optional_hud_failed_or_omitted_and_independent_claim(self):
        for case, budget in (('normal',30), ('hud-read-fails',30), ('normal',5)):
            with self.subTest(case=case,budget=budget):
                prepared = self.prepared(); backend = Backend(prepared, case, budget)
                retained = (prepared.root/owner.CLAIM).read_bytes()
                with self.patches(prepared):
                    result = live.execute_prepared(prepared, prepared.approval_token, backend)
                    live.validate_live_result(result, prepared)
                    recovered = live.recover_prepared(prepared, backend)
                self.assertEqual(result['verdict'],'PASS_F1_V2_P384_ROOT_CONSOLE_AND_ROLLED_BACK')
                self.assertTrue(result['live_state']['native_roundtrip']['proved'])
                self.assertTrue(recovered['live_state']['final_verified'])
                self.assertEqual(backend.race_enumerations,1)
                self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],
                    ['transfer-candidate','transfer-native-restore','transfer-rollback'])
                self.assertEqual((prepared.root/owner.CLAIM).read_bytes(),retained)
                claim = json.loads((prepared.root/owner.FOLLOWUP.claim).read_text())
                self.assertEqual(claim['schema'],owner.FOLLOWUP.schema)
                with self.assertRaises(live.F1LiveError): owner.preflight(live,prepared)
                identity = live._bound_candidate_registry_identity(prepared)
                self.assertIsNotNone(live.consumed_registry.active_claim(prepared.root,identity['candidate_key']))

    def test_health_wire_and_freshness_failure_cannot_continue_research(self):
        for case in ('first-bad-health','first-hud-wire-corrupt','bad-health','hud-wire-corrupt','same-boot','same-nonce'):
            with self.subTest(case=case):
                prepared = self.prepared(); backend = Backend(prepared,case,30)
                backend.same_boot = case == 'same-boot'
                with self.patches(prepared), mock.patch.dict(os.environ,
                        {'NB2_FIXED_NONCE':'1'} if case=='same-nonce' else {}):
                    try: result = live.execute_prepared(prepared,prepared.approval_token,backend)
                    except (live.F1LiveError, ordinary.candidate.observer.QualificationError):
                        with mock.patch.object(owner,'finish',side_effect=AssertionError('research replay')):
                            result = live.recover_prepared(prepared,backend)
                    live.validate_live_result(result,prepared)
                self.assertFalse(result['live_state']['native_roundtrip']['proved'])
                self.assertEqual(result['verdict'],'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
                self.assertEqual(backend.calls.count('transfer-native-restore'),0 if case.startswith('first-') else 1)
                if not case.startswith('first-'):
                    self.assertFalse((prepared.run_dir/owner.ARRIVAL_DIR/ordinary.candidate.return_host.INTENT_NAME).exists())
                self.assertEqual(backend.calls.count('transfer-rollback'),1)

    def test_publication_cuts_and_android_uncertainty_never_replay(self):
        for cut in ('restore-intent-after','delivery-after','restore-result-after','proof-after','a-start-after','a-result-after'):
            with self.subTest(cut=cut):
                prepared=self.prepared();backend=Backend(prepared,'normal',5);hit=[]
                original=live.core._write_exclusive
                names={'restore-intent-after':owner.INTENT,'delivery-after':'native-restore-delivery.json',
                    'restore-result-after':'native-restore-attempt-01.result.json','proof-after':'native-roundtrip-proof.json',
                    'a-start-after':'rollback-attempt-01.start.json','a-result-after':'rollback-attempt-01.result.json'}
                def write(path,value):
                    result=original(path,value)
                    if Path(path).name==names[cut] and not hit:
                        if cut=='a-result-after':backend.source_mode('android')
                        hit.append(True);raise KeyboardInterrupt(cut)
                    return result
                with self.patches(prepared):
                    with mock.patch.object(live.core,'_write_exclusive',side_effect=write),self.assertRaises(KeyboardInterrupt):
                        live.execute_prepared(prepared,prepared.approval_token,backend)
                    retained={p:p.read_bytes() for p in prepared.run_dir.rglob('*') if p.is_file()
                              and (p.name.endswith('.raw') or p.name=='native-restore-delivery.json')}
                    with mock.patch.object(owner,'finish',side_effect=AssertionError('native replay')), \
                            mock.patch.object(backend,'candidate_observer_session',side_effect=AssertionError('observer replay')):
                        if cut=='a-start-after':
                            with self.assertRaises(live.F1LiveError):live.recover_prepared(prepared,backend)
                        else:
                            result=live.recover_prepared(prepared,backend)
                            self.assertEqual(result['current_state'],'CLOSED')
                            self.assertEqual(result['live_state']['native_roundtrip']['proved'],cut in ('proof-after','a-result-after'))
                    for role in ('candidate','native-restore','rollback'):
                        self.assertLessEqual(backend.calls.count('transfer-'+role),1)
                    for path,raw in retained.items():self.assertEqual(path.read_bytes(),raw)

    def test_failed_restoration_and_failed_android_are_not_retried(self):
        for failure in ('odin_local_parse_failure','odin_device_session_failure_or_unknown'):
            with self.subTest(failure=failure):
                prepared=self.prepared();backend=Backend(prepared,'normal',5,restore=failure)
                with self.patches(prepared):
                    with self.assertRaises(live.F1LiveError):
                        live.execute_prepared(prepared,prepared.approval_token,backend)
                    backend.rollback=['odin_device_session_failure_or_unknown']
                    result=live.recover_prepared(prepared,backend)
                    self.assertTrue(result['recovery_required'])
                    with self.assertRaises(live.F1LiveError):live.recover_prepared(prepared,backend)
                self.assertEqual(backend.calls.count('transfer-native-restore'),1)
                self.assertEqual(backend.calls.count('transfer-rollback'),1)

    def test_wrong_fixed_target_android_or_typed_native_identity_is_rejected(self):
        prepared=self.prepared(); original=prepared.prepared['approval_binding']['native_roundtrip']['android']
        for case in ('target','android','native-size','arrival-time'):
            with self.subTest(case=case):
                bundle=copy.deepcopy(prepared.bundle);android=copy.deepcopy(original)
                if case=='target':bundle.profile['target']['model']='SM-G986N'
                if case=='android':
                    android['sha256']='f'*64
                    bundle.receipt['rollback_ap']['sha256']='f'*64
                if case=='native-size':bundle.receipt['candidate_ap']['size']=float(bundle.receipt['candidate_ap']['size'])
                if case=='arrival-time':bundle.manifest['observation']['timeout_sec']=60.0
                with self.assertRaises(ValueError):owner.plan(bundle,android)


class Selection(unittest.TestCase):
    def bundle(self, run, manifest):
        return SimpleNamespace(manifest=dict(manifest_id=manifest,observation=dict(acceptance=dict(run_id=run))))

    def test_ordinary_and_crossed_selectors_preserve_old_profile(self):
        self.assertFalse(owner.selected(self.bundle(owner.FOLLOWUP.run_id,'s22plus-fyg8-p384-h0-review')))
        self.assertEqual(owner.profile(self.bundle(owner.FIRST.run_id,'historical-manifest')),owner.FIRST)
        for run in (owner.FIRST.run_id,'foreign',None):
            with self.assertRaises(ValueError):owner.selected(self.bundle(run,owner.FOLLOWUP_MANIFEST))
        self.assertNotEqual(owner.FOLLOWUP.claim,owner.CLAIM)
        self.assertEqual(owner.FIRST.schema,'s22plus-native-roundtrip-owner-v1')
        self.assertEqual(owner.FIRST.arrival_seconds,600)
        self.assertEqual(owner.FOLLOWUP.arrival_seconds,60)


if __name__=='__main__':unittest.main()
