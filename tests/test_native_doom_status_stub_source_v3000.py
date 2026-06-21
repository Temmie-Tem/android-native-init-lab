"""Static checks for V3000 DOOM status-only demo surface."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
MENU_HEADER = REPO / "workspace/public/src/native-init/a90_menu.h"
MENU_SOURCE = REPO / "workspace/public/src/native-init/a90_menu.c"
STATUS_HUD = REPO / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_native_init_boot_v3000_doom_status_stub as runner  # noqa: E402


class TestNativeDoomStatusStubSourceV3000(unittest.TestCase):
    def test_build_identity_and_marker_contract(self) -> None:
        self.assertEqual(runner.CYCLE, "V3000")
        self.assertEqual(runner.INIT_VERSION, "0.10.68")
        self.assertEqual(runner.INIT_BUILD, "v3000-doom-status-stub")
        self.assertTrue(str(runner.BOOT_IMAGE).endswith("boot_linux_v3000_doom_status_stub.img"))
        markers = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"A90 Linux init 0.10.68 (v3000-doom-status-stub)", markers)
        self.assertIn(b"video.status.doom_stub=1", markers)
        self.assertIn(b"video.demo.status=blocked-input-prerequisite", markers)
        self.assertIn(b"video.demo.input.button_mux=v2999-doominput-mux-live", markers)
        self.assertIn(b"video.demo.input.next=doominputmux event3,event0 24 45000", markers)
        self.assertIn(b"menu.demo.doom.action=status-only", markers)
        self.assertIn(b"menu.demo.doom.input.live_handoff=v2999-doominput-mux-live", markers)

    def test_demo_menu_exposes_doom_status_entry(self) -> None:
        header = MENU_HEADER.read_text(encoding="utf-8")
        source = MENU_SOURCE.read_text(encoding="utf-8")
        self.assertIn("SCREEN_MENU_DEMO_DOOM", header)
        self.assertIn('{ "DOOM",          "SERIAL DOOMPAD STATUS", SCREEN_MENU_DEMO_DOOM', source)

    def test_video_status_and_demo_doom_report_current_gameplay_loop_frontier(self) -> None:
        text = STATUS_HUD.read_text(encoding="utf-8")
        self.assertIn('a90_console_printf("video.status.doom_stub=1\\r\\n");', text)
        self.assertIn('a90_console_printf("video.status.doom_input=serial-doompad-staged\\r\\n");', text)
        self.assertIn("video demo [badapple|badapple-scale|nyan|doom]", text)
        self.assertIn("static int video_demo_doom_status(const char *action)", text)
        self.assertIn('a90_console_printf("video.demo.asset_id=doompad-loop-v3016\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.status=doompad-frame-loop-ready\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input=serial-doompad-consumed\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.touch=event6,event8-zero-events\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.virtual_controller=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.consumed=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.hardware_gate=none-serial-control\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.command=doompad key <role> <0|1>\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.play.command=video demo doom play [frames]\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.doom.status_rc=0\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.doom.%s=doompad-frame-loop\\r\\n", action);', text)

    def test_menu_action_is_status_only(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn("case SCREEN_MENU_DEMO_DOOM:", text)
        self.assertIn('{ "video", "demo", "doom", "status" }', text)
        self.assertIn('a90_console_printf("menu.demo.doom.action=status-only\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.status=doompad-frame-loop-ready\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input=serial-doompad-consumed\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.live_handoff=v3016-doompad-gameplay-loop\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.virtual_controller=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.consumed=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.hardware_gate=none-serial-control\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.command=doompad key <role> <0|1>\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.play.command=video demo doom play [frames]\\r\\n");', text)
        self.assertIn("rc = cmd_video_demo(demo_argv,", text)
        self.assertIn('a90_console_printf("menu.demo.doom.rc=%d\\r\\n", rc);', text)
        self.assertNotIn("menu.demo.doom.action=play", text)
        self.assertNotIn("menu.demo.doom.action=verify", text)

    def test_render_report_describes_status_only_candidate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3000_doom_status_stub.img",
            "boot_sha256": "abc123",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "v3000_marker_strings": [
                "video.status.doom_stub=1",
                "menu.demo.doom.action=status-only",
            ],
        }
        report = runner.render_report(manifest, ("helper",), ("init",))
        self.assertIn("Native Init V3000 DOOM Status Stub Source Build", report)
        self.assertIn("Host-side source build only", report)
        self.assertIn("status-only", report)
        self.assertIn("without claiming that DOOM is playable", report)
        self.assertIn("not-proven", report)
        self.assertIn("doom-status-stub-candidate", report)


if __name__ == "__main__":
    unittest.main()
