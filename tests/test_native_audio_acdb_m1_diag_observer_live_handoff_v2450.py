"""Host-only tests for the V2450 ACDB M1 diagnostic observer live handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2450 = load_revalidation("native_audio_acdb_m1_diag_observer_live_handoff_v2450")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_module_template": False,
        "module_out_dir": v2450.v2449.DEFAULT_MODULE_OUT_DIR,
        "cc": v2450.v2449.DEFAULT_CC,
        "stimulus_apk": v2450.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2450.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2450.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2450.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2450.DEFAULT_CAPTURE_DURATION_SEC,
        "capture_observe_sec": 6.0,
        "post_module_root_retry_attempts": v2450.DEFAULT_POST_MODULE_ROOT_RETRY_ATTEMPTS,
        "post_module_root_retry_sleep_sec": v2450.DEFAULT_POST_MODULE_ROOT_RETRY_SLEEP_SEC,
        "post_module_adb_wait_timeout": v2450.DEFAULT_POST_MODULE_ADB_WAIT_TIMEOUT_SEC,
        "helper_completion_timeout_sec": v2450.DEFAULT_HELPER_COMPLETION_TIMEOUT_SEC,
        "max_bytes": v2450.v2449.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2450.v2449.DEFAULT_PROCESS_POLL_SEC,
        "max_unmatched_samples": v2450.v2449.DEFAULT_MAX_UNMATCHED_SAMPLES,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbM1DiagnosticObserverLiveHandoffV2450(unittest.TestCase):
    def test_dry_run_declares_v2450_diag_boundary(self) -> None:
        payload = v2450.dry_run(args())

        self.assertEqual(payload["run_id"], "V2450")
        self.assertEqual(payload["decision"], "v2450-acdb-m1-diag-observer-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2450.APPROVAL_PHRASE)
        self.assertEqual(payload["module_lifecycle"]["module_id"], v2450.v2449.MODULE_ID)
        self.assertEqual(payload["module_lifecycle"]["diagnostic_helper"], v2450.v2449.HELPER_NAME)
        self.assertFalse(payload["module_lifecycle"]["native_runtime_dependency"])
        self.assertFalse(payload["module_lifecycle"]["uses_magisk_install_module"])
        self.assertTrue(payload["module_lifecycle"]["v2450_helper_completion_wait"])
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("V2449 diagnostic module plan not live-ready", " ".join(payload["future_live_blockers"]))

    def test_materialized_dry_run_uses_v2449_helper_and_completion_wait(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2450.dry_run(args(
                materialize_module_template=True,
                module_out_dir=Path(temp_dir),
            ))

        flat = json.dumps(payload["commands"], sort_keys=True)
        self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
        self.assertIn("/data/adb/modules/a90_audio_acdb_m1_diag_v2449", flat)
        self.assertIn(v2450.v2449.HELPER_NAME, flat)
        self.assertIn("A90_M1_DIAG_WAIT_BEGIN", flat)
        self.assertIn("A90_M1_DIAG_WAIT_OK", flat)
        self.assertIn("A90_M1_DIAG_WAIT_PARTIAL", flat)
        self.assertIn("rollback_v2321", flat)
        self.assertNotIn("a90_acdb_ioctl_capture_threadset_v2423", flat)
        self.assertNotIn("a90_audio_acdb_m1_v2429", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("post-fs-data.sh", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn("tinymix set", flat)

    def test_summarize_diag_artifacts_classifies_partial_when_stop_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "service.log").write_text(
                "A90_M1_DIAG_SERVICE_BEGIN\n"
                "A90_M1_DIAG_HELPER_START tgid=1234\n"
                "A90_M1_DIAG_SERVICE_END\n"
            )
            (artifact_dir / "msm-audio-cal-diag-threadset-p1234.jsonl").write_text(
                '{"event":"start"}\n'
                '{"event":"tracee-add","tid":1234}\n'
            )

            summary = v2450.summarize_diag_capture_artifacts(out_dir)

        self.assertEqual(summary["classification"], "partial-helper-still-running")
        self.assertEqual(summary["helper_starts"], 1)
        self.assertEqual(summary["tracee_adds"], 1)
        self.assertEqual(len(summary["missing_stop_files"]), 1)

    def test_summarize_diag_artifacts_classifies_ioctl_any_fd_miss(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "service.log").write_text("A90_M1_DIAG_SERVICE_END\n")
            (artifact_dir / "msm-audio-cal-diag-threadset-p42.jsonl").write_text(
                '{"event":"start"}\n'
                '{"event":"ioctl_unmatched","sample":1,"request":"0x1234","fd":7,"readlink_errno":0,"fd_target":"socket:[1]"}\n'
                '{"event":"stop","syscall_stop_count":10,"syscall_entry_count":5,'
                '"ioctl_any_entry_count":2,"ioctl_fd_match_count":0,'
                '"ioctl_fd_miss_count":2,"fd_readlink_error_count":0,"unmatched_samples":1}\n'
            )

            summary = v2450.summarize_diag_capture_artifacts(out_dir)

        self.assertEqual(summary["classification"], "ioctl-any-but-fd-miss")
        self.assertEqual(summary["ioctl_unmatched"], 1)
        self.assertEqual(summary["ioctl_any_entry_count"], 2)
        self.assertEqual(summary["ioctl_fd_miss_count"], 2)

    def test_summarize_diag_artifacts_classifies_payload_without_raw_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "service.log").write_text("A90_M1_DIAG_SERVICE_END\n")
            (artifact_dir / "msm-audio-cal-diag-threadset-p77.jsonl").write_text(
                '{"event":"ioctl_entry","seq":1,"request":"0x4004c8ca","read_len":2,"bytes_hex":"00ff"}\n'
                '{"event":"ioctl_exit","seq":1,"request":"0x4004c8ca","ret":0}\n'
                '{"event":"stop","syscall_stop_count":4,"syscall_entry_count":2,'
                '"ioctl_any_entry_count":1,"ioctl_fd_match_count":1,'
                '"ioctl_fd_miss_count":0,"fd_readlink_error_count":0,"unmatched_samples":0}\n'
            )

            summary = v2450.summarize_diag_capture_artifacts(out_dir)

        self.assertEqual(summary["classification"], "msm-audio-cal-payload-captured")
        self.assertFalse(summary["raw_payload_in_summary"])
        self.assertEqual(summary["ioctl_entries"], 1)
        self.assertEqual(summary["ioctl_exits"], 1)
        self.assertEqual(summary["payload_hashes"][0]["sha256"], v2450.payload_sha256("00ff"))
        self.assertNotIn("bytes_hex", json.dumps(summary, sort_keys=True))

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_live_handoff_v2450.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2450.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2450-acdb-m1-diag-observer-live-refused")
        self.assertIn("exact AUD-5K", payload["reason"])
        self.assertFalse(payload["rolled_back"])


if __name__ == "__main__":
    unittest.main()
