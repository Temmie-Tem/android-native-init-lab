"""Static tests for the native-owned Wi-Fi service boundary source."""

from __future__ import annotations

import unittest
from pathlib import Path


SOURCE = Path("workspace/public/src/native-init/a90_wifi.c")


class NativeWifiServiceBoundarySourceTests(unittest.TestCase):
    def test_service_surface_is_registered_under_wifi_command(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('#define A90_WIFI_SERVICE_VERSION "a90-native-wifi-service-v1"', source)
        self.assertIn("static int wifi_service_cmd(char **argv, int argc)", source)
        self.assertIn('strcmp(argv[1], "service") == 0', source)
        self.assertIn("wifi service [status|start|stop|once]", source)

    def test_service_boundary_is_file_request_response_and_native_owned(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('#define A90_WIFI_SERVICE_REQUEST_FILE "request"', source)
        self.assertIn('#define A90_WIFI_SERVICE_RESPONSE_FILE "response"', source)
        self.assertIn("wifi_service_process_once", source)
        self.assertIn("wifi_service_daemon_run", source)
        self.assertIn("owner=native-init", source)
        self.assertIn("raw_results_redacted=1", source)

    def test_service_boundary_only_exposes_status_and_scan_in_this_rung(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('strcmp(op, "status") == 0', source)
        self.assertIn('strcmp(op, "scan") == 0', source)
        self.assertIn("wifi-service-op-denied", source)
        self.assertIn("credentials=0", source)
        self.assertIn("dhcp_routing=0", source)
        self.assertIn("public_tunnel=0", source)
        self.assertNotIn('strcmp(op, "connect") == 0', source)
        self.assertNotIn('strcmp(op, "dhcp") == 0', source)
        self.assertNotIn('strcmp(op, "ping") == 0', source)


if __name__ == "__main__":
    unittest.main()
