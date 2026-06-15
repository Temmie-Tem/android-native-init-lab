"""Host-only tests for the V2444 ACDB M1 Magisk-module retry runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2444 = load_revalidation("native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_module_template": False,
        "module_out_dir": v2444.v2429.DEFAULT_MODULE_OUT_DIR,
        "cc": v2444.v2429.DEFAULT_CC,
        "stimulus_apk": v2444.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2444.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2444.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2444.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2444.DEFAULT_CAPTURE_DURATION_SEC,
        "capture_observe_sec": 6.0,
        "post_module_root_retry_attempts": v2444.DEFAULT_POST_MODULE_ROOT_RETRY_ATTEMPTS,
        "post_module_root_retry_sleep_sec": v2444.DEFAULT_POST_MODULE_ROOT_RETRY_SLEEP_SEC,
        "max_bytes": v2444.v2429.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2444.v2429.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbM1MagiskModuleRetryLiveHandoffV2444(unittest.TestCase):
    def test_dry_run_declares_v2444_retry_boundary(self) -> None:
        payload = v2444.dry_run(args())

        self.assertEqual(payload["run_id"], "V2444")
        self.assertEqual(payload["decision"], "v2444-acdb-m1-magisk-module-retry-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2444.APPROVAL_PHRASE)
        self.assertEqual(payload["module_lifecycle"]["remote_module_dir"], f"/data/adb/modules/{v2444.v2429.MODULE_ID}")
        self.assertEqual(payload["module_lifecycle"]["remote_incoming_dir"], "/data/local/tmp/a90-audio-acdb-m1-v2429/incoming")
        self.assertEqual(payload["module_lifecycle"]["incoming_owner"], "2000:2000")
        self.assertFalse(payload["module_lifecycle"]["native_runtime_dependency"])
        self.assertFalse(payload["module_lifecycle"]["uses_magisk_install_module"])
        self.assertEqual(payload["module_lifecycle"]["corrected_remote_shell"], "adb shell \"su -c '<script>'\"")
        self.assertTrue(payload["module_lifecycle"]["v2435_cleanup_discipline"])
        self.assertTrue(payload["module_lifecycle"]["v2444_post_module_reboot_retry"])
        self.assertEqual(
            payload["commands"]["android_post_module_reboot_settle"]["root_retry_attempts"],
            v2444.DEFAULT_POST_MODULE_ROOT_RETRY_ATTEMPTS,
        )
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("V2429 module plan not live-ready", " ".join(payload["future_live_blockers"]))

    def test_materialized_dry_run_uses_corrected_su_and_exact_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2444.dry_run(args(
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
        self.assertIn("A90_M1_INCOMING_READY", flat)
        self.assertIn("A90_M1_INCOMING_HASH_OK", flat)
        self.assertIn("A90_M1_INSTALL_OK", flat)
        self.assertIn("A90_M1_CLEANUP_OK", flat)
        self.assertIn("/data/local/tmp/a90-audio-acdb-m1-v2429/incoming/module.prop", flat)
        self.assertIn("/data/local/tmp/a90-audio-acdb-m1-v2429/incoming/bin/a90_acdb_ioctl_capture_threadset_v2423", flat)
        self.assertIn("chown 2000:2000", flat)
        self.assertIn("chmod 711", flat)
        self.assertIn("check_file", flat)
        self.assertIn("sha256sum", flat)
        self.assertIn("find \\\"$INCOMING_DIR\\\" -type f | wc -l", flat)
        self.assertIn("bounded adb reacquire plus Magisk-root retry", flat)
        self.assertIn('"adb", "reboot"', flat)
        self.assertIn("uninstall", flat)
        self.assertIn("rollback_v2321", flat)
        self.assertNotIn("module-stage", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("post-fs-data.sh", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn("tinymix set", flat)
        self.assertNotIn("rm -rf /data/adb/modules", flat)

        manifest = payload["module_lifecycle"]["local_module_manifest"]
        self.assertEqual(set(manifest), {"module.prop", "service.sh", "README.md", "a90_acdb_ioctl_capture_threadset_v2423"})
        for entry in manifest.values():
            self.assertTrue(entry["exists"], entry)
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("/incoming/", entry["remote_path"])

    def test_pushes_target_shell_writable_incoming_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2444.dry_run(args(
                materialize_module_template=True,
                module_out_dir=Path(temp_dir),
            ))

        stage_commands = payload["commands"]["stage_module_and_apk"]
        push_targets = [
            command[-1]
            for command in stage_commands
            if v2444.adb_subcommand(command) == "push"
        ]
        self.assertEqual(len(push_targets), 4)
        self.assertTrue(all("/incoming/" in target for target in push_targets), push_targets)
        self.assertFalse(any("module-stage" in target for target in push_targets), push_targets)

    def test_post_module_reboot_settle_retries_root_until_uid0(self) -> None:
        call_names: list[str] = []
        root_attempts = {"count": 0}
        original_run_step = v2444.route.run_step
        original_sleep = v2444.time.sleep

        def fake_run_step(name: str, command: list[str], out_dir: Path, *, timeout_sec: float, check: bool = True) -> dict[str, object]:
            call_names.append(name)
            stdout_path = out_dir / f"{name}.stdout.txt"
            stderr_path = out_dir / f"{name}.stderr.txt"
            stdout = ""
            stderr = ""
            rc = 0
            ok = True
            if "root-check" in name:
                root_attempts["count"] += 1
                if root_attempts["count"] == 1:
                    rc = 1
                    ok = False
                    stderr = "adb: no devices/emulators found\n"
                else:
                    stdout = "uid=0(root) gid=0(root) groups=0(root)\n"
            stdout_path.write_text(stdout)
            stderr_path.write_text(stderr)
            return {
                "name": name,
                "command": command,
                "ok": ok,
                "rc": rc,
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "timeout_sec": timeout_sec,
            }

        try:
            v2444.route.run_step = fake_run_step
            v2444.time.sleep = lambda _seconds: None
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir)
                steps: list[dict[str, object]] = []
                v2444.run_post_module_reboot_settle(
                    args(post_module_root_retry_attempts=3, post_module_root_retry_sleep_sec=0.01),
                    out_dir,
                    steps,
                )
        finally:
            v2444.route.run_step = original_run_step
            v2444.time.sleep = original_sleep

        self.assertEqual(root_attempts["count"], 2)
        self.assertIn("android-post-module-reboot-root-check-1", call_names)
        self.assertIn("android-post-module-reboot-root-check-2", call_names)
        self.assertFalse(steps[-3]["root_ready"])
        self.assertEqual(steps[-3]["settle_decision"], "post-module-root-not-ready")
        self.assertTrue(steps[-1]["root_ready"])
        self.assertEqual(steps[-1]["settle_decision"], "post-module-root-ready")


    def test_run_live_wires_retry_after_module_activation_reboot(self) -> None:
        source = Path(v2444.__file__).read_text()
        flash_index = source.index('steps.append(route.run_step(\n            "flash-android"')
        initial_settle_index = source.index('v2396.run_android_post_handoff_settle(args, out_dir, steps)', flash_index)
        stage_index = source.index('for index, command in enumerate(stage_commands(args)):', initial_settle_index)
        reboot_index = source.index('"android-reboot-for-magisk-service"', stage_index)
        post_module_retry_index = source.index('run_post_module_reboot_settle(args, out_dir, steps)', reboot_index)
        logcat_index = source.index('"logcat-clear-before-stimulus"', post_module_retry_index)

        self.assertLess(flash_index, initial_settle_index)
        self.assertLess(initial_settle_index, stage_index)
        self.assertLess(stage_index, reboot_index)
        self.assertLess(reboot_index, post_module_retry_index)
        self.assertLess(post_module_retry_index, logcat_index)

    def test_stage_waits_cover_pushes_and_install_only(self) -> None:
        payload = v2444.dry_run(args())
        waits = payload["stage_adb_waits"]
        self.assertEqual([item["before_stage_index"] for item in waits], [4, 5, 6, 7, 8])
        for item in waits:
            self.assertEqual(item["command"], ["adb", "wait-for-device"])

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2444.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2444-acdb-m1-magisk-module-retry-live-refused")
        self.assertIn("exact AUD-5J", payload["reason"])
        self.assertFalse(payload["rolled_back"])

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2444.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2444")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
