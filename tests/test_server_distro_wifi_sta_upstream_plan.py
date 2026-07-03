"""Static checks for the server-distro Wi-Fi STA upstream plan."""

from __future__ import annotations

import unittest
from pathlib import Path


PLAN = Path("docs/plans/SERVER_DISTRO_WIFI_STA_UPSTREAM_RUNG_2026-07-04.md")


class ServerDistroWifiStaUpstreamPlanTests(unittest.TestCase):
    def test_plan_locks_stage0_debian_ownership_boundary(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        self.assertIn("native init wakes qcacld enough for wlan0", text)
        self.assertIn("Debian starts STA supplicant + DHCP", text)
        self.assertIn("Debian route/tunnel uses wlan0", text)
        self.assertIn("USB NCM remains the recovery/admin path", text)
        self.assertIn("Native child processes must not silently linger", text)

    def test_plan_names_source_only_next_unit_and_default_off_policy(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        self.assertIn("WSTA1: Debian STA client source unit", text)
        self.assertIn("wpasupplicant", text)
        self.assertIn("isc-dhcp-client", text)
        self.assertIn("/etc/a90-dpublic/wifi-sta-enable", text)
        self.assertIn("default D-public boot still does not start STA or cloudflared", text)

    def test_plan_preserves_safety_and_redaction_boundaries(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        self.assertIn("This gate is blocked, not failed, when credentials are absent", text)
        self.assertIn("Do not reopen modem/cellular upstream", text)
        self.assertIn("Do not require SoftAP+STA concurrency", text)
        self.assertIn("Do not start public exposure from native init", text)
        self.assertIn("Do not commit SSID, PSK, BSSID, MAC, DHCP lease", text)
        self.assertIn("secret_values_logged=0", text)


if __name__ == "__main__":
    unittest.main()
