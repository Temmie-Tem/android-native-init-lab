"""Tests for the V2840 audio chime screen boot-image builder."""

from __future__ import annotations

import importlib
import unittest

v2840 = importlib.import_module("build_native_init_boot_v2840_audio_chime_screen")


class BuildNativeInitBootV2840AudioChimeScreenTest(unittest.TestCase):
    def test_identity_and_paths_are_v2840(self) -> None:
        self.assertEqual(v2840.CYCLE, "V2840")
        self.assertEqual(v2840.INIT_VERSION, "0.10.11")
        self.assertEqual(v2840.INIT_BUILD, "v2840-audio-chime-screen")
        self.assertIn("boot_linux_v2840_audio_chime_screen.img", str(v2840.BOOT_IMAGE))
        self.assertIn("NATIVE_INIT_V2840_AUDIO_CHIME_SCREEN_SOURCE_BUILD", str(v2840.REPORT_PATH))

    def test_report_names_screen_delta_and_no_autoplay_boundary(self) -> None:
        manifest = {
            "decision": v2840.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2840_audio_chime_screen.img",
            "boot_sha256": "a" * 64,
            "init_version": v2840.INIT_VERSION,
            "init_build": v2840.INIT_BUILD,
        }
        report = v2840.render_report(manifest, ("-DTEST=1",), ("-DINIT=1",))
        self.assertIn("V2840", report)
        self.assertIn("0.10.11", report)
        self.assertIn("screenapp audio-chime", report)
        self.assertIn("APPS/AUDIO `CHIME`", report)
        self.assertIn("BOOT AUTOPLAY DISABLED BLOCKS_BOOT=0", report)
        self.assertIn("does not run playback", report)
        self.assertIn("Device flash: `no`", report)

    def test_metadata_rewrite_marks_chime_screen_candidate(self) -> None:
        source = v2840.__loader__.get_source(v2840.__name__)
        self.assertIsNotNone(source)
        assert source is not None

        self.assertIn('"audio-chime-screen"', source)
        self.assertIn('"audio-chime-menu-entry"', source)
        self.assertIn('"audio-chime-screenapp"', source)
        self.assertIn('"audio-chime-boot-autoplay-disabled"', source)
        self.assertIn('"audio-productization-candidate"', source)
        self.assertIn('"pending-live-validation"', source)


if __name__ == "__main__":
    unittest.main()
