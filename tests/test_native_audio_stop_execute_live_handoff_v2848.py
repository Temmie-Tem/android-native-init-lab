"""Tests for the V2848 bounded audio stop-execute live runner."""

from __future__ import annotations

import importlib
import inspect
import unittest

v2848 = importlib.import_module("native_audio_stop_execute_live_handoff_v2848")


class NativeAudioStopExecuteLiveHandoffV2848Test(unittest.TestCase):
    def test_runner_targets_v2847_candidate(self) -> None:
        self.assertEqual(v2848.runner.CYCLE, "V2848")
        self.assertEqual(v2848.runner.CANDIDATE_VERSION, "0.10.14")
        self.assertEqual(v2848.runner.CANDIDATE_TAG, "v2847-audio-stop-execute")
        self.assertIn("boot_linux_v2847_audio_stop_execute.img", str(v2848.runner.CANDIDATE_IMAGE))
        self.assertEqual(v2848.STOP_COMMAND, ["audio", "stop", "internal-speaker-safe", "--execute"])

    def test_dry_run_declares_single_stop_command_and_no_deploy(self) -> None:
        args = v2848.parse_args(["--dry-run"])
        state = v2848.preflight_state()
        payload = v2848.dry_run_payload(args, state)

        self.assertEqual(payload["commands"]["audio_stop_execute"], v2848.STOP_COMMAND)
        self.assertEqual(payload["commands"]["host_artifact_deploy_count"], 0)
        self.assertFalse(payload["preflight"]["host_artifact_deploy_required"])
        self.assertTrue(payload["preflight"]["host_artifact_deploy_forbidden_in_this_unit"])

    def test_stop_classifier_requires_bounded_route_reset_markers(self) -> None:
        good = "\n".join([
            "audio.stop.execute_supported=1",
            "audio.stop.execute_requested=1",
            "audio.stop.playback_stop_reason=no-active-pcm-handle",
            "audio.stop.setcal_deallocate_reason=no-active-setcal-session",
            "audio.stop.route_write_attempted=1",
            "audio.stop.ioctl_attempted=1",
            "audio.route.mode=reset",
            "audio.route.layer=core",
            "audio.route.write_attempted=1",
            "audio.route.write_done count=8 layer=core mode=reset",
            "audio.stop.route_reset_rc=0",
            "audio.stop.done=1 rc=0",
        ])
        self.assertTrue(v2848.classify_stop_output(good, 0)["pass"])
        self.assertFalse(v2848.classify_stop_output(good.replace("audio.route.layer=core", ""), 0)["pass"])
        self.assertFalse(v2848.classify_stop_output(good + "\naudio.route.write_failed control=x", 0)["pass"])
        self.assertFalse(v2848.classify_stop_output(good, 1)["pass"])

    def test_run_sequence_waits_then_runs_stop_without_artifact_deploy(self) -> None:
        source = inspect.getsource(v2848.run_play_sequence)
        self.assertIn("wait_for_worker_done", source)
        self.assertIn("wait_for_sound_card", source)
        self.assertIn("candidate-audio-stop-execute", source)
        self.assertIn("STOP_COMMAND", source)
        self.assertNotIn("install_runtime_artifacts", source)

    def test_report_declares_stop_scope(self) -> None:
        report = v2848.render_report({
            "decision": "v2848-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "a" * 64,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "stop_command": "audio stop internal-speaker-safe --execute",
            "stop_summary": {"pass": True, "stop_done": True, "route_write_done": True},
            "card_wait_after_play_start": {},
        })

        self.assertIn("Audio Stop Execute Live Handoff", report)
        self.assertIn("one `audio stop --execute`", report)
        self.assertIn("core route reset", report)


if __name__ == "__main__":
    unittest.main()
