from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p322_process_v2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p322_process_v2_ready", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P322 ready builder cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P322ProcessV2ReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.manifest, cls.payloads, cls.verification = cls.module.build()

    def test_thin_wrapper_rotates_every_live_identity_and_path(self) -> None:
        module = self.module
        self.assertEqual(
            module.P321_PREPARE_IDENTITY["sha256"],
            "856014ff9772a58b3d435395baba8457e3ab9842932bd1ba097d4f52c7b475e8",
        )
        self.assertEqual(module.adapter.P321_RUN_ID_HEX, module.p322_adapter.P322_RUN_ID_HEX)
        self.assertEqual(
            module.adapter.P321_OVERLAY_CONTRACT_ID,
            module.p322_adapter.P322_OVERLAY_CONTRACT_ID,
        )
        self.assertIn("s22plus_fyg8_p322", str(module.PRIVATE_PARENT))
        self.assertNotIn("s22plus_fyg8_p321", str(module.DEFAULT_PROMOTION))
        self.assertNotIn("prepare_s22plus_fyg8_p321_bound_for_p322", sys.modules)

    def test_rehearsal_is_canonical_p322_and_not_authority(self) -> None:
        module = self.module
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_result = json.loads(self.payloads["static_check"])
        self.assertEqual(
            run_manifest["schema"], module.current_evidence.P322_RUN_MANIFEST_SCHEMA
        )
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P322_STOCK_OBSERVER_V4_RETAINED",
        )
        self.assertEqual(run_manifest["run_id"], module.p322_adapter.P322_RUN_ID_HEX)
        self.assertEqual(
            run_manifest["userspace_overlay_contract_id"],
            module.p322_adapter.P322_OVERLAY_CONTRACT_ID,
        )
        self.assertEqual(self.payloads["run_manifest"], module.canonical(run_manifest))
        self.assertEqual(self.payloads["static_check"], module.canonical(static_result))
        self.assertTrue(self.verification["verified"])
        self.assertFalse(self.verification["runtime_values_observed"])
        self.assertFalse(self.verification["candidate_success"])

    def test_ready_manifest_reopens_and_published_files_are_sealed(self) -> None:
        module = self.module
        payload = module.manifest_bytes(self.manifest)
        module.verify_manifest(self.manifest, payload, promotion_payloads=self.payloads)
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")
        self.assertEqual(self.manifest["manifest_id"], module.DEFAULT_MANIFEST_ID)
        self.assertEqual(self.manifest["run_id"], module.DEFAULT_LIVE_RUN_ID)
        if module.DEFAULT_MANIFEST.exists():
            self.assertEqual(module.DEFAULT_MANIFEST.read_bytes(), payload)
            self.assertIn(
                stat.S_IMODE(module.DEFAULT_MANIFEST.stat().st_mode), {0o644, 0o664}
            )
        if module.DEFAULT_PROMOTION.exists():
            self.assertEqual(stat.S_IMODE(module.DEFAULT_PROMOTION.stat().st_mode), 0o700)
            for name in ("candidate-static.json", "run-manifest.json", "static-check-result.json"):
                path = module.DEFAULT_PROMOTION / name
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
                self.assertEqual(path.stat().st_nlink, 1)


if __name__ == "__main__":
    unittest.main()
