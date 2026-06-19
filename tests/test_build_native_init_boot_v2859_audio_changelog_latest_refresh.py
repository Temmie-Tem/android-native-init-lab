"""Tests for the V2859 audio changelog latest-refresh build wrapper."""

from __future__ import annotations

import importlib
import unittest

v2859 = importlib.import_module("build_native_init_boot_v2859_audio_changelog_latest_refresh")


class BuildNativeInitBootV2859AudioChangelogLatestRefreshTest(unittest.TestCase):
    def test_version_axes_are_distinct(self) -> None:
        self.assertEqual(v2859.CYCLE, "V2859")
        self.assertEqual(v2859.INIT_VERSION, "0.10.19")
        self.assertEqual(v2859.INIT_BUILD, "v2859-audio-changelog-latest-refresh")
        self.assertIn("boot_linux_v2859_audio_changelog_latest_refresh.img", str(v2859.BOOT_IMAGE))

    def test_configure_retargets_base_builder(self) -> None:
        v2859.configure_base_for_v2859()

        self.assertEqual(v2859.v2851.CYCLE, "V2859")
        self.assertEqual(v2859.v2851.INIT_VERSION, "0.10.19")
        self.assertEqual(v2859.v2851.INIT_BUILD, "v2859-audio-changelog-latest-refresh")
        self.assertEqual(v2859.v2851.BOOT_IMAGE, v2859.BOOT_IMAGE)

    def test_report_declares_latest_changelog_entries_and_safety(self) -> None:
        manifest = {
            "decision": v2859.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2859_audio_changelog_latest_refresh.img",
            "boot_sha256": "a" * 64,
            "init_version": v2859.INIT_VERSION,
            "init_build": v2859.INIT_BUILD,
            "audio_bundled_setcal": {
                "artifact_count": 15,
                "replay_entry_count": 11,
                "native_manifest_sha256": "b" * 64,
            },
            "audio_changelog_latest_refresh": {
                "latest_run": "V2860",
                "latest_version": "0.10.19",
                "latest_tag": "v2859-audio-changelog-latest-refresh",
                "changelog_validation_run": "V2860",
                "entries_added": ["0.10.19 v2859", "0.10.18 v2857"],
            },
        }
        report = v2859.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("0.10.16` through `0.10.19", report)
        self.assertIn("Latest run: `V2860`", report)
        self.assertIn("0.10.19 v2859, 0.10.18 v2857", report)
        self.assertIn("does not add new mixer, PCM, route, SET-cal, or smart-amp writes", report)


if __name__ == "__main__":
    unittest.main()
