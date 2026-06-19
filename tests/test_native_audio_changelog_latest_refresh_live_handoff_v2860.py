"""Tests for V2860 audio changelog latest-refresh live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2860 = importlib.import_module("native_audio_changelog_latest_refresh_live_handoff_v2860")


class NativeAudioChangelogLatestRefreshLiveHandoffV2860Test(unittest.TestCase):
    def test_wrapper_targets_v2859_candidate(self) -> None:
        self.assertEqual(v2860.CYCLE, "V2860")
        self.assertEqual(v2860.CANDIDATE_VERSION, "0.10.19")
        self.assertEqual(v2860.CANDIDATE_TAG, "v2859-audio-changelog-latest-refresh")
        self.assertIn("v2859-audio-changelog-latest-refresh", str(v2860.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2859_audio_changelog_latest_refresh.img", str(v2860.CANDIDATE_IMAGE))

    def test_audio_status_markers_expect_v2860_latest_contract(self) -> None:
        markers = "\n".join(v2860.REQUIRED_AUDIO_STATUS_MARKERS)
        for marker in [
            "audio.status.productization.latest_run=V2860",
            "audio.status.productization.latest_version=0.10.19",
            "audio.status.productization.latest_tag=v2859-audio-changelog-latest-refresh",
            "audio.status.feature.chime.validation_run=V2855",
            "audio.status.feature.stop_execute.validation_run=V2856",
            "audio.status.feature.changelog.validation_run=V2860",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, markers)

    def test_configure_runner_sets_about_and_audio_status_checks(self) -> None:
        v2860.configure_runner()
        self.assertEqual(v2860.runner.CYCLE, "V2860")
        self.assertEqual(v2860.runner.CANDIDATE_VERSION, "0.10.19")
        self.assertEqual(v2860.runner.SCREENAPP_COMMAND, ["screenapp", "about-changelog"])
        self.assertEqual(v2860.runner.EXTRA_MARKER_STEPS[0]["command"], ["screenapp", "audio-status"])
        self.assertIn("screenapp.app=about-changelog", "\n".join(v2860.runner.REQUIRED_SCREENAPP_MARKERS))

    def test_report_mentions_display_only_no_audio_write_boundary(self) -> None:
        report = v2860.render_report({
            "decision": "v2860-test",
            "candidate_sha256": "9" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 33, "required": 33, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
            "extra_markers": {"candidate-screenapp-audio-status": {"ok": True, "count": 6, "required": 6, "missing": []}},
        })
        self.assertIn("V2860", report)
        self.assertIn("screenapp about-changelog", report)
        self.assertIn("screenapp audio-status", report)
        self.assertIn("no ADSP boot", report)
        self.assertIn("No forbidden partitions", report)


if __name__ == "__main__":
    unittest.main()
