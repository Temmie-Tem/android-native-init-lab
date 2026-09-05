"""Actual P346 producer/consumer joins and predecessor rejection, host only."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "workspace/public/src/scripts/revalidation"),
               str(ROOT / "workspace/public/src/scripts/analysis")]
import device_action_f1_live_v2 as live
import device_action_f1_v2 as core
import s22plus_fyg8_p345_research_shell_runtime as old_runtime
import s22plus_fyg8_p346_research_shell_runtime as runtime
import s22plus_fyg8_p346_research_shell_observer as observer
import s22plus_fyg8_p346_artifact_identity as artifact
import s22plus_fyg8_p346_process_v2_candidate_static as static
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256


class SuccessorTests(unittest.TestCase):
    def test_runtime_identity_changes_only_nonce_and_entry_not_child_or_cancel(self):
        before = old_runtime.build_helper()
        after = runtime.build_helper()
        expected = before.replace(old_runtime._c_string(old_runtime.P345_COMMAND),
                                  runtime._c_string(runtime.P346_COMMAND), 1)
        self.assertEqual(after, expected)
        self.assertEqual(runtime.P346_ENTRY, old_runtime.P345_ENTRY.replace(
            old_runtime.P345_RUN_ID_HEX.encode(), runtime.P346_RUN_ID_HEX.encode()))
        self.assertEqual(runtime.child_source(), old_runtime.child_source())
        self.assertEqual(runtime.AUTH_DOMAIN_CANCEL, old_runtime.AUTH_DOMAIN_CANCEL)
        for prefix in range(328, 347):
            if hasattr(runtime, f"P{prefix}_RUN_ID"):
                self.assertEqual(getattr(runtime, f"P{prefix}_RUN_ID"), runtime.P346_RUN_ID)
        self.assertNotEqual(old_runtime.P345_RUN_ID, runtime.P346_RUN_ID)
        with self.assertRaises(runtime.RuntimeIdentityError):
            runtime.cancel_tag(KEY, old_runtime.P345_RUN_ID, b"n" * 32)

    def test_real_framed_reopen_arrival_projection_and_json_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = _ReceiptFixture(Path(directory) / "run", variant="p346")
            variant = live._host_first_variant(fixture.prepared.bundle)
            state = {"candidate_classification": "odin_transfer_completed", "candidate_completed": True,
                     "download_endpoint_absent": True, "rollback_classification": "odin_transfer_completed",
                     "rollback_completed": True, "final_verified": True}
            with mock.patch.object(live, "_p328_read_auth_key", return_value=(KEY, KEY_SHA256)), \
                 mock.patch.object(live, "_reopen_candidate_guard_release",
                                   return_value={"status": "released", "released": True}):
                durable = live._reopen_candidate_observation(fixture.prepared)
                self.assertTrue(variant.proof_ok(durable))
                projection = live._candidate_arrival_proof_projection(fixture.prepared, state)
                self.assertTrue(projection["proof"])
                self.assertNotIn("resident_lease_schema", projection)
                self.assertFalse(projection["later_action_lease_active"])
                self.assertEqual(json.loads(json.dumps(projection)), projection)
                for field in ("candidate_completed", "rollback_completed", "final_verified"):
                    bad = dict(state); bad[field] = False
                    self.assertFalse(live._candidate_arrival_proof_projection(fixture.prepared, bad)["proof"])
                closed = dict(state)
                closed[live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY] = projection
                with mock.patch.object(live, "_state", return_value=closed):
                    self.assertEqual(live._closed_terminal_classification(fixture.prepared),
                                     (variant.SUCCESS_VERDICT, variant.SUCCESS_OUTCOME))

    def test_consumed_banner_and_schema_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = _ReceiptFixture(Path(directory) / "run", variant="p346")
            codec = fixture.codec
            stale = fixture.rx_streams[0].replace(runtime.DEVICE_BANNER,
                                                old_runtime.DEVICE_BANNER, 1)
            with self.assertRaises(observer.QualificationError):
                observer.parse_captured_session(codec, stale, fixture.tx_streams[0], KEY)
            for key, value in (("schema", live.p345_shell_observer.SCHEMA),
                               ("run_id_hex", old_runtime.P345_RUN_ID_HEX)):
                bad = copy.deepcopy(fixture.proof); bad[key] = value
                with self.assertRaises(observer.QualificationError):
                    observer.validate_qualification(bad)
            spec = live.typed_evidence.p345_research_shell_observer_spec()
            with self.assertRaises(core.F1V2Error):
                core.verify_candidate_observer_binding(fixture.variant.adapter.acceptance_fixture(), spec)

    def test_source_closure_covers_executed_templates_and_rejects_drift(self):
        acceptance = live.typed_evidence.p346_stock_adapter.acceptance_fixture()
        closure = static.source_receipts()
        for name in ("research_shell_runtime", "research_shell_observer", "artifact_identity",
                     "stock_process_v2_adapter", "stock_candidate_build", "process_v2_candidate_static"):
            self.assertIn("p346_template_" + name, closure)
        sources = core.execution_critical_source_receipts(acceptance,
            candidate_arrival_proof_role=live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE)
        core.verify_candidate_source_binding(acceptance, {"source_closure": closure}, sources)
        changed = copy.deepcopy(sources)
        changed["p346_template_research_shell_observer"]["sha256"] = "0" * 64
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_source_binding(acceptance, {"source_closure": closure}, changed)
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_rollback_ap(Path("/unused"), artifact.P345_CONSUMED_AP_IDENTITY)
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact._validate_init(runtime.P346_RUN_ID_HEX.encode() + old_runtime.P345_RUN_ID_HEX.encode())

    def test_partial_backend_publication_has_no_legacy_p328_field_access(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = _ReceiptFixture(Path(directory) / "run", variant="p346")
            fixture.prepared.bundle.manifest["observation"]["timeout_sec"] = 300
            durable = dict(fixture.value)
            durable.update(accepted=False, classification="authenticated-session-error",
                receipt_sha256="a" * 64, qualification_complete=False,
                session_count=0, command_count=0, pid1_framed_exec_proof=False,
                busybox_ash_command_proof=False, framed_session_closed=False, same_tty_fd=False,
                p346_readonly_research_shell_qualification={"proved": False, "session_count": 0})
            self.assertNotIn("hmac_authenticated", durable)
            backend = object.__new__(live.SamsungOdinBackend); backend.odin = Path("/unused")
            absent = types.SimpleNamespace(absent=True, timed_out=False, next_sequence=1)
            with mock.patch.object(live.odin_core, "list_snapshot_receipts", return_value=[]), \
                 mock.patch.object(live.odin_core, "wait_for_no_live_endpoint", return_value=absent), \
                 mock.patch.object(live, "_reopen_candidate_observation", return_value=durable):
                value = backend.observe_candidate(fixture.prepared, fixture.run_dir, None, None)
            self.assertFalse(value["candidate_execution_proven"])
            self.assertFalse(value["qualification_complete"])
            self.assertEqual(value["session_count"], 0)
            self.assertEqual(json.loads(json.dumps(value)), value)


if __name__ == "__main__":
    unittest.main()
