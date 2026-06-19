"""Tests for V2832 audio profile screen live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2832 = importlib.import_module("native_audio_profile_screen_live_handoff_v2832")


class NativeAudioProfileScreenLiveHandoffV2832Test(unittest.TestCase):
    def test_wrapper_targets_v2831_profile_screen_candidate(self) -> None:
        self.assertEqual(v2832.CYCLE, "V2832")
        self.assertEqual(v2832.CANDIDATE_VERSION, "0.10.7")
        self.assertEqual(v2832.CANDIDATE_TAG, "v2831-audio-profile-screen")
        self.assertIn("v2831-audio-profile-screen", str(v2832.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2831_audio_profile_screen.img", str(v2832.CANDIDATE_IMAGE))

    def test_screenapp_profile_markers_are_required(self) -> None:
        self.assertEqual(v2832.SCREENAPP_COMMAND, ["screenapp", "audio-profile"])
        markers = v2832.REQUIRED_SCREENAPP_MARKERS
        self.assertIn("screenapp.app=audio-profile", markers)
        self.assertIn("screenapp.title=AUDIO PROFILE", markers)
        self.assertIn("screenapp.presented=1", markers)

    def test_report_names_read_only_profile_validation(self) -> None:
        rendered = v2832.render_report({
            "decision": "v2832-test",
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
        self.assertIn("screenapp audio-profile", rendered)
        self.assertIn("display-only", rendered)
        self.assertIn("no ADSP boot", rendered)
        self.assertIn("Rollback health", rendered)


if __name__ == "__main__":
    unittest.main()
