from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import prepare_s22plus_fyg8_p331_process_v2 as prepare  # noqa: E402


class P331PrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, cls.payloads, cls.verification = prepare.build()

    def test_exact_p331_defaults_and_final_artifact_pins(self) -> None:
        self.assertEqual(prepare.P330_PREPARE_IDENTITY["size"], 9_720)
        self.assertEqual(
            prepare.P330_PREPARE_IDENTITY["sha256"],
            "17b58112a287d0ad333e8a0d408fe8e35ec54a14cf315b3e1bcc9143fc695203",
        )
        self.assertEqual(
            prepare.DEFAULT_BUILDER_OUTPUT.name,
            "stock-candidate-build-v1-20260903-03",
        )
        self.assertEqual(
            prepare.DEFAULT_STATIC_OUTPUT.name,
            "process-v2-candidate-static-20260903-03.json",
        )
        self.assertEqual(
            prepare.DEFAULT_MANIFEST_ID,
            "s22plus-fyg8-p331-process-v2-ready-1",
        )
        self.assertEqual(prepare.DEFAULT_LIVE_RUN_ID, "s22plus-fyg8-p331-live-1")
        self.assertEqual(
            prepare.DEFAULT_PROMOTION,
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p331/process-v2-promotion-20260903-01",
        )
        self.assertEqual(
            prepare.DEFAULT_MANIFEST,
            ROOT
            / "workspace/public/src/device-action/manifests/"
            "s22plus_fyg8_p331_process_v2_ready_1.json",
        )
        self.assertEqual(
            len(prepare.DEFAULT_BUILDER_OUTPUT.joinpath("result.json").read_bytes()),
            46_253,
        )
        self.assertEqual(
            prepare.identity(
                prepare.DEFAULT_BUILDER_OUTPUT.joinpath("result.json").read_bytes()
            )["sha256"],
            "39c4ae4d6c156f3cac1eed5037dd5172e5dafedf2f24238de431f4e32ceb35d4",
        )
        self.assertEqual(
            prepare.identity(prepare.DEFAULT_STATIC_OUTPUT.read_bytes())["sha256"],
            "6a895b54f47a6c939bf480e3817080e7ae28d0bb15e31925648891c198fad906",
        )
        self.assertEqual(
            prepare.DEFAULT_CANDIDATE_AP.stat().st_size,
            28_631_081,
        )
        self.assertEqual(
            prepare.identity(prepare.DEFAULT_CANDIDATE_AP.read_bytes())["sha256"],
            "729b33c3bad602e1d5863fa8cfa6a4bdf22f194a74d378f7417879897bf4d08d",
        )
        self.assertEqual(
            prepare.ROLLBACK_IDENTITY["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

    def test_manifest_binds_p331_resident_role_and_fixed_spec(self) -> None:
        self.assertEqual(self.manifest["manifest_id"], prepare.DEFAULT_MANIFEST_ID)
        self.assertEqual(self.manifest["run_id"], prepare.DEFAULT_LIVE_RUN_ID)
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")
        observation = self.manifest["observation"]
        self.assertEqual(
            observation[evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY],
            evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
        )
        observer = observation["candidate_observer"]
        self.assertEqual(observer["protocol_contract"], prepare.framed_observer.CONTRACT_ID)
        self.assertEqual(observer["diagnostic_frame_type"], 0x86)
        self.assertEqual(
            observer["diagnostic_stages"],
            [{"stage": 1, "name": "open-parsed"}, {"stage": 2, "name": "rng"}],
        )
        self.assertEqual(observer["session_cap"], 2)
        self.assertEqual(observer["reconnect_cap"], 1)
        self.assertTrue(observer["fixed_heartbeat_only"])
        self.assertTrue(observer["partial_exchange_durable"])
        self.assertTrue(observer["host_only"])
        self.assertFalse(observer["device_contact"])
        self.assertFalse(observer["caller_selected_command"])

    def test_promotion_payloads_and_offline_verification_are_p331(self) -> None:
        self.assertEqual(set(self.payloads), {"candidate_static", "run_manifest", "static_check"})
        run_manifest = json.loads(self.payloads["run_manifest"])
        self.assertEqual(
            run_manifest["schema"],
            "s22plus_fyg8_p331_process_v2_run_manifest_v1",
        )
        self.assertEqual(run_manifest["run_id"], prepare.candidate_build.P331_RUN_ID_HEX)
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P331_STOCK_OBSERVER_V4_RETAINED",
        )
        static_check = json.loads(self.payloads["static_check"])
        self.assertEqual(
            static_check["schema"],
            "s22plus_fyg8_p331_process_v2_static_result_v1",
        )
        self.assertEqual(
            static_check["verdict"],
            "PASS_P331_PROCESS_V2_STATIC_RESULT_HOST_ONLY",
        )
        self.assertTrue(static_check["safety"]["host_only"])
        self.assertFalse(static_check["safety"]["device_contact"])
        self.assertTrue(self.verification["verified"])
        self.assertEqual(
            self.verification["schema"],
            "device_action_f1_p331_stock_offline_contract_v1",
        )
        self.assertEqual(self.verification["run_id"], prepare.candidate_build.P331_RUN_ID_HEX)
        self.assertTrue(self.verification["complete_is_noncausal"])
        self.assertFalse(self.verification["candidate_success"])

    def test_predecessor_ap_is_rejected_and_audit_only_creates_nothing(self) -> None:
        self.assertNotEqual(
            prepare.DEFAULT_CANDIDATE_AP.read_bytes(),
            (
                ROOT
                / "workspace/private/outputs/s22plus_fyg8_p330/"
                "stock-candidate-build-v1-20260903-07/candidate-a/odin4/AP.tar.md5"
            ).read_bytes(),
        )
        with tempfile.TemporaryDirectory(
            prefix=".p331-prepare-test-", dir=ROOT / "workspace/private"
        ) as name:
            temporary = Path(name)
            promotion = temporary / "promotion"
            manifest = temporary / "ready.json"
            result = prepare.main(
                [
                    "--audit-only",
                    "--promotion",
                    str(promotion),
                    "--manifest",
                    str(manifest),
                ]
            )
            self.assertEqual(result, 0)
            self.assertFalse(promotion.exists())
            self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
