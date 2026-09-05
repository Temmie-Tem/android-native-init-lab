"""Focused host-only P342 static and preparation checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
for directory in (
    ROOT / "workspace/public/src/scripts/analysis",
    ROOT / "workspace/public/src/scripts/revalidation",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import prepare_s22plus_fyg8_p342_process_v2 as prepare  # noqa: E402
import s22plus_fyg8_p342_process_v2_candidate_static as candidate_static  # noqa: E402


class P342ProcessV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.static = candidate_static.build_result()
        cls.manifest, cls.payloads, cls.verification = prepare.build()

    def test_static_binds_fresh_four_session_idle_geometry(self) -> None:
        self.assertEqual(
            self.static["schema"],
            "s22plus_fyg8_p342_process_v2_candidate_static_v1",
        )
        self.assertEqual(self.static["run_id"], prepare.RUN_ID)
        self.assertEqual(
            self.static["predecessor_run_id"], prepare.PREDECESSOR_RUN_ID
        )
        self.assertEqual(
            self.static["userspace_overlay_contract_id"],
            prepare.adapter.OVERLAY_CONTRACT_ID,
        )
        self.assertEqual(self.static["same_fd_session_count"], 3)
        self.assertEqual(self.static["total_session_count"], 4)
        self.assertEqual(self.static["total_command_count"], 12)
        self.assertEqual(self.static["physical_reopen_indexes"], [0, 0, 0, 1])
        self.assertEqual(
            self.static["idle_reuse"],
            {
                "phase": "s22plus-fyg8-idle-reuse-h0-v1",
                "before_session_index": 2,
                "requested_seconds": 120,
                "elapsed_seconds_min": 120,
                "elapsed_seconds_max": 180,
            },
        )
        self.assertIn("p342_idle_reuse_probe", self.static["source_closure"])
        self.assertFalse(self.static["safety"]["device_contact"])
        self.assertFalse(self.static["safety"]["f1_authorized"])

    def test_prepare_reopens_three_promotion_payloads(self) -> None:
        self.assertEqual(
            set(self.payloads), {"candidate_static", "run_manifest", "static_check"}
        )
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_check = json.loads(self.payloads["static_check"])
        self.assertEqual(run_manifest["schema"], prepare.RUN_MANIFEST_SCHEMA)
        self.assertEqual(run_manifest["run_id"], prepare.RUN_ID)
        observation = run_manifest["observation_contract"]
        self.assertEqual(observation["same_fd_session_count"], 3)
        self.assertEqual(observation["total_session_count"], 4)
        self.assertEqual(observation["total_command_count"], 12)
        self.assertEqual(observation["idle_seconds"], 120)
        self.assertFalse(observation["later_action_lease_active"])
        self.assertEqual(static_check["schema"], prepare.STATIC_RESULT_SCHEMA)
        self.assertEqual(static_check["verdict"], prepare.STATIC_RESULT_VERDICT)
        self.assertFalse(static_check["safety"]["device_contact"])
        self.assertTrue(self.verification["common_offline_verified"])
        self.assertEqual(
            self.verification["schema"],
            "device_action_f1_p342_stock_offline_contract_v1",
        )
        self.assertEqual(self.verification["run_id"], prepare.RUN_ID)
        self.assertFalse(self.verification["later_action_lease_active"])
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")

    def test_predecessor_identity_cannot_be_relabelled_as_p342(self) -> None:
        changed = copy.deepcopy(self.static)
        changed["run_id"] = prepare.PREDECESSOR_RUN_ID
        with self.assertRaises(candidate_static.StaticContractError):
            candidate_static.validate_result(changed)
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_p342_open_read_branch_proof(
                evidence.p341_authenticated_open_read_branch_observer_spec()
            )


if __name__ == "__main__":
    unittest.main()
