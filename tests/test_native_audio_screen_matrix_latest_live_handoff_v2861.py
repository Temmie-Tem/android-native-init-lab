"""Tests for V2861 latest audio/about screen matrix live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2861 = importlib.import_module("native_audio_screen_matrix_latest_live_handoff_v2861")


class NativeAudioScreenMatrixLatestLiveHandoffV2861Test(unittest.TestCase):
    def test_wrapper_targets_v2859_candidate(self) -> None:
        self.assertEqual(v2861.CYCLE, "V2861")
        self.assertEqual(v2861.CANDIDATE_VERSION, "0.10.19")
        self.assertEqual(v2861.CANDIDATE_TAG, "v2859-audio-changelog-latest-refresh")
        self.assertIn("v2859-audio-changelog-latest-refresh", str(v2861.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2859_audio_changelog_latest_refresh.img", str(v2861.CANDIDATE_IMAGE))

    def test_screen_matrix_covers_latest_about_and_audio_surfaces(self) -> None:
        self.assertEqual(v2861.SCREENAPP_COMMAND, ["screenapp", "about-version"])
        commands = [tuple(step["command"]) for step in v2861.EXTRA_MARKER_STEPS]
        for command in [
            ("screenapp", "about-changelog"),
            ("screenapp", "audio-status"),
            ("screenapp", "audio-profile"),
            ("screenapp", "audio-stages"),
            ("screenapp", "audio-map"),
            ("screenapp", "audio-chime"),
        ]:
            with self.subTest(command=command):
                self.assertIn(command, commands)

    def test_required_markers_are_display_only(self) -> None:
        markers = "\n".join(v2861.REQUIRED_SCREENAPP_MARKERS)
        self.assertIn("screenapp.app=about-version", markers)
        self.assertIn("screenapp.safety=display-only-explicit", markers)
        self.assertIn("screenapp.title=ABOUT / VERSION", markers)
        for step in v2861.EXTRA_MARKER_STEPS:
            step_markers = "\n".join(step["markers"])
            self.assertIn("screenapp.safety=display-only-explicit", step_markers)
            self.assertIn("screenapp.presented=1", step_markers)

    def test_configure_runner_sets_matrix_checks(self) -> None:
        v2861.configure_runner()
        self.assertEqual(v2861.runner.CYCLE, "V2861")
        self.assertEqual(v2861.runner.CANDIDATE_VERSION, "0.10.19")
        self.assertEqual(v2861.runner.SCREENAPP_COMMAND, ["screenapp", "about-version"])
        self.assertEqual(len(v2861.runner.EXTRA_MARKER_STEPS), 6)
        self.assertIn("audio.status.productization.latest_run=V2860", "\n".join(v2861.runner.REQUIRED_AUDIO_STATUS_MARKERS))

    def test_report_mentions_no_audio_write_boundary(self) -> None:
        extra = {
            step["name"]: {"ok": True, "count": 6, "required": 6, "missing": []}
            for step in v2861.EXTRA_MARKER_STEPS
        }
        report = v2861.render_report({
            "decision": "v2861-test",
            "candidate_sha256": "1" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 33, "required": 33, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
            "extra_markers": extra,
        })
        self.assertIn("screenapp about-version", report)
        self.assertIn("audio-profile", report)
        self.assertIn("audio-chime", report)
        self.assertIn("no ADSP boot", report)
        self.assertIn("No forbidden partitions", report)


if __name__ == "__main__":
    unittest.main()
