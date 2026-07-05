from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta197_seccomp_load_canary_transport_gate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta197_seccomp_load_canary_transport_gate.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta197SeccompLoadCanaryTransportGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta196_source_gate(self, root: Path, *, mutate: dict | None = None) -> Path:
        source_gate_path = root / "wsta196" / runner.wsta196.SOURCE_GATE_JSON_NAME
        payload = {
            "schema": "a90-wsta196-seccomp-load-canary-source-gate-v1",
            "state": "LIVE_RUNNER_SOURCE_READY_DEFAULT_OFF_NOT_EXECUTED",
            "source_wsta195_readiness": "workspace/private/wsta195.json",
            "source_wsta194_operator_packet": "workspace/private/wsta194.json",
            "source_gate_json": runner.rel(source_gate_path),
            "source_gate_markdown": runner.rel(root / "wsta196" / runner.wsta196.SOURCE_GATE_MD_NAME),
            "canary_service": "dpublic-hud",
            "policy_service": "dpublic-hud-intent",
            "launcher_command": ["/usr/local/bin/a90-service-launch", "dpublic-hud", "/bin/true"],
            "single_service_canary": True,
            "private_token_env": runner.wsta193.PRIVATE_TOKEN_ENV,
            "token_value_included": False,
            "correct_wsta161_token_supplied": False,
            "fresh_native_health_check_required": True,
            "post_run_native_health_check_required": True,
            "ready_for_attended_execution": True,
            "ready_for_unattended_execution": False,
            "execution_path_default_off": True,
            "live_command_executed": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "expected_success_markers": [
                "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1",
                "a90_seccomp_loader_decision=loaded",
            ],
            "required_execute_flags": [
                "--execute-real-seccomp-load-canary",
                "--allow-correct-wsta161-token",
                "--ack-seccomp-load-risk",
                "--ack-single-service-canary-only",
                "--ack-no-flash-no-reboot",
                "--ack-cleanup-required",
            ],
            "post_run_audit": ["fresh-native-health-after-canary"],
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        if mutate:
            payload.update(mutate)
        self.write_json(source_gate_path, payload)
        return source_gate_path

    def write_wsta196_result(self, root: Path, source_gate: Path, *, mutate: dict | None = None) -> Path:
        result_path = root / "wsta196" / runner.wsta196.SUMMARY_NAME
        payload = {
            "decision": runner.wsta196.SOURCE_GATE_PASS_DECISION,
            "checks": {
                "explicit_source_gate": True,
                "explicit_execution_gate": False,
                "wsta195_readiness_valid": True,
                "wsta194_packet_valid": True,
                "source_gate_valid": True,
            },
            "source_gate": {
                "source_gate_json": runner.rel(source_gate),
                "ready_for_attended_execution": True,
                "ready_for_unattended_execution": False,
                "live_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
            },
            "safety": {
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "packet_filter_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "rootfs_chroot_mutation": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
                "correct_wsta161_token_supplied": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
            },
        }
        if mutate:
            payload.update(mutate)
        self.write_json(result_path, payload)
        return result_path

    def write_wsta149_live(self, root: Path, *, mutate: dict | None = None) -> Path:
        result_path = root / "wsta149" / runner.wsta149.RESULT_NAME
        payload = {
            "decision": runner.wsta149.PASS_DECISION,
            "checks": {
                "explicit_live_gate": True,
                "chroot_mount_ready": True,
                "dropbear_started": True,
                "debian_ssh_marker": True,
                "service_hardening_assets_staged": True,
                "launcher_exec_logged": True,
                "service_identity_ok": True,
                "public_default_off": True,
                "network_syscalls_absent": True,
                "final_selftest_fail_zero": True,
                "chroot_cleanup_ok": True,
            },
            "safety": {
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "packet_filter_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "rootfs_chroot_mutation": "explicit-live-gated-sd-work-image-only",
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }
        if mutate:
            payload.update(mutate)
        self.write_json(result_path, payload)
        return result_path

    def write_wsta167_source_gate(self, root: Path, *, mutate: dict | None = None) -> Path:
        result_path = root / "wsta167" / runner.wsta167.RESULT_NAME
        payload = {
            "decision": "wsta167-blocked-seccomp-live-observation-required",
            "checks": {
                "contract_valid": True,
                "local_inputs_present": True,
                "explicit_live_gate": False,
            },
            "contract_checks": {
                "schema_ok": True,
                "script_no_external_network_inputs": True,
                "load_expected_false": True,
                "enforcement_expected_false": True,
                "correct_token_false": True,
            },
            "safety": {
                "boot_flash": False,
                "native_reboot": False,
                "wifi_connect": False,
                "dhcp": False,
                "public_tunnel": False,
                "packet_filter_mutation": False,
                "userdata_touch": False,
                "switch_root": False,
                "rootfs_chroot_mutation": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        }
        if mutate:
            payload.update(mutate)
        self.write_json(result_path, payload)
        return result_path

    def write_inputs(self, root: Path) -> tuple[Path, Path, Path, Path]:
        source_gate = self.write_wsta196_source_gate(root)
        wsta196_result = self.write_wsta196_result(root, source_gate)
        wsta149 = self.write_wsta149_live(root)
        wsta167 = self.write_wsta167_source_gate(root)
        return wsta196_result, source_gate, wsta149, wsta167

    def run_args(self, root: Path, paths: tuple[Path, Path, Path, Path]) -> list[str]:
        wsta196_result, source_gate, wsta149, wsta167 = paths
        return [
            "--run-dir",
            str(root / "wsta197"),
            "--wsta196-result-json",
            str(wsta196_result),
            "--wsta196-source-gate-json",
            str(source_gate),
            "--wsta149-live-result-json",
            str(wsta149),
            "--wsta167-source-gate-json",
            str(wsta167),
            "--emit-wsta197-seccomp-load-canary-transport-gate",
        ]

    def test_transport_gate_passes_and_blocks_direct_live_execute(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            paths = self.write_inputs(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.run_args(root, paths)))
            transport = json.loads((root / "wsta197" / runner.TRANSPORT_JSON_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta197" / runner.TRANSPORT_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(transport["selected_transport"], runner.SELECTED_TRANSPORT)
        self.assertFalse(transport["wsta196_direct_host_subprocess_execute_allowed"])
        self.assertTrue(transport["ready_for_wsta198_transport_adapter"])
        self.assertFalse(transport["ready_for_wsta196_live_execute"])
        self.assertEqual(transport["launcher_command"], ["/usr/local/bin/a90-service-launch", "dpublic-hud", "/bin/true"])
        self.assertIn("WSTA197 is a host-only transport decision gate", markdown)
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["wsta196_execute_invoked"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])

    def test_default_run_is_fail_closed_without_explicit_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            paths = self.write_inputs(root)
            args = self.run_args(root, paths)
            args.remove("--emit-wsta197-seccomp-load-canary-transport-gate")
            result = runner.run(runner.build_arg_parser().parse_args(args))

        self.assertEqual(result["decision"], "wsta197-blocked-explicit-gate-required")
        self.assertFalse(result["safety"]["transport_packet_executed"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])

    def test_blocks_invalid_wsta196_or_transport_evidence(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_gate = self.write_wsta196_source_gate(root)
            wsta196_result = self.write_wsta196_result(root, source_gate, mutate={"decision": "blocked"})
            wsta149 = self.write_wsta149_live(root)
            wsta167 = self.write_wsta167_source_gate(root)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.run_args(root, (wsta196_result, source_gate, wsta149, wsta167))
            ))
        self.assertEqual(result["decision"], "wsta197-blocked-wsta196-result-invalid")
        self.assertFalse(result["wsta196_result_checks"]["decision_source_gate_pass"])

        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_gate = self.write_wsta196_source_gate(root)
            wsta196_result = self.write_wsta196_result(root, source_gate)
            wsta149 = self.write_wsta149_live(root, mutate={"checks": {"dropbear_started": False}})
            wsta167 = self.write_wsta167_source_gate(root)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.run_args(root, (wsta196_result, source_gate, wsta149, wsta167))
            ))
        self.assertEqual(result["decision"], "wsta197-blocked-wsta149-transport-invalid")

    def test_blocks_nonprivate_inputs(self) -> None:
        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            paths = list(self.write_inputs(root))
            outside_result = Path(outside) / runner.wsta196.SUMMARY_NAME
            self.write_json(outside_result, {"decision": runner.wsta196.SOURCE_GATE_PASS_DECISION})
            paths[0] = outside_result
            result = runner.run(runner.build_arg_parser().parse_args(
                self.run_args(root, tuple(paths))  # type: ignore[arg-type]
            ))

        self.assertEqual(result["decision"], "wsta197-blocked-wsta196-result-nonprivate")

    def test_print_template_and_public_surfaces_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            paths = self.write_inputs(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.run_args(root, paths)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            transport_text = (root / "wsta197" / runner.TRANSPORT_JSON_NAME).read_text(encoding="utf-8")
            source_text = SOURCE.read_text(encoding="utf-8")

        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        for text in (summary_text, transport_text, source_text, printed.call_args.args[0]):
            self.assertNotIn(TOKEN_LITERAL, text)
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("native_init_flash.py", text)
        self.assertIn("wsta197-seccomp-load-canary-transport-gate-pass", source_text)
        self.assertIn("TRANSPORT_DECIDED_WSTA196_LIVE_BLOCKED_UNTIL_ADAPTER", source_text)
        self.assertIn('"boot_flash": False', source_text)
        self.assertIn('"correct_wsta161_token_in_artifact": False', source_text)


if __name__ == "__main__":
    unittest.main()
