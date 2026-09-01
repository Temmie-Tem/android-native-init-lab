from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p324_stock_candidate_build.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p324_stock_candidate_build", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P324 builder cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P324StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_module()
        cls.output = cls.builder.DEFAULT_OUTPUT_ROOT
        cls.result_path = cls.output / "result.json"
        cls.payload = cls.result_path.read_bytes()
        cls.result = json.loads(cls.payload.decode("ascii"))

    def test_result_is_fresh_h0_private_and_predecessor_bound(self) -> None:
        result = self.result
        self.assertEqual(stat.S_IMODE(self.result_path.stat().st_mode), 0o400)
        self.assertEqual(self.result_path.stat().st_nlink, 1)
        self.assertEqual(result["schema"], self.builder.SCHEMA)
        self.assertEqual(result["verdict"], self.builder.VERDICT)
        self.assertEqual(result["run_id_hex"], self.builder.P324_RUN_ID_HEX)
        self.assertTrue(result["scope"]["host_only"])
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["scope"]["live_authority_created"])
        self.assertEqual(
            result["lineage"]["predecessor_run_id"],
            self.builder.artifact.P323_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertEqual(result["compatibility_labels"]["actual_predecessor"], "P323")

    def test_real_ab_boot_only_join_and_fresh_identity(self) -> None:
        candidate = self.result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["differs_from_consumed_p323"])
        self.assertTrue(candidate["run_id_join"]["joined"])
        self.assertEqual(candidate["run_id_join"]["a"], candidate["run_id_join"]["b"])
        self.assertEqual(
            candidate["fixed_image_identity"]["sha256"],
            "bb3e650d5444e19c55eabeedfd7accfb7c8c16142792652713f9f01980dee165",
        )
        self.assertEqual(
            self.result["phase2"]["userspace"]["a"],
            self.result["phase2"]["userspace"]["b"],
        )
        self.assertTrue(self.result["phase2"]["rollback"]["untouched"])
        self.assertTrue(self.result["preservation"]["p323_consumed_candidate_unchanged"])
        self.assertTrue(self.result["preservation"]["runtime_byte_equivalent_to_p323"])

    def test_current_source_audit_reopens_without_device_contact(self) -> None:
        audited = self.builder.audit_existing()
        self.assertEqual(audited, self.result)


if __name__ == "__main__":
    unittest.main()
