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
        self.assertIn('strcmp(app, "audio-status") == 0 || strcmp(app, "audio") == 0', dispatch)
        self.assertIn('screenapp.title=AUDIO STATUS', dispatch)
        self.assertIn('a90_app_audio_draw_status()', dispatch)
        self.assertIn('screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status]', dispatch)
        self.assertIn('screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|audio-status]', help_text)

    def test_pid1_source_glob_includes_new_a90_module(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('for path in sorted(LINUX_INIT.glob("a90_*.c")):', text)
        self.assertIn('sources.append(path)', text)


if __name__ == "__main__":
    unittest.main()
