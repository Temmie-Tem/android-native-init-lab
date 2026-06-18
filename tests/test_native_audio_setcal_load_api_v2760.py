"""Tests for the V2760 audio SET-cal file-load dry-run API."""

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


class NativeAudioSetcalLoadApiV2760(unittest.TestCase):
    def test_load_option_is_exposed_as_manifest_backed_dry_run(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[argi], "--load") == 0', text)
        self.assertIn("load_manifest = true", text)
        self.assertIn("audio.setcal.load_requested", text)
        self.assertIn("manifest-required-for-verify-prepare-or-load", text)
        self.assertIn("audio.setcal.load.requested", text)

    def test_load_stage_is_between_prepare_and_replay(self) -> None:
        stages = {stage["stage_id"]: stage for stage in profiles.stage_manifests()}

        self.assertLess(stages["prepare-acdb-payload-bundle"]["order"], stages["load-acdb-payload-files"]["order"])
        self.assertLess(stages["load-acdb-payload-files"]["order"], stages["replay-acdb-setcal-sequence"]["order"])
        self.assertEqual(
            stages["load-acdb-payload-files"]["command"],
            [
                "audio",
                "setcal",
                "internal-speaker-safe",
                "--manifest",
                profiles.DEFAULT_SETCAL_MANIFEST_PATH,
                "--load",
                "--dry-run",
            ],
        )
        self.assertTrue(stages["load-acdb-payload-files"]["native_implemented"])
        self.assertFalse(stages["load-acdb-payload-files"]["writes_runtime_state"])

    def test_load_opens_only_manifest_files_and_drains_them(self) -> None:
        text = source_text()
        helper_start = text.index("static int audio_setcal_load_regular_file")
        helper_end = text.index("static int audio_setcal_verify_manifest_entry")
        helper_block = text[helper_start:helper_end]

        self.assertIn("open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW)", helper_block)
        self.assertIn("fstat(fd, &st)", helper_block)
        self.assertIn("S_ISREG(st.st_mode)", helper_block)
        self.assertIn("read(fd, buffer, sizeof(buffer))", helper_block)
        self.assertIn("bytes_read", helper_block)
        self.assertNotIn("ioctl(", helper_block)
        self.assertNotIn("/dev/ion", helper_block)
        self.assertNotIn("/dev/msm_audio_cal", helper_block)

    def test_load_summary_keeps_audio_devices_and_ioctls_zero(self) -> None:
        text = source_text()
        load_summary = text[text.index("if (load_manifest)"):text.index("if (execute_mode)")]

        for marker in [
            "audio.setcal.load.entry.count",
            "audio.setcal.load.arg_entries",
            "audio.setcal.load.payload_entries",
            "audio.setcal.load.files_opened",
            "audio.setcal.load.arg_bytes",
            "audio.setcal.load.payload_bytes",
            "audio.setcal.load.devices_opened=0",
            "audio.setcal.load.ioctl_attempted=0",
            "audio.setcal.load_ok=1",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, load_summary)
        self.assertNotIn("ioctl(", load_summary)
        self.assertNotIn("AUDIO_SET_CALIBRATION", load_summary)

    def test_execute_remains_blocked_after_load_api(self) -> None:
        text = source_text()

        self.assertRegex(
            text,
            re.compile(r'if \(execute_mode\).*?execute-not-implemented-native-setcal-ioctl.*?return -EPERM;', re.DOTALL),
        )


if __name__ == "__main__":
    unittest.main()
