"""Tests for the V2822 display-only audio status screenapp."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_APP_C = REPO / "workspace/public/src/native-init/a90_app_audio.c"
AUDIO_APP_H = REPO / "workspace/public/src/native-init/a90_app_audio.h"
PRELUDE = REPO / "workspace/public/src/native-init/v319/00_prelude.inc.c"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v725_fasttransport.py"


class NativeAudioScreenappStatusV2822Test(unittest.TestCase):
    def test_audio_screen_module_is_display_only(self) -> None:
        source = AUDIO_APP_C.read_text(encoding="utf-8")

        for marker in [
            'int a90_app_audio_draw_status(void)',
            'AUDIO_CORE_PROMOTION_VERSION',
            'AUDIO_CORE_PROMOTION_RUN',
            'AUDIO_DEFAULT_PROFILE_ID',
            'a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID)',
            'a90_audio_route_control_count()',
            'a90_audio_route_reset_count()',
            'a90_audio_speaker_map_count()',
            'a90_audio_route_has_smart_amp_boost()',
            'a90_audio_route_layer_write_allowed(AUDIO_ROUTE_LAYER_BLOCKED)',
            'a90_kms_present("screenaudio", true)',
            'DISPLAY ONLY - NO AUDIO WRITE',
            'int a90_app_audio_draw_profile(void)',
            'app_audio_format_acdb_order(profile, order, sizeof(order))',
            'GLOBAL CFG %s',
            'STREAM CFG %s',
            'SETS %d: %s',
            'AUDIO PROFILE',
            'int a90_app_audio_draw_stages(void)',
            'AUDIO STAGES',
            'CONTRACT v%d stages=%d native=%d writes=%d',
            'ACDB verify/prep/load RO; SET WRITE',
            'int a90_app_audio_draw_map(void)',
            'a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_CORE, false)',
            'a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_FEEDBACK, false)',
            'a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_ENDPOINT, false)',
            'a90_audio_route_selected_count(AUDIO_ROUTE_LAYER_BLOCKED, false)',
            'a90_audio_route_count_for_speaker("SpkrLeft")',
            'a90_audio_route_boost_count_for_speaker("SpkrRight")',
            'AUDIO ROUTE MAP',
            'int a90_app_audio_draw_chime(void)',
            'AUDIO CHIME',
            'COMMAND audio chime --execute',
            'BOOT AUTOPLAY %s BLOCKS_BOOT=0',
            'VALIDATED V2839 PCM ROUTE SETCAL OK',
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        forbidden = [
            'open(',
            'ioctl(',
            'audio_route_write',
            'audio_setcal',
            'audio_play',
            'SNDRV_CTL_IOCTL_ELEM_WRITE',
            'tinymix',
            'tinyplay',
        ]
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_screenapp_dispatch_wires_audio_status_aliases(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        prelude = PRELUDE.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")
        header = AUDIO_APP_H.read_text(encoding="utf-8")

        self.assertIn('#include "../a90_app_audio.h"', prelude)
        self.assertIn('int a90_app_audio_draw_status(void);', header)
        self.assertIn('int a90_app_audio_draw_profile(void);', header)
        self.assertIn('int a90_app_audio_draw_stages(void);', header)
        self.assertIn('int a90_app_audio_draw_map(void);', header)
        self.assertIn('int a90_app_audio_draw_chime(void);', header)
        self.assertIn('strcmp(app, "audio-status") == 0 || strcmp(app, "audio") == 0', dispatch)
        self.assertIn('screenapp.title=AUDIO STATUS', dispatch)
        self.assertIn('a90_app_audio_draw_status()', dispatch)
        self.assertIn('strcmp(app, "audio-profile") == 0 || strcmp(app, "profile") == 0', dispatch)
        self.assertIn('screenapp.title=AUDIO PROFILE', dispatch)
        self.assertIn('a90_app_audio_draw_profile()', dispatch)
        self.assertIn('strcmp(app, "audio-stages") == 0 || strcmp(app, "stages") == 0', dispatch)
        self.assertIn('screenapp.title=AUDIO STAGES', dispatch)
        self.assertIn('a90_app_audio_draw_stages()', dispatch)
        self.assertIn('strcmp(app, "audio-map") == 0 || strcmp(app, "speaker-map") == 0', dispatch)
        self.assertIn('screenapp.title=AUDIO ROUTE MAP', dispatch)
        self.assertIn('a90_app_audio_draw_map()', dispatch)
        self.assertIn('strcmp(app, "audio-chime") == 0 || strcmp(app, "chime") == 0', dispatch)
        self.assertIn('screenapp.title=AUDIO CHIME', dispatch)
        self.assertIn('a90_app_audio_draw_chime()', dispatch)
        self.assertIn('screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|wsta|audio-status|audio-profile|audio-stages|audio-map|audio-chime|about-version|about-changelog]', dispatch)
        self.assertIn('screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|wsta|audio-status|audio-profile|audio-stages|audio-map|audio-chime|about-version|about-changelog]', help_text)

    def test_pid1_source_glob_includes_new_a90_module(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('for path in sorted(LINUX_INIT.glob("a90_*.c")):', text)
        self.assertIn('sources.append(path)', text)


if __name__ == "__main__":
    unittest.main()
