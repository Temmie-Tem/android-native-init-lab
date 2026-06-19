"""Tests for the V2849 audio status productization build wrapper."""

from __future__ import annotations

import importlib
import unittest

v2849 = importlib.import_module("build_native_init_boot_v2849_audio_status_productization")


class BuildNativeInitBootV2849AudioStatusProductizationTest(unittest.TestCase):
    def test_version_axes_are_distinct(self) -> None:
        self.assertEqual(v2849.CYCLE, "V2849")
        self.assertEqual(v2849.INIT_VERSION, "0.10.15")
        self.assertEqual(v2849.INIT_BUILD, "v2849-audio-status-productization")
        self.assertIn("boot_linux_v2849_audio_status_productization.img", str(v2849.BOOT_IMAGE))

    def test_configure_retargets_base_builder(self) -> None:
        v2849.configure_base_for_v2849()

        self.assertEqual(v2849.v2847.CYCLE, "V2849")
        self.assertEqual(v2849.v2847.INIT_VERSION, "0.10.15")
        self.assertEqual(v2849.v2847.INIT_BUILD, "v2849-audio-status-productization")
        self.assertEqual(v2849.v2847.BOOT_IMAGE, v2849.BOOT_IMAGE)

    def test_report_declares_read_only_productization_markers(self) -> None:
        manifest = {
            "decision": v2849.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2849_audio_status_productization.img",
            "boot_sha256": "a" * 64,
            "init_version": v2849.INIT_VERSION,
            "init_build": v2849.INIT_BUILD,
            "audio_bundled_setcal": {
                "artifact_count": 15,
                "replay_entry_count": 11,
                "native_manifest_sha256": "b" * 64,
            },
            "audio_boot_chime": {
                "enabled": True,
            },
            "audio_stop_execute": {
                "execute_supported": True,
            },
            "audio_status_productization": {
                "version": 1,
                "latest_run": "V2848",
                "latest_version": "0.10.14",
                "latest_tag": "v2847-audio-stop-execute",
                "boot_chime_validation_run": "V2846",
                "stop_execute_validation_run": "V2848",
                "stop_execute_scope": "core-route-reset",
                "live_validation": "pending",
            },
        }
        report = v2849.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("audio.status.productization.*", report)
        self.assertIn("screenapp audio-status", report)
        self.assertIn("Latest proven run: `V2848`", report)
        self.assertIn("Boot-chime validation: `V2846`", report)
        self.assertIn("Stop-execute validation: `V2848`", report)
        self.assertIn("read-only status and display labels only", report)
        self.assertIn("audio-productization-status-candidate", report)


if __name__ == "__main__":
    unittest.main()
