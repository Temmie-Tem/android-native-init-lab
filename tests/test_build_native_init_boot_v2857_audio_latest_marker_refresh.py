"""Tests for the V2857 audio latest marker refresh build wrapper."""

from __future__ import annotations

import importlib
import unittest

v2857 = importlib.import_module("build_native_init_boot_v2857_audio_latest_marker_refresh")


class BuildNativeInitBootV2857AudioLatestMarkerRefreshTest(unittest.TestCase):
    def test_version_axes_are_distinct(self) -> None:
        self.assertEqual(v2857.CYCLE, "V2857")
        self.assertEqual(v2857.INIT_VERSION, "0.10.18")
        self.assertEqual(v2857.INIT_BUILD, "v2857-audio-latest-marker-refresh")
        self.assertIn("boot_linux_v2857_audio_latest_marker_refresh.img", str(v2857.BOOT_IMAGE))

    def test_configure_retargets_base_builder(self) -> None:
        v2857.configure_base_for_v2857()

        self.assertEqual(v2857.v2851.CYCLE, "V2857")
        self.assertEqual(v2857.v2851.INIT_VERSION, "0.10.18")
        self.assertEqual(v2857.v2851.INIT_BUILD, "v2857-audio-latest-marker-refresh")
        self.assertEqual(v2857.v2851.BOOT_IMAGE, v2857.BOOT_IMAGE)

    def test_report_declares_latest_marker_refresh_without_audio_writes(self) -> None:
        manifest = {
            "decision": v2857.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2857_audio_latest_marker_refresh.img",
            "boot_sha256": "a" * 64,
            "init_version": v2857.INIT_VERSION,
            "init_build": v2857.INIT_BUILD,
            "audio_bundled_setcal": {
                "artifact_count": 15,
                "replay_entry_count": 11,
                "native_manifest_sha256": "b" * 64,
            },
            "audio_productization_marker_refresh": {
                "latest_run": "V2856",
                "latest_version": "0.10.17",
                "latest_tag": "v2853-audio-productization-marker-refresh",
                "chime_validation_run": "V2855",
                "stop_execute_validation_run": "V2856",
                "changelog_validation_run": "V2852",
            },
        }
        report = v2857.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("AUDIO_PRODUCTIZATION_LATEST_*", report)
        self.assertIn("AUDIO_CHIME_VALIDATION_RUN", report)
        self.assertIn("Latest run: `V2856`", report)
        self.assertIn("Chime validation run: `V2855`", report)
        self.assertIn("Stop-execute validation run: `V2856`", report)
        self.assertIn("does not add new mixer, PCM, route, SET-cal, or smart-amp writes", report)


if __name__ == "__main__":
    unittest.main()
