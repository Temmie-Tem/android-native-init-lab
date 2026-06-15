"""Host-only tests for the V2421 clone-following ACDB observer planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2421 = load_revalidation("native_audio_acdb_clone_follow_planner_v2421")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "materialize_capture_helper": False,
        "helper_out_dir": v2421.DEFAULT_HELPER_OUT_DIR,
        "cc": v2421.DEFAULT_CC,
        "stimulus_apk": v2421.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2421.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2421.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2421.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2421.DEFAULT_DURATION_SEC,
        "max_bytes": v2421.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2421.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbCloneFollowPlanner(unittest.TestCase):
    def test_helper_source_follows_clones_without_sending_audio_ioctls(self) -> None:
        state = v2421.source_state()
        text = v2421.HELPER_SOURCE.read_text()

        self.assertTrue(state["ok"], state)
        self.assertTrue(state["contains_ptrace_attach"])
        self.assertTrue(state["contains_ptrace_traceclone"])
        self.assertTrue(state["contains_geteventmsg"])
        self.assertTrue(state["contains_wait_wall"])
        self.assertTrue(state["contains_process_vm_readv"])
        self.assertTrue(state["contains_ioctl_syscall_filter"])
        self.assertEqual(state["trace_mode"], "clone-following")
        self.assertIn("PTRACE_EVENT_CLONE", text)
        self.assertIn("waitpid(-1", text)
        self.assertNotIn("open(\"/dev/msm_audio_cal", text)
        self.assertNotIn("AUDIO_SET_CALIBRATION", text)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", text)
        self.assertFalse(state["opens_msm_audio_cal"])
        self.assertFalse(state["issues_audio_calibration_ioctl"])

    def test_controller_starts_one_clone_following_helper_per_process_not_per_tid(self) -> None:
        script = v2421.capture_shell_script(duration_sec=8, max_bytes=512)

        self.assertIn("A90_V2421_HELPER_START pid=$pid", script)
        self.assertIn('--pid "$pid" --fd-pid "$pid"', script)
        self.assertIn("msm-audio-cal-clone-p${pid}.jsonl", script)
        self.assertIn("mode=clone-following", script)
        self.assertIn("PROCESS_POLL_SEC", script)
        self.assertIn("proc-$pid-tasks-initial.txt", script)
        self.assertNotIn("A90_V2415_TASK_POLL_SEC", script)
        self.assertNotIn('tid="${task_dir##*/}"', script)
        self.assertNotIn('--pid "$tid" --fd-pid "$pid"', script)
        self.assertNotIn("msm-audio-cal-ioctl-p${pid}-t${tid}.jsonl", script)

    def test_dry_run_declares_clone_following_m0_before_magisk_module_fallback(self) -> None:
        payload = v2421.dry_run_payload(args())
        strategy = payload["magisk_strategy"]
        tiers = {item["tier"]: item for item in strategy["tiers"]}

        self.assertTrue(payload["ok"], payload.get("command_safety"))
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["future_live_run_id"], "V2422")
        self.assertEqual(payload["capture_contract"]["watcher"]["mode"], "process-attach-plus-PTRACE_O_TRACECLONE")
        self.assertFalse(strategy["native_runtime_dependency"])
        self.assertFalse(strategy["persistent_install"])
        self.assertEqual(strategy["default_tier"], "M0-clone-following-transient-helper")
        self.assertIn("same clone-following ptrace observer", strategy["single_observer_semantics"])
        self.assertTrue(tiers["M0-clone-following-transient-helper"]["default"])
        self.assertFalse(tiers["M1-temporary-boot-module"]["default"])
        self.assertIn("same clone-following observer", tiers["M1-temporary-boot-module"]["mechanism"])
        self.assertIn("service_sh", tiers["M1-temporary-boot-module"]["package_shape"])
        self.assertIn("no vendor partition writes", tiers["M1-temporary-boot-module"]["package_shape"]["post_fs_data_sh"])
        self.assertIn("removed by Android-to-V2321 rollback", tiers["M1-temporary-boot-module"]["allowed_scope"])

    def test_materialize_helper_builds_private_static_binary_and_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2421.dry_run_payload(args(materialize_capture_helper=True, helper_out_dir=Path(temp_dir)))

            bundle = payload["capture_helper"]["build"]
            build = bundle["build"]
            self.assertTrue(payload["capture_helper"]["ok"], build)
            self.assertTrue(build["aarch64_static"], build.get("file"))
            self.assertEqual(build["binary"]["mode"], "0o700")
            self.assertEqual(bundle["controller_script"]["mode"], "0o700")
            self.assertTrue((Path(temp_dir) / "a90_acdb_ioctl_capture_clone_v2421").exists())
            self.assertTrue((Path(temp_dir) / "a90_acdb_clone_follow_capture.sh").exists())
            self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])

    def test_command_safety_rejects_persistent_magisk_and_native_replay(self) -> None:
        payload = v2421.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)

        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("PTRACE_O_TRACECLONE", json.dumps(payload["capture_contract"], sort_keys=True))
        self.assertIn("A90AudioRouteStimulusActivity", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("AUDIO_SET_CALIBRATION", flat)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn("tinymix set", flat)

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_clone_follow_planner_v2421.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2421.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2421-acdb-clone-follow-observer-dry-run")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
