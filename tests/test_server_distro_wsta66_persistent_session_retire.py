from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta63 = load_script("workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py")
wsta64 = load_script("workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py")
wsta65 = load_script("workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta66_persistent_session_retire.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta66_persistent_session_retire.py")


class ServerDistroWsta66PersistentSessionRetireTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def make_ready_wsta65(self, root: Path) -> Path:
        wsta63_args = wsta63.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta63"),
            "--prepare-session",
            "--ttl-sec",
            "300",
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
            str(root / "wsta64"),
            "--wsta63-result-json",
            str(root / "wsta63" / "wsta63_result.json"),
        ])
        self.assertEqual(wsta64.run(wsta64_args)["decision"], wsta64.PASS_DECISION)
        wsta65_args = wsta65.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta65-ready"),
            "--wsta64-result-json",
            str(root / "wsta64" / "wsta64_result.json"),
        ])
        self.assertEqual(wsta65.run(wsta65_args)["decision"], wsta65.PASS_DECISION)
        return root / "wsta65-ready" / "wsta65_result.json"

    def retire_args(self, root: Path):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta66"),
            "--retire-session",
            "--ack-retire-session",
            "--wsta65-result-json",
            str(self.make_ready_wsta65(root)),
            "--reason",
            "operator-retired",
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta66-blocked-retire-session-required")
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

    def test_retire_marker_forces_wsta65_retired_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta65.wsta64.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                retire = runner.run(self.retire_args(root))
            marker = root / "wsta66" / "wsta66_retire_marker.json"
            self.assertTrue(marker.exists())
            status = wsta65.run(wsta65.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta65-retired"),
                "--wsta64-result-json",
                str(root / "wsta64" / "wsta64_result.json"),
                "--retire-marker-json",
                str(marker),
            ]))

        self.assertEqual(retire["decision"], runner.PASS_DECISION)
        self.assertEqual(retire["retire"]["session_state"], "RETIRED")
        self.assertFalse(retire["retire"]["ready_for_live"])
        self.assertEqual(status["decision"], wsta65.PASS_DECISION)
        self.assertEqual(status["session_status"]["session_state"], "RETIRED")
        self.assertFalse(status["session_status"]["ready_for_live"])
        self.assertEqual(status["session_status"]["recommended_next_action"], "rerun-wsta63-then-wsta64-if-live-is-needed")

    def test_retire_requires_explicit_ack(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.retire_args(root)
            args.ack_retire_session = False
            result = runner.run(args)

        self.assertEqual(result["decision"], "wsta66-blocked-retire-ack-required")

    def test_wsta65_rejects_retire_marker_for_different_wsta64_result(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            retire = runner.run(self.retire_args(root))
            marker = root / "wsta66" / "wsta66_retire_marker.json"
            payload = json.loads(marker.read_text(encoding="utf-8"))
            payload["wsta64_result"] = "workspace/private/runs/server-distro/other/wsta64_result.json"
            marker.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            status = wsta65.run(wsta65.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta65-retired"),
                "--wsta64-result-json",
                str(root / "wsta64" / "wsta64_result.json"),
                "--retire-marker-json",
                str(marker),
            ]))

        self.assertEqual(retire["decision"], runner.PASS_DECISION)
        self.assertEqual(status["decision"], "wsta65-blocked-retire-marker-source-mismatch")

    def test_public_summary_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(self.retire_args(Path(tmp)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())
            self.assertNotIn(runner.wsta65.wsta64.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta65.wsta64.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)

    def test_print_template_exits_without_retire(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA66 host-only", payload)
        self.assertIn("--retire-session", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("RETIRE_MARKER_SCHEMA", source)
        self.assertIn("RETIRED", source)
        self.assertIn("ready_for_live", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
