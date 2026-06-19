"""Tests for the V2833 display-only audio stage contract screen surface."""

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


class NativeAudioStageScreenV2833Test(unittest.TestCase):
    def test_stage_screen_is_display_only_and_contract_backed(self) -> None:
        source = AUDIO_APP_C.read_text(encoding="utf-8")
        header = AUDIO_APP_H.read_text(encoding="utf-8")

        for marker in [
            "int a90_app_audio_draw_stages(void)",
            "int a90_app_audio_draw_stages(void);",
            "AUDIO STAGES",
            "AUDIO_STAGE_CONTRACT_VERSION",
            "AUDIO_STAGE_CONTRACT_COUNT",
            "CONTRACT v%d stages=%d native=%d writes=%d",
            "BOOT preflight-v2321-health RO",
            "ADSP adsp-boot-once WRITE",
            "SND snd-materialize-once WRITE",
            "APP write-global-app-type-config WRITE",
            "ACDB verify/prep/load RO; SET WRITE",
            "ROUTE core WRITE; PCM bounded WRITE",
            "STOP cleanup/reset/dealloc WRITE",
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

    def test_menu_and_screenapp_expose_stage_surface(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")
        menu_c = MENU_C.read_text(encoding="utf-8")
        menu_h = MENU_H.read_text(encoding="utf-8")
        menu_apps = MENU_APPS.read_text(encoding="utf-8")

        for marker in [
            "SCREEN_MENU_AUDIO_STAGES",
            "SCREEN_APP_AUDIO_STAGES",
            '{ "STAGES",       "CONTRACT AND WRITES", SCREEN_MENU_AUDIO_STAGES,  SCREEN_MENU_PAGE_AUDIO }',
            "case SCREEN_MENU_AUDIO_STAGES:",
            "return SCREEN_APP_AUDIO_STAGES;",
            "state->active_app == SCREEN_APP_AUDIO_STAGES",
            "a90_app_audio_draw_stages();",
            'strcmp(app, "audio-stages") == 0 || strcmp(app, "stages") == 0',
            "screenapp.title=AUDIO STAGES",
            "screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status|audio-profile|audio-stages|audio-map]",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, menu_h + menu_c + menu_apps + dispatch + help_text)


if __name__ == "__main__":
    unittest.main()
