"""Tests for the V2764 native audio speaker-map API."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
QUERY_C = REPO / "workspace/public/src/native-init/a90_audio_query.c"
QUERY_H = REPO / "workspace/public/src/native-init/a90_audio_query.h"
ROUTE_C = REPO / "workspace/public/src/native-init/a90_audio_route.c"
ROUTE_H = REPO / "workspace/public/src/native-init/a90_audio_route.h"


def source_text() -> str:
    return "\n".join([
        AUDIO_C.read_text(encoding="utf-8"),
        QUERY_C.read_text(encoding="utf-8"),
        QUERY_H.read_text(encoding="utf-8"),
        ROUTE_C.read_text(encoding="utf-8"),
        ROUTE_H.read_text(encoding="utf-8"),
    ])


class NativeAudioSpeakerMapApiV2764(unittest.TestCase):
    def test_speaker_map_is_first_class_read_only_subcommand(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "speaker-map") == 0', text)
        self.assertIn("return a90_audio_query_speaker_map_cmd(argv, argc);", text)
        self.assertIn("usage: audio speaker-map", text)
        self.assertIn("audio.speaker_map.read_only=1", text)
        self.assertIn("audio.speaker_map.route_write_attempted=0", text)
        self.assertIn("audio.speaker_map.playback_attempted=0", text)

    def test_speaker_map_names_left_right_and_feedback_speakers(self) -> None:
        text = source_text()

        for speaker in [
            '"shared"',
            '"SPKR_VI_1"',
            '"SPKR_VI_2"',
            '"SPKR_VI"',
            '"SpkrLeft"',
            '"SpkrRight"',
        ]:
            with self.subTest(speaker=speaker):
                self.assertIn(speaker, text)
        self.assertIn("AUDIO_SPEAKER_MAP_ENTRIES", text)
        self.assertIn("audio.speaker_map.speaker.%d", text)
        self.assertIn("%s.role=%s", text)
        self.assertIn("%s.channel=%s", text)
        self.assertIn("%s.hardware=%s", text)
        self.assertIn("%s.safety=%s", text)

    def test_speaker_map_summarizes_route_observer_and_policy_counts(self) -> None:
        text = source_text()

        for marker in [
            "audio.speaker_map.route_control.count",
            "audio.speaker_map.observer_control.count",
            "audio.speaker_map.speaker.count",
            "route_core_controls",
            "route_feedback_controls",
            "route_endpoint_controls",
            "route_blocked_boost_controls",
            "observer_controls",
            "a90_audio_observer_count_for_prefix",
            "a90_audio_route_count_for_speaker",
            "a90_audio_route_layer_count_for_speaker",
            "a90_audio_route_boost_count_for_speaker",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_speaker_map_preserves_speaker_safety_boundary(self) -> None:
        text = QUERY_C.read_text(encoding="utf-8")
        start = text.index("int a90_audio_query_speaker_map_cmd")
        block = text[start:]

        self.assertIn("audio.speaker_map.safety.amplitude_cap_milli", block)
        self.assertIn("audio.speaker_map.safety.smart_amp_boost_write_allowed=0", block)
        self.assertIn("audio.speaker_map.safety.smart_amp_boost_blocked", block)
        self.assertNotIn("ioctl(", block)
        self.assertNotIn("open(", block)


if __name__ == "__main__":
    unittest.main()
