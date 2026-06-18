"""Tests for the V2783 audio route API module split."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO = REPO / "workspace/public/src/native-init/a90_audio.c"
ROUTE_H = REPO / "workspace/public/src/native-init/a90_audio_route.h"
ROUTE_C = REPO / "workspace/public/src/native-init/a90_audio_route.c"
PROFILE_H = REPO / "workspace/public/src/native-init/a90_audio_profile.h"


class NativeAudioRouteApiV2783(unittest.TestCase):
    def test_route_api_files_exist_and_define_contract(self) -> None:
        header = ROUTE_H.read_text(encoding="utf-8")
        source = ROUTE_C.read_text(encoding="utf-8")

        self.assertIn("#define AUDIO_ROUTE_API_VERSION 1", header)
        for symbol in [
            "a90_audio_route_control_count",
            "a90_audio_route_reset_count",
            "a90_audio_route_selected_count",
            "a90_audio_route_layer_write_allowed",
            "a90_audio_route_count_for_speaker",
            "a90_audio_speaker_map_id",
        ]:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, header)
                self.assertIn(symbol, source)

    def test_route_api_owns_speaker_map_and_layers(self) -> None:
        header = ROUTE_H.read_text(encoding="utf-8")
        source = ROUTE_C.read_text(encoding="utf-8")
        audio = AUDIO.read_text(encoding="utf-8")

        for layer in ["all", "core", "feedback", "endpoint", "blocked"]:
            with self.subTest(layer=layer):
                self.assertIn(f'"{layer}"', header + source)
        for speaker in ["shared", "SPKR_VI_1", "SPKR_VI_2", "SPKR_VI", "SpkrLeft", "SpkrRight"]:
            with self.subTest(speaker=speaker):
                self.assertIn(f'"{speaker}"', source)
        self.assertIn("a90_audio_speaker_map_id(index)", audio)
        self.assertNotIn("AUDIO_SPEAKER_MAP_IDS[]", audio)

    def test_route_api_keeps_profile_data_separate_from_route_logic(self) -> None:
        profile = PROFILE_H.read_text(encoding="utf-8")
        source = ROUTE_C.read_text(encoding="utf-8")

        self.assertIn("extern const struct audio_route_control AUDIO_INTERNAL_SPEAKER_ROUTE", profile)
        self.assertIn("AUDIO_INTERNAL_SPEAKER_ROUTE", source)
        self.assertNotIn("SNDRV_CTL_IOCTL_ELEM_WRITE", source)
        self.assertNotIn("ioctl(", source)

    def test_builder_tracks_route_api_boundary(self) -> None:
        builder = (REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2783_audio_route_api.py").read_text(encoding="utf-8")
        report = (REPO / "docs/reports/NATIVE_INIT_V2783_AUDIO_ROUTE_API_SOURCE_BUILD_2026-06-19.md").read_text(encoding="utf-8")

        self.assertIn('INIT_VERSION = "0.9.299"', builder)
        self.assertIn('INIT_BUILD = "v2783-audio-route-api"', builder)
        self.assertIn("a90_audio_route.{h,c}", builder)
        self.assertIn("audio route API module source build", report)
        self.assertIn("Boot SHA256", report)


if __name__ == "__main__":
    unittest.main()
