"""Tests for the V2762 native audio stop planning API."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation

profiles = load_revalidation("native_audio_speaker_profiles_v2749")

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioStopPlanApiV2762(unittest.TestCase):
    def test_stop_subcommand_is_exposed_as_first_class_audio_api(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "stop") == 0', text)
        self.assertIn("return audio_stop_cmd(argv, argc);", text)
        self.assertIn("usage: audio stop [profile] [--dry-run|--execute]", text)
        self.assertIn("audio.stop.version=1", text)
        self.assertIn("audio.stop.execute_supported=1", text)

    def test_stop_plan_names_cleanup_requirements(self) -> None:
        text = source_text()

        for marker in [
            "audio.stop.requires.pcm_stop=1",
            "audio.stop.requires.setcal_deallocate_reverse=1",
            "audio.stop.requires.route_reset_playback=1",
            "audio.stop.route_reset_command=audio route %s --reset --layer playback",
            "audio.stop.setcal_deallocate_order",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_stop_dry_run_does_not_touch_alsa_or_calibration(self) -> None:
        text = source_text()
        stop_start = text.index("static int audio_stop_cmd")
        stop_end = text.index("static int audio_open_control_device")
        stop_block = text[stop_start:stop_end]

        self.assertIn("audio.stop.playback_stop_attempted=0", stop_block)
        self.assertIn("audio.stop.setcal_deallocate_attempted=0", stop_block)
        self.assertIn("audio.stop.route_write_attempted=0", stop_block)
        self.assertIn("audio.stop.ioctl_attempted=0", stop_block)
        self.assertNotIn("open(", stop_block)
        self.assertNotIn("ioctl(", stop_block)
        self.assertNotIn("AUDIO_DEALLOCATE_CALIBRATION", stop_block)
        self.assertNotIn("SNDRV_CTL_IOCTL_ELEM_WRITE", stop_block)

    def test_stop_execute_runs_playback_route_reset_only(self) -> None:
        text = source_text()
        stop_start = text.index("static int audio_stop_cmd")
        stop_end = text.index("static int audio_open_control_device")
        stop_block = text[stop_start:stop_end]

        self.assertNotIn("execute-not-implemented-native-cleanup", stop_block)
        self.assertIn("audio.stop.playback_stop_reason=no-active-pcm-handle", stop_block)
        self.assertIn("audio.stop.setcal_deallocate_reason=no-active-setcal-session", stop_block)
        self.assertIn("audio.stop.route_write_attempted=1", stop_block)
        self.assertIn("audio.stop.ioctl_attempted=1", stop_block)
        self.assertIn('route_argv[3] = "--reset";', stop_block)
        self.assertIn('route_argv[5] = "playback";', stop_block)
        self.assertIn("route_rc = audio_route_cmd(route_argv, 6);", stop_block)
        self.assertIn("audio.stop.route_reset_rc=%d", stop_block)
        self.assertIn("audio.stop.done=%d rc=%d", stop_block)
        self.assertNotIn("AUDIO_DEALLOCATE_CALIBRATION", stop_block)

    def test_stage_api_places_stop_plan_before_route_reset(self) -> None:
        stages = {stage["stage_id"]: stage for stage in profiles.stage_manifests()}

        self.assertLess(stages["bounded-pcm-playback"]["order"], stages["plan-audio-stop-cleanup"]["order"])
        self.assertLess(stages["plan-audio-stop-cleanup"]["order"], stages["reset-playback-speaker-route"]["order"])
        self.assertEqual(stages["plan-audio-stop-cleanup"]["command"], ["audio", "stop", "internal-speaker-safe", "--dry-run"])
        self.assertTrue(stages["plan-audio-stop-cleanup"]["native_implemented"])
        self.assertFalse(stages["plan-audio-stop-cleanup"]["writes_runtime_state"])


if __name__ == "__main__":
    unittest.main()
