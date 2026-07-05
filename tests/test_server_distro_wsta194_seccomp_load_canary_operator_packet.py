from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta194_seccomp_load_canary_operator_packet.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta194_seccomp_load_canary_operator_packet.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta194SeccompLoadCanaryOperatorPacketTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta193_inputs(self, root: Path) -> tuple[Path, Path, Path]:
        wsta192_result = root / "inputs" / "wsta192_result.json"
        wsta192_charter = root / "inputs" / "wsta192_charter.json"
        source_path = root / "inputs" / runner.wsta193.SOURCE_NAME
        contract_path = root / "inputs" / runner.wsta193.CONTRACT_NAME
        contract = runner.wsta193.canary_contract(wsta192_result, wsta192_charter, source_path)
        source_text = runner.wsta193.canary_source(contract)
        self.write_json(contract_path, contract)
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(source_text, encoding="utf-8")
        result = {
            "decision": runner.wsta193.PASS_DECISION,
            "checks": {
                "contract_valid": True,
                "source_valid": True,
                "shell_syntax_ok": True,
            },
            "contract": {
                "contract_json": runner.rel(contract_path),
                "source_shell": runner.rel(source_path),
                "state": "SOURCE_ONLY_CANARY_NOT_EXECUTABLE",
                "canary_service": runner.wsta193.CANARY_SERVICE,
                "single_service_canary": True,
                "private_token_env": runner.wsta193.PRIVATE_TOKEN_ENV,
                "token_value_included": False,
                "correct_wsta161_token_supplied": False,
                "seccomp_filter_loaded_in_this_unit": False,
                "seccomp_enforced_in_this_unit": False,
            },
            "safety": {
                "live_command_executed": False,
                "correct_wsta161_token_supplied": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "secret_values_logged": 0,
            },
        }
        result_path = root / "inputs" / "wsta193_result.json"
        self.write_json(result_path, result)
        return result_path, contract_path, source_path

    def run_with_wsta193(self, root: Path, wsta193_result: Path) -> dict:
        return runner.run(runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta194"),
            "--wsta193-result-json",
            str(wsta193_result),
            "--prepare-wsta194-seccomp-load-canary-operator-packet",
        ]))

    def test_prepare_renders_default_off_operator_packet_without_live_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta193_result, _, _ = self.write_wsta193_inputs(root)
            result = self.run_with_wsta193(root, wsta193_result)
            saved = json.loads((root / "wsta194" / runner.PACKET_JSON_NAME).read_text(encoding="utf-8"))
            script = (root / "wsta194" / runner.PACKET_SH_NAME).read_text(encoding="utf-8")
            markdown = (root / "wsta194" / runner.PACKET_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["wsta193_result_valid"])
        self.assertTrue(result["checks"]["wsta193_contract_valid"])
        self.assertTrue(result["checks"]["wsta193_source_valid"])
        self.assertTrue(result["checks"]["operator_packet_valid"])
        self.assertTrue(result["checks"]["shell_syntax_ok"])
        packet = saved["operator_packet"]
        self.assertEqual(packet["state"], "READY_OPERATOR_PACKET_SINGLE_SERVICE_CANARY_DEFAULT_OFF_WSTA196_REQUIRED")
        self.assertFalse(packet["ready_for_live_execution"])
        self.assertTrue(packet["ready_for_wsta195_readiness"])
        self.assertEqual(packet["canary_service"], "dpublic-hud")
        self.assertTrue(packet["single_service_canary"])
        self.assertFalse(packet["token_value_included"])
        self.assertFalse(packet["seccomp_filter_loaded"])
        self.assertIn(runner.FUTURE_WSTA196_RUNNER, packet["future_live_command_template"])
        self.assertIn("--allow-correct-wsta161-token", packet["operator_acknowledgements_required"])
        self.assertIn("blocked-wsta196-not-implemented", script)
        self.assertIn("exit 65", script)
        self.assertIn("Default off", markdown)
        self.assertFalse(result["safety"]["live_command_executed"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])

    def test_default_run_is_fail_closed_without_explicit_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta193_result, _, _ = self.write_wsta193_inputs(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta194"),
                "--wsta193-result-json",
                str(wsta193_result),
            ]))

        self.assertEqual(result["decision"], "wsta194-blocked-explicit-gate-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])

    def test_blocks_nonprivate_or_missing_wsta193_result(self) -> None:
        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            outside_result = Path(outside) / "wsta193_result.json"
            self.write_json(outside_result, {"decision": runner.wsta193.PASS_DECISION})
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta194"),
                "--wsta193-result-json",
                str(outside_result),
                "--prepare-wsta194-seccomp-load-canary-operator-packet",
            ]))
        self.assertEqual(result["decision"], "wsta194-blocked-wsta193-result-nonprivate")

        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta194"),
                "--wsta193-result-json",
                str(root / "missing" / "wsta193_result.json"),
                "--prepare-wsta194-seccomp-load-canary-operator-packet",
            ]))
        self.assertEqual(result["decision"], "wsta194-blocked-wsta193-result-missing")

    def test_blocks_if_wsta193_result_or_contract_drifted_toward_load(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta193_result, _, _ = self.write_wsta193_inputs(root)
            payload = json.loads(wsta193_result.read_text(encoding="utf-8"))
            payload["contract"]["token_value_included"] = True
            self.write_json(wsta193_result, payload)
            result = self.run_with_wsta193(root, wsta193_result)
        self.assertEqual(result["decision"], "wsta194-blocked-wsta193-result-invalid")
        self.assertFalse(result["wsta193_checks"]["token_value_not_included"])

        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta193_result, contract_path, _ = self.write_wsta193_inputs(root)
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["single_service_canary"] = False
            self.write_json(contract_path, contract)
            result = self.run_with_wsta193(root, wsta193_result)
        self.assertEqual(result["decision"], "wsta194-blocked-wsta193-contract-invalid")
        self.assertFalse(result["contract_checks"]["single_service_canary"])

    def test_blocks_if_wsta193_source_reuses_no_load_wrappers(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta193_result, _, source_path = self.write_wsta193_inputs(root)
            source_path.write_text(source_path.read_text(encoding="utf-8") + "\n# run_wsta187_fresh\n", encoding="utf-8")
            result = self.run_with_wsta193(root, wsta193_result)

        self.assertEqual(result["decision"], "wsta194-blocked-wsta193-source-invalid")
        self.assertFalse(result["source_checks"]["source_no_wsta187"])

    def test_public_surfaces_are_redacted_and_default_off(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta193_result, _, _ = self.write_wsta193_inputs(root)
            result = self.run_with_wsta193(root, wsta193_result)
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            packet_text = (root / "wsta194" / runner.PACKET_JSON_NAME).read_text(encoding="utf-8")
            script_text = (root / "wsta194" / runner.PACKET_SH_NAME).read_text(encoding="utf-8")
            markdown = (root / "wsta194" / runner.PACKET_MD_NAME).read_text(encoding="utf-8")

        for text in (summary_text, template_text, packet_text, script_text, markdown):
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("http" + "://", text.lower())
            self.assertNotIn("https" + "://", text.lower())
            self.assertNotIn(TOKEN_LITERAL, text)
        self.assertFalse(result["operator_packet"]["ready_for_live_execution"])
        self.assertFalse(result["operator_packet"]["seccomp_filter_loaded"])

    def test_print_template_exits_without_running(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA194 host-only", payload)
        self.assertIn("--prepare-wsta194-seccomp-load-canary-operator-packet", payload)
        self.assertNotIn(TOKEN_LITERAL, payload)

    def test_source_keeps_flash_and_no_load_wrapper_reuse_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("wsta194-seccomp-load-canary-operator-packet-pass", source)
        self.assertIn("READY_OPERATOR_PACKET_SINGLE_SERVICE_CANARY_DEFAULT_OFF_WSTA196_REQUIRED", source)
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
