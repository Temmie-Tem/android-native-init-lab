"""Regression tests for V3390 Wi-Fi cache ENOSPC fallback source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3390_wifi_cache_enospc_fallback")


class BuildNativeInitBootV3390WifiCacheEnospcFallbackTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3390")
        self.assertEqual(builder.INIT_VERSION, "0.11.146")
        self.assertEqual(builder.INIT_BUILD, "v3390-wifi-cache-enospc-fallback")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3390-wifi-cache-enospc-fallback",
            b"0.11.146",
            b"a90-native-wifi-uplink-service-v1",
            b"autoconnect_profile_present=",
            b"config_profile_present=",
            b"requested_profile_present=",
            b"scan_recovery_attempted=",
            b"scan_recovery_first_scan_rc=",
            b"scan_recovery_rc=",
            b"scan_recovery_rescan_rc=",
            b"scan_recovery_success=",
            b"scan_recovery_decision=",
            b"connect_diag_attempted=",
            b"connect_diag_decision=",
            b"connect_ctrl_status_wpa_state=",
            b"connect_carrier_wait_rc=",
            b"connect_ctrl_reassociate_rc=",
            b"wifi-connect-status-not-completed",
            b"wifi-connect-no-carrier",
            b"wifi-config-enospc-inplace-fallback",
            b"wifi_config_cache_fallback=",
            b"wifi-uplink-service-confirm-required",
            b"credentials=private-config-gated",
            b"secret_values_logged=0",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3389_identity(self) -> None:
        text = builder._rewrite_v3390_text(
            "V3389 0.11.145 v3389-wifi-connect-carrier-diagnostics "
            "a90-doomgeneric-v3389"
        )
        self.assertIn("V3390", text)
        self.assertIn("0.11.146", text)
        self.assertIn("v3390-wifi-cache-enospc-fallback", text)
        self.assertIn("a90-doomgeneric-v3390", text)
        self.assertNotIn("v3389", text)
        self.assertNotIn("wifi-connect-carrier-diagnostics", text)

    def test_manifest_records_scan_recovery_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]

        self.assertEqual(service["version"], "a90-native-wifi-uplink-service-v1")
        self.assertEqual(service["scan_recovery"]["strategy"], "cleanup-iftype-probe-rescan-once")
        self.assertEqual(
            service["scan_recovery"]["redacted_result_fields"],
            [
                "scan_recovery_attempted",
                "scan_recovery_first_scan_rc",
                "scan_recovery_rc",
                "scan_recovery_rescan_rc",
                "scan_recovery_success",
                "scan_recovery_decision",
            ],
        )
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3389",
            service["obsolete_ramdisk_engines"],
        )

    def test_manifest_records_connect_diagnostic_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]

        self.assertEqual(
            service["connect_diagnostics"]["strategy"],
            "persist-redacted-connect-carrier-ctrl-summary",
        )
        for field in (
            "connect_diag_attempted",
            "connect_diag_decision",
            "connect_ctrl_status_wpa_state",
            "connect_carrier_wait_rc",
            "connect_ctrl_reassociate_rc",
        ):
            self.assertIn(field, service["connect_diagnostics"]["redacted_result_fields"])

    def test_manifest_records_cache_enospc_fallback_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        fallback = manifest["wifi_uplink_service_boundary"]["cache_enospc_fallback"]

        self.assertEqual(
            fallback["strategy"],
            "existing-config-in-place-rewrite-on-storage-pressure",
        )
        self.assertFalse(fallback["broad_cache_delete"])
        self.assertIn("A90_WIFICFG_SUPPLICANT_CONF", fallback["bounded_paths"])


if __name__ == "__main__":
    unittest.main()
