"""Static checks for V2977 read-only inputscan inventory."""

from __future__ import annotations

from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2977_inputscan_summary.py"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2977_INPUTSCAN_SUMMARY_SOURCE_BUILD_2026-06-20.md"


class TestNativeInputscanSourceV2977(unittest.TestCase):
    def test_inputscan_command_is_registered_read_only(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")
        self.assertIn('static int handle_inputscan(char **argv, int argc)', dispatch)
        self.assertIn('return cmd_inputscan(argv, argc);', dispatch)
        self.assertIn('{ "inputscan", handle_inputscan, "inputscan [eventX]", CMD_NONE, A90_CMD_GROUP_INPUT }', dispatch)
        self.assertIn('inputscan [eventX]', help_text)

    def test_inputscan_classifies_touch_keyboard_and_buttons(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        required = [
            'inputscan.summary events=%u nodes=%u touch_candidates=%u keyboard_candidates=%u button_candidates=%u',
            'inputscan.event=%s name=%s dev=%s node=%s class=%s',
            'BTN_TOUCH',
            'ABS_X',
            'ABS_Y',
            'ABS_MT_POSITION_X',
            'ABS_MT_POSITION_Y',
            'KEY_W',
            'KEY_A',
            'KEY_S',
            'KEY_D',
            'KEY_ENTER',
            'KEY_SPACE',
            'KEY_ESC',
            'KEY_POWER',
            'KEY_VOLUMEUP',
            'KEY_VOLUMEDOWN',
        ]
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertNotIn('EVIOCGRAB', text)
        self.assertNotIn('O_WRONLY', text)

    def test_builder_and_report_capture_v2977_contract(self) -> None:
        builder = BUILDER.read_text(encoding="utf-8")
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn('INIT_VERSION = "0.10.60"', builder)
        self.assertIn('INIT_BUILD = "v2977-inputscan-summary"', builder)
        self.assertIn('inputscan.summary events=', builder)
        self.assertIn('keyboard_candidates=', builder)
        self.assertIn('DOOM input prerequisite', report)
        self.assertIn('Live validation is deferred to V2978', report)
        self.assertIn('No PMIC/backlight/GPIO/regulator/GDSC', report)


if __name__ == "__main__":
    unittest.main()
