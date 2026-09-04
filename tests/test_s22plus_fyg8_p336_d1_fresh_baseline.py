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
SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p336_d1_fresh_baseline.py"
BINDING = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p336_d1_fresh_baseline.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p336_d1_test", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.36 D1 import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P336D1FreshBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_binding_is_canonical_and_new_namespace(self):
        payload = BINDING.read_bytes()
        value = json.loads(payload)
        self.assertEqual(payload, self.module.canonical(value))
        static = self.module._validated_static_inputs()
        self.assertEqual(static["manifest"], value)
        self.assertEqual(value["schema"], self.module.BINDING_SCHEMA)
        self.assertEqual(value["binding_id"], "s22plus-fyg8-p336-d1-fresh-baseline-v1")
        self.assertEqual(value["ordinal"], "p336-d1-fresh-baseline-1")
        self.assertTrue(str(self.module.RUN_PARENT).endswith("device-action-d1-p336-fresh-baseline"))
        self.assertEqual(value["inputs"]["d1_source"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(value["inputs"]["p335_source"]["path"], "workspace/public/src/scripts/revalidation/s22plus_fyg8_p335_d1_fresh_baseline.py")
        self.assertEqual(
            value["independent_review"],
            {
                "status": "pass-go",
                "verdict": "PASS_GO_P336_D1_FRESH_BASELINE_H0_CAPABILITY_V1",
            },
        )
        self.assertNotIn("p335", value["binding_id"])
        self.assertNotIn("p335", value["ordinal"])
        self.assertNotIn("p335", value["run"]["parent"])

    def test_self_test_exercises_exact_reboot_fixture_without_device_contact(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            value = self.module.self_test()
        self.assertEqual(value["verdict"], "PASS_P336_D1_FRESH_BASELINE_FIXTURE_H0")
        self.assertEqual(value["reboot_count"], 1)
        self.assertEqual(value["run_id"], self.module.P336_RUN_ID)
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])
        self.assertTrue(value["p335_run_id_rejected"])

    def test_exact_loader_isolated_from_p335_and_p320_modules(self):
        before = dict(sys.modules)
        bound = self.module._load_p335()
        self.assertEqual(bound.P335_RUN_ID, self.module.P336_RUN_ID)
        self.assertEqual(bound.ORDINAL, self.module.ORDINAL)
        self.assertNotIn("s22plus_fyg8_p335_d1_bound_for_p336", sys.modules)
        for name in ("s22plus_fyg8_p335_d1_fresh_baseline", "s22plus_fyg8_p320_d1_bound_for_p335"):
            self.assertIs(sys.modules.get(name), before.get(name))

    def test_wrong_approval_stops_before_arm(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            with self.assertRaises(self.module.D1Error):
                self.module.run_live("not-the-bound-approval")
        self.assertFalse(self.module.RUN_ARM.exists())


if __name__ == "__main__":
    unittest.main()
