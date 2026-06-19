"""Tests for V2836 audio help surface live handoff wrapper."""

from __future__ import annotations

import importlib
import unittest

v2836 = importlib.import_module("native_audio_help_surface_live_handoff_v2836")


class NativeAudioHelpSurfaceLiveHandoffV2836Test(unittest.TestCase):
    def test_wrapper_targets_v2835_help_surface_candidate(self) -> None:
        self.assertEqual(v2836.CYCLE, "V2836")
        self.assertEqual(v2836.CANDIDATE_VERSION, "0.10.9")
        self.assertEqual(v2836.CANDIDATE_TAG, "v2835-audio-help-surface")
        self.assertIn("v2835-audio-help-surface", str(v2836.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2835_audio_help_surface.img", str(v2836.CANDIDATE_IMAGE))

    def test_extra_marker_steps_cover_help_and_cmdmeta(self) -> None:
        names = {step["name"] for step in v2836.EXTRA_MARKER_STEPS}
        self.assertEqual(names, {"candidate-help", "candidate-cmdmeta-verbose"})
        for step in v2836.EXTRA_MARKER_STEPS:
            with self.subTest(step=step["name"]):
                self.assertIn(v2836.HELP_USAGE, "\n".join(step["markers"]))

    def test_report_names_read_only_help_validation(self) -> None:
        rendered = v2836.render_report({
            "decision": "v2836-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "c" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 16, "required": 16, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "extra_markers": {
                "candidate-help": {"ok": True, "count": 1, "required": 1, "missing": []},
                "candidate-cmdmeta-verbose": {"ok": True, "count": 2, "required": 2, "missing": []},
            },
        })
        self.assertIn("help-surface candidate", rendered)
        self.assertIn("cmdmeta verbose", rendered)
        self.assertIn("read-only", rendered)
        self.assertIn("Rollback health", rendered)


if __name__ == "__main__":
    unittest.main()
