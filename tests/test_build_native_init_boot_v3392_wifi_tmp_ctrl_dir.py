"""Regression tests for V3392 Wi-Fi tmp ctrl-dir source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3392_wifi_tmp_ctrl_dir")


class BuildNativeInitBootV3392WifiTmpCtrlDirTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3392")
        self.assertEqual(builder.INIT_VERSION, "0.11.148")
        self.assertEqual(builder.INIT_BUILD, "v3392-wifi-tmp-ctrl-dir")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3392-wifi-tmp-ctrl-dir",
            b"0.11.148",
            b"/tmp/a90-wifi/sockets",
            b"connect_wpa_complete_wait_rc=",
            b"connect_wpa_monitor_last_event=",
            b"wifi-config-enospc-inplace-fallback",
            b"secret_values_logged=0",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3391_identity(self) -> None:
        text = builder._rewrite_v3392_text(
            "V3391 0.11.147 v3391-wifi-wpa-handshake-diagnostics "
            "a90-doomgeneric-v3391"
        )
        self.assertIn("V3392", text)
        self.assertIn("0.11.148", text)
        self.assertIn("v3392-wifi-tmp-ctrl-dir", text)
        self.assertIn("a90-doomgeneric-v3392", text)
        self.assertNotIn("v3391", text)
        self.assertNotIn("wifi-wpa-handshake-diagnostics", text)

    def test_manifest_records_tmp_ctrl_dir_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]
        tmp_ctrl = service["tmp_ctrl_dir"]

        self.assertEqual(tmp_ctrl["strategy"], "move-wpa-control-socket-dir-off-full-cache")
        self.assertEqual(tmp_ctrl["ctrl_root"], "/tmp/a90-wifi")
        self.assertEqual(tmp_ctrl["ctrl_dir"], "/tmp/a90-wifi/sockets")
        self.assertEqual(tmp_ctrl["supplicant_config_path"], "unchanged-/cache/a90-wifi/wpa_supplicant.conf")
        self.assertEqual(tmp_ctrl["cache_space_dependency"], "config-file-only")
        self.assertIn("wpa_handshake_diagnostics", service)
        self.assertIn("cache_enospc_fallback", service)
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3391",
            service["obsolete_ramdisk_engines"],
        )


if __name__ == "__main__":
    unittest.main()
