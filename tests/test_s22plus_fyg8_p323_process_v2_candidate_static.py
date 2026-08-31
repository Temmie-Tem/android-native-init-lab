from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p323_process_v2_candidate_static.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p323_candidate_static", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P323 candidate-static cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P323CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.value = cls.module.build_result()

    def test_exact_p323_identity_and_boot_only_artifact(self) -> None:
        value = self.value
        self.assertEqual(value["run_id"], self.module.RUN_ID)
        self.assertEqual(value["userspace_overlay_contract_id"], self.module.OVERLAY)
        self.assertTrue(value["candidate"]["byte_identical"])
        self.assertTrue(value["candidate"]["boot_only"])
        self.assertEqual(value["candidate"]["a"]["ap_tar_md5"], self.module.AP_IDENTITY)

    def test_runtime_delta_is_acm_primary_and_carrier_continues(self) -> None:
        runtime = self.value["runtime_repair"]
        self.assertTrue(runtime["changed_only_in_anchor"])
        self.assertTrue(runtime["acm_primary"])
        self.assertTrue(runtime["retained_path_always_continues"])
        self.assertFalse(runtime["scientific_result_claimed_by_banner"])

    def test_result_is_canonical_and_non_authorizing(self) -> None:
        payload = self.module.canonical(self.value)
        self.assertEqual(json.loads(payload), self.value)
        self.assertFalse(self.value["safety"]["device_contact"])
        self.assertFalse(self.value["safety"]["f1_authorized"])
        self.assertFalse(self.value["safety"]["candidate_success"])

    def test_bound_reopen_matches_full_regeneration(self) -> None:
        self.assertEqual(self.module.validate_bound_result(self.value), self.value)


if __name__ == "__main__":
    unittest.main()
