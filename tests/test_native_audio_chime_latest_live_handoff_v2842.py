"""Tests for the V2842 latest-image audio chime playback wrapper."""

from __future__ import annotations

import importlib
import unittest

v2842 = importlib.import_module("native_audio_chime_latest_live_handoff_v2842")


class NativeAudioChimeLatestLiveHandoffV2842Test(unittest.TestCase):
    def test_targets_v2840_chime_screen_candidate(self) -> None:
        self.assertEqual(v2842.runner.CYCLE, "V2842")
        self.assertEqual(v2842.runner.CANDIDATE_VERSION, "0.10.11")
        self.assertEqual(v2842.runner.CANDIDATE_TAG, "v2840-audio-chime-screen")
        self.assertIn("v2840-audio-chime-screen", str(v2842.runner.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2840_audio_chime_screen.img", str(v2842.runner.CANDIDATE_IMAGE))
        self.assertIn("NATIVE_INIT_V2842_AUDIO_CHIME_LATEST_LIVE", str(v2842.runner.REPORT_PATH))

    def test_chime_command_uses_manual_safe_defaults(self) -> None:
        args = v2842.parse_args(["--dry-run"])
        command = v2842.chime_command(args)

        self.assertEqual(args.amplitude_milli, 80)
        self.assertEqual(args.duration_ms, 1200)
        self.assertEqual(command, [
            "audio",
            "chime",
            "--duration-ms",
            "1200",
            "--amplitude-milli",
            "80",
            "--execute",
        ])

    def test_chime_command_respects_explicit_bounds(self) -> None:
        args = v2842.parse_args([
            "--dry-run",
            "--duration-ms",
            "900",
            "--amplitude-milli",
            "70",
        ])
        command = v2842.chime_command(args)

        self.assertEqual(args.amplitude_milli, 70)
        self.assertEqual(args.duration_ms, 900)
        self.assertIn("900", command)
        self.assertIn("70", command)

    def test_report_adds_latest_candidate_evidence(self) -> None:
        report = v2842.render_report({
            "decision": "v2842-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "c" * 64,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "play_command": "audio chime --duration-ms 1200 --amplitude-milli 80 --execute",
            "play_summary": {},
            "card_wait_after_play_start": {},
            "status_after_deploy": {"summary": {}},
            "runtime_artifacts": {"installed": []},
        })

        self.assertIn("Latest Chime Playback Evidence", report)
        self.assertIn("0.10.11", report)
        self.assertIn("v2840-audio-chime-screen", report)
        self.assertIn("audio chime --duration-ms 1200", report)
        self.assertIn("Boot autoplay: `disabled`", report)
        self.assertIn("does not enable boot-time audio", report)


if __name__ == "__main__":
    unittest.main()
