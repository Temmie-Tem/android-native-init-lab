"""Tests for the V2753 native audio route command contract."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioRouteContractV2753(unittest.TestCase):
    def test_route_command_is_exposed_as_named_audio_api(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "route") == 0', text)
        self.assertIn('return audio_route_cmd(argv, argc);', text)
        self.assertIn('usage: audio route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]', text)
        self.assertIn('route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]', text)

    def test_route_contract_pins_apply_and_reset_counts(self) -> None:
        text = source_text()

        self.assertIn('#define AUDIO_ROUTE_APPLY_COUNT 13', text)
        self.assertIn('#define AUDIO_ROUTE_RESET_COUNT 12', text)
        self.assertIn('audio.route.apply.count=%d', text)
        self.assertIn('audio.route.reset.count=%d', text)
        self.assertIn('audio_route_control_count() != AUDIO_ROUTE_APPLY_COUNT', text)
        self.assertIn('audio_route_reset_count() != AUDIO_ROUTE_RESET_COUNT', text)

    def test_route_contract_contains_v2378_internal_speaker_controls(self) -> None:
        text = source_text()
        controls = [
            "Audio Stream 0 App Type Cfg",
            "Playback Channel Map0",
            "SLIMBUS_0_RX Audio Mixer MultiMedia1",
            "SLIM RX0 MUX",
            "RX INT7_1 MIX1 INP0",
            "COMP7 Switch",
            "AIF4_VI Mixer SPKR_VI_1",
            "AIF4_VI Mixer SPKR_VI_2",
            "SLIM_4_TX Format",
            "SpkrLeft VISENSE Switch",
            "SpkrLeft COMP Switch",
            "SpkrLeft BOOST Switch",
            "SpkrLeft SWR DAC_Port Switch",
        ]

        for control in controls:
            with self.subTest(control=control):
                self.assertIn(f'.name = "{control}"', text)

    def test_route_preserves_global_app_type_dependency(self) -> None:
        text = source_text()

        self.assertIn('audio.route.requires_global_app_type=1', text)
        self.assertIn('audio.route.global_app_type_primitive=audio app-type %s --write', text)
        self.assertIn('.apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {69941, 15, 48000, 2}, .int_count = 4, .zero_fill = 124}', text)

    def test_route_write_modes_are_blocked_by_smart_amp_policy(self) -> None:
        text = source_text()

        self.assertRegex(
            text,
            re.compile(
                r'\.name = "SpkrLeft BOOST Switch".*?\.smart_amp_boost = true',
                re.DOTALL,
            ),
        )
        self.assertIn('audio.route.smart_amp_boost_blocked=%d', text)
        self.assertIn('audio.route.blocked_control=SpkrLeft BOOST Switch', text)
        self.assertIn('audio.route.refused=write-mode-blocked-smart-amp-boost-review', text)
        self.assertIn('audio.route.write_attempted=0', text)
        self.assertIn('return -EPERM;', text)

    def test_reset_order_is_reverse_and_skips_non_resettable_stream_cfg(self) -> None:
        text = source_text()

        self.assertIn('for (index = audio_route_control_count() - 1; index >= 0; --index)', text)
        self.assertIn('if (!AUDIO_INTERNAL_SPEAKER_ROUTE[index].resettable)', text)
        self.assertIn('.name = "Audio Stream 0 App Type Cfg"', text)
        self.assertIn('.resettable = false', text)
        self.assertIn('.name = "SpkrLeft SWR DAC_Port Switch"', text)


if __name__ == "__main__":
    unittest.main()
