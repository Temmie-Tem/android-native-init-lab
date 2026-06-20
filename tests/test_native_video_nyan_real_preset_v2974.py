import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_HUD = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_C = ROOT / "workspace/public/src/native-init/a90_menu.c"
MENU_H = ROOT / "workspace/public/src/native-init/a90_menu.h"
MENU_APPS = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
HELP = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"


class NativeVideoNyanRealPresetV2974(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.status = STATUS_HUD.read_text(encoding="utf-8")
        cls.menu_c = MENU_C.read_text(encoding="utf-8")
        cls.menu_h = MENU_H.read_text(encoding="utf-8")
        cls.menu_apps = MENU_APPS.read_text(encoding="utf-8")
        cls.help = HELP.read_text(encoding="utf-8")
        cls.dispatch = DISPATCH.read_text(encoding="utf-8")

    def test_nyan_sd_cache_preset_is_content_addressed(self) -> None:
        expected_sha = "9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573"
        self.assertIn('#define VIDEO_CACHE_PRESET_NYAN_NAME "nyan"', self.status)
        self.assertIn('#define VIDEO_CACHE_PRESET_NYAN_ASSET_ID "nyancat-v2973-pal8-rle-preview"', self.status)
        self.assertIn(f'#define VIDEO_CACHE_PRESET_NYAN_SHA256 "{expected_sha}"', self.status)
        self.assertIn("return VIDEO_CACHE_PRESET_NYAN_SHA256;", self.status)
        self.assertIn("return VIDEO_CACHE_PRESET_NYAN_ASSET_ID;", self.status)

    def test_nyan_uses_player_hud_and_demo_cache_wrapper(self) -> None:
        self.assertIn("strcmp(preset_name, VIDEO_CACHE_PRESET_NYAN_NAME) == 0", self.status)
        self.assertIn("return VIDEO_STREAM_LAYOUT_PLAYER_HUD;", self.status)
        demo_block = self.status[self.status.index("static int cmd_video_demo"):self.status.index("static int cmd_video_stream")]
        self.assertIn("strcmp(argv[2], VIDEO_CACHE_PRESET_NYAN_NAME) == 0", demo_block)
        self.assertIn('video.demo.asset_id=%s', demo_block)
        self.assertIn("return cmd_video_cache(cache_argv, cache_argc);", demo_block)

    def test_help_and_status_advertise_nyan(self) -> None:
        self.assertIn("video cache preset [badapple|badapple-scale|nyan]", self.status)
        self.assertIn("video demo [badapple|badapple-scale|nyan]", self.status)
        self.assertIn("demo nyan", self.help)
        self.assertIn("badapple|badapple-scale|nyan", self.dispatch)

    def test_demo_menu_contains_nyan_preview_entry(self) -> None:
        self.assertIn("SCREEN_MENU_DEMO_NYAN", self.menu_h)
        self.assertIn('{ "NYAN CAT",      "10S COLOR PLAYER",    SCREEN_MENU_DEMO_NYAN', self.menu_c)
        self.assertIn("case SCREEN_MENU_DEMO_NYAN", self.menu_apps)
        self.assertIn("menu.demo.nyan.action=play-av-preview", self.menu_apps)
        self.assertIn("menu.demo.nyan.frames=300", self.menu_apps)
        self.assertIn("menu.demo.nyan.audio_duration_ms=10000", self.menu_apps)
        self.assertIn("/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le", self.menu_apps)
        self.assertIn('"video", "demo", "nyan", "play"', self.menu_apps)
        self.assertIn('"--frames", "300"', self.menu_apps)
        self.assertIn('"--present", "setcrtc"', self.menu_apps)
        self.assertIn('"--layout", "player-hud"', self.menu_apps)


if __name__ == "__main__":
    unittest.main()
