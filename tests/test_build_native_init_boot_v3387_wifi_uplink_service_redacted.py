"""Regression tests for V3387 Wi-Fi uplink-service redaction source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3387_wifi_uplink_service_redacted")


class BuildNativeInitBootV3387WifiUplinkServiceRedactedTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3387")
        self.assertEqual(builder.INIT_VERSION, "0.11.143")
        self.assertEqual(builder.INIT_BUILD, "v3387-wifi-uplink-service-redacted")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3387-wifi-uplink-service-redacted",
            b"0.11.143",
            b"a90-native-wifi-uplink-service-v1",
            b"autoconnect_profile_present=",
            b"config_profile_present=",
            b"requested_profile_present=",
            b"wifi-uplink-service-confirm-required",
            b"credentials=private-config-gated",
            b"secret_values_logged=0",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3386_identity(self) -> None:
        text = builder._rewrite_v3387_text(
            "V3386 0.11.142 v3386-wifi-uplink-service-boundary "
            "wifi-uplink-service-boundary a90-doomgeneric-v3386"
        )
        self.assertIn("V3387", text)
        self.assertIn("0.11.143", text)
        self.assertIn("v3387-wifi-uplink-service-redacted", text)
        self.assertIn("wifi-uplink-service-redacted", text)
        self.assertIn("a90-doomgeneric-v3387", text)
        self.assertNotIn("v3386", text)
        self.assertNotIn("wifi-uplink-service-boundary", text)

    def test_manifest_records_profile_label_redaction(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]

        self.assertEqual(service["version"], "a90-native-wifi-uplink-service-v1")
        self.assertEqual(service["profile_label_values"], "redacted-to-present-booleans")
        self.assertEqual(
            service["redacted_profile_fields"],
            [
                "autoconnect_profile_present",
                "config_profile_present",
                "requested_profile_present",
            ],
        )
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3386",
            service["obsolete_ramdisk_engines"],
        )


if __name__ == "__main__":
    unittest.main()
