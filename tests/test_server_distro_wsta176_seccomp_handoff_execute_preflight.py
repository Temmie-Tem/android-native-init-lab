from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta176_seccomp_handoff_execute_preflight.py")


class ServerDistroWsta176SeccompHandoffExecutePreflightTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta168_command(self, root: Path) -> tuple[Path, Path]:
        payload = {
            "schema": "a90-wsta168-seccomp-live-observation-command-v1",
            "state": "READY_TO_RUN_NOT_EXECUTED",
            "command": [
                "python3",
                "workspace/public/src/scripts/server-distro/run_wsta167_seccomp_live_observation.py",
                "--run-id",
                "wsta168-seccomp-live-observation-execute",
                "--run-dir",
                str(root / "wsta167-live-run"),
                "--execute-seccomp-live-observation",
                "--allow-seccomp-live-observation",
                "--ack-no-correct-wsta161-token",
                "--ack-no-seccomp-load",
                "--ack-cleanup-required",
            ],
            "required_ack_flags": [
                "--execute-seccomp-live-observation",
                "--allow-seccomp-live-observation",
                "--ack-no-correct-wsta161-token",
                "--ack-no-seccomp-load",
                "--ack-cleanup-required",
            ],
            "expected_outcome": {
                "decision": "wsta167-seccomp-live-observation-pass",
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
                "scenario_returncode": 65,
            },
            "executed": False,
            "secret_values_logged": 0,
        }
        command_json = root / "wsta168_live_command.json"
        command_sh = root / "wsta168_live_command.sh"
        self.write_json(command_json, payload)
        command_sh.write_text("#!/bin/sh\nexec true\n", encoding="utf-8")
        return command_json, command_sh

    def base_args(self, root: Path, command_json: Path, command_sh: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta176"),
            "--wsta168-command-json",
            str(command_json),
            "--wsta168-command-sh",
            str(command_sh),
        ]

    def gated_args(self, root: Path, command_json: Path, command_sh: Path) -> list[str]:
        return self.base_args(root, command_json, command_sh) + ["--emit-wsta175-execute-preflight"]

    def fake_pass_bundle(self, calls: list[str], command_json: Path, command_sh: Path):
        def fake_wsta174(args):
            calls.append("wsta174")
            handoff = args.run_dir / "wsta173-expiring-handoff" / runner.wsta174.wsta173.HANDOFF_NAME
            self.assertTrue(args.emit_fresh_expiring_handoff)
            result = {
                "decision": runner.wsta174.PASS_DECISION,
                "gate_decision": "ok",
                "wsta168_command_json": runner.rel(command_json),
                "wsta168_command_sh": runner.rel(command_sh),
                "checks": {
                    "fresh_preflight_valid": True,
                    "expiring_handoff_valid": True,
                },
                "expiring_handoff": {
                    "handoff_json": runner.rel(handoff),
                    "handoff_state": "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
                    "executed": False,
                    "expires_utc": "20260705T060000Z",
                },
                "safety": {
                    "handoff_generated": True,
                    "live_command_executed": False,
                    "seccomp_filter_loaded": False,
                    "seccomp_enforced": False,
                    "correct_wsta161_token_supplied": False,
                },
            }
            self.write_json(args.run_dir / runner.wsta174.SUMMARY_NAME, result)
            self.write_json(handoff, {"schema": "handoff-fixture"})
            return result

        def fake_wsta175(args):
            calls.append("wsta175")
            self.assertTrue(str(args.handoff_json).endswith(runner.wsta174.wsta173.HANDOFF_NAME))
            self.assertFalse(args.execute_wsta175_handoff)
            result = {
                "decision": "wsta175-blocked-explicit-execution-gate-required",
                "handoff_json": runner.rel(args.handoff_json),
                "checks": {
                    "handoff_valid": True,
                    "handoff_fresh": True,
                    "command_artifacts_valid": True,
                },
                "safety": {
                    "live_command_executed": False,
                    "wsta170_execute_command_executed": False,
                    "seccomp_filter_loaded": False,
                    "seccomp_enforced": False,
                    "correct_wsta161_token_supplied": False,
                },
            }
            self.write_json(args.run_dir / runner.wsta175.SUMMARY_NAME, result)
            return result

        return fake_wsta174, fake_wsta175

    def swap_nested(self, fake_wsta174, fake_wsta175):
        old = (runner.wsta174.run, runner.wsta175.run)
        runner.wsta174.run = fake_wsta174
        runner.wsta175.run = fake_wsta175
        return old

    def restore_nested(self, old) -> None:
        runner.wsta174.run, runner.wsta175.run = old

    def test_preflight_generates_wsta175_execute_command_without_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            calls: list[str] = []
            old = self.swap_nested(*self.fake_pass_bundle(calls, command_json, command_sh))
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.gated_args(root, command_json, command_sh)
                ))
            finally:
                self.restore_nested(old)
            payload = json.loads((root / "wsta176" / runner.COMMAND_JSON_NAME).read_text(encoding="utf-8"))
            script = (root / "wsta176" / runner.COMMAND_SH_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(calls, ["wsta174", "wsta175"])
        self.assertTrue(result["checks"]["fresh_handoff_valid"])
        self.assertTrue(result["checks"]["source_gate_valid"])
        self.assertTrue(result["checks"]["execution_command_valid"])
        self.assertFalse(result["safety"]["live_command_executed"])
        self.assertEqual(payload["state"], "READY_TO_RUN_NOT_EXECUTED")
        self.assertFalse(payload["executed"])
        self.assertIn("workspace/public/src/scripts/server-distro/run_wsta175_seccomp_handoff_execute_gate.py", payload["command"])
        for flag in payload["required_ack_flags"]:
            self.assertIn(flag, payload["command"])
            self.assertIn(flag, script)
        self.assertNotIn("WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD", script)

    def test_gate_blocks_before_nested_runs(self) -> None:
        def fail(*_args, **_kwargs):
            raise AssertionError("nested runner should not run")

        old = self.swap_nested(fail, fail)
        try:
            with self.private_tmp() as tmp:
                root = Path(tmp)
                command_json, command_sh = self.write_wsta168_command(root)
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.base_args(root, command_json, command_sh)
                ))
        finally:
            self.restore_nested(old)
        self.assertEqual(result["decision"], "wsta176-blocked-explicit-preflight-gate-required")

    def test_invalid_fresh_handoff_blocks_before_source_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            calls: list[str] = []

            def bad_wsta174(args):
                calls.append("wsta174")
                result = {
                    "decision": "blocked",
                    "checks": {"fresh_preflight_valid": False},
                    "safety": {
                        "handoff_generated": False,
                        "live_command_executed": False,
                        "seccomp_filter_loaded": False,
                        "seccomp_enforced": False,
                        "correct_wsta161_token_supplied": False,
                    },
                }
                self.write_json(args.run_dir / runner.wsta174.SUMMARY_NAME, result)
                return result

            def fail(*_args, **_kwargs):
                raise AssertionError("source gate should not run")

            old = self.swap_nested(bad_wsta174, fail)
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.gated_args(root, command_json, command_sh)
                ))
            finally:
                self.restore_nested(old)

        self.assertEqual(result["decision"], "wsta176-blocked-fresh-handoff-invalid")
        self.assertEqual(calls, ["wsta174"])

    def test_invalid_source_gate_blocks_command_generation(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            calls: list[str] = []
            fake_wsta174, fake_wsta175 = self.fake_pass_bundle(calls, command_json, command_sh)

            def bad_wsta175(args):
                result = fake_wsta175(args)
                result["decision"] = "blocked"
                return result

            old = self.swap_nested(fake_wsta174, bad_wsta175)
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.gated_args(root, command_json, command_sh)
                ))
            finally:
                self.restore_nested(old)

        self.assertEqual(result["decision"], "wsta176-blocked-source-gate-invalid")
        self.assertEqual(calls, ["wsta174", "wsta175"])
        self.assertFalse((root / "wsta176" / runner.COMMAND_JSON_NAME).exists())


if __name__ == "__main__":
    unittest.main()
