from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p325_stock_candidate_build.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p325_stock_candidate_build", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P325 builder cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P325StockCandidateBuildTests(unittest.TestCase):
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
        self.assertEqual(result["run_id_hex"], self.builder.P325_RUN_ID_HEX)
        self.assertEqual(
            result["lineage"]["predecessor_run_id"],
            self.builder.P324_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertTrue(result["scope"]["host_only"])
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["scope"]["live_authority_created"])

    def test_real_ab_boot_only_join_and_fresh_identity(self) -> None:
        candidate = self.result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["differs_from_consumed_p324"])
        self.assertTrue(candidate["run_id_join"]["joined"])
        self.assertEqual(candidate["run_id_join"]["a"], candidate["run_id_join"]["b"])
        self.assertEqual(
            candidate["fixed_image_identity"]["sha256"],
            "3b605c6bd60fb515c0015357e376dd7c1e33c4bbdb8c12905dff7d2749a26d92",
        )
        self.assertEqual(
            candidate["a"]["package"]["ap_structure"]["members"],
            ["boot.img.lz4"],
        )
        self.assertTrue(candidate["a"]["package"]["safety"]["boot_only"])
        self.assertEqual(
            self.result["phase2"]["userspace"]["a"],
            self.result["phase2"]["userspace"]["b"],
        )
        self.assertTrue(self.result["phase2"]["rollback"]["untouched"])
        self.assertTrue(self.result["guard_adapter"]["observer_taxonomy_unchanged"])
        self.assertEqual(
            self.result["guard_adapter"]["source"]["sha256"],
            "13d4ba6ee935d5b7a73d06f0e4e7ef34b5ac567fbed89813113205f87f34a648",
        )

    def test_current_source_audit_reopens_without_device_contact(self) -> None:
        audited = self.builder.audit_existing()
        self.assertEqual(audited, self.result)


if __name__ == "__main__":
    unittest.main()
