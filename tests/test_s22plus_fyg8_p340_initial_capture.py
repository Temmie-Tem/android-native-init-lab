"""Real initial exchange -> raw writer -> publisher -> receipt parser.

Only USB/baseline selection is substituted by a local fixture. No connected
device or private key is used, and no protocol/parser/publisher is mocked.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
sys.path.insert(0, str(ROOT / "tests"))

import device_action_f1_live_v2 as live
import device_action_raw_capture_v1 as raw_capture
import test_s22plus_fyg8_open_failure_capture as fixture


class P340InitialCaptureTests(unittest.TestCase):
    def test_actual_prepare_closure_uses_registered_carrier_exports(self):
        manifest_path = ROOT / "workspace/public/src/device-action/manifests/s22plus_fyg8_p340_process_v2_ready_1.json"
        bundle = SimpleNamespace(manifest=json.loads(manifest_path.read_bytes()))
        closure = live._closure(ROOT, bundle)
        adapter = live.typed_evidence.p340_stock_adapter
        for key, module in (("p340_carrier_model", adapter.model), ("p340_telemetry_spec", adapter.spec)):
            self.assertEqual(closure["sources"][key]["sha256"], hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest())
        self.assertIn("p340_open_failure_capture", closure["sources"])

    def _fixture(self):
        helper = fixture.OpenFailureCaptureTests()
        helper._module = live._p340_initial_observer_module
        return helper

    def test_registered_initial_collector_keeps_full_and_partial_failure_suffix(self):
        helper = self._fixture()
        module = helper._module()
        rejected = b"BAD!" + bytes(range(12))
        suffix = helper._suffix(module, rejected)
        for branch, cut in ((1, 96), (4, 96), (1, 48), (1, 0)):
            with self.subTest(branch=branch, cut=cut):
                session, _ = helper._run(suffix[:cut], branch=branch, patched=False)
                diagnostic = live.p340_open_read_observer.parse_retained_open_read_branch(session.raw_rx)
                self.assertEqual(len(session.raw_rx), 97 + cut)
                self.assertEqual(diagnostic["reason_frame_index"], 1)
                self.assertEqual(diagnostic["frame_count"], 2 + cut // 24)
                self.assertEqual(diagnostic["header_snapshot_hex"], rejected[:cut // 24 * 4].hex())
                self.assertFalse(diagnostic["candidate_success"])

    def test_failed_initial_receipt_is_published_and_reopens_without_lost_bytes(self):
        helper = self._fixture()
        module = helper._module()
        suffix = helper._suffix(module, b"BAD!" + bytes(range(12)))
        key_sha = hashlib.sha256(bytes(range(32))).hexdigest()
        for cut in (96, 48, 0, 85):
            with self.subTest(cut=cut), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                writer = raw_capture.RawCaptureWriter(
                    directory, "candidate-observer", stdout_maximum=193,
                    stderr_maximum=64, argv0_name="local-fixture",
                    stdout_name="candidate-observer.raw",
                    stderr_name="candidate-observer.raw.stderr",
                )
                resident, _ = helper._run(suffix[:cut], patched=False, writer=writer, return_result=True)
                handle = writer.finalize(returncode=0)
                raw = raw_capture.read_stdout(handle, maximum=193)
                raw_identity = live._receipt(handle.stdout_path, "fixture raw")
                raw_identity["capture_receipt"] = live._receipt(handle.receipt_path, "fixture capture")
                base_value = {
                    "binding": {}, "spec_sha256": "01" * 32,
                    "baseline_sha256": "02" * 32, "download_departure_sha256": "03" * 32,
                    "download_endpoint_absent": True, "topology_sha256": "04" * 32,
                    "endpoint_identity_sha256": "05" * 32, "guard_sha256": "06" * 32,
                    "raw": raw_identity, "banner_seen": False, "ready_seen": False,
                    "done_seen": False, "lane": {}, "bounded": True, "elapsed_sec": 0.1,
                    "classification": "authenticated-session-error", "accepted": False,
                }
                session = live._P340ObserverSession(
                    delegate=None, base=None, spec={}, run_dir=directory,
                    lane_binding={}, lane_binding_receipt={},
                    usb_root=Path("/unused/usb"), typec_root=Path("/unused/typec"),
                    auth_key=bytes(range(32)), auth_key_sha256=key_sha,
                )
                session.resident_result = resident
                with mock.patch.object(live._P327ObserverSession, "_observe_value", return_value=(base_value, {})):
                    value = session.observe(timeout_sec=1, download_departure={"absent": True})
                path = directory / "candidate-observer.json"
                self.assertEqual(live._read_json(path, "fixture receipt"), value)
                self.assertEqual(value["rx"]["size"], len(raw))
                self.assertEqual(value["proof"], {})
                self.assertEqual(value["command_count"], 0)
                self.assertEqual(value["session_count"], 1)
                self.assertEqual(value["schema"], live.P340_OBSERVER_RECEIPT_SCHEMA)
                self.assertNotIn("p339_authenticated_open_read_branch_resident", value)
                lane = {key: True for key in (
                    "both_topologies_inventory_complete", "accepted_inventory_exact",
                    "same_run_typec_partner_continuity", "accepted_for_p324",
                )}
                with (
                    mock.patch.object(live, "_p328_validate_common_receipt", return_value=(lane, "04" * 32, "05" * 32)),
                    mock.patch.object(live, "_p328_bound_auth_key_identity", return_value={"size": 32, "sha256": key_sha}),
                ):
                    reopened = live._p340_validate_receipt(SimpleNamespace(run_dir=directory), path, {})
                self.assertTrue(reopened["valid_receipt"])
                self.assertFalse(reopened["accepted"])
                if cut % 24:
                    self.assertIsNone(reopened["open_read_diagnostic"])
                else:
                    self.assertEqual(reopened["open_read_diagnostic"]["header_word_count"], cut // 24)
                self.assertEqual(raw_capture.read_stdout(raw_capture.load_handle(handle.receipt_path), maximum=193), raw)

    def test_registered_collector_preserves_three_authenticated_sessions(self):
        module = live._p340_initial_observer_module()
        success = fixture.success_fixture.P335RetainedListenerObserverTests()
        with mock.patch.object(fixture.success_fixture, "observer", module), \
             mock.patch.object(fixture.success_fixture, "runtime", module.runtime):
            success.test_two_same_fd_sessions_then_one_physical_reopen()

    def test_closed_terminal_mapping_stays_in_p340_namespace(self):
        acceptance = live.typed_evidence.p340_stock_adapter.acceptance_fixture()
        prepared = SimpleNamespace(bundle=SimpleNamespace(manifest={
            "observation": {"acceptance": acceptance,
                "candidate_observer": live.typed_evidence.p340_authenticated_open_read_branch_observer_spec(),
                live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
                live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE},
        }))
        for proved in (False, True):
            current = {live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY: {"proof": proved}}
            with self.subTest(proved=proved), mock.patch.object(live, "_state", return_value=current):
                verdict, outcome = live._closed_terminal_classification(prepared)
            self.assertEqual(outcome, live.P340_SUCCESS_OUTCOME if proved else live.P340_NO_PROOF_OUTCOME)
            self.assertEqual(verdict, live.P340_SUCCESS_VERDICT if proved else "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK")

    def test_final_health_projection_does_not_fall_into_p328(self):
        class HealthRecorded(Exception):
            pass

        acceptance = live.typed_evidence.p340_stock_adapter.acceptance_fixture()
        prepared = SimpleNamespace(run_dir=Path("/unused"), bundle=SimpleNamespace(manifest={
            "observation": {"acceptance": acceptance,
                "candidate_observer": live.typed_evidence.p340_authenticated_open_read_branch_observer_spec(),
                live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:
                live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE},
        }))
        projection = {"proof_class": "NO_PROOF_OBSERVER"}
        final = {"observer": {"accepted": False, "p340_stock": projection}}
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
        self.assertIs(current["p340_stock"], projection)
        self.assertNotIn("p328_stock", current)
        self.assertTrue(current["final_verified"])
        self.assertEqual(journal.transition.call_args.args[0], "HEALTH_VERIFIED")


if __name__ == "__main__":
    unittest.main()
