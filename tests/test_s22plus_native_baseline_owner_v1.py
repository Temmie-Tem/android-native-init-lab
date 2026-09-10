"""Native owner through real C/raw/registry/AP/Download/D0 consumers.

Only hardware, the independent approval fixture and the prebuilt image contents
are synthetic. No production device endpoint or artifact is used by these tests.
"""
import contextlib
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import test_device_action_f1_live_v2 as generic
import test_s22plus_fyg8_p383_lifecycle as platform
import test_s22plus_native_baseline_backend_v1 as backend_checks
import test_s22plus_native_baseline_protocol_v1 as native
from test_s22plus_fyg8_p345_live_receipt import KEY, KEY_SHA256
import device_action_f1_live_v2 as live
import s22plus_native_baseline_owner_v1 as owner


class Backend(platform.Backend):
    def __init__(self, prepared, test, *, fault=None):
        super().__init__(prepared, test.binary)
        self.test = test; self.fault = fault; self.peer_context = None; self.peer = None
        self.boots = 0; self.source_mode('android')
        self.client = live.d0.adb_client_for_bundle(self.adb, prepared.bundle)
        self.root = prepared.root
        self.raw_observers = []

    def adb_source(self):
        source = super().adb_source()
        return source.replace("else:raise SystemExit(2)",
            "elif args==['version']:print('Android Debug Bridge version 1.0.41')\n"
            "elif args[-2:]==['reboot','download']:pass\nelse:raise SystemExit(2)")

    def stop_peer(self):
        if self.peer_context is not None:
            context = self.peer_context; self.peer_context = None; self.peer = None
            context.__exit__(None,None,None)

    def start_peer(self, phase):
        self.stop_peer(); self.boots += 1
        ordinal = 1 if self.fault == 'same-boot' else self.boots
        boot = f'{ordinal:08x}-89ab-4cde-8fab-0123456789ab\n'
        case = 'bad-health' if self.fault == phase+'-health' else 'normal'
        with mock.patch.dict(os.environ, NB1_UUID=boot):
            self.peer_context = self.test.running(case)
            self.peer = self.peer_context.__enter__()

    def request_download(self, prepared):
        self.calls.append('request-download')
        live.SamsungOdinBackend.request_download(self, prepared)
        self.source_mode('download')

    @contextlib.contextmanager
    def candidate_observer_session(self, prepared):
        if self.fault == 'native-start-guard' and prepared.native_baseline_context['phase'] == 'native-start':
            raise live.F1LiveError('fixture missing current MM flag before AUTH')
        def observe(**kwargs):
            fixture, session, value, _, _ = self.test.exercise_native(prepared=prepared, external_peer=self.peer)
            self.raw_observers.append((fixture, session))
            return value
        yield SimpleNamespace(observe=observe)

    def transfer(self, prepared, endpoint, kind, destination, attempt, prefix):
        owner.validate_arm(live, prepared, endpoint, kind, attempt, prefix)
        self.calls.append('transfer-'+kind)
        phase = prepared.native_baseline_context['phase']
        classification = 'odin_device_session_failure_or_unknown' if self.fault == phase+'-transfer' else 'odin_transfer_completed'
        if classification == 'odin_transfer_completed':
            if kind == owner.TRANSFER_NATIVE:
                self.start_peer(phase); self.source_mode('absent'); self.generation += 1
            else:
                self.stop_peer(); self.source_mode('android')
        value = generic.FakeBackend._write_transfer(self, prepared, kind, classification, attempt, prefix,
            native_kinds=(owner.TRANSFER_NATIVE,))
        return live.TransferOutcome(classification, classification == 'odin_transfer_completed', True, value)


class OwnerTests(unittest.TestCase):
    running = native.ProtocolTests.running
    exercise_native = backend_checks.BackendTests.exercise

    @classmethod
    def setUpClass(cls):
        native.ProtocolTests.setUpClass.__func__(cls)

    def fixture(self, *, fault=None):
        factory = generic.DeviceActionF1LiveV2Test(); factory.module = live
        temporary, prepared = factory.prepared(); self.addCleanup(temporary.cleanup)
        variant = live.typed_evidence.SHELL_VARIANTS['p385']
        prepared.bundle.manifest.update(target_profile=owner.PROFILE, manifest_id='p385-baseline-owner-fixture',
            run_id='p385-baseline-owner-fixture')
        prepared.bundle.manifest['observation'] = dict(timeout_sec=5, acceptance=variant.adapter.acceptance_fixture(),
            candidate_observer=live.typed_evidence._shell_observer_spec('p385'),
            **{live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE})
        prepared.private_target['topology'] = live.p324_typec_lane.SOURCE_TOPOLOGY
        ap = prepared.bundle.receipt['rollback_ap']
        with live.core.pin_boot_only_ap(Path(ap['path']), label='baseline fixture A', expected_size=ap['size'],
                expected_sha256=ap['sha256'], require_deterministic_metadata=False) as pinned:
            prepared.bundle.receipt['rollback_ap'] = pinned.receipt()
        bundle = replace(prepared.bundle, sha256=core_digest(prepared.bundle.receipt))
        prepared = replace(prepared, bundle=bundle)
        backend = Backend(prepared, self, fault=fault); self.addCleanup(backend.stop_peer)
        closure = {'sources': {'fixture_host': {'path':str(backend.adb),'size':backend.adb.stat().st_size,
                                               'sha256':hashlib.sha256(backend.adb.read_bytes()).hexdigest()}}}
        source = prepared.root/'native-source-fixture.c'; source.write_text('/* fixture image bytes; production C peer is compiled separately */\n')
        review = prepared.root/'review.json'; live.core._write_exclusive(review, {'verdict':'PASS_GO','findings':[]})
        manifest = prepared.root/'manifest.json'; live.core._write_exclusive(manifest, bundle.manifest)
        target_file = prepared.root/'workspace/private/target.json'
        live.core._write_exclusive(target_file, {k:prepared.private_target[k] for k in ('serial','topology')})
        declaration = SimpleNamespace(IDENTITY=native.candidate.IDENTITY,
            artifact=SimpleNamespace(auth_key_identity=lambda:dict(size=32,sha256=KEY_SHA256)))
        static = SimpleNamespace(declaration=declaration,
            builder=SimpleNamespace(source_receipts=lambda:{'native_fixture':owner.pin(source)}))
        stack = contextlib.ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(owner, 'current_static', return_value=static))
        stack.enter_context(mock.patch.object(owner, 'reviewed', return_value=owner.pin(review)))
        stack.enter_context(mock.patch.object(live.core, 'verify_bundle', return_value=bundle))
        stack.enter_context(mock.patch.object(live, '_closure', return_value=closure))
        stack.enter_context(mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)))
        stack.enter_context(mock.patch.object(live, '_p300_bundle', return_value=False))
        stack.enter_context(mock.patch.object(live.native_usb_departure, '_snapshot',
            side_effect=live.native_usb_departure.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/003/077')))
        return SimpleNamespace(prepared=prepared, backend=backend, manifest=manifest, target_file=target_file)

    def grant(self, fixture, *, operations=None, reservations=1, seconds=600):
        folder = fixture.prepared.root/owner.BASE/str(time.monotonic_ns())
        result = owner.prepare_request(live, fixture.prepared.root, folder,
            manifest=fixture.manifest, target_file=fixture.target_file,
            operations=operations or ['bootstrap'], reservations=reservations, seconds=seconds)
        owner.open_grant(live, fixture.prepared.root, Path(result['request']['path']), result['approval'], attended=True)
        return folder/'grant.json'

    def execute(self, fixture, grant, operation='bootstrap', origin='android', prior=None):
        return owner.execute(live, fixture.prepared.root, grant, operation, origin,
            prior_native=prior, attended=True, backend=fixture.backend)

    def test_bootstrap_native_restore_then_exact_android_exit(self):
        fixture = self.fixture(); grant = self.grant(fixture, operations=list(owner.OPERATIONS), reservations=3)
        first = self.execute(fixture, grant)
        self.assertEqual(first['state'], 'NATIVE_CLOSED', first)
        first_path = grant.parent/'operation-01'/'terminal.json'
        second = self.execute(fixture, grant, 'restore', 'native', first_path)
        self.assertEqual(second['state'], 'NATIVE_CLOSED', second)
        self.assertNotEqual(first['proof']['kernel_boot_identity_sha256'], second['proof']['kernel_boot_identity_sha256'])
        final = self.execute(fixture, grant, 'android-exit', 'native', grant.parent/'operation-02'/'terminal.json')
        self.assertEqual(final['state'], 'ANDROID_CLOSED', final)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE), 3)
        self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID), 1)
        self.assertFalse(final['recovery_required'])
        operation = owner.load_operation(live, fixture.prepared.root, first_path.parent)
        claim_id = live._bound_candidate_registry_identity(owner.primary_prepared(live, operation))
        self.assertIsNotNone(owner.registry.active_claim(fixture.prepared.root, claim_id['candidate_key']))
        owner.admission(live, fixture.prepared.root, first['native'])
        with self.assertRaises(owner.BaselineError): self.execute(fixture, grant, 'restore', 'native', first_path)

    def test_exact_authority_and_suspend_aware_grant_expiry_precede_reservation(self):
        fixture = self.fixture()
        folder = fixture.prepared.root/owner.BASE/'authority-cases'
        result = owner.prepare_request(live, fixture.prepared.root, folder,
            manifest=fixture.manifest, target_file=fixture.target_file,
            operations=['bootstrap'], reservations=1, seconds=600)
        request = Path(result['request']['path'])
        for approval, attended in ((result['approval'],False), ('OLD_CONSUMED_APPROVAL',True),
                                    (result['approval']+'0',True)):
            with self.subTest(approval=approval[:24],attended=attended), self.assertRaises(owner.BaselineError):
                owner.open_grant(live,fixture.prepared.root,request,approval,attended=attended)
            self.assertFalse((folder/'grant.json').exists())
        start=owner.protocol.host_now_ns()
        with mock.patch.object(owner.protocol,'host_now_ns',return_value=start):
            owner.open_grant(live,fixture.prepared.root,request,result['approval'],attended=True)
        for instant in (start-1,start+600*10**9):
            with self.subTest(instant=instant), mock.patch.object(owner.protocol,'host_now_ns',return_value=instant), \
                    self.assertRaisesRegex(owner.BaselineError,'expired or changed host epoch'):
                self.execute(fixture,folder/'grant.json')
        with mock.patch.object(owner,'host_epoch',return_value='0'*64), \
                self.assertRaisesRegex(owner.BaselineError,'expired or changed host epoch'):
            self.execute(fixture,folder/'grant.json')
        self.assertFalse((folder/'01-reserved.json').exists())
        self.assertEqual(fixture.backend.calls,[])
        with mock.patch.object(owner.protocol.time,'clock_gettime_ns',return_value=123) as clock:
            self.assertEqual(owner.protocol.host_now_ns(),123)
            clock.assert_called_once_with(owner.protocol.time.CLOCK_BOOTTIME)

    def test_native_admission_rejects_a_different_physical_target_before_reservation(self):
        fixture=self.fixture();first_grant=self.grant(fixture)
        first=self.execute(fixture,first_grant)
        self.assertEqual(first['state'],'NATIVE_CLOSED',first)
        prior=first_grant.parent/'operation-01'/'terminal.json'
        fixture.target_file.unlink()
        live.core._write_exclusive(fixture.target_file,dict(serial='DIFFERENT_FIXTURE_DEVICE',
            topology=live.p324_typec_lane.SOURCE_TOPOLOGY))
        grant=self.grant(fixture,operations=['restore'])
        before=list(fixture.backend.calls)
        with self.assertRaises(owner.BaselineError):self.execute(fixture,grant,'restore','native',prior)
        self.assertEqual(fixture.backend.calls,before)
        self.assertFalse((grant.parent/'01-reserved.json').exists())
        self.assertFalse((prior.parent/'next-operation.json').exists())

    def test_large_request_writer_enforces_reader_limit_exclusive_publication_and_readback(self):
        fixture=self.fixture();path=fixture.prepared.root/'workspace/private/request.json'
        overhead=len((json.dumps({'payload':''},sort_keys=True,separators=(',',':'))+'\n').encode())
        value={'payload':'x'*(live.core.MAX_JSON-overhead)}
        receipt=owner.publish(path,value)
        self.assertEqual(receipt['size'],live.core.MAX_JSON)
        self.assertEqual(owner.read(path)[0],value)
        before=path.read_bytes()
        with self.assertRaises(Exception):owner.publish(path,{'replacement':True})
        self.assertEqual(path.read_bytes(),before)
        oversized=path.parent/'oversized'/'request.json';oversized.parent.mkdir()
        with self.assertRaisesRegex(owner.BaselineError,'one-MiB'):
            owner.publish(oversized,{'payload':value['payload']+'x'})
        self.assertFalse(oversized.exists())

    def test_native_faults_stop_before_another_native_role_and_keep_exact_A(self):
        for fault, native_count in (('bootstrap-first-health',1), ('native-final-health',2),
                                    ('same-boot',2), ('native-final-transfer',2)):
            with self.subTest(fault=fault):
                fixture = self.fixture(fault=fault); grant = self.grant(fixture)
                result = self.execute(fixture, grant)
                self.assertEqual(result['state'], 'ANDROID_CLOSED', result)
                self.assertTrue(result['research_stopped'])
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),native_count)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)
                operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
                with owner.registry.target_session_lease(fixture.prepared.root):
                    self.assertEqual(owner.recover(live,operation,fixture.backend,attended=True),result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)

    def test_retained_guard_failure_and_reserve_lane_cut_use_only_bound_A(self):
        for fault in ('native-start-guard','reserve-before-lane'):
            with self.subTest(fault=fault):
                fixture=self.fixture(); first_grant=self.grant(fixture)
                first=self.execute(fixture,first_grant)
                self.assertEqual(first['state'],'NATIVE_CLOSED',first)
                prior=first_grant.parent/'operation-01'/'terminal.json'
                grant=self.grant(fixture,operations=['restore'])
                if fault=='native-start-guard':
                    fixture.backend.fault=fault
                    result=self.execute(fixture,grant,'restore','native',prior)
                else:
                    original=owner.journal
                    def cut(operation,action=None,**details):
                        result=original(operation,action,**details)
                        if action=='reserved':raise KeyboardInterrupt('fixture cut before lane preparation')
                        return result
                    with mock.patch.object(owner,'journal',side_effect=cut), self.assertRaises(KeyboardInterrupt):
                        self.execute(fixture,grant,'restore','native',prior)
                    operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
                    self.assertFalse((operation.directory/live.P324_TYPEC_LANE_NAME).exists())
                    with owner.registry.target_session_lease(fixture.prepared.root):
                        result=owner.recover(live,operation,fixture.backend,attended=True)
                self.assertEqual(result['state'],'ANDROID_CLOSED',result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),2)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)
                self.assertFalse((grant.parent/'operation-01'/'native-start'/'p385-native-auth-01.intent.json').exists())

    def test_each_role_publication_cut_recovers_without_native_or_A_replay(self):
        cuts = (
            ('bootstrap-first',owner.TRANSFER_NATIVE+'-attempt-01.start.json','before'),
            ('bootstrap-first',owner.TRANSFER_NATIVE+'-attempt-01.start.json','after'),
            ('bootstrap-first',owner.TRANSFER_NATIVE+'-attempt-01.delivery.json','before'),
            ('bootstrap-first',owner.TRANSFER_NATIVE+'-attempt-01.delivery.json','after'),
            ('bootstrap-first',owner.TRANSFER_NATIVE+'-attempt-01.result.json','before'),
            ('bootstrap-first',owner.TRANSFER_NATIVE+'-attempt-01.result.json','after'),
            ('native-final',owner.TRANSFER_NATIVE+'-attempt-01.start.json','before'),
            ('native-final',owner.TRANSFER_NATIVE+'-attempt-01.start.json','after'),
            ('native-final',owner.TRANSFER_NATIVE+'-attempt-01.delivery.json','before'),
            ('native-final',owner.TRANSFER_NATIVE+'-attempt-01.delivery.json','after'),
            ('native-final',owner.TRANSFER_NATIVE+'-attempt-01.result.json','before'),
            ('native-final',owner.TRANSFER_NATIVE+'-attempt-01.result.json','after'),
            ('native-final','candidate-observer.json','after'),
            ('operation-01','terminal.json','before'),
            ('operation-01','terminal.json','after'),
            ('android-exit',owner.TRANSFER_ANDROID+'-attempt-01.start.json','before'),
            ('android-exit',owner.TRANSFER_ANDROID+'-attempt-01.start.json','after'),
            ('android-exit',owner.TRANSFER_ANDROID+'-attempt-01.delivery.json','before'),
            ('android-exit',owner.TRANSFER_ANDROID+'-attempt-01.delivery.json','after'),
            ('android-exit',owner.TRANSFER_ANDROID+'-attempt-01.result.json','before'),
            ('android-exit',owner.TRANSFER_ANDROID+'-attempt-01.result.json','after'))
        for phase, name, when in cuts:
            with self.subTest(phase=phase,name=name,when=when):
                fixture=self.fixture(fault='bootstrap-first-health' if phase=='android-exit' else None)
                grant=self.grant(fixture); hit=[]
                def intercept(writer):
                    def write(path,value,*args,**kwargs):
                        selected=Path(path).parent.name==phase and Path(path).name==name and not hit
                        if selected and when=='before':hit.append(True);raise KeyboardInterrupt('fixture before durable boundary')
                        result=writer(path,value,*args,**kwargs)
                        if selected and when=='after':hit.append(True);raise KeyboardInterrupt('fixture after durable boundary')
                        return result
                    return write
                with mock.patch.object(live.core,'_write_exclusive',side_effect=intercept(live.core._write_exclusive)), \
                        mock.patch.object(owner.records,'_write_exclusive',side_effect=intercept(owner.records._write_exclusive)), \
                        self.assertRaises(KeyboardInterrupt):
                    self.execute(fixture,grant)
                self.assertEqual(hit,[True])
                operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
                retained={p:p.read_bytes() for p in operation.directory.rglob('*') if p.is_file()
                    and (p.name.endswith('.raw') or p.name.endswith('.delivery.json'))}
                before=fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE)
                with owner.registry.target_session_lease(fixture.prepared.root), \
                        mock.patch.object(fixture.backend,'candidate_observer_session',side_effect=AssertionError('native observer replay')):
                    if phase=='android-exit' and not (name.endswith('.start.json') and when=='before'
                            or name.endswith('.result.json') and when=='after'):
                        with self.assertRaisesRegex(owner.BaselineError,'consumed'):owner.recover(live,operation,fixture.backend,attended=True)
                    else:
                        result=owner.recover(live,operation,fixture.backend,attended=True)
                        expected='NATIVE_CLOSED' if name in ('terminal.json','candidate-observer.json') else 'ANDROID_CLOSED'
                        self.assertEqual(result['state'],expected,result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),before)
                self.assertLessEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)
                for path,raw in retained.items():self.assertEqual(path.read_bytes(),raw)

    def test_incomplete_android_phase_and_final_read_resume_in_fresh_namespace(self):
        for cut in ('phase-directory','health-directory'):
            with self.subTest(cut=cut):
                fixture=self.fixture(fault='bootstrap-first-health');grant=self.grant(fixture);hit=[]
                original=Path.mkdir
                def mkdir(path,*args,**kwargs):
                    result=original(path,*args,**kwargs)
                    selected=(cut=='phase-directory' and path.name=='android-exit'
                              or cut=='health-directory' and path.name=='health' and path.parent.name=='android-exit')
                    if selected and not hit:hit.append(True);raise KeyboardInterrupt('fixture mkdir-only cut')
                    return result
                with mock.patch.object(Path,'mkdir',new=mkdir),self.assertRaises(KeyboardInterrupt):self.execute(fixture,grant)
                self.assertEqual(hit,[True])
                operation=owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
                with owner.registry.target_session_lease(fixture.prepared.root):
                    result=owner.recover(live,operation,fixture.backend,attended=True)
                self.assertEqual(result['state'],'ANDROID_CLOSED',result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_NATIVE),1)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)
                if cut=='health-directory':
                    self.assertEqual(list((operation.directory/'android-exit'/'health').iterdir()),[])
                    self.assertIn('health-attempt-002',result['final_health']['path'])
                operation = owner.load_operation(live,fixture.prepared.root,grant.parent/'operation-01')
                with owner.registry.target_session_lease(fixture.prepared.root):
                    self.assertEqual(owner.recover(live,operation,fixture.backend,attended=True),result)
                self.assertEqual(fixture.backend.calls.count('transfer-'+owner.TRANSFER_ANDROID),1)


def core_digest(value): return live.core.json_sha256(value)


if __name__ == '__main__': unittest.main()
