"""Regression tests for V3391 Wi-Fi WPA handshake diagnostics source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3391_wifi_wpa_handshake_diagnostics")


class BuildNativeInitBootV3391WifiWpaHandshakeDiagnosticsTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3391")
        self.assertEqual(builder.INIT_VERSION, "0.11.147")
        self.assertEqual(builder.INIT_BUILD, "v3391-wifi-wpa-handshake-diagnostics")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3391-wifi-wpa-handshake-diagnostics",
            b"0.11.147",
            b"ctrl.monitor_attach_rc=",
            b"wpa_complete_wait_rc=",
            b"wpa_monitor_event_count=",
            b"connect_wpa_complete_wait_rc=",
            b"connect_wpa_complete_last_state=",
            b"connect_wpa_monitor_event_count=",
            b"connect_wpa_monitor_last_event=",
            b"wifi-config-enospc-inplace-fallback",
            b"secret_values_logged=0",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3390_identity(self) -> None:
        text = builder._rewrite_v3391_text(
            "V3390 0.11.146 v3390-wifi-cache-enospc-fallback "
            "a90-doomgeneric-v3390"
        )
        self.assertIn("V3391", text)
        self.assertIn("0.11.147", text)
        self.assertIn("v3391-wifi-wpa-handshake-diagnostics", text)
        self.assertIn("a90-doomgeneric-v3391", text)
        self.assertNotIn("v3390", text)
        self.assertNotIn("wifi-cache-enospc-fallback", text)

    def test_manifest_records_wpa_handshake_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]
        diagnostic = service["wpa_handshake_diagnostics"]

        self.assertEqual(service["connect_diagnostics"]["strategy"], "wait-and-persist-redacted-wpa-handshake-summary")
        self.assertEqual(diagnostic["complete_wait_ms"], 25000)
        self.assertEqual(diagnostic["sample_ms"], 1000)
        self.assertEqual(diagnostic["retry_ms"], 5000)
        self.assertTrue(diagnostic["monitor_event_categories_only"])
        self.assertFalse(diagnostic["raw_event_logging"])
        for field in (
            "connect_wpa_complete_wait_rc",
            "connect_wpa_complete_last_state",
            "connect_wpa_monitor_event_count",
            "connect_wpa_monitor_last_event",
        ):
            self.assertIn(field, service["connect_diagnostics"]["redacted_result_fields"])

    def test_manifest_carries_cache_enospc_fallback(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]

        self.assertIn("cache_enospc_fallback", service)
        self.assertEqual(
            service["cache_enospc_fallback"]["strategy"],
            "existing-config-in-place-rewrite-on-storage-pressure",
        )
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3390",
            service["obsolete_ramdisk_engines"],
        )


if __name__ == "__main__":
    unittest.main()
