"""Tests for the V2803 foreground ADSP prime before audio play worker."""

from __future__ import annotations

import unittest
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2803_audio_foreground_adsp_prime.py"
LIVE = REPO / "workspace/public/src/scripts/revalidation/native_audio_foreground_adsp_prime_live_handoff_v2803.py"


def load_live_module():
    sys.path.insert(0, str(LIVE.parent))
    spec = importlib.util.spec_from_file_location("v2803_live", LIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioForegroundAdspPrimeV2803(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = load_live_module()

    def test_audio_play_execute_primes_adsp_before_worker(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("audio.play.execute.plan.foreground_prime_adsp=1", text)
        self.assertIn("audio.play.execute.foreground_prime_adsp=1", text)
        self.assertIn("prime_rc = audio_play_run_adsp_stage(profile);", text)
        self.assertIn("audio.play.execute.foreground_prime_adsp.rc=%d", text)
        self.assertIn("audio.play.execute.foreground_prime_adsp.failed=1", text)
        self.assertLess(
            text.index("prime_rc = audio_play_run_adsp_stage(profile);"),
            text.index('a90_console_printf("audio.play.execute.async_worker=1\\r\\n");'),
        )
        self.assertLess(
            text.index('a90_console_printf("audio.play.execute.async_worker=1\\r\\n");'),
            text.index("return audio_play_start_worker(profile, mode, amplitude_milli, duration_ms, manifest_path);"),
        )

    def test_worker_stage_remains_idempotent_after_foreground_prime(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("audio.play.integrated.adsp.already_ready=1", text)
        self.assertIn("rc = audio_adsp_boot_once(adsp_argv, 3);", text)
        self.assertIn("if (rc == -EALREADY)", text)
        self.assertIn(
            'audio_wait_for_audio_condition("sound_control", 70000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )

    def test_builder_uses_v2803_artifact_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('CYCLE = "V2803"', text)
        self.assertIn('INIT_VERSION = "0.9.313"', text)
        self.assertIn('INIT_BUILD = "v2803-audio-foreground-adsp-prime"', text)
        self.assertIn('boot_linux_v2803_audio_foreground_adsp_prime.img', text)
        self.assertIn("foreground_adsp_prime_compiled", text)
        self.assertIn("v2802_blocker", text)

    def test_live_runner_targets_v2803_and_requires_prime_markers(self) -> None:
        module = self.live

        self.assertEqual(module.CYCLE, "V2803")
        self.assertEqual(module.CANDIDATE_VERSION, "0.9.313")
        self.assertEqual(module.CANDIDATE_TAG, "v2803-audio-foreground-adsp-prime")
        self.assertIn("boot_linux_v2803_audio_foreground_adsp_prime.img", str(module.CANDIDATE_IMAGE))
        self.assertIn("NATIVE_INIT_V2803_AUDIO_FOREGROUND_ADSP_PRIME_LIVE", str(module.REPORT_PATH))

        summary = module.classify_play_output(
            "\n".join([
                "audio.play.execute.foreground_prime_adsp=1",
                "audio.play.execute.foreground_prime_adsp.rc=0",
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

        self.assertTrue(summary["foreground_prime_seen"], summary)
        self.assertTrue(summary["foreground_prime_ok"], summary)
        self.assertFalse(summary["foreground_prime_failed"], summary)
        self.assertTrue(module.play_output_pass(summary), summary)


if __name__ == "__main__":
    unittest.main()
