"""Host-only tests for the V2415 ACDB payload capture planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2415 = load_revalidation("native_audio_acdb_payload_capture_planner_v2415")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_capture_helper": False,
        "helper_out_dir": v2415.DEFAULT_HELPER_OUT_DIR,
        "cc": v2415.DEFAULT_CC,
        "stimulus_apk": v2415.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": 2000,
        "sample_rate": 48000,
        "amplitude": 0.05,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": 8,
        "max_bytes": 512,
        "from_native": True,
        "approval": "",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AcdbPayloadCapturePlanner(unittest.TestCase):
    def test_dry_run_is_host_only_and_blocks_live_until_helper_materialized(self) -> None:
        payload = v2415.dry_run_payload(args())

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertFalse(payload["future_live_ready"])
        self.assertIn("capture_helper not ready", " ".join(payload["future_live_blockers"]))
        self.assertIn("AUD-5D-acdb-payload-capture go:", payload["approval_phrase_required_for_future_live"])
        self.assertFalse(payload["magisk_strategy"]["native_runtime_dependency"])

    def test_helper_source_is_read_only_observer_not_ioctl_sender(self) -> None:
        state = v2415.source_state()
        text = v2415.HELPER_SOURCE.read_text()

        self.assertTrue(state["ok"], state)
        self.assertIn("PTRACE_ATTACH", text)
        self.assertIn("process_vm_readv", text)
        self.assertIn("__NR_ioctl", text)
        self.assertNotIn("AUDIO_SET_CALIBRATION", text)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", text)
        self.assertFalse(state["opens_msm_audio_cal"])

    def test_materialize_capture_helper_builds_private_aarch64_static_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2415.dry_run_payload(args(materialize_capture_helper=True, helper_out_dir=Path(temp_dir)))

            self.assertTrue(payload["capture_helper"]["ok"], payload["capture_helper"].get("build"))
            self.assertTrue(payload["capture_helper"]["build"]["aarch64_static"])
            self.assertEqual(payload["capture_helper"]["build"]["binary"]["mode"], "0o700")
            self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
            self.assertEqual(payload["future_live_blockers"], [])
            self.assertTrue((Path(temp_dir) / "a90_acdb_ioctl_capture_v2415").exists())
            self.assertTrue((Path(temp_dir) / "a90_acdb_payload_capture.sh").exists())

    def test_command_plan_uses_checked_android_handoff_and_v2321_rollback(self) -> None:
        payload = v2415.dry_run_payload(args(adb="/opt/android/adb", serial="A90ADB01"))
        commands = payload["commands"]

        self.assertIn("native_init_flash.py", " ".join(commands["flash_android"]))
        self.assertIn("--post-flash-target", commands["flash_android"])
        self.assertIn("android-adb", commands["flash_android"])
        self.assertEqual(commands["android_post_handoff_settle"][0], ["/opt/android/adb", "-s", "A90ADB01", "wait-for-device"])
        self.assertEqual(commands["android_post_handoff_settle"][2], ["/opt/android/adb", "-s", "A90ADB01", "shell", "su", "-c", "id"])
        self.assertIn("a90_acdb_ioctl_capture_v2415", " ".join(" ".join(step) for step in commands["stage_capture_helper_and_stimulus"]))
        self.assertIn("A90AudioRouteStimulusActivity", " ".join(commands["playback_start_background"]))
        self.assertIn("rollback_v2321", commands)
        self.assertIn("--expect-version", commands["rollback_v2321"])
        self.assertIn("0.9.285", commands["rollback_v2321"])

    def test_capture_contract_requires_private_payloads_and_no_native_replay(self) -> None:
        payload = v2415.dry_run_payload(args())
        contract = payload["capture_contract"]

        self.assertEqual(contract["target_device"], "/dev/msm_audio_cal")
        self.assertIn("android.hardware.audio.service", contract["target_processes"])
        self.assertEqual(contract["max_bytes_per_ioctl"], 512)
        self.assertEqual(contract["raw_payload_storage"], "workspace/private only")
        self.assertIn("raw bytes", contract["public_report_forbidden"])
        self.assertFalse(contract["native_replay_allowed"])

    def test_magisk_strategy_keeps_wifi_style_module_as_deferred_measurement_fallback(self) -> None:
        payload = v2415.dry_run_payload(args())
        strategy = payload["magisk_strategy"]

        self.assertEqual(strategy["default_tier"], "M0-transient-helper")
        self.assertFalse(strategy["native_runtime_dependency"])
        self.assertFalse(strategy["persistent_install"])
        self.assertIn("Wi-Fi-style", strategy["precedent"])
        self.assertIn("stock-good producer path", strategy["wifi_pattern_applied"])
        tiers = {item["tier"]: item for item in strategy["tiers"]}
        self.assertTrue(tiers["M0-transient-helper"]["default"])
        self.assertFalse(tiers["M1-temporary-boot-module"]["default"])
        self.assertIn("missed-early-payload", tiers["M1-temporary-boot-module"]["gate"])
        self.assertIn("removed by Android-to-V2321 rollback", tiers["M1-temporary-boot-module"]["allowed_scope"])

    def test_command_safety_allows_observer_but_rejects_replay_and_persistent_magisk(self) -> None:
        payload = v2415.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)

        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("ioctl", flat)
        self.assertIn("/dev/msm_audio_cal", flat)
        self.assertIn("ptrace", " ".join(payload["command_safety"]["allowed_observer_tokens"]))
        self.assertNotIn("AUDIO_SET_CALIBRATION", flat)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn(" tinymix set ", flat)

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_planner_v2415.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2415.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertIn("exact AUD-5D", completed.stderr)

    def test_exact_live_approval_is_source_only_placeholder(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_planner_v2415.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--run-live",
                "--approval",
                v2415.APPROVAL_PHRASE,
            ],
            cwd=v2415.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2415-live-not-executed-source-only-capture-plan-ready")
        self.assertEqual(payload["device_action"], "none")
        self.assertTrue(payload["approval_phrase_matched"])

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_planner_v2415.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2415.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "v2415-acdb-payload-capture-planner-dry-run")


if __name__ == "__main__":
    unittest.main()
