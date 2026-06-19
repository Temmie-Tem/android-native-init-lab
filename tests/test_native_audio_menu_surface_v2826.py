"""Tests for the V2826 audio screen menu surface."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MENU_H = REPO / "workspace/public/src/native-init/a90_menu.h"
MENU_C = REPO / "workspace/public/src/native-init/a90_menu.c"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
AUDIO_APP_C = REPO / "workspace/public/src/native-init/a90_app_audio.c"


class NativeAudioMenuSurfaceV2826Test(unittest.TestCase):
    def test_menu_model_exposes_audio_page_and_actions(self) -> None:
        header = MENU_H.read_text(encoding="utf-8")
        source = MENU_C.read_text(encoding="utf-8")

        for marker in [
            "SCREEN_MENU_PAGE_AUDIO",
            "SCREEN_MENU_AUDIO_STATUS",
            "SCREEN_MENU_AUDIO_PROFILE",
            "SCREEN_MENU_AUDIO_MAP",
            "SCREEN_APP_AUDIO_STATUS",
            "SCREEN_APP_AUDIO_PROFILE",
            "SCREEN_APP_AUDIO_MAP",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, header)

        for marker in [
            '{ "AUDIO >", "SPEAKER STATUS AND ROUTE MAP", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_AUDIO }',
            'static const struct screen_menu_item screen_menu_audio_items[]',
            '{ "AUDIO STATUS", "CORE PROFILE SAFETY", SCREEN_MENU_AUDIO_STATUS, SCREEN_MENU_PAGE_AUDIO }',
            '{ "PROFILE",      "APP TYPE AND STAGES", SCREEN_MENU_AUDIO_PROFILE, SCREEN_MENU_PAGE_AUDIO }',
            '{ "ROUTE MAP",    "SPEAKERS AND PATH",   SCREEN_MENU_AUDIO_MAP,    SCREEN_MENU_PAGE_AUDIO }',
            '"APPS / AUDIO", screen_menu_audio_items',
            'case SCREEN_MENU_AUDIO_STATUS:',
            'return SCREEN_APP_AUDIO_STATUS;',
            'case SCREEN_MENU_AUDIO_PROFILE:',
            'return SCREEN_APP_AUDIO_PROFILE;',
            'case SCREEN_MENU_AUDIO_MAP:',
            'return SCREEN_APP_AUDIO_MAP;',
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_menu_draw_dispatch_reuses_display_only_audio_apps(self) -> None:
        source = MENU_APPS.read_text(encoding="utf-8")
        audio_source = AUDIO_APP_C.read_text(encoding="utf-8")

        for marker in [
            'state->active_app == SCREEN_APP_AUDIO_STATUS',
            'a90_app_audio_draw_status();',
            'state->active_app == SCREEN_APP_AUDIO_PROFILE',
            'a90_app_audio_draw_profile();',
            'state->active_app == SCREEN_APP_AUDIO_MAP',
            'a90_app_audio_draw_map();',
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        for forbidden in [
            'open(',
            'ioctl(',
            'audio_route_write',
            'audio_setcal',
            'audio_play',
            'SNDRV_CTL_IOCTL_ELEM_WRITE',
            'tinymix',
            'tinyplay',
        ]:
            with self.subTest(marker=forbidden):
                self.assertNotIn(forbidden, audio_source)


if __name__ == "__main__":
    unittest.main()
