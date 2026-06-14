"""Host-only tests for the V2396 Android/Magisk ACDB measurement planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2396 = load_revalidation("native_audio_acdb_android_measurement_planner_v2396")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "dry_run": True,
        "materialize_module_template": False,
        "module_out_dir": v2396.DEFAULT_MODULE_OUT_DIR,
        "stimulus_apk": v2396.DEFAULT_STIMULUS_APK,
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
        "from_native": True,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AcdbAndroidMeasurementPlanner(unittest.TestCase):
    def test_dry_run_is_host_only_and_defers_live_until_module_materialized(self) -> None:
        payload = v2396.dry_run_payload(args())

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertFalse(payload["future_live_ready"])
        self.assertIn("AUD-5A-android-acdb-magisk-measurement go:", payload["approval_phrase_required_for_future_live"])
        self.assertIn("module template not materialized", " ".join(payload["future_live_blockers"]))
        self.assertFalse(payload["magisk_module"]["native_runtime_dependency"])

    def test_command_plan_reuses_checked_android_handoff_and_rollback(self) -> None:
        payload = v2396.dry_run_payload(args(adb="/opt/android/adb", serial="A90ADB01"))
        commands = payload["commands"]

        self.assertIn("native_init_flash.py", " ".join(commands["flash_android"]))
        self.assertIn("--post-flash-target", commands["flash_android"])
        self.assertIn("android-adb", commands["flash_android"])
        self.assertEqual(commands["baseline_probe"][:3], ["/opt/android/adb", "-s", "A90ADB01"])
        self.assertEqual(commands["android_reboot_recovery_for_rollback"], ["/opt/android/adb", "-s", "A90ADB01", "reboot", "recovery"])
        self.assertIn("rollback_v2321", commands)
        self.assertIn("--expect-version", commands["rollback_v2321"])
        self.assertIn("0.9.285", commands["rollback_v2321"])

    def test_plan_contains_acdb_specific_observability(self) -> None:
        payload = v2396.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)

        self.assertIn("/dev/msm_audio_cal", "".join(v2396.module_files().values()))
        self.assertIn("audio-hal-pids", "".join(v2396.module_files().values()))
        self.assertIn("ACDB", payload["measurement_focus"]["log_filter_regex"])
        self.assertIn("q6asm_send_cal", payload["measurement_focus"]["log_filter_regex"])
        self.assertIn("logcat", flat)
        self.assertIn("A90AudioRouteStimulusActivity", flat)
        self.assertIn("a90_acdb_probe.sh", flat)

    def test_command_safety_blocks_persistent_magisk_install_and_native_playback(self) -> None:
        payload = v2396.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)

        self.assertTrue(payload["command_safety"]["ok"])
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn(" tinymix set ", flat)
        self.assertNotIn("fastboot", flat)
        self.assertEqual(payload["command_safety"]["default_delivery"], "transient Magisk-root helper; no persistent module install")

    def test_module_template_materialization_is_private_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2396.dry_run_payload(args(materialize_module_template=True, module_out_dir=Path(temp_dir)))

            self.assertTrue(payload["magisk_module"]["zip"]["ok"])
            self.assertEqual(payload["magisk_module"]["zip"]["mode"], "0o600")
            self.assertTrue(payload["magisk_module"]["manifest"]["ok"])
            self.assertTrue(payload["future_live_ready"])
            self.assertEqual(payload["future_live_blockers"], [])
            self.assertTrue((Path(temp_dir) / "service.sh").exists())
            self.assertTrue((Path(temp_dir) / "system/bin/a90_acdb_probe.sh").exists())
            self.assertTrue((Path(temp_dir) / "a90_audio_acdb_probe_v2396.zip").exists())

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2396.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2396-audio-acdb-android-magisk-planner-dry-run")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
