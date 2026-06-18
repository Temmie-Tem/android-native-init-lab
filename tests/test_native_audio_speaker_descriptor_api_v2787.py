"""Tests for the V2787 native audio speaker descriptor API."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
QUERY_C = REPO / "workspace/public/src/native-init/a90_audio_query.c"
ROUTE_H = REPO / "workspace/public/src/native-init/a90_audio_route.h"
ROUTE_C = REPO / "workspace/public/src/native-init/a90_audio_route.c"


def all_text() -> str:
    return "\n".join([
        AUDIO_C.read_text(encoding="utf-8"),
        QUERY_C.read_text(encoding="utf-8"),
        ROUTE_H.read_text(encoding="utf-8"),
        ROUTE_C.read_text(encoding="utf-8"),
    ])


class NativeAudioSpeakerDescriptorApiV2787(unittest.TestCase):
    def test_route_api_exposes_descriptor_struct(self) -> None:
        header = ROUTE_H.read_text(encoding="utf-8")
        source = ROUTE_C.read_text(encoding="utf-8")

        for marker in [
            "struct audio_speaker_map_entry",
            "const char *id;",
            "const char *role;",
            "const char *channel;",
            "const char *hardware;",
            "const char *safety;",
            "a90_audio_speaker_map_entry",
            "AUDIO_SPEAKER_MAP_ENTRIES",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, header + source)

    def test_descriptors_name_physical_roles_and_channels(self) -> None:
        source = ROUTE_C.read_text(encoding="utf-8")

        for marker in [
            '.id = "shared"',
            '.role = "stream-route"',
            '.channel = "both"',
            '.id = "SPKR_VI_1"',
            '.role = "feedback"',
            '.channel = "left"',
            '.id = "SPKR_VI_2"',
            '.channel = "right"',
            '.id = "SpkrLeft"',
            '.role = "endpoint"',
            '.hardware = "left WSA881x speaker endpoint"',
            '.id = "SpkrRight"',
            '.hardware = "right WSA881x speaker endpoint"',
            '.safety = "boost-write-blocked"',
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_speaker_map_command_prints_descriptor_fields(self) -> None:
        text = all_text()

        for marker in [
            '"audio.speaker_map.speaker.%d"',
            '"%s.role=%s',
            '"%s.channel=%s',
            '"%s.hardware=%s',
            '"%s.safety=%s',
            "a90_audio_speaker_map_entry(index)",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_descriptor_api_stays_read_only(self) -> None:
        source = ROUTE_C.read_text(encoding="utf-8")

        self.assertNotIn("ioctl(", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("SNDRV_CTL_IOCTL_ELEM_WRITE", source)


if __name__ == "__main__":
    unittest.main()
