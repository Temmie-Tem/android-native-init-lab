from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta202_wsta201_live_preflight.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta202_wsta201_live_preflight.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta202Wsta201LivePreflightTests(unittest.TestCase):
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
        runner.wsta201.wsta200.wsta199.run(runner.wsta201.wsta200.wsta199.build_arg_parser().parse_args([
            "--run-dir",
            str(wsta199_dir),
            "--wsta198-adapter-json",
            str(adapter_dir / runner.wsta198.ADAPTER_JSON_NAME),
        ]))
        wsta200_dir = root / "wsta200"
        runner.wsta201.wsta200.run(runner.wsta201.wsta200.build_arg_parser().parse_args([
            "--run-dir",
            str(wsta200_dir),
            "--wsta199-status-json",
            str(wsta199_dir / runner.wsta201.wsta200.wsta199.STATUS_JSON_NAME),
            "--prepare-wsta200-operator-handoff",
        ]))
        wsta201_dir = root / "wsta201"
        runner.wsta201.run(runner.wsta201.build_arg_parser().parse_args([
            "--run-dir",
            str(wsta201_dir),
            "--wsta200-handoff-json",
            str(wsta200_dir / runner.wsta201.wsta200.HANDOFF_JSON_NAME),
        ]))
        return wsta201_dir / runner.wsta201.STATUS_JSON_NAME

    def args(self, root: Path, status: Path, *, prepare: bool = True) -> list[str]:
        args = [
            "--run-dir",
            str(root / "wsta202"),
            "--wsta201-status-json",
            str(status),
        ]
        if prepare:
            args.append("--prepare-wsta202-live-preflight")
        return args

    def test_preflight_passes_current_status_but_blocks_without_token(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))
            preflight = json.loads((root / "wsta202" / runner.PREFLIGHT_JSON_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta202" / runner.PREFLIGHT_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(preflight["live_preflight"]["state"], "BLOCKED_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF")
        self.assertTrue(preflight["live_preflight"]["handoff_current"])
        self.assertTrue(preflight["live_preflight"]["ready_for_attended_live_handoff"])
        self.assertFalse(preflight["live_preflight"]["ready_for_immediate_live_execute"])
        self.assertFalse(preflight["live_preflight"]["private_token_env_present"])
        self.assertTrue(result["safety"]["wsta201_recheck_executed"])
        self.assertFalse(result["safety"]["wsta200_handoff_shell_executed"])
        self.assertFalse(result["safety"]["wsta198_live_command_executed"])
        self.assertIn("WSTA202 is a preflight only", markdown)

    def test_preflight_reports_ready_when_token_env_matches_without_supplying_it(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_status_chain(root)
            with mock.patch.dict(runner.os.environ, {
                runner.wsta193.PRIVATE_TOKEN_ENV: runner.wsta161.LOAD_TOKEN
            }):
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))

        preflight = result["live_preflight"]
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(preflight["state"], "READY_FOR_ATTENDED_WSTA200_WRAPPER_EXECUTION_DEFAULT_OFF")
        self.assertTrue(preflight["ready_for_immediate_live_execute"])
        self.assertTrue(preflight["private_token_env_present"])
        self.assertTrue(preflight["private_token_matches_wsta161"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["safety"]["device_action"])

    def test_blocks_without_explicit_preflight_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path, prepare=False)))

        self.assertEqual(result["decision"], "wsta202-blocked-explicit-preflight-gate-required")
        self.assertFalse(result["safety"]["wsta201_recheck_executed"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_blocks_invalid_or_nonprivate_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_status_chain(root)
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            payload["handoff_status"]["handoff_match"] = False
            self.write_json(status_path, payload)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))
        self.assertEqual(result["decision"], "wsta202-blocked-status-invalid")
        self.assertFalse(result["status_checks"]["handoff_match"])

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            status_path = self.write_status_chain(root)
            outside_status = Path(outside) / runner.wsta201.STATUS_JSON_NAME
            outside_status.write_text(status_path.read_text(encoding="utf-8"), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, outside_status)))
        self.assertEqual(result["decision"], "wsta202-blocked-status-nonprivate")

    def test_blocks_status_drift_after_recheck(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_status_chain(root)
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            payload["handoff_status"]["operator_preflight_checks"].append("stale-extra")
            self.write_json(status_path, payload)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))

        self.assertEqual(result["decision"], "wsta202-blocked-status-drift")
        self.assertTrue(result["checks"]["wsta201_recheck_valid"])
        self.assertFalse(result["checks"]["status_stable_view_match"])
        self.assertFalse(result["safety"]["wsta200_handoff_shell_executed"])

    def test_print_template_and_public_surfaces_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            preflight_text = (root / "wsta202" / runner.PREFLIGHT_JSON_NAME).read_text(encoding="utf-8")
            source_text = SOURCE.read_text(encoding="utf-8")

        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        for text in (summary_text, preflight_text, source_text, printed.call_args.args[0]):
            self.assertNotIn(TOKEN_LITERAL, text)
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("native_init_flash.py", text)
        self.assertIn("wsta202-wsta201-live-preflight-pass", source_text)
        self.assertIn("BLOCKED_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF", source_text)
        self.assertIn('"boot_flash": False', source_text)
        self.assertIn('"correct_wsta161_token_in_artifact": False', source_text)


if __name__ == "__main__":
    unittest.main()
