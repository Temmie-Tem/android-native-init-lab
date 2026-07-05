from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta173_seccomp_expiring_execute_handoff.py")


class ServerDistroWsta173SeccompExpiringExecuteHandoffTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def command_payload(self, root: Path) -> tuple[Path, Path]:
        command = [
            "python3",
            "workspace/public/src/scripts/server-distro/run_wsta170_seccomp_live_observation_execute.py",
            "--run-id",
            "wsta171-seccomp-live-observation-execute",
            "--run-dir",
            str(root / "wsta170-live-run"),
            "--wsta169-readiness-json",
            str(root / "wsta169-readiness" / runner.wsta169.SUMMARY_NAME),
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
        command_json = root / "wsta171-execute-preflight" / runner.wsta171.COMMAND_JSON_NAME
        command_sh = root / "wsta171-execute-preflight" / runner.wsta171.COMMAND_SH_NAME
        self.write_json(command_json, payload)
        command_sh.write_text("#!/bin/sh\nexec " + " ".join(command) + "\n", encoding="utf-8")
        return command_json, command_sh

    def write_bundle(self, root: Path, *, timestamp: str = "20260705T050000Z", command_executed: bool = False) -> Path:
        command_json, command_sh = self.command_payload(root)
        readiness_path = root / "wsta169-readiness" / runner.wsta169.SUMMARY_NAME
        source_path = root / "wsta170-source-gate" / runner.wsta170.SUMMARY_NAME
        preflight_path = root / "wsta171-execute-preflight" / runner.wsta171.SUMMARY_NAME
        self.write_json(readiness_path, {
            "decision": runner.wsta169.PASS_DECISION,
            "ended_utc": timestamp,
            "safety": {
                "live_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        })
        self.write_json(source_path, {
            "decision": "wsta170-blocked-explicit-execution-gate-required",
            "ended_utc": timestamp,
            "safety": {
                "live_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        })
        self.write_json(preflight_path, {
            "decision": runner.wsta171.PASS_DECISION,
            "ended_utc": timestamp,
            "command": {
                "state": "READY_TO_RUN_NOT_EXECUTED",
                "executed": command_executed,
            },
            "safety": {
                "live_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        })
        proof = root / runner.wsta172.SUMMARY_NAME
        self.write_json(proof, {
            "decision": runner.wsta172.PASS_DECISION,
            "gate_decision": "ok",
            "ended_utc": timestamp,
            "checks": {
                "fresh_readiness_valid": True,
                "source_gate_valid": True,
                "execute_preflight_valid": True,
            },
            "safety": {
                "live_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
                "wsta170_execute_command_generated": True,
                "wsta170_execute_command_executed": False,
            },
            "fresh_readiness": {"result_json": runner.rel(readiness_path)},
            "source_gate": {"result_json": runner.rel(source_path)},
            "execute_preflight": {
                "result_json": runner.rel(preflight_path),
                "command_json": runner.rel(command_json),
                "command_script": runner.rel(command_sh),
            },
        })
        return proof

    def args(self, root: Path, proof: Path, *, max_age: int = 900) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta173"),
            "--wsta172-proof-json",
            str(proof),
            "--max-age-sec",
            str(max_age),
            "--emit-expiring-handoff",
        ]

    def set_now(self, value: str):
        old = runner.now_utc
        fixed = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
        runner.now_utc = lambda: fixed
        return old

    def restore_now(self, old) -> None:
        runner.now_utc = old

    def test_handoff_passes_when_command_is_fresh_and_unexecuted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            proof = self.write_bundle(root)
            old = self.set_now("20260705T050300Z")
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, proof)))
            finally:
                self.restore_now(old)
            handoff = json.loads((root / "wsta173" / runner.HANDOFF_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["freshness_valid"])
        self.assertTrue(result["checks"]["command_valid"])
        self.assertTrue(result["safety"]["handoff_generated"])
        self.assertFalse(handoff["executed"])
        self.assertEqual(handoff["state"], "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY")
        self.assertEqual(handoff["freshness"]["age_sec"], 180)

    def test_gate_and_nonprivate_paths_block(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            proof = self.write_bundle(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta173"),
                "--wsta172-proof-json",
                str(proof),
            ]))
        self.assertEqual(result["decision"], "wsta173-blocked-explicit-handoff-gate-required")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            proof = self.write_bundle(Path(outside))
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, proof)))
        self.assertEqual(result["decision"], "wsta173-blocked-wsta172-proof-nonprivate")

    def test_stale_proof_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            proof = self.write_bundle(root)
            old = self.set_now("20260705T053000Z")
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, proof, max_age=900)))
            finally:
                self.restore_now(old)

        self.assertEqual(result["decision"], "wsta173-blocked-handoff-invalid")
        self.assertFalse(result["freshness_checks"]["within_max_age"])

    def test_executed_preflight_command_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            proof = self.write_bundle(root, command_executed=True)
            old = self.set_now("20260705T050300Z")
            try:
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, proof)))
            finally:
                self.restore_now(old)

        self.assertEqual(result["decision"], "wsta173-blocked-handoff-invalid")
        self.assertFalse(result["nested_checks"]["preflight_command_not_executed"])


if __name__ == "__main__":
    unittest.main()
