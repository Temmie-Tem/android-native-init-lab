"""Tests for V2852 audio changelog productization live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2852 = importlib.import_module("native_audio_changelog_productization_live_handoff_v2852")


class NativeAudioChangelogProductizationLiveHandoffV2852Test(unittest.TestCase):
    def test_wrapper_targets_v2851_candidate(self) -> None:
        self.assertEqual(v2852.CYCLE, "V2852")
        self.assertEqual(v2852.CANDIDATE_VERSION, "0.10.16")
        self.assertEqual(v2852.CANDIDATE_TAG, "v2851-audio-changelog-productization")
        self.assertIn("v2851-audio-changelog-productization", str(v2852.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2851_audio_changelog_productization.img", str(v2852.CANDIDATE_IMAGE))

    def test_screenapp_changelog_and_version_markers_are_required(self) -> None:
        changelog_markers = "\n".join(v2852.REQUIRED_SCREENAPP_MARKERS)
        for required in [
            "screenapp.app=about-changelog",
            "screenapp.safety=display-only-explicit",
            "screenapp.title=ABOUT / CHANGELOG",
            "screenapp.valid=1",
            "screenapp.presented=1",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, changelog_markers)

        extra = v2852.EXTRA_MARKER_STEPS[0]
        self.assertEqual(extra["command"], ["screenapp", "about-version"])
        version_markers = "\n".join(extra["markers"])
        self.assertIn("screenapp.app=about-version", version_markers)
        self.assertIn("screenapp.title=ABOUT / VERSION", version_markers)

    def test_configure_runner_sets_about_checks(self) -> None:
        v2852.configure_runner()
        self.assertEqual(v2852.runner.CYCLE, "V2852")
        self.assertEqual(v2852.runner.CANDIDATE_VERSION, "0.10.16")
        self.assertEqual(v2852.runner.SCREENAPP_COMMAND, ["screenapp", "about-changelog"])
        self.assertEqual(v2852.runner.EXTRA_MARKER_STEPS[0]["command"], ["screenapp", "about-version"])
        self.assertIn("screenapp.app=about-changelog", "\n".join(v2852.runner.REQUIRED_SCREENAPP_MARKERS))

    def test_report_mentions_display_only_about_validation(self) -> None:
        report = v2852.render_report({
            "decision": "v2852-test",
            "candidate_sha256": "9" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 30, "required": 30, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
            "extra_markers": {"candidate-screenapp-about-version": {"ok": True, "count": 6, "required": 6, "missing": []}},
        })
        self.assertIn("V2852", report)
        self.assertIn("screenapp about-changelog", report)
        self.assertIn("screenapp about-version", report)
        self.assertIn("no ADSP boot", report)
        self.assertIn("No forbidden partitions", report)


if __name__ == "__main__":
    unittest.main()
