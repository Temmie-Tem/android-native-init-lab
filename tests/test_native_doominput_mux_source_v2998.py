"""Static checks for V2998 DOOM input multi-event mux source build."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
DISPATCH = REPO / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
HELP = REPO / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_native_init_boot_v2998_doominput_mux as runner  # noqa: E402


class TestNativeDoominputMuxSourceV2998(unittest.TestCase):
    def test_build_identity_and_marker_contract(self) -> None:
        self.assertEqual(runner.CYCLE, "V2998")
        self.assertEqual(runner.INIT_VERSION, "0.10.67")
        self.assertEqual(runner.INIT_BUILD, "v2998-doominput-mux")
        self.assertTrue(str(runner.BOOT_IMAGE).endswith("boot_linux_v2998_doominput_mux.img"))
        markers = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]", markers)
        self.assertIn(b"doominputmux.event %d: source=%s", markers)
        self.assertIn(b"doominputmux.state %d: source=%s", markers)
        self.assertIn(b"doom_button_forward", markers)
        self.assertIn(b"doom_button_back", markers)
        self.assertIn(b"doom_button_fire", markers)

    def test_source_adds_read_only_multi_event_mux(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn("#define DOOMINPUTMUX_MAX_EVENTS 4", text)
        self.assertIn("static int cmd_doominputmux(char **argv, int argc)", text)
        self.assertIn("doominputmux_parse_sources(argv[1], sources, &source_count)", text)
        self.assertIn("sources[index].fd = open(sources[index].path, O_RDONLY | O_NONBLOCK)", text)
        self.assertIn("poll(fds, (nfds_t)(source_count + 1), poll_timeout)", text)
        self.assertIn("doominput_apply_event(&state, &event)", text)
        self.assertIn("doominputmux_print_state(index, sources[fi].name, &state)", text)
        self.assertIn("doominputmux_close_sources(sources, source_count)", text)

    def test_source_preserves_button_proxy_mappings(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn('case KEY_VOLUMEUP:\n            return "doom_button_forward";', text)
        self.assertIn('case KEY_VOLUMEDOWN:\n            return "doom_button_back";', text)
        self.assertIn('case KEY_POWER:\n            return "doom_button_fire";', text)
        self.assertIn("case KEY_VOLUMEUP:\n        state->forward = down;", text)
        self.assertIn("case KEY_VOLUMEDOWN:\n        state->back = down;", text)
        self.assertIn("case KEY_POWER:\n        state->fire = down;", text)

    def test_command_is_registered_in_shell_and_help(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        help_text = HELP.read_text(encoding="utf-8")
        self.assertIn("static int handle_doominputmux(char **argv, int argc)", dispatch)
        self.assertIn('{ "doominputmux", handle_doominputmux, "doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]"', dispatch)
        self.assertIn('a90_console_printf("doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]', help_text)

    def test_mux_keeps_runtime_read_only(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn("O_RDONLY | O_NONBLOCK", text)
        self.assertNotIn("EVIOCGRAB", text)
        self.assertNotIn("O_WRONLY", text)
        self.assertNotIn("sendevent", text)
        self.assertNotIn("ioctl(sources", text)

    def test_render_report_describes_host_only_candidate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2998_doominput_mux.img",
            "boot_sha256": "abc123",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "v2998_marker_strings": [
                "doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]",
                "doominputmux.event",
                "doominputmux.state",
            ],
        }
        report = runner.render_report(manifest, ("helper",), ("init",))
        self.assertIn("Native Init V2998 DOOM Input Mux Source Build", report)
        self.assertIn("Host-side source build only", report)
        self.assertIn("event3 volume keys and event0 power", report)
        self.assertIn("not a final DOOM control scheme", report)
        self.assertIn("doominput-mux-candidate", report)


if __name__ == "__main__":
    unittest.main()
