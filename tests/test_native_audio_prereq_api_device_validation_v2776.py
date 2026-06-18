"""Tests for the V2776 audio prereq API live validation runner."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "workspace/public/src/scripts/revalidation/native_audio_prereq_api_device_validation_handoff_v2776.py"


def runner_text() -> str:
    return RUNNER.read_text(encoding="utf-8")


class NativeAudioPrereqApiDeviceValidationV2776(unittest.TestCase):
    def test_runner_targets_v2775_image_and_rolls_back_v2321(self) -> None:
        text = runner_text()

        self.assertIn("v2775-audio-prereq-api/manifest.json", text)
        self.assertIn("boot_linux_v2775_audio_prereq_api.img", text)
        self.assertIn('CANDIDATE_VERSION = "0.9.296"', text)
        self.assertIn("boot_linux_v2321_usb_clean_identity_rodata.img", text)
        self.assertIn("ROLLBACK_SHA256", text)
        self.assertIn("native_init_flash.py", text)

    def test_runner_validates_prereq_markers(self) -> None:
        text = runner_text()

        for marker in [
            "audio.prereq.version=1",
            "audio.prereq.read_only=1",
            "audio.prereq.write_attempted=0",
            "audio.prereq.playback_attempted=0",
            "audio.prereq.stage_order=boot,adsp,snd,app_type,setcal,route,pcm,cleanup,rollback",
            "audio.prereq.ready.runtime_state_verified=0",
            "v2776-audio-prereq-api-device-pass",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_runner_stays_read_only_for_audio_validation(self) -> None:
        text = runner_text()

        self.assertIn('["audio", "prereq", PROFILE]', text)
        self.assertIn('["audio", "play", PROFILE, "--mode", "probe", "--dry-run"]', text)
        self.assertNotIn('["audio", "play", PROFILE, "--mode", "probe", "--execute"]', text)
        self.assertNotIn('["audio", "route", PROFILE, "--apply"', text)
        self.assertNotIn('["audio", "setcal", PROFILE', text)
        self.assertIn("No audio route apply, ACDB SET, PCM open, mixer write, or playback execute", text)


if __name__ == "__main__":
    unittest.main()
