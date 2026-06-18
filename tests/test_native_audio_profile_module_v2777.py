"""Tests for the V2777 native audio speaker profile module split."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
PROFILE_H = REPO / "workspace/public/src/native-init/a90_audio_profile.h"
PROFILE_C = REPO / "workspace/public/src/native-init/a90_audio_profile.c"
ROUTE_C = REPO / "workspace/public/src/native-init/a90_audio_route.c"


class NativeAudioProfileModuleV2777(unittest.TestCase):
    def test_profile_module_owns_profile_types_and_constants(self) -> None:
        header = PROFILE_H.read_text(encoding="utf-8")

        self.assertIn("#define AUDIO_DEFAULT_PROFILE_ID", header)
        self.assertIn("#define AUDIO_PROFILE_ACDB_SET_COUNT 11", header)
        self.assertIn("#define AUDIO_ROUTE_APPLY_COUNT 13", header)
        self.assertIn("struct audio_speaker_profile", header)
        self.assertIn("struct audio_route_control", header)
        self.assertIn("extern const struct audio_speaker_profile AUDIO_SPEAKER_PROFILES", header)
        self.assertIn("extern const struct audio_route_control AUDIO_INTERNAL_SPEAKER_ROUTE", header)

    def test_profile_module_owns_canonical_internal_speaker_data(self) -> None:
        profile = PROFILE_C.read_text(encoding="utf-8")

        for marker in [
            '.id = AUDIO_DEFAULT_PROFILE_ID',
            '.endpoint = "internal-speaker"',
            '.speaker_map = "SpkrLeft/SpkrRight WSA881x via WSA_CDC_DMA_RX"',
            '.global_app_type_config = "1 69941 48000 16"',
            '.stream_app_type_config = "69941 15 48000 2"',
            '.acdb_set_order = {39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21}',
            '.forbidden_cal_types = {10, 14, 24}',
            '.name = "Audio Stream 0 App Type Cfg"',
            '.name = "SpkrLeft BOOST Switch"',
            '.smart_amp_boost = true',
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, profile)

    def test_command_file_uses_profile_module_instead_of_owning_profile_data(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")
        route = ROUTE_C.read_text(encoding="utf-8")

        self.assertIn('#include "a90_audio_profile.h"', text)
        self.assertIn("return AUDIO_SPEAKER_PROFILE_COUNT;", text)
        self.assertIn("return AUDIO_ROUTE_APPLY_COUNT;", route)
        self.assertNotIn("static const struct audio_speaker_profile AUDIO_SPEAKER_PROFILES", text)
        self.assertNotIn("static const struct audio_route_control AUDIO_INTERNAL_SPEAKER_ROUTE", text)
        self.assertNotIn("struct audio_speaker_profile {", text)


if __name__ == "__main__":
    unittest.main()
