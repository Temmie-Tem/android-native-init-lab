from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py")


class ServerDistroWsta28RebootMaterializationGateTests(unittest.TestCase):
    def test_default_gate_blocks_native_reboot(self) -> None:
        class Args:
            allow_native_reboot = False

        ok, decision = runner.explicit_live_gate(Args())
        self.assertFalse(ok)
        self.assertEqual(decision, "wsta28-blocked-explicit-native-reboot-allow-required")

    def test_nested_wsta27_args_use_bridge_fields_expected_by_wsta27(self) -> None:
        class Args:
            host = "127.0.0.1"
            port = 54321
            timeout = 12.0
            probe_timeout_ms = 100
            scan_delay_ms = 5
            scan_slack_sec = 1.0
            scan_interval_sec = 1.0
            scan_attempts = 2

        args = runner.wsta27_args(Args(), Path("/tmp/run"), 2)
        self.assertTrue(args.allow_materialization_live)
        self.assertEqual(args.bridge_host, "127.0.0.1")
        self.assertEqual(args.bridge_port, 54321)
        self.assertEqual(args.run_dir, Path("/tmp/run/wsta27-after-reboot-attempt-02"))

    def test_classification_passes_only_after_nested_scan_gate(self) -> None:
        base = {"checks": {"explicit_live_gate": True, "post_reboot_health": True}}
        passed = {**base, "wsta27_after_reboot": {"decision": "wsta27-materialization-scan-gate-pass"}}
        zero = {**base, "wsta27_after_reboot": {"decision": "wsta27-materialization-scan-engine-ok-zero-bss"}}
        blocked = {**base, "wsta27_after_reboot": {"decision": "wsta27-blocked-materialization-preflight"}}
        self.assertEqual(runner.classify(passed), "wsta28-reboot-materialization-scan-gate-pass")
        self.assertEqual(runner.classify(zero), "wsta28-reboot-materialization-scan-engine-ok-zero-bss")
        self.assertEqual(runner.classify(blocked), "wsta28-reboot-materialization-still-blocked")

    def test_public_summary_omits_health_transcripts(self) -> None:
        result = {
            "decision": "wsta28-reboot-materialization-scan-gate-pass",
            "run_dir": "workspace/private/runs/server-distro/example",
            "checks": {"post_reboot_health": True},
            "reboot_send": {"accepted_no_end_marker": True, "transport_error": "drop"},
            "post_reboot_health": {"commands": {"version": {"text": "raw version transcript"}}},
            "post_reboot_health_summary": {"version": {"contains_v3387": True}},
            "wsta27_after_reboot": {
                "decision": "wsta27-materialization-scan-gate-pass",
                "materialized_scan_window": {"best": {"decision": "wifi-scan-pass"}},
            },
        }
        summary = runner.public_summary(result)
        self.assertTrue(summary["reboot_send"]["transport_error_present"])
        self.assertNotIn("post_reboot_health", summary)
        self.assertEqual(summary["wsta27_after_reboot"]["decision"], "wsta27-materialization-scan-gate-pass")

    def test_runner_surface_reboots_but_stays_below_connectivity_and_flash(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("resident.send_warm_reboot", source)
        self.assertIn("resident.restart_bridge_and_wait_health", source)
        self.assertIn("run_nested_wsta27", source)
        self.assertIn("post_reboot_settle_sec", source)
        self.assertIn('"native_reboot": gate_ok', source)
        self.assertIn('"service_connect_request": False', source)
        self.assertIn('"wifi_association": False', source)
        self.assertIn('"dhcp": False', source)
        self.assertIn('"public_tunnel": False', source)
        for forbidden in (
            '["wifi", "connect"',
            '["wifi", "dhcp"',
            '["wifi", "ping"',
            "autoconnect-confirmed",
            "cloudflared tunnel",
            "ssid=",
            "psk=",
            "native_init_flash.py",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
