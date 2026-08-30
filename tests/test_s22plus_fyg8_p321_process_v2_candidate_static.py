from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p321_process_v2_candidate_static.py"
)
SPEC = importlib.util.spec_from_file_location("p321_candidate_static", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("P3.21 static source cannot be loaded")
static = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(static)


OUTPUT = static.DEFAULT_OUTPUT


class P321CandidateStaticTests(unittest.TestCase):
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
        self.assertEqual(self.result["run_id"], static.P321_RUN_ID)
        self.assertFalse(self.result["ready_manifest_created"])
        self.assertFalse(self.result["run_manifest_created"])
        self.assertFalse(self.result["approval_created"])
        self.assertTrue(self.result["safety"]["host_only"])
        self.assertFalse(self.result["safety"]["device_contact"])
        self.assertFalse(self.result["safety"]["live_authorized"])

    def test_receipt_binds_minus_02_and_real_ab_join(self) -> None:
        builder = self.result["builder_result"]
        self.assertTrue(builder["path"].endswith(
            "s22plus_fyg8_p321/stock-candidate-build-v1-20260831-02/result.json"
        ))
        candidate = self.result["candidate"]
        self.assertTrue(candidate["boot_only"])
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["run_id_join"]["joined"])
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], static.P321_RUN_ID)
        self.assertEqual(candidate["run_id_join"]["a"], candidate["run_id_join"]["b"])
        self.assertEqual(
            set(self.result["source_closure"]),
            {
                "p321_candidate_static",
                "p321_stock_candidate_build",
                "p321_stock_process_v2_adapter",
                "p321_artifact_identity",
                "p319_fixed_image",
                "p319_rollback_ap",
            },
        )

    def test_receipt_regenerates_exactly_from_current_sources(self) -> None:
        self.assertEqual(static.validate_result(self.result), self.result)
        self.assertEqual(static.validate_bound_result(self.result), self.result)
        self.assertEqual(self.payload, static.canonical(self.result))


if __name__ == "__main__":
    unittest.main()
