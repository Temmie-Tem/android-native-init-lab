from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta179_seccomp_one_shot_result_audit.py")


class ServerDistroWsta179SeccompOneShotResultAuditTests(unittest.TestCase):
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

    def write_wsta178_command(self, root: Path, *, bad_script: bool = False) -> tuple[Path, Path, Path]:
        command_json, command_sh = self.write_wsta168_command(root)
        command = runner.wsta178.execution_command(
            root / "wsta178",
            command_json,
            command_sh,
            20.0,
            1800.0,
            900,
        )
        payload = runner.wsta178.command_payload(command)
        packet_json = root / "wsta178" / runner.wsta178.COMMAND_JSON_NAME
        packet_sh = root / "wsta178" / runner.wsta178.COMMAND_SH_NAME
        self.write_json(packet_json, payload)
        script = "#!/bin/sh\nset -eu\nexec " + " ".join(command) + "\n"
        if bad_script:
            script += "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD\n"
        packet_sh.parent.mkdir(parents=True, exist_ok=True)
        packet_sh.write_text(script, encoding="utf-8")
        result_path = runner.inferred_wsta177_result_path(payload)
        assert result_path is not None
        return packet_json, packet_sh, result_path

    def write_wsta177_pass_result(self, result_path: Path, *, bad_nested: bool = False) -> None:
        wsta167_decision = "bad" if bad_nested else runner.wsta177.wsta175.wsta170.wsta167.PASS_DECISION
        wsta170_result = {
            "decision": runner.wsta177.wsta175.wsta170.PASS_DECISION,
            "nested_result": {"decision": wsta167_decision},
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
        }
        wsta175_result = {
            "decision": runner.wsta177.wsta175.PASS_DECISION,
            "checks": {
                "handoff_valid": True,
                "handoff_fresh": True,
                "command_artifacts_valid": True,
                "execution_returncode_ok": True,
                "wsta170_result_present": True,
                "wsta170_result_valid": True,
            },
            "safety": {
                "wsta170_execute_command_executed": True,
                "live_command_executed": True,
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
            "wsta170_result": wsta170_result,
        }
        result = {
            "decision": runner.wsta177.PASS_DECISION,
            "gate_decision": "ok",
            "run_dir": runner.rel(result_path.parent),
            "checks": {
                "explicit_prepare_gate": True,
                "explicit_execution_gate": True,
                "fresh_preflight_valid": True,
                "execution_command_valid": True,
                "execution_returncode_ok": True,
                "wsta175_result_present": True,
                "wsta175_result_valid": True,
            },
            "wsta175_result": wsta175_result,
            "wsta175_checks": {
                "decision_pass": True,
                "handoff_valid": True,
                "handoff_fresh": True,
                "command_artifacts_valid": True,
                "execution_returncode_ok": True,
                "wsta170_result_present": True,
                "wsta170_result_valid": True,
                "no_seccomp_load": True,
                "no_seccomp_enforce": True,
                "no_correct_token": True,
                "no_flash": True,
                "no_reboot": True,
                "no_wifi": True,
                "no_dhcp": True,
                "no_public_tunnel": True,
                "no_packet_filter_mutation": True,
            },
            "safety": {
                "live_command_executed": True,
                "wsta175_execute_command_executed": True,
                "wsta170_execute_command_executed": True,
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
        }
        self.write_json(result_path, result)

    def args(self, root: Path, packet_json: Path, packet_sh: Path, *extra: str) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta179"),
            "--wsta178-command-json",
            str(packet_json),
            "--wsta178-command-sh",
            str(packet_sh),
            "--audit-wsta177-result",
            *extra,
        ]

    def test_missing_result_blocks_after_command_packet_validation(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, _result_path = self.write_wsta178_command(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, packet_json, packet_sh)))

        self.assertEqual(result["decision"], "wsta179-blocked-wsta177-result-missing")
        self.assertTrue(result["checks"]["command_packet_valid"])
        self.assertFalse(result["checks"]["wsta177_result_present"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_valid_wsta177_result_passes_audit(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, result_path = self.write_wsta178_command(root)
            self.write_wsta177_pass_result(result_path)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, packet_json, packet_sh)))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["command_packet_valid"])
        self.assertTrue(result["checks"]["wsta177_result_valid"])
        self.assertTrue(result["wsta177_checks"]["wsta167_decision_pass"])

    def test_bad_command_packet_blocks_before_result(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, result_path = self.write_wsta178_command(root, bad_script=True)
            self.write_wsta177_pass_result(result_path)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, packet_json, packet_sh)))

        self.assertEqual(result["decision"], "wsta179-blocked-command-packet-invalid")
        self.assertFalse(result["command_checks"]["correct_token_literal_absent"])

    def test_bad_nested_result_blocks_audit(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, result_path = self.write_wsta178_command(root)
            self.write_wsta177_pass_result(result_path, bad_nested=True)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, packet_json, packet_sh)))

        self.assertEqual(result["decision"], "wsta179-blocked-wsta177-result-invalid")
        self.assertFalse(result["wsta177_checks"]["wsta167_decision_pass"])


if __name__ == "__main__":
    unittest.main()
