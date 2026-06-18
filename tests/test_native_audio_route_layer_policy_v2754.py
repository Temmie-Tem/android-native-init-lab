"""Tests for the V2754 native audio route layer and policy contract."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
AUDIO_PROFILE_H = REPO / "workspace/public/src/native-init/a90_audio_profile.h"
AUDIO_PROFILE_C = REPO / "workspace/public/src/native-init/a90_audio_profile.c"


def source_text() -> str:
    return "\n".join([
        AUDIO_C.read_text(encoding="utf-8"),
        AUDIO_PROFILE_H.read_text(encoding="utf-8"),
        AUDIO_PROFILE_C.read_text(encoding="utf-8"),
    ])


class NativeAudioRouteLayerPolicyV2754(unittest.TestCase):
    def test_route_accepts_explicit_layer_filter_api(self) -> None:
        text = source_text()

        self.assertIn('--layer all|core|feedback|endpoint|blocked', text)
        self.assertIn('static bool audio_route_layer_valid', text)
        self.assertIn('strcmp(layer, "core") == 0', text)
        self.assertIn('strcmp(layer, "feedback") == 0', text)
        self.assertIn('strcmp(layer, "endpoint") == 0', text)
        self.assertIn('strcmp(layer, "blocked") == 0', text)
        self.assertIn('audio.route.layer=%s', text)

    def test_route_controls_are_grouped_by_layer_and_speaker(self) -> None:
        text = source_text()

        self.assertRegex(text, re.compile(r'\.name = "Audio Stream 0 App Type Cfg".*?\.layer = "core".*?\.speaker = "shared"', re.DOTALL))
        self.assertRegex(text, re.compile(r'\.name = "AIF4_VI Mixer SPKR_VI_1".*?\.layer = "feedback".*?\.speaker = "SPKR_VI_1"', re.DOTALL))
        self.assertRegex(text, re.compile(r'\.name = "SpkrLeft VISENSE Switch".*?\.layer = "endpoint".*?\.speaker = "SpkrLeft"', re.DOTALL))
        self.assertRegex(text, re.compile(r'\.name = "SpkrLeft BOOST Switch".*?\.layer = "endpoint".*?\.speaker = "SpkrLeft"', re.DOTALL))

    def test_route_policy_marks_boost_as_blocked_without_blocking_core_dry_run(self) -> None:
        text = source_text()

        self.assertIn('.policy = "safe-observed"', text)
        self.assertIn('.policy = "speaker-protection-observed"', text)
        self.assertIn('.policy = "speaker-endpoint-review"', text)
        self.assertRegex(text, re.compile(r'\.name = "SpkrLeft BOOST Switch".*?\.policy = "blocked-smart-amp-boost".*?\.smart_amp_boost = true', re.DOTALL))
        self.assertIn('audio.route.selected.smart_amp_boost_blocked=%d', text)
        self.assertIn('audio_route_selected_has_smart_amp_boost(layer)', text)

    def test_write_refusal_distinguishes_policy_block_from_unimplemented_writer(self) -> None:
        text = source_text()

        self.assertIn('audio.route.refused=write-mode-blocked-smart-amp-boost-review', text)
        self.assertIn('audio.route.refused=write-mode-blocked-non-core-layer', text)
        self.assertIn('if (selected_has_boost)', text)
        self.assertIn('return -EPERM;', text)

    def test_selected_counts_are_layer_aware(self) -> None:
        text = source_text()

        self.assertIn('static int audio_route_selected_count(const char *layer, bool reset_mode)', text)
        self.assertIn('audio.route.selected.apply.count=%d', text)
        self.assertIn('audio.route.selected.reset.count=%d', text)
        self.assertIn('audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)', text)


if __name__ == "__main__":
    unittest.main()
