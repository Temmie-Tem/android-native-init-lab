from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
for directory in (
    ROOT / "workspace/public/src/scripts/analysis",
    ROOT / "workspace/public/src/scripts/revalidation",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import prepare_s22plus_fyg8_p340_process_v2 as prepare  # noqa: E402
import s22plus_fyg8_p340_process_v2_candidate_static as candidate_static  # noqa: E402


class P340ProcessV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.static = candidate_static.build_result()
        cls.static_payload = candidate_static.canonical(cls.static)
        cls.manifest, cls.payloads, cls.verification = prepare.build()

    def test_static_reopens_fresh_candidate_and_collector(self) -> None:
        self.assertEqual(
            self.static["schema"],
            "s22plus_fyg8_p340_process_v2_candidate_static_v1",
        )
        self.assertEqual(self.static["run_id"], prepare.RUN_ID)
        self.assertEqual(self.static["predecessor_run_id"], prepare.PREDECESSOR_RUN_ID)
        candidate = self.static["candidate"]
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertTrue(candidate["boot_only"])
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertNotEqual(
            candidate["a"]["ap_tar_md5"],
            {"size": 28_631_081, "sha256": "80830eed6818528577e3dd5d68af79743b55a014b1dd4e2c8a3c5f54711b47d3"},
        )
        self.assertIn("p340_open_failure_capture", self.static["source_closure"])
        self.assertIn("latch", self.static["source_closure"])
        self.assertFalse(self.static["safety"]["device_contact"])
        self.assertFalse(self.static["safety"]["f1_authorized"])

    def test_static_stored_receipt_round_trips_exactly(self) -> None:
        stored = candidate_static.DEFAULT_OUTPUT.read_bytes()
        self.assertEqual(stored, self.static_payload)
        self.assertEqual(
            candidate_static.canonical(candidate_static.validate_result(json.loads(stored))),
            self.static_payload,
        )

    def test_prepare_emits_three_payloads_and_reopens_registered_contract(self) -> None:
        self.assertEqual(
            set(self.payloads), {"candidate_static", "run_manifest", "static_check"}
        )
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_check = json.loads(self.payloads["static_check"])
        self.assertEqual(run_manifest["schema"], prepare.RUN_MANIFEST_SCHEMA)
        self.assertEqual(run_manifest["run_id"], prepare.RUN_ID)
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P340_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE",
        )
        self.assertEqual(static_check["schema"], prepare.STATIC_RESULT_SCHEMA)
        self.assertEqual(static_check["verdict"], prepare.STATIC_RESULT_VERDICT)
        self.assertTrue(static_check["candidate"]["boot_only_ap"])
        self.assertFalse(static_check["safety"]["device_contact"])
        self.assertTrue(self.verification["common_offline_verified"])
        self.assertEqual(
            self.verification["schema"],
            "device_action_f1_p340_stock_offline_contract_v1",
        )
        self.assertEqual(self.verification["run_id"], prepare.RUN_ID)
        self.assertEqual(
            self.verification["userspace_overlay_contract_id"],
            prepare.adapter.OVERLAY_CONTRACT_ID,
        )
        self.assertNotIn("common_registration_pending", self.verification)
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")
        self.assertFalse(self.manifest["observation"]["acceptance"]["auth_key"] is None)

    def test_prepare_audit_only_does_not_publish(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix=".p340-prepare-test-", dir=ROOT / "workspace/private"
        ) as name:
            temporary = Path(name)
            promotion = temporary / "promotion"
            manifest = temporary / "manifest.json"
            self.assertEqual(
                prepare.main(
                    [
                        "--audit-only",
                        "--promotion",
                        str(promotion),
                        "--manifest",
                        str(manifest),
                    ]
                ),
                0,
            )
            self.assertFalse(promotion.exists())
            self.assertFalse(manifest.exists())

    def test_mutated_static_run_id_is_rejected(self) -> None:
        changed = copy.deepcopy(self.static)
        changed["run_id"] = prepare.PREDECESSOR_RUN_ID
        with self.assertRaises(candidate_static.StaticContractError):
            candidate_static.validate_result(changed)


if __name__ == "__main__":
    unittest.main()
