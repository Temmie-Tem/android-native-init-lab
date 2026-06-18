"""Tests for the V2791 integrated audio playback live handoff runner."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "workspace/public/src/scripts/revalidation/native_audio_integrated_play_live_handoff_v2791.py"


def load_module():
    spec = importlib.util.spec_from_file_location("v2791_live", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioIntegratedPlayLiveHandoffV2791(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_runner_targets_v2791_candidate_and_v2321_rollback(self) -> None:
        module = self.module

        self.assertEqual(module.CYCLE, "V2791")
        self.assertEqual(module.CANDIDATE_VERSION, "0.9.304")
        self.assertIn("boot_linux_v2791_audio_integrated_play.img", str(module.CANDIDATE_IMAGE))
        self.assertEqual(module.ROLLBACK_VERSION, "0.9.285")
        self.assertIn("boot_linux_v2321_usb_clean_identity_rodata.img", str(module.ROLLBACK_IMAGE))
        self.assertIn("NATIVE_INIT_V2791_AUDIO_INTEGRATED_PLAY_LIVE_2026-06-19.md", str(module.REPORT_PATH))

    def test_native_manifest_renders_expected_set_order_and_legacy_runtime_paths(self) -> None:
        module = self.module
        deploy_plan = module.read_json(module.DEPLOY_PLAN)
        manifest = module.render_native_manifest(deploy_plan)

        self.assertIn("version 1\n", manifest)
        self.assertIn("profile internal-speaker-safe\n", manifest)
        self.assertIn("entry_count 11\n", manifest)
        entry_lines = [line for line in manifest.splitlines() if line.startswith("entry ")]
        self.assertEqual(len(entry_lines), 11)
        self.assertEqual([int(line.split()[2]) for line in entry_lines], module.EXPECTED_SET_ORDER)
        self.assertIn("/cache/a90-acdb-setcal-replay-v2725/00-set-arg-cal39-core-custom-topologies.bin", manifest)
        self.assertIn("/cache/a90-acdb-setcal-replay-v2725/00-payload-cal39-core-custom-topologies.bin", manifest)
        self.assertNotIn("a90_acdb_setcal_replay_execute_v2635", manifest)

    def test_deploy_plan_validation_is_clean_for_current_private_manifest(self) -> None:
        module = self.module
        deploy_plan = module.read_json(module.DEPLOY_PLAN)

        self.assertEqual(module.validate_deploy_plan(deploy_plan), [])
        self.assertEqual(len(module.deploy_artifacts_for_native_manifest(deploy_plan)), 15)

    def test_dry_run_play_command_is_bounded_listen_execute(self) -> None:
        module = self.module
        args = module.parse_args(["--dry-run"])
        state = module.preflight_state()
        payload = module.dry_run_payload(args, state)
        play = payload["commands"]["play"]

        self.assertEqual(play[:6], ["audio", "play", "internal-speaker-safe", "--mode", "listen", "--duration-ms"])
        self.assertIn("8000", play)
        self.assertIn("--amplitude-milli", play)
        self.assertIn("150", play)
        self.assertIn("--manifest", play)
        self.assertIn(module.REMOTE_NATIVE_MANIFEST, play)
        self.assertEqual(play[-1], "--execute")

    def test_play_classifier_requires_cleanup_and_safety_markers(self) -> None:
        module = self.module
        text = "\n".join([
            "A90_LISTEN_WINDOW_BEGIN profile=internal-speaker-safe mode=listen amplitude_milli=150 duration_ms=8000",
            "audio.setcal.execute.hold_active=1",
            "audio.setcal.execute.set_count=11",
            "audio.setcal.execute.deallocated_count=4",
            "audio.play.integrated.route_apply.rc=0",
            "audio.play.integrated.route_reset.rc=0",
            "audio.play.execute.pcm_write_attempted=1",
            "audio.play.execute.done=1",
            "audio.play.safety.amplitude_within_cap=1",
            "audio.play.safety.duration_within_cap=1",
            "A90_LISTEN_WINDOW_END rc=0 chunks=94 frames=384000 bytes=1536000",
            "audio.play.integrated.done=1 rc=0",
        ])

        summary = module.classify_play_output(text)
        self.assertTrue(module.play_output_pass(summary))
        summary["setcal_deallocated"] = False
        self.assertFalse(module.play_output_pass(summary))


if __name__ == "__main__":
    unittest.main()
