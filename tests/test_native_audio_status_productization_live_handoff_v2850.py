"""Tests for V2850 audio status productization live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2850 = importlib.import_module("native_audio_status_productization_live_handoff_v2850")


class NativeAudioStatusProductizationLiveHandoffV2850Test(unittest.TestCase):
    def test_wrapper_targets_v2849_candidate(self) -> None:
        self.assertEqual(v2850.CYCLE, "V2850")
        self.assertEqual(v2850.CANDIDATE_VERSION, "0.10.15")
        self.assertEqual(v2850.CANDIDATE_TAG, "v2849-audio-status-productization")
        self.assertIn("v2849-audio-status-productization", str(v2850.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2849_audio_status_productization.img", str(v2850.CANDIDATE_IMAGE))

    def test_productization_markers_are_required(self) -> None:
        markers = "\n".join(v2850.REQUIRED_AUDIO_STATUS_MARKERS)
        for required in [
            "audio.status.productization.version=1",
            "audio.status.productization.latest_run=V2848",
            "audio.status.productization.latest_version=0.10.14",
            "audio.status.productization.latest_tag=v2847-audio-stop-execute",
            "audio.status.feature.boot_chime.enabled=1",
            "audio.status.feature.boot_chime.validation_run=V2846",
            "audio.status.feature.stop_execute.scope=core-route-reset",
            "audio.status.feature.stop_execute.validation_run=V2848",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, markers)

    def test_configure_runner_sets_screenapp_status_check(self) -> None:
        v2850.configure_runner()
        self.assertEqual(v2850.runner.CYCLE, "V2850")
        self.assertEqual(v2850.runner.CANDIDATE_VERSION, "0.10.15")
        self.assertEqual(v2850.runner.SCREENAPP_COMMAND, ["screenapp", "audio-status"])
        markers = "\n".join(v2850.runner.REQUIRED_SCREENAPP_MARKERS)
        self.assertIn("screenapp.app=audio-status", markers)
        self.assertIn("screenapp.presented=1", markers)

    def test_report_mentions_read_only_productization_validation(self) -> None:
        report = v2850.render_report({
            "decision": "v2850-test",
            "candidate_sha256": "9" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 30, "required": 30, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
        })
        self.assertIn("V2850", report)
        self.assertIn("audio.status.productization.*", report)
        self.assertIn("screenapp audio-status", report)
        self.assertIn("no ADSP boot", report)
        self.assertIn("No forbidden partitions", report)


if __name__ == "__main__":
    unittest.main()
