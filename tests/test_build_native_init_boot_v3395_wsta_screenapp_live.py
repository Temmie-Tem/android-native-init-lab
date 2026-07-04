"""Regression tests for V3395 WSTA screenapp source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3395_wsta_screenapp_live")


class BuildNativeInitBootV3395WstaScreenappLiveTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3395")
        self.assertEqual(builder.INIT_VERSION, "0.11.151")
        self.assertEqual(builder.INIT_BUILD, "v3395-wsta-screenapp-live")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3395-wsta-screenapp-live",
            b"0.11.151",
            b"screenapp.title=WSTA D-PUBLIC",
            b"WSTA D-PUBLIC",
            b"WSTA PUBLISH",
            b"FLOW WSTA45 -> WSTA43 -> WSTA42",
            b"PUBLISH: HOST RUNBOOK ONLY",
            b"NATIVE MENU: DISPLAY-ONLY NO CONNECT",
            b"AGGREGATE: WSTA48 REDACTED RESULT",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3394_identity(self) -> None:
        text = builder._rewrite_v3395_text(
            "V3394 0.11.150 v3394-wifi-wpa-failure-detail "
            "a90-doomgeneric-v3394"
        )
        self.assertIn("V3395", text)
        self.assertIn("0.11.151", text)
        self.assertIn("v3395-wsta-screenapp-live", text)
        self.assertIn("a90-doomgeneric-v3395", text)
        self.assertNotIn("v3394", text)
        self.assertNotIn("wifi-wpa-failure-detail", text)

    def test_manifest_records_wsta_screenapp_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        self.assertEqual(manifest["rung"], "wsta-screenapp-live")
        self.assertEqual(manifest["scope"], "native-wsta-operator-screenapp")

        screenapp = manifest["wsta_operator_screenapp"]
        self.assertEqual(screenapp["surface"], "NETWORK menu + screenapp wsta/dpublic")
        self.assertEqual(screenapp["mode"], "read-only-display")
        self.assertEqual(screenapp["flow"], "WSTA45 -> WSTA43 -> WSTA42")
        self.assertEqual(screenapp["native_public_action"], "none")
        self.assertEqual(screenapp["redacted_result_source"], "WSTA48")

        service = manifest["wifi_uplink_service_boundary"]
        self.assertIn("wpa_failure_detail", service)
        self.assertIn("ctrl_socket_uniqueness", service)
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3394",
            service["obsolete_ramdisk_engines"],
        )


if __name__ == "__main__":
    unittest.main()
