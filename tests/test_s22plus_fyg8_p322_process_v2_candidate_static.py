from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p322_process_v2_candidate_static.py"
)
SPEC = importlib.util.spec_from_file_location("p322_candidate_static", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("P3.22 static source cannot be loaded")
static = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(static)


OUTPUT = static.DEFAULT_OUTPUT


class P322CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = OUTPUT.read_bytes()
        cls.result = json.loads(cls.payload.decode("ascii"))

    def test_receipt_is_private_host_only_and_not_ready(self) -> None:
        mode = stat.S_IMODE(OUTPUT.stat().st_mode)
        self.assertEqual(mode, 0o400)
        self.assertEqual(OUTPUT.stat().st_nlink, 1)
        self.assertEqual(self.result["schema"], static.SCHEMA)
        self.assertEqual(self.result["verdict"], static.VERDICT)
        self.assertEqual(self.result["target"], static.TARGET)
        self.assertEqual(self.result["run_id"], static.P322_RUN_ID)
        self.assertFalse(self.result["ready_manifest_created"])
        self.assertFalse(self.result["run_manifest_created"])
        self.assertFalse(self.result["approval_created"])
        self.assertTrue(self.result["safety"]["host_only"])
        self.assertFalse(self.result["safety"]["device_contact"])
        self.assertFalse(self.result["safety"]["live_authorized"])
        self.assertFalse(self.result["safety"]["candidate_success"])

    def test_receipt_binds_final_builder_and_real_ab_join(self) -> None:
        builder = self.result["builder_result"]
        self.assertTrue(builder["path"].endswith(
            "s22plus_fyg8_p322/stock-candidate-build-v1-20260831-02/result.json"
        ))
        self.assertEqual(builder["size"], static.P322_BUILDER_RESULT_IDENTITY["size"])
        self.assertEqual(builder["sha256"], static.P322_BUILDER_RESULT_IDENTITY["sha256"])
        candidate = self.result["candidate"]
        self.assertTrue(candidate["boot_only"])
        self.assertTrue(candidate["byte_identical"])
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], static.P322_RUN_ID)
        self.assertTrue(candidate["run_id_join"]["joined"])
        self.assertEqual(candidate["run_id_join"]["a"], candidate["run_id_join"]["b"])
        self.assertEqual(
            candidate["run_id_join"]["a"]["ap"], static.P322_AP_IDENTITY
        )
        self.assertEqual(
            set(self.result["source_closure"]),
            {
                "p322_candidate_static",
                "p322_stock_candidate_build",
                "p322_stock_process_v2_adapter",
                "p322_artifact_identity",
                "p322_runtime_repair",
                "p319_fixed_image",
                "p319_rollback_ap",
            },
        )

    def test_adapter_artifact_and_one_function_repair_receipts_are_bound(self) -> None:
        adapter = self.result["adapter"]
        self.assertEqual(adapter["lineage"]["run_id"], static.P322_RUN_ID)
        self.assertEqual(
            adapter["lineage"]["predecessor_run_id_rejected"], static.P321_RUN_ID
        )
        self.assertEqual(adapter["lineage"]["overlay_contract_id"], static.OVERLAY)
        self.assertEqual(adapter["acceptance"]["run_id"], static.P322_RUN_ID)
        self.assertFalse(adapter["acceptance"]["causal_result_allowed"])
        self.assertFalse(adapter["acceptance"]["candidate_success"])

        artifact = self.result["artifact_identity"]
        self.assertEqual(artifact["candidate_a"]["ap"], static.P322_AP_IDENTITY)
        self.assertEqual(artifact["candidate_a"], artifact["candidate_b"])
        self.assertEqual(artifact["rollback"]["identity"], static.ROLLBACK_IDENTITY)

        repair = self.result["runtime_repair"]
        self.assertEqual(repair["changed_anchor"], "p319_stock_bypass_to_pair")
        self.assertTrue(repair["changed_only_in_anchor"])
        self.assertFalse(repair["diagnostic_provider_widening"])

    def test_receipt_regenerates_exactly_and_rejects_run_mutation(self) -> None:
        self.assertEqual(static.canonical(self.result), self.payload)
        self.assertEqual(static.validate_result(self.result), self.result)
        self.assertEqual(static.validate_bound_result(self.result), self.result)

        mutated = copy.deepcopy(self.result)
        mutated["run_id"] = static.P321_RUN_ID
        with self.assertRaises(static.StaticContractError):
            static.validate_bound_result(mutated)


if __name__ == "__main__":
    unittest.main()
