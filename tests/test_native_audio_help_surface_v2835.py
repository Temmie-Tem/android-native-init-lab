"""Tests for the V2835 native audio help surface."""

from __future__ import annotations

from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
AUDIO = REPO / "workspace/public/src/native-init/a90_audio.c"


class NativeAudioHelpSurfaceV2835Test(unittest.TestCase):
    def test_top_level_help_lists_current_audio_subcommands(self) -> None:
        expected = (
            "audio [status|profiles|profile|speaker-map|stages|prereq|app-type|"
            "setcal|route|play|chime|play-status|stop|adsp-status|snd-status]"
        )
        stale = "audio [adsp-status|status|snd-status|adsp-boot-once|snd-materialize-once]"
        for path in [DISPATCH, BASIC]:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn(expected, text)
                self.assertNotIn(stale, text)

    def test_audio_command_usage_still_exposes_full_safety_contract(self) -> None:
        audio = AUDIO.read_text(encoding="utf-8")
        for marker in [
            "usage: audio [adsp-status|status|profiles|profile [id]|speaker-map [id]|stages [id]|prereq [id]",
            "app-type [profile] [--dry-run|--write]",
            "setcal [profile] [--dry-run|--execute] [--manifest PATH --verify|--prepare|--load]",
            "play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]",
            "play-status|stop [profile] [--dry-run|--execute]",
            "route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|playback|blocked]",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, audio)


if __name__ == "__main__":
    unittest.main()
