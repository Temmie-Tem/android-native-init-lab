from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta53 = load_script("workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py")
wsta54 = load_script("workspace/public/src/scripts/server-distro/run_wsta54_private_lease_artifact.py")
wsta58 = load_script("workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py")


class ServerDistroWsta63PersistentSessionControllerTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def valid_args(self, root: Path):
        return runner.build_arg_parser().parse_args([
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

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            with mock.patch.object(runner.wsta53, "run", side_effect=AssertionError("unexpected child run")):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(Path(tmp) / "run"),
                ]))

        self.assertEqual(result["decision"], "wsta63-blocked-prepare-session-required")
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

    def test_valid_session_prepares_initial_lease_renewal_source_and_wsta58_preflight(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(self.valid_args(root))

            saved = json.loads((root / "wsta63" / "wsta63_result.json").read_text(encoding="utf-8"))
            manifest = json.loads((root / "wsta63" / "wsta63_session_manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["initial_wsta53_pass"])
        self.assertTrue(result["checks"]["initial_wsta54_pass"])
        self.assertTrue(result["checks"]["renewal_source_wsta53_pass"])
        self.assertTrue(result["checks"]["wsta58_preflight_pass"])
        self.assertTrue(result["checks"]["renewal_lease_minted_after_initial"])
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertEqual(manifest["wsta58_preflight_decision"], wsta58.PREFLIGHT_DECISION)
        self.assertIn("initial-wsta54", manifest["initial_private_lease_artifact"])
        self.assertIn("renewal-source-wsta53", manifest["renewal_wsta53_result"])
        self.assertIn("--execute-renewal-manual-stop", manifest["live_command_template"])
        self.assertIn("<native-confirm-token>", manifest["live_command_template"])
        self.assertIn("<public-confirm-token>", manifest["live_command_template"])

    def test_ttl_must_remain_short_for_session_preflight(self) -> None:
        with self.private_tmp() as tmp:
            args = self.valid_args(Path(tmp))
            args.ttl_sec = runner.SHORT_SESSION_MAX_TTL_SEC + 1
            result = runner.run(args)

        self.assertEqual(result["decision"], "wsta63-blocked-ttl-not-short")
        self.assertEqual(result["gate_detail"]["short_session_max_ttl_sec"], runner.SHORT_SESSION_MAX_TTL_SEC)

    def test_public_summary_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(self.valid_args(Path(tmp)))
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
            self.assertNotIn(runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN, text)
            self.assertNotIn(runner.wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN, text)
        self.assertIn("<native-confirm-token>", summary_text)
        self.assertIn("<public-confirm-token>", summary_text)

    def test_print_template_exits_without_running_session(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA63 host-only", payload)
        self.assertIn("--prepare-session", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("run_wsta58_renewal_manual_stop_proof", source)
        self.assertIn("renewal_lease_minted_after_initial", source)
        self.assertIn("<native-confirm-token>", source)
        self.assertIn("<public-confirm-token>", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
