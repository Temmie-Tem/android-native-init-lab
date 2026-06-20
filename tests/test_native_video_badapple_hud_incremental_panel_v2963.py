"""Tests for V2963 Bad Apple HUD incremental panel wiring."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2963_badapple_hud_incremental_panel.py"


class TestNativeVideoBadAppleHudIncrementalPanelV2963(unittest.TestCase):
    def test_badapple_menu_uses_setcrtc_and_trimmed_audio_gain(self) -> None:
        text = MENU.read_text(encoding="utf-8")
        self.assertIn('"--present", "setcrtc"', text)
        self.assertIn("menu.demo.badapple.video_present=setcrtc", text)
        self.assertNotIn('"--present", "pageflip"', text)
        self.assertIn('"--pcm-gain-milli", "780"', text)
        self.assertIn("menu.demo.badapple.audio_pcm_gain_milli=780", text)
        self.assertNotIn('"--pcm-gain-milli", "840"', text)

    def test_v2963_builder_requires_setcrtc_default_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('CYCLE = "V2963"', text)
        self.assertIn('INIT_VERSION = "0.10.57"', text)
        self.assertIn('INIT_BUILD = "v2963-badapple-hud-incremental-panel"', text)
        self.assertIn("boot_linux_v2963_badapple_hud_incremental_panel.img", text)
        self.assertIn('b"video.status.version=7"', text)
        self.assertIn('b"video.status.player_hud_incremental_panel=1"', text)
        self.assertIn('b"menu.demo.badapple.video_present=setcrtc"', text)
        self.assertNotIn("pageflip_phase_lock", text)
        self.assertIn('"recommended_pcm_gain_milli": 780', text)
        self.assertIn('"default_present_mode": "setcrtc"', text)
        self.assertIn('"hud_incremental_panel": True', text)


if __name__ == "__main__":
    unittest.main()
