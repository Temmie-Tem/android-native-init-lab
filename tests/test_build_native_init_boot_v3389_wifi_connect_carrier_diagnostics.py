"""Regression tests for V3389 Wi-Fi connect carrier diagnostics source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3389_wifi_connect_carrier_diagnostics")


class BuildNativeInitBootV3389WifiConnectCarrierDiagnosticsTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3389")
        self.assertEqual(builder.INIT_VERSION, "0.11.145")
        self.assertEqual(builder.INIT_BUILD, "v3389-wifi-connect-carrier-diagnostics")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3389-wifi-connect-carrier-diagnostics",
            b"0.11.145",
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
            b"wifi-uplink-service-confirm-required",
            b"credentials=private-config-gated",
            b"secret_values_logged=0",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3388_identity(self) -> None:
        text = builder._rewrite_v3389_text(
            "V3388 0.11.144 v3388-wifi-autoconnect-scan-recovery "
            "a90-doomgeneric-v3388"
        )
        self.assertIn("V3389", text)
        self.assertIn("0.11.145", text)
        self.assertIn("v3389-wifi-connect-carrier-diagnostics", text)
        self.assertIn("a90-doomgeneric-v3389", text)
        self.assertNotIn("v3388", text)
        self.assertNotIn("wifi-autoconnect-scan-recovery", text)

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
            "bin/a90_doomgeneric_private_engine_v3388",
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


if __name__ == "__main__":
    unittest.main()
