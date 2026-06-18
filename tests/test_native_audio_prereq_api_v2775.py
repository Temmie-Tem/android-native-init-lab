"""Tests for the V2775 native audio prerequisite API."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioPrereqApiV2775(unittest.TestCase):
    def test_prereq_command_is_dispatchable_and_read_only(self) -> None:
        text = source_text()

        self.assertRegex(text, r'strcmp\(argv\[1\], "prereq"\) == 0')
        self.assertIn("static int audio_prereq_cmd", text)
        for marker in [
            "audio.prereq.version=1",
            "audio.prereq.read_only=1",
            "audio.prereq.write_attempted=0",
            "audio.prereq.playback_attempted=0",
            "usage: audio prereq",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_prereq_api_exports_ordered_callable_stages(self) -> None:
        text = source_text()

        for marker in [
            "audio.prereq.stage_order=boot,adsp,snd,app_type,setcal,route,pcm,cleanup,rollback",
            "audio.prereq.adsp.command=audio adsp-boot-once",
            "audio.prereq.snd.required=1",
            "audio.prereq.app_type.command=audio app-type %s --write",
            "audio.prereq.setcal.command=audio setcal %s --manifest %s --execute",
            "audio.prereq.route.command=audio route %s --apply --layer core",
            "audio.prereq.play.command=audio play %s --mode probe --execute",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_prereq_reuses_pcm_prereq_helper_with_distinct_prefixes(self) -> None:
        text = source_text()

        self.assertIn("static bool audio_print_pcm_prereq", text)
        self.assertIn('audio_print_pcm_prereq("audio.play.prereq"', text)
        self.assertIn('audio_print_pcm_prereq("audio.prereq.snd"', text)
        for marker in [
            "%s.pcm_path=%s",
            "%s.pcm_node.state=%s",
            "%s.pcm_node.ready=%d",
            "%s.snd_materialize_command=audio snd-materialize-once %s",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_prereq_does_not_claim_runtime_state_is_verified(self) -> None:
        text = source_text()
        prereq_start = text.index("static int audio_prereq_cmd")
        prereq_end = text.index("static bool audio_pcm_param_is_mask")
        block = text[prereq_start:prereq_end]

        self.assertIn("audio.prereq.ready.snd=%d", block)
        self.assertIn("audio.prereq.ready.runtime_state_verified=0", block)
        self.assertIn("audio.prereq.ready.play=0", block)
        self.assertNotIn("open(", block)
        self.assertNotIn("ioctl(", block)
        self.assertNotIn("write(", block)


if __name__ == "__main__":
    unittest.main()
