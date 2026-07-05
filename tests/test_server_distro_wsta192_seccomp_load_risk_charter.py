from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta192_seccomp_load_risk_charter.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta192_seccomp_load_risk_charter.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta192SeccompLoadRiskCharterTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def clean_safety(self, *, device_action=False) -> dict:
        return {
            "device_action": device_action,
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
            "secret_values_logged": 0,
        }

    def wsta190_live_pass(self) -> dict:
        return {
            "decision": runner.wsta190.PASS_DECISION,
            "checks": {
                "status_valid": True,
                "operator_packet_valid": True,
                "execute_gate_valid": True,
                "explicit_live_gate": True,
                "wsta187_result_valid": True,
            },
            "safety": self.clean_safety(device_action=True),
            "wsta187_result": {
                "decision": runner.wsta190.wsta189.wsta188.wsta187.PASS_DECISION,
                "checks": {"wsta185_execution_valid": True},
                "safety": self.clean_safety(device_action="wsta185-no-load-live"),
            },
        }

    def wsta164_contract_pass(self) -> dict:
        proof_checks = {
            "no_gate_no_load_attempt": True,
            "missing_token_no_load_attempt": True,
            "wrong_token_no_load_attempt": True,
            "no_gate_blocks_load_gate": True,
            "missing_token_blocks_before_helper": True,
            "wrong_token_blocks_token": True,
        }
        safety = self.clean_safety(device_action=False)
        safety.pop("correct_wsta161_token_supplied")
        return {
            "decision": runner.wsta164.PASS_DECISION,
            "checks": {
                "launcher_has_wsta164_load_gate": True,
                "launcher_forwards_load_env": True,
                "launcher_does_not_hardcode_wsta161_token": True,
                "helper_schema_is_wsta161": True,
                "helper_apply_code_compiled": True,
            },
            "proof": {
                "correct_wsta161_token_supplied": False,
                "filter_load_enabled": False,
                "seccomp_enforced": False,
            },
            "proof_checks": proof_checks,
            "safety": safety,
        }

    def run_with_inputs(self, root: Path, wsta190_payload: dict, wsta164_payload: dict) -> dict:
        wsta190_path = root / "inputs" / "wsta190_execute_gate.json"
        wsta164_path = root / "inputs" / "wsta164_result.json"
        self.write_json(wsta190_path, wsta190_payload)
        self.write_json(wsta164_path, wsta164_payload)
        return runner.run(runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta192"),
            "--wsta190-live-result-json",
            str(wsta190_path),
            "--wsta164-load-env-contract-json",
            str(wsta164_path),
            "--prepare-wsta192-seccomp-load-risk-charter",
        ]))

    def test_charter_consumes_wsta190_live_and_wsta164_contract(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = self.run_with_inputs(root, self.wsta190_live_pass(), self.wsta164_contract_pass())
            saved = json.loads((root / "wsta192" / runner.SUMMARY_NAME).read_text(encoding="utf-8"))
            charter = json.loads((root / "wsta192" / runner.CHARTER_JSON_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta192" / runner.CHARTER_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertTrue(result["wsta190_checks"]["decision_live_pass"])
        self.assertTrue(result["wsta164_checks"]["decision_pass"])
        self.assertTrue(result["charter_checks"]["state_not_executable"])
        self.assertEqual(charter["state"], "READY_FOR_SEPARATE_SECCOMP_LOAD_DESIGN_NOT_EXECUTABLE")
        self.assertEqual(charter["no_load_workflow"]["status"], "closed-through-wsta191")
        self.assertFalse(charter["this_unit"]["live_command_generated"])
        self.assertFalse(charter["this_unit"]["correct_wsta161_token_supplied"])
        self.assertFalse(charter["this_unit"]["seccomp_filter_loaded"])
        self.assertIn("--allow-correct-wsta161-token", charter["future_acknowledgements_required"])
        self.assertIn("not executable", markdown.lower())

    def test_default_run_is_fail_closed_without_explicit_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta192"),
                "--wsta190-live-result-json",
                str(root / "missing" / "wsta190_execute_gate.json"),
                "--wsta164-load-env-contract-json",
                str(root / "missing" / "wsta164_result.json"),
            ]))

        self.assertEqual(result["decision"], "wsta192-blocked-explicit-gate-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])

    def test_blocks_if_wsta190_input_already_loaded_or_used_correct_token(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta190_payload = self.wsta190_live_pass()
            wsta190_payload["safety"]["seccomp_filter_loaded"] = True
            result = self.run_with_inputs(root, wsta190_payload, self.wsta164_contract_pass())
        self.assertEqual(result["decision"], "wsta192-blocked-charter-invalid")
        self.assertFalse(result["wsta190_checks"]["top_no_mutation"])

        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta190_payload = self.wsta190_live_pass()
            wsta190_payload["wsta187_result"]["safety"]["correct_wsta161_token_supplied"] = True
            result = self.run_with_inputs(root, wsta190_payload, self.wsta164_contract_pass())
        self.assertEqual(result["decision"], "wsta192-blocked-charter-invalid")
        self.assertFalse(result["wsta190_checks"]["delegated_no_mutation"])

    def test_blocks_if_wsta164_contract_drifted_toward_load(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta164_payload = self.wsta164_contract_pass()
            wsta164_payload["proof"]["correct_wsta161_token_supplied"] = True
            result = self.run_with_inputs(root, self.wsta190_live_pass(), wsta164_payload)
        self.assertEqual(result["decision"], "wsta192-blocked-charter-invalid")
        self.assertFalse(result["wsta164_checks"]["proof_correct_token_not_supplied"])

        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta164_payload = self.wsta164_contract_pass()
            wsta164_payload["proof_checks"]["wrong_token_no_load_attempt"] = False
            result = self.run_with_inputs(root, self.wsta190_live_pass(), wsta164_payload)
        self.assertEqual(result["decision"], "wsta192-blocked-charter-invalid")
        self.assertFalse(result["wsta164_checks"]["all_proof_checks_true"])

    def test_public_surfaces_are_redacted_and_not_executable(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = self.run_with_inputs(root, self.wsta190_live_pass(), self.wsta164_contract_pass())
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            charter_text = (root / "wsta192" / runner.CHARTER_JSON_NAME).read_text(encoding="utf-8")
            markdown = (root / "wsta192" / runner.CHARTER_MD_NAME).read_text(encoding="utf-8")

        for text in (summary_text, template_text, charter_text, markdown):
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("http" + "://", text.lower())
            self.assertNotIn("https" + "://", text.lower())
            self.assertNotIn(TOKEN_LITERAL, text)
        self.assertFalse(result["charter"]["live_command_generated"])

    def test_print_template_exits_without_running(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA192 host-only", payload)
        self.assertIn("--prepare-wsta192-seccomp-load-risk-charter", payload)
        self.assertNotIn(TOKEN_LITERAL, payload)

    def test_source_keeps_flash_and_live_load_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("wsta192-seccomp-load-risk-charter-pass", source)
        self.assertIn("READY_FOR_SEPARATE_SECCOMP_LOAD_DESIGN_NOT_EXECUTABLE", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"seccomp_filter_loaded": False', source)
        self.assertIn('"correct_wsta161_token_supplied": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())
        self.assertNotIn(TOKEN_LITERAL, source)


if __name__ == "__main__":
    unittest.main()
