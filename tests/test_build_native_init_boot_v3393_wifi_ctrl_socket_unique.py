"""Regression tests for V3393 Wi-Fi ctrl socket uniqueness source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3393_wifi_ctrl_socket_unique")


class BuildNativeInitBootV3393WifiCtrlSocketUniqueTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3393")
        self.assertEqual(builder.INIT_VERSION, "0.11.149")
        self.assertEqual(builder.INIT_BUILD, "v3393-wifi-ctrl-socket-unique")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3393-wifi-ctrl-socket-unique",
            b"0.11.149",
            b"a90-wifi-%ld-%ld-%lu",
            b"/tmp/a90-wifi/sockets",
            b"connect_wpa_complete_wait_rc=",
            b"connect_wpa_monitor_last_event=",
            b"secret_values_logged=0",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3392_identity(self) -> None:
        text = builder._rewrite_v3393_text(
            "V3392 0.11.148 v3392-wifi-tmp-ctrl-dir "
            "a90-doomgeneric-v3392"
        )
        self.assertIn("V3393", text)
        self.assertIn("0.11.149", text)
        self.assertIn("v3393-wifi-ctrl-socket-unique", text)
        self.assertIn("a90-doomgeneric-v3393", text)
        self.assertNotIn("v3392", text)
        self.assertNotIn("wifi-tmp-ctrl-dir", text)

    def test_manifest_records_socket_uniqueness_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_uplink_service_boundary"]
        uniqueness = service["ctrl_socket_uniqueness"]

        self.assertEqual(uniqueness["strategy"], "pid-monotonic-time-plus-process-local-sequence")
        self.assertEqual(
            uniqueness["bug_target"],
            "avoid-EADDRINUSE-when-monitor-and-request-sockets-bind-same-ms",
        )
        self.assertEqual(uniqueness["monitor_socket"], "persistent-ATTACH")
        self.assertEqual(uniqueness["request_socket"], "one-shot-control-command")
        self.assertIn("tmp_ctrl_dir", service)
        self.assertIn("wpa_handshake_diagnostics", service)
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3392",
            service["obsolete_ramdisk_engines"],
        )


if __name__ == "__main__":
    unittest.main()
