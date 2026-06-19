"""Tests for the V2761 native audio play planning API."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from _loader import load_revalidation

profiles = load_revalidation("native_audio_speaker_profiles_v2749")

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
CHIME_H = REPO / "workspace/public/src/native-init/a90_audio_chime.h"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioPlayPlanApiV2761(unittest.TestCase):
    def test_play_subcommand_is_exposed_as_first_class_audio_api(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "play") == 0', text)
        self.assertIn("return audio_play_cmd(argv, argc);", text)
        self.assertIn("usage: audio play [profile] [--mode probe|listen]", text)
        self.assertIn("audio.play.version=1", text)
        self.assertIn("audio.play.execute_supported=1", text)
        self.assertIn("audio.play.execute_plan_supported", text)

    def test_play_plan_exports_profile_pcm_defaults_and_safety_caps(self) -> None:
        text = source_text()

        for marker in [
            "audio.play.card",
            "audio.play.pcm_device",
            "audio.play.channels",
            "audio.play.sample_rate",
            "audio.play.bit_width",
            "audio.play.format=s16le",
            "audio.play.amplitude_milli",
            "audio.play.duration_ms",
            "audio.play.cap.amplitude_milli",
            "audio.play.cap.duration_ms",
            "audio.play.safety.no_smart_amp_gain_boost_changes=1",
            "audio.play.safety.amplitude_within_cap",
            "audio.play.safety.duration_within_cap",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_probe_and_listen_modes_use_profile_defaults(self) -> None:
        text = source_text()

        self.assertIn('strcmp(mode, "probe") == 0', text)
        self.assertIn("profile->probe_amplitude_milli", text)
        self.assertIn("profile->probe_duration_ms", text)
        self.assertIn('strcmp(mode, "listen") == 0', text)
        self.assertIn("profile->listen_amplitude_milli", text)
        self.assertIn("profile->listen_duration_ms", text)

    def test_play_dry_run_does_not_open_alsa_or_issue_ioctls(self) -> None:
        text = source_text()
        play_start = text.index("static int audio_play_cmd")
        play_end = text.index("static int audio_stop_cmd")
        play_block = text[play_start:play_end]
        execute_branch = play_block.index("if (execute_mode) {")
        dry_run_line = play_block.index("audio.play.dry_run_ok=1")
        dry_run_tail = play_block[execute_branch:dry_run_line]

        self.assertIn("audio.play.alsa_open_attempted=0", text)
        self.assertIn("audio.play.ioctl_attempted=0", text)
        self.assertIn("audio.play.playback_attempted=0", text)
        self.assertNotIn("open(", dry_run_tail)
        self.assertNotIn("ioctl(", dry_run_tail)

    def test_play_refuses_cap_violations_before_execute(self) -> None:
        text = source_text()

        self.assertIn("audio.play.refused=safety-cap-exceeded", text)
        self.assertNotIn("audio.play.refused=execute-not-implemented-native-pcm", text)
        self.assertRegex(
            text,
            re.compile(r'audio.play.refused=safety-cap-exceeded.*?return -EPERM;.*?if \(execute_mode\)', re.DOTALL),
        )

    def test_chime_subcommand_is_safe_preset_over_audio_play(self) -> None:
        text = source_text()
        chime_start = text.index("static int audio_chime_cmd")
        chime_end = text.index("static int audio_stop_cmd")
        chime_block = text[chime_start:chime_end]

        self.assertIn('strcmp(argv[1], "chime") == 0', text)
        self.assertIn("return audio_chime_cmd(argv, argc);", text)
        chime_header = CHIME_H.read_text(encoding="utf-8")
        self.assertIn("AUDIO_CHIME_DEFAULT_AMPLITUDE_MILLI 80", chime_header)
        self.assertIn("AUDIO_CHIME_DEFAULT_DURATION_MS 1200", chime_header)
        self.assertIn("AUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT 0", chime_header)
        self.assertIn("audio.chime.boot_autoplay_default=0", chime_block)
        self.assertIn("audio.chime.best_effort=1", chime_block)
        self.assertIn("audio.chime.blocks_boot=0", chime_block)
        self.assertIn("audio.chime.delegates=audio-play", chime_block)
        self.assertIn('play_argv[play_argc++] = "play"', chime_block)
        self.assertIn('play_argv[play_argc++] = "listen"', chime_block)
        self.assertIn("execute_mode ? \"--execute\" : \"--dry-run\"", chime_block)

    def test_stage_api_has_native_play_plan_before_blocked_execute(self) -> None:
        stages = {stage["stage_id"]: stage for stage in profiles.stage_manifests()}

        self.assertLess(stages["plan-bounded-pcm-playback"]["order"], stages["bounded-pcm-playback"]["order"])
        self.assertEqual(
            stages["plan-bounded-pcm-playback"]["command"],
            ["audio", "play", "internal-speaker-safe", "--mode", "probe", "--dry-run"],
        )
        self.assertTrue(stages["plan-bounded-pcm-playback"]["native_implemented"])
        self.assertFalse(stages["plan-bounded-pcm-playback"]["writes_runtime_state"])
        self.assertEqual(
            stages["bounded-pcm-playback"]["command"],
            ["audio", "play", "internal-speaker-safe", "--mode", "probe", "--execute"],
        )
        self.assertTrue(stages["bounded-pcm-playback"]["native_implemented"])


if __name__ == "__main__":
    unittest.main()
