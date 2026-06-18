"""Tests for the V2786 audio route core apply/reset live validation runner."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "workspace/public/src/scripts/revalidation/native_audio_route_core_apply_device_validation_handoff_v2786.py"


def runner_text() -> str:
    return RUNNER.read_text(encoding="utf-8")


class NativeAudioRouteCoreApplyDeviceValidationV2786(unittest.TestCase):
    def test_runner_targets_v2786_image_and_rolls_back_v2321(self) -> None:
        text = runner_text()

        self.assertIn("v2786-audio-route-boolean-core/manifest.json", text)
        self.assertIn("boot_linux_v2786_audio_route_boolean_core.img", text)
        self.assertIn('CANDIDATE_VERSION = "0.9.300"', text)
        self.assertIn("boot_linux_v2321_usb_clean_identity_rodata.img", text)
        self.assertIn("ROLLBACK_SHA256", text)
        self.assertIn("native_init_flash.py", text)

    def test_runner_validates_core_apply_reset_markers(self) -> None:
        text = runner_text()

        for marker in [
            "audio.adsp_boot_once.write=accepted",
            "audio.snd_materialize.version=1",
            "audio.snd_materialize.open_attempted=0",
            "audio.snd_materialize.ioctl_attempted=0",
            "audio.snd_materialize.playback_attempted=0",
            "audio.route.version=1",
            "audio.route.mode=dry-run",
            "audio.route.mode=apply",
            "audio.route.mode=reset",
            "audio.route.layer=core",
            "audio.route.write_attempted=0",
            "audio.route.write_attempted=1",
            "audio.route.dry_run_ok=1",
            "audio.route.write_done count=6 layer=core mode=apply",
            "audio.route.write_done count=5 layer=core mode=reset",
            "audio.route.selected.smart_amp_boost_blocked=0",
            "v2786-audio-route-core-apply-device-pass",
            "sound_control_ready_after_adsp",
            "dev_snd_control_observed",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_runner_limits_writes_to_core_route_apply_reset(self) -> None:
        text = runner_text()

        self.assertIn('["audio", "adsp-boot-once", ADSP_TOKEN]', text)
        self.assertIn('["audio", "snd-materialize-once", SND_TOKEN]', text)
        self.assertIn("def run_a90ctl_step", text)
        self.assertIn("--input-mode", text)
        self.assertIn("slow", text)
        self.assertIn("sound_control_ready_before_adsp", text)
        self.assertIn("snd_materialize_skipped_already_ready", text)
        self.assertIn('["audio", "route", PROFILE, "--dry-run", "--layer", "core"]', text)
        self.assertIn('["audio", "route", PROFILE, "--apply", "--layer", "core"]', text)
        self.assertIn('["audio", "route", PROFILE, "--reset", "--layer", "core"]', text)
        self.assertNotIn('["audio", "status"]', text)
        self.assertNotIn('["audio", "profiles"]', text)
        self.assertNotIn('["audio", "profile", PROFILE]', text)
        self.assertNotIn('["audio", "speaker-map", PROFILE]', text)
        self.assertNotIn('["audio", "stages", PROFILE]', text)
        self.assertNotIn('["audio", "prereq", PROFILE]', text)
        self.assertNotIn('["audio", "play", PROFILE, "--mode", "probe", "--execute"]', text)
        self.assertNotIn('["audio", "setcal", PROFILE', text)
        self.assertNotIn('"--layer", "all"', text)
        self.assertNotIn('"--layer", "feedback"', text)
        self.assertNotIn('"--layer", "endpoint"', text)
        self.assertNotIn('"--layer", "blocked"', text)
        self.assertIn("No ACDB SET, PCM open, PCM write, or playback execute", text)

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
