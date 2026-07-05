from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta174_seccomp_fresh_expiring_handoff.py")


class ServerDistroWsta174SeccompFreshExpiringHandoffTests(unittest.TestCase):
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
            str(root / "wsta174"),
            "--wsta168-command-json",
            str(command_json),
            "--wsta168-command-sh",
            str(command_sh),
        ]

    def gated_args(self, root: Path, command_json: Path, command_sh: Path) -> list[str]:
        return self.base_args(root, command_json, command_sh) + ["--emit-fresh-expiring-handoff"]

    def fake_pass_bundle(self, calls: list[str], command_json: Path, command_sh: Path):
        def fake_wsta172(args):
            calls.append("wsta172")
            result = {
                "decision": runner.wsta172.PASS_DECISION,
                "gate_decision": "ok",
                "wsta168_command_json": runner.rel(command_json),
                "wsta168_command_sh": runner.rel(command_sh),
                "checks": {
                    "fresh_readiness_valid": True,
                    "source_gate_valid": True,
                    "execute_preflight_valid": True,
                },
                "execute_preflight": {
                    "command_json": runner.rel(args.run_dir / "wsta171-execute-preflight" / "command.json"),
                    "command_script": runner.rel(args.run_dir / "wsta171-execute-preflight" / "command.sh"),
                },
                "safety": {
                    "wsta170_execute_command_generated": True,
                    "wsta170_execute_command_executed": False,
                    "live_command_executed": False,
                    "seccomp_filter_loaded": False,
                    "seccomp_enforced": False,
                    "correct_wsta161_token_supplied": False,
                },
            }
            self.write_json(args.run_dir / runner.wsta172.SUMMARY_NAME, result)
            return result

        def fake_wsta173(args):
            calls.append("wsta173")
            self.assertEqual(args.wsta172_proof_json.name, runner.wsta172.SUMMARY_NAME)
            self.assertTrue(args.emit_expiring_handoff)
            result = {
                "decision": runner.wsta173.PASS_DECISION,
                "gate_decision": "ok",
                "wsta172_proof_json": runner.rel(args.wsta172_proof_json),
                "checks": {
                    "freshness_valid": True,
                    "wsta172_valid": True,
                    "nested_valid": True,
                    "command_valid": True,
                },
                "handoff": {
                    "handoff_json": runner.rel(args.run_dir / runner.wsta173.HANDOFF_NAME),
                    "state": "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
                    "expires_utc": "20260705T060000Z",
                    "command_json": runner.rel(args.wsta172_proof_json.parent / "command.json"),
                    "command_script": runner.rel(args.wsta172_proof_json.parent / "command.sh"),
                    "executed": False,
                },
                "safety": {
                    "handoff_generated": True,
                    "live_command_executed": False,
                    "seccomp_filter_loaded": False,
                    "seccomp_enforced": False,
                    "correct_wsta161_token_supplied": False,
                },
            }
            self.write_json(args.run_dir / runner.wsta173.SUMMARY_NAME, result)
            return result

        return fake_wsta172, fake_wsta173

    def swap_nested(self, fake_wsta172, fake_wsta173):
        old = (runner.wsta172.run, runner.wsta173.run)
        runner.wsta172.run = fake_wsta172
        runner.wsta173.run = fake_wsta173
        return old

    def restore_nested(self, old) -> None:
        runner.wsta172.run, runner.wsta173.run = old

    def test_one_shot_bundle_generates_fresh_expiring_handoff(self) -> None:
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

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(calls, ["wsta172", "wsta173"])
        self.assertTrue(result["checks"]["fresh_preflight_valid"])
        self.assertTrue(result["checks"]["expiring_handoff_valid"])
        self.assertTrue(result["safety"]["wsta170_execute_command_generated"])
        self.assertTrue(result["safety"]["handoff_generated"])
        self.assertFalse(result["safety"]["live_command_executed"])

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
        self.assertEqual(result["decision"], "wsta174-blocked-explicit-bundle-gate-required")

    def test_invalid_fresh_preflight_blocks_before_handoff(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            calls: list[str] = []

            def bad_wsta172(args):
                calls.append("wsta172")
                result = {
                    "decision": "blocked",
                    "gate_decision": "blocked",
                    "wsta168_command_json": runner.rel(command_json),
                    "wsta168_command_sh": runner.rel(command_sh),
                    "checks": {"fresh_readiness_valid": False},
                    "safety": {
                        "wsta170_execute_command_generated": False,
                        "wsta170_execute_command_executed": False,
                        "live_command_executed": False,
                        "seccomp_filter_loaded": False,
                        "seccomp_enforced": False,
                        "correct_wsta161_token_supplied": False,
                    },
                }
                self.write_json(args.run_dir / runner.wsta172.SUMMARY_NAME, result)
                return result

            def fail(*_args, **_kwargs):
                raise AssertionError("handoff runner should not run")

            old = self.swap_nested(bad_wsta172, fail)
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.gated_args(root, command_json, command_sh)
                ))
            finally:
                self.restore_nested(old)

        self.assertEqual(result["decision"], "wsta174-blocked-fresh-preflight-invalid")
        self.assertEqual(calls, ["wsta172"])

    def test_invalid_expiring_handoff_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            calls: list[str] = []
            fake_wsta172, fake_wsta173 = self.fake_pass_bundle(calls, command_json, command_sh)

            def bad_wsta173(args):
                result = fake_wsta173(args)
                result["decision"] = "blocked"
                return result

            old = self.swap_nested(fake_wsta172, bad_wsta173)
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.gated_args(root, command_json, command_sh)
                ))
            finally:
                self.restore_nested(old)

        self.assertEqual(result["decision"], "wsta174-blocked-expiring-handoff-invalid")
        self.assertEqual(calls, ["wsta172", "wsta173"])


if __name__ == "__main__":
    unittest.main()
