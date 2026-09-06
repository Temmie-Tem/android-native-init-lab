"""Host-only P348 artifact, adapter and static-closure checks."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for path in (ANALYSIS, REVALIDATION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import s22plus_fyg8_p347_artifact_identity as p347_artifact  # noqa: E402
import s22plus_fyg8_p348_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p348_process_v2_candidate_static as static  # noqa: E402
import s22plus_fyg8_p348_research_shell_observer as observer  # noqa: E402
import s22plus_fyg8_p348_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p348_stock_process_v2_adapter as adapter  # noqa: E402


class P348SuccessorTests(unittest.TestCase):
    def test_artifact_identity_is_fresh_and_rejects_consumed_p347_ap(self) -> None:
        value = artifact.validate_p348_identity()
        self.assertEqual(value["run_id_hex"], observer.RUN_ID_HEX)
        self.assertEqual(value["initial_session_count"], 6)
        self.assertEqual(value["same_fd_session_count"], 5)
        self.assertEqual(value["initial_reconnect_count"], 1)
        self.assertEqual(value["idle_seconds"], 120)
        self.assertEqual(value["total_session_count"], 6)
        self.assertEqual(value["total_command_count"], 18)
        self.assertEqual(value["physical_reopen_count"], 1)
        self.assertNotEqual(artifact.P348_IMAGE_IDENTITY, p347_artifact.P347_IMAGE_IDENTITY)
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_rollback_ap(Path("unused"), artifact.P347_CONSUMED_AP_IDENTITY)

    def test_adapter_acceptance_binds_six_session_geometry_and_lease_schema(self) -> None:
        acceptance = adapter.acceptance_fixture()
        adapter.validate_acceptance_item(acceptance)
        contract = adapter._contract()
        adapter.validate_contract(contract)
        self.assertEqual(adapter.LEASE_SCHEMA, "s22plus_fyg8_p348_shell_lease_v1")
        self.assertEqual(acceptance["initial_session_count"], 6)
        self.assertEqual(acceptance["same_fd_session_count"], 5)
        self.assertEqual(acceptance["initial_reconnect_count"], 1)
        self.assertEqual(acceptance["idle_seconds"], 120)
        self.assertEqual(acceptance["total_session_count"], 6)
        self.assertEqual(acceptance["total_command_count"], 18)
        self.assertEqual(acceptance["physical_reopen_count"], 1)
        self.assertEqual(len(acceptance["qualification_commands"]), 6)
        self.assertFalse(acceptance["later_action_lease_active"])
        self.assertEqual(
            acceptance["initial_observation"],
            "p348_readonly_research_shell_qualification",
        )

    def test_static_closure_names_fresh_workers_without_running_build(self) -> None:
        self.assertEqual(builder.P348_RUN_ID_HEX, observer.RUN_ID_HEX)
        self.assertEqual(builder._worker_pins["P348_RUNTIME_IDENTITY"]["size"], 1916)
        self.assertEqual(
            builder._worker_pins["P348_OBSERVER_IDENTITY"]["sha256"],
            observer.identity(Path(observer.__file__).read_bytes())["sha256"],
        )
        closure = static.source_receipts()
        for role in (
            "p348_research_shell_runtime",
            "p348_research_shell_observer",
            "p348_artifact_identity",
            "p348_stock_process_v2_adapter",
            "p348_stock_candidate_build",
            "p348_candidate_static",
            "p348_prepare",
            "p348_p347_runtime_wrapper",
            "p348_p347_observer_wrapper",
            "p348_p347_artifact_wrapper",
            "p348_p347_adapter_wrapper",
            "p348_p347_builder_wrapper",
            "p348_p347_static_wrapper",
            "p348_p347_prepare_wrapper",
            "p348_shell_session",
            "p348_shell_action",
            "p348_raw_capture",
        ):
            self.assertIn(role, closure)
        self.assertEqual(closure["p348_research_shell_observer"]["size"], 22531)
        self.assertEqual(closure["p348_research_shell_runtime"]["size"], 1916)
        self.assertFalse(adapter.audit()["device_contact"])
        self.assertFalse(adapter.audit()["live_authorized"])


if __name__ == "__main__":
    unittest.main()
