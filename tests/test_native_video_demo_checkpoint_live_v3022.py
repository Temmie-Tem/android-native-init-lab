"""Static checks for V3022 same-image Bad Apple + Nyan live checkpoint."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "workspace/public/src/scripts/revalidation/native_video_demo_checkpoint_badapple_nyan_live_v3022.py"


class NativeVideoDemoCheckpointLiveV3022(unittest.TestCase):
    def setUp(self) -> None:
        self.text = RUNNER.read_text(encoding="utf-8")

    def test_runner_targets_exact_v3021_image_and_checked_rollback(self) -> None:
        self.assertIn('RUN_ID = "V3022"', self.text)
        self.assertIn("boot_linux_v3021_demo_checkpoint_badapple_nyan.img", self.text)
        self.assertIn('CANDIDATE_VERSION = "0.10.72"', self.text)
        self.assertIn('CANDIDATE_TAG = "v3021-demo-checkpoint-badapple-nyan"', self.text)
        self.assertIn("c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7", self.text)
        self.assertIn("video_live.flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True)", self.text)
        self.assertIn("video_live.flash_command(video_live.ROLLBACK_IMAGE, video_live.ROLLBACK_VERSION, video_live.ROLLBACK_SHA256, from_native=False) + [\"--verify-only\"]", self.text)
        self.assertIn("base.rollback_v2321", self.text)
        self.assertIn("rollback_selftest_fail0", self.text)

    def test_runner_preflights_fallbacks_and_twrp_before_live_flash(self) -> None:
        self.assertIn("fallback_v2237", self.text)
        self.assertIn("fallback_v48", self.text)
        self.assertIn("TWRP_RECOVERY_IMG", self.text)
        self.assertIn("TWRP_RECOVERY_TAR", self.text)
        self.assertIn('state["twrp"].get("available")', self.text)
        self.assertIn("bridge-status-before-flash", self.text)

    def test_runner_validates_badapple_full_song_setcrtc_path(self) -> None:
        self.assertIn("BADAPPLE_FRAMES = badapple_hud.BADAPPLE_FRAMES_TOTAL", self.text)
        self.assertIn("BADAPPLE_DURATION_MS = 232_090", self.text)
        self.assertIn("BADAPPLE_PCM_GAIN_MILLI = 780", self.text)
        self.assertIn('BADAPPLE_PRESENT_MODE = "setcrtc"', self.text)
        self.assertIn("candidate-video-demo-badapple-fullsong-player-hud-av-play", self.text)
        self.assertIn("--sync-start-offset-ms", self.text)
        self.assertIn("require_beat_flash=True", self.text)
        self.assertIn("video.stream.beat_flash.active_frames", self.text)

    def test_runner_validates_nyan_in_same_candidate_before_rollback(self) -> None:
        self.assertIn("result[\"badapple\"] = validate_badapple(args, out_dir, steps)", self.text)
        self.assertIn("result[\"nyan\"] = validate_nyan(args, out_dir, steps)", self.text)
        self.assertIn("candidate_video_status_demo_surface", self.text)
        self.assertIn("video.status.next_demo=video demo [badapple|badapple-scale|nyan|doom]", self.text)
        self.assertLess(
            self.text.index("result[\"badapple\"] = validate_badapple(args, out_dir, steps)"),
            self.text.index("result[\"nyan\"] = validate_nyan(args, out_dir, steps)"),
        )
        self.assertLess(
            self.text.index("result[\"nyan\"] = validate_nyan(args, out_dir, steps)"),
            self.text.index("rollback = base.rollback_v2321"),
        )
        self.assertIn("nyan.classify_setcrtc_play", self.text)
        self.assertIn("Same-image validation", self.text)

    def test_runner_keeps_private_media_untracked_and_forbidden_paths_out(self) -> None:
        forbidden = (
            "/efs",
            "/sec_efs",
            "fastboot flash",
            "pmic write",
            "regulator write",
            "gpio write",
            "gdsc write",
            "backlight write",
        )
        lowered = self.text.lower()
        for token in forbidden:
            self.assertNotIn(token, lowered)
        self.assertIn("private streams/audio and raw run logs remain untracked", self.text)
        self.assertIn("No Wi-Fi connect/DHCP/ping", self.text)


if __name__ == "__main__":
    unittest.main()
