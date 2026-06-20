"""Tests for V2952 Bad Apple Player HUD fastpath wiring."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STATUS_HUD = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2952_badapple_player_hud_fastpath.py"


class TestNativeVideoBadApplePlayerHudFastpathV2952(unittest.TestCase):
    def test_video_command_claims_display(self) -> None:
        dispatch = (ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c").read_text(encoding="utf-8")
        self.assertIn(
            '[badapple|badapple-scale] [status|verify|play]]", CMD_DISPLAY, A90_CMD_GROUP_DISPLAY }',
            dispatch,
        )
        self.assertIn("if ((command->flags & CMD_DISPLAY) != 0) {\n        stop_auto_hud(false);", dispatch)

    def test_player_hud_fastpath_markers_and_code(self) -> None:
        text = STATUS_HUD.read_text(encoding="utf-8")
        self.assertIn("video.status.player_hud_fastpath=1", text)
        self.assertIn("render_session_frames < 2U", text)
        self.assertIn("previous_frame_index == UINT32_MAX || frame_index <= previous_frame_index", text)
        self.assertIn("memcpy(dst, dst0, scaled_row_bytes);", text)
        self.assertIn("scaled_row_bytes = (size_t)scaled_width * sizeof(uint32_t);", text)

    def test_v2952_builder_requires_fastpath_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('CYCLE = "V2952"', text)
        self.assertIn('INIT_VERSION = "0.10.52"', text)
        self.assertIn('INIT_BUILD = "v2952-badapple-player-hud-fastpath"', text)
        self.assertIn("boot_linux_v2952_badapple_player_hud_fastpath.img", text)
        self.assertIn('b"video.status.player_hud_fastpath=1"', text)
        self.assertIn("V2951 showed V2950 solved display ownership", text)


if __name__ == "__main__":
    unittest.main()
