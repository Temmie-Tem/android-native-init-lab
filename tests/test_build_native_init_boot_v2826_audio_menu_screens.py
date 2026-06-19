"""Tests for the V2826 audio menu screens boot-image builder."""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path

v2826 = importlib.import_module("build_native_init_boot_v2826_audio_menu_screens")


class BuildNativeInitBootV2826AudioMenuScreensTest(unittest.TestCase):
    def test_identity_and_paths_are_v2826(self) -> None:
        self.assertEqual(v2826.CYCLE, "V2826")
        self.assertEqual(v2826.INIT_VERSION, "0.10.5")
        self.assertEqual(v2826.INIT_BUILD, "v2826-audio-menu-screens")
        self.assertIn("boot_linux_v2826_audio_menu_screens.img", str(v2826.BOOT_IMAGE))
        self.assertIn("NATIVE_INIT_V2826_AUDIO_MENU_SCREENS_SOURCE_BUILD", str(v2826.REPORT_PATH))

    def test_report_names_menu_screens_and_no_device_action(self) -> None:
        manifest = {
            "decision": v2826.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2826_audio_menu_screens.img",
            "boot_sha256": "a" * 64,
            "init_version": v2826.INIT_VERSION,
            "init_build": v2826.INIT_BUILD,
        }
        report = v2826.render_report(manifest, ("-DTEST=1",), ("-DINIT=1",))
        self.assertIn("V2826", report)
        self.assertIn("0.10.5", report)
        self.assertIn("APPS / AUDIO", report)
        self.assertIn("Device flash: `no`", report)
        self.assertIn("Rollback target remains `v2321-usb-clean-identity-rodata`", report)

    def test_metadata_rewrite_marks_pending_live_validation(self) -> None:
        source = Path(v2826.__file__).read_text(encoding="utf-8")

        self.assertIn('"audio-menu-screens"', source)
        self.assertIn('"v2824-audio-screenapp-map"', source)
        self.assertIn('"pending-live-validation"', source)


if __name__ == "__main__":
    unittest.main()
