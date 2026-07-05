from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta178_seccomp_one_shot_execute_preflight.py")


class ServerDistroWsta178SeccompOneShotExecutePreflightTests(unittest.TestCase):
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

    def write_wsta177_source_gate(
        self,
        root: Path,
        command_json: Path,
        command_sh: Path,
        *,
        decision: str = "wsta177-blocked-explicit-execution-gate-required",
        path_mismatch: bool = False,
    ) -> Path:
        packet_json = root / "wsta176-handoff-execute-preflight" / runner.wsta177.wsta176.COMMAND_JSON_NAME
        packet_sh = root / "wsta176-handoff-execute-preflight" / runner.wsta177.wsta176.COMMAND_SH_NAME
        self.write_json(packet_json, {"schema": "a90-wsta176-wsta175-execute-command-v1"})
        packet_sh.parent.mkdir(parents=True, exist_ok=True)
        packet_sh.write_text("#!/bin/sh\nexec true\n", encoding="utf-8")
        result = {
            "decision": decision,
            "gate_decision": decision,
            "wsta168_command_json": runner.rel(root / "other.json") if path_mismatch else runner.rel(command_json),
            "wsta168_command_sh": runner.rel(command_sh),
            "checks": {
                "explicit_prepare_gate": True,
                "explicit_execution_gate": False,
                "fresh_preflight_valid": True,
                "execution_command_valid": True,
            },
            "fresh_preflight": {
                "command_json": runner.rel(packet_json),
                "command_script": runner.rel(packet_sh),
                "decision": runner.wsta177.wsta176.PASS_DECISION,
            },
            "fresh_preflight_checks": {
                "decision_pass": True,
                "gate_ok": True,
                "fresh_handoff_valid": True,
                "source_gate_valid": True,
                "execution_command_valid": True,
                "wsta168_json_path_matches": True,
                "wsta168_sh_path_matches": True,
                "command_ready": True,
                "command_not_executed": True,
                "command_json_present": True,
                "command_script_present": True,
                "no_live_execution": True,
                "no_wsta175_execution": True,
                "no_wsta170_execution": True,
                "no_seccomp_load": True,
                "no_seccomp_enforce": True,
                "no_correct_token": True,
            },
            "execution_command_checks": {
                "schema_ok": True,
                "ready_not_executed": True,
                "not_executed": True,
                "command_is_string_list": True,
                "command_targets_wsta175": True,
                "all_ack_flags_present": True,
                "correct_token_literal_absent": True,
                "no_external_network_inputs": True,
                "expected_wsta175_pass": True,
                "expected_wsta170_pass": True,
                "expected_wsta167_pass": True,
                "expected_no_seccomp_load": True,
                "expected_no_seccomp_enforce": True,
                "expected_no_correct_token": True,
            },
            "safety": {
                "device_action_requested": False,
                "fresh_preflight_generated": True,
                "live_command_executed": False,
                "wsta175_execute_command_executed": False,
                "wsta170_execute_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        }
        source_gate = root / "wsta177_result.json"
        self.write_json(source_gate, result)
        return source_gate

    def base_args(self, root: Path, source_gate: Path, command_json: Path, command_sh: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta178"),
            "--wsta177-source-gate-json",
            str(source_gate),
            "--wsta168-command-json",
            str(command_json),
            "--wsta168-command-sh",
            str(command_sh),
        ]

    def preflight_args(self, root: Path, source_gate: Path, command_json: Path, command_sh: Path) -> list[str]:
        return self.base_args(root, source_gate, command_json, command_sh) + [
            "--emit-wsta177-execute-preflight"
        ]

    def test_preflight_emits_wsta177_execution_command_without_executing(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            source_gate = self.write_wsta177_source_gate(root, command_json, command_sh)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.preflight_args(root, source_gate, command_json, command_sh)
            ))
            payload = json.loads((root / "wsta178" / runner.COMMAND_JSON_NAME).read_text(encoding="utf-8"))
            script = (root / "wsta178" / runner.COMMAND_SH_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["source_gate_valid"])
        self.assertTrue(result["checks"]["execution_command_valid"])
        self.assertTrue(result["safety"]["wsta177_execute_command_generated"])
        self.assertFalse(result["safety"]["live_command_executed"])
        self.assertEqual(payload["schema"], "a90-wsta178-wsta177-execute-command-v1")
        self.assertFalse(payload["executed"])
        self.assertIn("workspace/public/src/scripts/server-distro/run_wsta177_seccomp_one_shot_execute_gate.py", payload["command"])
        self.assertIn("--execute-wsta177-one-shot", payload["command"])
        self.assertIn("--prepare-wsta177-one-shot", payload["command"])
        self.assertIn("--allow-wsta175-command-execution", payload["command"])
        self.assertIn("--execute-wsta177-one-shot", script)
        self.assertNotIn("WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD", script)

    def test_missing_preflight_gate_blocks_before_loading_source_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            source_gate = self.write_wsta177_source_gate(root, command_json, command_sh)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.base_args(root, source_gate, command_json, command_sh)
            ))

        self.assertEqual(result["decision"], "wsta178-blocked-explicit-preflight-gate-required")
        self.assertFalse((root / "wsta178" / runner.COMMAND_JSON_NAME).exists())

    def test_source_gate_mismatch_blocks_command_generation(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            source_gate = self.write_wsta177_source_gate(root, command_json, command_sh, path_mismatch=True)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.preflight_args(root, source_gate, command_json, command_sh)
            ))

        self.assertEqual(result["decision"], "wsta178-blocked-source-gate-invalid")
        self.assertFalse(result["source_gate_checks"]["wsta168_json_path_matches"])
        self.assertFalse((root / "wsta178" / runner.COMMAND_JSON_NAME).exists())

    def test_source_gate_pass_decision_is_rejected(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root)
            source_gate = self.write_wsta177_source_gate(
                root,
                command_json,
                command_sh,
                decision=runner.wsta177.PASS_DECISION,
            )
            result = runner.run(runner.build_arg_parser().parse_args(
                self.preflight_args(root, source_gate, command_json, command_sh)
            ))

        self.assertEqual(result["decision"], "wsta178-blocked-source-gate-invalid")
        self.assertFalse(result["source_gate_checks"]["decision_is_explicit_gate_block"])


if __name__ == "__main__":
    unittest.main()
