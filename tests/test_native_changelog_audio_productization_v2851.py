"""Tests for the V2851 native audio changelog productization surface."""

from __future__ import annotations

from pathlib import Path
import re
import unittest

REPO = Path(__file__).resolve().parents[1]
CHANGELOG_C = REPO / "workspace/public/src/native-init/a90_changelog.c"
CHANGELOG_H = REPO / "workspace/public/src/native-init/a90_changelog.h"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"


class NativeChangelogAudioProductizationV2851Test(unittest.TestCase):
    def test_changelog_capacity_covers_existing_history_and_audio_entries(self) -> None:
        header = CHANGELOG_H.read_text(encoding="utf-8")
        source = CHANGELOG_C.read_text(encoding="utf-8")
        match = re.search(r"#define A90_CHANGELOG_MAX_ENTRIES (\d+)", header)
        self.assertIsNotNone(match)
        max_entries = int(match.group(1))
        entry_count = source.count('ENTRY("')

        self.assertGreaterEqual(max_entries, 128)
        self.assertGreaterEqual(max_entries, entry_count)
        self.assertGreater(entry_count, 110)

    def test_latest_audio_productization_entries_are_first_class(self) -> None:
        source = CHANGELOG_C.read_text(encoding="utf-8")
        expected = [
            ("0.10.15 v2849", "AUDIO STATUS PRODUCTIZATION"),
            ("0.10.14 v2847", "AUDIO STOP EXECUTE"),
            ("0.10.13 v2845", "AUDIO BOOT CHIME"),
            ("0.10.12 v2843", "AUDIO BUNDLED SETCAL"),
            ("0.10.11 v2840", "AUDIO CHIME SCREEN"),
            ("0.10.10 v2838", "AUDIO CHIME PRESET"),
            ("0.10.9 v2835", "AUDIO HELP SURFACE"),
            ("0.10.0 v2812", "AUDIO CORE PROMOTION"),
        ]
        first_audio = source.find('ENTRY("0.10.15 v2849"')
        first_legacy = source.find('ENTRY("0.9.68 v724"')
        self.assertNotEqual(first_audio, -1)
        self.assertNotEqual(first_legacy, -1)
        self.assertLess(first_audio, first_legacy)

        for label, summary in expected:
            with self.subTest(label=label):
                self.assertIn(f'ENTRY("{label}", "{summary}"', source)

    def test_screenapp_exposes_about_changelog_directly(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")
        usage = "screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status|audio-profile|audio-stages|audio-map|audio-chime|about-version|about-changelog]"

        self.assertIn(usage, dispatch)
        self.assertIn(usage, help_text)
        self.assertIn('strcmp(app, "about-version") == 0 || strcmp(app, "version") == 0', dispatch)
        self.assertIn('screenapp.title=ABOUT / VERSION', dispatch)
        self.assertIn('a90_app_about_draw_version()', dispatch)
        self.assertIn('strcmp(app, "about-changelog") == 0 || strcmp(app, "changelog") == 0', dispatch)
        self.assertIn('screenapp.title=ABOUT / CHANGELOG', dispatch)
        self.assertIn('a90_app_about_draw_changelog()', dispatch)


if __name__ == "__main__":
    unittest.main()
