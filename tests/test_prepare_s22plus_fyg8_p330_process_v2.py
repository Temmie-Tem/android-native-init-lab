from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import prepare_s22plus_fyg8_p330_process_v2 as prepare  # noqa: E402


class P330PrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, cls.payloads, cls.verification = prepare.build()

    def test_exact_p330_defaults_and_published_outputs(self) -> None:
        self.assertEqual(prepare.P329_PREPARE_IDENTITY["size"], 7_846)
        self.assertEqual(
            prepare.P329_PREPARE_IDENTITY["sha256"],
            "c33663f9e30d63599dcf71d9f30fb5b3e30eac204b137bbad8c413efdf3357a0",
        )
        self.assertEqual(
            prepare.DEFAULT_BUILDER_OUTPUT.name,
            "stock-candidate-build-v1-20260903-07",
        )
        self.assertEqual(prepare.DEFAULT_MANIFEST_ID, "s22plus-fyg8-p330-process-v2-ready-1")
        self.assertEqual(prepare.DEFAULT_LIVE_RUN_ID, "s22plus-fyg8-p330-live-1")
        self.assertEqual(
            prepare.DEFAULT_MANIFEST.read_bytes(),
            prepare.manifest_bytes(self.manifest),
        )
        for key, filename in {
            "candidate_static": "candidate-static.json",
            "run_manifest": "run-manifest.json",
            "static_check": "static-check-result.json",
        }.items():
            self.assertEqual(
                (prepare.DEFAULT_PROMOTION / filename).read_bytes(),
                self.payloads[key],
            )

    def test_manifest_binds_p330_diagnostic_role(self) -> None:
        self.assertEqual(self.manifest["manifest_id"], prepare.DEFAULT_MANIFEST_ID)
        self.assertEqual(self.manifest["run_id"], prepare.DEFAULT_LIVE_RUN_ID)
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")
        observation = self.manifest["observation"]
        self.assertEqual(
            observation[prepare._INNER.evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY],
            prepare._INNER.evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
        )
        observer = observation["candidate_observer"]
        self.assertEqual(observer["protocol_contract"], prepare.framed_observer.CONTRACT_ID)
        self.assertEqual(observer["diagnostic_frame_type"], 0x86)
        self.assertEqual(observer["diagnostic_stages"], [{"stage": 1, "name": "open-parsed"}, {"stage": 2, "name": "rng"}])
        self.assertTrue(observer["partial_exchange_durable"])
        self.assertTrue(observer["host_only"])
        self.assertFalse(observer["device_contact"])

    def test_promotion_payloads_and_offline_verification_are_p330(self) -> None:
        self.assertEqual(set(self.payloads), {"candidate_static", "run_manifest", "static_check"})
        run_manifest = json.loads(self.payloads["run_manifest"])
        self.assertEqual(
            run_manifest["schema"],
            "s22plus_fyg8_p330_process_v2_run_manifest_v1",
        )
        self.assertEqual(run_manifest["run_id"], prepare.candidate_build.P330_RUN_ID_HEX)
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P330_STOCK_OBSERVER_V4_RETAINED",
        )
        static_check = json.loads(self.payloads["static_check"])
        self.assertEqual(
            static_check["schema"],
            "s22plus_fyg8_p330_process_v2_static_result_v1",
        )
        self.assertEqual(
            static_check["verdict"],
            "PASS_P330_PROCESS_V2_STATIC_RESULT_HOST_ONLY",
        )
        self.assertTrue(static_check["safety"]["host_only"])
        self.assertFalse(static_check["safety"]["device_contact"])
        self.assertTrue(self.verification["verified"])
        self.assertEqual(
            self.verification["schema"],
            "device_action_f1_p330_stock_offline_contract_v1",
        )
        self.assertEqual(self.verification["run_id"], prepare.candidate_build.P330_RUN_ID_HEX)
        self.assertTrue(self.verification["complete_is_noncausal"])
        self.assertFalse(self.verification["candidate_success"])
        self.assertEqual(
            self.verification["p330_authenticated_observer_source"]["size"],
            15_035,
        )
        self.assertEqual(
            self.verification["p330_authenticated_runtime_source"]["size"],
            8_818,
        )

    def test_exact_rollback_and_candidate_ap_are_preserved(self) -> None:
        self.assertEqual(
            self.manifest["candidate_ap"]["sha256"],
            "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b",
        )
        self.assertEqual(
            self.manifest["rollback_ap"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(self.manifest["allowed_member"], "boot.img.lz4")
        self.assertFalse(self.verification["causal_result_allowed"])


if __name__ == "__main__":
    unittest.main()
