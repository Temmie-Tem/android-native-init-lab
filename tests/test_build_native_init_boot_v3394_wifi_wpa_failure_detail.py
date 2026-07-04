"""Regression tests for V3394 Wi-Fi WPA failure-detail source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3394_wifi_wpa_failure_detail")


class BuildNativeInitBootV3394WifiWpaFailureDetailTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3394")
        self.assertEqual(builder.INIT_VERSION, "0.11.150")
        self.assertEqual(builder.INIT_BUILD, "v3394-wifi-wpa-failure-detail")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3394-wifi-wpa-failure-detail",
            b"0.11.150",
            b"connect_wpa_monitor_temp_disabled_reason_class=",
            b"connect_wpa_monitor_disconnect_reason_class=",
            b"connect_ctrl_status_key_mgmt=",
            b"connect_ctrl_status_pairwise_cipher=",
            b"connect_ctrl_status_group_cipher=",
            b"connect_ctrl_status_network_selected=",
            b"secret_values_logged=0",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3393_identity(self) -> None:
        text = builder._rewrite_v3394_text(
            "V3393 0.11.149 v3393-wifi-ctrl-socket-unique "
            "a90-doomgeneric-v3393"
        )
        self.assertIn("V3394", text)
        self.assertIn("0.11.150", text)
        self.assertIn("v3394-wifi-wpa-failure-detail", text)
        self.assertIn("a90-doomgeneric-v3394", text)
        self.assertNotIn("v3393", text)
        self.assertNotIn("wifi-ctrl-socket-unique", text)

    def test_manifest_records_failure_detail_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]
        detail = service["wpa_failure_detail"]

        self.assertEqual(detail["strategy"], "redacted-wpa-reason-and-status-classification")
        self.assertIn("temp-disabled-reason-class", detail["event_detail"])
        self.assertIn("disconnect-reason-class", detail["event_detail"])
        self.assertIn("key-mgmt", detail["status_detail"])
        self.assertEqual(detail["redaction"], "no-ssid-psk-bssid-raw-mac-ip-gateway-dns-token")
        self.assertIn("ctrl_socket_uniqueness", service)
        self.assertIn("tmp_ctrl_dir", service)
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3393",
            service["obsolete_ramdisk_engines"],
        )


if __name__ == "__main__":
    unittest.main()
