from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(".")
MENU_H = ROOT / "workspace/public/src/native-init/a90_menu.h"
MENU_C = ROOT / "workspace/public/src/native-init/a90_menu.c"
MENU_APPS = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
HELP = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
NETWORK_APP = ROOT / "workspace/public/src/native-init/a90_app_network.c"
NETWORK_H = ROOT / "workspace/public/src/native-init/a90_app_network.h"


class NativeWstaOperatorScreenappSourceTests(unittest.TestCase):
    def test_network_menu_exposes_wsta_operator_screen(self) -> None:
        menu_h = MENU_H.read_text(encoding="utf-8")
        menu_c = MENU_C.read_text(encoding="utf-8")
        menu_apps = MENU_APPS.read_text(encoding="utf-8")

        for marker in (
            "SCREEN_MENU_WSTA_OPERATOR",
            "SCREEN_APP_WSTA_OPERATOR",
            '{ "WSTA PUBLISH",   "RUNBOOK + REDACTED RESULT", SCREEN_MENU_WSTA_OPERATOR, SCREEN_MENU_PAGE_NETWORK }',
            "case SCREEN_MENU_WSTA_OPERATOR:",
            "return SCREEN_APP_WSTA_OPERATOR;",
            "state->active_app == SCREEN_APP_WSTA_OPERATOR",
            "a90_app_network_draw_wsta_operator();",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, menu_h + menu_c + menu_apps)

    def test_screenapp_wsta_alias_is_display_only(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")

        self.assertIn("screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|wsta|audio-status", dispatch)
        self.assertIn("screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping|wsta|audio-status", help_text)
        self.assertIn('strcmp(app, "wsta") == 0 || strcmp(app, "dpublic") == 0', dispatch)
        self.assertIn("screenapp.title=WSTA D-PUBLIC", dispatch)
        self.assertIn("a90_app_network_draw_wsta_operator()", dispatch)
        self.assertIn("screenapp.safety=display-only-explicit", dispatch)

    def test_wsta_screen_content_points_to_host_runner_not_native_public_action(self) -> None:
        source = NETWORK_APP.read_text(encoding="utf-8")
        header = NETWORK_H.read_text(encoding="utf-8")
        block_start = source.index("int a90_app_network_draw_wsta_operator(void)")
        block = source[block_start:source.index("\n}", block_start) + 2]

        self.assertIn("int a90_app_network_draw_wsta_operator(void);", header)
        self.assertIn("WSTA D-PUBLIC", block)
        self.assertIn("STATE: PUBLIC_OFF EXEC-GATED", block)
        self.assertIn("GATE: WSTA80 READY -> WSTA58", block)
        self.assertIn("URL: REDACTED PRIVATE-RUN ONLY", block)
        self.assertIn("NATIVE: DISPLAY-ONLY NO AUTOSTART", block)
        self.assertNotIn("a90_wifi_cmd", block)
        self.assertNotIn("a90_wifi_scan_collect", block)
        self.assertNotIn("a90_wifi_ping_collect", block)
        self.assertNotIn("cloudflared", block.lower())
        self.assertNotIn("trycloudflare", block.lower())
        self.assertNotIn("connect", block.lower())
        self.assertNotIn("native_init_flash.py", block)


if __name__ == "__main__":
    unittest.main()
