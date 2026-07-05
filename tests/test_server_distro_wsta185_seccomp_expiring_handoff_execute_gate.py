from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/server-distro/run_wsta185_seccomp_expiring_handoff_execute_gate.py"
)


class ServerDistroWsta185SeccompExpiringHandoffExecuteGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def format_utc(self, value: dt.datetime) -> str:
        return value.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def write_handoff(self, root: Path, *, expired: bool = False, dirty_script: bool = False) -> tuple[Path, list[str]]:
        bundle_json = root / "wsta180_operator_handoff.json"
        bundle_sh = root / "wsta180_operator_handoff_commands.sh"
        self.write_json(bundle_json, {"schema": "a90-wsta180-seccomp-live-handoff-bundle-v1"})
        bundle_sh.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        command = runner.wsta184.wsta182.execution_command(
            root / "fresh-wsta182-readiness-status",
            bundle_json,
            bundle_sh,
            1800.0,
            1800.0,
        )
        command_payload = runner.wsta184.wsta182.command_payload(command)
        command_json = root / "fresh-wsta182-readiness-status" / runner.wsta184.wsta182.COMMAND_JSON_NAME
        command_sh = root / "fresh-wsta182-readiness-status" / runner.wsta184.wsta182.COMMAND_SH_NAME
        self.write_json(command_json, command_payload)
        script_text = "#!/bin/sh\nset -eu\nexec " + " ".join(command) + "\n"
        if dirty_script:
            script_text += "printf '%s\\n' WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD\n"
        command_sh.write_text(script_text, encoding="utf-8")
        now = dt.datetime.now(dt.timezone.utc)
        expires = now - dt.timedelta(seconds=1) if expired else now + dt.timedelta(seconds=900)
        freshness = {
            "now_utc": self.format_utc(now),
            "age_sec": 0,
            "max_age_sec": 900,
            "expires_utc": self.format_utc(expires),
        }
        handoff = runner.wsta184.handoff_payload(
            root / "fresh-wsta183-readiness" / runner.wsta184.wsta183.SUMMARY_NAME,
            root / "fresh-wsta182-readiness-status" / runner.wsta184.wsta182.SUMMARY_NAME,
            command_json,
            command_sh,
            command_payload,
            freshness,
        )
        handoff_path = root / runner.wsta184.HANDOFF_NAME
        self.write_json(handoff_path, handoff)
        return handoff_path, command

    def base_args(self, root: Path, handoff_json: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta185"),
            "--handoff-json",
            str(handoff_json),
        ]

    def execute_args(self, root: Path, handoff_json: Path) -> list[str]:
        return self.base_args(root, handoff_json) + [
            "--execute-wsta185-handoff",
            "--allow-wsta181-command-execution",
            "--ack-handoff-fresh",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ]

    def write_wsta181_pass_result(self, command: list[str]) -> Path:
        run_dir = runner.command_run_dir(command)
        self.assertIsNotNone(run_dir)
        assert run_dir is not None
        result_path = run_dir / runner.wsta181.SUMMARY_NAME
        self.write_json(result_path, {
            "decision": runner.wsta181.PASS_DECISION,
            "checks": {
                "handoff_bundle_valid": True,
                "execution_packet_valid": True,
                "post_run_audit_command_valid": True,
                "execution_returncode_ok": True,
                "post_run_audit_returncode_ok": True,
                "post_run_audit_result_present": True,
                "post_run_audit_result_valid": True,
            },
            "post_run_audit_result": {
                "decision": runner.wsta181.wsta179.PASS_DECISION,
            },
            "post_run_deep_audit_checks": {
                "source_wsta175_executed": True,
                "source_wsta170_executed": True,
                "wsta175_decision_pass": True,
                "wsta170_decision_pass": True,
                "wsta167_decision_pass": True,
            },
            "safety": {
                "handoff_consumed": True,
                "wsta178_execute_command_executed": True,
                "wsta177_execute_command_executed": True,
                "wsta175_execute_command_executed": True,
                "wsta170_execute_command_executed": True,
                "post_run_audit_executed": True,
                "live_command_executed": True,
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "packet_filter_mutation": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        })
        return result_path

    def test_source_gate_validates_fresh_handoff_but_does_not_execute(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff_json, _command = self.write_handoff(root)
            old_exec = runner.run_generated_command
            runner.run_generated_command = lambda command, *, timeout: (_ for _ in ()).throw(
                AssertionError(f"must not execute: {command} {timeout}")
            )
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.base_args(root, handoff_json)))
            finally:
                runner.run_generated_command = old_exec

        self.assertEqual(result["decision"], "wsta185-blocked-explicit-execution-gate-required")
        self.assertTrue(result["checks"]["handoff_valid"])
        self.assertTrue(result["checks"]["command_artifacts_valid"])
        self.assertTrue(result["checks"]["freshness_valid"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_explicit_gate_executes_wsta181_command_and_validates_result(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff_json, command = self.write_handoff(root)
            calls: list[list[str]] = []

            def fake_executor(exec_command: list[str], *, timeout: float) -> dict:
                del timeout
                calls.append(exec_command)
                self.assertEqual(exec_command, command)
                self.write_wsta181_pass_result(exec_command)
                return {"command": exec_command, "returncode": 0, "stdout": "ok\n", "stderr": ""}

            old_exec = runner.run_generated_command
            runner.run_generated_command = fake_executor
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.execute_args(root, handoff_json)))
            finally:
                runner.run_generated_command = old_exec

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(len(calls), 1)
        self.assertTrue(result["checks"]["wsta181_result_valid"])
        self.assertTrue(result["safety"]["handoff_consumed"])
        self.assertTrue(result["safety"]["wsta181_execute_command_executed"])
        self.assertTrue(result["safety"]["wsta175_execute_command_executed"])
        self.assertTrue(result["safety"]["wsta170_execute_command_executed"])
        self.assertTrue(result["wsta181_result"]["deep_audit"]["wsta167_decision_pass"])

    def test_expired_handoff_blocks_before_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff_json, _command = self.write_handoff(root, expired=True)
            old_exec = runner.run_generated_command
            runner.run_generated_command = lambda command, *, timeout: (_ for _ in ()).throw(
                AssertionError(f"must not execute: {command} {timeout}")
            )
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.execute_args(root, handoff_json)))
            finally:
                runner.run_generated_command = old_exec

        self.assertEqual(result["decision"], "wsta185-blocked-handoff-expired-or-stale")
        self.assertFalse(result["freshness_checks"]["not_expired"])

    def test_bad_command_artifact_blocks_before_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff_json, _command = self.write_handoff(root, dirty_script=True)
            old_exec = runner.run_generated_command
            runner.run_generated_command = lambda command, *, timeout: (_ for _ in ()).throw(
                AssertionError(f"must not execute: {command} {timeout}")
            )
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.execute_args(root, handoff_json)))
            finally:
                runner.run_generated_command = old_exec

        self.assertEqual(result["decision"], "wsta185-blocked-command-artifacts-invalid")
        self.assertFalse(result["command_artifact_checks"]["correct_token_literal_absent"])


if __name__ == "__main__":
    unittest.main()
