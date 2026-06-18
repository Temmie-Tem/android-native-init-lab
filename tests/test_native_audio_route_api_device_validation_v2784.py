"""Tests for the V2784 audio route API live validation runner."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "workspace/public/src/scripts/revalidation/native_audio_route_api_device_validation_handoff_v2784.py"


def runner_text() -> str:
    return RUNNER.read_text(encoding="utf-8")


class NativeAudioRouteApiDeviceValidationV2784(unittest.TestCase):
    def test_runner_targets_v2783_image_and_rolls_back_v2321(self) -> None:
        text = runner_text()

        self.assertIn("v2783-audio-route-api/manifest.json", text)
        self.assertIn("boot_linux_v2783_audio_route_api.img", text)
        self.assertIn('CANDIDATE_VERSION = "0.9.299"', text)
        self.assertIn("boot_linux_v2321_usb_clean_identity_rodata.img", text)
        self.assertIn("ROLLBACK_SHA256", text)
        self.assertIn("native_init_flash.py", text)

    def test_runner_validates_route_api_markers(self) -> None:
        text = runner_text()

        for marker in [
            "audio.speaker_map.version=1",
            "audio.speaker_map.read_only=1",
            "audio.speaker_map.route_write_attempted=0",
            "audio.speaker_map.speaker.4.id=SpkrLeft",
            "audio.speaker_map.speaker.5.id=SpkrRight",
            "audio.route.version=1",
            "audio.route.mode=dry-run",
            "audio.route.layer=all",
            "audio.route.layer=core",
            "audio.route.write_attempted=0",
            "audio.route.dry_run_ok=1",
            "v2784-audio-route-api-device-pass",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_runner_stays_read_only_for_audio_validation(self) -> None:
        text = runner_text()

        self.assertIn('["audio", "speaker-map", PROFILE]', text)
        self.assertIn('["audio", "route", PROFILE, "--dry-run", "--layer", "all"]', text)
        self.assertIn('["audio", "route", PROFILE, "--dry-run", "--layer", "core"]', text)
        self.assertIn('["audio", "play", PROFILE, "--mode", "probe", "--dry-run"]', text)
        self.assertNotIn('["audio", "play", PROFILE, "--mode", "probe", "--execute"]', text)
        self.assertNotIn('["audio", "route", PROFILE, "--apply"', text)
        self.assertNotIn('["audio", "setcal", PROFILE', text)
        self.assertIn("No audio route apply, ACDB SET, PCM open, mixer write, or playback execute", text)

    def test_runner_accepts_structured_selftest_protocol_fallback(self) -> None:
        text = runner_text()

        self.assertIn("def protocol_selftest_ok", text)
        self.assertIn("def selftest_step_ok", text)
        self.assertIn('end.get("cmd") == "selftest"', text)
        self.assertIn('end.get("rc") == "0"', text)
        self.assertIn("candidate_selftest_used_protocol_fallback", text)
        self.assertIn("if not selftest_step_ok(candidate_selftest)", text)

    def test_runner_has_recovery_mode_rollback_fallback(self) -> None:
        text = runner_text()

        self.assertIn("def adb_recovery_present", text)
        self.assertIn('["adb", "devices"]', text)
        self.assertIn("def rollback_v2321", text)
        self.assertIn('"rollback-v2321-recovery-fallback"', text)
        self.assertIn("flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False)", text)
        self.assertIn("rollback_recovery_fallback_used", text)


if __name__ == "__main__":
    unittest.main()
