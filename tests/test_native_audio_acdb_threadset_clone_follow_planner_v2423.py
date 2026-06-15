"""Host-only tests for the V2423 thread-set clone-following ACDB observer planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2423 = load_revalidation("native_audio_acdb_threadset_clone_follow_planner_v2423")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "materialize_capture_helper": False,
        "helper_out_dir": v2423.DEFAULT_HELPER_OUT_DIR,
        "cc": v2423.DEFAULT_CC,
        "stimulus_apk": v2423.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2423.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2423.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2423.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2423.DEFAULT_DURATION_SEC,
        "max_bytes": v2423.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2423.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbThreadsetCloneFollowPlanner(unittest.TestCase):
    def test_helper_source_attaches_threadset_without_audio_ioctls(self) -> None:
        state = v2423.source_state()
        text = v2423.HELPER_SOURCE.read_text()

        self.assertTrue(state["ok"], state)
        self.assertTrue(state["contains_ptrace_attach"])
        self.assertTrue(state["contains_ptrace_traceclone"])
        self.assertTrue(state["contains_geteventmsg"])
        self.assertTrue(state["contains_task_enumeration"])
        self.assertTrue(state["contains_tgid_option"])
        self.assertEqual(state["trace_mode"], "threadset-clone-following")
        self.assertIn("/proc/%ld/task", text)
        self.assertIn("--tgid", text)
        self.assertIn("attach_existing_threadset", text)
        self.assertIn("set_options_and_resume_all", text)
        self.assertIn("PTRACE_EVENT_CLONE", text)
        self.assertNotIn("open(\"/dev/msm_audio_cal", text)
        self.assertNotIn("AUDIO_SET_CALIBRATION", text)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", text)
        self.assertFalse(state["opens_msm_audio_cal"])
        self.assertFalse(state["issues_audio_calibration_ioctl"])

    def test_controller_starts_one_threadset_helper_per_process(self) -> None:
        script = v2423.capture_shell_script(duration_sec=8, max_bytes=512)

        self.assertIn("A90_V2423_HELPER_START tgid=$pid", script)
        self.assertIn('--tgid "$pid" --fd-pid "$pid"', script)
        self.assertIn("msm-audio-cal-threadset-p${pid}.jsonl", script)
        self.assertIn("mode=threadset-clone-following", script)
        self.assertIn("proc-$pid-tasks-initial.txt", script)
        self.assertNotIn('--pid "$pid" --fd-pid "$pid"', script)
        self.assertNotIn("msm-audio-cal-clone-p${pid}.jsonl", script)
        self.assertNotIn('tid="${task_dir##*/}"', script)

    def test_dry_run_declares_v2424_live_boundary_and_m1_deferred(self) -> None:
        payload = v2423.dry_run_payload(args())
        strategy = payload["magisk_strategy"]
        tiers = {item["tier"]: item for item in strategy["tiers"]}

        self.assertTrue(payload["ok"], payload.get("command_safety"))
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["future_live_run_id"], "V2424")
        self.assertEqual(payload["capture_contract"]["watcher"]["mode"], "threadset-attach-plus-PTRACE_O_TRACECLONE")
        self.assertEqual(payload["capture_contract"]["watcher"]["per_process_output"], "msm-audio-cal-threadset-p<TGID>.jsonl")
        self.assertFalse(strategy["native_runtime_dependency"])
        self.assertFalse(strategy["persistent_install"])
        self.assertEqual(strategy["default_tier"], "M0-threadset-clone-following-transient-helper")
        self.assertTrue(tiers["M0-threadset-clone-following-transient-helper"]["default"])
        self.assertFalse(tiers["M1-temporary-boot-module"]["default"])
        self.assertIn("same hybrid thread-set clone-following observer", tiers["M1-temporary-boot-module"]["mechanism"])
        self.assertIn("before the audio HAL process or worker pool starts", tiers["M1-temporary-boot-module"]["gate"])

    def test_materialize_helper_builds_private_static_binary_and_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2423.dry_run_payload(args(materialize_capture_helper=True, helper_out_dir=Path(temp_dir)))

            bundle = payload["capture_helper"]["build"]
            build = bundle["build"]
            self.assertTrue(payload["capture_helper"]["ok"], build)
            self.assertTrue(build["aarch64_static"], build.get("file"))
            self.assertEqual(build["binary"]["mode"], "0o700")
            self.assertEqual(bundle["controller_script"]["mode"], "0o700")
            self.assertTrue((Path(temp_dir) / "a90_acdb_ioctl_capture_threadset_v2423").exists())
            self.assertTrue((Path(temp_dir) / "a90_acdb_threadset_clone_follow_capture.sh").exists())
            self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])

    def test_command_safety_requires_threadset_tokens_and_rejects_native_replay(self) -> None:
        payload = v2423.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)
        contract = json.dumps(payload["capture_contract"], sort_keys=True)

        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("--tgid", contract)
        self.assertIn("threadset-clone-following", contract)
        self.assertIn("PTRACE_O_TRACECLONE", contract)
        self.assertIn("A90AudioRouteStimulusActivity", flat)
        self.assertIn("prepare_private_artifacts_for_pull", payload["commands"])
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("AUDIO_SET_CALIBRATION", flat)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn("tinymix set", flat)

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_planner_v2423.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2423.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2423-acdb-threadset-clone-follow-observer-dry-run")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
