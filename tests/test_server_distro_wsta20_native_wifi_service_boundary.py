from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta20_native_wifi_service_boundary.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta20_native_wifi_service_boundary.py")


class ServerDistroWsta20NativeWifiServiceBoundaryTests(unittest.TestCase):
    def test_classify_requires_service_responses_and_cleanup(self) -> None:
        base = {
            "checks": {
                "native_v3385": True,
                "baseline_selftest_fail_zero": True,
                "final_selftest_fail_zero": True,
                "materialization_admin_up": True,
                "debian_ssh_marker": True,
                "service_start_pass": True,
                "status_response_pass": True,
                "scan_response_pass": True,
                "service_stop_pass": True,
                "cleanup_ok": True,
            }
        }

        self.assertEqual(runner.classify(base), runner.PASS_DECISION)

        for key, decision in (
            ("materialization_admin_up", "wsta20-blocked-materialization"),
            ("debian_ssh_marker", "wsta20-blocked-debian-chroot-ssh"),
            ("service_start_pass", "wsta20-blocked-service-start"),
            ("status_response_pass", "wsta20-blocked-status-response"),
            ("scan_response_pass", "wsta20-blocked-scan-response"),
            ("service_stop_pass", "wsta20-blocked-service-stop"),
            ("cleanup_ok", "wsta20-blocked-cleanup"),
        ):
            variant = {"checks": {**base["checks"], key: False}}
            self.assertEqual(runner.classify(variant), decision)

    def test_response_checks_require_native_owner_redaction_and_scan_count(self) -> None:
        status = {
            "version": runner.SERVICE_VERSION,
            "seq": "1",
            "op": "status",
            "owner": "native-init",
            "decision": "wifi-service-status-pass",
            "dhcp_routing": "0",
            "public_tunnel": "0",
        }
        scan = {
            "version": runner.SERVICE_VERSION,
            "seq": "2",
            "op": "scan",
            "owner": "native-init",
            "raw_results_redacted": "1",
            "decision": "wifi-scan-pass",
            "scan_result_count": "3",
        }

        self.assertTrue(runner.response_status_ok(status, 1, "status"))
        self.assertTrue(runner.response_scan_ok(scan, 2))
        self.assertFalse(runner.response_scan_ok({**scan, "raw_results_redacted": "0"}, 2))
        self.assertFalse(runner.response_scan_ok({**scan, "scan_result_count": "0"}, 2))

    def test_runner_surface_uses_checked_flash_and_native_service_not_switchroot(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("wsta2.FLASH_HELPER", source)
        self.assertIn("V3385_SHA256", source)
        self.assertIn('"wifi",\n                "service",\n                "start"', source)
        self.assertIn('"wifi", "service", "stop"', source)
        self.assertIn("A90WSTA20_REQUEST_WRITTEN", source)
        self.assertIn("A90WSTA20_RESPONSE_READY", source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertNotIn("switch-root-to-distro", source)
        self.assertNotIn("cloudflared tunnel", source)

        for forbidden_command in (
            '["wifi", "connect"',
            '["wifi", "dhcp"',
            '["wifi", "ping"',
            "ssid=",
            "psk=",
        ):
            self.assertNotIn(forbidden_command, source)


if __name__ == "__main__":
    unittest.main()
