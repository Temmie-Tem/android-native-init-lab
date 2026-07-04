from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta63 = load_script("workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py")
wsta64 = load_script("workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py")
wsta67 = load_script("workspace/public/src/scripts/server-distro/run_wsta67_persistent_session_inventory.py")
wsta70 = load_script("workspace/public/src/scripts/server-distro/run_wsta70_persistent_session_launch_manifest.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta71_persistent_launch_readiness_audit.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta71_persistent_launch_readiness_audit.py")


class ServerDistroWsta71PersistentLaunchReadinessAuditTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def prepare_session(self, root: Path, label: str, ttl_sec: int = 300) -> dict[str, Path]:
        base = root / label
        wsta63_args = wsta63.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "wsta63"),
            "--prepare-session",
            "--ttl-sec",
            str(ttl_sec),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])
        self.assertEqual(wsta63.run(wsta63_args)["decision"], wsta63.PASS_DECISION)
        wsta64_args = wsta64.build_arg_parser().parse_args([
            "--run-dir",
            str(base / "wsta64"),
            "--wsta63-result-json",
            str(base / "wsta63" / "wsta63_result.json"),
        ])
        self.assertEqual(wsta64.run(wsta64_args)["decision"], wsta64.PASS_DECISION)
        return {
            "base": base,
            "wsta63": base / "wsta63" / "wsta63_result.json",
            "wsta64": base / "wsta64" / "wsta64_result.json",
            "initial": base / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json",
        }

    def inventory(self, root: Path) -> Path:
        args = wsta67.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "inventory"),
            "--scan-root",
            str(root),
        ])
        self.assertEqual(wsta67.run(args)["decision"], wsta67.PASS_DECISION)
        return root / "inventory" / "wsta67_inventory.json"

    def launch_manifest(self, root: Path, inventory: Path) -> Path:
        args = wsta70.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "launch"),
            "--wsta67-inventory-json",
            str(inventory),
        ])
        self.assertEqual(wsta70.run(args)["decision"], wsta70.PASS_DECISION)
        return root / "launch" / "wsta70_launch_manifest.json"

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta71-blocked-launch-manifest-required")
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

    def test_ready_launch_manifest_revalidates_and_writes_readiness_audit(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready", ttl_sec=300)
            inventory = self.inventory(root)
            launch = self.launch_manifest(root, inventory)
            with mock.patch.object(runner.wsta65.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "readiness"),
                    "--wsta70-launch-manifest-json",
                    str(launch),
                ]))
            saved = json.loads((root / "readiness" / "wsta71_launch_readiness.json").read_text(encoding="utf-8"))
            markdown = (root / "readiness" / "wsta71_launch_readiness.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        readiness = result["readiness"]
        self.assertEqual(readiness["state"], "READY_TO_ARM_DEFAULT_OFF")
        self.assertEqual(readiness["wsta65_session_state"], "READY")
        self.assertTrue(readiness["ready_for_live"])
        self.assertIn("--execute-renewal-manual-stop", readiness["live_command_template"])
        self.assertIn("<native-confirm-token>", readiness["live_command_template"])
        self.assertIn("<public-confirm-token>", readiness["live_command_template"])
        self.assertIn("WSTA Persistent Launch Readiness Audit", markdown)
        self.assertIn("READY_TO_ARM_DEFAULT_OFF", markdown)
        self.assertFalse(result["checks"]["live_execution_requested"])

    def test_launch_manifest_that_ages_stale_blocks_on_revalidation(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            ready = self.prepare_session(root, "ready", ttl_sec=60)
            inventory = self.inventory(root)
            launch = self.launch_manifest(root, inventory)
            artifact = json.loads(ready["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta65.wsta64.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            later = runner.wsta70.wsta67.utc_stamp(expires - runner._dt.timedelta(seconds=10))
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "readiness"),
                "--wsta70-launch-manifest-json",
                str(launch),
                "--now-utc",
                later,
            ]))

        self.assertEqual(result["decision"], "wsta71-blocked-launch-not-ready")
        self.assertEqual(result["gate_detail"]["session_state"], "STALE")
        self.assertIn("wsta65_result", result["gate_detail"])

    def test_nonpass_wsta70_manifest_is_rejected(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            launch = root / "bad" / "wsta70_launch_manifest.json"
            launch.parent.mkdir(parents=True)
            launch.write_text(json.dumps({
                "decision": "wsta70-blocked-no-ready-session",
                "launch_manifest": {},
            }), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "readiness"),
                "--wsta70-launch-manifest-json",
                str(launch),
            ]))

        self.assertEqual(result["decision"], "wsta71-blocked-launch-manifest-not-pass")

    def test_manifest_template_drift_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            session = self.prepare_session(root, "ready", ttl_sec=300)
            inventory = self.inventory(root)
            launch = self.launch_manifest(root, inventory)
            payload = json.loads(session["wsta63"].read_text(encoding="utf-8"))
            payload["session_redacted"]["live_command_template"] = [
                *payload["session_redacted"]["live_command_template"],
                "--drift",
            ]
            session["wsta63"].write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "readiness"),
                "--wsta70-launch-manifest-json",
                str(launch),
            ]))

        self.assertEqual(result["decision"], "wsta71-blocked-live-template-drift")

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready")
            inventory = self.inventory(root)
            launch = self.launch_manifest(root, inventory)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "readiness"),
                "--wsta70-launch-manifest-json",
                str(launch),
            ]))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "readiness" / "wsta71_launch_readiness.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta65.wsta64.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta65.wsta64.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_readiness_audit(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA71 host-only", payload)
        self.assertIn("--wsta70-launch-manifest-json", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("READY_TO_ARM_DEFAULT_OFF", source)
        self.assertIn("wsta65_revalidated_ready", source)
        self.assertIn("live_command_template", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
