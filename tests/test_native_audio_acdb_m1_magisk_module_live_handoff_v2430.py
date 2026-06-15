"""Host-only tests for the V2430 ACDB M1 Magisk-module live handoff runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2430 = load_revalidation("native_audio_acdb_m1_magisk_module_live_handoff_v2430")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_module_template": False,
        "module_out_dir": v2430.v2429.DEFAULT_MODULE_OUT_DIR,
        "cc": v2430.v2429.DEFAULT_CC,
        "stimulus_apk": v2430.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2430.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2430.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2430.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2430.DEFAULT_CAPTURE_DURATION_SEC,
        "capture_observe_sec": 6.0,
        "max_bytes": v2430.v2429.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2430.v2429.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbM1MagiskModuleLiveHandoffV2430(unittest.TestCase):
    def test_dry_run_declares_temporary_module_lifecycle(self) -> None:
        payload = v2430.dry_run(args())

        self.assertEqual(payload["run_id"], "V2430")
        self.assertEqual(payload["decision"], "v2430-acdb-m1-magisk-module-capture-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2430.APPROVAL_PHRASE)
        self.assertEqual(payload["module_lifecycle"]["remote_module_dir"], f"/data/adb/modules/{v2430.v2429.MODULE_ID}")
        self.assertFalse(payload["module_lifecycle"]["native_runtime_dependency"])
        self.assertFalse(payload["module_lifecycle"]["uses_magisk_install_module"])
        self.assertTrue(payload["command_safety"]["ok"])
        self.assertIn("V2429 module plan not live-ready", " ".join(payload["future_live_blockers"]))

    def test_materialized_dry_run_has_reboot_cleanup_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2430.dry_run(args(
                materialize_module_template=True,
                module_out_dir=Path(temp_dir),
            ))

        flat = json.dumps(payload["commands"], sort_keys=True)
        self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
        self.assertIn("/data/adb/modules/a90_audio_acdb_m1_v2429", flat)
        self.assertIn("service.sh", flat)
        self.assertIn("a90_acdb_ioctl_capture_threadset_v2423", flat)
        self.assertIn('"adb", "reboot"', flat)
        self.assertIn("uninstall", flat)
        self.assertIn("rollback_v2321", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("post-fs-data.sh", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn("tinymix set", flat)

    def test_stage_waits_cover_pushes_and_install_only(self) -> None:
        payload = v2430.dry_run(args())
        waits = payload["stage_adb_waits"]
        self.assertEqual([item["before_stage_index"] for item in waits], [1, 2, 3, 4, 5])
        for item in waits:
            self.assertEqual(item["command"], ["adb", "wait-for-device"])

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_live_handoff_v2430.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2430.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2430-acdb-m1-magisk-module-capture-live-refused")
        self.assertIn("exact AUD-5G", payload["reason"])
        self.assertFalse(payload["rolled_back"])

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_live_handoff_v2430.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2430.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2430")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
