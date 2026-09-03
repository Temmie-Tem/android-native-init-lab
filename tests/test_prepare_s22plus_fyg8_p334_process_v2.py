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
import device_action_f1_v2 as core  # noqa: E402
import prepare_s22plus_fyg8_p334_process_v2 as prepare  # noqa: E402


class P334PrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, cls.payloads, cls.verification = prepare.build()

    def test_manifest_binds_existing_logical_role_and_stage_zero(self) -> None:
        observation = self.manifest["observation"]
        self.assertEqual(
            observation[evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY],
            evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
        )
        self.assertEqual(
            observation["acceptance"]["userspace_overlay_contract_id"],
            evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
        )
        observer = observation["candidate_observer"]
        self.assertEqual(
            observer["diagnostic_stages"],
            [
                {"stage": 0, "name": "console-enter"},
                {"stage": 1, "name": "open-parsed"},
                {"stage": 2, "name": "rng"},
            ],
        )
        self.assertTrue(observer["entry_diagnostic_before_console"])
        self.assertFalse(observer["transport_reconnect"])

    def test_promotion_and_offline_verification_are_p334(self) -> None:
        self.assertEqual(
            set(self.payloads), {"candidate_static", "run_manifest", "static_check"}
        )
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_check = json.loads(self.payloads["static_check"])
        self.assertEqual(run_manifest["schema"], evidence.P334_RUN_MANIFEST_SCHEMA)
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P334_STOCK_OBSERVER_V4_RETAINED",
        )
        self.assertEqual(static_check["schema"], evidence.P334_STATIC_RESULT_SCHEMA)
        self.assertEqual(static_check["verdict"], evidence.P334_STATIC_RESULT_VERDICT)
        self.assertEqual(
            self.verification["schema"],
            "device_action_f1_p334_stock_offline_contract_v1",
        )
        self.assertTrue(self.verification["verified"])
        self.assertFalse(self.verification["candidate_success"])
        self.assertTrue(self.verification["entry_diagnostic_before_console"])

    def test_defaults_are_one_exact_host_only_package(self) -> None:
        self.assertEqual(
            prepare.DEFAULT_BUILDER_OUTPUT.name,
            "stock-candidate-build-v1-20260904-01",
        )
        self.assertEqual(
            prepare.DEFAULT_MANIFEST_ID,
            "s22plus-fyg8-p334-process-v2-ready-1",
        )
        self.assertEqual(
            prepare.DEFAULT_LIVE_RUN_ID,
            "s22plus-fyg8-p334-live-1",
        )
        self.assertEqual(
            prepare.ROLLBACK_IDENTITY["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")
        safety = json.loads(self.payloads["static_check"])["safety"]
        self.assertTrue(safety["host_only"])
        self.assertFalse(safety["device_contact"])
        self.assertFalse(safety["live_authorized"])

    def test_execution_source_round_trip_and_cross_wire_reject(self) -> None:
        acceptance = self.manifest["observation"]["acceptance"]
        sources = core.execution_critical_source_receipts(
            acceptance,
            candidate_arrival_proof_role=(
                evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
            ),
            bind_private_inputs=False,
        )
        core.verify_candidate_source_binding(
            acceptance, self.verification, sources
        )
        changed = copy.deepcopy(sources)
        changed["p334_first_read_rc_runtime"]["sha256"] = "0" * 64
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_source_binding(
                acceptance, self.verification, changed
            )


if __name__ == "__main__":
    unittest.main()
