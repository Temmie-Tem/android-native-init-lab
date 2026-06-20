"""Static checks for V2981 bounded readinput timeout source build."""

from __future__ import annotations

from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2981_readinput_timeout.py"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2981_READINPUT_TIMEOUT_SOURCE_BUILD_2026-06-20.md"


class TestNativeReadinputTimeoutSourceV2981(unittest.TestCase):
    def test_readinput_timeout_is_bounded_and_read_only(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn('usage: readinput <eventX> [count] [timeout_ms]', text)
        self.assertIn('readinput: timeout_ms=%d', text)
        self.assertIn('readinput: timeout after %dms captured=%d/%d', text)
        self.assertIn('return -ETIMEDOUT;', text)
        self.assertIn('poll(fds, 2, poll_timeout)', text)
        self.assertIn('deadline_ms = monotonic_millis() + timeout_ms;', text)
        self.assertNotIn('EVIOCGRAB', text)
        self.assertNotIn('O_WRONLY', text)
        self.assertNotIn('sendevent', text)

    def test_help_and_builder_markers(self) -> None:
        help_text = HELP.read_text(encoding="utf-8")
        dispatch = DISPATCH.read_text(encoding="utf-8")
        builder = BUILDER.read_text(encoding="utf-8")
        self.assertIn('readinput <eventX> [count] [timeout_ms]', help_text)
        self.assertIn('readinput <eventX> [count] [timeout_ms]', dispatch)
        self.assertIn('INIT_VERSION = "0.10.61"', builder)
        self.assertIn('INIT_BUILD = "v2981-readinput-timeout"', builder)
        self.assertIn('boot_linux_v2981_readinput_timeout.img', builder)
        self.assertIn('readinput: timeout after', builder)

    def test_report_written_by_builder(self) -> None:
        self.assertTrue(REPORT.exists())
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn('V2981', text)
        self.assertIn('bounded `readinput', text)
        self.assertIn('No PMIC/backlight/GPIO/regulator/GDSC', text)


if __name__ == "__main__":
    unittest.main()
