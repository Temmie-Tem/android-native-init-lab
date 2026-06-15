"""Host-only tests for the V2422 clone-following ACDB live handoff runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2422 = load_revalidation("native_audio_acdb_clone_follow_live_handoff_v2422")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_capture_helper": False,
        "helper_out_dir": v2422.v2421.DEFAULT_HELPER_OUT_DIR,
        "cc": v2422.v2421.DEFAULT_CC,
        "stimulus_apk": v2422.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2422.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2422.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2422.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2422.v2421.DEFAULT_DURATION_SEC,
        "capture_warmup_sec": v2422.DEFAULT_CAPTURE_WARMUP_SEC,
        "max_bytes": v2422.v2421.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2422.v2421.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbCloneFollowLiveHandoff(unittest.TestCase):
    def test_dry_run_declares_v2422_clone_follow_live_boundary(self) -> None:
        payload = v2422.dry_run(args())

        self.assertEqual(payload["run_id"], "V2422")
        self.assertEqual(payload["decision"], "v2422-acdb-clone-follow-capture-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2422.APPROVAL_PHRASE)
        self.assertEqual(payload["capture_contract"]["watcher"]["mode"], "process-attach-plus-PTRACE_O_TRACECLONE")
        self.assertIn("native_audio_acdb_clone_follow_live_handoff_v2422.py", payload["live_runner"])

    def test_materialized_dry_run_has_stimulus_install_and_pull_permission_fix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2422.dry_run(args(materialize_capture_helper=True, helper_out_dir=Path(temp_dir)))

        commands = payload["commands"]
        flat = json.dumps(commands, sort_keys=True)
        self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
        self.assertIn("stage_clone_follow_helper_and_stimulus", commands)
        self.assertIn("A90AudioRouteStimulus.apk", flat)
        self.assertIn("install", flat)
        self.assertIn("prepare_private_artifacts_for_pull", commands)
        self.assertIn("chmod 644", " ".join(commands["prepare_private_artifacts_for_pull"]))
        self.assertIn("rollback_v2321", commands)

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_clone_follow_live_handoff_v2422.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2422.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2422-acdb-clone-follow-capture-live-refused")
        self.assertIn("exact AUD-5E", payload["reason"])
        self.assertFalse(payload["rolled_back"])

    def test_summarize_clone_jsonl_hashes_payload_without_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts"
            artifact_dir.mkdir()
            (artifact_dir / "audio-hal-pids.txt").write_text("1234\n")
            (artifact_dir / "msm-audio-cal-clone-p1234.jsonl").write_text(
                '\n'.join([
                    '{"event":"start","pid":1234}',
                    '{"event":"tracee-add","tid":1234}',
                    '{"event":"clone","tid":1234,"child_tid":1235}',
                    '{"event":"ioctl_entry","seq":1,"request":"0x4004d0c8","read_len":4,"bytes_hex":"01020304"}',
                    '{"event":"ioctl_exit","seq":1,"ret":0}',
                ]) + "\n"
            )

            summary = v2422.summarize_capture_artifacts(out_dir)

        self.assertEqual(summary["classification"], "captured-msm-audio-cal-payload-events")
        self.assertEqual(summary["helper_starts"], 1)
        self.assertEqual(summary["tracee_adds"], 1)
        self.assertEqual(summary["clone_events"], 1)
        self.assertEqual(summary["ioctl_entries"], 1)
        self.assertEqual(summary["ioctl_exits"], 1)
        self.assertEqual(summary["requests"], ["0x4004d0c8"])
        self.assertEqual(summary["payload_hashes"][0]["read_len"], 4)
        self.assertFalse(summary["raw_payload_in_summary"])
        self.assertNotIn("01020304", json.dumps(summary))

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_clone_follow_live_handoff_v2422.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2422.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2422")
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
