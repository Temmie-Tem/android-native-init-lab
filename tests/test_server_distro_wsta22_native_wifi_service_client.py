from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta22_native_wifi_service_client.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta22_native_wifi_service_client.py")


class ServerDistroWsta22NativeWifiServiceClientTests(unittest.TestCase):
    def test_classify_requires_helper_stage_helper_calls_and_cleanup(self) -> None:
        base = {
            "checks": {
                "native_v3385": True,
                "baseline_selftest_fail_zero": True,
                "final_selftest_fail_zero": True,
                "materialization_admin_up": True,
                "native_scan_ready": True,
                "debian_ssh_marker": True,
                "helper_staged": True,
                "service_start_pass": True,
                "helper_status_pass": True,
                "helper_scan_pass": True,
                "service_stop_pass": True,
                "helper_cleanup_ok": True,
                "cleanup_ok": True,
            }
        }

        self.assertEqual(runner.classify(base), runner.PASS_DECISION)

        for key, decision in (
            ("helper_staged", "wsta22-blocked-helper-stage"),
            ("native_scan_ready", "wsta22-blocked-native-scan-precheck"),
            ("service_start_pass", "wsta22-blocked-service-start"),
            ("helper_status_pass", "wsta22-blocked-helper-status"),
            ("helper_scan_pass", "wsta22-blocked-helper-scan"),
            ("service_stop_pass", "wsta22-blocked-service-stop"),
            ("helper_cleanup_ok", "wsta22-blocked-helper-cleanup"),
            ("cleanup_ok", "wsta22-blocked-cleanup"),
        ):
            variant = {"checks": {**base["checks"], key: False}}
            self.assertEqual(runner.classify(variant), decision)

    def test_helper_output_checks_require_native_owner_and_redaction(self) -> None:
        status = {
            "native_wifi_service_client_decision": "native-wifi-service-client-pass",
            "native_wifi_service_client_secret_values_logged": "0",
            "version": runner.wsta20.SERVICE_VERSION,
            "op": "status",
            "owner": "native-init",
            "decision": "wifi-service-status-pass",
            "dhcp_routing": "0",
            "public_tunnel": "0",
        }
        scan = {
            "native_wifi_service_client_decision": "native-wifi-service-client-pass",
            "native_wifi_service_client_secret_values_logged": "0",
            "version": runner.wsta20.SERVICE_VERSION,
            "op": "scan",
            "owner": "native-init",
            "decision": "wifi-scan-pass",
            "raw_results_redacted": "1",
            "credentials": "0",
            "connect": "0",
            "scan_result_count": "3",
        }

        self.assertTrue(runner.helper_status_ok(status))
        self.assertTrue(runner.helper_scan_ok(scan))
        self.assertFalse(runner.helper_status_ok({**status, "owner": "debian"}))
        self.assertFalse(runner.helper_scan_ok({**scan, "raw_results_redacted": "0"}))
        self.assertFalse(runner.helper_scan_ok({**scan, "scan_result_count": "0"}))

    def test_scan_window_ready_uses_best_summary(self) -> None:
        self.assertTrue(runner.scan_window_has_bss({"best": {"scan_has_bss": True}}))
        self.assertFalse(runner.scan_window_has_bss({"scan_has_bss": True}))

    def test_runner_surface_stages_helper_and_keeps_network_actions_denied(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("a90_native_wifi_service_client.sh", source)
        self.assertIn("A90WSTA22_HELPER_STAGED", source)
        self.assertIn("A90WSTA22_HELPER_CLEANED", source)
        self.assertIn("native_pre_service_scan_window", source)
        self.assertIn("recover_iftype_probe_on_scan_fail", source)
        self.assertIn("native_reboot_recovery", source)
        self.assertIn("reboot_on_native_scan_fail", source)
        self.assertIn("bridge_restart_command", source)
        self.assertIn("a90-native-wifi-service-client", source)
        self.assertIn('"wifi",\n                "service",\n                "start"', source)
        self.assertIn('"wifi", "service", "stop"', source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"--flash-v3385"', source)
        self.assertIn("action=argparse.BooleanOptionalAction, default=False", source)
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
