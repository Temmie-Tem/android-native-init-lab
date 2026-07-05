from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta175_seccomp_handoff_execute_gate.py")


class ServerDistroWsta175SeccompHandoffExecuteGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def set_now(self, value: str):
        old = runner.now_utc
        fixed = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
        runner.now_utc = lambda: fixed
        return old

    def restore_now(self, old) -> None:
        runner.now_utc = old

    def write_handoff(self, root: Path, *, expires: str = "20260705T060000Z", token: bool = False) -> Path:
        wsta170_run_dir = root / "wsta170-live-run"
        command = [
            "python3",
            "workspace/public/src/scripts/server-distro/run_wsta170_seccomp_live_observation_execute.py",
            "--run-id",
            "wsta171-seccomp-live-observation-execute",
            "--run-dir",
            str(wsta170_run_dir),
            "--wsta169-readiness-json",
            str(root / "wsta169-readiness" / runner.wsta170.wsta169.SUMMARY_NAME),
            "--wsta168-command-json",
            str(root / "wsta168_live_command.json"),
            "--wsta168-command-sh",
            str(root / "wsta168_live_command.sh"),
            "--execution-timeout",
            "1800.0",
            "--execute-wsta170-no-load-live-observation",
            "--allow-wsta168-command-execution",
            "--ack-readiness-proof-current",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ]
        payload = {
            "schema": "a90-wsta171-wsta170-execute-command-v1",
            "state": "READY_TO_RUN_NOT_EXECUTED",
            "command": command,
            "required_ack_flags": [
                "--execute-wsta170-no-load-live-observation",
                "--allow-wsta168-command-execution",
                "--ack-readiness-proof-current",
                "--ack-no-correct-wsta161-token",
                "--ack-no-seccomp-load",
                "--ack-cleanup-required",
            ],
            "expected_outcome": {
                "decision": runner.wsta170.PASS_DECISION,
                "nested_decision": runner.wsta170.wsta167.PASS_DECISION,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
            "executed": False,
            "secret_values_logged": 0,
        }
        command_json = root / "wsta171_wsta170_execute_command.json"
        command_sh = root / "wsta171_wsta170_execute_command.sh"
        self.write_json(command_json, payload)
        script = "#!/bin/sh\nexec " + " ".join(command) + "\n"
        if token:
            script += "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD\n"
        command_sh.write_text(script, encoding="utf-8")
        handoff = {
            "schema": "a90-wsta173-expiring-wsta170-execute-handoff-v1",
            "state": "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
            "wsta172_result": str(root / "wsta172_result.json"),
            "command_json": str(command_json),
            "command_script": str(command_sh),
            "command": command,
            "required_ack_flags": payload["required_ack_flags"],
            "expected_outcome": payload["expected_outcome"],
            "freshness": {
                "readiness_ended_utc": "20260705T050000Z",
                "expires_utc": expires,
                "max_age_sec": 900,
            },
            "executed": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "correct_wsta161_token_supplied": False,
            "secret_values_logged": 0,
        }
        handoff_path = root / runner.wsta173.HANDOFF_NAME
        self.write_json(handoff_path, handoff)
        return handoff_path

    def base_args(self, root: Path, handoff: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta175"),
            "--handoff-json",
            str(handoff),
        ]

    def execute_args(self, root: Path, handoff: Path) -> list[str]:
        return self.base_args(root, handoff) + [
            "--execute-wsta175-handoff",
            "--allow-wsta170-command-execution",
            "--ack-handoff-fresh",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ]

    def test_default_blocks_after_validating_fresh_handoff_without_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_handoff(root)
            old_now = self.set_now("20260705T050300Z")
            old_exec = runner.run_generated_command
            runner.run_generated_command = lambda command, *, timeout: (_ for _ in ()).throw(
                AssertionError(f"must not execute: {command} {timeout}")
            )
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.base_args(root, handoff)))
            finally:
                runner.run_generated_command = old_exec
                self.restore_now(old_now)

        self.assertEqual(result["decision"], "wsta175-blocked-explicit-execution-gate-required")
        self.assertTrue(result["checks"]["handoff_valid"])
        self.assertTrue(result["checks"]["handoff_fresh"])
        self.assertTrue(result["checks"]["command_artifacts_valid"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_explicit_gate_executes_handoff_command_and_validates_wsta170_result(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_handoff(root)
            calls: list[list[str]] = []

            def fake_executor(command: list[str], *, timeout: float) -> dict:
                del timeout
                calls.append(command)
                run_dir = runner.command_run_dir(command)
                self.assertIsNotNone(run_dir)
                assert run_dir is not None
                self.write_json(run_dir / runner.wsta170.SUMMARY_NAME, {
                    "decision": runner.wsta170.PASS_DECISION,
                    "checks": {
                        "execution_returncode_ok": True,
                        "nested_result_present": True,
                        "nested_result_valid": True,
                    },
                    "safety": {
                        "seccomp_filter_loaded": False,
                        "seccomp_enforced": False,
                        "correct_wsta161_token_supplied": False,
                        "boot_flash": False,
                        "native_reboot": False,
                        "wifi_connect": False,
                        "dhcp": False,
                        "public_tunnel": False,
                        "packet_filter_mutation": False,
                    },
                    "nested_result": {
                        "decision": runner.wsta170.wsta167.PASS_DECISION,
                    },
                    "nested_checks": {
                        "nested_decision_pass": True,
                        "nested_observation_pass": True,
                        "nested_cleanup_ok": True,
                        "nested_final_selftest_fail_zero": True,
                        "nested_no_seccomp_load": True,
                        "nested_no_seccomp_enforce": True,
                        "nested_no_correct_token": True,
                        "nested_no_flash": True,
                        "nested_no_reboot": True,
                        "nested_no_wifi": True,
                        "nested_no_dhcp": True,
                        "nested_no_public_tunnel": True,
                        "nested_no_packet_filter_mutation": True,
                    },
                })
                return {"command": command, "returncode": 0, "stdout": "ok\n", "stderr": ""}

            old_now = self.set_now("20260705T050300Z")
            old_exec = runner.run_generated_command
            runner.run_generated_command = fake_executor
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.execute_args(root, handoff)))
            finally:
                runner.run_generated_command = old_exec
                self.restore_now(old_now)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(len(calls), 1)
        self.assertTrue(result["checks"]["wsta170_result_valid"])
        self.assertTrue(result["safety"]["wsta170_execute_command_executed"])
        self.assertTrue(result["safety"]["live_command_executed"])

    def test_expired_handoff_blocks_before_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_handoff(root, expires="20260705T050100Z")
            old_now = self.set_now("20260705T050300Z")
            old_exec = runner.run_generated_command
            runner.run_generated_command = lambda command, *, timeout: (_ for _ in ()).throw(
                AssertionError(f"must not execute: {command} {timeout}")
            )
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.execute_args(root, handoff)))
            finally:
                runner.run_generated_command = old_exec
                self.restore_now(old_now)

        self.assertEqual(result["decision"], "wsta175-blocked-handoff-expired")
        self.assertFalse(result["freshness_checks"]["not_expired"])

    def test_invalid_command_artifact_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_handoff(root, token=True)
            old_now = self.set_now("20260705T050300Z")
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.execute_args(root, handoff)))
            finally:
                self.restore_now(old_now)

        self.assertEqual(result["decision"], "wsta175-blocked-command-artifacts-invalid")
        self.assertFalse(result["command_artifact_checks"]["correct_token_absent"])


if __name__ == "__main__":
    unittest.main()
