"""Tests for V2960 Bad Apple setcrtc default wiring."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2960_badapple_setcrtc_default.py"


class TestNativeVideoBadAppleSetcrtcDefaultV2960(unittest.TestCase):
    def test_badapple_menu_uses_setcrtc_and_trimmed_audio_gain(self) -> None:
        text = MENU.read_text(encoding="utf-8")
        self.assertIn('"--present", "setcrtc"', text)
        self.assertIn("menu.demo.badapple.video_present=setcrtc", text)
        self.assertNotIn('"--present", "pageflip"', text)
        self.assertIn('"--pcm-gain-milli", "780"', text)
        self.assertIn("menu.demo.badapple.audio_pcm_gain_milli=780", text)
        self.assertNotIn('"--pcm-gain-milli", "840"', text)

    def test_v2960_builder_requires_setcrtc_default_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('CYCLE = "V2960"', text)
        self.assertIn('INIT_VERSION = "0.10.56"', text)
        self.assertIn('INIT_BUILD = "v2960-badapple-setcrtc-default"', text)
        self.assertIn("boot_linux_v2960_badapple_setcrtc_default.img", text)
        self.assertIn('b"video.status.version=6"', text)
        self.assertIn('b"menu.demo.badapple.video_present=setcrtc"', text)
        self.assertNotIn("pageflip_phase_lock", text)
        self.assertIn('"recommended_pcm_gain_milli": 780', text)
        self.assertIn('"default_present_mode": "setcrtc"', text)


if __name__ == "__main__":
    unittest.main()
