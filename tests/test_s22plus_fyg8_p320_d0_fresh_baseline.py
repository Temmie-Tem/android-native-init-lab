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
SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p320_d0_fresh_baseline.py"
BINDING = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p320_d0_fresh_baseline_2.json"
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
        self.assertEqual(value["ordinal"], "p320-d0-fresh-baseline-2")
        self.assertTrue(str(self.module.RUN_PARENT).endswith("device-action-d0-p320-fresh-baseline-2"))
        self.assertEqual(value["target"], {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"})
        self.assertEqual(value["inputs"]["d0_source"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(value["d1_dependency"]["result_schema"], "s22plus_fyg8_p320_d1_fresh_baseline_v1_result")
        self.assertEqual(
            value["independent_review"],
            {"status": "pass-go", "verdict": self.module.REVIEW_VERDICT},
        )

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

    def test_live_is_blocked_on_wrong_exact_approval_without_contact(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("device/process call")):
            result = self.module.main(["--live", "--approval", "bad"])
        self.assertEqual(result, 2)

    def test_pretty_target_profile_uses_strict_document_parser(self):
        payload = self.module.PROFILE.read_bytes()
        profile = self.module._strict_document(payload, "S22+ target profile")
        self.assertEqual(profile["target"]["device"], "g0q")
        self.assertNotEqual(payload, self.module.canonical(profile))
        with self.assertRaisesRegex(self.module.D0Error, "canonical object"):
            self.module._strict(payload, "canonical binding")
        for hostile in (b'{"target":{},"target":{}}', b'{"value":Infinity}'):
            with self.subTest(hostile=hostile), self.assertRaises(self.module.D0Error):
                self.module._strict_document(hostile, "hostile profile")

    def test_snapshot_inside_run_directory_is_reachable_after_single_creation(self):
        payload = b"fixture-adb"
        with tempfile.TemporaryDirectory(prefix="p320-d0-snapshot-") as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            snapshot = run_dir / "adb-snapshot"
            with mock.patch.object(self.module, "HOST_ADB_SIZE", len(payload)), mock.patch.object(
                self.module, "HOST_ADB_SHA256", hashlib.sha256(payload).hexdigest()
            ):
                run_dir.mkdir(mode=0o700)
                self.module._prepare_snapshot(payload, snapshot)
                self.assertEqual(snapshot.read_bytes(), payload)
                self.assertEqual(snapshot.stat().st_mode & 0o777, 0o500)

    def test_d1_result_validator_requires_full_continuity_before_device_reads(self):
        static = self.module._validated_static_inputs()
        binding_payload = self.module._stable_read(
            self.module.D1_BINDING, "P3.20 D1 binding", maximum=256 * 1024
        )
        serial_sha = static["d1_binding"]["target"]["adb_serial_sha256"]
        base = {
            "schema": "s22plus_fyg8_p320_d1_fresh_baseline_v1_result",
            "verdict": "PASS_P320_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH",
            "execution_manifest": self.module._receipt(self.module.D1_BINDING, binding_payload),
            "ordinal": static["d1_binding"]["ordinal"],
            "run_id": self.module.P320_RUN_ID,
            "run_directory": static["manifest"]["d1_dependency"]["result"].rsplit("/", 1)[0],
            "reboot_count": 1,
            "selection": {
                "inventory_count": 1,
                "inventory_models": ["SM_S906N"],
                "inventory_sha256": "c" * 64,
                "selected_serial_sha256": serial_sha,
                "selected_topology_sha256": "d" * 64,
                "other_targets_commanded": False,
            },
            "before": {"boot_id_sha256": "a" * 64},
            "after": {"boot_id_sha256": "b" * 64},
            "device_contact": True,
            "live_authorized": True,
            "device_writes": False,
            "candidate_transfer": False,
            "partition_transfer": False,
            "odin_invoked": False,
            "download_transition_requested": False,
            "f1_authorized": False,
            "other_targets_commanded": False,
        }
        self.module._validate_d1_value(base, static, binding_payload)
        for key, bad in (("device_contact", False), ("live_authorized", False), ("candidate_transfer", True), ("partition_transfer", True)):
            mutated = dict(base)
            mutated[key] = bad
            with self.subTest(key=key), self.assertRaises(self.module.D0Error):
                self.module._validate_d1_value(mutated, static, binding_payload)
        equal_boot = dict(base)
        equal_boot["after"] = {"boot_id_sha256": "a" * 64}
        with self.assertRaisesRegex(self.module.D0Error, "changed boot"):
            self.module._validate_d1_value(equal_boot, static, binding_payload)


if __name__ == "__main__":
    unittest.main()
