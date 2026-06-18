"""Tests for the V2763 native audio SET-cal execute-gate API."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalExecuteGateV2763(unittest.TestCase):
    def test_execute_requires_manifest_and_auto_loads_private_payloads(self) -> None:
        text = source_text()

        self.assertIn("audio.setcal.execute_manifest_required", text)
        self.assertIn("audio.setcal.execute_auto_load", text)
        self.assertIn("manifest-required-for-execute", text)
        self.assertIn("manifest_action_requested = verify_manifest || prepare_manifest || load_manifest || execute_mode", text)
        self.assertIn("load_files = load_manifest || execute_mode", text)

    def test_execute_plan_publishes_ioctl_abi_without_calling_it(self) -> None:
        text = source_text()
        plan_start = text.index("static void audio_setcal_print_execute_plan")
        plan_end = text.index("static int audio_setcal_cmd")
        plan_block = text[plan_start:plan_end]

        for marker in [
            "AUDIO_SETCAL_IOCTL_ALLOCATE_CALIBRATION 0xC00461C8u",
            "AUDIO_SETCAL_IOCTL_DEALLOCATE_CALIBRATION 0xC00461C9u",
            "AUDIO_SETCAL_IOCTL_SET_CALIBRATION 0xC00461CBu",
            "audio.setcal.execute.plan.ioctl.allocate",
            "audio.setcal.execute.plan.ioctl.set",
            "audio.setcal.execute.plan.ioctl.deallocate",
            "audio.setcal.execute.plan.sequence=open_ion,open_msm_audio_cal,allocate_payload_entries,set_entries_in_order,hold_fds,deallocate_payload_entries_reverse,close_fds",
            "audio.setcal.execute.plan.devices_opened=0",
            "audio.setcal.execute.plan.ioctl_attempted=0",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertNotIn("open(", plan_block)
        self.assertNotIn("ioctl(", plan_block)

    def test_execute_refusal_happens_after_verify_load_and_plan(self) -> None:
        text = source_text()

        verify_call = text.index("verify_rc = audio_setcal_verify_manifest")
        plan_call = text.index("audio_setcal_print_execute_plan(profile, &totals, &load_totals)")
        refusal = text.index("audio.setcal.refused=execute-not-implemented-native-setcal-ioctl")

        self.assertLess(verify_call, plan_call)
        self.assertLess(plan_call, refusal)
        self.assertRegex(
            text,
            re.compile(r'if \(execute_mode\).*?audio_setcal_print_execute_plan.*?execute-not-implemented-native-setcal-ioctl.*?return -EPERM;', re.DOTALL),
        )


if __name__ == "__main__":
    unittest.main()
