from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py")


class ServerDistroWsta43OrchestratedNativeUplinkDpublicTests(unittest.TestCase):
    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            allow_orchestrated_live=False,
            allow_native_reboot=False,
            allow_public_live=False,
            ack_credentialed_wifi=False,
            ack_public_exposure=False,
            native_confirm_token="",
            public_confirm_token="",
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta43-blocked-explicit-orchestrated-live-allow-required"),
        )

        args.allow_orchestrated_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta43-blocked-explicit-native-reboot-allow-required"),
        )

        args.allow_native_reboot = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta43-blocked-explicit-public-live-allow-required"),
        )

        args.allow_public_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta43-blocked-credentialed-wifi-ack-required"),
        )

        args.ack_credentialed_wifi = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta43-blocked-public-exposure-ack-required"),
        )

        args.ack_public_exposure = True
        args.native_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta43-blocked-native-confirm-token-required"),
        )

        args.native_confirm_token = runner.wsta25.NATIVE_CONFIRM_TOKEN
        args.public_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta43-blocked-public-confirm-token-required"),
        )

        args.public_confirm_token = runner.PUBLIC_CONFIRM_TOKEN
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_classify_orders_precondition_before_public_tunnel(self) -> None:
        self.assertEqual(
            runner.classify({"gate_decision": "gate", "checks": {"explicit_live_gate": False}}),
            "gate",
        )
        self.assertEqual(
            runner.classify({"checks": {"explicit_live_gate": True, "wsta28_scan_green": False}}),
            "wsta43-blocked-reboot-materialization",
        )
        self.assertEqual(
            runner.classify({
                "checks": {
                    "explicit_live_gate": True,
                    "wsta28_scan_green": True,
                    "wsta42_pass": False,
                }
            }),
            "wsta43-blocked-dpublic-tunnel",
        )
        self.assertEqual(
            runner.classify({
                "checks": {
                    "explicit_live_gate": True,
                    "wsta28_scan_green": True,
                    "wsta42_pass": True,
                }
            }),
            runner.PASS_DECISION,
        )

    def test_nested_args_preserve_gates_without_public_values(self) -> None:
        args = runner.build_arg_parser().parse_args([
            "--allow-orchestrated-live",
            "--allow-native-reboot",
            "--allow-public-live",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token",
            runner.wsta25.NATIVE_CONFIRM_TOKEN,
            "--public-confirm-token",
            runner.PUBLIC_CONFIRM_TOKEN,
            "--run-dir",
            "workspace/private/runs/server-distro/example",
            "--host-resolver-conf",
            "/tmp/resolv.example",
        ])
        run_dir = Path("workspace/private/runs/server-distro/example")

        w28 = runner.wsta28_args(args, run_dir)
        self.assertTrue(w28.allow_native_reboot)
        self.assertEqual(w28.run_dir, run_dir / "wsta28-reboot-materialization")

        w42 = runner.wsta42_args(args, run_dir)
        self.assertTrue(w42.allow_public_live)
        self.assertTrue(w42.ack_credentialed_wifi)
        self.assertTrue(w42.ack_public_exposure)
        self.assertTrue(w42.enable_autoconnect)
        self.assertEqual(w42.native_confirm_token, runner.wsta25.NATIVE_CONFIRM_TOKEN)
        self.assertEqual(w42.public_confirm_token, runner.PUBLIC_CONFIRM_TOKEN)
        self.assertEqual(w42.host_resolver_conf, [Path("/tmp/resolv.example")])

    def test_public_summary_redacts_url_and_secret_material(self) -> None:
        result = {
            "decision": runner.PASS_DECISION,
            "run_dir": "workspace/private/runs/example",
            "gate_decision": "ok",
            "checks": {"explicit_live_gate": True, "wsta28_scan_green": True, "wsta42_pass": True},
            "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
            "wsta28": {"decision": "wsta28-reboot-materialization-scan-gate-pass"},
            "wsta42": {
                "decision": runner.wsta42.PASS_DECISION,
                "checks": {"public_url_value_logged": False},
                "resolver_sync": {"ready": True, "source": "host-resolver", "nameserver_count": 2},
                "smoke_start": {"local_smoke_ok": True, "loopback_up_rc": 0},
                "cloudflared_start": {"url_observed": True},
                "public_url_fetch": {
                    "url_observed": True,
                    "url_len": 53,
                    "stdout_redacted": True,
                    "private_path": "workspace/private/runs/example/public-url.txt",
                },
                "host_public_smoke": {
                    "returncode": 0,
                    "http_status": 200,
                    "marker_ok": True,
                    "service_ok": True,
                    "public_exposure_marker_ok": True,
                    "url_redacted": True,
                },
            },
        }

        summary = runner.public_summary(result)
        text = repr(summary)
        self.assertIn("url_len", text)
        self.assertNotIn("trycloudflare.com", text)
        self.assertNotIn("public-url.txt", text)
        self.assertNotIn(runner.wsta25.NATIVE_CONFIRM_TOKEN, text)
        self.assertNotIn(runner.PUBLIC_CONFIRM_TOKEN, text)

    def test_source_surface_has_expected_safety_gates(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("--allow-orchestrated-live", source)
        self.assertIn("--allow-native-reboot", source)
        self.assertIn("--allow-public-live", source)
        self.assertIn("--ack-credentialed-wifi", source)
        self.assertIn("--ack-public-exposure", source)
        self.assertIn("wsta28.run", source)
        self.assertIn("wsta42.run", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
