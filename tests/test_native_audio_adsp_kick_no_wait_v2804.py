"""Tests for the V2804 no-wait ADSP kick before audio play worker."""

from __future__ import annotations

import unittest
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2804_audio_adsp_kick_no_wait.py"
LIVE = REPO / "workspace/public/src/scripts/revalidation/native_audio_adsp_kick_no_wait_live_handoff_v2804.py"


def load_live_module():
    sys.path.insert(0, str(LIVE.parent))
    spec = importlib.util.spec_from_file_location("v2804_live", LIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioAdspKickNoWaitV2804(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = load_live_module()

    def test_play_execute_kicks_adsp_without_waiting_before_worker(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("audio_play_kick_adsp_stage_no_wait", text)
        self.assertIn("audio.play.execute.foreground_prime_adsp.wait=0", text)
        self.assertIn("prime_rc = audio_play_kick_adsp_stage_no_wait(profile);", text)
        self.assertIn("audio.play.worker.adsp_prebooted=%d", text)
        self.assertIn("audio.play.integrated.adsp_prebooted=%d", text)
        self.assertIn("audio.play.integrated.adsp.boot_skipped=1 reason=foreground_prime_no_wait", text)
        self.assertLess(
            text.index("prime_rc = audio_play_kick_adsp_stage_no_wait(profile);"),
            text.index('a90_console_printf("audio.play.execute.async_worker=1\\r\\n");'),
        )
        self.assertLess(
            text.index('a90_console_printf("audio.play.execute.async_worker=1\\r\\n");'),
            text.index("return audio_play_start_worker(profile, mode, amplitude_milli, duration_ms, manifest_path, true);"),
        )

    def test_integrated_worker_does_not_rewrite_adsp_after_preboot(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("audio_play_run_adsp_stage(profile, !adsp_prebooted)", text)
        self.assertIn("audio.play.integrated.adsp.boot_allowed=%d", text)
        self.assertIn("audio.play.integrated.adsp.boot_skipped=1 reason=foreground_prime_no_wait", text)
        self.assertIn(
            'audio_wait_for_audio_condition("sound_control", 70000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )

    def test_builder_uses_v2804_artifact_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('CYCLE = "V2804"', text)
        self.assertIn('INIT_VERSION = "0.9.314"', text)
        self.assertIn('INIT_BUILD = "v2804-audio-adsp-kick-no-wait"', text)
        self.assertIn('boot_linux_v2804_audio_adsp_kick_no_wait.img', text)
        self.assertIn("foreground_adsp_kick_no_wait_compiled", text)
        self.assertIn("v2803_blocker", text)

    def test_live_runner_targets_v2804_and_requires_no_wait_markers(self) -> None:
        module = self.live

        self.assertEqual(module.CYCLE, "V2804")
        self.assertEqual(module.CANDIDATE_VERSION, "0.9.314")
        self.assertEqual(module.CANDIDATE_TAG, "v2804-audio-adsp-kick-no-wait")
        self.assertIn("boot_linux_v2804_audio_adsp_kick_no_wait.img", str(module.CANDIDATE_IMAGE))
        self.assertIn("NATIVE_INIT_V2804_AUDIO_ADSP_KICK_NO_WAIT_LIVE", str(module.REPORT_PATH))

        summary = module.classify_play_output(
            "\n".join([
                "audio.play.execute.foreground_prime_adsp=1",
                "audio.play.execute.foreground_prime_adsp.wait=0",
                "audio.play.execute.foreground_prime_adsp.rc=0",
                "audio.play.worker.adsp_prebooted=1",
                "audio.play.integrated.adsp_prebooted=1",
                "audio.play.integrated.adsp.boot_skipped=1 reason=foreground_prime_no_wait",
                "audio.play.worker.started=1",
                "audio.play.worker.done=1 rc=0",
                "A90_LISTEN_WINDOW_BEGIN",
                "A90_LISTEN_WINDOW_END",
                "audio.play.integrated.done=1 rc=0",
                "audio.ion_materialize.version=1",
                "audio.ion_materialize.already_ok=1",
                "audio.setcal.execute.ion.alloc_ok=1",
                "audio.msm_audio_cal_materialize.version=1",
                "audio.msm_audio_cal_materialize.already_ok=1",
                "audio.setcal.execute.open.msm_audio_cal.open_ok=1",
                "audio.setcal.execute.hold_active=1",
                "audio.setcal.execute.set_count=11",
                "audio.setcal.execute.deallocated_count=4",
                "audio.play.integrated.route_apply.rc=0",
                "audio.play.integrated.route_reset.rc=0",
                "audio.play.execute.pcm_write_attempted=1",
                "audio.play.execute.done=1",
                "audio.play.safety.amplitude_within_cap=1",
                "audio.play.safety.duration_within_cap=1",
            ])
        )

        self.assertTrue(summary["foreground_prime_no_wait"], summary)
        self.assertTrue(summary["worker_adsp_prebooted"], summary)
        self.assertTrue(summary["worker_adsp_boot_skipped"], summary)
        self.assertTrue(module.play_output_pass(summary), summary)


if __name__ == "__main__":
    unittest.main()
