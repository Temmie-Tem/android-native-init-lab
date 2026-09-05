from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for path in (ANALYSIS, REVALIDATION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import s22plus_fyg8_p342_stock_candidate_build as builder  # noqa: E402


class P342StockCandidateBuildTests(unittest.TestCase):
    def test_existing_build_reopens_and_audits_real_ab_joins_host_only(self) -> None:
        result = builder.audit_existing(builder.DEFAULT_OUTPUT_ROOT)
        self.assertEqual(result["run_id_hex"], builder.P342_RUN_ID_HEX)
        self.assertEqual(result["scope"]["tier"], "H0")
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["scope"]["live_authority_created"])
        candidate = result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["ab_artifact_identity_equal"])
        self.assertTrue(candidate["differs_from_consumed_p341"])
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], builder.P342_RUN_ID_HEX)
        self.assertEqual(candidate["a"]["ap_tar_md5"], candidate["b"]["ap_tar_md5"])
        self.assertNotEqual(candidate["a"]["ap_tar_md5"], builder.P341_AP_IDENTITY)
        self.assertEqual(candidate["a"]["ap_tar_md5"], builder.artifact.P342_AP_IDENTITY)
        self.assertEqual(candidate["run_id_join"]["image_run_id_hex"], builder.P342_RUN_ID_HEX)
        self.assertEqual(candidate["run_id_join"]["init_run_id_hex"], builder.P342_RUN_ID_HEX)
        self.assertTrue(result["preservation"]["runtime_behavior_unchanged"])
        self.assertEqual(result["preservation"]["same_fd_session_count"], 3)
        self.assertEqual(result["preservation"]["idle_seconds"], 120)
        self.assertEqual(result["preservation"]["total_command_count"], 12)


if __name__ == "__main__":
    unittest.main()
