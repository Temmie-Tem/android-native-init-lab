"""Static checks for V2985 DOOM keyboard fallback key capability surface."""

from __future__ import annotations

from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2985_doom_keyboard_caps.py"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2985_DOOM_KEYBOARD_CAPS_SOURCE_BUILD_2026-06-20.md"


class TestNativeDoomKeyboardCapsSourceV2985(unittest.TestCase):
    def test_inputcaps_decodes_doom_keyboard_keys(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        required = [
            "key_w=%d",
            "key_a=%d",
            "key_s=%d",
            "key_d=%d",
            "key_up=%d",
            "key_down=%d",
            "key_left=%d",
            "key_right=%d",
            "key_enter=%d",
            "key_space=%d",
            "key_esc=%d",
            "key_leftctrl=%d",
            "key_rightctrl=%d",
            "key_leftshift=%d",
            "key_rightshift=%d",
            "KEY_W",
            "KEY_A",
            "KEY_S",
            "KEY_D",
            "KEY_UP",
            "KEY_DOWN",
            "KEY_LEFT",
            "KEY_RIGHT",
            "KEY_ENTER",
            "KEY_SPACE",
            "KEY_ESC",
        ]
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_inputcaps_keyboard_surface_remains_read_only(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn('inputcaps_print_capability(event_name, "key", key_bitmap, sizeof(key_bitmap))', text)
        self.assertNotIn("EVIOCGRAB", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("write_text_file", text)

    def test_builder_and_report_capture_v2985_contract(self) -> None:
        builder = BUILDER.read_text(encoding="utf-8")
        self.assertIn('INIT_VERSION = "0.10.63"', builder)
        self.assertIn('INIT_BUILD = "v2985-doom-keyboard-caps"', builder)
        self.assertIn("boot_linux_v2985_doom_keyboard_caps.img", builder)
        self.assertIn("doom-keyboard-fallback-caps-candidate", builder)
        self.assertIn("pending-usb-keyboard-live-validation", builder)
        self.assertIn("inputcaps.decode key_w=", builder)
        self.assertTrue(REPORT.exists())
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("V2984 live diagnostics proved", report)
        self.assertIn("USB-keyboard fallback", report)
        self.assertIn("No PMIC/backlight/GPIO/regulator/GDSC", report)


if __name__ == "__main__":
    unittest.main()
