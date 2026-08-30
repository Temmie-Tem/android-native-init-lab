from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p320_process_v2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p320_promotion", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.20 promotion source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P320PromotionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.payloads, cls.verification = cls.module.build()

    def test_private_promotion_is_canonical_and_h0_only(self):
        self.assertEqual(
            set(self.payloads), {"candidate_static", "run_manifest", "static_check"}
        )
        for payload in self.payloads.values():
            self.assertIsInstance(payload, bytes)
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_result = json.loads(self.payloads["static_check"])
        self.assertEqual(
            self.module.canonical(run_manifest), self.payloads["run_manifest"]
        )
        self.assertEqual(
            self.module.canonical(static_result), self.payloads["static_check"]
        )
        self.assertEqual(run_manifest["run_id"], "c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
        self.assertFalse(static_result["safety"]["candidate_success"])
        self.assertFalse(static_result["safety"]["device_contact"])

    def test_offline_contract_reopens_p320_ap_and_sources(self):
        self.assertTrue(self.verification["verified"])
        self.assertEqual(
            self.verification["schema"],
            "device_action_f1_p320_stock_offline_contract_v1",
        )
        self.assertNotEqual(
            self.verification["candidate_ap_sha256"],
            self.module.candidate_build.P319_AP_IDENTITY["sha256"],
        )
        self.assertEqual(
            self.verification["p320_builder_result"]["sha256"],
            hashlib.sha256(
                (self.module.candidate_build.DEFAULT_OUTPUT_ROOT / "result.json").read_bytes()
            ).hexdigest(),
        )
        self.assertFalse(self.verification["causal_result_allowed"])
        self.assertFalse(self.verification["candidate_success"])
        self.assertEqual(
            self.verification["ap_payload_closure"]["run_id"],
            "c320f1e0a90b5e6d7c8a9b0c1d2e3f40",
        )

    def test_published_promotion_output_is_no_clobber_and_exact(self):
        output = self.module.DEFAULT_OUTPUT
        self.assertTrue(output.is_dir())
        for name, filename in {
            "candidate_static": "candidate-static.json",
            "run_manifest": "run-manifest.json",
            "static_check": "static-check-result.json",
        }.items():
            path = output / filename
            info = path.lstat()
            self.assertTrue(stat.S_ISREG(info.st_mode))
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
            self.assertEqual(info.st_nlink, 1)
            self.assertEqual(path.read_bytes(), self.payloads[name])


if __name__ == "__main__":
    unittest.main()
