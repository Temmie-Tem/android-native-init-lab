from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py")


class ServerDistroWsta72PersistentPrepareToArmTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def valid_args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta72"),
            "--prepare-to-arm",
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

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta72-blocked-prepare-to-arm-required")
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

    def test_valid_prepare_to_arm_runs_host_only_ladder(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta63.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(self.valid_args(root))
            saved = json.loads((root / "wsta72" / "wsta72_prepare_to_arm.json").read_text(encoding="utf-8"))
            markdown = (root / "wsta72" / "wsta72_prepare_to_arm.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        pipeline = result["pipeline"]
        self.assertEqual(pipeline["state"], "READY_TO_ARM_DEFAULT_OFF")
        self.assertEqual(pipeline["wsta63_decision"], runner.wsta63.PASS_DECISION)
        self.assertEqual(pipeline["wsta64_decision"], runner.wsta64.PASS_DECISION)
        self.assertEqual(pipeline["wsta67_decision"], runner.wsta67.PASS_DECISION)
        self.assertEqual(pipeline["wsta69_decision"], runner.wsta69.PASS_DECISION)
        self.assertEqual(pipeline["wsta70_decision"], runner.wsta70.PASS_DECISION)
        self.assertEqual(pipeline["wsta71_decision"], runner.wsta71.PASS_DECISION)
        self.assertIn("--execute-renewal-manual-stop", pipeline["wsta58_live_command_template"])
        self.assertIn("<native-confirm-token>", pipeline["wsta58_live_command_template"])
        self.assertIn("<public-confirm-token>", pipeline["wsta58_live_command_template"])
        self.assertIn("WSTA Persistent Prepare-To-Arm", markdown)
        self.assertIn("READY_TO_ARM_DEFAULT_OFF", markdown)
        self.assertFalse(result["checks"]["live_execution_requested"])

    def test_ttl_must_remain_short(self) -> None:
        with self.private_tmp() as tmp:
            args = self.valid_args(Path(tmp))
            args.ttl_sec = runner.SHORT_SESSION_MAX_TTL_SEC + 1
            result = runner.run(args)

        self.assertEqual(result["decision"], "wsta72-blocked-ttl-not-short")
        self.assertEqual(result["gate_detail"]["short_session_max_ttl_sec"], runner.SHORT_SESSION_MAX_TTL_SEC)

    def test_ready_index_out_of_range_blocks_at_wsta70(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.valid_args(root, "--ready-index", "1"))

        self.assertEqual(result["decision"], "wsta72-blocked-wsta70")
        self.assertEqual(result["pipeline"]["wsta70_decision"], "wsta70-blocked-ready-index-out-of-range")
        self.assertEqual(result["pipeline"]["state"], "NOT_READY")
        self.assertFalse(result["checks"]["live_execution_requested"])

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.valid_args(root))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "wsta72" / "wsta72_prepare_to_arm.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta63.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta63.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_prepare(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA72 host-only", payload)
        self.assertIn("--prepare-to-arm", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("READY_TO_ARM_DEFAULT_OFF", source)
        self.assertIn("wsta72-persistent-prepare-to-arm-pass", source)
        self.assertIn("wsta71", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
