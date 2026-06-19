"""Tests for the V2822 audio screenapp status boot-image builder."""

from __future__ import annotations

import importlib
import unittest

v2822 = importlib.import_module("build_native_init_boot_v2822_audio_screenapp_status")


class BuildNativeInitBootV2822AudioScreenappStatusTest(unittest.TestCase):
    def test_identity_and_paths_are_v2822(self) -> None:
        self.assertEqual(v2822.CYCLE, "V2822")
        self.assertEqual(v2822.INIT_VERSION, "0.10.3")
        self.assertEqual(v2822.INIT_BUILD, "v2822-audio-screenapp-status")
        self.assertIn("boot_linux_v2822_audio_screenapp_status.img", str(v2822.BOOT_IMAGE))
        self.assertIn("NATIVE_INIT_V2822_AUDIO_SCREENAPP_STATUS_SOURCE_BUILD", str(v2822.REPORT_PATH))

    def test_report_names_display_only_screen_and_no_device_action(self) -> None:
        manifest = {
            "decision": v2822.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2822_audio_screenapp_status.img",
            "boot_sha256": "8" * 64,
            "init_version": v2822.INIT_VERSION,
            "init_build": v2822.INIT_BUILD,
        }
        report = v2822.render_report(manifest, ("-DTEST=1",), ("-DINIT=1",))
        self.assertIn("V2822", report)
        self.assertIn("0.10.3", report)
        self.assertIn("screenapp audio-status", report)
        self.assertIn("display-only", report)
        self.assertIn("Device flash: `no`", report)
        self.assertIn("Rollback target remains `v2321-usb-clean-identity-rodata`", report)

    def test_metadata_rewrite_marks_pending_live_validation(self) -> None:
        from pathlib import Path
        source = Path(v2822.__file__).read_text(encoding="utf-8")

        self.assertIn('"audio-screenapp-status"', source)
        self.assertIn('"pending-live-validation"', source)
        self.assertIn("display-only screenapp audio-status surface", source)


if __name__ == "__main__":
    unittest.main()
