"""Tests for the V2752 native audio App Type Config command contract."""

from __future__ import annotations

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


class NativeAudioAppTypeCommandV2752(unittest.TestCase):
    def test_command_is_exposed_as_explicit_app_type_api(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "app-type") == 0', text)
        self.assertIn('return audio_app_type_cmd(argv, argc);', text)
        self.assertIn('usage: audio app-type [profile] [--dry-run|--write]', text)
        self.assertIn('app-type [profile] [--dry-run|--write]', text)

    def test_write_requires_explicit_write_flag_and_defaults_to_dry_run(self) -> None:
        text = source_text()

        self.assertIn('bool write_mode = false;', text)
        self.assertIn('audio.app_type.mode=%s', text)
        self.assertIn('write_mode ? "write" : "dry-run"', text)
        self.assertIn('if (!write_mode)', text)
        self.assertIn('audio.app_type.dry_run_ok=1', text)
        self.assertIn('audio.app_type.write_attempted=0', text)
        self.assertIn('audio.app_type.write_attempted=1', text)

    def test_native_writer_uses_atomic_alsa_elem_write_for_global_app_type_config(self) -> None:
        text = source_text()

        self.assertIn('#include <sound/asound.h>', text)
        self.assertIn('SNDRV_CTL_IOCTL_ELEM_LIST', text)
        self.assertIn('SNDRV_CTL_IOCTL_ELEM_INFO', text)
        self.assertIn('SNDRV_CTL_IOCTL_ELEM_WRITE', text)
        self.assertIn('audio_resolve_control_by_name(fd, "App Type Config", &id)', text)
        self.assertIn('value->value.integer.value[0] = 1;', text)
        self.assertIn('value->value.integer.value[1] = profile->app_type;', text)
        self.assertIn('value->value.integer.value[2] = profile->sample_rate;', text)
        self.assertIn('value->value.integer.value[3] = profile->bit_width;', text)

    def test_app_type_api_reuses_profile_contract_values(self) -> None:
        text = source_text()

        self.assertIn('audio.app_type.payload=%s', text)
        self.assertIn('profile->global_app_type_config', text)
        self.assertIn('.global_app_type_config = "1 69941 48000 16"', text)
        self.assertIn('.app_type = 69941', text)
        self.assertIn('.sample_rate = 48000', text)
        self.assertIn('.bit_width = 16', text)


if __name__ == "__main__":
    unittest.main()
