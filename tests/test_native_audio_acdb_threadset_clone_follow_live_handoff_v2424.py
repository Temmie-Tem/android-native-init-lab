"""Host-only tests for the V2424 thread-set clone-following ACDB live handoff runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2424 = load_revalidation("native_audio_acdb_threadset_clone_follow_live_handoff_v2424")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_capture_helper": False,
        "helper_out_dir": v2424.v2423.DEFAULT_HELPER_OUT_DIR,
        "cc": v2424.v2423.DEFAULT_CC,
        "stimulus_apk": v2424.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2424.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2424.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2424.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2424.v2423.DEFAULT_DURATION_SEC,
        "capture_warmup_sec": v2424.DEFAULT_CAPTURE_WARMUP_SEC,
        "max_bytes": v2424.v2423.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2424.v2423.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbThreadsetCloneFollowLiveHandoff(unittest.TestCase):
    def test_dry_run_declares_v2424_threadset_live_boundary(self) -> None:
        payload = v2424.dry_run(args())

        self.assertEqual(payload["run_id"], "V2424")
        self.assertEqual(payload["decision"], "v2424-acdb-threadset-clone-follow-capture-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2424.APPROVAL_PHRASE)
        self.assertEqual(payload["capture_contract"]["watcher"]["mode"], "threadset-attach-plus-PTRACE_O_TRACECLONE")
        self.assertIn("native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py", payload["live_runner"])

    def test_materialized_dry_run_uses_threadset_stage_and_pull_permission_fix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2424.dry_run(args(materialize_capture_helper=True, helper_out_dir=Path(temp_dir)))

        commands = payload["commands"]
        flat = json.dumps({"commands": commands, "capture_contract": payload["capture_contract"]}, sort_keys=True)
        self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
        self.assertIn("stage_threadset_clone_follow_helper_and_stimulus", commands)
        self.assertIn("--tgid", flat)
        self.assertIn("threadset-clone-following", flat)
        self.assertIn("A90AudioRouteStimulus.apk", flat)
        self.assertIn("prepare_private_artifacts_for_pull", commands)
        self.assertIn("chmod 644", " ".join(commands["prepare_private_artifacts_for_pull"]))
        self.assertIn("rollback_v2321", commands)

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2424.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2424-acdb-threadset-clone-follow-capture-live-refused")
        self.assertIn("exact AUD-5F", payload["reason"])
        self.assertFalse(payload["rolled_back"])

    def test_summarize_threadset_jsonl_hashes_payload_without_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts"
            artifact_dir.mkdir()
            (artifact_dir / "audio-hal-pids.txt").write_text("1234\n")
            (artifact_dir / "proc-1234-tasks-initial.txt").write_text("1234\n1235\n")
            (artifact_dir / "msm-audio-cal-threadset-p1234.jsonl").write_text(
                "\n".join([
                    '{"event":"start","pid":1234,"tgid":1234,"fd_pid":1234}',
                    '{"event":"tracee-add","tid":1234}',
                    '{"event":"tracee-add","tid":1235}',
                    '{"event":"clone","tid":1235,"child_tid":1236}',
                    '{"event":"ioctl_entry","seq":1,"tid":1235,"request":"0x4004d0c8","read_len":4,"bytes_hex":"01020304"}',
                    '{"event":"ioctl_exit","seq":1,"tid":1235,"ret":0}',
                    '{"event":"stop","captured_entries":1,"tracees":3,"timed_out":true}',
                ]) + "\n"
            )

            summary = v2424.summarize_capture_artifacts(out_dir)

        self.assertEqual(summary["classification"], "captured-msm-audio-cal-payload-events")
        self.assertEqual(summary["helper_starts"], 1)
        self.assertEqual(summary["tracee_adds"], 2)
        self.assertEqual(summary["clone_events"], 1)
        self.assertEqual(summary["ioctl_entries"], 1)
        self.assertEqual(summary["ioctl_exits"], 1)
        self.assertEqual(summary["requests"], ["0x4004d0c8"])
        self.assertEqual(summary["task_snapshots"][0]["line_count"], 2)
        self.assertEqual(summary["payload_hashes"][0]["read_len"], 4)
        self.assertFalse(summary["raw_payload_in_summary"])
        self.assertNotIn("01020304", json.dumps(summary))

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2424.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2424")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
