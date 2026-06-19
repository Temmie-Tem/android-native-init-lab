"""Tests for the V2824 audio screenapp route-map boot-image builder."""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path

v2824 = importlib.import_module("build_native_init_boot_v2824_audio_screenapp_map")


class BuildNativeInitBootV2824AudioScreenappMapTest(unittest.TestCase):
    def test_identity_and_paths_are_v2824(self) -> None:
        self.assertEqual(v2824.CYCLE, "V2824")
        self.assertEqual(v2824.INIT_VERSION, "0.10.4")
        self.assertEqual(v2824.INIT_BUILD, "v2824-audio-screenapp-map")
        self.assertIn("boot_linux_v2824_audio_screenapp_map.img", str(v2824.BOOT_IMAGE))
        self.assertIn("NATIVE_INIT_V2824_AUDIO_SCREENAPP_MAP_SOURCE_BUILD", str(v2824.REPORT_PATH))

    def test_report_names_map_screen_and_no_device_action(self) -> None:
        manifest = {
            "decision": v2824.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2824_audio_screenapp_map.img",
            "boot_sha256": "a" * 64,
            "init_version": v2824.INIT_VERSION,
            "init_build": v2824.INIT_BUILD,
        }
        report = v2824.render_report(manifest, ("-DTEST=1",), ("-DINIT=1",))
        self.assertIn("V2824", report)
        self.assertIn("0.10.4", report)
        self.assertIn("screenapp audio-map", report)
        self.assertIn("speaker/route map", report)
        self.assertIn("Device flash: `no`", report)
        self.assertIn("Rollback target remains `v2321-usb-clean-identity-rodata`", report)

    def test_metadata_rewrite_marks_pending_live_validation(self) -> None:
        source = Path(v2824.__file__).read_text(encoding="utf-8")

        self.assertIn('"audio-screenapp-route-map"', source)
        self.assertIn('"pending-live-validation"', source)
        self.assertIn("display-only screenapp audio-map surface", source)


if __name__ == "__main__":
    unittest.main()
