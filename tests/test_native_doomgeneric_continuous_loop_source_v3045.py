from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3045_doomgeneric_continuous_loop.py")
keyboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py")
dashboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py")


class NativeDoomgenericContinuousLoopSourceV3045Tests(unittest.TestCase):
    def test_builder_contract_pins_v3045_continuous_loop_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3045")
        self.assertEqual(runner.INIT_VERSION, "0.10.81")
        self.assertEqual(runner.INIT_BUILD, "v3045-doomgeneric-continuous-loop")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3045")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3045-continuous-loop")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3045-continuous-loop-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3045-input.state")
        self.assertEqual(runner.CONTINUOUS_LOOP_FRAMES, 0)
        self.assertEqual(runner.LOOP_FRAME_MS, 33)
        self.assertEqual(keyboard.DEFAULT_LOOP_FRAMES, runner.CONTINUOUS_LOOP_FRAMES)
        self.assertEqual(dashboard.DEFAULT_LOOP_FRAMES, runner.CONTINUOUS_LOOP_FRAMES)
        self.assertIn(
            b"a90.doomgeneric.v3045.continuous_loop=33ms-loop-start-zero-continuous",
            runner.REQUIRED_STRINGS,
        )
        self.assertIn(b"video.demo.doom.loop_start.continuous", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.loop_status.continuous", runner.REQUIRED_STRINGS)

    def test_adapter_source_treats_zero_frames_as_continuous(self) -> None:
        source = runner.v3045_adapter_source()

        self.assertIn("a90.doomgeneric.v3045.loop_frames_zero=continuous", source)
        self.assertIn("a90_doomgeneric_parse_loop_frames", source)
        self.assertIn('strcmp(text, "0") == 0', source)
        self.assertIn("frames < 0 || frames > 300", source)
        self.assertIn("for (index = 0; frames == 0 || index < frames; ++index)", source)
        self.assertIn("frames = a90_doomgeneric_parse_loop_frames(argv[4], 300);", source)
        self.assertNotIn("frames <= 0 || frames > 300 || frame_ms <= 0", source)

    def test_native_status_hud_loop_start_defaults_to_continuous_background(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("static bool video_demo_doom_loop_continuous;", source)
        self.assertIn("static uint32_t video_demo_doom_loop_frames;", source)
        self.assertIn("video.demo.doom.loop_status.continuous=%d", source)
        self.assertIn("video.demo.doom.loop_start.continuous=%d", source)
        self.assertIn('uint32_t min_frames = strcmp(action, "loop-start") == 0 ? 0U : 1U;', source)
        self.assertIn('} else if (strcmp(action, "loop-start") == 0) {', source)
        self.assertIn("frames = 0U;", source)
        self.assertIn("while ((continuous || presented < frames) && (continuous || poll_count < max_polls))", source)

    def test_bridge_allows_zero_frame_loop_helper(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")

        self.assertIn(
            "pid_out == NULL || frames < 0 || frames > A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES",
            source,
        )
        self.assertNotIn(
            "pid_out == NULL || frames <= 0 || frames > A90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES",
            source,
        )

    def test_report_template_records_v3046_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3045.img",
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
                "loop_command": "video demo doom loop 300 --wad runtime-private",
                "host_keyboard_bridge": "workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py",
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "frame_width": runner.FRAME_WIDTH,
                "frame_height": runner.FRAME_HEIGHT,
                "loop_frame_ms": runner.LOOP_FRAME_MS,
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3045/doom",
                "engine_binary_sha256": "engine-sha",
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
            },
            "v3033_marker_strings": [
                "v3045-doomgeneric-continuous-loop",
                "a90.doomgeneric.v3045.loop_frames_zero=continuous",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3045 DOOMGENERIC Continuous Loop Source Build", report)
        self.assertIn("loop-start 0 --wad runtime-private", report)
        self.assertIn("Run ID: `V3046`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
