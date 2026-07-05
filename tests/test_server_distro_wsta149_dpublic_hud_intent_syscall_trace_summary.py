from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta149_dpublic_hud_intent_syscall_trace_summary.py")
wsta149 = runner.wsta149


class ServerDistroWsta149DpublicHudIntentSyscallTraceSummaryTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def source_result(self) -> dict:
        syscalls = [
            "brk",
            "close",
            "execve",
            "fsync",
            "openat",
            "renameat",
            "write",
        ]
        return {
            "decision": wsta149.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta149-live-test",
            "local_image_sha256": wsta149.WSTA115_STRACE_IMAGE_SHA256,
            "safety": {
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "public_smoke": False,
                "packet_filter_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "drm_open": False,
                "kms_setcrtc": False,
            },
            "checks": {
                "service_identity_ok": True,
                "launcher_exec_logged": True,
                "intent_written": True,
                "intent_schema_ok": True,
                "atomic_rename_observed": True,
                "network_syscalls_absent": True,
                "drm_syscalls_absent": True,
                "trace_artifact_saved": True,
                "final_selftest_fail_zero": True,
            },
            "syscall_profile": {
                "schema": "a90-wsta149-dpublic-hud-intent-syscall-profile-v1",
                "service": "dpublic-hud",
                "scope": "hud-intent-producer-only",
                "command_shape": (
                    "a90-service-launch dpublic-hud strace -f "
                    "a90-dpublic-hud-intent --output /run/a90-dpublic/hud-intent.json"
                ),
                "intent_path": wsta149.REMOTE_INTENT_JSON,
                "intent_sequence": wsta149.INTENT_SEQUENCE,
                "native_presenter_owner": True,
                "public_default_off": True,
                "no_new_privs": True,
                "cap_eff_zero": True,
                "core_syscalls": list(wsta149.CORE_SYSCALLS),
                "core_syscalls_observed": True,
                "atomic_rename_observed": True,
                "network_syscalls_absent": True,
                "ioctl_syscall_absent": True,
                "drm_trace_absent": True,
                "syscall_count": len(syscalls),
                "syscall_names": syscalls,
                "trace_artifacts": {
                    "all_saved": True,
                    "raw_trace": {"sha256": "raw-sha"},
                    "syscall_list": {"sha256": "syscalls-sha"},
                    "intent_json": {"sha256": "intent-sha"},
                },
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "final_version": {
                "text": "A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)",
            },
            "final_selftest": {
                "text": "selftest: pass=12 warn=1 fail=0",
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def test_summarize_source_passes_for_valid_wsta149_result(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_path = root / "source" / "wsta149_result.json"
            source_path.parent.mkdir(parents=True)
            source_path.write_text(json.dumps(self.source_result()) + "\n", encoding="utf-8")

            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary"),
                "--source-json",
                str(source_path),
                "--summarize-wsta149-hud-intent-trace",
            ]))
            proof = json.loads((root / "summary" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(proof["decision"], runner.PASS_DECISION)
        self.assertEqual(proof["schema"], "a90-wsta149-dpublic-hud-intent-syscall-trace-live-v1")
        self.assertEqual(proof["service"], "dpublic-hud")
        self.assertEqual(proof["scope"], "hud-intent-producer-only")
        self.assertEqual(proof["uid"], 3904)
        self.assertEqual(proof["gid"], 3904)
        self.assertTrue(proof["no_new_privs"])
        self.assertTrue(proof["cap_eff_zero"])
        self.assertTrue(proof["atomic_rename_observed"])
        self.assertTrue(proof["network_syscalls_absent"])
        self.assertTrue(proof["ioctl_syscall_absent"])
        self.assertTrue(proof["drm_trace_absent"])
        self.assertTrue(proof["trace_artifacts_saved"])
        self.assertEqual(proof["raw_trace_sha256"], "raw-sha")
        self.assertFalse(proof["public_url_value_logged"])
        self.assertEqual(proof["secret_values_logged"], 0)

    def test_validation_fails_closed_on_network_or_drm_syscalls(self) -> None:
        source = self.source_result()
        source["syscall_profile"]["syscall_names"].append("socket")
        self.assertFalse(runner.validate_source_result(source)["no_network_syscalls"])

        source = self.source_result()
        source["syscall_profile"]["syscall_names"].append("ioctl")
        self.assertFalse(runner.validate_source_result(source)["no_drm_or_ioctl"])

    def test_default_and_nonprivate_runs_block(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_path = root / "source.json"
            source_path.write_text(json.dumps(self.source_result()) + "\n", encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary"),
                "--source-json",
                str(source_path),
            ]))
        self.assertEqual(result["decision"], "wsta149-summary-blocked-explicit-gate-required")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "source.json"
            source_path.write_text(json.dumps(self.source_result()) + "\n", encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "summary"),
                "--source-json",
                str(source_path),
                "--summarize-wsta149-hud-intent-trace",
            ]))
        self.assertEqual(result["decision"], "wsta149-summary-blocked-nonprivate-run-dir")


if __name__ == "__main__":
    unittest.main()
