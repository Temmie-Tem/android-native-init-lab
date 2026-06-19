"""Tests for the V2833 audio stage screen boot-image builder."""

from __future__ import annotations

import importlib
import unittest

v2833 = importlib.import_module("build_native_init_boot_v2833_audio_stage_screen")


class BuildNativeInitBootV2833AudioStageScreenTest(unittest.TestCase):
    def test_identity_and_paths_are_v2833(self) -> None:
        self.assertEqual(v2833.CYCLE, "V2833")
        self.assertEqual(v2833.INIT_VERSION, "0.10.8")
        self.assertEqual(v2833.INIT_BUILD, "v2833-audio-stage-screen")
        self.assertIn("boot_linux_v2833_audio_stage_screen.img", str(v2833.BOOT_IMAGE))
        self.assertIn("NATIVE_INIT_V2833_AUDIO_STAGE_SCREEN_SOURCE_BUILD", str(v2833.REPORT_PATH))

    def test_report_names_profile_screen_delta_and_no_device_action(self) -> None:
        manifest = {
            "decision": v2833.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2833_audio_stage_screen.img",
            "boot_sha256": "a" * 64,
            "init_version": v2833.INIT_VERSION,
            "init_build": v2833.INIT_BUILD,
        }
        report = v2833.render_report(manifest, ("-DTEST=1",), ("-DINIT=1",))
        self.assertIn("V2833", report)
        self.assertIn("0.10.8", report)
        self.assertIn("screenapp audio-stages", report)
        self.assertIn("Device flash: `no`", report)
        self.assertIn("Rollback target remains `v2321-usb-clean-identity-rodata`", report)

    def test_metadata_rewrite_marks_pending_live_validation(self) -> None:
        source = v2833.__loader__.get_source(v2833.__name__)
        self.assertIsNotNone(source)
        assert source is not None

        self.assertIn('"audio-stage-screen"', source)
        self.assertIn('"audio-screenapp-stages"', source)
        self.assertIn('"pending-live-validation"', source)


if __name__ == "__main__":
    unittest.main()
