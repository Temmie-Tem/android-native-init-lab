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
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta70_persistent_session_launch_manifest.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta70_persistent_session_launch_manifest.py")


class ServerDistroWsta70PersistentSessionLaunchManifestTests(unittest.TestCase):
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
            "wsta64": base / "wsta64" / "wsta64_result.json",
            "initial": base / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json",
        }

    def inventory(self, root: Path, now_utc: str | None = None) -> Path:
        args_list = [
            "--run-dir",
            str(root / "inventory"),
            "--scan-root",
            str(root),
        ]
        if now_utc:
            args_list.extend(["--now-utc", now_utc])
        args = wsta67.build_arg_parser().parse_args(args_list)
        self.assertEqual(wsta67.run(args)["decision"], wsta67.PASS_DECISION)
        return root / "inventory" / "wsta67_inventory.json"

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta70-blocked-inventory-required")
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

    def test_ready_inventory_selects_session_and_writes_launch_manifest(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready", ttl_sec=300)
            inventory = self.inventory(root)
            with mock.patch.object(runner.wsta65.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "launch"),
                    "--wsta67-inventory-json",
                    str(inventory),
                ]))
            saved = json.loads((root / "launch" / "wsta70_launch_manifest.json").read_text(encoding="utf-8"))
            markdown = (root / "launch" / "wsta70_launch_manifest.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        manifest = result["launch_manifest"]
        self.assertEqual(manifest["wsta65_session_state"], "READY")
        self.assertTrue(manifest["ready_for_live"])
        self.assertEqual(manifest["ready_candidate_count"], 1)
        self.assertEqual(manifest["selected_ready_index"], 0)
        self.assertIn("--execute-renewal-manual-stop", manifest["live_command_template"])
        self.assertIn("<native-confirm-token>", manifest["live_command_template"])
        self.assertIn("<public-confirm-token>", manifest["live_command_template"])
        self.assertIn("Operator Command Template", markdown)
        self.assertIn("PUBLIC_OFF", markdown)
        self.assertFalse(result["checks"]["live_execution_requested"])

    def test_no_ready_inventory_blocks_without_live_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            stale = self.prepare_session(root, "stale", ttl_sec=60)
            artifact = json.loads(stale["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta65.wsta64.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            now = runner.wsta67.utc_stamp(expires - runner._dt.timedelta(seconds=10))
            inventory = self.inventory(root, now)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "launch"),
                "--wsta67-inventory-json",
                str(inventory),
            ]))

        self.assertEqual(result["decision"], "wsta70-blocked-no-ready-session")
        self.assertEqual(result["candidate_summary"]["ready_candidate_count"], 0)
        self.assertFalse(result["safety"]["public_tunnel"])

    def test_stale_after_inventory_is_revalidated_and_blocked(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            ready = self.prepare_session(root, "ready", ttl_sec=60)
            inventory = self.inventory(root)
            artifact = json.loads(ready["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta65.wsta64.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            later = runner.wsta67.utc_stamp(expires - runner._dt.timedelta(seconds=10))
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "launch"),
                "--wsta67-inventory-json",
                str(inventory),
                "--now-utc",
                later,
            ]))

        self.assertEqual(result["decision"], "wsta70-blocked-selected-not-ready")
        self.assertEqual(result["gate_detail"]["session_state"], "STALE")
        self.assertIn("wsta65_result", result["gate_detail"])

    def test_ready_index_out_of_range_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready", ttl_sec=300)
            inventory = self.inventory(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "launch"),
                "--wsta67-inventory-json",
                str(inventory),
                "--ready-index",
                "1",
            ]))

        self.assertEqual(result["decision"], "wsta70-blocked-ready-index-out-of-range")
        self.assertEqual(result["candidate_summary"]["ready_candidate_count"], 1)

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            self.prepare_session(root, "ready")
            inventory = self.inventory(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "launch"),
                "--wsta67-inventory-json",
                str(inventory),
            ]))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "launch" / "wsta70_launch_manifest.md").read_text(encoding="utf-8")
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

    def test_print_template_exits_without_launch_manifest(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA70 host-only", payload)
        self.assertIn("--wsta67-inventory-json", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

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
