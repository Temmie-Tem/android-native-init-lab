import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3441_debug_mid_rescue_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_v3441_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class V3441DebugMidRescueLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_exact_candidate_and_rollback_pins(self):
        self.assertEqual(
            self.module.EXPECTED_AP_SHA256,
            "25a8a5b5cfdeeebd47525c236d975561da8492bb08df5716cfa9da15e00ecfd6",
        )
        self.assertEqual(self.module.EXPECTED_REBOOT_ARG, "debug0x494d")
        self.assertEqual(self.module.EXPECTED_DEBUG_MID, "18765")
        self.assertEqual(
            self.module.EXPECTED_BOOT_SHA256,
            "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e",
        )
        self.assertEqual(
            self.module.EXPECTED_STOCK_BOOT_AP_SHA256,
            "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94",
        )
        self.assertEqual(
            self.module.EXPECTED_STOCK_BOOT_SHA256,
            "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae",
        )

    def test_timeline_uses_only_standard_events_shape(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            for name in self.module.TIMELINE_NAMES:
                self.module.append_event(path, events, name)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {"events"})
            self.assertEqual(
                [event["name"] for event in payload["events"]],
                list(self.module.TIMELINE_NAMES),
            )
            self.assertTrue(
                all(set(event) == {"name", "timestamp_utc"} for event in payload["events"])
            )

    def test_duplicate_or_unknown_timeline_event_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            self.module.append_event(path, events, "live_session_start")
            with self.assertRaises(self.module.GateError):
                self.module.append_event(path, events, "live_session_start")
            with self.assertRaises(self.module.GateError):
                self.module.append_event(path, events, "not-a-phase")

    def test_inactive_policy_blocks_all_device_modes_before_contact(self):
        harmless_artifacts = {"candidate_ap_sha256": self.module.EXPECTED_AP_SHA256}
        harmless_draft = {"active": False}
        for mode, token in (
            ("--dry-run", None),
            ("--live", self.module.LIVE_ACK_TOKEN),
            ("--rollback-from-download", self.module.ROLLBACK_ACK_TOKEN),
        ):
            argv = [mode]
            if token:
                argv.extend(["--ack", token])
            with self.subTest(mode=mode), mock.patch.object(
                self.module, "verify_artifacts", return_value=harmless_artifacts
            ), mock.patch.object(
                self.module, "verify_policy_draft", return_value=harmless_draft
            ), mock.patch.object(
                self.module, "policy_active", return_value=False
            ), mock.patch.object(
                self.module, "current_android", side_effect=AssertionError("device contact")
            ), mock.patch.object(
                self.module, "odin_devices", side_effect=AssertionError("device contact")
            ):
                self.assertEqual(self.module.main(argv), 2)

    def test_offline_check_never_requires_active_policy_or_device(self):
        with mock.patch.object(
            self.module,
            "verify_artifacts",
            return_value={"candidate_ap_sha256": self.module.EXPECTED_AP_SHA256},
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.module, "policy_active", side_effect=AssertionError("active policy check")
        ), mock.patch.object(
            self.module, "current_android", side_effect=AssertionError("device contact")
        ), mock.patch("builtins.print"):
            self.assertEqual(self.module.main(["--offline-check"]), 0)

    def test_live_source_orders_policy_before_android_and_odin(self):
        source = SCRIPT.read_text(encoding="utf-8")
        main = source.split("def main(", 1)[1]
        self.assertLess(
            main.index('if not policy_active(root):'),
            main.index('if args.rollback_from_download:'),
        )
        live = source.split("def live_run(", 1)[1].split("def build_parser(", 1)[0]
        self.assertLess(live.index("policy_active(root)"), live.index("current_android()"))
        self.assertIn("full FYG8 stock evidence failed", source)

    def test_recovery_only_rollback_writes_complete_standard_timeline(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "odin_devices", return_value=["/dev/fake-odin"]
        ), mock.patch.object(self.module, "flash_exact"), mock.patch.object(
            self.module, "wait_android", return_value=("serial", {"boot": "magisk"})
        ):
            run_dir = Path(temporary)
            result = self.module.rollback_from_download(
                Path.cwd(), Path("/fake/odin4"), run_dir
            )
            timeline = json.loads(
                (run_dir / "timeline.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [event["name"] for event in timeline["events"]],
                list(self.module.TIMELINE_NAMES),
            )
            self.assertEqual(result["verdict"], "PASS_MAGISK_ROLLBACK_FROM_DOWNLOAD")
            self.assertEqual(
                result["timeline_phase_semantics"]["candidate_flash_start"],
                "recovery-only-session-no-candidate-flash",
            )


if __name__ == "__main__":
    unittest.main()
