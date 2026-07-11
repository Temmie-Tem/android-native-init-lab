import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


BUILD_SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "build_s22plus_v3442_debug_level_setter.py"
)
LIVE_SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3442_high_set_only_live_gate.py"
)
SOURCE = Path(
    "workspace/public/src/native-init/s22plus_reboot_debug_level_v3442.S"
)
MANIFEST = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3442_debug_level_setter_v0_1/manifest.json"
)


def load_module(path: Path, name: str):
    script_dir = str(path.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class V3442HighSetOnlyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_module(BUILD_SCRIPT, "build_s22plus_v3442_test")
        cls.gate = load_module(LIVE_SCRIPT, "s22plus_v3442_gate_test")

    def test_source_contains_both_exact_reboot_reasons(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('.asciz "debug0x4948"', text)
        self.assertIn('.asciz "debug0x494d"', text)
        self.assertEqual(text.count("svc     #0"), 3)
        self.assertNotIn("/dev/", text)
        self.assertNotIn("/proc/", text)

    def test_manifest_pins_first_syscall_and_no_dangerous_actions(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["hashes"]["setter"], self.gate.EXPECTED_SETTER_SHA256)
        self.assertEqual(data["hashes"]["source"], self.gate.EXPECTED_SETTER_SOURCE_SHA256)
        safety = data["safety"]
        self.assertEqual(safety["valid_path_first_syscall"], "reboot")
        self.assertFalse(safety["block_write"])
        self.assertFalse(safety["flash"])
        self.assertFalse(safety["panic"])
        self.assertFalse(safety["rdx_protocol"])

    def test_classification_uses_sysfs_and_bootloader_value(self):
        classify = self.gate.classify_high_state
        self.assertEqual(
            classify({"debug_level": "18760", "boot_debug_level": "0x4948"}),
            "HIGH_ACCEPTED",
        )
        self.assertEqual(
            classify({"debug_level": "18765", "boot_debug_level": "0x4948"}),
            "HIGH_PARTIAL_OR_MIXED_ACCEPTANCE",
        )
        self.assertEqual(
            classify({"debug_level": "18765", "boot_debug_level": "0x494d"}),
            "HIGH_CLAMPED_OR_REJECTED_TO_MID",
        )

    def test_partial_boot_empty_partition_sha_fails_closed(self):
        self.assertEqual(
            self.gate.parse_partition_sha256("a" * 64 + "  /dev/boot", "boot"),
            "a" * 64,
        )
        for output in ("", "not-a-sha /dev/boot"):
            with self.subTest(output=output), self.assertRaisesRegex(
                self.gate.GateError, "partial Android boot"
            ):
                self.gate.parse_partition_sha256(output, "boot")

    def test_timeline_is_exact_single_events_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            for name in self.gate.TIMELINE_NAMES:
                self.gate.append_event(path, events, name)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {"events"})
            self.assertEqual(
                [event["name"] for event in payload["events"]],
                list(self.gate.TIMELINE_NAMES),
            )

    def test_inactive_policy_blocks_every_device_mode(self):
        artifacts = {"setter_sha256": self.gate.EXPECTED_SETTER_SHA256}
        for mode, token in (
            ("--dry-run", None),
            ("--live", self.gate.LIVE_ACK_TOKEN),
            ("--recover-high-from-download", self.gate.RECOVERY_ACK_TOKEN),
            ("--rollback-magisk-from-download", self.gate.MAGISK_ACK_TOKEN),
        ):
            argv = [mode]
            if token:
                argv.extend(["--ack", token])
            with self.subTest(mode=mode), mock.patch.object(
                self.gate, "verify_setter", return_value=artifacts
            ), mock.patch.object(
                self.gate, "verify_policy_draft", return_value={"active": False}
            ), mock.patch.object(
                self.gate, "policy_active", return_value=False
            ), mock.patch.object(
                self.gate, "require_mid_baseline", side_effect=AssertionError("device contact")
            ), mock.patch.object(
                self.gate, "odin_devices", side_effect=AssertionError("device contact")
            ):
                self.assertEqual(self.gate.main(argv), 2)

    def test_offline_check_has_no_device_contact(self):
        with mock.patch.object(
            self.gate,
            "verify_setter",
            return_value={"setter_sha256": self.gate.EXPECTED_SETTER_SHA256},
        ), mock.patch.object(
            self.gate, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.gate, "require_mid_baseline", side_effect=AssertionError("device contact")
        ), mock.patch("builtins.print"):
            self.assertEqual(self.gate.main(["--offline-check"]), 0)

    def test_live_source_forbids_panic_and_rdx_protocol(self):
        source = LIVE_SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("/proc/sysrq-trigger", source)
        self.assertNotIn("PrEaMbLe", source)
        self.assertNotIn("PrObE", source)
        self.assertNotIn("DaTaXfEr", source)
        self.assertIn("recover_high_via_download", source)
        self.assertIn("GateError, rescue.GateError", source)
        live = source.split("def live_run(", 1)[1].split("def build_parser(", 1)[0]
        rollback = live.split('"MID-restore dispatch; no rollback flash"', 1)[1]
        self.assertLess(rollback.index("stage_setter(high_serial"), rollback.index("dispatch_level(high_serial"))

    def test_emergency_high_recovery_writes_complete_timeline(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.gate, "policy_active", return_value=True
        ), mock.patch.object(
            self.gate, "odin_devices", return_value=["/dev/fake-high"]
        ), mock.patch.object(
            self.gate.rescue, "flash_exact"
        ), mock.patch.object(
            self.gate.rescue, "wait_odin_absent", return_value=True
        ), mock.patch.object(
            self.gate, "wait_for_odin", return_value="/dev/fake-mid"
        ), mock.patch.object(
            self.gate.rescue, "flash_boot_rollback", return_value="magisk"
        ), mock.patch.object(
            self.gate, "wait_android_mid", return_value=("serial", {"debug_level": "18765"})
        ), mock.patch.object(self.gate, "cleanup_setter"):
            root = Path(temporary)
            args = Namespace(
                ack=self.gate.RECOVERY_ACK_TOKEN,
                odin=Path("/fake/odin4"),
                manual_wait_sec=1,
                android_wait_sec=1,
            )
            result = self.gate.emergency_recovery(root, args, True)
            run_dir = next((root / self.gate.RUN_ROOT).iterdir())
            timeline = json.loads(
                (run_dir / "timeline.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [event["name"] for event in timeline["events"]],
                list(self.gate.TIMELINE_NAMES),
            )
            self.assertEqual(result["verdict"], "PASS_EMERGENCY_MID_AND_MAGISK_RECOVERY")


if __name__ == "__main__":
    unittest.main()
