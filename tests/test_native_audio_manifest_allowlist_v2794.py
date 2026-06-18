"""Tests for the V2794 audio manifest allowlist fix."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2794_audio_manifest_allowlist.py"
LIVE = REPO / "workspace/public/src/scripts/revalidation/native_audio_manifest_allowlist_live_handoff_v2794.py"


def load_live_module():
    sys.path.insert(0, str(LIVE.parent))
    spec = importlib.util.spec_from_file_location("v2794_live", LIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioManifestAllowlistV2794(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = load_live_module()

    def test_sound_control_wait_matches_prior_device_settle_budget(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("AUDIO_PLAY_ASYNC_STATUS_PATH", text)
        self.assertIn("audio_play_start_worker", text)
        self.assertIn("audio.play.execute.async_worker=1", text)
        self.assertIn(
            "audio_setcal_path_has_prefix(path, AUDIO_SETCAL_LEGACY_REPLAY_PREFIX)",
            text,
        )
        self.assertIn('strcmp(argv[1], "play-status") == 0', text)
        self.assertIn("a90_console_redirect_child_to_file(AUDIO_PLAY_ASYNC_LOG_PATH)", text)
        self.assertIn(
            'audio_wait_for_audio_condition("sound_control", 70000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )
        self.assertNotIn(
            'audio_wait_for_audio_condition("sound_control", 20000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )

    def test_builder_uses_v2794_patch_artifact_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('CYCLE = "V2794"', text)
        self.assertIn('INIT_VERSION = "0.9.307"', text)
        self.assertIn('INIT_BUILD = "v2794-audio-manifest-allowlist"', text)
        self.assertIn('boot_linux_v2794_audio_manifest_allowlist.img', text)
        self.assertIn('NATIVE_INIT_V2794_AUDIO_MANIFEST_ALLOWLIST_SOURCE_BUILD_2026-06-19.md', text)
        self.assertIn('"sound_control_wait_timeout_ms": 70000', text)
        self.assertIn('"play_worker_executor_compiled": True', text)

    def test_live_runner_targets_v2794_and_allowed_manifest_path(self) -> None:
        module = self.live
        args = module.parse_args(["--dry-run"])
        state = module.preflight_state()
        payload = module.dry_run_payload(args, state)

        self.assertEqual(module.CANDIDATE_VERSION, "0.9.307")
        self.assertIn("boot_linux_v2794_audio_manifest_allowlist.img", str(module.CANDIDATE_IMAGE))
        self.assertEqual(
            module.REMOTE_NATIVE_MANIFEST,
            "/cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest",
        )
        self.assertIn(module.REMOTE_NATIVE_MANIFEST, payload["commands"]["play"])
        self.assertEqual(payload["commands"]["play"][-1], "--execute")
        self.assertEqual(payload["commands"]["play_status"], ["audio", "play-status"])
        self.assertEqual(payload["commands"]["play_worker_log"], ["run", "/bin/busybox", "cat", module.REMOTE_PLAY_LOG])

    def test_worker_output_classification_requires_worker_markers(self) -> None:
        module = self.live
        summary = module.classify_play_output(
            "\n".join([
                "audio.play.worker.started=1",
                "audio.play.worker.done=1 rc=0",
                "A90_LISTEN_WINDOW_BEGIN",
                "A90_LISTEN_WINDOW_END",
                "audio.play.integrated.done=1 rc=0",
                "audio.setcal.execute.hold_active=1",
                "audio.setcal.execute.set_count=11",
                "audio.setcal.execute.deallocated_count=4",
                "audio.play.integrated.route_apply.rc=0",
                "audio.play.integrated.route_reset.rc=0",
                "audio.play.execute.pcm_write_attempted=1",
                "audio.play.execute.done=1",
                "audio.play.safety.amplitude_within_cap=1",
                "audio.play.safety.duration_within_cap=1",
            ])
        )

        self.assertTrue(module.play_output_pass(summary), summary)


if __name__ == "__main__":
    unittest.main()
