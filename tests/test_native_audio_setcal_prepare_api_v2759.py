"""Tests for the V2759 audio SET-cal prepare dry-run API."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from _loader import load_revalidation

profiles = load_revalidation("native_audio_speaker_profiles_v2749")

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalPrepareApiV2759(unittest.TestCase):
    def test_prepare_option_is_exposed_and_requires_manifest(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[argi], "--prepare") == 0', text)
        self.assertIn("prepare_manifest = true", text)
        self.assertIn("audio.setcal.prepare_requested", text)
        self.assertIn("manifest-required-for-verify-or-prepare", text)

    def test_prepare_includes_verify_then_prints_byte_plan(self) -> None:
        text = source_text()

        self.assertIn("verify_manifest || prepare_manifest", text)
        self.assertIn("struct audio_setcal_manifest_totals", text)
        for marker in [
            "audio.setcal.prepare.entry.count",
            "audio.setcal.prepare.arg_entries",
            "audio.setcal.prepare.payload_entries",
            "audio.setcal.prepare.arg_bytes",
            "audio.setcal.prepare.payload_bytes",
            "audio.setcal.prepare_ok=1",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_prepare_does_not_open_audio_devices_or_issue_ioctls(self) -> None:
        text = source_text()
        prepare_start = text.index("if (prepare_manifest)")
        execute_refusal = text.index("audio.setcal.refused=execute-not-implemented-native-setcal-ioctl")
        prepare_block = text[prepare_start:execute_refusal]

        self.assertIn("audio.setcal.prepare.devices_opened=0", prepare_block)
        self.assertIn("audio.setcal.prepare.ioctl_attempted=0", prepare_block)
        self.assertNotIn("open(", prepare_block)
        self.assertNotIn("ioctl(", prepare_block)
        self.assertNotIn("AUDIO_SET_CALIBRATION", prepare_block)

    def test_prepare_stage_is_between_verify_and_replay(self) -> None:
        stages = {stage["stage_id"]: stage for stage in profiles.stage_manifests()}

        self.assertLess(stages["verify-private-acdb-manifest"]["order"], stages["prepare-acdb-payload-bundle"]["order"])
        self.assertLess(stages["prepare-acdb-payload-bundle"]["order"], stages["replay-acdb-setcal-sequence"]["order"])
        self.assertEqual(
            stages["prepare-acdb-payload-bundle"]["command"],
            [
                "audio",
                "setcal",
                "internal-speaker-safe",
                "--manifest",
                profiles.DEFAULT_SETCAL_MANIFEST_PATH,
                "--prepare",
                "--dry-run",
            ],
        )

    def test_replay_execute_remains_blocked_after_prepare(self) -> None:
        text = source_text()

        self.assertRegex(
            text,
            re.compile(r'if \(execute_mode\).*?execute-not-implemented-native-setcal-ioctl.*?return -EPERM;', re.DOTALL),
        )


if __name__ == "__main__":
    unittest.main()
