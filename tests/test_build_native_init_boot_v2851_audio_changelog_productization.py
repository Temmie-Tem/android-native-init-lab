"""Tests for the V2851 audio changelog productization build wrapper."""

from __future__ import annotations

import importlib
import unittest

v2851 = importlib.import_module("build_native_init_boot_v2851_audio_changelog_productization")


class BuildNativeInitBootV2851AudioChangelogProductizationTest(unittest.TestCase):
    def test_version_axes_are_distinct(self) -> None:
        self.assertEqual(v2851.CYCLE, "V2851")
        self.assertEqual(v2851.INIT_VERSION, "0.10.16")
        self.assertEqual(v2851.INIT_BUILD, "v2851-audio-changelog-productization")
        self.assertIn("boot_linux_v2851_audio_changelog_productization.img", str(v2851.BOOT_IMAGE))

    def test_configure_retargets_base_builder(self) -> None:
        v2851.configure_base_for_v2851()

        self.assertEqual(v2851.v2849.CYCLE, "V2851")
        self.assertEqual(v2851.v2849.INIT_VERSION, "0.10.16")
        self.assertEqual(v2851.v2849.INIT_BUILD, "v2851-audio-changelog-productization")
        self.assertEqual(v2851.v2849.BOOT_IMAGE, v2851.BOOT_IMAGE)

    def test_report_declares_changelog_and_about_screen_surface(self) -> None:
        manifest = {
            "decision": v2851.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2851_audio_changelog_productization.img",
            "boot_sha256": "a" * 64,
            "init_version": v2851.INIT_VERSION,
            "init_build": v2851.INIT_BUILD,
            "audio_bundled_setcal": {
                "artifact_count": 15,
                "replay_entry_count": 11,
                "native_manifest_sha256": "b" * 64,
            },
            "audio_changelog_productization": {
                "version": 1,
                "latest_run": "V2850",
                "latest_version": "0.10.15",
                "latest_tag": "v2849-audio-status-productization",
                "direct_screenapps": ["about-version", "about-changelog"],
                "live_validation": "pending",
            },
        }
        report = v2851.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("latest `0.10.x` audio-core", report)
        self.assertIn("screenapp about-version", report)
        self.assertIn("screenapp about-changelog", report)
        self.assertIn("Latest changelog run: `V2850`", report)
        self.assertIn("audio-productization-changelog-candidate", report)
        self.assertIn("does not add new mixer, PCM, route, SET-cal, or smart-amp writes", report)


if __name__ == "__main__":
    unittest.main()
