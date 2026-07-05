from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta193_seccomp_correct_token_canary_source.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta193_seccomp_correct_token_canary_source.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta193SeccompCorrectTokenCanarySourceTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def wsta192_inputs(self, root: Path) -> tuple[Path, Path]:
        wsta190_path = root / "inputs" / "wsta190_execute_gate.json"
        wsta164_path = root / "inputs" / "wsta164_result.json"
        charter_path = root / "inputs" / "wsta192_seccomp_load_risk_charter.json"
        charter = runner.wsta192.risk_charter(
            wsta190_path,
            wsta164_path,
            charter_path,
            root / "inputs" / "wsta192_seccomp_load_risk_charter.md",
        )
        self.write_json(charter_path, charter)
        result = {
            "decision": runner.wsta192.PASS_DECISION,
            "charter": {
                "charter_json": runner.rel(charter_path),
                "state": "READY_FOR_SEPARATE_SECCOMP_LOAD_DESIGN_NOT_EXECUTABLE",
                "risk_class": "higher-risk-real-seccomp-load",
                "future_rung_count": 4,
                "live_command_generated": False,
                "correct_wsta161_token_supplied": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
            },
            "checks": {
                "charter_guardrail_separate_script": True,
                "charter_future_requires_correct_token_ack": True,
                "wsta190_decision_live_pass": True,
                "wsta164_decision_pass": True,
            },
            "safety": {
                "host_charter_only": True,
                "live_command_executed": False,
                "correct_wsta161_token_supplied": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "secret_values_logged": 0,
            },
        }
        result_path = root / "inputs" / "wsta192_result.json"
        self.write_json(result_path, result)
        return result_path, charter_path

    def run_with_wsta192(self, root: Path, wsta192_result: Path) -> dict:
        return runner.run(runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta193"),
            "--wsta192-result-json",
            str(wsta192_result),
            "--prepare-wsta193-correct-token-canary-source",
        ]))

    def test_source_proof_consumes_wsta192_and_emits_placeholder_canary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta192_result, _ = self.wsta192_inputs(root)
            result = self.run_with_wsta192(root, wsta192_result)
            saved = json.loads((root / "wsta193" / runner.SUMMARY_NAME).read_text(encoding="utf-8"))
            contract = json.loads((root / "wsta193" / runner.CONTRACT_NAME).read_text(encoding="utf-8"))
            source_text = (root / "wsta193" / runner.SOURCE_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertTrue(result["wsta192_checks"]["decision_pass"])
        self.assertTrue(result["checks"]["wsta192_charter_valid"])
        self.assertTrue(result["checks"]["contract_valid"])
        self.assertTrue(result["checks"]["source_valid"])
        self.assertTrue(result["checks"]["shell_syntax_ok"])
        self.assertEqual(contract["state"], "SOURCE_ONLY_CANARY_NOT_EXECUTABLE")
        self.assertEqual(contract["canary_service"], "dpublic-hud")
        self.assertTrue(contract["single_service_canary"])
        self.assertEqual(contract["private_token_env"], runner.PRIVATE_TOKEN_ENV)
        self.assertFalse(contract["token_value_included"])
        self.assertFalse(contract["correct_wsta161_token_supplied"])
        self.assertEqual(
            contract["launcher_env_template"]["A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN"],
            "${" + runner.PRIVATE_TOKEN_ENV + ":?private-token-required}",
        )
        self.assertIn("${" + runner.PRIVATE_TOKEN_ENV + ":?private-token-required}", source_text)
        self.assertIn('A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN="${' + runner.PRIVATE_TOKEN_ENV + '}"', source_text)
        self.assertIn("exit 65", source_text)
        self.assertNotIn(TOKEN_LITERAL, source_text)

    def test_default_run_is_fail_closed_without_explicit_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta192_result, _ = self.wsta192_inputs(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta193"),
                "--wsta192-result-json",
                str(wsta192_result),
            ]))

        self.assertEqual(result["decision"], "wsta193-blocked-explicit-gate-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])

    def test_blocks_nonprivate_or_missing_wsta192_result(self) -> None:
        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            outside_result = Path(outside) / "wsta192_result.json"
            self.write_json(outside_result, {"decision": runner.wsta192.PASS_DECISION})
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta193"),
                "--wsta192-result-json",
                str(outside_result),
                "--prepare-wsta193-correct-token-canary-source",
            ]))
        self.assertEqual(result["decision"], "wsta193-blocked-wsta192-result-nonprivate")

        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta193"),
                "--wsta192-result-json",
                str(root / "missing" / "wsta192_result.json"),
                "--prepare-wsta193-correct-token-canary-source",
            ]))
        self.assertEqual(result["decision"], "wsta193-blocked-wsta192-result-missing")

    def test_blocks_if_wsta192_drifted_toward_executable_or_loaded(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta192_result, _ = self.wsta192_inputs(root)
            payload = json.loads(wsta192_result.read_text(encoding="utf-8"))
            payload["charter"]["live_command_generated"] = True
            self.write_json(wsta192_result, payload)
            result = self.run_with_wsta192(root, wsta192_result)
        self.assertEqual(result["decision"], "wsta193-blocked-wsta192-result-invalid")
        self.assertFalse(result["wsta192_checks"]["charter_no_live_command"])

        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta192_result, _ = self.wsta192_inputs(root)
            payload = json.loads(wsta192_result.read_text(encoding="utf-8"))
            payload["safety"]["seccomp_filter_loaded"] = True
            self.write_json(wsta192_result, payload)
            result = self.run_with_wsta192(root, wsta192_result)
        self.assertEqual(result["decision"], "wsta193-blocked-wsta192-result-invalid")
        self.assertFalse(result["wsta192_checks"]["safety_no_seccomp_load"])

    def test_blocks_if_wsta192_charter_file_is_invalid(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta192_result, charter_path = self.wsta192_inputs(root)
            charter = json.loads(charter_path.read_text(encoding="utf-8"))
            charter["state"] = "READY_TO_EXECUTE"
            self.write_json(charter_path, charter)
            result = self.run_with_wsta192(root, wsta192_result)

        self.assertEqual(result["decision"], "wsta193-blocked-wsta192-charter-invalid")
        self.assertFalse(result["wsta192_charter_checks"]["charter_state_not_executable"])

    def test_public_surfaces_are_redacted_and_source_only(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta192_result, _ = self.wsta192_inputs(root)
            result = self.run_with_wsta192(root, wsta192_result)
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            contract_text = (root / "wsta193" / runner.CONTRACT_NAME).read_text(encoding="utf-8")
            source_text = (root / "wsta193" / runner.SOURCE_NAME).read_text(encoding="utf-8")

        for text in (summary_text, template_text, contract_text, source_text):
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("http" + "://", text.lower())
            self.assertNotIn("https" + "://", text.lower())
            self.assertNotIn(TOKEN_LITERAL, text)
        self.assertFalse(result["contract"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["contract"]["seccomp_filter_loaded_in_this_unit"])
        self.assertFalse(result["contract"]["seccomp_enforced_in_this_unit"])

    def test_print_template_exits_without_running(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA193 host-only", payload)
        self.assertIn("--prepare-wsta193-correct-token-canary-source", payload)
        self.assertNotIn(TOKEN_LITERAL, payload)

    def test_source_keeps_flash_and_no_load_wrapper_reuse_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("wsta193-seccomp-correct-token-canary-source-pass", source)
        self.assertIn("SOURCE_ONLY_CANARY_NOT_EXECUTABLE", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"seccomp_filter_loaded": False', source)
        self.assertIn('"correct_wsta161_token_supplied": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("run_wsta187_fresh", source)
        self.assertNotIn("run_wsta190_wsta189", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())
        self.assertNotIn(TOKEN_LITERAL, source)


if __name__ == "__main__":
    unittest.main()
