from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py")


class ServerDistroWsta45ApplianceOperatorTests(unittest.TestCase):
    def publish_args(self, tmp: Path) -> SimpleNamespace:
        return runner.build_arg_parser().parse_args([
            "--mode",
            "publish",
            "--run-dir",
            str(tmp / "run"),
            "--use-native-uplink-profile",
            "--allow-operator-live",
            "--allow-native-reboot",
            "--allow-public-live",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--ack-packet-filter-mutation",
            "--force-packet-filter-restore-proof",
            "--native-confirm-token",
            runner.wsta25.NATIVE_CONFIRM_TOKEN,
            "--public-confirm-token",
            runner.PUBLIC_CONFIRM_TOKEN,
        ])

    def test_profile_contract_is_default_off_and_wsta45_marked(self) -> None:
        contract = runner.profile_contract()

        self.assertTrue(contract["ok"])
        self.assertTrue(contract["default_public_off"])
        self.assertTrue(contract["operator_enable_gate"])
        self.assertTrue(contract["confirmed_env_gate"])
        self.assertTrue(contract["wsta43_required_marker"])
        self.assertTrue(contract["wsta45_wrapper_marker"])
        self.assertTrue(contract["does_not_start_cloudflared"])
        self.assertEqual(contract["secret_values_logged"], 0)

    def test_operator_publish_template_is_redacted_and_profile_enabled(self) -> None:
        template = runner.operator_publish_template()
        command = template["command"]
        text = repr(template)

        self.assertEqual(command[:2], ["python3", "workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py"])
        self.assertIn("--mode", command)
        self.assertIn("publish", command)
        self.assertIn("--use-native-uplink-profile", command)
        self.assertIn("--allow-operator-live", command)
        self.assertIn("--allow-native-reboot", command)
        self.assertIn("--allow-public-live", command)
        self.assertIn("--ack-credentialed-wifi", command)
        self.assertIn("--ack-public-exposure", command)
        self.assertIn("--ack-packet-filter-mutation", command)
        self.assertIn("--force-packet-filter-restore-proof", command)
        self.assertIn("--enable-cloudflared-egress-allowlist", template["optional_cloudflared_egress_allowlist"])
        self.assertIn("--force-cloudflared-egress-allowlist-proof", template["optional_cloudflared_egress_allowlist"])
        self.assertIn("<native-confirm-token>", command)
        self.assertIn("<public-confirm-token>", command)
        self.assertEqual(template["secret_values_logged"], 0)
        self.assertFalse(template["public_url_value_logged"])
        self.assertNotIn(runner.wsta25.NATIVE_CONFIRM_TOKEN, text)
        self.assertNotIn(runner.PUBLIC_CONFIRM_TOKEN, text)
        self.assertNotIn("trycloudflare.com", text)

    def test_explicit_publish_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            mode="preflight",
            use_native_uplink_profile=False,
            allow_operator_live=False,
            allow_native_reboot=False,
            allow_public_live=False,
            ack_credentialed_wifi=False,
            ack_public_exposure=False,
            ack_packet_filter_mutation=False,
            force_packet_filter_restore_proof=False,
            native_confirm_token="",
            public_confirm_token="",
        )
        self.assertEqual(runner.explicit_publish_gate(args), (True, "ok"))

        args.mode = "publish"
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-native-uplink-profile-required"),
        )
        args.use_native_uplink_profile = True
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-operator-live-allow-required"),
        )
        args.allow_operator_live = True
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-native-reboot-allow-required"),
        )
        args.allow_native_reboot = True
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-public-live-allow-required"),
        )
        args.allow_public_live = True
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-credentialed-wifi-ack-required"),
        )
        args.ack_credentialed_wifi = True
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-public-exposure-ack-required"),
        )
        args.ack_public_exposure = True
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-packet-filter-mutation-ack-required"),
        )
        args.ack_packet_filter_mutation = True
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-packet-filter-restore-proof-required"),
        )
        args.force_packet_filter_restore_proof = True
        args.native_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-native-confirm-token-required"),
        )
        args.native_confirm_token = runner.wsta25.NATIVE_CONFIRM_TOKEN
        args.public_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_publish_gate(args),
            (False, "wsta45-blocked-public-confirm-token-required"),
        )
        args.public_confirm_token = runner.PUBLIC_CONFIRM_TOKEN
        self.assertEqual(runner.explicit_publish_gate(args), (True, "ok"))

    def test_cloudflared_egress_allowlist_gate_and_nested_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = self.publish_args(Path(tmp))
            args.enable_cloudflared_egress_allowlist = True

            self.assertEqual(
                runner.explicit_publish_gate(args),
                (False, "wsta45-blocked-cloudflared-egress-allowlist-proof-required"),
            )
            args.force_cloudflared_egress_allowlist_proof = True
            self.assertEqual(
                runner.explicit_publish_gate(args),
                (False, "wsta45-blocked-cloudflared-egress-route-required"),
            )
            args.cloudflared_egress_dns4 = ["dns-route-redacted"]
            args.cloudflared_egress_tls4 = ["tls-route-redacted"]
            self.assertEqual(runner.explicit_publish_gate(args), (True, "ok"))

            nested = runner.wsta43_args(args, Path(tmp) / "run")

        self.assertTrue(nested.enable_cloudflared_egress_allowlist)
        self.assertTrue(nested.force_cloudflared_egress_allowlist_proof)
        self.assertEqual(nested.cloudflared_egress_dns4, ["dns-route-redacted"])
        self.assertEqual(nested.cloudflared_egress_tls4, ["tls-route-redacted"])

    def test_preflight_does_not_call_wsta43_or_require_live_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = runner.build_arg_parser().parse_args(["--run-dir", str(Path(tmp) / "run")])

            with mock.patch.object(runner.wsta43, "run", side_effect=AssertionError("unexpected live call")):
                result = runner.run(args)

        self.assertEqual(result["decision"], runner.PREFLIGHT_DECISION)
        self.assertFalse(result["safety"]["native_reboot"])
        self.assertFalse(result["safety"]["wifi_connect"])
        self.assertFalse(result["safety"]["public_tunnel"])
        self.assertTrue(result["checks"]["profile_contract_ok"])
        self.assertIn("operator_publish_template", result)
        self.assertIn("<native-confirm-token>", result["operator_publish_template"]["command"])

    def test_publish_calls_wsta43_with_profile_enabled_and_redacts_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = self.publish_args(Path(tmp))
            nested = {
                "decision": runner.wsta43.PASS_DECISION,
                "run_dir": "workspace/private/runs/server-distro/example",
                "checks": {"explicit_live_gate": True},
                "safety": {"secret_values_logged": 0, "public_url_value_logged": False},
                "wsta28": {"decision": "wsta28-reboot-materialization-scan-gate-pass"},
                "wsta42": {
                    "use_native_uplink_profile": True,
                    "checks": {
                        "use_native_uplink_profile": True,
                        "native_uplink_profile_confirmed": True,
                        "public_url_value_logged": False,
                    },
                    "host_public_smoke": {"http_status": 200, "url_redacted": True},
                },
            }

            with mock.patch.object(runner.wsta43, "run", return_value=nested) as call:
                result = runner.run(args)

            nested_args = call.call_args.args[0]
            self.assertTrue(nested_args.allow_orchestrated_live)
            self.assertTrue(nested_args.allow_native_reboot)
            self.assertTrue(nested_args.allow_public_live)
            self.assertTrue(nested_args.ack_credentialed_wifi)
            self.assertTrue(nested_args.ack_public_exposure)
            self.assertTrue(nested_args.ack_packet_filter_mutation)
            self.assertTrue(nested_args.force_packet_filter_restore_proof)
            self.assertTrue(nested_args.use_native_uplink_profile)

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["wsta43_pass"])
        self.assertTrue(result["checks"]["wsta43_profile_requested"])
        summary_text = repr(runner.public_summary(result))
        self.assertNotIn(runner.wsta25.NATIVE_CONFIRM_TOKEN, summary_text)
        self.assertNotIn(runner.PUBLIC_CONFIRM_TOKEN, summary_text)
        self.assertNotIn("trycloudflare.com", summary_text)

    def test_print_publish_template_exits_without_running_live(self) -> None:
        with mock.patch.object(runner.wsta43, "run", side_effect=AssertionError("unexpected live call")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-publish-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("<native-confirm-token>", payload)
        self.assertIn("<public-confirm-token>", payload)
        self.assertNotIn(runner.wsta25.NATIVE_CONFIRM_TOKEN, payload)

    def test_passthrough_cannot_supply_or_override_gate_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = runner.build_arg_parser().parse_args([
                "--mode",
                "publish",
                "--run-dir",
                str(Path(tmp) / "run"),
                "--use-native-uplink-profile",
                "--allow-operator-live",
                "--allow-native-reboot",
                "--allow-public-live",
                "--ack-credentialed-wifi",
                "--ack-public-exposure",
                "--native-confirm-token",
                runner.wsta25.NATIVE_CONFIRM_TOKEN,
                "--public-confirm-token",
                runner.PUBLIC_CONFIRM_TOKEN,
                "--",
                "--allow-public-live",
            ])

            with self.assertRaises(ValueError):
                runner.wsta43_args(args, Path(tmp) / "run")

            args.wsta43_args = ["--", "--enable-cloudflared-egress-allowlist"]
            with self.assertRaises(ValueError):
                runner.wsta43_args(args, Path(tmp) / "run")

    def test_source_surface_has_expected_safety_contract(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("--mode", source)
        self.assertIn("--use-native-uplink-profile", source)
        self.assertIn("--allow-operator-live", source)
        self.assertIn("--allow-native-reboot", source)
        self.assertIn("--allow-public-live", source)
        self.assertIn("--ack-credentialed-wifi", source)
        self.assertIn("--ack-public-exposure", source)
        self.assertIn("--print-publish-template", source)
        self.assertIn("operator_publish_template", source)
        self.assertIn("nested.use_native_uplink_profile = True", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertIn("native_confirm_token_value_logged", source)
        self.assertIn("public_url_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
