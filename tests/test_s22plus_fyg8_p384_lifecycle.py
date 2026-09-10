"""Direct candidate in real owner/raw-reopen/close; USB/Odin/ADB are fixtures."""
import contextlib
import copy
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import test_device_action_f1_live_v2 as generic
import test_s22plus_fyg8_p367_lifecycle as joined
import test_s22plus_fyg8_p384_observer as integration
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256
from s22plus_native_departure_h0_support import Fixture as DeparturePlatform, departure
import device_action_f1_live_v2 as live
import s22plus_fyg8_p384_candidate as candidate


class Receipt(_ReceiptFixture):
    def __init__(self, prepared, binary, case, budget):
        self.prepared = prepared; self.run_dir = prepared.run_dir; self.binary = binary
        self.case, self.budget = case, budget
        self.variant = live.typed_evidence.SHELL_VARIANTS['p384']
        self.runtime, self.observer = self.variant.runtime, self.variant.observer
        self.spec = live.typed_evidence._shell_observer_spec('p384')
        self.codec = live._open_header_initial_observer_module(self.runtime, self.observer, 'p384-owner-fixture')
        self.departure_receipt = None

    def _lane(self):
        return getattr(self, '_observed_lane', super()._lane())

    def arm(self):
        self._write_supporting_receipts()
        path = self.run_dir/'candidate-observer-guard.json'; path.unlink()
        live.cdc_acm_observer.persist_json(path, dict(schema=live.cdc_acm_observer.GUARD_SCHEMA,
            status='armed', spec_sha256='1'*64, topology_sha256='2'*64, rule_sha256='3'*64,
            instance_sha256='5'*64, output_sha256='6'*64, raw_capture_receipt={}, child_alive=True))
        self.plan, self.plan_receipt = candidate.console_owner.seal(None, self.run_dir)

    def observe(self, *, timeout_sec, download_departure):
        writer = live.raw_capture.RawCaptureWriter(self.run_dir, 'candidate-observer',
            stdout_maximum=self.observer.RAW_MAXIMUM, stderr_maximum=1, argv0_name='p384-fixture-socket',
            stdout_name='candidate-observer.raw', stderr_name='candidate-observer.raw.stderr')
        platform = DeparturePlatform(self.run_dir/'native-platform')
        capture = live.native_usb_departure.capture_binding
        def capture_fixture(run, **kw):
            with mock.patch.object(departure, '_snapshot', return_value=platform.snapshot):
                return capture(run, endpoint=platform.endpoint, binding=kw['binding'], request=kw['request'])
        session = live._P375ObserverSession.__new__(live._P375ObserverSession)
        session.delegate = SimpleNamespace(); session.run_dir = self.run_dir; session.namespace = 'p384'
        session.base = SimpleNamespace(binding=live._candidate_observer_binding(self.prepared))
        session.endpoint = SimpleNamespace(identity_sha256='e'*64)
        session.auth_key = KEY; session.auth_key_sha256 = KEY_SHA256
        session.auth_runtime = self.runtime; session.qualification_observer = self.observer
        session.root_console_plan_value = self.plan; session.root_console_plan_receipt = self.plan_receipt
        if live.native_roundtrip.selected(self.prepared.bundle):
            session.native_transaction = live.PreparedRun(self.prepared.root,
                self.prepared.native_parent or self.run_dir, self.prepared.bundle,
                self.prepared.prepared, self.prepared.private_target)
            session.native_previous = (live.native_roundtrip.native_health(live, session.native_transaction)
                                       if self.prepared.native_parent is not None else None)
        session.qualification = session.qualification_error = session.protocol_error = None
        session.control_intent_receipt = session.pre_control_lane = None
        session.proof_key = self.variant.proof_key
        session.receipt_schema = 's22plus_fyg8_p384_shell_qualification_acm_receipt_v1'
        session.receipt_label = 'P384 owner fixture'
        host, peer = socket.socketpair(); host.setblocking(False); peer.setblocking(False)
        process = subprocess.Popen([str(self.binary), str(peer.fileno()), '1'], pass_fds=(peer.fileno(),),
            env=dict(os.environ, P364_CASE=self.case, P364_MARK=str(self.run_dir/'marks'),
                     RC1_WORK=str(self.run_dir)), stderr=subprocess.PIPE, start_new_session=True)
        peer.close()
        try:
            with mock.patch.object(session, '_endpoint_exact', return_value=True), \
                    mock.patch.object(live._P345ObserverSession, '_lane_supplement', return_value=self._lane()), \
                    mock.patch.object(live.native_usb_departure, 'capture_binding',
                        side_effect=capture_fixture):
                try:
                    session.qualification = session._qualify_on_descriptor(self.codec, host.fileno(), writer,
                        time.monotonic()+min(timeout_sec, self.budget))
                except self.observer.QualificationError as exc:
                    session.qualification_error = exc; session.protocol_error = str(exc)
        finally:
            host.close()
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.communicate(timeout=3)
        result, error = session.qualification, session.qualification_error
        if error is not None and self.case not in ('hud-wire-corrupt', 'bad-health', 'same-boot', 'same-nonce'):
            raise AssertionError('unexpected qualification failure') from error
        audit = result.sessions[0].session.audit if result else error.failed_audit
        self.capture_path = writer.finalize(returncode=0).receipt_path
        self.audits = [audit]; self.rx_streams = [bytes(audit.rx)]; self.tx_streams = [bytes(audit.tx)]
        self.payload = bytes(audit.rx); self.proof = result.receipt if result else error.partial_receipt
        session.proof = self.proof
        if session.pre_control_lane is not None: self._observed_lane = session.pre_control_lane
        base = super()._receipt_value(); base.pop('p384_readonly_research_shell_qualification')
        base.update(session_count=1, accepted=result is not None,
            classification='accepted' if result else 'authenticated-session-error')
        lane = session.pre_control_lane or self._lane()
        raw = live.p318_topology.raw_snapshot(phase='candidate_end', capture_complete=True, endpoints=[])
        with mock.patch.object(live._P327ObserverSession, '_observe_value', return_value=(base, lane)), \
                mock.patch.object(live.p318_topology, 'capture_candidate_raw', return_value=raw):
            return live._P345ObserverSession.observe(session, timeout_sec=timeout_sec, download_departure=download_departure)


class Backend(joined.JoinedBackend):
    def __init__(self, prepared, binary, case, budget):
        with mock.patch.object(joined.parent.BaseBackend, '__init__',
                lambda self, *args: generic.FakeBackend.__init__(self, live)):
            super().__init__(prepared, None, 'normal')
        self.fixture = Receipt(prepared, binary, case, budget)

    @contextlib.contextmanager
    def candidate_observer_session(self, prepared):
        self.fixture.arm()
        try: yield self.fixture
        finally:
            live.cdc_acm_observer.persist_json(prepared.run_dir/'candidate-observer-guard-release.json',
                dict(schema=live.cdc_acm_observer.GUARD_SCHEMA, status='released', instance_sha256='5'*64,
                     released=True, returncode=0))

    def observe_candidate(self, prepared, run, lease, session):
        self.calls.append('observe'); wait = live.odin_core.wait_for_no_live_endpoint
        def absent(*args, **kw):
            kw.update(self.platform()); return wait(*args, **kw)
        with mock.patch.object(live.odin_core, 'wait_for_no_live_endpoint', side_effect=absent):
            return live.SamsungOdinBackend.observe_candidate(self, prepared, run, lease, session)


class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls): integration.ObserverTests.setUpClass.__func__(cls)

    def prepared(self):
        factory = generic.DeviceActionF1LiveV2Test(); factory.module = live
        temporary, prepared = factory.prepared(); self.addCleanup(temporary.cleanup)
        variant = live.typed_evidence.SHELL_VARIANTS['p384']
        prepared.bundle.manifest['manifest_id'] = 'p384-full-owner-fixture'
        prepared.bundle.manifest['observation'] = dict(timeout_sec=60, acceptance=variant.adapter.acceptance_fixture(),
            candidate_observer=live.typed_evidence._shell_observer_spec('p384'))
        prepared.bundle.manifest['observation'][live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY] = live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        prepared.private_target['topology'] = live.p324_typec_lane.SOURCE_TOPOLOGY
        prepared.prepared.update(p328_auth_key_identity=dict(size=32, sha256=KEY_SHA256),
            approval_binding=dict(p328_auth_key_identity=dict(size=32, sha256=KEY_SHA256)))
        return prepared

    def test_complete_failure_and_durable_resume(self):
        for case, budget, cut in (('normal', 30, False), ('hud-read-fails', 30, False),
                                  ('normal', 5, True), ('hud-wire-corrupt', 30, False)):
            with self.subTest(case=case, budget=budget, cut=cut):
                prepared = self.prepared(); backend = Backend(prepared, self.binary, case, budget)
                transition = live.core.Journal.transition
                def interrupted(journal, state, action, details):
                    result = transition(journal, state, action, details)
                    if cut and state == 'OBSERVED': raise KeyboardInterrupt('after durable observation')
                    return result
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(live, '_p300_bundle', return_value=False))
                    stack.enter_context(mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)))
                    stack.enter_context(mock.patch.object(departure, '_snapshot',
                        side_effect=departure.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/003/077')))
                    stack.enter_context(mock.patch.dict(os.environ, HUD_RENDERER=str(self.real_renderer),
                        METRICS_COLLECTOR=str(self.collector), LOCAL_CLOCK_RATE='1'))
                    with mock.patch.object(live.core.Journal, 'transition', new=interrupted):
                        if cut:
                            with self.assertRaises(KeyboardInterrupt): live.execute_prepared(prepared, prepared.approval_token, backend)
                        else: result = live.execute_prepared(prepared, prepared.approval_token, backend)
                    if cut:
                        with mock.patch.object(backend, 'observe_candidate', side_effect=AssertionError('observer replay')):
                            result = live.recover_prepared(prepared, backend)
                    live.validate_live_result(json.loads((prepared.run_dir/'live-result.json').read_text()), prepared)
                expected = ('NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK' if case == 'hud-wire-corrupt'
                            else 'PASS_F1_V2_P384_ROOT_CONSOLE_AND_ROLLED_BACK')
                self.assertEqual(result['verdict'], expected)
                self.assertEqual(result['current_state'], 'CLOSED'); self.assertFalse(result['recovery_required'])
                self.assertTrue(result['live_state']['final_verified'])
                self.assertEqual([c for c in backend.calls if c.startswith('transfer-')], ['transfer-candidate', 'transfer-rollback'])
                self.assertEqual(backend.calls.count('observe'), 1)
                self.assertFalse((prepared.run_dir/'native-restore-intent.json').exists())
                if case != 'hud-wire-corrupt':
                    proof = result['live_state'][backend.fixture.variant.proof_key]
                    self.assertTrue(proof['local_display']['native_health_proved'])
                    self.assertEqual(proof['control_sequence'], 5 if budget == 5 else 6)


if __name__ == '__main__': unittest.main()
