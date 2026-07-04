from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py")


class ServerDistroWsta24NativeWifiUplinkClientTests(unittest.TestCase):
    def test_classify_requires_helper_service_and_cleanup(self) -> None:
        base = {
            "checks": {
                "native_v3387": True,
                "baseline_selftest_fail_zero": True,
                "final_selftest_fail_zero": True,
                "debian_ssh_marker": True,
                "helper_staged": True,
                "service_start_pass": True,
                "helper_status_pass": True,
                "helper_no_confirm_pass": True,
                "service_stop_pass": True,
                "helper_cleanup_ok": True,
                "cleanup_ok": True,
            }
        }

        self.assertEqual(runner.classify(base), runner.PASS_DECISION)

        for key, decision in (
            ("native_v3387", "wsta24-blocked-v3387-not-resident"),
            ("baseline_selftest_fail_zero", "wsta24-blocked-native-health"),
            ("debian_ssh_marker", "wsta24-blocked-debian-chroot-ssh"),
            ("helper_staged", "wsta24-blocked-helper-stage"),
            ("service_start_pass", "wsta24-blocked-service-start"),
            ("helper_status_pass", "wsta24-blocked-helper-status"),
            ("helper_no_confirm_pass", "wsta24-blocked-helper-no-confirm"),
            ("service_stop_pass", "wsta24-blocked-service-stop"),
            ("helper_cleanup_ok", "wsta24-blocked-helper-cleanup"),
            ("cleanup_ok", "wsta24-blocked-cleanup"),
        ):
            variant = {"checks": {**base["checks"], key: False}}
            self.assertEqual(runner.classify(variant), decision)

    def test_helper_output_checks_require_native_owner_and_redaction(self) -> None:
        status = {
            "native_wifi_uplink_client_decision": "native-wifi-uplink-client-pass",
            "native_wifi_uplink_client_secret_values_logged": "0",
            "version": runner.UPLINK_SERVICE_VERSION,
            "op": "status",
            "owner": "native-init",
            "decision": "wifi-uplink-service-status-pass",
            "credentials": "0",
            "connect": "0",
            "dhcp_routing": "observed-only",
            "public_tunnel": "0",
            "secret_values_logged": "0",
        }
        no_confirm = {
            "native_wifi_uplink_client_decision": "native-wifi-uplink-client-pass",
            "native_wifi_uplink_client_requested_op": "autoconnect-no-confirm",
            "native_wifi_uplink_client_secret_values_logged": "0",
            "version": runner.UPLINK_SERVICE_VERSION,
            "op": "autoconnect",
            "owner": "native-init",
            "credentials": "private-config-gated",
            "connect": "confirm-gated",
            "dhcp_routing": "config-gated",
            "external_ping_execution": "0",
            "public_tunnel": "0",
            "secret_values_logged": "0",
            "rc": "-13",
            "decision": "wifi-uplink-service-confirm-required",
        }

        self.assertTrue(runner.helper_status_ok(status))
        self.assertTrue(runner.helper_no_confirm_ok(no_confirm))
        self.assertFalse(runner.helper_status_ok({**status, "owner": "debian"}))
        self.assertFalse(runner.helper_status_ok({**status, "profile": "private-label"}))
        self.assertFalse(runner.helper_no_confirm_ok({**no_confirm, "connect": "started"}))
        self.assertFalse(runner.helper_no_confirm_ok({**no_confirm, "decision": "wifi-uplink-service-autoconnect-pass"}))

    def test_parse_kv_ignores_runner_markers(self) -> None:
        parsed = runner.parse_kv(
            "A90WSTA24_HELPER_STAGED\n"
            "owner=native-init\n"
            "decision=wifi-uplink-service-status-pass\n"
        )

        self.assertEqual(parsed["owner"], "native-init")
        self.assertEqual(parsed["decision"], "wifi-uplink-service-status-pass")
        self.assertNotIn("A90WSTA24_HELPER_STAGED", parsed)

    def test_native_lineage_accepts_v3387_through_v3395(self) -> None:
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.144 (v3388-wifi-autoconnect-scan-recovery)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.145 (v3389-wifi-connect-carrier-diagnostics)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.146 (v3390-wifi-cache-enospc-fallback)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.147 (v3391-wifi-wpa-handshake-diagnostics)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.148 (v3392-wifi-tmp-ctrl-dir)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.149 (v3393-wifi-ctrl-socket-unique)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.150 (v3394-wifi-wpa-failure-detail)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.151 (v3395-wsta-screenapp-live)"))
        self.assertFalse(runner.native_is_v3387("A90 Linux init 0.11.144"))

    def test_runner_surface_stages_helper_and_keeps_network_actions_denied(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("a90_native_wifi_uplink_client.sh", source)
        self.assertIn("A90WSTA24_HELPER_STAGED", source)
        self.assertIn("A90WSTA24_HELPER_CLEANED", source)
        self.assertIn("a90-native-wifi-uplink-client", source)
        self.assertIn("native_is_v3387", source)
        self.assertIn('"wifi",\n                "uplink-service",\n                "start"', source)
        self.assertIn('"wifi", "uplink-service", "stop"', source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertIn('"wifi_association": False', source)
        self.assertIn('"confirm_token_supplied": False', source)
        self.assertIn('"dhcp": False', source)
        self.assertIn('"ping": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"helper_supported_ops": ["status", "autoconnect-no-confirm"]', source)
        self.assertNotIn("native_init_flash.py", source)

        for forbidden_command in (
            '["wifi", "connect"',
            '["wifi", "dhcp"',
            '["wifi", "ping"',
            "confirm=A90_NATIVE_UPLINK_AUTOCONNECT_V1",
            "ssid=",
            "psk=",
        ):
            self.assertNotIn(forbidden_command, source)


if __name__ == "__main__":
    unittest.main()
