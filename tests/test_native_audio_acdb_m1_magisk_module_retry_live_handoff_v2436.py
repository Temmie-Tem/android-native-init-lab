"""Host-only tests for the V2436 ACDB M1 Magisk-module retry runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2436 = load_revalidation("native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_module_template": False,
        "module_out_dir": v2436.v2429.DEFAULT_MODULE_OUT_DIR,
        "cc": v2436.v2429.DEFAULT_CC,
        "stimulus_apk": v2436.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2436.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2436.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2436.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2436.DEFAULT_CAPTURE_DURATION_SEC,
        "capture_observe_sec": 6.0,
        "max_bytes": v2436.v2429.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2436.v2429.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbM1MagiskModuleRetryLiveHandoffV2436(unittest.TestCase):
    def test_dry_run_declares_v2436_retry_boundary(self) -> None:
        payload = v2436.dry_run(args())

        self.assertEqual(payload["run_id"], "V2436")
        self.assertEqual(payload["decision"], "v2436-acdb-m1-magisk-module-retry-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2436.APPROVAL_PHRASE)
        self.assertEqual(payload["module_lifecycle"]["remote_module_dir"], f"/data/adb/modules/{v2436.v2429.MODULE_ID}")
        self.assertFalse(payload["module_lifecycle"]["native_runtime_dependency"])
        self.assertFalse(payload["module_lifecycle"]["uses_magisk_install_module"])
        self.assertEqual(payload["module_lifecycle"]["corrected_remote_shell"], "adb shell \"su -c '<script>'\"")
        self.assertTrue(payload["module_lifecycle"]["v2435_cleanup_discipline"])
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("V2429 module plan not live-ready", " ".join(payload["future_live_blockers"]))

    def test_materialized_dry_run_uses_corrected_su_and_exact_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2436.dry_run(args(
                materialize_module_template=True,
                module_out_dir=Path(temp_dir),
            ))

        flat = json.dumps(payload["commands"], sort_keys=True)
        self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("/data/adb/modules/a90_audio_acdb_m1_v2429", flat)
        self.assertIn("service.sh", flat)
        self.assertIn("a90_acdb_ioctl_capture_threadset_v2423", flat)
        self.assertIn("su -c", flat)
        self.assertIn("su -mm -c", flat)
        self.assertIn("A90_M1_RESIDUE_CHECK_OK", flat)
        self.assertIn("A90_M1_INSTALL_OK", flat)
        self.assertIn("A90_M1_CLEANUP_OK", flat)
        self.assertIn('"adb", "reboot"', flat)
        self.assertIn("uninstall", flat)
        self.assertIn("rollback_v2321", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("post-fs-data.sh", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn("tinymix set", flat)
        self.assertNotIn("rm -rf /data/adb/modules", flat)

    def test_stage_waits_cover_pushes_and_install_only(self) -> None:
        payload = v2436.dry_run(args())
        waits = payload["stage_adb_waits"]
        self.assertEqual([item["before_stage_index"] for item in waits], [4, 5, 6, 7, 8])
        for item in waits:
            self.assertEqual(item["command"], ["adb", "wait-for-device"])

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2436.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2436-acdb-m1-magisk-module-retry-live-refused")
        self.assertIn("exact AUD-5J", payload["reason"])
        self.assertFalse(payload["rolled_back"])

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2436.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2436")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
