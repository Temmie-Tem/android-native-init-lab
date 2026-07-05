from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta201_wsta200_handoff_status.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta201_wsta200_handoff_status.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta201Wsta200HandoffStatusTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def transport_gate_payload(self, gate_path: Path) -> dict:
        return {
            "schema": "a90-wsta197-seccomp-load-canary-transport-gate-v1",
            "state": "TRANSPORT_DECIDED_WSTA196_LIVE_BLOCKED_UNTIL_ADAPTER",
            "selected_transport": runner.wsta198.wsta197.SELECTED_TRANSPORT,
            "transport_gate_json": runner.rel(gate_path),
            "transport_gate_markdown": runner.rel(gate_path.with_suffix(".md")),
            "source_wsta196_result": "workspace/private/wsta196_result.json",
            "source_wsta196_source_gate": "workspace/private/wsta196_source_gate.json",
            "source_wsta149_live_transport_proof": "workspace/private/wsta149_result.json",
            "source_wsta167_seccomp_asset_source_gate": "workspace/private/wsta167_result.json",
            "canary_service": "dpublic-hud",
            "policy_service": "dpublic-hud-intent",
            "launcher_command": ["/usr/local/bin/a90-service-launch", "dpublic-hud", "/bin/true"],
            "single_service_canary": True,
            "private_token_env": runner.wsta193.PRIVATE_TOKEN_ENV,
            "token_value_included": False,
            "correct_wsta161_token_supplied": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "wsta196_direct_host_subprocess_execute_allowed": False,
            "ready_for_wsta198_transport_adapter": True,
            "ready_for_wsta196_live_execute": False,
            "execution_sequence": [
                "fresh-native-readonly-health",
                "start-temporary-dropbear-over-ncm",
                "post-native-readonly-health",
            ],
            "adapter_contract": {
                "runner": "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py",
                "must_not_put_token_on_command_line": True,
                "must_redact_token_from_stdout_stderr": True,
                "must_fail_closed_without_wsta196_ack_flags": True,
                "must_fail_closed_without_private_token_env": True,
                "must_fail_closed_without_fresh_health": True,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def write_status_chain(self, root: Path) -> Path:
        gate = root / "wsta197" / runner.wsta198.wsta197.TRANSPORT_JSON_NAME
        self.write_json(gate, self.transport_gate_payload(gate))
        adapter_dir = root / "wsta198"
        adapter, adapter_script = runner.wsta198.build_adapter_packet(
            adapter_dir,
            gate,
            self.transport_gate_payload(gate),
        )
        self.write_json(adapter_dir / runner.wsta198.ADAPTER_JSON_NAME, adapter)
        (adapter_dir / runner.wsta198.ADAPTER_SH_NAME).write_text(adapter_script, encoding="utf-8")
        (adapter_dir / runner.wsta198.ADAPTER_SH_NAME).chmod(0o700)
        wsta199_dir = root / "wsta199"
        runner.wsta200.wsta199.run(runner.wsta200.wsta199.build_arg_parser().parse_args([
            "--run-dir",
            str(wsta199_dir),
            "--wsta198-adapter-json",
            str(adapter_dir / runner.wsta198.ADAPTER_JSON_NAME),
        ]))
        wsta200_dir = root / "wsta200"
        runner.wsta200.run(runner.wsta200.build_arg_parser().parse_args([
            "--run-dir",
            str(wsta200_dir),
            "--wsta199-status-json",
            str(wsta199_dir / runner.wsta200.wsta199.STATUS_JSON_NAME),
            "--prepare-wsta200-operator-handoff",
        ]))
        return wsta200_dir / runner.wsta200.HANDOFF_JSON_NAME

    def args(self, root: Path, handoff: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta201"),
            "--wsta200-handoff-json",
            str(handoff),
        ]

    def test_status_passes_for_current_handoff_and_requires_token(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, handoff)))
            status = json.loads((root / "wsta201" / runner.STATUS_JSON_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta201" / runner.STATUS_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(status["handoff_status"]["state"], "HANDOFF_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF")
        self.assertTrue(status["handoff_status"]["handoff_current"])
        self.assertTrue(status["handoff_status"]["ready_for_attended_live_handoff"])
        self.assertFalse(status["handoff_status"]["ready_for_immediate_live_execute"])
        self.assertFalse(status["handoff_status"]["private_token_env_present"])
        self.assertTrue(status["handoff_status"]["handoff_match"])
        self.assertTrue(status["handoff_status"]["script_match"])
        self.assertTrue(result["safety"]["wsta200_recheck_executed"])
        self.assertFalse(result["safety"]["live_command_executed"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])
        self.assertIn("WSTA201 does not execute", markdown)

    def test_status_reports_ready_when_token_env_matches_without_supplying_it(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_status_chain(root)
            with mock.patch.dict(runner.os.environ, {
                runner.wsta193.PRIVATE_TOKEN_ENV: runner.wsta161.LOAD_TOKEN
            }):
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, handoff)))

        status = result["handoff_status"]
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(status["state"], "HANDOFF_CURRENT_READY_FOR_ATTENDED_LIVE_DEFAULT_OFF")
        self.assertTrue(status["ready_for_immediate_live_execute"])
        self.assertTrue(status["private_token_env_present"])
        self.assertTrue(status["private_token_matches_wsta161"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["safety"]["device_action"])

    def test_status_detects_handoff_drift_without_executing_wrapper(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_status_chain(root)
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            payload["operator_preflight_checks"].append("stale-extra")
            self.write_json(handoff, payload)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, handoff)))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(result["handoff_status"]["state"], "DRIFT_RECHECK_REQUIRED")
        self.assertFalse(result["handoff_status"]["handoff_current"])
        self.assertFalse(result["handoff_status"]["handoff_match"])
        self.assertTrue(result["handoff_status"]["script_match"])
        self.assertFalse(result["safety"]["wsta200_handoff_shell_executed"])

    def test_blocks_invalid_or_nonprivate_handoff(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_status_chain(root)
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            payload["operator_acknowledgements_required"] = []
            self.write_json(handoff, payload)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, handoff)))
        self.assertEqual(result["decision"], "wsta201-blocked-handoff-invalid")
        self.assertFalse(result["handoff_checks"]["ack_stack_matches_wsta198"])

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            handoff = self.write_status_chain(root)
            outside_handoff = Path(outside) / runner.wsta200.HANDOFF_JSON_NAME
            outside_handoff.write_text(handoff.read_text(encoding="utf-8"), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, outside_handoff)))
        self.assertEqual(result["decision"], "wsta201-blocked-handoff-nonprivate")

    def test_print_template_and_public_surfaces_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            handoff = self.write_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, handoff)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            status_text = (root / "wsta201" / runner.STATUS_JSON_NAME).read_text(encoding="utf-8")
            source_text = SOURCE.read_text(encoding="utf-8")

        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        for text in (summary_text, status_text, source_text, printed.call_args.args[0]):
            self.assertNotIn(TOKEN_LITERAL, text)
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("native_init_flash.py", text)
        self.assertIn("wsta201-wsta200-handoff-status-pass", source_text)
        self.assertIn("HANDOFF_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF", source_text)
        self.assertIn('"boot_flash": False', source_text)
        self.assertIn('"correct_wsta161_token_in_artifact": False', source_text)


if __name__ == "__main__":
    unittest.main()
