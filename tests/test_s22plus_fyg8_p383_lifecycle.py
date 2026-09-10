"""Joined three-role owner tests: real C/auth/raw/writers, fixture USB/Odin/ADB.

The existing P382 Receipt fixture is projected only to the fresh test namespace;
production ownership, health parsing and the exceptional transfer arm are real.
"""
import ast
import contextlib
import copy
import hashlib
import inspect
import io
import tarfile
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import textwrap
import time
import types
import unittest
from unittest import mock

import test_device_action_f1_live_v2 as generic
import test_s22plus_fyg8_p367_lifecycle as joined
import test_s22plus_fyg8_p383_native_health_integration as integration
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256
from s22plus_native_departure_h0_support import Fixture as DeparturePlatform, departure
import device_action_f1_live_v2 as live
import s22plus_fyg8_p383_research_shell_runtime as runtime
import s22plus_fyg8_p383_research_shell_observer as observer
import s22plus_fyg8_p383_console_owner as owner
import s22plus_fyg8_p383_return_host as return_host


def plan():
    return dict(schema=owner.SCHEMA, commands=[])


_source = Path(__file__).with_name('test_s22plus_fyg8_p382_lifecycle.py').read_text()
_tree = ast.parse(_source)
for _node in _tree.body:
    if isinstance(_node, ast.ClassDef) and _node.name == 'Receipt':
        fixture_source = ast.get_source_segment(_source, _node).replace('p382','p383').replace('P382','P383')
        fixture_source = fixture_source.replace('        def intent(request):', '''        def intent(request):
            parent = live.PreparedRun(self.prepared.root, self.prepared.native_parent or self.run_dir,
                self.prepared.bundle, self.prepared.prepared, self.prepared.private_target)
            prior = live.native_roundtrip.native_health(live, parent) if self.prepared.native_parent else None
            context = types.SimpleNamespace(namespace='p383', native_transaction=parent,
                native_previous=prior, _seal_control_intent=lambda *_:None)
            live._P375ObserverSession._native_before_control(context, request, None)''')
        exec(compile(fixture_source,
                     __file__+'#shared-receipt-fixture', 'exec'), globals())

# The unchanged generic fixture raw producer receives the explicit new role.
_raw_producer = textwrap.dedent(inspect.getsource(generic.FakeBackend._write_transfer))
_raw_producer = _raw_producer.replace('kind == "candidate"', 'kind in {"candidate", "native-restore"}')
exec(compile(_raw_producer, __file__+'#fixture-odin-producer', 'exec'), globals())


class Backend(joined.JoinedBackend):
    _write_transfer = _write_transfer

    def __init__(self, prepared, binary, *, restore='odin_transfer_completed'):
        with mock.patch.object(joined.parent.BaseBackend, '__init__',
                lambda self,*args: generic.FakeBackend.__init__(self, live)):
            super().__init__(prepared, None, 'normal')
        self.binary = binary
        self.restore = restore

    @contextlib.contextmanager
    def candidate_observer_session(self, prepared):
        fixture = Receipt(prepared, self.binary)
        fixture.arm()
        try:
            yield fixture
        finally:
            live.cdc_acm_observer.persist_json(prepared.run_dir/'candidate-observer-guard-release.json',
                dict(schema=live.cdc_acm_observer.GUARD_SCHEMA, status='released',
                     instance_sha256='5'*64, released=True, returncode=0))

    def observe_candidate(self, prepared, run, lease, session):
        self.calls.append('observe')
        wait = live.odin_core.wait_for_no_live_endpoint
        def absent(*args, **kwargs):
            kwargs.update(self.platform())
            return wait(*args, **kwargs)
        uuid = ('11234567' if prepared.native_parent and not getattr(self, 'same_boot', False) else '01234567')+'-89ab-4cde-8fab-0123456789ab\n'
        with mock.patch.object(live.odin_core, 'wait_for_no_live_endpoint', side_effect=absent), \
                mock.patch.dict(os.environ, NB1_UUID=uuid):
            return live.SamsungOdinBackend.observe_candidate(self, prepared, run, lease, session)

    def transfer(self, prepared, endpoint, kind, destination, attempt, prefix):
        if kind == 'native-restore':
            live.native_roundtrip.validate_restore_arm(live, prepared, endpoint, attempt, prefix)
            self.calls.append('transfer-native-restore')
            receipt = self._write_transfer(prepared, kind, self.restore, attempt, prefix)
            result = live.TransferOutcome(self.restore, self.restore == 'odin_transfer_completed', True, receipt)
            self.source_mode('absent')
            self.generation += 1
            return result
        return super().transfer(prepared, endpoint, kind, destination, attempt, prefix)


class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        integration.IntegrationTests.setUpClass.__func__(cls)

    def prepared(self):
        factory = generic.DeviceActionF1LiveV2Test()
        factory.module = live
        temporary, prepared = factory.prepared()
        self.addCleanup(temporary.cleanup)
        variant = live.typed_evidence.SHELL_VARIANTS['p383']
        prepared.bundle.manifest['manifest_id'] = 'p383-full-lifecycle-fixture'
        prepared.bundle.manifest['observation'] = dict(timeout_sec=30,
            acceptance=variant.adapter.acceptance_fixture(),
            candidate_observer=live.typed_evidence._shell_observer_spec('p383'))
        prepared.bundle.manifest['observation'][live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY] = live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        prepared.private_target['topology'] = live.p324_typec_lane.SOURCE_TOPOLOGY
        # A's existing archive is hash-pinned but need not use candidate metadata.
        ap = Path(prepared.bundle.receipt['rollback_ap']['path'])
        with tarfile.open(fileobj=io.BytesIO(ap.read_bytes()), mode='r:') as old_archive:
            payload = old_archive.extractfile('boot.img.lz4').read()
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            entry = tarfile.TarInfo('boot.img.lz4')
            entry.uid, entry.gid, entry.mtime, entry.size = 123, 456, 1, len(payload)
            archive.addfile(entry, io.BytesIO(payload))
        raw = stream.getvalue()
        raw += hashlib.md5(raw).hexdigest().encode() + b'  AP.tar\n'
        ap.unlink(); ap.write_bytes(raw); ap.chmod(0o400)
        prepared.bundle.manifest['rollback_ap'].update(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with live.core.pin_boot_only_ap(ap, label='actual rollback receipt fixture',
                expected_size=len(raw), expected_sha256=hashlib.sha256(raw).hexdigest(),
                require_deterministic_metadata=False) as pinned:
            # This is the actual rollback receipt producer used by verify_bundle.
            prepared.bundle.receipt['rollback_ap'] = pinned.receipt()
        prepared.prepared.update(p328_auth_key_identity=dict(size=32, sha256=KEY_SHA256),
            approval_binding=dict(p328_auth_key_identity=dict(size=32, sha256=KEY_SHA256),
                                  native_roundtrip=live.native_roundtrip.prepare_plan(prepared.bundle)))
        return prepared

    def patches(self, prepared):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(live, '_p300_bundle', return_value=False))
        stack.enter_context(mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)))
        stack.enter_context(mock.patch.object(live, '_closure', side_effect=lambda *_: prepared.prepared['execution_closure']))
        stack.enter_context(mock.patch.object(departure, '_snapshot',
            side_effect=departure.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/003/077')))
        return stack

    def test_complete_roundtrip_with_retained_consumed_claim(self):
        prepared = self.prepared()
        backend = Backend(prepared, self.binary)
        with self.patches(prepared):
            result = live.execute_prepared(prepared, prepared.approval_token, backend)
            live.validate_live_result(result, prepared)
            replayed = live.recover_prepared(prepared, backend)
        self.assertEqual(result['current_state'], 'CLOSED')
        self.assertEqual(result['verdict'], 'PASS_F1_V2_P383_ROOT_CONSOLE_AND_ROLLED_BACK')
        self.assertTrue(result['live_state']['native_roundtrip']['proved'])
        self.assertTrue(replayed['live_state']['final_verified'])
        self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],
                         ['transfer-candidate', 'transfer-native-restore', 'transfer-rollback'])
        identity = live._bound_candidate_registry_identity(prepared)
        self.assertIsNotNone(live.consumed_registry.active_claim(prepared.root, identity['candidate_key']))

    def test_publication_cuts_never_repeat_a_role(self):
        cuts = ('exception-claim', 'restore-intent-before', 'restore-intent-after',
                'delivery-before', 'delivery-after', 'restore-result-after',
                'second-raw-after', 'proof-after', 'a-start-after', 'a-result-after',
                'closed-before-result')
        original = live.core._write_exclusive
        for cut in cuts:
            with self.subTest(cut=cut):
                prepared = self.prepared()
                backend = Backend(prepared, self.binary)
                hit = []
                def publish(path, value):
                    path = Path(path)
                    name = path.name
                    second = path.parent.name == live.native_roundtrip.ARRIVAL_DIR
                    selected = (
                        cut == 'exception-claim' and path == prepared.root/live.native_roundtrip.CLAIM
                        or cut.startswith('restore-intent-') and second and name == live.native_roundtrip.INTENT
                        or cut.startswith('delivery-') and second and name == 'native-restore-delivery.json'
                        or cut == 'restore-result-after' and second and name == 'native-restore-attempt-01.result.json'
                        or cut == 'second-raw-after' and second and name == 'candidate-observer.json'
                        or cut == 'proof-after' and name == 'native-roundtrip-proof.json'
                        or cut == 'a-start-after' and name == 'rollback-attempt-01.start.json'
                        or cut == 'a-result-after' and name == 'rollback-attempt-01.result.json')
                    if selected and not hit and (cut.endswith('before') or cut == 'exception-claim'):
                        hit.append(str(path)); raise KeyboardInterrupt(cut)
                    result = original(path, value)
                    if selected and not hit:
                        if cut == 'a-result-after': backend.source_mode('android')
                        hit.append(str(path)); raise KeyboardInterrupt(cut)
                    return result
                original_result = live._result
                def result_cut(p, journal, *args):
                    if cut == 'closed-before-result' and journal.state() == 'CLOSED' and not hit:
                        hit.append('CLOSED'); raise KeyboardInterrupt(cut)
                    return original_result(p, journal, *args)
                original_observe = live._P345ObserverSession.observe
                def observe_cut(session, **kwargs):
                    result = original_observe(session, **kwargs)
                    if cut == 'second-raw-after' and session.run_dir.name == live.native_roundtrip.ARRIVAL_DIR and not hit:
                        hit.append('second-raw'); raise KeyboardInterrupt(cut)
                    return result
                with self.patches(prepared):
                    with mock.patch.object(live._P345ObserverSession, 'observe', new=observe_cut), \
                            mock.patch.object(live.core, '_write_exclusive', side_effect=publish), \
                            mock.patch.object(live, '_result', side_effect=result_cut):
                        with self.assertRaises(KeyboardInterrupt):
                            live.execute_prepared(prepared, prepared.approval_token, backend)
                    self.assertTrue(hit)
                    retained = {path:path.read_bytes() for path in prepared.run_dir.rglob('*')
                        if path.is_file() and (path.name.endswith('.raw') or path.name == 'native-restore-delivery.json')}
                    with mock.patch.object(backend, 'candidate_observer_session', side_effect=AssertionError('observer replay')), \
                            mock.patch.object(live.native_roundtrip, 'finish', side_effect=AssertionError('native replay')):
                        if cut == 'a-start-after':
                            with self.assertRaises(live.F1LiveError):
                                live.recover_prepared(prepared, backend)
                            self.assertNotIn('transfer-rollback', backend.calls)
                        else:
                            result = live.recover_prepared(prepared, backend)
                            self.assertEqual(result['current_state'], 'CLOSED')
                            completed = cut in ('proof-after', 'a-result-after', 'closed-before-result')
                            self.assertEqual(result['live_state']['native_roundtrip']['proved'], completed)
                    for role in ('candidate', 'native-restore', 'rollback'):
                        self.assertLessEqual(backend.calls.count('transfer-'+role), 1)
                    for path, raw in retained.items():
                        self.assertEqual(path.read_bytes(), raw)

    def test_failed_restoration_and_failed_android_are_not_retried(self):
        for failure in ('odin_local_parse_failure', 'odin_device_session_failure_or_unknown'):
            with self.subTest(failure=failure):
                prepared = self.prepared()
                backend = Backend(prepared, self.binary, restore=failure)
                with self.patches(prepared):
                    with self.assertRaises(live.F1LiveError):
                        live.execute_prepared(prepared, prepared.approval_token, backend)
                    backend.rollback = ['odin_device_session_failure_or_unknown']
                    result = live.recover_prepared(prepared, backend)
                    self.assertTrue(result['recovery_required'])
                    with self.assertRaises(live.F1LiveError):
                        live.recover_prepared(prepared, backend)
                self.assertEqual(backend.calls.count('transfer-native-restore'), 1)
                self.assertEqual(backend.calls.count('transfer-rollback'), 1)

    def test_same_kernel_boot_stops_before_second_control(self):
        prepared = self.prepared()
        backend = Backend(prepared, self.binary)
        backend.same_boot = True
        with self.patches(prepared):
            with self.assertRaises(observer.QualificationError):
                live.execute_prepared(prepared, prepared.approval_token, backend)
            child = live.native_roundtrip.child(live, prepared)
            self.assertFalse((child.run_dir/return_host.INTENT_NAME).exists())
            result = live.recover_prepared(prepared, backend)
        self.assertFalse(result['live_state']['native_roundtrip']['proved'])
        self.assertEqual(backend.calls.count('transfer-native-restore'), 1)
        self.assertEqual(backend.calls.count('transfer-rollback'), 1)

    def test_actual_short_restore_intent_write_preserves_partial_and_recovers(self):
        prepared = self.prepared()
        backend = Backend(prepared, self.binary)
        original = os.write
        target = prepared.run_dir/live.native_roundtrip.ARRIVAL_DIR/live.native_roundtrip.INTENT
        def short(fd, payload):
            if Path(os.readlink('/proc/self/fd/'+str(fd))) == target:
                return original(fd, payload[:19])
            return original(fd, payload)
        with self.patches(prepared):
            with mock.patch.object(os, 'write', side_effect=short), self.assertRaises(live.core.F1V2Error):
                live.execute_prepared(prepared, prepared.approval_token, backend)
            retained = target.read_bytes()
            self.assertEqual(len(retained), 19)
            result = live.recover_prepared(prepared, backend)
        self.assertEqual(target.read_bytes(), retained)
        self.assertFalse(result['live_state']['native_roundtrip']['proved'])
        self.assertNotIn('transfer-native-restore', backend.calls)
        self.assertEqual(backend.calls.count('transfer-rollback'), 1)


if __name__ == '__main__':
    unittest.main()
