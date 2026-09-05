"""P341 actual closure/terminal and PTY initial-session integration; H0 only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "workspace/public/src/scripts/revalidation"), str(ROOT / "tests")]
import device_action_f1_live_v2 as live
import device_action_raw_capture_v1 as raw_capture
import test_s22plus_fyg8_host_first_open as pty_fixture


class P341InitialTests(unittest.TestCase):
    def test_real_pty_initial_sessions_and_auth_rejection(self):
        test = pty_fixture.HostFirstTests()
        completed = []
        def codec():
            module = live._p341_initial_observer_module()
            original = module.exchange_retained
            def exchange(*args, **kwargs):
                result = original(*args, **kwargs)
                completed.append(module.validate_retained_proof(result))
                return result
            module.exchange_retained = exchange
            return module
        test.codec = codec
        test.test_three_real_pty_sessions_and_bad_hmac()
        self.assertEqual(len(completed), 1)
        proof = live._p341_repin_proof(completed[0])
        live.typed_evidence.validate_p341_open_read_branch_proof(proof)

    def test_no_banner_failure_raw_publishes_without_invented_preamble(self):
        for silent in (True, False):
            module = live._p341_initial_observer_module()
            response = b'' if silent else module.encode_frame(
                module.runtime.DIAGNOSTIC_FRAME_TYPE, 0, module.DIAGNOSTIC.pack(3, 1))
            master, slave = os.openpty()
            live.cdc_acm_observer.ObserverSession._raw_tty(None, slave)
            os.set_blocking(slave, False)
            release = threading.Event()
            errors = []
            def peer():
                try:
                    endpoint = pty_fixture.Peer(master)
                    request = bytearray()
                    while len(request) < 32:
                        request.extend(endpoint.recv(32 - len(request)))
                    self.assertEqual(bytes(request), module.encode_frame(
                        module.runtime.FRAME_OPEN, 0, module.runtime.P335_RUN_ID))
                    endpoint.sendall(response)
                    release.wait(2)
                except BaseException as exc:
                    errors.append(exc)
            thread = threading.Thread(target=peer)
            with tempfile.TemporaryDirectory(prefix='p341-receipt-h0-') as temporary:
                directory = Path(temporary)
                writer = raw_capture.RawCaptureWriter(directory, 'candidate-observer',
                    stdout_maximum=193, stderr_maximum=64, argv0_name='local-pty-fixture',
                    stdout_name='candidate-observer.raw', stderr_name='candidate-observer.raw.stderr')
                thread.start()
                try:
                    with self.assertRaises(module.RetainedListenerObserverError) as caught:
                        module.exchange_retained(slave, bytes(range(32)),
                            reopen=lambda: self.fail('failure cannot reopen'), timeout_sec=0.15, writer=writer)
                    resident = caught.exception.result
                finally:
                    release.set(); thread.join(3)
                    pty_fixture.close(slave); pty_fixture.close(master)
                self.assertFalse(errors)
                handle = writer.finalize(returncode=0)
                self.assertEqual(raw_capture.read_stdout(handle, maximum=193), response)
                identity = live._receipt(handle.stdout_path, 'local raw')
                identity['capture_receipt'] = live._receipt(handle.receipt_path, 'local capture')
                base = dict(binding={}, spec_sha256='01'*32, baseline_sha256='02'*32,
                    download_departure_sha256='03'*32, download_endpoint_absent=True,
                    topology_sha256='04'*32, endpoint_identity_sha256='05'*32,
                    guard_sha256='06'*32, raw=identity, banner_seen=False, ready_seen=False,
                    done_seen=False, lane={}, bounded=True, elapsed_sec=0.15,
                    classification='authenticated-session-error', accepted=False)
                key_sha = hashlib.sha256(bytes(range(32))).hexdigest()
                session = live._P341ObserverSession(delegate=None, base=None, spec={},
                    run_dir=directory, lane_binding={}, lane_binding_receipt={},
                    usb_root=Path('/unused/usb'), typec_root=Path('/unused/typec'),
                    auth_key=bytes(range(32)), auth_key_sha256=key_sha)
                session.resident_result = resident
                with mock.patch.object(live._P327ObserverSession, '_observe_value', return_value=(base, {})):
                    value = session.observe(timeout_sec=1, download_departure={'absent': True})
                path = directory / 'candidate-observer.json'
                self.assertEqual(live._read_json(path, 'local receipt'), value)
                self.assertEqual(value['proof'], {})
                self.assertIsNone(value['open_read_diagnostic'])
                self.assertEqual(value['rx']['size'], len(response))
                self.assertEqual(value['tx']['size'], 32)
                lane = {key: True for key in ('both_topologies_inventory_complete',
                    'accepted_inventory_exact', 'same_run_typec_partner_continuity', 'accepted_for_p324')}
                with mock.patch.object(live, '_p328_validate_common_receipt', return_value=(lane,'04'*32,'05'*32)), \
                     mock.patch.object(live, '_p328_bound_auth_key_identity', return_value={'size':32,'sha256':key_sha}):
                    reopened = live._p341_validate_receipt(SimpleNamespace(run_dir=directory), path, {})
                self.assertTrue(reopened['valid_receipt'])
                self.assertFalse(reopened['accepted'])
                self.assertIsNone(reopened['open_read_diagnostic'])

    def test_actual_prepare_closure_uses_registered_carrier_exports(self):
        manifest_path = ROOT / "workspace/public/src/device-action/manifests/s22plus_fyg8_p341_process_v2_ready_1.json"
        bundle = SimpleNamespace(manifest=json.loads(manifest_path.read_bytes()))
        closure = live._closure(ROOT, bundle)
        adapter = live.typed_evidence.p341_stock_adapter
        for key, module in (("p341_carrier_model", adapter.model), ("p341_telemetry_spec", adapter.spec)):
            self.assertEqual(closure["sources"][key]["sha256"], hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest())
        self.assertIn("p341_open_failure_capture", closure["sources"])

    def test_closed_terminal_mapping_stays_in_p341_namespace(self):
        acceptance = live.typed_evidence.p341_stock_adapter.acceptance_fixture()
        prepared = SimpleNamespace(bundle=SimpleNamespace(manifest={
            "observation": {"acceptance": acceptance,
                "candidate_observer": live.typed_evidence.p341_authenticated_open_read_branch_observer_spec(),
                live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
                live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE},
        }))
        for proved in (False, True):
            current = {live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY: {"proof": proved}}
            with self.subTest(proved=proved), mock.patch.object(live, "_state", return_value=current):
                verdict, outcome = live._closed_terminal_classification(prepared)
            self.assertEqual(outcome, live.P341_SUCCESS_OUTCOME if proved else live.P341_NO_PROOF_OUTCOME)
            self.assertEqual(verdict, live.P341_SUCCESS_VERDICT if proved else "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK")

    def test_final_health_projection_does_not_fall_into_p328(self):
        class HealthRecorded(Exception):
            pass

        acceptance = live.typed_evidence.p341_stock_adapter.acceptance_fixture()
        prepared = SimpleNamespace(run_dir=Path("/unused"), bundle=SimpleNamespace(manifest={
            "observation": {"acceptance": acceptance,
                "candidate_observer": live.typed_evidence.p341_authenticated_open_read_branch_observer_spec(),
                live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
                live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE},
        }))
        projection = {"proof_class": "NO_PROOF_OBSERVER"}
        final = {"observer": {"accepted": False, "p341_stock": projection}}
        backend = SimpleNamespace(verify_final=lambda *_args: final)
        journal = SimpleNamespace(state=lambda: "ROLLBACK_FLASHED",
                                  transition=mock.Mock(side_effect=HealthRecorded))
        with (
            mock.patch.object(live, "_events", return_value={"rollback_flash_done"}),
            mock.patch.object(live, "_state", return_value={}),
            mock.patch.object(live, "_save_state") as saved,
            self.assertRaises(HealthRecorded),
        ):
            live._finish_rollback(prepared, backend, journal, Path("/unused"), None)
        current = saved.call_args.args[1]
        self.assertIs(current["p341_stock"], projection)
        self.assertNotIn("p328_stock", current)
        self.assertTrue(current["final_verified"])
        self.assertEqual(journal.transition.call_args.args[0], "HEALTH_VERIFIED")
