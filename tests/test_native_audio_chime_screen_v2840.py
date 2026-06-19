"""Tests for the V2840 display-only audio chime screen/menu surface."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_APP_C = REPO / "workspace/public/src/native-init/a90_app_audio.c"
AUDIO_APP_H = REPO / "workspace/public/src/native-init/a90_app_audio.h"
CHIME_H = REPO / "workspace/public/src/native-init/a90_audio_chime.h"
MENU_H = REPO / "workspace/public/src/native-init/a90_menu.h"
MENU_C = REPO / "workspace/public/src/native-init/a90_menu.c"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"


class NativeAudioChimeScreenV2840Test(unittest.TestCase):
    def test_chime_defaults_are_shared_with_audio_command(self) -> None:
        header = CHIME_H.read_text(encoding="utf-8")
        audio_app = AUDIO_APP_C.read_text(encoding="utf-8")

        self.assertIn("AUDIO_CHIME_DEFAULT_AMPLITUDE_MILLI 80", header)
        self.assertIn("AUDIO_CHIME_DEFAULT_DURATION_MS 1200", header)
        self.assertIn("AUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT 0", header)
        self.assertIn('#include "a90_audio_chime.h"', audio_app)
        self.assertIn("AUDIO_CHIME_DEFAULT_AMPLITUDE_MILLI", audio_app)
        self.assertIn("AUDIO_CHIME_DEFAULT_DURATION_MS", audio_app)
        self.assertIn("AUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT", audio_app)

    def test_audio_chime_screen_is_display_only_status_surface(self) -> None:
        audio_app = AUDIO_APP_C.read_text(encoding="utf-8")
        header = AUDIO_APP_H.read_text(encoding="utf-8")

        for marker in [
            "int a90_app_audio_draw_chime(void)",
            "COMMAND audio chime --execute",
            "DEFAULT %dmilli %dms LISTEN",
            "PROFILE %s -> audio play",
            "BOOT AUTOPLAY %s BLOCKS_BOOT=0",
            "VALIDATED V2839 PCM ROUTE SETCAL OK",
            "ROLLBACK v2321 SELFTEST fail=0",
            "NO SMART-AMP BOOST/SP BYPASS WRITE",
            "DISPLAY ONLY - MANUAL COMMAND",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, audio_app)

        self.assertIn("int a90_app_audio_draw_chime(void);", header)

        chime_start = audio_app.index("int a90_app_audio_draw_chime(void)")
        chime_block = audio_app[chime_start:]
        for forbidden in [
            "open(",
            "ioctl(",
            "audio_route_write",
            "audio_setcal",
            "audio_play",
            "SNDRV_CTL_IOCTL_ELEM_WRITE",
            "tinymix",
            "tinyplay",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, chime_block)

    def test_chime_is_reachable_from_menu_and_screenapp(self) -> None:
        menu_h = MENU_H.read_text(encoding="utf-8")
        menu_c = MENU_C.read_text(encoding="utf-8")
        menu_apps = MENU_APPS.read_text(encoding="utf-8")
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")

        for marker in [
            "SCREEN_MENU_AUDIO_CHIME",
            "SCREEN_APP_AUDIO_CHIME",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, menu_h)

        for marker in [
            '{ "CHIME",        "MANUAL SAFE PRESET",  SCREEN_MENU_AUDIO_CHIME,   SCREEN_MENU_PAGE_AUDIO }',
            "case SCREEN_MENU_AUDIO_CHIME:",
            "return SCREEN_APP_AUDIO_CHIME;",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, menu_c)

        self.assertIn("state->active_app == SCREEN_APP_AUDIO_CHIME", menu_apps)
        self.assertIn("a90_app_audio_draw_chime();", menu_apps)
        self.assertIn('strcmp(app, "audio-chime") == 0 || strcmp(app, "chime") == 0', dispatch)
        self.assertIn("screenapp.title=AUDIO CHIME", dispatch)
        self.assertIn("a90_app_audio_draw_chime()", dispatch)
        self.assertIn("audio-map|audio-chime", dispatch)
        self.assertIn("audio-map|audio-chime", help_text)


if __name__ == "__main__":
    unittest.main()
