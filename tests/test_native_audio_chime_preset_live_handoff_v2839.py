"""Tests for the V2839 audio chime preset live wrapper."""

from __future__ import annotations

import importlib
import unittest

v2839 = importlib.import_module("native_audio_chime_preset_live_handoff_v2839")


class NativeAudioChimePresetLiveHandoffV2839Test(unittest.TestCase):
    def test_targets_v2838_candidate(self) -> None:
        self.assertEqual(v2839.runner.CYCLE, "V2839")
        self.assertEqual(v2839.runner.CANDIDATE_VERSION, "0.10.10")
        self.assertEqual(v2839.runner.CANDIDATE_TAG, "v2838-audio-chime-preset")
        self.assertIn("boot_linux_v2838_audio_chime_preset.img", str(v2839.runner.CANDIDATE_IMAGE))
        self.assertIn("NATIVE_INIT_V2839_AUDIO_CHIME_PRESET_LIVE", str(v2839.runner.REPORT_PATH))

    def test_chime_command_uses_manual_safe_defaults(self) -> None:
        args = v2839.parse_args(["--dry-run"])
        command = v2839.chime_command(args)

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
        args = v2839.parse_args([
            "--dry-run",
            "--duration-ms",
            "900",
            "--amplitude-milli",
            "70",
        ])
        command = v2839.chime_command(args)

        self.assertEqual(args.amplitude_milli, 70)
        self.assertEqual(args.duration_ms, 900)
        self.assertIn("900", command)
        self.assertIn("70", command)

    def test_report_adds_chime_specific_evidence(self) -> None:
        report = v2839.render_report({
            "decision": "v2839-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "a" * 64,
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

        self.assertIn("Chime Preset Evidence", report)
        self.assertIn("audio chime --duration-ms 1200", report)
        self.assertIn("Boot autoplay: `disabled`", report)
        self.assertIn("manual preset surface", report)


if __name__ == "__main__":
    unittest.main()
