"""Tests for the V2792 integrated audio playback settle fix."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2792_audio_integrated_play_settle.py"
LIVE = REPO / "workspace/public/src/scripts/revalidation/native_audio_integrated_play_live_handoff_v2792.py"


def load_live_module():
    spec = importlib.util.spec_from_file_location("v2792_live", LIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioIntegratedPlaySettleV2792(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = load_live_module()

    def test_sound_control_wait_matches_prior_device_settle_budget(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn(
            'audio_wait_for_audio_condition("sound_control", 70000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )
        self.assertNotIn(
            'audio_wait_for_audio_condition("sound_control", 20000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )

    def test_builder_uses_v2792_patch_artifact_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('CYCLE = "V2792"', text)
        self.assertIn('INIT_VERSION = "0.9.305"', text)
        self.assertIn('INIT_BUILD = "v2792-audio-integrated-play-settle"', text)
        self.assertIn('boot_linux_v2792_audio_integrated_play_settle.img', text)
        self.assertIn('NATIVE_INIT_V2792_AUDIO_INTEGRATED_PLAY_SETTLE_SOURCE_BUILD_2026-06-19.md', text)
        self.assertIn('"sound_control_wait_timeout_ms": 70000', text)

    def test_live_runner_targets_v2792_and_allowed_manifest_path(self) -> None:
        module = self.live
        args = module.parse_args(["--dry-run"])
        state = module.preflight_state()
        payload = module.dry_run_payload(args, state)

        self.assertEqual(module.CANDIDATE_VERSION, "0.9.305")
        self.assertIn("boot_linux_v2792_audio_integrated_play_settle.img", str(module.CANDIDATE_IMAGE))
        self.assertEqual(
            module.REMOTE_NATIVE_MANIFEST,
            "/cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest",
        )
        self.assertIn(module.REMOTE_NATIVE_MANIFEST, payload["commands"]["play"])
        self.assertEqual(payload["commands"]["play"][-1], "--execute")


if __name__ == "__main__":
    unittest.main()
