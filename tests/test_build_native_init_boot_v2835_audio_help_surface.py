"""Tests for the V2835 audio help surface boot-image builder."""

from __future__ import annotations

import importlib
import unittest

v2835 = importlib.import_module("build_native_init_boot_v2835_audio_help_surface")


class BuildNativeInitBootV2835AudioHelpSurfaceTest(unittest.TestCase):
    def test_identity_and_paths_are_v2835(self) -> None:
        self.assertEqual(v2835.CYCLE, "V2835")
        self.assertEqual(v2835.INIT_VERSION, "0.10.9")
        self.assertEqual(v2835.INIT_BUILD, "v2835-audio-help-surface")
        self.assertIn("boot_linux_v2835_audio_help_surface.img", str(v2835.BOOT_IMAGE))
        self.assertIn("NATIVE_INIT_V2835_AUDIO_HELP_SURFACE_SOURCE_BUILD", str(v2835.REPORT_PATH))

    def test_report_names_help_surface_delta_and_no_device_action(self) -> None:
        manifest = {
            "decision": v2835.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2835_audio_help_surface.img",
            "boot_sha256": "a" * 64,
            "init_version": v2835.INIT_VERSION,
            "init_build": v2835.INIT_BUILD,
        }
        report = v2835.render_report(manifest, ("-DTEST=1",), ("-DINIT=1",))
        self.assertIn("V2835", report)
        self.assertIn("0.10.9", report)
        self.assertIn("help-surface observability", report)
        self.assertIn("top-level `help` / `cmdmeta` audio usage", report)
        self.assertIn("Device flash: `no`", report)
        self.assertIn("Rollback target remains `v2321-usb-clean-identity-rodata`", report)

    def test_metadata_rewrite_marks_pending_live_validation(self) -> None:
        source = v2835.__loader__.get_source(v2835.__name__)
        self.assertIsNotNone(source)
        assert source is not None

        self.assertIn('"audio-help-surface"', source)
        self.assertIn('"audio-command-table-usage"', source)
        self.assertIn('"audio-screenapp-stages"', source)
        self.assertIn('"pending-live-validation"', source)


if __name__ == "__main__":
    unittest.main()
