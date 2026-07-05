from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/server-distro/run_wsta171_seccomp_live_observation_execute_preflight.py"
)


class ServerDistroWsta171SeccompLiveObservationExecutePreflightTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta168_command(self, root: Path, *, correct_token: bool = False) -> tuple[Path, Path]:
        command = [
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
        ]
        payload = {
            "schema": "a90-wsta168-seccomp-live-observation-command-v1",
            "state": "READY_TO_RUN_NOT_EXECUTED",
            "command": command,
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
        script = "#!/bin/sh\nexec " + " ".join(command) + "\n"
        if correct_token:
            script += "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD\n"
        command_sh.write_text(script, encoding="utf-8")
        return command_json, command_sh

    def write_wsta169_proof(self, path: Path, command_json: Path, command_sh: Path) -> None:
        command_checks = {
            "command_json_present": True,
            "command_sh_present": True,
            "schema_ok": True,
            "ready_not_executed": True,
            "payload_not_executed": True,
            "command_targets_wsta167": True,
            "script_targets_wsta167": True,
            "all_ack_flags_present": True,
            "correct_token_absent": True,
            "expected_no_load": True,
            "expected_no_enforce": True,
        }
        self.write_json(path, {
            "decision": runner.wsta170.wsta169.PASS_DECISION,
            "wsta168_command_json": runner.rel(command_json),
            "wsta168_command_sh": runner.rel(command_sh),
            "checks": {
                "explicit_gate": True,
                "command_ready": True,
                "bridge_ready": True,
                "version_ok": True,
                "status_ok": True,
                "selftest_fail_zero": True,
            },
            "command_checks": command_checks,
            "safety": {
                "live_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        })

    def write_wsta170_source_gate(
        self,
        path: Path,
        readiness: Path,
        command_json: Path,
        command_sh: Path,
        *,
        decision: str = "wsta170-blocked-explicit-execution-gate-required",
    ) -> None:
        self.write_json(path, {
            "decision": decision,
            "gate_decision": "wsta170-blocked-explicit-execution-gate-required",
            "wsta169_readiness_json": runner.rel(readiness),
            "wsta168_command_json": runner.rel(command_json),
            "wsta168_command_sh": runner.rel(command_sh),
            "checks": {
                "explicit_execution_gate": False,
                "readiness_proof_valid": True,
                "command_ready": True,
            },
            "readiness_checks": {
                "decision_pass": True,
                "explicit_readiness_gate": True,
                "command_ready": True,
                "bridge_ready": True,
                "version_ok": True,
                "status_ok": True,
                "selftest_fail_zero": True,
                "command_json_matches": True,
                "command_sh_matches": True,
                "proof_command_checks_true": True,
                "proof_no_live_execution": True,
                "proof_no_seccomp_load": True,
                "proof_no_seccomp_enforce": True,
                "proof_no_correct_token": True,
            },
            "command_checks": {
                "command_json_present": True,
                "command_sh_present": True,
                "schema_ok": True,
                "ready_not_executed": True,
                "payload_not_executed": True,
                "command_targets_wsta167": True,
                "script_targets_wsta167": True,
                "all_ack_flags_present": True,
                "correct_token_absent": True,
                "expected_no_load": True,
                "expected_no_enforce": True,
                "command_is_string_list": True,
                "command_targets_wsta167_exact": True,
                "command_has_execute_gate": True,
                "command_has_allow_gate": True,
                "command_has_no_correct_token_ack": True,
                "command_has_no_load_ack": True,
                "command_has_cleanup_ack": True,
                "command_excludes_correct_token": True,
                "command_excludes_public_tunnel": True,
                "nested_run_dir_private": True,
            },
            "safety": {
                "device_action": False,
                "live_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        })

    def fixture_paths(self, root: Path) -> tuple[Path, Path, Path, Path]:
        command_json, command_sh = self.write_wsta168_command(root)
        readiness = root / "wsta169_result.json"
        self.write_wsta169_proof(readiness, command_json, command_sh)
        source_gate = root / "wsta170_result.json"
        self.write_wsta170_source_gate(source_gate, readiness, command_json, command_sh)
        return source_gate, readiness, command_json, command_sh

    def args(self, root: Path, source_gate: Path, readiness: Path, command_json: Path, command_sh: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta171"),
            "--wsta170-source-gate-json",
            str(source_gate),
            "--wsta169-readiness-json",
            str(readiness),
            "--wsta168-command-json",
            str(command_json),
            "--wsta168-command-sh",
            str(command_sh),
            "--emit-wsta170-execute-preflight",
        ]

    def test_preflight_emits_wsta170_execution_command_without_executing(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_gate, readiness, command_json, command_sh = self.fixture_paths(root)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.args(root, source_gate, readiness, command_json, command_sh)
            ))
            command_payload = json.loads(
                (root / "wsta171" / runner.COMMAND_JSON_NAME).read_text(encoding="utf-8")
            )
            command_script = (root / "wsta171" / runner.COMMAND_SH_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(command_payload["state"], "READY_TO_RUN_NOT_EXECUTED")
        self.assertFalse(command_payload["executed"])
        self.assertFalse(result["safety"]["live_command_executed"])
        self.assertIn(
            "workspace/public/src/scripts/server-distro/run_wsta170_seccomp_live_observation_execute.py",
            command_payload["command"],
        )
        for flag in command_payload["required_ack_flags"]:
            self.assertIn(flag, command_payload["command"])
            self.assertIn(flag, command_script)
        self.assertNotIn("WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD", command_script)
        self.assertTrue(result["checks"]["source_gate_valid"])
        self.assertTrue(result["checks"]["readiness_valid"])
        self.assertTrue(result["checks"]["wsta168_command_valid"])
        self.assertTrue(result["checks"]["execution_command_valid"])

    def test_gate_or_nonprivate_input_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_gate, readiness, command_json, command_sh = self.fixture_paths(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta171"),
                "--wsta170-source-gate-json",
                str(source_gate),
                "--wsta169-readiness-json",
                str(readiness),
                "--wsta168-command-json",
                str(command_json),
                "--wsta168-command-sh",
                str(command_sh),
            ]))
        self.assertEqual(result["decision"], "wsta171-blocked-explicit-preflight-gate-required")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            source_gate, readiness, command_json, command_sh = self.fixture_paths(Path(outside))
            result = runner.run(runner.build_arg_parser().parse_args(
                self.args(root, source_gate, readiness, command_json, command_sh)
            ))
        self.assertEqual(result["decision"], "wsta171-blocked-source-gate-nonprivate")

    def test_bad_source_gate_or_command_artifact_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_gate, readiness, command_json, command_sh = self.fixture_paths(root)
            self.write_wsta170_source_gate(
                source_gate,
                readiness,
                command_json,
                command_sh,
                decision="wsta170-seccomp-live-observation-execute-pass",
            )
            result = runner.run(runner.build_arg_parser().parse_args(
                self.args(root, source_gate, readiness, command_json, command_sh)
            ))
        self.assertEqual(result["decision"], "wsta171-blocked-preflight-invalid")
        self.assertFalse(result["source_gate_checks"]["decision_is_explicit_gate_block"])

        with self.private_tmp() as tmp:
            root = Path(tmp)
            command_json, command_sh = self.write_wsta168_command(root, correct_token=True)
            readiness = root / "wsta169_result.json"
            self.write_wsta169_proof(readiness, command_json, command_sh)
            source_gate = root / "wsta170_result.json"
            self.write_wsta170_source_gate(source_gate, readiness, command_json, command_sh)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.args(root, source_gate, readiness, command_json, command_sh)
            ))
        self.assertEqual(result["decision"], "wsta171-blocked-preflight-invalid")
        self.assertFalse(result["wsta168_command_checks"]["correct_token_absent"])


if __name__ == "__main__":
    unittest.main()
