from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta181_seccomp_handoff_execute_audit_gate.py")


class ServerDistroWsta181SeccompHandoffExecuteAuditGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta168_command(self, root: Path) -> tuple[Path, Path]:
        command_json = root / "wsta168_live_command.json"
        command_sh = root / "wsta168_live_command.sh"
        self.write_json(command_json, {
            "schema": "a90-wsta168-seccomp-live-observation-command-v1",
            "state": "READY_TO_RUN_NOT_EXECUTED",
            "command": ["python3", "workspace/public/src/scripts/server-distro/run_wsta167_seccomp_live_observation.py"],
            "required_ack_flags": [],
            "expected_outcome": {},
            "executed": False,
            "secret_values_logged": 0,
        })
        command_sh.write_text("#!/bin/sh\nexec true\n", encoding="utf-8")
        return command_json, command_sh

    def write_wsta180_bundle(self, root: Path, *, existing_result: bool = False) -> tuple[Path, Path, Path]:
        command_json, command_sh = self.write_wsta168_command(root)
        execute_command = runner.wsta180.wsta179.wsta178.execution_command(
            root / "wsta178-preflight",
            command_json,
            command_sh,
            20.0,
            1800.0,
            900,
        )
        packet = runner.wsta180.wsta179.wsta178.command_payload(execute_command)
        packet_json = root / "wsta178-preflight" / runner.wsta180.wsta179.wsta178.COMMAND_JSON_NAME
        packet_sh = root / "wsta178-preflight" / runner.wsta180.wsta179.wsta178.COMMAND_SH_NAME
        self.write_json(packet_json, packet)
        packet_sh.write_text("#!/bin/sh\nset -eu\nexec " + " ".join(execute_command) + "\n", encoding="utf-8")
        result_path = runner.wsta180.wsta179.inferred_wsta177_result_path(packet)
        assert result_path is not None
        if existing_result:
            self.write_json(result_path, {"decision": "stale-existing-result"})
        audit_command = runner.wsta180.audit_command(root / "wsta180", packet_json, packet_sh, result_path)
        bundle = runner.wsta180.bundle_payload(
            command_packet=packet,
            command_json=packet_json,
            command_sh=packet_sh,
            wsta177_result_json=result_path,
            wsta179_result_json=root / "wsta180" / "pre-run-wsta179-result-audit" / runner.wsta179.SUMMARY_NAME,
            post_run_audit_command=audit_command,
        )
        bundle_json = root / "wsta180" / runner.wsta180.BUNDLE_JSON_NAME
        bundle_sh = root / "wsta180" / runner.wsta180.BUNDLE_SH_NAME
        self.write_json(bundle_json, bundle)
        bundle_sh.write_text(
            "#!/bin/sh\nset -eu\nprintf '%s\\n' EXECUTE\nexec "
            + " ".join(audit_command)
            + "\n",
            encoding="utf-8",
        )
        return bundle_json, bundle_sh, result_path

    def base_args(self, root: Path, bundle_json: Path, bundle_sh: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta181"),
            "--wsta180-bundle-json",
            str(bundle_json),
            "--wsta180-bundle-sh",
            str(bundle_sh),
        ]

    def execute_args(self, root: Path, bundle_json: Path, bundle_sh: Path) -> list[str]:
        return self.base_args(root, bundle_json, bundle_sh) + [
            "--execute-wsta181-handoff",
            "--allow-wsta178-command-execution",
            "--ack-handoff-ready",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-post-run-audit-required",
            "--ack-cleanup-required",
        ]

    def write_wsta179_pass_result(self, result_path: Path, wsta177_result_path: Path) -> None:
        self.write_json(result_path, {
            "decision": runner.wsta179.PASS_DECISION,
            "wsta177_result_json": runner.rel(wsta177_result_path),
            "checks": {
                "command_packet_valid": True,
                "wsta177_result_present": True,
                "wsta177_result_valid": True,
            },
            "wsta177_checks": {
                "source_wsta175_executed": True,
                "source_wsta170_executed": True,
                "wsta175_decision_pass": True,
                "wsta170_decision_pass": True,
                "wsta167_decision_pass": True,
                "source_no_seccomp_load": True,
                "source_no_seccomp_enforce": True,
                "source_no_correct_token": True,
                "source_no_flash": True,
                "source_no_reboot": True,
                "source_no_wifi": True,
                "source_no_dhcp": True,
                "source_no_public_tunnel": True,
                "source_no_packet_filter_mutation": True,
            },
            "safety": {
                "audit_only": True,
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

    def test_source_gate_validates_bundle_but_does_not_execute(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            bundle_json, bundle_sh, _result_path = self.write_wsta180_bundle(root)
            old_exec = runner.run_generated_command
            runner.run_generated_command = lambda command, *, timeout: (_ for _ in ()).throw(
                AssertionError(f"must not execute: {command} {timeout}")
            )
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.base_args(root, bundle_json, bundle_sh)
                ))
            finally:
                runner.run_generated_command = old_exec

        self.assertEqual(result["decision"], "wsta181-blocked-explicit-execution-gate-required")
        self.assertTrue(result["checks"]["handoff_bundle_valid"])
        self.assertTrue(result["checks"]["execution_packet_valid"])
        self.assertTrue(result["checks"]["post_run_audit_command_valid"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_explicit_gate_executes_packet_then_audit_and_validates_result(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            bundle_json, bundle_sh, wsta177_result = self.write_wsta180_bundle(root)
            calls: list[list[str]] = []

            def fake_executor(command: list[str], *, timeout: float) -> dict:
                del timeout
                calls.append(command)
                if len(calls) == 1:
                    self.write_json(wsta177_result, {"decision": runner.wsta180.wsta179.wsta177.PASS_DECISION})
                else:
                    audit_run_dir = runner.command_run_dir(command)
                    self.assertIsNotNone(audit_run_dir)
                    assert audit_run_dir is not None
                    self.write_wsta179_pass_result(audit_run_dir / runner.wsta179.SUMMARY_NAME, wsta177_result)
                return {"command": command, "returncode": 0, "stdout": "ok\n", "stderr": ""}

            old_exec = runner.run_generated_command
            runner.run_generated_command = fake_executor
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.execute_args(root, bundle_json, bundle_sh)
                ))
            finally:
                runner.run_generated_command = old_exec

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(len(calls), 2)
        self.assertTrue(result["checks"]["post_run_audit_result_valid"])
        self.assertTrue(result["safety"]["wsta178_execute_command_executed"])
        self.assertTrue(result["safety"]["wsta175_execute_command_executed"])
        self.assertTrue(result["safety"]["wsta170_execute_command_executed"])
        self.assertTrue(result["safety"]["post_run_audit_executed"])
        self.assertTrue(result["post_run_deep_audit_checks"]["wsta167_decision_pass"])

    def test_existing_result_blocks_source_gate_as_stale(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            bundle_json, bundle_sh, _result_path = self.write_wsta180_bundle(root, existing_result=True)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.execute_args(root, bundle_json, bundle_sh)
            ))

        self.assertEqual(result["decision"], "wsta181-blocked-handoff-bundle-invalid")
        self.assertFalse(result["handoff_bundle_checks"]["expected_result_missing"])

    def test_bad_post_run_audit_command_blocks_before_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            bundle_json, bundle_sh, _result_path = self.write_wsta180_bundle(root)
            bundle = json.loads(bundle_json.read_text(encoding="utf-8"))
            bundle["post_run_audit"]["command"].append("WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD")
            self.write_json(bundle_json, bundle)
            old_exec = runner.run_generated_command
            runner.run_generated_command = lambda command, *, timeout: (_ for _ in ()).throw(
                AssertionError(f"must not execute: {command} {timeout}")
            )
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.execute_args(root, bundle_json, bundle_sh)
                ))
            finally:
                runner.run_generated_command = old_exec

        self.assertEqual(result["decision"], "wsta181-blocked-post-run-audit-command-invalid")
        self.assertFalse(result["post_run_audit_command_checks"]["correct_token_literal_absent"])


if __name__ == "__main__":
    unittest.main()
