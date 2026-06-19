"""Tests for the V2827 audio menu screens live wrapper."""

from __future__ import annotations

import importlib
import json
import unittest

v2827 = importlib.import_module("native_audio_menu_screens_live_handoff_v2827")


class NativeAudioMenuScreensLiveV2827Test(unittest.TestCase):
    def test_wrapper_pins_v2826_candidate_constants(self) -> None:
        self.assertEqual(v2827.CYCLE, "V2827")
        self.assertEqual(v2827.CANDIDATE_VERSION, "0.10.5")
        self.assertEqual(v2827.CANDIDATE_TAG, "v2826-audio-menu-screens")
        self.assertIn("boot_linux_v2826_audio_menu_screens.img", str(v2827.CANDIDATE_IMAGE))
        self.assertIn("NATIVE_INIT_V2827_AUDIO_MENU_SCREENS_LIVE", str(v2827.REPORT_PATH))

    def test_configure_runner_sets_screenapp_map_check(self) -> None:
        v2827.configure_runner()
        self.assertEqual(v2827.runner.CYCLE, "V2827")
        self.assertEqual(v2827.runner.CANDIDATE_VERSION, "0.10.5")
        self.assertEqual(v2827.runner.CANDIDATE_TAG, "v2826-audio-menu-screens")
        self.assertEqual(v2827.runner.SCREENAPP_COMMAND, ["screenapp", "audio-map"])
        markers = "\n".join(v2827.runner.REQUIRED_SCREENAPP_MARKERS)
        self.assertIn("screenapp.app=audio-map", markers)
        self.assertIn("screenapp.title=AUDIO ROUTE MAP", markers)
        self.assertIn("screenapp.presented=1", markers)

        dry = v2827.runner.dry_run({"candidate": {"sha256": "2" * 64}})
        rendered = json.dumps(dry["commands"], sort_keys=True)
        self.assertIn('["hide"]', rendered)
        self.assertIn('["screenapp", "audio-map"]', rendered)

    def test_report_mentions_menu_scope_and_display_only_boundary(self) -> None:
        report = v2827.render_report({
            "decision": "v2827-test",
            "candidate_sha256": "b" * 64,
            "audio_status_markers": {"ok": True, "count": 16, "required": 16, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
        })
        self.assertIn("V2827", report)
        self.assertIn("APPS/AUDIO", report)
        self.assertIn("screenapp audio-map", report)
        self.assertIn("display/KMS only", report)
        self.assertIn("No forbidden partitions", report)


if __name__ == "__main__":
    unittest.main()
