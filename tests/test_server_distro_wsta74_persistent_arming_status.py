from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta72 = load_script("workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py")
wsta73 = load_script("workspace/public/src/scripts/server-distro/run_wsta73_persistent_arming_packet.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta74_persistent_arming_status.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta74_persistent_arming_status.py")


class ServerDistroWsta74PersistentArmingStatusTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def prepare_packet(self, root: Path, ttl_sec: int = 300) -> dict[str, Path]:
        prepare_args = wsta72.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "prepare"),
            "--prepare-to-arm",
            "--ttl-sec",
            str(ttl_sec),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])
        self.assertEqual(wsta72.run(prepare_args)["decision"], wsta72.PASS_DECISION)
        packet_args = wsta73.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "packet"),
            "--wsta72-prepare-to-arm-json",
            str(root / "prepare" / "wsta72_prepare_to_arm.json"),
        ])
        self.assertEqual(wsta73.run(packet_args)["decision"], wsta73.PASS_DECISION)
        return {
            "prepare": root / "prepare" / "wsta72_prepare_to_arm.json",
            "packet": root / "packet" / "wsta73_arming_packet.json",
            "initial": root / "prepare" / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json",
        }

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta74-blocked-arming-packet-required")
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

    def test_ready_packet_status_rechecks_and_reports_ready(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_packet(root)
            with mock.patch.object(runner.wsta73.wsta71.wsta65.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "status"),
                    "--wsta73-arming-packet-json",
                    str(artifacts["packet"]),
                ]))
            saved = json.loads((root / "status" / "wsta74_arming_status.json").read_text(encoding="utf-8"))
            markdown = (root / "status" / "wsta74_arming_status.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        status = result["arming_status"]
        self.assertEqual(status["state"], "READY_TO_EXECUTE_DEFAULT_OFF")
        self.assertTrue(status["ready_for_live"])
        self.assertEqual(status["wsta73_recheck_decision"], wsta73.PASS_DECISION)
        self.assertTrue(status["template_match"])
        self.assertEqual(status["recommended_next_action"], "operator-may-run-explicit-wsta58-live-gate")
        self.assertIn("WSTA Persistent Arming Packet Status", markdown)
        self.assertFalse(result["checks"]["live_execution_requested"])

    def test_packet_that_ages_stale_reports_not_ready_without_live_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_packet(root, ttl_sec=60)
            artifact = json.loads(artifacts["initial"].read_text(encoding="utf-8"))
            expires = runner.wsta73.wsta71.wsta65.wsta64.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            later = runner.wsta73.wsta72.wsta67.utc_stamp(expires - runner._dt.timedelta(seconds=10))
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "status"),
                "--wsta73-arming-packet-json",
                str(artifacts["packet"]),
                "--now-utc",
                later,
            ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        status = result["arming_status"]
        self.assertEqual(status["state"], "STALE_OR_NOT_READY")
        self.assertFalse(status["ready_for_live"])
        self.assertEqual(status["wsta73_recheck_decision"], "wsta73-blocked-wsta71-recheck")
        self.assertEqual(status["recommended_next_action"], "rerun-wsta72-then-wsta73")
        self.assertFalse(result["checks"]["public_tunnel"] if "public_tunnel" in result["checks"] else False)

    def test_nonpass_arming_packet_is_rejected(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet = root / "bad" / "wsta73_arming_packet.json"
            packet.parent.mkdir(parents=True)
            packet.write_text(json.dumps({
                "decision": "wsta73-blocked-wsta71-recheck",
                "arming_packet": {},
            }), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "status"),
                "--wsta73-arming-packet-json",
                str(packet),
            ]))

        self.assertEqual(result["decision"], "wsta74-blocked-arming-packet-not-pass")

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            artifacts = self.prepare_packet(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "status"),
                "--wsta73-arming-packet-json",
                str(artifacts["packet"]),
            ]))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "status" / "wsta74_arming_status.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta73.wsta72.wsta63.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta73.wsta72.wsta63.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_status(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA74 host-only", payload)
        self.assertIn("--wsta73-arming-packet-json", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("READY_TO_EXECUTE_DEFAULT_OFF", source)
        self.assertIn("wsta74-persistent-arming-status-pass", source)
        self.assertIn("rerun-wsta72-then-wsta73", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
