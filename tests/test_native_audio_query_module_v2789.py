"""Tests for the V2789 native audio read-only query module split."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
QUERY_H = REPO / "workspace/public/src/native-init/a90_audio_query.h"
QUERY_C = REPO / "workspace/public/src/native-init/a90_audio_query.c"
PROFILE_H = REPO / "workspace/public/src/native-init/a90_audio_profile.h"
PROFILE_C = REPO / "workspace/public/src/native-init/a90_audio_profile.c"


class NativeAudioQueryModuleV2789(unittest.TestCase):
    def test_query_module_declares_read_only_command_api(self) -> None:
        header = QUERY_H.read_text(encoding="utf-8")
        source = QUERY_C.read_text(encoding="utf-8")

        for symbol in [
            "a90_audio_query_profiles_cmd",
            "a90_audio_query_profile_cmd",
            "a90_audio_query_stages_cmd",
            "a90_audio_query_speaker_map_cmd",
        ]:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, header)
                self.assertIn(symbol, source)

    def test_audio_command_dispatches_to_query_module(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn('#include "a90_audio_query.h"', text)
        self.assertIn("return a90_audio_query_profiles_cmd();", text)
        self.assertIn("return a90_audio_query_profile_cmd(argv, argc);", text)
        self.assertIn("return a90_audio_query_speaker_map_cmd(argv, argc);", text)
        self.assertIn("return a90_audio_query_stages_cmd(argv, argc);", text)
        self.assertNotIn("static int audio_print_profiles", text)
        self.assertNotIn("static int audio_print_profile", text)
        self.assertNotIn("static int audio_print_stages", text)
        self.assertNotIn("static int audio_speaker_map_cmd", text)

    def test_query_module_owns_read_only_output_markers(self) -> None:
        source = QUERY_C.read_text(encoding="utf-8")

        for marker in [
            "audio.profiles.version=%d",
            "audio.profile.read_only=1",
            "audio.stages.read_only=1",
            "audio.stages.all_native_ready=0",
            "audio.speaker_map.read_only=1",
            "audio.speaker_map.route_write_attempted=0",
            "audio.speaker_map.playback_attempted=0",
            "audio.speaker_map.speaker.%d",
            "audio.speaker_map.safety.smart_amp_boost_write_allowed=0",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_query_module_is_observability_only(self) -> None:
        source = QUERY_C.read_text(encoding="utf-8")

        self.assertNotIn("ioctl(", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("SNDRV_CTL_IOCTL_ELEM_WRITE", source)
        self.assertNotIn("write_all_checked", source)
        self.assertNotIn("audio_play_execute_pcm", source)

    def test_profile_lookup_api_moved_to_profile_module(self) -> None:
        header = PROFILE_H.read_text(encoding="utf-8")
        source = PROFILE_C.read_text(encoding="utf-8")
        audio = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("int a90_audio_profile_count(void);", header)
        self.assertIn("const struct audio_speaker_profile *a90_audio_find_profile", header)
        self.assertIn("int a90_audio_profile_count(void)", source)
        self.assertIn("const struct audio_speaker_profile *a90_audio_find_profile", source)
        self.assertIn("a90_audio_find_profile(profile_id)", audio)
        self.assertNotIn("static const struct audio_speaker_profile *audio_find_profile", audio)
        self.assertNotIn("static int audio_profile_count", audio)


if __name__ == "__main__":
    unittest.main()
