from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p323_stock_candidate_build.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p323_stock_candidate_build", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P323 builder cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P323StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_module()
        cls.result_path = cls.builder.DEFAULT_OUTPUT_ROOT / "result.json"
        cls.payload = cls.result_path.read_bytes()
        cls.result = json.loads(cls.payload.decode("ascii"))

    def test_result_is_fresh_h0_and_private(self) -> None:
        result = self.result
        self.assertEqual(stat.S_IMODE(self.result_path.stat().st_mode), 0o400)
        self.assertEqual(self.result_path.stat().st_nlink, 1)
        self.assertEqual(result["schema"], self.builder.SCHEMA)
        self.assertEqual(result["verdict"], self.builder.VERDICT)
        self.assertEqual(result["run_id_hex"], self.builder.P323_RUN_ID_HEX)
        self.assertTrue(result["scope"]["host_only"])
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["scope"]["live_authority_created"])
        self.assertEqual(
            result["lineage"]["predecessor_run_id"],
            self.builder.artifact.P322_PREDECESSOR_RUN_ID_HEX,
        )

    def test_acm_runtime_delta_and_real_ab_boot_join(self) -> None:
        result = self.result
        repair = result["lineage"]["runtime_repair"]
        self.assertEqual(repair["changed_anchor"], "p319_stock_publish")
        self.assertTrue(repair["changed_only_in_anchor"])
        self.assertTrue(repair["acm_primary"])
        self.assertTrue(repair["retained_path_always_continues"])
        candidate = result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["differs_from_consumed_p322"])
        self.assertTrue(candidate["run_id_join"]["joined"])
        self.assertEqual(candidate["run_id_join"]["a"], candidate["run_id_join"]["b"])
        self.assertTrue(result["phase2"]["rollback"]["untouched"])
        self.assertTrue(result["preservation"]["p322_consumed_candidate_unchanged"])
        self.assertTrue(result["preservation"]["p322_source_closure_reopened"])
        self.assertNotIn("p321_consumed_candidate_unchanged", result["preservation"])
        self.assertIn("native PID-1/USB arrival", result["limitations"][1])

    def test_current_source_audit_reopens_without_device_contact(self) -> None:
        audited = self.builder.audit_existing()
        self.assertEqual(audited, self.result)


if __name__ == "__main__":
    unittest.main()
