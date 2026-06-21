"""Static checks for V3016 DOOMPAD gameplay-loop source build."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
STATUS_HUD = REPO / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_APPS = REPO / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_native_init_boot_v3016_doompad_gameplay_loop as runner  # noqa: E402


def source_block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


class TestNativeDoompadGameplayLoopSourceV3016(unittest.TestCase):
    def test_build_identity_and_marker_contract(self) -> None:
        self.assertEqual(runner.CYCLE, "V3016")
        self.assertEqual(runner.INIT_VERSION, "0.10.71")
        self.assertEqual(runner.INIT_BUILD, "v3016-doompad-gameplay-loop")
        self.assertTrue(str(runner.BOOT_IMAGE).endswith("boot_linux_v3016_doompad_gameplay_loop.img"))
        markers = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"A90 Linux init 0.10.71 (v3016-doompad-gameplay-loop)", markers)
        self.assertIn(b"video.demo.asset_id=doompad-loop-v3016", markers)
        self.assertIn(b"video.demo.status=doompad-frame-loop-ready", markers)
        self.assertIn(b"video.demo.engine=doompad-loop-not-doomgeneric", markers)
        self.assertIn(b"video.demo.input=serial-doompad-consumed", markers)
        self.assertIn(b"video.demo.input.consumed=doompad-serial-v3014", markers)
        self.assertIn(b"video.demo.play.command=video demo doom play [frames]", markers)
        self.assertIn(b"doomplay.version=1", markers)
        self.assertIn(b"doomplay.source=doompad-state", markers)
        self.assertIn(b"doomplay.frames_presented=", markers)
        self.assertIn(b"video.demo.doom.play=doompad-frame-loop", markers)
        self.assertIn(b"menu.demo.doom.play.command=video demo doom play [frames]", markers)

    def test_video_demo_doom_routes_verify_and_play_to_doomplay(self) -> None:
        text = STATUS_HUD.read_text(encoding="utf-8")
        self.assertIn("static int cmd_doomplay(char **argv, int argc);", text)
        self.assertIn('a90_console_printf("video.demo.asset_id=doompad-loop-v3016\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.status=doompad-frame-loop-ready\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.gameplay_loop=doompad-kms-v3016\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input=serial-doompad-consumed\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.input.consumed=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.play.command=video demo doom play [frames]\\r\\n");', text)
        self.assertIn('a90_console_printf("video.demo.doom.%s=doompad-frame-loop\\r\\n", action);', text)
        self.assertIn('doom_argv[doom_argc++] = "doomplay";', text)
        self.assertIn("return cmd_doomplay(doom_argv, doom_argc);", text)
        self.assertNotIn('video.demo.doom.%s=blocked-gameplay-not-wired\\r\\n", action);', text)

    def test_doomplay_consumes_doompad_snapshot_without_input_injection(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn("struct doompad_snapshot {", text)
        self.assertIn("static void doompad_get_snapshot(struct doompad_snapshot *snapshot)", text)
        self.assertIn("static int doomplay_run_frames(int frames, bool render_frames)", text)
        self.assertIn("static int cmd_doomplay(char **argv, int argc)", text)
        self.assertIn("doompad_get_snapshot(&input);", text)
        self.assertIn('a90_console_printf("doomplay.consumed_doompad_seq=%u\\r\\n", input.seq);', text)
        self.assertIn('a90_console_printf("doomplay.input.forward=%d back=%d left=%d right=%d fire=%d use=%d menu=%d run=%d active=%d\\r\\n",', text)
        self.assertIn("if (input.forward) {", text)
        self.assertIn("player_y -= speed;", text)
        self.assertIn("if (input->fire) {", text)
        self.assertIn("a90_kms_begin_frame(0x050505)", text)
        self.assertIn('a90_kms_present("doomplay", false)', text)
        self.assertIn('a90_console_printf("doomplay.frames_presented=%d\\r\\n", render_frames ? presented : 0);', text)

        block = source_block(text, "#define DOOMPLAY_DEFAULT_FRAMES", "static void doominput_print_event")
        self.assertNotIn("/dev/input", block)
        self.assertNotIn("open(", block)
        self.assertNotIn("ioctl(", block)
        self.assertNotIn("EVIOCGRAB", block)
        self.assertNotIn("O_WRONLY", block)
        self.assertNotIn("uinput", block)
        self.assertNotIn("sendevent", block)
        self.assertNotIn("sysfs", block.lower())

    def test_menu_reports_gameplay_loop_frontier(self) -> None:
        text = MENU_APPS.read_text(encoding="utf-8")
        self.assertIn('a90_console_printf("menu.demo.doom.status=doompad-frame-loop-ready\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input=serial-doompad-consumed\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.live_handoff=v3016-doompad-gameplay-loop\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.input.consumed=doompad-serial-v3014\\r\\n");', text)
        self.assertIn('a90_console_printf("menu.demo.doom.play.command=video demo doom play [frames]\\r\\n");', text)
        self.assertNotIn('menu.demo.doom.status=blocked-gameplay-loop\\r\\n");', text)
        self.assertNotIn('menu.demo.doom.input=serial-doompad-staged\\r\\n");', text)

    def test_render_report_describes_gameplay_loop_candidate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3016_doompad_gameplay_loop.img",
            "boot_sha256": "abc123",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "v3016_marker_strings": [
                "doomplay.version=1",
                "video.demo.doom.play=doompad-frame-loop",
            ],
        }
        report = runner.render_report(manifest, ("helper",), ("init",))
        self.assertIn("Native Init V3016 DOOMPAD Gameplay Loop Source Build", report)
        self.assertIn("consumes the current `doompad` snapshot", report)
        self.assertIn("foreground KMS loop", report)
        self.assertIn("no evdev open", report.lower())
        self.assertIn("doompad-gameplay-loop-candidate", report)


if __name__ == "__main__":
    unittest.main()
