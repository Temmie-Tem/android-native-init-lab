from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p320_d0_fresh_baseline.py"
BINDING = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p320_d0_fresh_baseline.json"
D1_SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p320_d1_fresh_baseline.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p320_d0_test", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.20 D0 import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P320D0FreshBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_binding_reopens_and_is_self_bound(self):
        payload = BINDING.read_bytes()
        value = json.loads(payload)
        self.assertEqual(payload, self.module.canonical(value))
        static = self.module._validated_static_inputs()
        self.assertEqual(static["manifest"], value)
        self.assertEqual(value["schema"], self.module.BINDING_SCHEMA)
        self.assertEqual(value["ordinal"], self.module.ORDINAL)
        self.assertEqual(value["target"], {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"})
        self.assertEqual(value["inputs"]["d0_source"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(value["d1_dependency"]["result_schema"], "s22plus_fyg8_p320_d1_fresh_baseline_v1_result")
        self.assertEqual(value["independent_review"], {"status": "review-pending", "verdict": None})

    def test_self_test_is_zero_device_and_rejects_p319_run_id(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            value = self.module.self_test()
        self.assertEqual(value["verdict"], "PASS_P320_D0_FRESH_BASELINE_FIXTURE_H0")
        self.assertTrue(value["raw_first"])
        self.assertTrue(value["clean_baseline"])
        self.assertTrue(value["p319_run_id_rejected"])
        self.assertEqual(value["run_id"], "c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_clean_baseline_seam_requires_p320_run_id(self):
        static = self.module._validated_static_inputs()
        adapter_payload = self.module._stable_read(self.module.ADAPTER, "P3.20 adapter", maximum=2 * 1024 * 1024)
        adapter = self.module._load_adapter(adapter_payload)
        result = self.module._classify_clean_baseline(adapter, bytes(self.module.RAW_SIZE))
        self.assertEqual(result["classification"], "ZERO_AMBIGUOUS")
        old = type("Old", (), {"P320_STOCK_RUN_ID": bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")})
        old.classify_clean_baseline = adapter.classify_clean_baseline
        with self.assertRaisesRegex(self.module.D0Error, "run ID is not bound"):
            self.module._classify_clean_baseline(old, bytes(self.module.RAW_SIZE))
        self.assertEqual(static["manifest"]["safety"]["device_writes"], False)
        self.assertEqual(static["manifest"]["safety"]["reboot"], False)

    def test_live_is_blocked_while_review_pending_without_contact(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            result = self.module.main(["--live", "--approval", "bad"])
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
