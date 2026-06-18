"""Tests for the V2791 integrated native audio playback path."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
AUDIO_STAGE_H = REPO / "workspace/public/src/native-init/a90_audio_stage.h"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2791_audio_integrated_play.py"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioIntegratedPlayV2791(unittest.TestCase):
    def test_default_manifest_and_integrated_sequence_are_pinned(self) -> None:
        text = source_text()

        stage_header = AUDIO_STAGE_H.read_text(encoding="utf-8")

        self.assertIn(
            '#define AUDIO_SETCAL_DEFAULT_MANIFEST_PATH "/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest"',
            stage_header,
        )
        self.assertNotIn("#define AUDIO_SETCAL_DEFAULT_MANIFEST_PATH", text)
        self.assertIn("audio.play.integrated_execute_supported=1", text)
        self.assertIn("audio.play.requires.adsp=1", text)
        self.assertIn("audio.play.requires.snd=1", text)
        self.assertIn("audio.play.requires.app_type=1", text)
        self.assertIn("audio.play.requires.setcal=1", text)
        self.assertIn("audio.play.requires.route=1", text)
        self.assertIn(
            "audio.play.execute.sequence=adsp,snd,app_type,setcal_hold,route_core,pcm,route_core_reset,setcal_deallocate",
            text,
        )

    def test_integrated_execute_wires_prereq_stages_around_pcm(self) -> None:
        text = source_text()
        start = text.index("static int audio_play_execute_integrated")
        end = text.index("static int audio_play_cmd", start)
        block = text[start:end]

        order = [
            "audio_play_run_adsp_stage(profile)",
            "audio_play_run_snd_stage(profile)",
            "audio_play_run_app_type_stage(profile)",
            "audio_play_load_setcal_session(profile, manifest_path, &setcal_session)",
            "audio_play_run_route_stage(profile, false)",
            "audio_play_execute_pcm(profile, mode, amplitude_milli, duration_ms)",
            "audio_play_run_route_stage(profile, true)",
            "audio_setcal_execute_session_cleanup(&setcal_session, rc, &ioctl_count)",
        ]
        last = -1
        for marker in order:
            with self.subTest(marker=marker):
                position = block.index(marker)
                self.assertGreater(position, last)
                last = position
        self.assertIn("audio.play.integrated.done=%d rc=%d", block)

    def test_setcal_session_holds_calibration_until_integrated_cleanup(self) -> None:
        text = source_text()

        self.assertIn("struct audio_setcal_execute_session", text)
        self.assertIn("audio_setcal_execute_session_start", text)
        self.assertIn("audio_setcal_execute_session_cleanup", text)
        self.assertIn("audio.setcal.execute.hold_active=1", text)
        self.assertRegex(
            text,
            re.compile(
                r"audio_setcal_execute_session_start\(session, &plan\).*?"
                r"audio\.play\.integrated\.setcal\.start_rc=%d",
                re.DOTALL,
            ),
        )

    def test_listen_window_markers_wrap_pcm_write(self) -> None:
        text = source_text()
        execute_start = text.index("static int audio_play_execute_pcm")
        execute_end = text.index("static void audio_play_print_execute_plan", execute_start)
        block = text[execute_start:execute_end]

        self.assertIn("A90_LISTEN_WINDOW_BEGIN", block)
        self.assertIn("A90_LISTEN_WINDOW_END", block)
        self.assertLess(block.index("A90_LISTEN_WINDOW_BEGIN"), block.index("audio_pcm_write_frames(fd"))
        self.assertIn("audio.play.execute.done", block)

    def test_builder_uses_next_patch_version_and_v2791_artifact_names(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('CYCLE = "V2791"', text)
        self.assertIn('INIT_VERSION = "0.9.304"', text)
        self.assertIn('INIT_BUILD = "v2791-audio-integrated-play"', text)
        self.assertIn("boot_linux_v2791_audio_integrated_play.img", text)
        self.assertIn("NATIVE_INIT_V2791_AUDIO_INTEGRATED_PLAY_SOURCE_BUILD_2026-06-19.md", text)
        self.assertIn('"integrated_play_executor_compiled": True', text)
        self.assertIn('"setcal_held_across_pcm": True', text)


if __name__ == "__main__":
    unittest.main()
