from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py")


class ServerDistroWsta53PersistentExposurePlanTests(unittest.TestCase):
    def valid_args(self, tmp: Path):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(tmp / "run"),
            "--ttl-sec",
            "1800",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = runner.build_arg_parser().parse_args(["--run-dir", str(Path(tmp) / "run")])
            result = runner.run(args)

        self.assertEqual(result["decision"], "wsta53-blocked-credentialed-wifi-ack-required")
        self.assertFalse(result["plan_redacted"]["future_live_allowed"])
        self.assertFalse(result["plan_redacted"]["wsta54_private_artifact_ready"])
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

    def test_valid_request_generates_redacted_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.valid_args(Path(tmp)))
            saved = json.loads((Path(tmp) / "run" / "wsta53_result.json").read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertTrue(result["plan_redacted"]["wsta54_private_artifact_ready"])
        self.assertFalse(result["plan_redacted"]["future_live_allowed"])
        self.assertEqual(result["request_redacted"]["ttl_sec"], 1800)
        self.assertIn("WSTA45 operator wrapper", result["plan_redacted"]["flow"])
        self.assertIn("WSTA43 orchestrator", result["plan_redacted"]["flow"])
        self.assertIn("WSTA28 reboot/materialization scan-green precondition", result["plan_redacted"]["flow"])
        self.assertIn("WSTA42 native-owned STA uplink + Debian D-public quick Tunnel", result["plan_redacted"]["flow"])
        self.assertIn("WSTA48 redacted aggregate", result["plan_redacted"]["flow"])
        self.assertIn("wsta48_redaction_guard_ok", result["plan_redacted"]["cleanup_required"])
        self.assertEqual(result["safety"]["secret_values_logged"], 0)
        self.assertFalse(result["safety"]["public_url_value_logged"])

    def test_ttl_above_cap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = self.valid_args(Path(tmp))
            args.ttl_sec = runner.MAX_TTL_SEC + 1
            result = runner.run(args)

        self.assertEqual(result["decision"], "wsta53-blocked-ttl-out-of-range")
        self.assertEqual(result["gate_detail"]["maximum_lease_ttl_sec"], runner.MAX_TTL_SEC)

    def test_forbidden_fields_in_private_lease_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lease = Path(tmp) / "lease.json"
            lease.write_text(json.dumps({
                "schema": runner.LEASE_SCHEMA,
                "mode": runner.LEASE_MODE,
                "ttl_sec": 1800,
                "operator_ack_credentialed_wifi": True,
                "operator_ack_public_exposure": True,
                "native_confirm_token_source": "private",
                "public_confirm_token_source": "private",
                "public_url_storage": "workspace/private-only",
                "nested": {"raw_public_url": "redacted-placeholder"},
            }), encoding="utf-8")
            args = runner.build_arg_parser().parse_args([
                "--run-dir",
                str(Path(tmp) / "run"),
                "--lease-json",
                str(lease),
            ])
            result = runner.run(args)

        self.assertEqual(result["decision"], "wsta53-blocked-forbidden-field")
        self.assertIn("nested.raw_public_url", result["gate_detail"]["forbidden_fields"])

    def test_public_summary_and_template_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.valid_args(Path(tmp)))
            summary_text = repr(runner.public_summary(result))
            template_text = repr(runner.template())

        for text in (summary_text, template_text):
            self.assertNotIn("trycloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("http://", text.lower())
            self.assertNotIn("https://", text.lower())
            self.assertNotIn("native-confirm-token", text.lower())
            self.assertNotIn("public-confirm-token", text.lower())
        self.assertIn("workspace/private-only", template_text)

    def test_print_template_exits_without_running_plan(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn(runner.LEASE_SCHEMA, payload)
        self.assertIn("workspace/private-only", payload)

    def test_source_does_not_import_or_call_live_control_surfaces(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertNotIn("subprocess", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("run_wsta42", source)
        self.assertNotIn("run_wsta43", source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"native_reboot": False', source)


if __name__ == "__main__":
    unittest.main()
