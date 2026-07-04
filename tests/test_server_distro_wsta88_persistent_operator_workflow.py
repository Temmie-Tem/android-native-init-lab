from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py")


class ServerDistroWsta88PersistentOperatorWorkflowTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def valid_args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "workflow"),
            "--prepare-to-execute",
            "--ttl-sec",
            "300",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
            *extra,
        ])

    def fake_wsta58_pass(self) -> dict:
        return {
            "decision": runner.wsta80.wsta58.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/example/wsta58",
            "gate_decision": "ok",
            "checks": {
                "initial_wsta55_pass": True,
                "renewal_wsta55_pass": True,
                "manual_stop_cleanup_ok": True,
                "manual_stop_public_state_off": True,
                "wsta48_redaction_ok": True,
                "wsta48_all_pass": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "manual_stop": {"manual_stop_public_state": "PUBLIC_OFF"},
            "wsta48_redacted": {"all_pass": True, "redaction_guard_ok": True},
            "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
        }

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta72, "run", side_effect=AssertionError("unexpected WSTA72")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "workflow"),
                ]))

        self.assertEqual(result["decision"], "wsta88-blocked-prepare-to-execute-required")
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "userdata_touch",
            "switch_root",
        ):
            self.assertFalse(result["safety"][key])

    def test_valid_prepare_to_execute_builds_fresh_execute_gate_without_live(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.valid_args(root))
            saved = json.loads((root / "workflow" / "wsta88_operator_workflow.json").read_text(encoding="utf-8"))
            markdown = (root / "workflow" / "wsta88_operator_workflow.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PREFLIGHT_DECISION)
        self.assertEqual(saved["decision"], runner.PREFLIGHT_DECISION)
        workflow = result["workflow"]
        self.assertEqual(workflow["state"], "READY_FOR_EXPLICIT_WSTA58_LIVE_GATE")
        self.assertEqual(workflow["wsta72_decision"], runner.wsta72.PASS_DECISION)
        self.assertEqual(workflow["wsta73_decision"], runner.wsta73.PASS_DECISION)
        self.assertEqual(workflow["wsta75_decision"], runner.wsta75.PASS_DECISION)
        self.assertEqual(workflow["wsta76_decision"], runner.wsta76.PASS_DECISION)
        self.assertEqual(workflow["wsta77_decision"], runner.wsta77.PASS_DECISION)
        self.assertEqual(workflow["wsta78_decision"], runner.wsta78.PASS_DECISION)
        self.assertEqual(workflow["wsta79_decision"], runner.wsta79.PASS_DECISION)
        self.assertEqual(workflow["wsta80_preflight_decision"], runner.wsta80.PREFLIGHT_DECISION)
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertIn("WSTA Persistent Operator Workflow", markdown)
        self.assertIn("READY_FOR_EXPLICIT_WSTA58_LIVE_GATE", markdown)

    def test_execute_flag_without_full_live_ack_blocks_before_wsta58(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.valid_args(root, "--execute-wsta58-from-status"))

        self.assertEqual(result["decision"], "wsta88-blocked-wsta80-live")
        self.assertEqual(result["workflow"]["wsta80_live_decision"], "wsta80-blocked-operator-live-allow-required")
        self.assertTrue(result["checks"]["live_execution_requested"])
        self.assertFalse(result["checks"]["explicit_live_gate"])
        self.assertFalse(result["safety"]["device_action"])

    def test_live_delegates_through_wsta80_only_after_full_ack_stack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            original_wsta80_run = runner.wsta80.run

            def fake_wsta80_run(args):
                if getattr(args, "execute_wsta58_from_status", False):
                    return {
                        "decision": runner.wsta80.PASS_DECISION,
                        "run_dir": runner.rel(root / "workflow" / "gate-live"),
                        "gate_decision": "ok",
                        "checks": {
                            "wsta58_pass": True,
                            "explicit_live_gate": True,
                            "default_public_off": True,
                            "public_url_value_logged": False,
                            "secret_values_logged": 0,
                        },
                        "wsta58_redacted": self.fake_wsta58_pass(),
                        "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
                    }
                return original_wsta80_run(args)

            with mock.patch.object(runner.wsta80, "run", side_effect=fake_wsta80_run) as delegated:
                result = runner.run(self.valid_args(
                    root,
                    "--execute-wsta58-from-status",
                    "--allow-operator-live",
                    "--allow-native-reboot",
                    "--allow-public-live",
                    "--force-ttl-expiry-proof",
                    "--force-manual-stop-proof",
                    "--native-confirm-token",
                    runner.wsta80.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN,
                    "--public-confirm-token",
                    runner.wsta80.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN,
                ))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(delegated.call_count, 2)
        self.assertTrue(delegated.call_args_list[-1].args[0].execute_wsta58_from_status)
        self.assertTrue(result["checks"]["explicit_live_gate"])
        self.assertTrue(result["checks"]["wsta80_live_pass"])
        self.assertTrue(result["safety"]["device_action"])
        public_text = json.dumps(runner.public_summary(result), sort_keys=True)
        self.assertNotIn(runner.wsta80.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, public_text)
        self.assertNotIn(runner.wsta80.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, public_text)

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.valid_args(root))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "workflow" / "wsta88_operator_workflow.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta80.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta80.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_workflow(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA88 one-command", payload)
        self.assertIn("--prepare-to-execute", payload)
        self.assertIn("<native-confirm-token>", payload)
        self.assertIn("<public-confirm-token>", payload)

    def test_source_keeps_flash_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("READY_FOR_EXPLICIT_WSTA58_LIVE_GATE", source)
        self.assertIn("wsta88-persistent-operator-workflow-preflight-pass", source)
        self.assertIn("--execute-wsta58-from-status", source)
        self.assertIn("wsta80.run", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
