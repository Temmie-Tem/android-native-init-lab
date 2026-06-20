"""Static checks for V3005 DOOM keyboard-gate status source build."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
MENU_SOURCE = REPO / "workspace/public/src/native-init/a90_menu.c"
STATUS_HUD = REPO / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_native_init_boot_v3005_doom_keyboard_gate_status as runner  # noqa: E402


class TestNativeDoomKeyboardGateStatusSourceV3005(unittest.TestCase):
    def test_build_identity_and_marker_contract(self) -> None:
        self.assertEqual(runner.CYCLE, "V3005")
        self.assertEqual(runner.INIT_VERSION, "0.10.69")
        self.assertEqual(runner.INIT_BUILD, "v3005-doom-keyboard-gate-status")
        self.assertTrue(str(runner.BOOT_IMAGE).endswith("boot_linux_v3005_doom_keyboard_gate_status.img"))
        markers = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"A90 Linux init 0.10.69 (v3005-doom-keyboard-gate-status)", markers)
        self.assertIn(b"video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat", markers)
        self.assertIn(b"video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate", markers)
        self.assertIn(b"video.demo.input.hardware_gate=usb-keyboard-otg", markers)
        self.assertIn(b"video.demo.input.command=doominput <keyboard-event> 32 60000", markers)
        self.assertIn(b"menu.demo.doom.input.live_handoff=v3004-doominput-keyboard-live-gate", markers)

    def test_demo_menu_stays_status_only(self) -> None:
        source = MENU_SOURCE.read_text(encoding="utf-8")
        self.assertIn('{ "DOOM",          "SERIAL DOOMPAD STATUS", SCREEN_MENU_DEMO_DOOM', source)

    def test_video_status_reports_current_serial_controller_gate(self) -> None:
        text = STATUS_HUD.read_text(encoding="utf-8")
        self.assertIn('a90_console_printf("video.demo.status=blocked-gameplay-loop\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input=serial-doompad-staged\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.touch=event6,event8-zero-events\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.virtual_controller=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.hardware_gate=none-serial-control\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.command=doompad key <role> <0|1>\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.doom.status_rc=0\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.doom.%s=blocked-gameplay-not-wired\\r\\n", action);', text)
        self.assertIn("return -EAGAIN;", text)
        self.assertNotIn('video.demo.input.button_mux=v2999-doominput-mux-live', text)
        self.assertNotIn('video.demo.input.next=doominputmux event3,event0 24 45000', text)

    def test_menu_action_reports_current_serial_controller_gate(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn("case SCREEN_MENU_DEMO_DOOM:", text)
        self.assertIn('{ "video", "demo", "doom", "status" }', text)
        self.assertIn('a90_console_printf("menu.demo.doom.action=status-only\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.status=blocked-gameplay-loop\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input=serial-doompad-staged\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.live_handoff=v3014-doompad-serial-controller\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.virtual_controller=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.hardware_gate=none-serial-control\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.command=doompad key <role> <0|1>\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.restore=menu\\r\\n");', text)
        self.assertIn("rc = cmd_video_demo(demo_argv,", text)
        self.assertNotIn('menu.demo.doom.input.live_handoff=v2999-doominput-mux-live', text)
        self.assertNotIn('menu.demo.doom.input.command=doominputmux event3,event0 24 45000', text)

    def test_render_report_describes_keyboard_gate_candidate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3005_doom_keyboard_gate_status.img",
            "boot_sha256": "abc123",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "v3005_marker_strings": [
                "video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate",
                "menu.demo.doom.input.command=doominput <keyboard-event> 32 60000",
            ],
        }
        report = runner.render_report(manifest, ("helper",), ("init",))
        self.assertIn("Native Init V3005 DOOM Keyboard Gate Status Source Build", report)
        self.assertIn("status-only", report)
        self.assertIn("v3004-doominput-keyboard-live-gate", report)
        self.assertIn("stale physical-button mux command", report)
        self.assertIn("doom-keyboard-gate-status-candidate", report)


if __name__ == "__main__":
    unittest.main()
