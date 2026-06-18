"""Tests for the V2767 audio SET-cal execute open-only boundary."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalOpenBoundaryV2767(unittest.TestCase):
    def test_execute_open_state_tracks_only_runtime_device_fds(self) -> None:
        text = source_text()

        for marker in [
            "struct audio_setcal_execute_open_state",
            "int ion_fd",
            "int msm_audio_cal_fd",
            "int devices_opened",
            "audio_setcal_execute_open_state_reset",
            "state->ion_fd = -1",
            "state->msm_audio_cal_fd = -1",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_open_boundary_opens_only_ion_and_msm_audio_cal_with_no_ioctl(self) -> None:
        text = source_text()
        helper_start = text.index("static int audio_setcal_open_execute_devices")
        helper_end = text.index("static void audio_setcal_close_execute_devices", helper_start)
        helper_block = text[helper_start:helper_end]

        for marker in [
            "audio.setcal.execute.open.version=1",
            "audio.setcal.execute.open.ioctl_attempted=0",
            "audio_setcal_open_execute_device(\"audio.setcal.execute.open.ion\"",
            "AUDIO_SETCAL_DEV_ION",
            "audio_setcal_open_execute_device(\"audio.setcal.execute.open.msm_audio_cal\"",
            "AUDIO_SETCAL_DEV_MSM_AUDIO_CAL",
            "audio.setcal.execute.open.devices_opened",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, helper_block)
        self.assertNotIn("ioctl(", helper_block)
        self.assertNotIn("AUDIO_SETCAL_IOCTL_SET_CALIBRATION", helper_block)

    def test_single_device_open_uses_rdwr_cloexec_and_reports_errno(self) -> None:
        text = source_text()
        helper_start = text.index("static int audio_setcal_open_execute_device")
        helper_end = text.index("static void audio_setcal_close_execute_device", helper_start)
        helper_block = text[helper_start:helper_end]

        self.assertIn("open(path, O_RDWR | O_CLOEXEC)", helper_block)
        self.assertIn("%s.flags=O_RDWR|O_CLOEXEC", helper_block)
        self.assertIn("%s.open_attempted=1", helper_block)
        self.assertIn("%s.open_ok=0 errno=%d", helper_block)
        self.assertIn("%s.open_ok=1", helper_block)
        self.assertNotIn("ioctl(", helper_block)

    def test_execute_calls_open_boundary_after_verified_manifest_plan(self) -> None:
        text = source_text()
        cmd_start = text.index("static int audio_setcal_cmd")
        cmd_end = text.index("static bool audio_parse_nonnegative_int", cmd_start)
        cmd_block = text[cmd_start:cmd_end]

        verify = cmd_block.index("verify_rc = audio_setcal_verify_manifest")
        plan = cmd_block.index("audio_setcal_print_execute_plan(profile, manifest_plan)")
        open_call = cmd_block.index("open_rc = audio_setcal_open_execute_devices(&execute_open_state)")
        close_call = cmd_block.index("audio_setcal_close_execute_devices(&execute_open_state)")
        refusal = cmd_block.index("execute-not-implemented-native-setcal-ioctl")

        self.assertLess(verify, plan)
        self.assertLess(plan, open_call)
        self.assertLess(open_call, close_call)
        self.assertLess(close_call, refusal)
        self.assertIn("audio.setcal.execute_open_boundary_supported", cmd_block)
        self.assertIn("execute-open-failed-before-ioctl", cmd_block)
        self.assertIn("audio.setcal.ioctl_attempted=0", cmd_block)
        self.assertRegex(cmd_block, re.compile(r"if \(open_rc < 0\).*?return open_rc;", re.DOTALL))

    def test_close_boundary_clears_fds_and_keeps_ioctl_zero(self) -> None:
        text = source_text()
        close_start = text.index("static void audio_setcal_close_execute_devices")
        close_end = text.index("static int audio_setcal_cmd", close_start)
        close_block = text[close_start:close_end]

        self.assertIn("audio.setcal.execute.close.msm_audio_cal", close_block)
        self.assertIn("audio.setcal.execute.close.ion", close_block)
        self.assertIn("audio.setcal.execute.close.fds_held=0", close_block)
        self.assertIn("audio.setcal.execute.close.ioctl_attempted=0", close_block)
        self.assertNotIn("ioctl(", close_block)


if __name__ == "__main__":
    unittest.main()
