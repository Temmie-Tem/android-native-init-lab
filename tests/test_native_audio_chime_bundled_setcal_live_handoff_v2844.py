"""Tests for the V2844 bundled SET-cal chime live runner."""

from __future__ import annotations

import importlib
import inspect
import unittest

v2844 = importlib.import_module("native_audio_chime_bundled_setcal_live_handoff_v2844")


class NativeAudioChimeBundledSetcalLiveHandoffV2844Test(unittest.TestCase):
    def test_runner_targets_bundled_v2843_candidate(self) -> None:
        self.assertEqual(v2844.runner.CYCLE, "V2844")
        self.assertEqual(v2844.runner.CANDIDATE_VERSION, "0.10.12")
        self.assertEqual(v2844.runner.CANDIDATE_TAG, "v2843-audio-bundled-setcal")
        self.assertIn("boot_linux_v2843_audio_bundled_setcal.img", str(v2844.runner.CANDIDATE_IMAGE))
        self.assertEqual(
            v2844.BUNDLED_REMOTE_MANIFEST,
            "/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest",
        )

    def test_chime_defaults_are_low_amplitude_and_bounded(self) -> None:
        args = v2844.parse_args(["--dry-run"])
        self.assertEqual(args.amplitude_milli, 80)
        self.assertEqual(args.duration_ms, 1200)
        self.assertEqual(
            v2844.chime_command(args),
            [
                "audio",
                "chime",
                "--duration-ms",
                "1200",
                "--amplitude-milli",
                "80",
                "--execute",
            ],
        )

    def test_run_play_sequence_has_no_host_artifact_install(self) -> None:
        source = inspect.getsource(v2844.run_play_sequence)
        self.assertNotIn("install_runtime_artifacts", source)
        self.assertIn('"host_artifact_deploy_performed": False', source)
        self.assertIn('"installed": []', source)

    def test_dry_run_reports_zero_host_deploy_count(self) -> None:
        args = v2844.parse_args(["--dry-run"])
        state = v2844.preflight_state()
        payload = v2844.dry_run_payload(args, state)

        self.assertEqual(payload["commands"]["audio_chime"], v2844.chime_command(args))
        self.assertEqual(payload["commands"]["host_artifact_deploy_count"], 0)
        self.assertFalse(payload["preflight"]["host_artifact_deploy_required"])
        self.assertTrue(payload["preflight"]["host_artifact_deploy_forbidden_in_this_unit"])

    def test_report_declares_no_runtime_copy(self) -> None:
        report = v2844.render_report({
            "decision": "v2844-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "a" * 64,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "play_command": "audio chime --execute",
            "host_artifact_deploy_performed": False,
            "play_summary": {},
            "card_wait_after_play_start": {},
        })

        self.assertIn("Host artifact deployment performed: `0`", report)
        self.assertIn("/a90/audio", report)
        self.assertIn("no runtime ACDB files are copied from the host", report)


if __name__ == "__main__":
    unittest.main()
