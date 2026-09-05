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

import s22plus_fyg8_p344_stock_candidate_build as builder  # noqa: E402


class P344StockCandidateBuildTests(unittest.TestCase):
    def test_existing_build_reopens_real_ab_join_and_identity_only_runtime(self) -> None:
        result = builder.audit_existing(builder.DEFAULT_OUTPUT_ROOT)
        self.assertEqual(result["run_id_hex"], builder.P344_RUN_ID_HEX)
        self.assertEqual(result["scope"]["tier"], "H0")
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["scope"]["live_authority_created"])
        candidate = result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["ab_artifact_identity_equal"])
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], builder.P344_RUN_ID_HEX)
        self.assertEqual(candidate["a"]["ap_tar_md5"], candidate["b"]["ap_tar_md5"])
        self.assertEqual(candidate["a"]["ap_tar_md5"], builder.artifact.P344_AP_IDENTITY)
        self.assertEqual(candidate["run_id_join"]["image_run_id_hex"], builder.P344_RUN_ID_HEX)
        self.assertEqual(candidate["run_id_join"]["init_run_id_hex"], builder.P344_RUN_ID_HEX)
        self.assertFalse(result["catalog_allowlist_expanded"])
        self.assertTrue(result["catalog_unchanged"])
        self.assertEqual(result["catalog_allowlist_actions"], list(builder.runtime.CATALOG_ACTIONS))
        self.assertTrue(result["runtime_delta_identity_only"])
        self.assertTrue(result["runtime_behavior_unchanged"])
        self.assertTrue(result["preservation"]["idle_listener_unchanged"])
        self.assertEqual(result["preservation"]["same_fd_session_count"], 3)
        self.assertEqual(result["preservation"]["idle_seconds"], 120)
        self.assertEqual(result["preservation"]["total_command_count"], 12)
        self.assertEqual(
            result["resident"]["resident_lease_schema"],
            "s22plus_fyg8_p344_exploration_lease_v1",
        )


if __name__ == "__main__":
    unittest.main()
