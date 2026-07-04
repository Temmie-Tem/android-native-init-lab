"""Regression tests for V3385 Wi-Fi service-boundary source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3385_wifi_service_boundary")


class BuildNativeInitBootV3385WifiServiceBoundaryTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3385")
        self.assertEqual(builder.INIT_VERSION, "0.11.141")
        self.assertEqual(builder.INIT_BUILD, "v3385-wifi-service-boundary")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3385-wifi-service-boundary",
            b"0.11.141",
            b"a90-native-wifi-service-v1",
            b"wifi service [status|start|stop|once]",
            b"wifi-service-start-pass",
            b"wifi-service-once-pass",
            b"wifi-service-status-running",
            b"owner=native-init",
            b"raw_results_redacted=1",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3384_identity(self) -> None:
        text = builder._rewrite_v3385_text(
            "V3384 0.11.140 v3384-server-distro-hardware-contract "
            "server-distro-stage0-hardware-contract a90-doomgeneric-v3384"
        )
        self.assertIn("V3385", text)
        self.assertIn("0.11.141", text)
        self.assertIn("v3385-wifi-service-boundary", text)
        self.assertIn("wifi-service-boundary", text)
        self.assertIn("a90-doomgeneric-v3385", text)
        self.assertNotIn("v3384", text)
        self.assertNotIn("server-distro-stage0-hardware-contract", text)

    def test_manifest_names_request_response_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["wifi_service_boundary"]

        self.assertEqual(service["version"], "a90-native-wifi-service-v1")
        self.assertEqual(service["request_file"], "request")
        self.assertEqual(service["response_file"], "response")
        self.assertEqual(service["supported_ops"], ["status", "scan"])
        self.assertEqual(service["owner"], "native-init")
        self.assertIn("connect", service["denied_in_this_rung"])
        self.assertIn(
            "bin/a90_doomgeneric_private_engine_v3384",
            service["obsolete_ramdisk_engines"],
        )


if __name__ == "__main__":
    unittest.main()
