from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p324_process_v2_candidate_static.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p324_candidate_static", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P324 candidate-static cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P324CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.output_path = cls.module.DEFAULT_OUTPUT
        cls.value = json.loads(cls.output_path.read_text(encoding="ascii"))

    def test_exact_p324_identity_and_boot_only_artifact(self) -> None:
        value = self.value
        self.assertEqual(value["run_id"], self.module.RUN_ID)
        self.assertEqual(value["predecessor_run_id"], self.module.PREDECESSOR_RUN_ID)
        self.assertEqual(value["userspace_overlay_contract_id"], self.module.OVERLAY)
        self.assertTrue(value["candidate"]["byte_identical"])
        self.assertTrue(value["candidate"]["boot_only"])
        self.assertEqual(value["candidate"]["a"]["ap_tar_md5"], value["candidate"]["b"]["ap_tar_md5"])

    def test_runtime_is_byte_equivalent_and_result_non_authorizing(self) -> None:
        runtime = self.value["runtime_repair"]
        self.assertTrue(runtime["runtime_byte_equivalent_to_p323"])
        self.assertFalse(runtime["changed_only_in_anchor"])
        self.assertTrue(runtime["acm_primary"])
        self.assertTrue(runtime["retained_path_always_continues"])
        payload = self.module.canonical(self.value)
        self.assertEqual(json.loads(payload), self.value)
        self.assertEqual(stat.S_IMODE(self.output_path.stat().st_mode), 0o400)
        self.assertFalse(self.value["safety"]["device_contact"])
        self.assertFalse(self.value["safety"]["f1_authorized"])
        self.assertFalse(self.value["safety"]["candidate_success"])

    def test_bound_reopen_matches_full_regeneration(self) -> None:
        self.assertEqual(self.module.validate_bound_result(self.value), self.value)


if __name__ == "__main__":
    unittest.main()
