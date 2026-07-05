from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta196_seccomp_load_canary_execute.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta196_seccomp_load_canary_execute.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta196SeccompLoadCanaryExecuteTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta194_packet(self, root: Path, *, mutate: dict | None = None) -> Path:
        packet_json = root / "wsta194" / runner.wsta194.PACKET_JSON_NAME
        shell = root / "wsta194" / runner.wsta194.PACKET_SH_NAME
        markdown = root / "wsta194" / runner.wsta194.PACKET_MD_NAME
        command = [
            "python3",
            runner.wsta194.FUTURE_WSTA196_RUNNER,
            "--run-id",
            "wsta196-seccomp-load-canary-execute-live-<fresh-timestamp>",
            "--wsta194-operator-packet-json",
            runner.rel(packet_json),
            "--execute-real-seccomp-load-canary",
            "--allow-correct-wsta161-token",
            "--ack-seccomp-load-risk",
            "--ack-single-service-canary-only",
            "--ack-no-flash-no-reboot",
            "--ack-cleanup-required",
            "--print-full-json",
        ]
        packet = {
            "schema": "a90-wsta194-seccomp-load-canary-operator-packet-v1",
            "state": "READY_OPERATOR_PACKET_SINGLE_SERVICE_CANARY_DEFAULT_OFF_WSTA196_REQUIRED",
            "default_off": True,
            "ready_for_live_execution": False,
            "ready_for_wsta195_readiness": True,
            "ready_for_wsta196_design": True,
            "source_wsta193_result": "workspace/private/wsta193_result.json",
            "source_wsta193_contract": "workspace/private/wsta193_contract.json",
            "source_wsta193_shell": "workspace/private/wsta193_source.sh",
            "canary_service": "dpublic-hud",
            "policy_service": "dpublic-hud-intent",
            "canary_command": ["/bin/true"],
            "launcher_command": ["/usr/local/bin/a90-service-launch", "dpublic-hud", "/bin/true"],
            "single_service_canary": True,
            "private_token_env": runner.wsta193.PRIVATE_TOKEN_ENV,
            "token_value_included": False,
            "correct_wsta161_token_supplied": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "future_live_command_template": command,
            "operator_packet_shell": runner.rel(shell),
            "operator_packet_markdown": runner.rel(markdown),
            "operator_acknowledgements_required": [
                "--execute-real-seccomp-load-canary",
                "--allow-correct-wsta161-token",
                "--ack-seccomp-load-risk",
                "--ack-single-service-canary-only",
                "--ack-no-flash-no-reboot",
                "--ack-cleanup-required",
            ],
            "operator_preflight_checks": ["confirm-single-service-canary-only"],
            "abort_conditions": ["WSTA196-runner-absent"],
            "cleanup_expectations": ["post-run audit required after any future WSTA196 execution"],
            "safety_boundary": {
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "packet_filter_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
            "json_path": runner.rel(packet_json),
        }
        if mutate:
            packet.update(mutate)
        self.write_json(packet_json, {"decision": runner.wsta194.PASS_DECISION, "operator_packet": packet})
        shell.parent.mkdir(parents=True, exist_ok=True)
        shell.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "echo A90WSTA194_OPERATOR_PACKET_DEFAULT_OFF=1\n"
            "echo A90WSTA194_WSTA196_REQUIRED=1\n"
            "echo a90_wsta194_decision=blocked-wsta196-not-implemented\n"
            "exit 65\n",
            encoding="utf-8",
        )
        shell.chmod(0o700)
        markdown.write_text(
            "# WSTA194 Seccomp-Load Canary Operator Packet\n\n"
            "- Default off: `true`\n\n"
            "WSTA194 does not execute the canary.\n",
            encoding="utf-8",
        )
        return packet_json

    def write_wsta195_readiness(self, root: Path, packet_json: Path, *, mutate: dict | None = None) -> Path:
        readiness_path = root / "wsta195" / runner.wsta195.READINESS_JSON_NAME
        payload = {
            "schema": "a90-wsta195-seccomp-load-canary-readiness-v1",
            "state": "READY_FOR_WSTA196_DESIGN_READONLY_NOT_EXECUTABLE",
            "readiness_scope": "host-only-packet-readiness-not-device-readiness",
            "source_wsta194_operator_packet": runner.rel(packet_json),
            "source_wsta194_operator_shell": runner.rel(root / "wsta194" / runner.wsta194.PACKET_SH_NAME),
            "source_wsta194_operator_markdown": runner.rel(root / "wsta194" / runner.wsta194.PACKET_MD_NAME),
            "canary_service": "dpublic-hud",
            "policy_service": "dpublic-hud-intent",
            "single_service_canary": True,
            "private_token_env": runner.wsta193.PRIVATE_TOKEN_ENV,
            "token_value_included": False,
            "correct_wsta161_token_supplied": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "device_readiness_checked": False,
            "read_only_native_health_check_required_in_wsta196": True,
            "ready_for_wsta196_design": True,
            "ready_for_live_execution": False,
            "live_command_generated": False,
            "live_command_executed": False,
            "future_wsta196_runner": runner.wsta194.FUTURE_WSTA196_RUNNER,
            "required_wsta196_preconditions": ["fresh-WSTA195-readiness-pass"],
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        if mutate:
            payload.update(mutate)
        self.write_json(readiness_path, payload)
        return readiness_path

    def source_args(self, root: Path, readiness: Path, packet: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta196"),
            "--wsta195-readiness-json",
            str(readiness),
            "--wsta194-operator-packet-json",
            str(packet),
            "--emit-wsta196-seccomp-load-canary-source-gate",
        ]

    def execute_args(self, root: Path, readiness: Path, packet: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta196"),
            "--wsta195-readiness-json",
            str(readiness),
            "--wsta194-operator-packet-json",
            str(packet),
            "--execute-real-seccomp-load-canary",
            "--allow-correct-wsta161-token",
            "--ack-seccomp-load-risk",
            "--ack-single-service-canary-only",
            "--ack-no-flash-no-reboot",
            "--ack-cleanup-required",
        ]

    def healthy(self) -> dict:
        return {
            "checks": {
                "bridge_ready": True,
                "version_ok": True,
                "status_ok": True,
                "selftest_fail_zero": True,
            },
            "readiness": {},
        }

    def test_source_gate_passes_without_device_contact_or_token(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet = self.write_wsta194_packet(root)
            readiness = self.write_wsta195_readiness(root, packet)
            with mock.patch.object(runner, "run_readonly_health_checks", side_effect=AssertionError("no health")):
                with mock.patch.object(runner, "run_canary_command", side_effect=AssertionError("no execute")):
                    result = runner.run(runner.build_arg_parser().parse_args(
                        self.source_args(root, readiness, packet)
                    ))
            source_gate = json.loads((root / "wsta196" / runner.SOURCE_GATE_JSON_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.SOURCE_GATE_PASS_DECISION)
        self.assertTrue(result["checks"]["wsta195_readiness_valid"])
        self.assertTrue(result["checks"]["wsta194_packet_valid"])
        self.assertTrue(result["checks"]["source_gate_valid"])
        self.assertEqual(source_gate["state"], "LIVE_RUNNER_SOURCE_READY_DEFAULT_OFF_NOT_EXECUTED")
        self.assertTrue(source_gate["ready_for_attended_execution"])
        self.assertFalse(source_gate["ready_for_unattended_execution"])
        self.assertFalse(source_gate["live_command_executed"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])

    def test_default_blocks_without_source_or_execute_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet = self.write_wsta194_packet(root)
            readiness = self.write_wsta195_readiness(root, packet)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta196"),
                "--wsta195-readiness-json",
                str(readiness),
                "--wsta194-operator-packet-json",
                str(packet),
            ]))

        self.assertEqual(result["decision"], "wsta196-blocked-explicit-source-gate-required")
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_invalid_readiness_or_packet_blocks_before_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet = self.write_wsta194_packet(root)
            readiness = self.write_wsta195_readiness(root, packet, mutate={"ready_for_live_execution": True})
            result = runner.run(runner.build_arg_parser().parse_args(
                self.source_args(root, readiness, packet)
            ))
        self.assertEqual(result["decision"], "wsta196-blocked-wsta195-readiness-invalid")
        self.assertFalse(result["wsta195_readiness_checks"]["not_ready_for_live_execution"])

        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet = self.write_wsta194_packet(root, mutate={"token_value_included": True})
            readiness = self.write_wsta195_readiness(root, packet)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.source_args(root, readiness, packet)
            ))
        self.assertEqual(result["decision"], "wsta196-blocked-wsta194-packet-invalid")
        self.assertFalse(result["wsta194_packet_checks"]["token_value_not_included"])

    def test_execute_blocks_missing_private_token_before_health_or_command(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet = self.write_wsta194_packet(root)
            readiness = self.write_wsta195_readiness(root, packet)
            with mock.patch.dict(runner.os.environ, {}, clear=True):
                with mock.patch.object(runner, "run_readonly_health_checks", side_effect=AssertionError("no health")):
                    with mock.patch.object(runner, "run_canary_command", side_effect=AssertionError("no execute")):
                        result = runner.run(runner.build_arg_parser().parse_args(
                            self.execute_args(root, readiness, packet)
                        ))

        self.assertEqual(result["decision"], "wsta196-blocked-private-token-env-missing")
        self.assertFalse(result["safety"]["fresh_native_health_checked"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_execute_with_token_health_and_loaded_marker_passes(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet = self.write_wsta194_packet(root)
            readiness = self.write_wsta195_readiness(root, packet)
            health_calls: list[float] = []
            command_calls: list[list[str]] = []

            def fake_health(timeout: float) -> dict:
                health_calls.append(timeout)
                return self.healthy()

            def fake_canary(command: list[str], *, env: dict[str, str], timeout: float) -> dict:
                self.assertEqual(timeout, 120.0)
                self.assertEqual(env["A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN"], runner.wsta161.LOAD_TOKEN)
                command_calls.append(command)
                return {
                    "command": command,
                    "returncode": 65,
                    "stdout": (
                        "A90WSTA154_SECCOMP_SERVICE=dpublic-hud\n"
                        "A90WSTA154_SECCOMP_POLICY_SERVICE=dpublic-hud-intent\n"
                        "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1\n"
                        "A90WSTA161_SECCOMP_LOAD=1\n"
                        "a90_seccomp_loader_decision=loaded\n"
                        "A90WSTA163_SECCOMP_HELPER_APPLY_OK=1\n"
                    ),
                    "stderr": "",
                }

            with mock.patch.dict(runner.os.environ, {
                runner.wsta193.PRIVATE_TOKEN_ENV: runner.wsta161.LOAD_TOKEN,
            }, clear=True):
                with mock.patch.object(runner, "run_readonly_health_checks", side_effect=fake_health):
                    with mock.patch.object(runner, "run_canary_command", side_effect=fake_canary):
                        result = runner.run(runner.build_arg_parser().parse_args(
                            self.execute_args(root, readiness, packet)
                        ))

        self.assertEqual(result["decision"], runner.EXECUTE_PASS_DECISION)
        self.assertEqual(len(health_calls), 2)
        self.assertEqual(command_calls, [["/usr/local/bin/a90-service-launch", "dpublic-hud", "/bin/true"]])
        self.assertTrue(result["checks"]["fresh_health_valid"])
        self.assertTrue(result["checks"]["canary_loaded"])
        self.assertTrue(result["checks"]["post_health_valid"])
        self.assertTrue(result["safety"]["correct_wsta161_token_supplied"])
        self.assertTrue(result["safety"]["seccomp_filter_loaded"])
        self.assertTrue(result["safety"]["seccomp_enforced"])

    def test_print_template_and_public_source_are_redacted(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        texts = [
            printed.call_args.args[0],
            SOURCE.read_text(encoding="utf-8"),
        ]
        for text in texts:
            self.assertNotIn(TOKEN_LITERAL, text)
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("native_init_flash.py", text)
        self.assertIn("wsta196-seccomp-load-canary-source-gate-pass", texts[1])
        self.assertIn("LIVE_RUNNER_SOURCE_READY_DEFAULT_OFF_NOT_EXECUTED", texts[1])
        self.assertIn('"boot_flash": False', texts[1])
        self.assertIn('"correct_wsta161_token_in_artifact": False', texts[1])


if __name__ == "__main__":
    unittest.main()
