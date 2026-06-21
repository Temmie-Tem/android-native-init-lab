from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3033_doomgeneric_visible_loop.py")
keyboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py")
ROOT = REPO_ROOT


class NativeDoomgenericVisibleLoopSourceV3033Tests(unittest.TestCase):
    def test_builder_contract_pins_v3033_visible_loop_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3033")
        self.assertEqual(runner.INIT_VERSION, "0.10.76")
        self.assertEqual(runner.INIT_BUILD, "v3033-doomgeneric-visible-loop")
        self.assertEqual(runner.RUNTIME_WAD_PATH, "/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD")
        self.assertEqual(runner.EXPECTED_WAD_SHA256, "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3033-loop-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3033-input.state")
        self.assertEqual(runner.DEFAULT_LOOP_FRAMES, 90)
        self.assertEqual(runner.LOOP_FRAME_MS, 50)
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3033")
        self.assertIn(b"--wad-frame-loop", runner.REQUIRED_STRINGS)
        self.assertIn(b"--input-state", runner.REQUIRED_STRINGS)
        self.assertIn(b"host_doompad_keyboard_v3033.py", runner.REQUIRED_STRINGS)
        self.assertFalse(runner.ENGINE_RAMDISK_PATH.lower().endswith(".wad"))
        self.assertEqual(runner.v3029.count_wad_entries(["init", runner.ENGINE_RAMDISK_PATH]), 0)

    def test_adapter_source_adds_state_file_frame_loop(self) -> None:
        source = runner.v3033_adapter_source()

        self.assertIn("a90.doomgeneric.v3033.visible_loop=state-file-frame-loop", source)
        self.assertIn("a90.doomgeneric.v3033.loop=input-state-file-to-DG_GetKey", source)
        self.assertIn("a90_doomgeneric_apply_input_state_file", source)
        self.assertIn("a90_doomgeneric_dump_frame_xbgr8888_atomic", source)
        self.assertIn("a90_doomgeneric_run_wad_frame_loop", source)
        self.assertIn('strcmp(argv[1], "--wad-frame-loop") == 0', source)
        self.assertIn('strcmp(argv[7], "--input-state") == 0', source)
        self.assertIn('strcmp(argv[9], "--frame-ms") == 0', source)
        self.assertIn("a90_doomgeneric_feed_snapshot(&snapshot);", source)
        self.assertIn("doomgeneric_Tick()", source)
        self.assertIn("usleep((useconds_t)frame_ms * 1000U);", source)
        self.assertNotIn("/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD", source)

    def test_native_bridge_exposes_loop_helper_and_input_state_file_without_injection(self) -> None:
        header = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.h").read_text(encoding="utf-8")
        source = (ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")
        combined = header + source

        self.assertIn("struct a90_doomgeneric_input_state", combined)
        self.assertIn("input_state_path", combined)
        self.assertIn("A90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH", combined)
        self.assertIn("a90_doomgeneric_bridge_write_input_state", combined)
        self.assertIn("a90_doomgeneric_bridge_start_frame_loop_helper", combined)
        self.assertIn("--wad-frame-loop", combined)
        self.assertIn("--input-state", combined)
        self.assertIn("--frame-ms", combined)
        self.assertNotIn("/dev/input", combined)
        self.assertNotIn("uinput", combined.lower())
        self.assertNotIn("/efs", combined)

    def test_video_doom_loop_commands_and_background_presenter_are_wired(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video demo doom loop [frames] --wad runtime-private --sha256", text)
        self.assertIn("video demo doom loop-start [frames] --wad runtime-private --sha256", text)
        self.assertIn("video demo doom loop-stop", text)
        self.assertIn("video_demo_doom_run_visible_loop", text)
        self.assertIn("video_demo_doom_loop_start", text)
        self.assertIn("fork()", text)
        self.assertIn("setsid()", text)
        self.assertIn("a90_doomgeneric_bridge_start_frame_loop_helper", text)
        self.assertIn("video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop", text)
        self.assertIn("video.demo.doom.loop_start=background-presenter", text)
        self.assertIn("host_doompad_keyboard_v3033.py", text)

    def test_doompad_mirrors_serial_state_to_helper_input_file(self) -> None:
        text = (ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c").read_text(encoding="utf-8")

        self.assertIn("doompad_mirror_bridge_input_state", text)
        self.assertIn("a90_doomgeneric_bridge_write_input_state(&input)", text)
        self.assertIn("doompad.input_state.path=%s", text)
        self.assertIn("doompad.input_state.updated=%d", text)
        self.assertIn("menu.demo.doom.action=visible-playable-loop", text)
        self.assertIn('demo_argv[3] = "loop";', text)
        self.assertIn('demo_argv[4] = "90";', text)
        self.assertIn("menu.demo.doom.loop.command=video demo doom loop 90", text)
        self.assertIn("menu.demo.doom.loop_rc=%d", text)
        menu = (ROOT / "workspace/public/src/native-init/a90_menu.c").read_text(encoding="utf-8")
        self.assertIn("WAD PLAYABLE LOOP", menu)

    def test_host_keyboard_bridge_maps_keys_and_cleans_up(self) -> None:
        self.assertEqual(keyboard.DEFAULT_LOOP_FRAME_MS, 33)
        self.assertEqual(keyboard.role_for_key_token("w"), "forward")
        self.assertEqual(keyboard.role_for_key_token("\x1b[A"), "forward")
        self.assertEqual(keyboard.role_for_key_token(" "), "fire")
        self.assertEqual(keyboard.role_for_key_token("\r"), "use")
        self.assertEqual(keyboard.role_for_key_token("r"), "run")
        self.assertEqual(keyboard.doompad_command("fire", True), ["doompad", "key", "fire", "1"])
        self.assertEqual(
            keyboard.loop_start_command(8, "a" * 64),
            [
                "video",
                "demo",
                "doom",
                "loop-start",
                "8",
                "--wad",
                "runtime-private",
                "--sha256",
                "a" * 64,
            ],
        )

        class FakeSender:
            def __init__(self) -> None:
                self.sent: list[list[str]] = []

            def send(self, command: list[str]) -> int:
                self.sent.append(list(command))
                return 0

        sender = FakeSender()
        session = keyboard.DoompadKeyboardSession(sender, hold_ms=10)
        self.assertTrue(session.handle_token("w", now=1.0))
        session.release_expired(now=1.02)
        session.release_all()
        self.assertIn(["doompad", "key", "forward", "1"], sender.sent)
        self.assertIn(["doompad", "key", "forward", "0"], sender.sent)
        self.assertIn(["doompad", "key", "run", "0"], sender.sent)

    def test_host_keyboard_loop_keeper_restarts_inactive_visible_loop(self) -> None:
        class FakeSender:
            def __init__(self) -> None:
                self.sent: list[tuple[list[str], bool]] = []
                self.responses = [
                    keyboard.a90ctl.ProtocolResult(
                        {},
                        {"rc": "0", "status": "ok", "cmd": "loop-status"},
                        "video.demo.doom.loop_status.active=0\n",
                    ),
                    keyboard.a90ctl.ProtocolResult(
                        {},
                        {"rc": "0", "status": "ok", "cmd": "loop-start"},
                        "",
                    ),
                ]

            def send_result(self, command: list[str], *, fast: bool = False):
                self.sent.append((list(command), fast))
                return self.responses.pop(0)

        sender = FakeSender()
        keeper = keyboard.DoomLoopKeeper(
            sender,
            loop_frames=10,
            frame_ms=10,
            sha256="a" * 64,
            restart_grace_ms=5,
        )
        keeper.loop_started_at = 1.0
        keeper.next_check_at = 1.105

        rc = keeper.maybe_restart(now=1.2)

        self.assertEqual(rc, 0)
        self.assertEqual(
            sender.sent,
            [
                (["video", "demo", "doom", "loop-status"], True),
                (keyboard.loop_start_command(10, "a" * 64), True),
            ],
        )
        self.assertEqual(keeper.loop_started_at, 1.2)

    def test_report_template_records_v3034_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3033.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_root": runner.RUNTIME_WAD_ROOT,
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "runtime_wad_max_bytes": runner.RUNTIME_WAD_MAX_BYTES,
                "ramdisk_wad_file_count": 0,
                "public_wad_file_count": 0,
                "wad_embedded_in_boot": 0,
                "helper_loop_command": "helper --wad-frame-loop",
                "loop_command": "video demo doom loop 90 --wad runtime-private",
                "loop_start_command": "video demo doom loop-start 300 --wad runtime-private",
                "host_keyboard_bridge": "workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py",
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "frame_format": "xbgr8888-raw",
                "frame_width": runner.FRAME_WIDTH,
                "frame_height": runner.FRAME_HEIGHT,
                "frame_stride": runner.FRAME_STRIDE,
                "frame_bytes": runner.FRAME_BYTES,
                "default_loop_frames": runner.DEFAULT_LOOP_FRAMES,
                "loop_frame_ms": runner.LOOP_FRAME_MS,
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3033/doom",
                "engine_binary_sha256": "engine-sha",
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
            },
            "v3033_marker_strings": [
                "v3033-doomgeneric-visible-loop",
                "video demo doom loop [frames] --wad runtime-private --sha256",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3033 DOOMGENERIC Visible Loop Source Build", report)
        self.assertIn("WAD files in ramdisk: `0`", report)
        self.assertIn("WAD bytes embedded in boot image: `0`", report)
        self.assertIn("host_doompad_keyboard_v3033.py", report)
        self.assertIn("Run ID: `V3034`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
