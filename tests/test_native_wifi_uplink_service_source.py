"""Static tests for the gated native-owned Wi-Fi uplink service source."""

from __future__ import annotations

import unittest
from pathlib import Path


SOURCE = Path("workspace/public/src/native-init/a90_wifi.c")


class NativeWifiUplinkServiceSourceTests(unittest.TestCase):
    def test_uplink_service_is_separate_from_status_scan_service(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('#define A90_WIFI_SERVICE_VERSION "a90-native-wifi-service-v1"', source)
        self.assertIn('#define A90_WIFI_UPLINK_SERVICE_VERSION "a90-native-wifi-uplink-service-v1"', source)
        self.assertIn("static int wifi_service_cmd(char **argv, int argc)", source)
        self.assertIn("static int wifi_uplink_service_cmd(char **argv, int argc)", source)
        self.assertIn('strcmp(argv[1], "service") == 0', source)
        self.assertIn('strcmp(argv[1], "uplink-service") == 0', source)
        self.assertIn("wifi service [status|start|stop|once]", source)
        self.assertIn("wifi uplink-service [status|start|stop|once]", source)

    def test_uplink_autoconnect_requires_explicit_confirm_token(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('#define A90_WIFI_UPLINK_SERVICE_CONFIRM "A90_NATIVE_UPLINK_AUTOCONNECT_V1"', source)
        self.assertIn('strcmp(op, "autoconnect") == 0', source)
        self.assertIn("wifi-uplink-service-confirm-required", source)
        self.assertIn("strcmp(confirm, A90_WIFI_UPLINK_SERVICE_CONFIRM) != 0", source)
        self.assertIn("wifi_run_autoconnect_sequence", source)
        self.assertIn("wifi-uplink-service-autoconnect-pass", source)

    def test_uplink_response_records_safety_boundaries(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("static void wifi_uplink_service_append_autoconnect_result")
        end = source.index("int a90_wifi_cmd(char **argv, int argc)")
        uplink_service = source[start:end]

        for marker in (
            "owner=native-init",
            "credentials=private-config-gated",
            "connect=confirm-gated",
            "dhcp_routing=config-gated",
            "external_ping_execution=0",
            "public_tunnel=0",
            "raw_values_redacted=1",
            "secret_values_logged=0",
        ):
            self.assertIn(marker, source)
        self.assertIn("autoconnect_profile_present=%d", uplink_service)
        self.assertIn("config_profile_present=%d", uplink_service)
        self.assertIn("requested_profile_present=%d", uplink_service)
        self.assertNotIn("profile=%s\\n", uplink_service)
        self.assertNotIn("requested_profile=%s", uplink_service)

    def test_status_scan_service_still_denies_connection_ops(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("static int wifi_service_process_once")
        end = source.index("static void wifi_service_daemon_run")
        service_process = source[start:end]

        self.assertIn('strcmp(op, "status") == 0', service_process)
        self.assertIn('strcmp(op, "scan") == 0', service_process)
        self.assertIn("wifi-service-op-denied", service_process)
        self.assertNotIn('strcmp(op, "autoconnect") == 0', service_process)
        self.assertNotIn('strcmp(op, "connect") == 0', service_process)
        self.assertNotIn('strcmp(op, "dhcp") == 0', service_process)
        self.assertNotIn('strcmp(op, "ping") == 0', service_process)


if __name__ == "__main__":
    unittest.main()
