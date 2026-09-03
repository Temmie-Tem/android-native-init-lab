from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p335_d0_fresh_baseline.py"
BINDING = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p335_d0_fresh_baseline.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p335_d0_test", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.35 D0 import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P335D0FreshBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_binding_is_canonical_and_reopens_only_new_p335_d1(self):
        payload = BINDING.read_bytes()
        value = json.loads(payload)
        self.assertEqual(payload, self.module.canonical(value))
        static = self.module._validated_static_inputs()
        self.assertEqual(static["manifest"], value)
        self.assertEqual(value["schema"], self.module.BINDING_SCHEMA)
        self.assertEqual(value["binding_id"], "s22plus-fyg8-p335-d0-fresh-baseline-v1")
        self.assertEqual(value["ordinal"], "p335-d0-fresh-baseline-1")
        self.assertTrue(str(self.module.RUN_PARENT).endswith("device-action-d0-p335-fresh-baseline"))
        self.assertEqual(value["d1_dependency"]["binding"], "workspace/public/src/device-action/bindings/s22plus_fyg8_p335_d1_fresh_baseline.json")
        self.assertEqual(value["d1_dependency"]["result_schema"], self.module.D1_RESULT_SCHEMA)
        self.assertEqual(value["inputs"]["d0_source"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(
            value["independent_review"],
            {
                "status": "pass-go",
                "verdict": self.module.REVIEW_VERDICT,
            },
        )
        self.assertNotIn("p320", value["binding_id"])
        self.assertNotIn("p320", value["ordinal"])
        self.assertNotIn("p320", value["run"]["parent"])

    def test_self_test_is_raw_first_clean_baseline_without_device_contact(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            value = self.module.self_test()
        self.assertEqual(value["verdict"], "PASS_P335_D0_FRESH_BASELINE_FIXTURE_H0")
        self.assertTrue(value["raw_first"])
        self.assertTrue(value["clean_baseline"])
        self.assertTrue(value["p335_d1_dependency"])
        self.assertEqual(value["run_id"], self.module.P335_RUN_ID)
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_clean_baseline_seam_rejects_predecessor_run_id(self):
        static = self.module._validated_static_inputs()
        adapter_payload = self.module._stable(
            self.module.ADAPTER,
            "P3.35 adapter",
            maximum=2 * 1024 * 1024,
            expected=static["payloads"]["adapter"],
        )
        bound = self.module._load_p320()
        adapter = bound._load_adapter(adapter_payload)
        value = self.module._classify_clean_baseline(adapter, bytes(self.module.RAW_SIZE))
        self.assertEqual(value["classification"], "ZERO_AMBIGUOUS")
        self.assertTrue(value["baseline_clean"])

        for old_run_id in (
            "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b",
            "c320f1e0a90b5e6d7c8a9b0c1d2e3f40",
        ):
            with self.subTest(old_run_id=old_run_id):
                old = type("OldAdapter", (), {"STOCK_RUN_ID": bytes.fromhex(old_run_id)})
                with self.assertRaisesRegex(self.module.D0Error, "run ID is not bound"):
                    self.module._classify_clean_baseline(old(), bytes(self.module.RAW_SIZE))

    def test_exact_loader_isolated_and_wrong_approval_has_no_arm(self):
        before = dict(sys.modules)
        bound = self.module._load_p320()
        self.assertEqual(bound.P320_RUN_ID, self.module.P335_RUN_ID)
        self.assertNotIn("s22plus_fyg8_p320_d0_bound_for_p335", sys.modules)
        for name in ("s22plus_fyg8_p320_d0_fresh_baseline", "p320_stock_adapter_bound"):
            self.assertIs(sys.modules.get(name), before.get(name))
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            with self.assertRaises(self.module.D0Error):
                self.module.run_live("not-the-bound-approval")
        self.assertFalse(self.module.RUN_ARM.exists())

    def test_binding_comparison_rejects_boolean_integer_substitution(self):
        left = {"bounds": {"observer_read_count": 1}}
        right = {"bounds": {"observer_read_count": True}}
        self.assertFalse(self.module._typed_equal(left, right))


if __name__ == "__main__":
    unittest.main()
