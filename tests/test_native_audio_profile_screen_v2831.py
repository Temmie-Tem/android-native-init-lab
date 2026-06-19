"""Tests for the V2831 display-only audio profile screen surface."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_APP_C = REPO / "workspace/public/src/native-init/a90_app_audio.c"
AUDIO_APP_H = REPO / "workspace/public/src/native-init/a90_app_audio.h"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
MENU_C = REPO / "workspace/public/src/native-init/a90_menu.c"
MENU_H = REPO / "workspace/public/src/native-init/a90_menu.h"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"


class NativeAudioProfileScreenV2831Test(unittest.TestCase):
    def test_profile_screen_is_display_only_and_profile_backed(self) -> None:
        source = AUDIO_APP_C.read_text(encoding="utf-8")
        header = AUDIO_APP_H.read_text(encoding="utf-8")

        for marker in [
            "int a90_app_audio_draw_profile(void)",
            "int a90_app_audio_draw_profile(void);",
            "AUDIO PROFILE",
            "AUDIO_DEFAULT_PROFILE_ID",
            "a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID)",
            "app_audio_format_acdb_order(profile, order, sizeof(order))",
            "GLOBAL CFG %s",
            "STREAM CFG %s",
            "SETS %d: %s",
            "STAGES %d native=%d writes=%d",
            "AUDIO_STAGE_CONTRACT_COUNT",
            "app_audio_stage_native_count()",
            "app_audio_stage_runtime_write_count()",
            "DISPLAY ONLY - NO AUDIO WRITE",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source + header)

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
            with self.subTest(marker=forbidden):
                self.assertNotIn(forbidden, source)

    def test_menu_and_screenapp_expose_profile_surface(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")
        menu_c = MENU_C.read_text(encoding="utf-8")
        menu_h = MENU_H.read_text(encoding="utf-8")
        menu_apps = MENU_APPS.read_text(encoding="utf-8")

        for marker in [
            "SCREEN_MENU_AUDIO_PROFILE",
            "SCREEN_APP_AUDIO_PROFILE",
            '{ "PROFILE",      "APP TYPE AND STAGES", SCREEN_MENU_AUDIO_PROFILE, SCREEN_MENU_PAGE_AUDIO }',
            "case SCREEN_MENU_AUDIO_PROFILE:",
            "return SCREEN_APP_AUDIO_PROFILE;",
            "state->active_app == SCREEN_APP_AUDIO_PROFILE",
            "a90_app_audio_draw_profile();",
            'strcmp(app, "audio-profile") == 0 || strcmp(app, "profile") == 0',
            "screenapp.title=AUDIO PROFILE",
            "screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status|audio-profile|audio-map]",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, menu_h + menu_c + menu_apps + dispatch + help_text)


if __name__ == "__main__":
    unittest.main()
