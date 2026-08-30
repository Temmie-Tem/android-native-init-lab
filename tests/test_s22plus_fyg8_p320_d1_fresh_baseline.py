from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p320_d1_fresh_baseline.py"
BINDING = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p320_d1_fresh_baseline.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p320_d1_test", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.20 D1 import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P320D1FreshBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_binding_is_canonical_and_self_bound(self):
        payload = BINDING.read_bytes()
        value = json.loads(payload)
        self.assertEqual(payload, self.module.canonical(value))
        static = self.module._validated_static_inputs()
        self.assertEqual(static["manifest"], value)
        self.assertEqual(value["schema"], self.module.BINDING_SCHEMA)
        self.assertEqual(value["ordinal"], self.module.ORDINAL)
        self.assertEqual(value["target"]["model"], "SM-S906N")
        self.assertEqual(value["target"]["codename"], "g0q")
        self.assertEqual(value["target"]["build"], "S906NKSS7FYG8")
        self.assertEqual(
            value["inputs"]["d1_source"]["sha256"],
            hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            value["independent_review"],
            {"status": "pass-go", "verdict": self.module.REVIEW_VERDICT},
        )

    def test_self_test_executes_the_pinned_p296_one_reboot_path(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            value = self.module.self_test()
        self.assertEqual(value["verdict"], "PASS_P320_D1_FRESH_BASELINE_FIXTURE_H0")
        self.assertEqual(value["reboot_count"], 1)
        self.assertEqual(value["ordinal"], self.module.ORDINAL)
        self.assertEqual(value["run_id"], self.module.P320_RUN_ID)
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_p296_source_is_exactly_bound(self):
        static = self.module._validated_static_inputs()
        primitive = static["payloads"]["p296_primitive"]
        self.assertEqual(primitive["size"], 18_578)
        self.assertEqual(primitive["sha256"], "bfec4bc9c947e098b6a18134a805524aa8fe8103edd5ddc4bc3b398895cad8ea")
        self.assertEqual(static["manifest"]["safety"]["partition_payload"], False)
        self.assertEqual(static["manifest"]["safety"]["candidate_transfer"], False)
        self.assertEqual(static["manifest"]["safety"]["f1_authorized"], False)

    def test_live_is_blocked_on_wrong_exact_approval_without_contact(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            result = self.module.main(["--live", "--approval", "bad"])
        self.assertEqual(result, 2)

    def test_fixture_transport_rejects_second_reboot_and_other_target(self):
        transport = self.module.FixtureTransport()
        with self.assertRaisesRegex(self.module.D1Error, "fixture reboot target"):
            transport.reboot_once("WRONG")
        transport.reboot_once(transport.serial)
        with self.assertRaisesRegex(self.module.D1Error, "fixture reboot target"):
            transport.reboot_once(transport.serial)
        self.assertEqual(transport.reboot_count, 1)
        self.assertEqual(transport.other_target_commands, 0)

    def test_raw_root_is_created_before_raw_capture_binding(self):
        with tempfile.TemporaryDirectory(prefix="p320-d1-raw-root-") as temporary:
            root = Path(temporary)
            with mock.patch.object(self.module, "RUN_PARENT", root / "parent"), mock.patch.object(
                self.module, "RAW_ROOT", root / "parent" / "raw"
            ):
                self.module.RUN_PARENT.mkdir(mode=0o700)
                self.module._prepare_raw_root()
                self.assertTrue(self.module.RAW_ROOT.is_dir())
                self.assertEqual(self.module.RAW_ROOT.stat().st_mode & 0o777, 0o700)

                calls = []

                class FakeClient:
                    def bind_raw_capture_dir(self, path):
                        calls.append(path)
                        assert path.is_dir()

                FakeClient.bind_raw_capture_dir(FakeClient(), self.module.RAW_ROOT)
                self.assertEqual(calls, [self.module.RAW_ROOT])


if __name__ == "__main__":
    unittest.main()
