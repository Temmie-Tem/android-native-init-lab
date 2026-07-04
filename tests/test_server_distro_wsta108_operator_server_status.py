from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta88 = load_script("workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py")


class ServerDistroWsta108OperatorServerStatusTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def wsta88_args(self, root: Path):
        return wsta88.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta88"),
            "--prepare-to-execute",
            "--ttl-sec",
            "300",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])

    def hardening_manifest(self) -> dict:
        return {
            "decision": runner.wsta90.PASS_DECISION,
            "manifest": {
                "state": "SERVICE_HARDENING_MANIFEST_SKELETON",
                "services": [
                    {"name": "dpublic-smoke-httpd"},
                    {"name": "cloudflared-quick-tunnel"},
                    {"name": "dropbear-admin-usb"},
                    {"name": "dpublic-hud"},
                    {"name": "wsta-native-uplink-helper"},
                ],
                "global_policy": {
                    "default_public_off": True,
                    "no_new_privs_default": True,
                    "capability_drop_required": True,
                    "seccomp_ready_for_profile_source": True,
                    "packet_filter_backend_required": False,
                    "root_login_policy": "replace-root-authorized-keys-before-always-on",
                },
                "blocking_before_enforcement": [
                    "non-root users/groups not staged",
                    "syscall traces not captured",
                ],
            },
        }

    def valid_args(self, root: Path, wsta88_json: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta108"),
            "--emit-server-status",
            "--wsta88-operator-workflow-json",
            str(wsta88_json),
            *extra,
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta108"),
            ]))

        self.assertEqual(result["decision"], "wsta108-blocked-emit-server-status-required")
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

    def test_valid_wsta88_preflight_emits_server_status_without_hardening_manifest(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            result = runner.run(self.valid_args(root, root / "wsta88" / "wsta88_operator_workflow.json"))
            saved = json.loads((root / "wsta108" / "wsta108_operator_server_status.json").read_text(encoding="utf-8"))
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        status = result["server_status"]
        self.assertEqual(status["state"], "SERVER_PROFILE_READY_DEFAULT_OFF")
        self.assertEqual(status["exposure"]["public_state"], "PUBLIC_OFF")
        self.assertFalse(status["exposure"]["live_execution_requested"])
        self.assertEqual(status["network_model"]["wifi_owner"], "native-init")
        self.assertEqual(status["network_model"]["debian_role"], "service-surface-consumer")
        self.assertFalse(status["network_model"]["handoff_required_for_wsta88"])
        self.assertTrue(status["packet_filter"]["ready"])
        self.assertEqual(status["hardening"]["state"], "NOT_SUPPLIED")
        self.assertFalse(result["checks"]["hardening_manifest_supplied"])
        self.assertIn("WSTA Operator Server Status", markdown)
        self.assertIn("Switch-root required for WSTA88: `false`", markdown)
        self.assertIn("Packet Filter", markdown)

    def test_valid_wsta88_and_wsta90_manifest_emits_hardening_summary(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            self.write_json(manifest_path, self.hardening_manifest())
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
            ))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        hardening = result["server_status"]["hardening"]
        self.assertEqual(hardening["state"], "SERVICE_HARDENING_MANIFEST_SKELETON")
        self.assertEqual(hardening["service_count"], 5)
        self.assertTrue(hardening["global_policy"]["no_new_privs_default"])
        self.assertTrue(hardening["global_policy"]["capability_drop_required"])
        self.assertTrue(result["checks"]["hardening_manifest_supplied"])

    def test_nonpass_wsta88_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta88_json = root / "inputs" / "wsta88_operator_workflow.json"
            self.write_json(wsta88_json, {"decision": "wsta88-blocked"})
            result = runner.run(self.valid_args(root, wsta88_json))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta88-workflow-not-pass")

    def test_nonpass_hardening_manifest_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            manifest = self.hardening_manifest()
            manifest["decision"] = "wsta90-blocked"
            self.write_json(manifest_path, manifest)
            result = runner.run(self.valid_args(
                root,
                root / "wsta88" / "wsta88_operator_workflow.json",
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
            ))

        self.assertEqual(result["decision"], "wsta108-blocked-wsta90-manifest-not-pass")

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.assertEqual(wsta88.run(self.wsta88_args(root))["decision"], wsta88.PREFLIGHT_DECISION)
            result = runner.run(self.valid_args(root, root / "wsta88" / "wsta88_operator_workflow.json"))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "wsta108" / "wsta108_operator_server_status.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(wsta88.wsta80.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(wsta88.wsta80.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_work(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA108 host-only", payload)
        self.assertIn("--emit-server-status", payload)
        self.assertIn("--wsta88-operator-workflow-json", payload)

    def test_source_is_host_only_and_names_server_model(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("SERVER_PROFILE_READY_DEFAULT_OFF", source)
        self.assertIn("native-init", source)
        self.assertIn("service-surface-consumer", source)
        self.assertIn("wsta88-status-hud", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
