from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta63 = load_script("workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py")
runner = load_script("workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py")


class ServerDistroWsta64PersistentSessionReadinessAuditTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def make_wsta63_session(self, root: Path, ttl_sec: int = 300) -> Path:
        args = wsta63.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta63"),
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
        result = wsta63.run(args)
        self.assertEqual(result["decision"], wsta63.PASS_DECISION)
        return root / "wsta63" / "wsta63_result.json"

    def valid_args(self, root: Path):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta64"),
            "--wsta63-result-json",
            str(self.make_wsta63_session(root)),
            "--min-initial-seconds-remaining",
            "30",
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta64-blocked-wsta63-result-required")
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

    def test_fresh_wsta63_session_is_ready_without_live_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            with mock.patch.object(runner.wsta58.wsta55, "run", side_effect=AssertionError("unexpected live WSTA55")):
                result = runner.run(self.valid_args(root))
            saved = json.loads((root / "wsta64" / "wsta64_result.json").read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["wsta63_pass"])
        self.assertTrue(result["checks"]["initial_private_lease_unexpired"])
        self.assertTrue(result["checks"]["renewal_source_wsta53_valid"])
        self.assertTrue(result["checks"]["wsta58_preflight_pass"])
        self.assertTrue(result["checks"]["live_template_placeholders_only"])
        self.assertFalse(result["checks"]["live_execution_requested"])
        self.assertTrue(result["readiness"]["ready_for_explicit_wsta58_live_gate"])
        self.assertGreaterEqual(result["readiness"]["initial_seconds_remaining"], 30)

    def test_expired_initial_lease_blocks_readiness(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta63_result = self.make_wsta63_session(root, ttl_sec=60)
            source = json.loads(wsta63_result.read_text(encoding="utf-8"))
            initial = Path(root / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json")
            artifact = json.loads(initial.read_text(encoding="utf-8"))
            args = runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta64"),
                "--wsta63-result-json",
                str(wsta63_result),
                "--now-utc",
                artifact["expires_utc"],
            ])
            result = runner.run(args)

        self.assertEqual(source["decision"], wsta63.PASS_DECISION)
        self.assertEqual(result["decision"], "wsta64-blocked-initial-wsta55-blocked-lease-already-expired")

    def test_near_expiry_initial_lease_blocks_readiness(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta63_result = self.make_wsta63_session(root, ttl_sec=60)
            initial = Path(root / "wsta63" / "initial-wsta54" / "wsta54_private_lease.json")
            artifact = json.loads(initial.read_text(encoding="utf-8"))
            expires = runner.parse_utc_stamp(artifact["expires_utc"])
            self.assertIsNotNone(expires)
            now = expires - runner._dt.timedelta(seconds=10)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta64"),
                "--wsta63-result-json",
                str(wsta63_result),
                "--min-initial-seconds-remaining",
                "30",
                "--now-utc",
                runner.utc_stamp(now),
            ]))

        self.assertEqual(result["decision"], "wsta64-blocked-initial-lease-near-expiry")
        self.assertEqual(result["readiness"]["initial_seconds_remaining"], 10)

    def test_raw_token_or_missing_placeholder_in_live_template_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            wsta63_result = self.make_wsta63_session(root)
            payload = json.loads(wsta63_result.read_text(encoding="utf-8"))
            command = payload["session_redacted"]["live_command_template"]
            command[command.index("<native-confirm-token>")] = runner.wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN
            wsta63_result.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta64"),
                "--wsta63-result-json",
                str(wsta63_result),
            ]))

        self.assertEqual(result["decision"], "wsta64-blocked-live-template-token-placeholder-missing")

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

    def test_print_template_exits_without_audit(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA64 host-only", payload)
        self.assertIn("--wsta63-result-json", payload)

    def test_source_keeps_live_and_raw_public_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("validate_command_template", source)
        self.assertIn("wsta55.validate_artifact", source)
        self.assertIn("validate_renewal_source", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
