"""Tests for the V2853 audio productization marker refresh build wrapper."""

from __future__ import annotations

import importlib
import unittest

v2853 = importlib.import_module("build_native_init_boot_v2853_audio_productization_marker_refresh")


class BuildNativeInitBootV2853AudioProductizationMarkerRefreshTest(unittest.TestCase):
    def test_version_axes_are_distinct(self) -> None:
        self.assertEqual(v2853.CYCLE, "V2853")
        self.assertEqual(v2853.INIT_VERSION, "0.10.17")
        self.assertEqual(v2853.INIT_BUILD, "v2853-audio-productization-marker-refresh")
        self.assertIn("boot_linux_v2853_audio_productization_marker_refresh.img", str(v2853.BOOT_IMAGE))

    def test_configure_retargets_base_builder(self) -> None:
        v2853.configure_base_for_v2853()

        self.assertEqual(v2853.v2851.CYCLE, "V2853")
        self.assertEqual(v2853.v2851.INIT_VERSION, "0.10.17")
        self.assertEqual(v2853.v2851.INIT_BUILD, "v2853-audio-productization-marker-refresh")
        self.assertEqual(v2853.v2851.BOOT_IMAGE, v2853.BOOT_IMAGE)

    def test_report_declares_marker_refresh_without_audio_writes(self) -> None:
        manifest = {
            "decision": v2853.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2853_audio_productization_marker_refresh.img",
            "boot_sha256": "a" * 64,
            "init_version": v2853.INIT_VERSION,
            "init_build": v2853.INIT_BUILD,
            "audio_bundled_setcal": {
                "artifact_count": 15,
                "replay_entry_count": 11,
                "native_manifest_sha256": "b" * 64,
            },
            "audio_productization_marker_refresh": {
                "latest_run": "V2852",
                "latest_version": "0.10.16",
                "latest_tag": "v2851-audio-changelog-productization",
                "changelog_validation_run": "V2852",
                "changelog_screenapp_count": 2,
            },
        }
        report = v2853.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("AUDIO_PRODUCTIZATION_LATEST_*", report)
        self.assertIn("audio.status.feature.changelog.*", report)
        self.assertIn("Latest run: `V2852`", report)
        self.assertIn("Changelog validation run: `V2852`", report)
        self.assertIn("audio-productization-marker-refresh-candidate", report)
        self.assertIn("does not add new mixer, PCM, route, SET-cal, or smart-amp writes", report)


if __name__ == "__main__":
    unittest.main()
