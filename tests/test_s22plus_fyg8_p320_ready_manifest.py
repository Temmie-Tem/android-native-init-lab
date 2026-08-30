from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p320_ready_manifest.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p320_ready", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.20 ready-manifest source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P320ReadyManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.manifest, cls.payload = cls.module.build()

    def test_ready_manifest_is_valid_and_published_after_pass_go(self):
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")
        self.assertTrue(self.module.DEFAULT_OUTPUT.exists())
        self.assertEqual(
            self.module.DEFAULT_OUTPUT.read_bytes(), self.payload
        )
        self.assertNotEqual(
            self.manifest["candidate_ap"]["sha256"],
            self.module.candidate_build.P319_AP_IDENTITY["sha256"],
        )
        self.assertEqual(
            self.manifest["rollback_ap"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(
            self.manifest["observation"]["acceptance"]["userspace_overlay_contract_id"],
            "s22plus-fyg8-p320-observer-v4-carrier-v1",
        )
        self.assertNotIn("candidate_observer", self.manifest["observation"])

    def test_manifest_payload_is_deterministic_and_h0(self):
        self.assertEqual(self.payload, self.module._manifest_bytes(self.manifest))
        self.assertEqual(self.payload[-1:], b"\n")
        self.assertEqual(
            json.loads(self.payload.decode("ascii"))["run_id"],
            "s22plus-fyg8-p320-live-1",
        )
        self.assertEqual(
            self.module.verify_bundle(self.manifest), self.payload
        )


if __name__ == "__main__":
    unittest.main()
