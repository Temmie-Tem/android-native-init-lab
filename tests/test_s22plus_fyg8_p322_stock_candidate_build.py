from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p322_stock_candidate_build.py"
)
SPEC = importlib.util.spec_from_file_location("p322_stock_candidate_build", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("P322 builder source cannot be loaded")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class P322StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result_path = builder.DEFAULT_OUTPUT_ROOT / "result.json"
        cls.payload = cls.result_path.read_bytes()
        cls.result = json.loads(cls.payload.decode("ascii"))

    def test_result_is_private_host_only_and_fresh(self) -> None:
        self.assertEqual(stat.S_IMODE(self.result_path.stat().st_mode), 0o400)
        self.assertEqual(self.result_path.stat().st_nlink, 1)
        self.assertEqual(self.result["schema"], builder.SCHEMA)
        self.assertEqual(self.result["verdict"], builder.VERDICT)
        self.assertEqual(self.result["run_id_hex"], builder.P322_RUN_ID_HEX)
        self.assertTrue(self.result["scope"]["host_only"])
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertFalse(self.result["scope"]["live_authority_created"])
        self.assertEqual(
            self.result["lineage"]["predecessor_run_id"],
            builder.artifact.P321_PREDECESSOR_RUN_ID_HEX,
        )

    def test_one_runtime_repair_and_real_ab_package_join(self) -> None:
        repair = self.result["lineage"]["runtime_repair"]
        self.assertEqual(repair["changed_anchor"], "p319_stock_bypass_to_pair")
        self.assertTrue(repair["changed_only_in_anchor"])
        self.assertFalse(repair["diagnostic_provider_widening"])
        candidate = self.result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["differs_from_consumed_p321"])
        self.assertTrue(candidate["run_id_join"]["joined"])
        self.assertEqual(candidate["run_id_join"]["a"], candidate["run_id_join"]["b"])
        self.assertEqual(candidate["overlay_members"], [
            "lib/modules/s22plus_dwc3_event_latch.ko"
        ])
        self.assertTrue(self.result["phase2"]["rollback"]["untouched"])

    def test_current_sources_reopen_existing_result(self) -> None:
        self.assertEqual(builder.audit_existing(), self.result)


if __name__ == "__main__":
    unittest.main()
