"""Tests for the V2831 audio profile screen boot-image builder."""

from __future__ import annotations

import importlib
import unittest

v2831 = importlib.import_module("build_native_init_boot_v2831_audio_profile_screen")


class BuildNativeInitBootV2831AudioProfileScreenTest(unittest.TestCase):
    def test_identity_and_paths_are_v2831(self) -> None:
        self.assertEqual(v2831.CYCLE, "V2831")
        self.assertEqual(v2831.INIT_VERSION, "0.10.7")
        self.assertEqual(v2831.INIT_BUILD, "v2831-audio-profile-screen")
        self.assertIn("boot_linux_v2831_audio_profile_screen.img", str(v2831.BOOT_IMAGE))
        self.assertIn("NATIVE_INIT_V2831_AUDIO_PROFILE_SCREEN_SOURCE_BUILD", str(v2831.REPORT_PATH))

    def test_report_names_profile_screen_delta_and_no_device_action(self) -> None:
        manifest = {
            "decision": v2831.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2831_audio_profile_screen.img",
            "boot_sha256": "a" * 64,
            "init_version": v2831.INIT_VERSION,
            "init_build": v2831.INIT_BUILD,
        }
        report = v2831.render_report(manifest, ("-DTEST=1",), ("-DINIT=1",))
        self.assertIn("V2831", report)
        self.assertIn("0.10.7", report)
        self.assertIn("screenapp audio-profile", report)
        self.assertIn("Device flash: `no`", report)
        self.assertIn("Rollback target remains `v2321-usb-clean-identity-rodata`", report)

    def test_metadata_rewrite_marks_pending_live_validation(self) -> None:
        source = v2831.__loader__.get_source(v2831.__name__)
        self.assertIsNotNone(source)
        assert source is not None

        self.assertIn('"audio-profile-screen"', source)
        self.assertIn('"audio-screenapp-profile"', source)
        self.assertIn('"pending-live-validation"', source)


if __name__ == "__main__":
    unittest.main()
