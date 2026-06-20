"""Static checks for V2983 expanded inputcaps touch diagnostics."""

from __future__ import annotations

from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2983_inputcaps_touch_diag.py"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2983_INPUTCAPS_TOUCH_DIAG_SOURCE_BUILD_2026-06-20.md"


class TestNativeInputcapsTouchDiagSourceV2983(unittest.TestCase):
    def test_inputcaps_prints_touch_capabilities_and_runtime_pm(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn('inputcaps.cap.%s=%s', text)
        self.assertIn('inputcaps.decode ev_syn=%d ev_key=%d ev_abs=%d btn_touch=%d', text)
        self.assertIn('mt_slot=%d mt_touch_major=%d mt_x=%d mt_y=%d mt_tracking_id=%d', text)
        self.assertIn('inputcaps_print_device_attr(event_name, "power.runtime_status", "power/runtime_status")', text)
        self.assertIn('inputcaps_print_device_attr(event_name, "power.control", "power/control")', text)
        self.assertIn('ABS_MT_SLOT', text)
        self.assertIn('ABS_MT_TRACKING_ID', text)
        self.assertIn('ABS_MT_POSITION_X', text)
        self.assertIn('ABS_MT_POSITION_Y', text)

    def test_inputcaps_remains_read_only(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertNotIn('EVIOCGRAB', text)
        self.assertNotIn('O_WRONLY', text)
        self.assertNotIn('sendevent', text)
        self.assertNotIn('write_text_file', text)

    def test_builder_and_report_markers(self) -> None:
        builder = BUILDER.read_text(encoding="utf-8")
        self.assertIn('INIT_VERSION = "0.10.62"', builder)
        self.assertIn('INIT_BUILD = "v2983-inputcaps-touch-diag"', builder)
        self.assertIn('boot_linux_v2983_inputcaps_touch_diag.img', builder)
        self.assertIn('inputcaps.cap.%s=%s', builder)
        self.assertIn('power.runtime_status', builder)
        self.assertTrue(REPORT.exists())
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn('V2983', report)
        self.assertIn('inputcaps-touch-diagnostics-candidate', report)


if __name__ == "__main__":
    unittest.main()
