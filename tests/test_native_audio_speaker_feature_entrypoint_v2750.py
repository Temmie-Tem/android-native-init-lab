"""Tests for the V2750 speaker feature entrypoint facade."""

from __future__ import annotations

import unittest
import contextlib
import io

from _loader import load_revalidation

entry = load_revalidation("native_audio_speaker_feature_entrypoint_v2750")


class NativeAudioSpeakerFeatureEntrypointV2750(unittest.TestCase):
    def test_listen_plan_exports_staged_contract_and_profile(self) -> None:
        args = entry.parse_args(["--plan"])
        plan = entry.build_plan(args)

        self.assertEqual(plan["decision"], "v2750-audio-speaker-feature-entrypoint-plan")
        self.assertTrue(plan["host_only"])
        self.assertEqual(plan["device_action"], "none")
        self.assertEqual(plan["profile"]["profile_id"], "internal-speaker-safe")
        self.assertEqual(plan["request"]["mode"], "listen")
        self.assertEqual(plan["request"]["amplitude"], 0.15)
        self.assertEqual(plan["request"]["duration_ms"], 8000)
        self.assertEqual(plan["profile"]["global_app_type_values"], ["1", "69941", "48000", "16"])
        self.assertEqual(plan["profile"]["acdb_set_order"], [39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21])
        self.assertEqual(plan["safety"]["amplitude_cap"], 0.20)
        self.assertTrue(plan["safety"]["no_smart_amp_gain_boost_changes"])
        self.assertIn("write-global-app-type-config", plan["staged_contract"])
        self.assertIn("replay-acdb-setcal-sequence", plan["staged_contract"])
        self.assertIn("rollback-v2321", plan["staged_contract"])

    def test_legacy_command_delegates_to_v2639_with_profile_and_listen_flags(self) -> None:
        plan = entry.build_plan(entry.parse_args(["--plan", "--mode", "listen"]))
        command = plan["legacy_v2639_live_command"]
        text = " ".join(command)

        self.assertTrue(any(part.endswith("native_audio_acdb_setcal_replay_live_handoff_v2639.py") for part in command))
        self.assertIn("--run-live", command)
        self.assertIn("--audio-profile internal-speaker-safe", text)
        self.assertIn("--listen-test", command)
        self.assertIn("--listen-countdown-sec 5", text)
        self.assertIn("--amplitude 0.15", text)
        self.assertIn("--duration-ms 8000", text)

    def test_probe_plan_omits_listen_flags_and_uses_probe_defaults(self) -> None:
        plan = entry.build_plan(entry.parse_args(["--plan", "--mode", "probe"]))
        command = plan["legacy_v2639_live_command"]

        self.assertEqual(plan["request"]["mode"], "probe")
        self.assertEqual(plan["request"]["amplitude"], 0.02)
        self.assertEqual(plan["request"]["duration_ms"], 1000)
        self.assertNotIn("--listen-test", command)
        self.assertNotIn("--listen-countdown-sec", command)

    def test_safety_caps_reject_unsafe_listen_requests(self) -> None:
        with self.assertRaises(ValueError):
            entry.build_plan(entry.parse_args(["--plan", "--mode", "listen", "--amplitude", "0.21"]))
        with self.assertRaises(ValueError):
            entry.build_plan(entry.parse_args(["--plan", "--mode", "listen", "--duration-ms", "10001"]))

    def test_without_plan_is_rejected(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                entry.parse_args([])


if __name__ == "__main__":
    unittest.main()
