"""Host-only tests for the V2426 hardened ACDB live rerun wrapper."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path

from _loader import load_revalidation

v2426 = load_revalidation("native_audio_acdb_threadset_clone_follow_live_handoff_v2426")


def args(**overrides: object) -> argparse.Namespace:
    base = v2426.base
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_capture_helper": False,
        "helper_out_dir": base.v2423.DEFAULT_HELPER_OUT_DIR,
        "cc": base.v2423.DEFAULT_CC,
        "stimulus_apk": base.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": base.v2396.DEFAULT_DURATION_MS,
        "sample_rate": base.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": base.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": base.v2423.DEFAULT_DURATION_SEC,
        "capture_warmup_sec": base.DEFAULT_CAPTURE_WARMUP_SEC,
        "max_bytes": base.v2423.DEFAULT_MAX_BYTES,
        "process_poll_sec": base.v2423.DEFAULT_PROCESS_POLL_SEC,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbThreadsetCloneFollowV2426Wrapper(unittest.TestCase):
    def test_dry_run_relabels_runner_identity_and_keeps_stage_waits(self) -> None:
        payload = v2426.dry_run(args())

        self.assertEqual(payload["run_id"], "V2426")
        self.assertEqual(payload["build_tag"], "v2426-audio-acdb-threadset-clone-follow-live-rerun")
        self.assertEqual(payload["decision"], "v2426-acdb-threadset-clone-follow-capture-live-dry-run")
        self.assertTrue(payload["inherits_v2425_stage_adb_waits"])
        self.assertIn("native_audio_acdb_threadset_clone_follow_live_handoff_v2426.py", payload["live_runner"])
        self.assertIn("native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py", payload["base_runner"])
        self.assertEqual([item["before_stage_index"] for item in payload["stage_adb_waits"]], [1, 2, 3])

    def test_default_live_out_dir_uses_current_run_id(self) -> None:
        out_dir = v2426.base.default_live_out_dir()
        self.assertIn("v2426-acdb-threadset-clone-follow-capture-", str(out_dir))

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_live_handoff_v2426.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2426.base.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2426")
        self.assertEqual(payload["decision"], "v2426-acdb-threadset-clone-follow-capture-live-refused")
        self.assertFalse(payload["rolled_back"])


if __name__ == "__main__":
    unittest.main()
