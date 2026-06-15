"""Host-only tests for the V2434 Magisk cleanup-probe runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2434 = load_revalidation("native_audio_magisk_cleanup_probe_live_handoff_v2434")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "adb": "adb",
        "serial": None,
        "stimulus_apk": v2434.v2396.DEFAULT_STIMULUS_APK,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2434.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2434.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2434.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "from_native": True,
        "approval": None,
        "probe_tag": "unit_test",
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class MagiskCleanupProbeV2434(unittest.TestCase):
    def test_dry_run_uses_exact_inert_path_and_checked_rollback(self) -> None:
        payload = v2434.dry_run(args())

        self.assertEqual(payload["run_id"], "V2434")
        self.assertEqual(payload["decision"], "v2434-magisk-cleanup-probe-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2434.APPROVAL_PHRASE)
        self.assertEqual(
            payload["probe_path"],
            "/data/adb/modules/.a90_v2433_cleanup_probe_unit_test",
        )
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        flat = json.dumps(payload["commands"], sort_keys=True)
        self.assertIn("mkdir", flat)
        self.assertIn("$PROBE_DIR", flat)
        self.assertIn("rm -f", flat)
        self.assertIn("$MARKER", flat)
        self.assertIn("rmdir", flat)
        self.assertIn("A90_MAGISK_CLEANUP_OK", flat)
        self.assertIn("rollback_v2321", flat)
        self.assertNotIn("--install-module", flat)
        self.assertNotIn("--remove-modules", flat)
        self.assertNotIn("module.prop", flat)
        self.assertNotIn("service.sh", flat)
        self.assertNotIn("post-fs-data.sh", flat)
        self.assertNotIn("rm -rf /data/adb/modules", flat)
        self.assertNotIn("am start", flat)
        self.assertNotIn("/dev/msm_audio_cal", flat)

    def test_unsafe_probe_tag_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            v2434.dry_run(args(probe_tag="../bad"))

    def test_cleanup_commands_include_mount_master_readonly_and_one_write_probe(self) -> None:
        commands = v2434.cleanup_commands(args(), "unit_test")

        self.assertEqual([item["name"] for item in commands], [
            "root-readonly-probe",
            "root-mount-master-readonly-probe",
            "magisk-cleanup-create-remove",
        ])
        self.assertIn("su -mm -c", commands[1]["command"][2])
        self.assertIn("su -c", commands[2]["command"][2])
        self.assertEqual(
            commands[2]["probe_path"],
            "/data/adb/modules/.a90_v2433_cleanup_probe_unit_test",
        )

    def test_summary_classifies_successful_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            readonly = out_dir / "root-readonly-probe.stdout.txt"
            mount_master = out_dir / "root-mount-master-readonly-probe.stdout.txt"
            cleanup = out_dir / "magisk-cleanup-create-remove.stdout.txt"
            readonly.write_text("uid=0(root)\nA90_MAGISK_CLEANUP_READONLY_END\n")
            mount_master.write_text("uid=0(root)\nA90_MAGISK_CLEANUP_READONLY_END\n")
            cleanup.write_text(
                "A90_MAGISK_CLEANUP_BEGIN\n"
                "A90_CLEANUP_CREATED /data/adb/modules/.a90_v2433_cleanup_probe_unit_test\n"
                "A90_CLEANUP_REMOVED /data/adb/modules/.a90_v2433_cleanup_probe_unit_test\n"
                "A90_CLEANUP_NO_RESIDUE\n"
                "A90_MAGISK_CLEANUP_OK\n"
            )
            steps = [
                {"name": "root-readonly-probe", "ok": True, "stdout": str(readonly)},
                {"name": "root-mount-master-readonly-probe", "ok": True, "stdout": str(mount_master)},
                {"name": "magisk-cleanup-create-remove", "ok": True, "stdout": str(cleanup)},
            ]
            summary = v2434.summarize_live_outputs(out_dir, steps)

        self.assertEqual(summary["classification"], "cleanup-probe-ok")
        self.assertTrue(summary["created_marker_seen"])
        self.assertTrue(summary["removed_marker_seen"])
        self.assertTrue(summary["no_residue_seen"])

    def test_summary_classifies_residue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            cleanup = out_dir / "magisk-cleanup-create-remove.stdout.txt"
            cleanup.write_text("A90_CLEANUP_RESIDUE_POST_BEGIN\nleftover\nA90_CLEANUP_RESIDUE_POST_END\n")
            steps = [{"name": "magisk-cleanup-create-remove", "ok": False, "stdout": str(cleanup)}]
            summary = v2434.summarize_live_outputs(out_dir, steps)

        self.assertEqual(summary["classification"], "cleanup-residue-detected")
        self.assertTrue(summary["residue_lines"])

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_magisk_cleanup_probe_live_handoff_v2434.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2434.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2434-magisk-cleanup-probe-live-refused")
        self.assertIn("exact AUD-5I", payload["reason"])
        self.assertFalse(payload["rolled_back"])

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_magisk_cleanup_probe_live_handoff_v2434.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run", "--probe-tag", "unit_test"],
            cwd=v2434.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2434")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
