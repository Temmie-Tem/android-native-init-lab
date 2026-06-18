"""Tests for the native audio PCM play execute path."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioPlayExecuteGateV2765(unittest.TestCase):
    def test_play_execute_gate_pins_pcm_geometry(self) -> None:
        text = source_text()

        for marker in [
            "#define AUDIO_PCM_PERIOD_SIZE 1024",
            "#define AUDIO_PCM_PERIOD_COUNT 4",
            "audio_play_frame_bytes",
            "audio_play_data_bytes",
            "audio.play.execute.plan.period_size",
            "audio.play.execute.plan.period_count",
            "audio.play.execute.plan.frame_bytes",
            "audio.play.execute.plan.period_bytes",
            "audio.play.execute.plan.data_bytes",
            "audio.play.execute.plan.chunks",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_play_execute_plan_reports_pcm_path_and_waveform(self) -> None:
        text = source_text()
        plan_start = text.index("static void audio_play_print_execute_plan")
        plan_end = text.index("static int audio_play_cmd")
        plan_block = text[plan_start:plan_end]

        for marker in [
            "/dev/snd/pcmC%dD%dp",
            "audio.play.execute.plan.pcm_path",
            "audio.play.execute.plan.waveform=s16le-stereo-bounded-tone",
            "audio.play.execute.plan.sequence=open_pcm,configure_hw_params,write_bounded_tone,drain,close_pcm",
            "audio.play.execute.plan.alsa_open_attempted=0",
            "audio.play.execute.plan.ioctl_attempted=0",
            "audio.play.execute.plan.pcm_write_attempted=0",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertNotIn("open(", plan_block)
        self.assertNotIn("ioctl(", plan_block)
        self.assertNotIn("write(", plan_block)

    def test_play_execute_uses_integrated_sequence_after_cap_checks_and_plan(self) -> None:
        text = source_text()

        cap_check = text.index("audio.play.refused=safety-cap-exceeded")
        plan_call = text.index("audio_play_print_execute_plan(profile, mode, amplitude_milli, duration_ms)")
        integrated_call = text.index("return audio_play_execute_integrated(profile, mode, amplitude_milli, duration_ms, manifest_path)")

        self.assertLess(cap_check, plan_call)
        self.assertLess(plan_call, integrated_call)
        self.assertNotIn("execute-not-implemented-native-pcm", text)
        self.assertNotIn("audio.play.refused=missing-pcm-node", text)
        self.assertRegex(
            text,
            re.compile(
                r'if \(execute_mode\).*?audio_play_print_execute_plan.*?audio.play.initial_pcm_node_ready=.*?return audio_play_execute_integrated',
                re.DOTALL,
            ),
        )

    def test_play_execute_reports_and_materializes_snd_prerequisite(self) -> None:
        text = source_text()

        for marker in [
            "audio_play_print_pcm_prereq",
            "audio.play.requires.snd=1",
            'audio_print_pcm_prereq("audio.play.prereq"',
            "%s.pcm_path=%s",
            "%s.pcm_node.state=%s",
            "%s.pcm_node.ready=%d",
            "%s.snd_materialize_command=audio snd-materialize-once %s",
            "audio.play.initial_pcm_node_ready=%d",
            "audio_play_run_snd_stage",
            "audio_snd_materialize_once",
            "audio.play.alsa_open_attempted=0",
            "audio.play.ioctl_attempted=0",
            "audio.play.execute.plan.pcm_write_attempted=0",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_pcm_writer_is_bounded_and_uses_kernel_pcm_ioctls(self) -> None:
        text = source_text()
        execute_start = text.index("static int audio_play_execute_pcm")
        execute_end = text.index("static void audio_play_print_execute_plan")
        execute_block = text[execute_start:execute_end]

        for marker in [
            "AUDIO_PCM_MAX_CHANNELS 8",
            "AUDIO_PCM_TONE_HZ 440",
            "SNDRV_PCM_IOCTL_HW_PARAMS",
            "SNDRV_PCM_IOCTL_SW_PARAMS",
            "SNDRV_PCM_IOCTL_PREPARE",
            "SNDRV_PCM_IOCTL_WRITEI_FRAMES",
            "SNDRV_PCM_IOCTL_DRAIN",
            "audio.play.execute.alsa_open_attempted=1",
            "audio.play.execute.ioctl_attempted=1",
            "audio.play.execute.pcm_write_attempted=1",
            "audio.play.execute.done",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertIn("profile->bit_width != 16", execute_block)
        self.assertIn("profile->channels > AUDIO_PCM_MAX_CHANNELS", execute_block)


if __name__ == "__main__":
    unittest.main()
