"""Tests for the V2830 latest-image audio profile API live wrapper."""

from __future__ import annotations

import importlib
import json
import unittest

v2830 = importlib.import_module("native_audio_profile_api_live_handoff_v2830")


class NativeAudioProfileApiLiveV2830Test(unittest.TestCase):
    def test_constants_pin_latest_audio_observability_candidate(self) -> None:
        self.assertEqual(v2830.CYCLE, "V2830")
        self.assertEqual(v2830.CANDIDATE_VERSION, "0.10.6")
        self.assertEqual(v2830.CANDIDATE_TAG, "v2828-audio-route-map-safety")
        self.assertIn("boot_linux_v2828_audio_route_map_safety.img", str(v2830.CANDIDATE_IMAGE))
        self.assertIn("NATIVE_INIT_V2830_AUDIO_PROFILE_API_LIVE", str(v2830.REPORT_PATH))

    def test_marker_sets_cover_profile_stage_and_speaker_contracts(self) -> None:
        marker_sets = v2830.command_marker_sets()
        self.assertIn("audio.profile.read_only=1", marker_sets["audio-profile"])
        self.assertIn("audio.profile.acdb_set_order=39,20,20,13,9,11,12,15,23,16,21", marker_sets["audio-profile"])
        self.assertIn("audio.stages.count=14", marker_sets["audio-stages"])
        self.assertIn(
            "audio.stages.10.command=audio play internal-speaker-safe --mode probe --execute",
            marker_sets["audio-stages"],
        )
        self.assertIn("audio.speaker_map.safety.smart_amp_boost_write_allowed=0", marker_sets["audio-speaker-map"])
        self.assertIn("audio.speaker_map.speaker.5.safety=boost-write-blocked", marker_sets["audio-speaker-map"])

    def test_dry_run_includes_read_only_audio_api_commands(self) -> None:
        dry = v2830.dry_run({"candidate": {"sha256": "3" * 64}})
        rendered = json.dumps(dry["commands"], sort_keys=True)
        self.assertIn('["audio", "profiles"]', rendered)
        self.assertIn('["audio", "profile", "internal-speaker-safe"]', rendered)
        self.assertIn('["audio", "stages", "internal-speaker-safe"]', rendered)
        self.assertIn('["audio", "speaker-map", "internal-speaker-safe"]', rendered)
        self.assertNotIn('["audio", "play"', rendered)
        self.assertNotIn('["audio", "route"', rendered)

    def test_report_declares_observability_only_boundary(self) -> None:
        report = v2830.render_report({
            "decision": "v2830-test",
            "candidate_sha256": "c" * 64,
            "command_markers": {
                "audio-profiles": {"ok": True, "count": 4, "required": 4, "missing": []},
                "audio-profile": {"ok": True, "count": 21, "required": 21, "missing": []},
                "audio-stages": {"ok": True, "count": 17, "required": 17, "missing": []},
                "audio-speaker-map": {"ok": True, "count": 19, "required": 19, "missing": []},
            },
        })
        self.assertIn("V2830", report)
        self.assertIn("read-only profile API", report)
        self.assertIn("no ADSP boot", report)
        self.assertIn("No forbidden partitions", report)


if __name__ == "__main__":
    unittest.main()
