"""Regression tests for the superseded V2767 SET-cal open-only boundary."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalOpenBoundaryV2767(unittest.TestCase):
    def test_open_only_boundary_helpers_are_removed_after_native_replay_lands(self) -> None:
        text = source_text()

        for stale_marker in [
            "struct audio_setcal_execute_open_state",
            "audio_setcal_execute_open_state_reset",
            "audio_setcal_open_execute_device",
            "audio_setcal_open_execute_devices",
            "audio_setcal_close_execute_devices",
            "execute-open-failed-before-ioctl",
        ]:
            with self.subTest(stale_marker=stale_marker):
                self.assertNotIn(stale_marker, text)

    def test_execute_uses_manifest_plan_directly_for_native_replay(self) -> None:
        text = source_text()
        cmd_start = text.index("static int audio_setcal_cmd")
        cmd_end = text.index("static bool audio_parse_nonnegative_int", cmd_start)
        cmd_block = text[cmd_start:cmd_end]

        verify = cmd_block.index("verify_rc = audio_setcal_verify_manifest")
        plan = cmd_block.index("audio_setcal_print_execute_plan(profile, manifest_plan)")
        replay = cmd_block.index("audio_setcal_execute_manifest_plan(manifest_plan, &ioctl_count)")

        self.assertLess(verify, plan)
        self.assertLess(plan, replay)
        self.assertIn("audio.setcal.execute_native_replay_supported", cmd_block)
        self.assertIn("audio.setcal.ioctl_attempted=0", cmd_block)
        self.assertNotIn("execute-not-implemented-native-setcal-ioctl", cmd_block)


if __name__ == "__main__":
    unittest.main()
