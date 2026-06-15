"""Host-only tests for the V2451 ACDB M1 hybrid late-observer handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2451 = load_revalidation("native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_module_template": False,
        "module_out_dir": v2451.v2449.DEFAULT_MODULE_OUT_DIR,
        "cc": v2451.v2449.DEFAULT_CC,
        "stimulus_apk": v2451.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2451.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2451.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2451.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2451.v2450.DEFAULT_CAPTURE_DURATION_SEC,
        "capture_observe_sec": 6.0,
        "android_root_recheck_attempts": v2451.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
        "android_root_recheck_sleep_sec": 0.0,
        "post_module_root_retry_attempts": v2451.v2450.DEFAULT_POST_MODULE_ROOT_RETRY_ATTEMPTS,
        "post_module_root_retry_sleep_sec": v2451.v2450.DEFAULT_POST_MODULE_ROOT_RETRY_SLEEP_SEC,
        "post_module_adb_wait_timeout": v2451.v2450.DEFAULT_POST_MODULE_ADB_WAIT_TIMEOUT_SEC,
        "stage_adb_retry_attempts": v2451.DEFAULT_STAGE_ADB_RETRY_ATTEMPTS,
        "stage_adb_retry_sleep_sec": 0.0,
        "post_module_boot_complete_timeout_sec": v2451.DEFAULT_POST_MODULE_BOOT_COMPLETE_TIMEOUT_SEC,
        "helper_completion_timeout_sec": v2451.v2450.DEFAULT_HELPER_COMPLETION_TIMEOUT_SEC,
        "late_capture_duration_sec": v2451.DEFAULT_LATE_CAPTURE_DURATION_SEC,
        "late_helper_completion_timeout_sec": v2451.DEFAULT_LATE_HELPER_COMPLETION_TIMEOUT_SEC,
        "late_max_events": 4096,
        "max_bytes": v2451.v2449.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2451.v2449.DEFAULT_PROCESS_POLL_SEC,
        "max_unmatched_samples": v2451.v2449.DEFAULT_MAX_UNMATCHED_SAMPLES,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbM1HybridLateObserverLiveHandoffV2451(unittest.TestCase):
    def test_dry_run_declares_v2451_hybrid_boundary(self) -> None:
        payload = v2451.dry_run(args())

        self.assertEqual(payload["run_id"], "V2451")
        self.assertEqual(payload["decision"], "v2451-acdb-m1-hybrid-late-observer-live-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_live"], v2451.APPROVAL_PHRASE)
        self.assertTrue(payload["module_lifecycle"]["v2451_hybrid_late_observer"])
        self.assertEqual(payload["module_lifecycle"]["v2451_boot_service_role"], "optional early observer only")
        self.assertFalse(payload["module_lifecycle"]["native_runtime_dependency"])
        self.assertFalse(payload["module_lifecycle"]["uses_magisk_install_module"])
        self.assertEqual(payload["magisk_strategy"]["classification"], "Wi-Fi-style Android-good measurement capsule")
        self.assertEqual(payload["android_root_recheck"]["initial_handoff_attempts"], v2451.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)
        self.assertIn("root-output-empty", payload["android_root_recheck"]["classifications"])
        self.assertIn("uid=0", payload["android_root_recheck"]["hard_gate"])
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("V2449 diagnostic module plan not live-ready", " ".join(payload["future_live_blockers"]))

    def test_materialized_dry_run_adds_late_observer_before_playback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2451.dry_run(args(
                materialize_module_template=True,
                module_out_dir=Path(temp_dir),
            ))

        commands = payload["commands"]
        flat = json.dumps(commands, sort_keys=True)
        self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])
        self.assertIn("start_late_diag_observer_after_post_module_settle", commands)
        self.assertIn("wait_for_late_diag_helper_completion", commands)
        self.assertEqual(commands["playback_order"][1], "start late observer supervisor")
        self.assertIn("A90_M1_LATE_DIAG_BEGIN", flat)
        self.assertIn("A90_M1_LATE_DIAG_SUPERVISOR_STARTED", flat)
        self.assertIn("A90_M1_LATE_DIAG_END", flat)
        self.assertIn("msm-audio-cal-diag-threadset-p${pid}-late.jsonl", flat)
        self.assertIn(v2451.v2449.HELPER_NAME, flat)
        self.assertIn("/dev/msm_audio_cal", flat)
        self.assertIn("--fd-pid", flat)
        self.assertIn("--dmabuf-out-dir", flat)
        self.assertIn("dmabuf-late", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("post-fs-data.sh", flat)
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn("tinymix set", flat)

    def test_stage_adb_wait_plan_covers_shell_push_and_install(self) -> None:
        payload = v2451.dry_run(args())
        waits = payload["stage_adb_waits"]
        stage_commands = v2451.v2450.stage_commands(args())
        expected_indexes = [
            index
            for index, command in enumerate(stage_commands)
            if v2451.v2450.adb_subcommand(command) in {"shell", "push", "install"}
        ]

        self.assertEqual([item["before_stage_index"] for item in waits], expected_indexes)
        self.assertIn("shell", {item["stage_subcommand"] for item in waits})
        self.assertIn("push", {item["stage_subcommand"] for item in waits})
        self.assertIn("install", {item["stage_subcommand"] for item in waits})
        self.assertEqual(waits[2]["stage_subcommand"], "shell")

    def test_stage_adb_retry_plan_targets_v2464_transport_gap(self) -> None:
        payload = v2451.dry_run(args())
        retry = payload["stage_adb_retry"]

        self.assertTrue(retry["enabled"])
        self.assertEqual(retry["attempts"], v2451.DEFAULT_STAGE_ADB_RETRY_ATTEMPTS)
        self.assertIn("error: closed", retry["retry_markers"])
        self.assertIn("no devices/emulators found", retry["retry_markers"])
        self.assertIn("A90_M1_RESIDUE_PRESENT", retry["semantic_stop_markers"])
        self.assertIn("staged adb shell/push/install", retry["scope"])

    def test_stage_adb_retry_classifier_ignores_semantic_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = Path(temp_dir) / "stdout.txt"
            stderr = Path(temp_dir) / "stderr.txt"
            stdout.write_text("A90_M1_RESIDUE_PRESENT /data/adb/modules/a90_audio_acdb_m1_v2429\n")
            stderr.write_text("error: closed\n")
            step = {"ok": False, "stdout": str(stdout), "stderr": str(stderr)}

            self.assertTrue(v2451.stage_step_has_semantic_failure(step))
            self.assertFalse(v2451.stage_step_has_transient_adb_failure(step))

    def test_stage_adb_retry_retries_transient_closed_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            calls: list[str] = []

            def fake_run_step(name: str, command: list[str], out: Path, *, timeout_sec: float, check: bool = True) -> dict[str, object]:
                calls.append(name)
                stdout = out / f"{name}.stdout.txt"
                stderr = out / f"{name}.stderr.txt"
                stdout.write_text("")
                stderr.write_text("")
                if name == "stage-2-attempt-1":
                    stderr.write_text("error: closed\n")
                    return {"name": name, "ok": False, "rc": 1, "stdout": str(stdout), "stderr": str(stderr)}
                return {"name": name, "ok": True, "rc": 0, "stdout": str(stdout), "stderr": str(stderr)}

            original_run_step = v2451.route.run_step
            original_sleep = v2451.time.sleep
            try:
                v2451.route.run_step = fake_run_step  # type: ignore[assignment]
                v2451.time.sleep = lambda _seconds: None  # type: ignore[assignment]
                steps: list[dict[str, object]] = []
                step = v2451.run_stage_command_with_adb_retry(
                    args(stage_adb_retry_attempts=2),
                    2,
                    ["adb", "shell", "true"],
                    out_dir,
                    steps,  # type: ignore[arg-type]
                )
            finally:
                v2451.route.run_step = original_run_step  # type: ignore[assignment]
                v2451.time.sleep = original_sleep  # type: ignore[assignment]

        self.assertEqual(step["name"], "stage-2-attempt-2")
        self.assertIn("stage-2-attempt-1-adb-wait-before-shell", calls)
        self.assertIn("stage-2-attempt-2-adb-wait-before-shell", calls)
        self.assertEqual([item["name"] for item in steps if item["name"].startswith("stage-2-attempt-") and "adb-wait" not in item["name"]], ["stage-2-attempt-1", "stage-2-attempt-2"])

    def test_post_module_boot_complete_is_soft_gate_before_root(self) -> None:
        payload = v2451.dry_run(args())
        plan = payload["commands"]["android_post_module_reboot_settle"]
        flat = json.dumps(plan, sort_keys=True)

        self.assertTrue(plan["boot_complete_soft_gate"])
        self.assertEqual(plan["boot_complete_timeout_sec"], v2451.DEFAULT_POST_MODULE_BOOT_COMPLETE_TIMEOUT_SEC)
        self.assertTrue(plan["root_check_hard_gate"])
        self.assertIn("A90_POST_MODULE_BOOT_COMPLETE_WAIT_BEGIN", flat)
        self.assertIn("A90_POST_MODULE_BOOT_COMPLETE_NOT_READY", flat)
        self.assertIn("root_check", plan)
        self.assertIn("Magisk uid=0", payload["magisk_strategy"]["post_module_settle"])

    def test_late_observer_start_command_targets_audio_processes_with_supervisor(self) -> None:
        command = " ".join(v2451.late_observer_start_command(args()))

        self.assertIn("android.hardware.audio.service", command)
        self.assertIn("audioserver", command)
        self.assertIn("late-helper-pids.txt", command)
        self.assertIn("A90_M1_LATE_DIAG_HELPER_WAIT_DONE", command)
        self.assertIn("A90_M1_LATE_DIAG_END", command)
        self.assertIn("--dmabuf-out-dir \"$ARTIFACT_DIR/dmabuf-late\"", command)
        self.assertIn("&", command)

    def test_late_wait_command_waits_for_end_and_terminal_stops(self) -> None:
        command = " ".join(v2451.late_helper_completion_wait_command(args()))

        self.assertIn("A90_M1_LATE_DIAG_WAIT_BEGIN", command)
        self.assertIn("A90_M1_LATE_DIAG_WAIT_OK", command)
        self.assertIn("A90_M1_LATE_DIAG_WAIT_PARTIAL", command)
        self.assertIn("msm-audio-cal-diag-threadset-p*-late.jsonl", command)
        self.assertIn("A90_M1_LATE_DIAG_END", command)
        self.assertIn('"event":"stop"', command)

    def test_hybrid_summary_late_payload_overrides_boot_service_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "service.log").write_text(
                "A90_M1_DIAG_HELPER_START tgid=111\n"
                "A90_M1_DIAG_SERVICE_END\n"
            )
            (artifact_dir / "msm-audio-cal-diag-threadset-p111.jsonl").write_text('{"event":"start"}\n')
            (artifact_dir / "late-observer.log").write_text(
                "A90_M1_LATE_DIAG_HELPER_START tgid=222 helper_pid=333\n"
                "A90_M1_LATE_DIAG_END status=complete\n"
            )
            (artifact_dir / "msm-audio-cal-diag-threadset-p222-late.jsonl").write_text(
                '{"event":"ioctl_entry","seq":1,"request":"0x4004c8ca","read_len":2,"bytes_hex":"abcd"}\n'
                '{"event":"stop","syscall_stop_count":4,"ioctl_any_entry_count":1,'
                '"ioctl_fd_match_count":1,"ioctl_fd_miss_count":0,"fd_readlink_error_count":0}\n'
            )

            summary = v2451.summarize_hybrid_capture_artifacts(out_dir)

        self.assertEqual(summary["classification"], "late-msm-audio-cal-payload-captured")
        self.assertEqual(summary["late_observer"]["classification"], "late-msm-audio-cal-payload-captured")
        self.assertFalse(summary["late_observer"]["raw_payload_in_summary"])
        self.assertNotIn("bytes_hex", json.dumps(summary, sort_keys=True))

    def test_hybrid_summary_hashes_private_dmabuf_without_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            artifact_dir = out_dir / "device-artifacts"
            dmabuf_dir = artifact_dir / "dmabuf-late"
            dmabuf_dir.mkdir(parents=True)
            (artifact_dir / "late-observer.log").write_text(
                "A90_M1_LATE_DIAG_HELPER_START tgid=222 helper_pid=333\n"
                "A90_M1_LATE_DIAG_END status=complete\n"
            )
            (artifact_dir / "msm-audio-cal-diag-threadset-p222-late.jsonl").write_text(
                '{"event":"dmabuf_capture","seq":7,"status":"ok","cal_type":39,'
                '"cal_size":4,"mem_handle":37,"capture_len":4,"written_len":4}\n'
                '{"event":"stop","syscall_stop_count":4,"ioctl_any_entry_count":1,'
                '"ioctl_fd_match_count":1,"ioctl_fd_miss_count":0,"fd_readlink_error_count":0}\n'
            )
            (dmabuf_dir / "dmabuf-seq0007-cal39-fd37.bin").write_bytes(b"ABCD")

            summary = v2451.summarize_hybrid_capture_artifacts(out_dir)

        encoded = json.dumps(summary, sort_keys=True)
        self.assertEqual(summary["classification"], "late-msm-audio-cal-dmabuf-payload-captured")
        self.assertEqual(summary["late_observer"]["classification"], "late-msm-audio-cal-dmabuf-payload-captured")
        self.assertEqual(summary["late_observer"]["dmabuf_payload_count"], 1)
        self.assertEqual(summary["late_observer"]["dmabuf_payload_hashes"][0]["size"], 4)
        self.assertFalse(summary["late_observer"]["raw_dmabuf_in_summary"])
        self.assertNotIn("ABCD", encoded)

    def test_wrong_live_approval_exits_before_device_action(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--run-live", "--approval", "continue"],
            cwd=v2451.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2451-acdb-m1-hybrid-late-observer-live-refused")
        self.assertIn("exact AUD-5L", payload["reason"])
        self.assertFalse(payload["rolled_back"])


if __name__ == "__main__":
    unittest.main()
