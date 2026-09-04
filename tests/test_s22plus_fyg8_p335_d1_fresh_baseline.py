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
SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p335_d1_fresh_baseline.py"
BINDING = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p335_d1_fresh_baseline.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p335_d1_test", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.35 D1 import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def path_snapshot(path: Path):
    try:
        current = path.lstat()
    except FileNotFoundError:
        return None
    return (
        current.st_mode,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
        current.st_ctime_ns,
        path.read_bytes(),
    )


class P335D1FreshBaselineTest(unittest.TestCase):
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
        self.assertEqual(value["binding_id"], "s22plus-fyg8-p335-d1-fresh-baseline-v1")
        self.assertEqual(value["ordinal"], "p335-d1-fresh-baseline-1")
        self.assertTrue(str(self.module.RUN_PARENT).endswith("device-action-d1-p335-fresh-baseline"))
        self.assertEqual(value["target"]["model"], "SM-S906N")
        self.assertEqual(value["target"]["codename"], "g0q")
        self.assertEqual(value["target"]["build"], "S906NKSS7FYG8")
        self.assertEqual(value["inputs"]["d1_source"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
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
        self.assertNotEqual(self.module.P335_RUN_ID, "c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
        self.assertNotEqual(self.module.P335_RUN_ID, "c318f1e0a90b5e6d7c8a9b0c1d2e3f3b")

    def test_self_test_exercises_p296_once_without_device_contact(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            value = self.module.self_test()
        self.assertEqual(value["verdict"], "PASS_P335_D1_FRESH_BASELINE_FIXTURE_H0")
        self.assertEqual(value["reboot_count"], 1)
        self.assertEqual(value["ordinal"], "p335-d1-fresh-baseline-1")
        self.assertEqual(value["run_id"], self.module.P335_RUN_ID)
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_exact_loader_does_not_register_or_mutate_predecessor_module(self):
        before = dict(sys.modules)
        bound = self.module._load_p320()
        self.assertEqual(bound.P320_RUN_ID, self.module.P335_RUN_ID)
        self.assertEqual(bound.ORDINAL, self.module.ORDINAL)
        self.assertNotIn("s22plus_fyg8_p320_d1_bound_for_p335", sys.modules)
        for name in ("s22plus_fyg8_p320_d1_fresh_baseline", "p320_bound_p296_d1"):
            self.assertIs(sys.modules.get(name), before.get(name))

    def test_wrong_approval_stops_before_arm_or_device_contact(self):
        arm_before = path_snapshot(self.module.RUN_ARM)
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            with self.assertRaises(self.module.D1Error):
                self.module.run_live("not-the-bound-approval")
        self.assertEqual(path_snapshot(self.module.RUN_ARM), arm_before)

    def test_binding_comparison_rejects_boolean_integer_substitution(self):
        left = {"bounds": {"reboot_count": 1}}
        right = {"bounds": {"reboot_count": True}}
        self.assertFalse(self.module._typed_equal(left, right))


if __name__ == "__main__":
    unittest.main()
