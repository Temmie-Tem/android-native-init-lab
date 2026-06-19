"""Tests for V2858 latest audio marker refresh live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2858 = importlib.import_module("native_audio_latest_marker_refresh_live_handoff_v2858")


class NativeAudioLatestMarkerRefreshLiveHandoffV2858Test(unittest.TestCase):
    def test_wrapper_targets_v2857_candidate(self) -> None:
        self.assertEqual(v2858.CYCLE, "V2858")
        self.assertEqual(v2858.CANDIDATE_VERSION, "0.10.18")
        self.assertEqual(v2858.CANDIDATE_TAG, "v2857-audio-latest-marker-refresh")
        self.assertIn("v2857-audio-latest-marker-refresh", str(v2858.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2857_audio_latest_marker_refresh.img", str(v2858.CANDIDATE_IMAGE))

    def test_latest_productization_markers_are_required(self) -> None:
        markers = "\n".join(v2858.REQUIRED_AUDIO_STATUS_MARKERS)
        for required in [
            "audio.status.productization.latest_run=V2856",
            "audio.status.productization.latest_version=0.10.17",
            "audio.status.productization.latest_tag=v2853-audio-productization-marker-refresh",
            "audio.status.feature.chime.validation_run=V2855",
            "audio.status.feature.stop_execute.validation_run=V2856",
            "audio.status.feature.changelog.validation_run=V2852",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, markers)

    def test_configure_runner_sets_audio_status_and_about_changelog_checks(self) -> None:
        v2858.configure_runner()
        self.assertEqual(v2858.runner.CYCLE, "V2858")
        self.assertEqual(v2858.runner.CANDIDATE_VERSION, "0.10.18")
        self.assertEqual(v2858.runner.SCREENAPP_COMMAND, ["screenapp", "audio-status"])
        self.assertEqual(v2858.runner.EXTRA_MARKER_STEPS[0]["command"], ["screenapp", "about-changelog"])
        self.assertIn("audio.status.feature.stop_execute.validation_run=V2856", "\n".join(v2858.runner.REQUIRED_AUDIO_STATUS_MARKERS))

    def test_report_mentions_latest_marker_refresh_validation(self) -> None:
        report = v2858.render_report({
            "decision": "v2858-test",
            "candidate_sha256": "9" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 33, "required": 33, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
            "extra_markers": {"candidate-screenapp-about-changelog": {"ok": True, "count": 6, "required": 6, "missing": []}},
        })
        self.assertIn("V2858", report)
        self.assertIn("V2855/V2856 latest-candidate chime/stop evidence", report)
        self.assertIn("screenapp about-changelog", report)
        self.assertIn("no ADSP boot", report)
        self.assertIn("No forbidden partitions", report)


if __name__ == "__main__":
    unittest.main()
