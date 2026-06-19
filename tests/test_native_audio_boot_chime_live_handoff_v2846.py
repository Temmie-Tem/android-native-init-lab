"""Tests for the V2846 boot-chime live runner."""

from __future__ import annotations

import importlib
import inspect
import unittest

v2846 = importlib.import_module("native_audio_boot_chime_live_handoff_v2846")


class NativeAudioBootChimeLiveHandoffV2846Test(unittest.TestCase):
    def test_runner_targets_v2845_candidate(self) -> None:
        self.assertEqual(v2846.runner.CYCLE, "V2846")
        self.assertEqual(v2846.runner.CANDIDATE_VERSION, "0.10.13")
        self.assertEqual(v2846.runner.CANDIDATE_TAG, "v2845-audio-boot-chime")
        self.assertIn("boot_linux_v2845_audio_boot_chime.img", str(v2846.runner.CANDIDATE_IMAGE))
        self.assertEqual(
            v2846.BOOT_CHIME_LAUNCH_LOG,
            "/cache/a90-audio-play/boot-chime-launch.log",
        )

    def test_dry_run_has_no_manual_audio_command_or_host_deploy(self) -> None:
        args = v2846.parse_args(["--dry-run"])
        state = v2846.preflight_state()
        payload = v2846.dry_run_payload(args, state)

        self.assertIsNone(payload["commands"]["manual_audio_command"])
        self.assertEqual(payload["commands"]["host_artifact_deploy_count"], 0)
        self.assertEqual(payload["commands"]["boot_chime_launch_log"], [
            "run",
            "/bin/busybox",
            "cat",
            v2846.BOOT_CHIME_LAUNCH_LOG,
        ])
        self.assertFalse(payload["preflight"]["host_artifact_deploy_required"])
        self.assertTrue(payload["preflight"]["host_artifact_deploy_forbidden_in_this_unit"])

    def test_boot_chime_marker_classifier_requires_autoplay_markers(self) -> None:
        good = "\n".join([
            "audio.boot_chime.child_started=1",
            "audio.chime.version=1",
            "audio.chime.execute_requested=1",
            "audio.chime.boot_autoplay_default=1",
        ])
        self.assertTrue(v2846.boot_chime_started(good))
        self.assertFalse(v2846.boot_chime_started(good.replace("audio.chime.execute_requested=1", "")))

    def test_run_play_sequence_observes_logs_instead_of_sending_chime(self) -> None:
        source = inspect.getsource(v2846.run_play_sequence)
        self.assertIn("BOOT_CHIME_LAUNCH_LOG", source)
        self.assertIn("boot-autoplay audio chime", source)
        self.assertNotIn('"audio",\\n        "chime"', source)
        self.assertNotIn("install_runtime_artifacts", source)
        self.assertIn('"host_artifact_deploy_performed": False', source)

    def test_report_declares_pid1_autoplay_scope(self) -> None:
        report = v2846.render_report({
            "decision": "v2846-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "a" * 64,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "host_artifact_deploy_performed": False,
            "boot_chime_started": True,
            "play_summary": {},
            "card_wait_after_play_start": {},
        })

        self.assertIn("Manual audio command sent: `0`", report)
        self.assertIn("PID1 boot autoplay", report)
        self.assertIn("Host artifact deployment performed: `0`", report)


if __name__ == "__main__":
    unittest.main()
