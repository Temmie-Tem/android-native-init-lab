from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta190_wsta189_execute_gate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta190_wsta189_execute_gate.py")


class ServerDistroWsta190Wsta189ExecuteGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_packet_and_status(self, root: Path, *, status_state: str = "READY_TO_RUN_NO_LOAD_DEFAULT_OFF") -> dict[str, Path]:
        command_json = root / "wsta168_live_command.json"
        command_sh = root / "wsta168_live_command.sh"
        self.write_json(command_json, {
            "schema": "a90-wsta168-seccomp-live-observation-command-v1",
            "state": "READY_TO_RUN_NOT_EXECUTED",
            "command": [
                "python3",
                "workspace/public/src/scripts/server-distro/run_wsta167_seccomp_live_observation.py",
                "--run-dir",
                str(root / "wsta167-live-run"),
            ],
            "required_ack_flags": [],
            "expected_outcome": {},
            "executed": False,
            "secret_values_logged": 0,
        })
        command_sh.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        packet_dir = root / "packet"
        packet_sh = packet_dir / runner.wsta189.wsta188.PACKET_SH_NAME
        packet_sh.parent.mkdir(parents=True, exist_ok=True)
        packet_sh.write_text("#!/bin/sh\nprintf '{}\\n'\n", encoding="utf-8")
        packet_sh.chmod(0o700)
        packet = {
            "schema": "a90-wsta188-wsta187-no-load-operator-packet-v1",
            "state": "READY_OPERATOR_PACKET_NO_LOAD_DEFAULT_OFF",
            "ready_for_no_load_live": True,
            "default_off": True,
            "source_wsta187_result": runner.rel(root / "source" / "wsta185_result.json"),
            "source_wsta187_run_dir": runner.rel(root / "source"),
            "source_wsta187_decision": "wsta187-blocked-explicit-execution-gate-required",
            "live_command_template": runner.wsta189.wsta188.live_command_template(command_json, command_sh),
            "live_command_script": runner.rel(packet_sh),
            "operator_acknowledgements_required": runner.wsta189.wsta188.ACK_FLAGS,
            "operator_preflight_checks": [
                "run-wsta188-immediately-before-attended-live-observation",
                "confirm-WSTA187-source-gate-valid",
                "confirm-final-selftest-fail-zero-after-live-run",
            ],
            "abort_conditions": [
                "source-gate-not-pass",
                "bridge-or-device-health-unclear",
                "operator-not-present",
                "unexpected-seccomp-load-request",
                "unexpected-correct-token-request",
            ],
            "cleanup_expectations": [
                "WSTA167 work image restored to clean hash",
                "no public tunnel to retire",
                "no packet filter state to restore",
            ],
            "safety_boundary": {
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
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
            "json_path": runner.rel(packet_dir / runner.wsta189.wsta188.PACKET_JSON_NAME),
            "markdown_path": runner.rel(packet_dir / runner.wsta189.wsta188.PACKET_MD_NAME),
        }
        packet_payload = {
            "scope": "WSTA188 host-only WSTA187 no-load live operator packet",
            "decision": runner.wsta189.wsta188.PASS_DECISION,
            "operator_packet": packet,
            "checks": {"operator_packet_valid": True, "wsta187_source_gate_valid": True},
            "safety": {"live_command_executed": False, "wsta187_live_command_executed": False},
        }
        packet_path = packet_dir / runner.wsta189.wsta188.PACKET_JSON_NAME
        self.write_json(packet_path, packet_payload)
        status = {
            "state": status_state,
            "ready_for_no_load_live": status_state == "READY_TO_RUN_NO_LOAD_DEFAULT_OFF",
            "wsta188_operator_packet": runner.rel(packet_path),
            "wsta188_recheck_result": runner.rel(root / "status" / "wsta188-recheck" / runner.wsta189.wsta188.SUMMARY_NAME),
            "wsta188_recheck_decision": runner.wsta189.wsta188.PASS_DECISION,
            "wsta188_recheck_source_gate_valid": True,
            "packet_match": True,
            "template_match": True,
            "operator_acknowledgements_required": runner.wsta189.wsta188.ACK_FLAGS,
            "live_command_script": runner.rel(packet_sh),
            "source_wsta187_decision": "wsta187-blocked-explicit-execution-gate-required",
            "fresh_source_wsta187_decision": "wsta187-blocked-explicit-execution-gate-required",
            "recommended_next_action": "operator-may-run-wsta188-private-shell-wrapper-for-no-load-live",
            "default_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        status_payload = {
            "scope": "WSTA189 host-only WSTA188 operator packet status",
            "decision": runner.wsta189.PASS_DECISION,
            "operator_packet_status": status,
            "checks": {"operator_packet_status_valid": True},
            "safety": {"live_command_executed": False, "wsta187_live_command_executed": False},
        }
        status_path = root / "status" / runner.wsta189.STATUS_JSON_NAME
        self.write_json(status_path, status_payload)
        return {"packet": packet_path, "status": status_path, "script": packet_sh}

    def wsta187_pass_execution(self) -> dict:
        payload = {
            "decision": runner.wsta189.wsta188.wsta187.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/example-wsta187-live",
            "checks": {"wsta185_execution_valid": True},
            "safety": {
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
        }
        return {
            "returncode": 0,
            "stdout_json": payload,
            "stderr": "",
        }

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner, "run_shell_wrapper", side_effect=AssertionError("unexpected live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta189-operator-packet-status-json",
                    str(root / "missing" / runner.wsta189.STATUS_JSON_NAME),
                ]))

        self.assertEqual(result["decision"], "wsta190-blocked-status-missing")
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "packet_filter_mutation",
            "userdata_touch",
            "switch_root",
        ):
            self.assertFalse(result["safety"][key])

    def test_ready_status_preflight_writes_execute_gate_without_live(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.write_packet_and_status(root)
            with mock.patch.object(runner, "run_shell_wrapper", side_effect=AssertionError("unexpected live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta189-operator-packet-status-json",
                    str(artifacts["status"]),
                ]))
            saved = json.loads((root / "gate" / runner.SUMMARY_NAME).read_text(encoding="utf-8"))
            markdown = (root / "gate" / runner.SUMMARY_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PREFLIGHT_DECISION)
        self.assertEqual(saved["decision"], runner.PREFLIGHT_DECISION)
        gate = result["execute_gate"]
        self.assertEqual(gate["state"], "READY_FOR_EXPLICIT_WSTA187_NO_LOAD_LIVE")
        self.assertEqual(gate["wsta189_operator_packet_status"], runner.rel(artifacts["status"]))
        self.assertEqual(gate["wsta188_operator_packet"], runner.rel(artifacts["packet"]))
        self.assertEqual(gate["wsta188_live_command_script"], runner.rel(artifacts["script"]))
        self.assertIn("--ack-no-seccomp-load", gate["operator_acknowledgements_required"])
        self.assertIn("explicit-wsta187-no-load-gate-required", gate["execution_guardrails"])
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertIn("WSTA187 No-Load Execute Gate", markdown)

    def test_stale_status_blocks_before_live(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.write_packet_and_status(root, status_state="STALE_OR_NOT_READY")
            with mock.patch.object(runner, "run_shell_wrapper", side_effect=AssertionError("unexpected live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta189-operator-packet-status-json",
                    str(artifacts["status"]),
                ]))

        self.assertEqual(result["decision"], "wsta190-blocked-status-not-ready")
        self.assertEqual(result["gate_detail"]["state"], "STALE_OR_NOT_READY")

    def test_live_gate_blocks_without_full_ack_stack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.write_packet_and_status(root)
            with mock.patch.object(runner, "run_shell_wrapper", side_effect=AssertionError("unexpected live")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta189-operator-packet-status-json",
                    str(artifacts["status"]),
                    "--execute-wsta187-from-status",
                ]))

        self.assertEqual(result["decision"], "wsta190-blocked-wsta185-handoff-execution-allow-required")
        self.assertTrue(result["checks"]["live_execution_requested"])
        self.assertFalse(result["checks"]["explicit_live_gate"])

    def test_live_gate_delegates_to_wsta187_wrapper_only_after_full_ack_stack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.write_packet_and_status(root)
            with mock.patch.object(runner, "run_shell_wrapper", return_value=self.wsta187_pass_execution()) as delegated:
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta189-operator-packet-status-json",
                    str(artifacts["status"]),
                    "--execute-wsta187-from-status",
                    "--allow-wsta185-handoff-execution",
                    "--ack-fresh-sequence",
                    "--ack-no-correct-wsta161-token",
                    "--ack-no-seccomp-load",
                    "--ack-cleanup-required",
                ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(delegated.call_count, 1)
        self.assertEqual(delegated.call_args.args[0], artifacts["script"])
        self.assertTrue(result["checks"]["wsta187_result_valid"])
        self.assertEqual(result["wsta187_result"]["decision"], runner.wsta189.wsta188.wsta187.PASS_DECISION)
        self.assertFalse(result["wsta187_result"]["safety"]["boot_flash"])
        self.assertFalse(result["wsta187_result"]["safety"]["seccomp_filter_loaded"])

    def test_live_gate_blocks_failed_wsta187_delegation(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.write_packet_and_status(root)
            failed = self.wsta187_pass_execution()
            failed["returncode"] = 1
            with mock.patch.object(runner, "run_shell_wrapper", return_value=failed):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "gate"),
                    "--wsta189-operator-packet-status-json",
                    str(artifacts["status"]),
                    "--execute-wsta187-from-status",
                    "--allow-wsta185-handoff-execution",
                    "--ack-fresh-sequence",
                    "--ack-no-correct-wsta161-token",
                    "--ack-no-seccomp-load",
                    "--ack-cleanup-required",
                ]))

        self.assertEqual(result["decision"], "wsta190-blocked-wsta187-delegation")
        self.assertFalse(result["checks"]["wsta187_result_valid"])

    def test_public_surfaces_are_redacted_and_host_only(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.write_packet_and_status(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "gate"),
                "--wsta189-operator-packet-status-json",
                str(artifacts["status"]),
            ]))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "gate" / runner.SUMMARY_MD_NAME).read_text(encoding="utf-8")

        for text in (summary_text, template_text, markdown):
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("http" + "://", text.lower())
            self.assertNotIn("https" + "://", text.lower())
            self.assertNotIn("WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD", text)

    def test_print_template_exits_without_gate(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA190 host-only", payload)
        self.assertIn("--wsta189-operator-packet-status-json", payload)
        self.assertIn("--execute-wsta187-from-status", payload)

    def test_source_keeps_flash_and_raw_network_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("wsta190-wsta189-execute-gate-preflight-pass", source)
        self.assertIn("READY_FOR_EXPLICIT_WSTA187_NO_LOAD_LIVE", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"seccomp_filter_loaded": False', source)
        self.assertIn('"correct_wsta161_token_supplied": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
