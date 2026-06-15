"""Host-only tests for the V2449 ACDB M1 diagnostic observer planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2449 = load_revalidation("native_audio_acdb_m1_diag_observer_planner_v2449")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "materialize_module_template": False,
        "module_out_dir": v2449.DEFAULT_MODULE_OUT_DIR,
        "cc": v2449.DEFAULT_CC,
        "stimulus_apk": v2449.v2396.DEFAULT_STIMULUS_APK,
        "capture_duration_sec": v2449.DEFAULT_CAPTURE_DURATION_SEC,
        "max_bytes": v2449.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2449.DEFAULT_PROCESS_POLL_SEC,
        "max_unmatched_samples": v2449.DEFAULT_MAX_UNMATCHED_SAMPLES,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbM1DiagnosticObserverPlannerV2449(unittest.TestCase):
    def test_helper_source_adds_diagnostic_counters_without_native_ioctls(self) -> None:
        state = v2449.source_state()
        text = v2449.HELPER_SOURCE.read_text()

        self.assertTrue(state["ok"], state)
        self.assertTrue(state["contains_ptrace_attach"])
        self.assertTrue(state["contains_ptrace_traceclone"])
        self.assertTrue(state["contains_ptrace_syscall"])
        self.assertTrue(state["contains_ioctl_syscall_filter"])
        self.assertTrue(state["contains_compat_arm_ioctl_filter"])
        self.assertTrue(state["contains_regset_len_abi_detection"])
        self.assertTrue(state["contains_abi_metadata"])
        self.assertTrue(state["contains_task_enumeration"])
        self.assertTrue(state["contains_fd_owner_option"])
        self.assertTrue(state["contains_unmatched_ioctl_event"])
        self.assertTrue(state["contains_stop_counters"])
        self.assertTrue(state["contains_fd_miss_counters"])
        self.assertTrue(state["contains_unmatched_sample_limit"])
        self.assertTrue(state["contains_dmabuf_capture"])
        self.assertTrue(state["contains_mmap_lifecycle_capture"])
        self.assertTrue(state["contains_signed_mmap_fd_filter"])
        self.assertTrue(state["contains_remote_mmap_fallback"])
        self.assertTrue(state["contains_targeted_set_cal_constants_without_forbidden_symbol"])
        self.assertTrue(state["contains_monotonic_ts"])
        self.assertTrue(state["contains_wall_ts"])
        self.assertTrue(state["forbidden_ok"], state["forbidden"])
        self.assertIn("ioctl_unmatched", text)
        self.assertIn("syscall_stop_count", text)
        self.assertIn("ioctl_any_entry_count", text)
        self.assertIn("ioctl_fd_miss_count", text)
        self.assertIn("fd_readlink_error_count", text)
        self.assertIn("max_unmatched_samples", text)
        self.assertIn("--dmabuf-out-dir", text)
        self.assertIn("dmabuf_capture", text)
        self.assertIn("mmap_entry", text)
        self.assertIn("mmap_exit", text)
        self.assertIn("mmap_fd_arg", text)
        self.assertIn("(int32_t)((uint32_t)frame->args[4])", text)
        self.assertIn("ok-remote-mmap", text)
        self.assertIn("A90_COMPAT_ARM_NR_MMAP2", text)
        self.assertIn("A90_CAL_CMD_SET_COMPAT", text)
        self.assertIn("A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE", text)
        self.assertIn("CLOCK_MONOTONIC", text)
        self.assertIn("wall_ms", text)
        self.assertIn("PTRACE_SYSCALL", text)
        self.assertIn("PTRACE_O_TRACECLONE", text)
        self.assertIn("A90_COMPAT_ARM_NR_IOCTL", text)
        self.assertIn("A90_COMPAT_ARM_GPR_BYTES", text)
        self.assertIn("regset_len", text)
        self.assertIn('"aarch32"', text)
        self.assertIn('"aarch64"', text)
        self.assertNotIn("open(\"/dev/msm_audio_cal", text)
        self.assertNotIn("AUDIO_SET_CALIBRATION", text)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", text)

    def test_service_waits_for_helpers_and_passes_diagnostic_flags(self) -> None:
        service = v2449.service_sh(
            duration_sec=v2449.DEFAULT_CAPTURE_DURATION_SEC,
            max_bytes=v2449.DEFAULT_MAX_BYTES,
            process_poll_sec=v2449.DEFAULT_PROCESS_POLL_SEC,
            max_unmatched_samples=v2449.DEFAULT_MAX_UNMATCHED_SAMPLES,
        )

        self.assertIn("A90_M1_DIAG_SERVICE_BEGIN", service)
        self.assertIn("A90_M1_DIAG_HELPER_START", service)
        self.assertIn("A90_M1_DIAG_HELPER_WAIT_BEGIN", service)
        self.assertIn("A90_M1_DIAG_HELPER_WAIT_DONE", service)
        self.assertIn("A90_M1_DIAG_SERVICE_END", service)
        self.assertIn(f"HELPER=\"$MODDIR/bin/{v2449.HELPER_NAME}\"", service)
        self.assertIn('HELPER_MAX_DURATION_SEC="120"', service)
        self.assertIn("--tgid \"$pid\"", service)
        self.assertIn("--fd-pid \"$pid\"", service)
        self.assertIn("--device-substr /dev/msm_audio_cal", service)
        self.assertIn("--max-unmatched-samples \"$MAX_UNMATCHED_SAMPLES\"", service)
        self.assertIn("--dmabuf-out-dir \"$OUT/dmabuf\"", service)
        self.assertIn("--max-dmabuf-bytes \"$MAX_DMABUF_BYTES\"", service)
        self.assertIn("wait \"$helper_pid\"", service)
        self.assertIn("msm-audio-cal-diag-threadset-p${pid}.jsonl", service)
        self.assertNotIn("post-fs-data.sh", service)
        self.assertNotIn("magisk --install-module", service)
        self.assertNotIn("tinyplay", service)

    def test_dry_run_defines_v2449_boundary_and_collection_contract(self) -> None:
        payload = v2449.dry_run_payload(args())

        self.assertEqual(payload["run_id"], "V2449")
        self.assertEqual(payload["decision"], "v2449-acdb-m1-diagnostic-observer-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["approval_phrase_required_for_future_live"], v2449.APPROVAL_PHRASE)
        self.assertTrue(payload["diagnostic_contract"]["fixes_v2447_capture_gap"])
        self.assertTrue(payload["diagnostic_contract"]["adds_syscall_ioctl_fd_counters"])
        self.assertTrue(payload["diagnostic_contract"]["adds_bounded_unmatched_ioctl_samples"])
        self.assertTrue(payload["diagnostic_contract"]["adds_private_dmabuf_payload_capture"])
        self.assertTrue(payload["diagnostic_contract"]["adds_mmap_lifecycle_fallback"])
        self.assertTrue(payload["diagnostic_contract"]["requires_terminal_stop_before_collection"])
        self.assertIn("private binary artifacts", payload["diagnostic_contract"]["dmabuf_capture_policy"])
        self.assertTrue(payload["planned_live"]["collection_contract"]["must_wait_for_service_helper_completion"])
        self.assertTrue(payload["planned_live"]["collection_contract"]["must_poll_jsonl_terminal_stop_before_pull"])
        self.assertEqual(
            payload["planned_live"]["collection_contract"]["missing_terminal_stop_classification"],
            "partial-helper-still-running",
        )
        self.assertFalse(payload["module"]["native_runtime_dependency"])
        self.assertFalse(payload["module"]["persistent_module_baseline"])
        self.assertTrue(payload["module"]["uses_service_sh"])
        self.assertFalse(payload["module"]["uses_post_fs_data"])
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn("diagnostic M1 module template not materialized", " ".join(payload["future_live_blockers"]))

    def test_materialize_module_template_builds_private_zip_and_diag_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2449.dry_run_payload(args(
                materialize_module_template=True,
                module_out_dir=Path(temp_dir),
            ))

            module = payload["module"]
            self.assertTrue(module["ok"], module)
            self.assertTrue(module["helper"]["ok"], module["helper"])
            self.assertTrue(module["helper_module_binary"]["ok"], module["helper_module_binary"])
            self.assertTrue(module["zip"]["ok"], module["zip"])
            self.assertEqual(module["zip"]["mode"], "0o600")
            self.assertTrue((Path(temp_dir) / "service.sh").exists())
            self.assertTrue((Path(temp_dir) / "bin" / v2449.HELPER_NAME).exists())
            self.assertTrue((Path(temp_dir) / f"{v2449.MODULE_ID}.zip").exists())
            self.assertEqual(payload["future_live_blockers"], [])
            self.assertTrue(payload["future_live_ready"], payload["future_live_blockers"])

    def test_command_safety_requires_diagnostics_and_rejects_replay_paths(self) -> None:
        payload = v2449.dry_run_payload(args())
        executable_plan = json.dumps(
            {
                "planned_live": payload["planned_live"],
                "module_files": {
                    key: value.decode(errors="replace")
                    for key, value in v2449.module_files(
                        v2449.DEFAULT_CAPTURE_DURATION_SEC,
                        v2449.DEFAULT_MAX_BYTES,
                        v2449.DEFAULT_PROCESS_POLL_SEC,
                        v2449.DEFAULT_MAX_UNMATCHED_SAMPLES,
                        include_helper=False,
                    ).items()
                },
            },
            sort_keys=True,
        )
        full_payload = json.dumps(payload, sort_keys=True)

        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertIn(v2449.HELPER_NAME, full_payload)
        self.assertIn("ioctl_unmatched", full_payload)
        self.assertIn("syscall_stop_count", full_payload)
        self.assertIn("ioctl_any_entry_count", full_payload)
        self.assertIn("dmabuf_capture", full_payload)
        self.assertIn("mmap_entry", full_payload)
        self.assertIn("ok-remote-mmap", full_payload)
        self.assertIn("partial-helper-still-running", full_payload)
        self.assertIn("helper-completion", full_payload)
        self.assertNotIn("magisk --install-module", executable_plan)
        self.assertNotIn("post-fs-data.sh", executable_plan)
        self.assertNotIn("AUDIO_SET_CALIBRATION", executable_plan)
        self.assertNotIn("AUDIO_ALLOCATE_CALIBRATION", executable_plan)
        self.assertNotIn("tinyplay", executable_plan)
        self.assertNotIn("tinymix set", executable_plan)

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2449.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2449")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
