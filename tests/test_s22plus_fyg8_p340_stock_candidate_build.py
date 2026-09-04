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

import s22plus_fyg8_p340_stock_candidate_build as builder  # noqa: E402


class P340StockCandidateBuildTests(unittest.TestCase):
    def test_existing_build_reopens_and_audits_host_only(self) -> None:
        result = builder.audit_existing(builder.DEFAULT_OUTPUT_ROOT)
        self.assertEqual(result["run_id_hex"], builder.P340_RUN_ID_HEX)
        self.assertEqual(result["scope"]["tier"], "H0")
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["scope"]["live_authority_created"])
        self.assertTrue(result["phase2"]["candidate"]["byte_identical"])
        self.assertTrue(result["phase2"]["candidate"]["ab_artifact_identity_equal"])
        self.assertTrue(result["phase2"]["candidate"]["differs_from_consumed_p339"])
        self.assertEqual(result["phase2"]["candidate"]["run_id_join"]["run_id_hex"], builder.P340_RUN_ID_HEX)
        self.assertEqual(result["phase2"]["candidate"]["a"]["ap_tar_md5"], result["phase2"]["candidate"]["b"]["ap_tar_md5"])
        self.assertNotEqual(result["phase2"]["candidate"]["a"]["ap_tar_md5"], builder.P339_AP_IDENTITY)
        self.assertEqual(result["phase2"]["rollback"]["artifact_identity"]["identity"], builder.ROLLBACK_IDENTITY)
        self.assertEqual(result["phase2"]["candidate"]["run_id_join"]["image_run_id_hex"], builder.P340_RUN_ID_HEX)
        self.assertEqual(result["phase2"]["candidate"]["run_id_join"]["init_run_id_hex"], builder.P340_RUN_ID_HEX)


if __name__ == "__main__":
    unittest.main()
