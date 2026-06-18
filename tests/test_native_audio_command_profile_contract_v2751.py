"""Tests for the V2751 native audio profile command contract."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from _loader import load_revalidation

profiles = load_revalidation("native_audio_speaker_profiles_v2749")

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


class NativeAudioCommandProfileContractV2751(unittest.TestCase):
    def test_native_profile_pins_python_profile_contract(self) -> None:
        text = source_text()
        profile = profiles.get_profile("internal-speaker-safe")

        self.assertIn('#define AUDIO_DEFAULT_PROFILE_ID "internal-speaker-safe"', text)
        self.assertIn('.endpoint = "internal-speaker"', text)
        self.assertIn('.speaker_map = "SpkrLeft/SpkrRight WSA881x via WSA_CDC_DMA_RX"', text)
        self.assertIn(f'.app_type = {profile.app_type.app_type}', text)
        self.assertIn(f'.acdb_id = {profile.app_type.acdb_id}', text)
        self.assertIn(f'.sample_rate = {profile.app_type.sample_rate}', text)
        self.assertIn(f'.bit_width = {profile.app_type.bit_width}', text)
        self.assertIn('.global_app_type_config = "1 69941 48000 16"', text)
        self.assertIn('.stream_app_type_config = "69941 15 48000 2"', text)
        self.assertIn('.acdb_set_order = {39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21}', text)
        self.assertIn('.forbidden_cal_types = {10, 14, 24}', text)

    def test_native_audio_exports_read_only_profile_subcommands(self) -> None:
        text = source_text()

        self.assertRegex(text, r'strcmp\(argv\[1\], "profiles"\) == 0')
        self.assertRegex(text, r'strcmp\(argv\[1\], "profile"\) == 0')
        self.assertIn('audio.profile.read_only=1', text)
        self.assertIn('audio.status.default_profile=%s', text)
        self.assertIn('usage: audio [adsp-status|status|profiles|profile [id]|speaker-map [id]|stages [id]|prereq [id]|app-type [profile] [--dry-run|--write]|setcal [profile] [--dry-run|--execute] [--manifest PATH --verify|--prepare|--load]|play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]|stop [profile] [--dry-run|--execute]|route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]|snd-status|adsp-boot-once|snd-materialize-once]', text)

    def test_native_profile_preserves_speaker_safety_limits(self) -> None:
        text = source_text()

        self.assertIn('.probe_amplitude_milli = 20', text)
        self.assertIn('.probe_duration_ms = 1000', text)
        self.assertIn('.listen_amplitude_milli = 150', text)
        self.assertIn('.listen_duration_ms = 8000', text)
        self.assertIn('.amplitude_cap_milli = 200', text)
        self.assertIn('.duration_cap_ms = 10000', text)
        self.assertIn('audio.profile.safety.no_smart_amp_gain_boost_changes=1', text)

    def test_profile_output_has_parseable_list_contracts(self) -> None:
        text = source_text()

        self.assertRegex(text, r'print_int_list\("audio\.profile\.acdb_set_order",\s*profile->acdb_set_order')
        self.assertRegex(text, r'print_int_list\("audio\.profile\.forbidden_cal_types",\s*profile->forbidden_cal_types')
        self.assertRegex(text, r'print_str_list\("audio\.profile\.observer_controls",\s*profile->observer_controls')


if __name__ == "__main__":
    unittest.main()
