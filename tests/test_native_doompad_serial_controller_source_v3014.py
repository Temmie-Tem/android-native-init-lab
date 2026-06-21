"""Static checks for V3014 DOOMPAD serial-controller source build."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
MENU_SOURCE = REPO / "workspace/public/src/native-init/a90_menu.c"
STATUS_HUD = REPO / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_native_init_boot_v3014_doompad_serial_controller as runner  # noqa: E402


def function_block(source: str, name: str) -> str:
    start = source.index(f"static int {name}(")
    next_function = source.find("\nstatic ", start + 1)
    if next_function == -1:
        return source[start:]
    return source[start:next_function]


class TestNativeDoompadSerialControllerSourceV3014(unittest.TestCase):
    def test_build_identity_and_marker_contract(self) -> None:
        self.assertEqual(runner.CYCLE, "V3014")
        self.assertEqual(runner.INIT_VERSION, "0.10.70")
        self.assertEqual(runner.INIT_BUILD, "v3014-doompad-serial-controller")
        self.assertTrue(str(runner.BOOT_IMAGE).endswith("boot_linux_v3014_doompad_serial_controller.img"))
        markers = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"A90 Linux init 0.10.70 (v3014-doompad-serial-controller)", markers)
        self.assertIn(b"video.status.doom_input=serial-doompad-staged", markers)
        self.assertIn(b"doompad [status|reset|key <role> <0|1>|tap <role>]", markers)
        self.assertIn(b"doompad.version=1", markers)
        self.assertIn(b"doompad.source=serial-control", markers)
        self.assertIn(b"doompad.event seq=", markers)
        self.assertIn(b"doompad.state seq=", markers)
        self.assertIn(b"video.demo.input.virtual_controller=doompad-serial-v3014", markers)
        self.assertIn(b"video.demo.input.command=doompad key <role> <0|1>", markers)
        self.assertIn(b"menu.demo.doom.input.command=doompad key <role> <0|1>", markers)

    def test_doompad_command_is_serial_state_only(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn("static struct doominput_state doompad_state;", text)
        self.assertIn("static int cmd_doompad(char **argv, int argc)", text)
        self.assertIn('a90_console_printf("doompad.version=1\\r\\n");', text)
        self.assertIn('a90_console_printf("doompad.source=serial-control\\r\\n");', text)
        self.assertIn('a90_console_printf("doompad.event seq=%u role=%s value=%d\\r\\n",', text)
        self.assertIn('a90_console_printf("doompad.state seq=%u forward=%d back=%d left=%d right=%d fire=%d use=%d menu=%d run=%d active=%d\\r\\n",', text)
        self.assertIn('strcmp(role, "forward") == 0', text)
        self.assertIn('strcmp(role, "fire") == 0', text)
        self.assertIn('strcmp(role, "run") == 0', text)

        block = function_block(text, "cmd_doompad")
        self.assertNotIn("/dev/input", block)
        self.assertNotIn("open(", block)
        self.assertNotIn("ioctl(", block)
        self.assertNotIn("EVIOCGRAB", block)
        self.assertNotIn("O_WRONLY", block)
        self.assertNotIn("uinput", block)
        self.assertNotIn("sendevent", block)

    def test_dispatch_and_help_expose_doompad(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")
        usage = "doompad [status|reset|key <role> <0|1>|tap <role>]"
        self.assertIn("static int handle_doompad(char **argv, int argc)", dispatch)
        self.assertIn("return cmd_doompad(argv, argc);", dispatch)
        self.assertIn(f'{{ "doompad", handle_doompad, "{usage}", CMD_NONE, A90_CMD_GROUP_INPUT }},', dispatch)
        self.assertIn(f'a90_console_printf("{usage}\\r\\n");', help_text)

    def test_video_status_reports_current_gameplay_loop_frontier(self) -> None:
        text = STATUS_HUD.read_text(encoding="utf-8")
        self.assertIn('a90_console_printf("video.status.doom_input=serial-doompad-staged\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.asset_id=doompad-loop-v3016\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.status=doompad-frame-loop-ready\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input=serial-doompad-consumed\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.virtual_controller=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.consumed=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.hardware_gate=none-serial-control\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.next=scripted-doompad-gameplay-loop-validation\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.command=doompad key <role> <0|1>\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.keyboard_fallback=usb-keyboard-otg\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.play.command=video demo doom play [frames]\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.doom.%s=doompad-frame-loop\\r\\n", action);', text)
        self.assertNotIn('video.demo.input.hardware_gate=usb-keyboard-otg\\r\\n");', text)
        self.assertNotIn('video.demo.input.next=attach-usb-keyboard-otg\\r\\n");', text)

    def test_menu_action_reports_serial_controller_frontier(self) -> None:
        menu = MENU_SOURCE.read_text(encoding="utf-8")
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn('{ "DOOM",          "SERIAL DOOMPAD STATUS", SCREEN_MENU_DEMO_DOOM', menu)
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
        self.assertIn('a90_console_printf("menu.demo.doom.input.keyboard_fallback=usb-keyboard-otg\\r\\n");', text)
        self.assertIn("rc = cmd_video_demo(demo_argv,", text)
        self.assertNotIn('menu.demo.doom.input.hardware_gate=usb-keyboard-otg\\r\\n");', text)
        self.assertNotIn('menu.demo.doom.input.command=doominput <keyboard-event> 32 60000\\r\\n");', text)

    def test_render_report_describes_serial_controller_candidate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3014_doompad_serial_controller.img",
            "boot_sha256": "abc123",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "v3014_marker_strings": [
                "doompad.version=1",
                "video.demo.input.command=doompad key <role> <0|1>",
            ],
        }
        report = runner.render_report(manifest, ("helper",), ("init",))
        self.assertIn("Native Init V3014 DOOMPAD Serial Controller Source Build", report)
        self.assertIn("host-serial virtual controller", report)
        self.assertIn("native-init-memory-only", report)
        self.assertIn("does not open `/dev/input`", report)
        self.assertIn("doompad-serial-controller-candidate", report)


if __name__ == "__main__":
    unittest.main()
