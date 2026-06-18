"""Tests for the V2761 native audio play planning API."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from _loader import load_revalidation

profiles = load_revalidation("native_audio_speaker_profiles_v2749")

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioPlayPlanApiV2761(unittest.TestCase):
    def test_play_subcommand_is_exposed_as_first_class_audio_api(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "play") == 0', text)
        self.assertIn("return audio_play_cmd(argv, argc);", text)
        self.assertIn("usage: audio play [profile] [--mode probe|listen]", text)
        self.assertIn("audio.play.version=1", text)
        self.assertIn("audio.play.execute_supported=0", text)

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
        play_end = text.index("static int audio_open_control_device")
        play_block = text[play_start:play_end]

        self.assertIn("audio.play.alsa_open_attempted=0", play_block)
        self.assertIn("audio.play.ioctl_attempted=0", play_block)
        self.assertIn("audio.play.playback_attempted=0", play_block)
        self.assertNotIn("open(", play_block)
        self.assertNotIn("ioctl(", play_block)
        self.assertNotIn("SNDRV_PCM", play_block)

    def test_play_refuses_execute_and_cap_violations_before_playback(self) -> None:
        text = source_text()

        self.assertIn("audio.play.refused=safety-cap-exceeded", text)
        self.assertIn("audio.play.refused=execute-not-implemented-native-pcm", text)
        self.assertRegex(
            text,
            re.compile(r'if \(execute_mode\).*?execute-not-implemented-native-pcm.*?return -EPERM;', re.DOTALL),
        )

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
        self.assertFalse(stages["bounded-pcm-playback"]["native_implemented"])


if __name__ == "__main__":
    unittest.main()
