"""Tests for V2841 audio chime screen live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2841 = importlib.import_module("native_audio_chime_screen_live_handoff_v2841")


class NativeAudioChimeScreenLiveHandoffV2841Test(unittest.TestCase):
    def test_wrapper_targets_v2840_chime_screen_candidate(self) -> None:
        self.assertEqual(v2841.CYCLE, "V2841")
        self.assertEqual(v2841.CANDIDATE_VERSION, "0.10.11")
        self.assertEqual(v2841.CANDIDATE_TAG, "v2840-audio-chime-screen")
        self.assertIn("v2840-audio-chime-screen", str(v2841.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2840_audio_chime_screen.img", str(v2841.CANDIDATE_IMAGE))

    def test_screenapp_chime_markers_are_required(self) -> None:
        self.assertEqual(v2841.SCREENAPP_COMMAND, ["screenapp", "audio-chime"])
        markers = v2841.REQUIRED_SCREENAPP_MARKERS
        self.assertIn("screenapp.app=audio-chime", markers)
        self.assertIn("screenapp.title=AUDIO CHIME", markers)
        self.assertIn("screenapp.presented=1", markers)

    def test_report_names_display_only_chime_validation(self) -> None:
        rendered = v2841.render_report({
            "decision": "v2841-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "b" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 16, "required": 16, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
        })
        self.assertIn("screenapp audio-chime", rendered)
        self.assertIn("display-only", rendered)
        self.assertIn("no ADSP boot", rendered)
        self.assertIn("boot-autoplay", rendered)
        self.assertIn("Rollback health", rendered)


if __name__ == "__main__":
    unittest.main()
