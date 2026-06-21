from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3042_doomgeneric_latency_color.py")


class NativeDoomgenericLatencyColorSourceV3042Tests(unittest.TestCase):
    def test_builder_contract_pins_v3042_latency_color_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3042")
        self.assertEqual(runner.INIT_VERSION, "0.10.80")
        self.assertEqual(runner.INIT_BUILD, "v3042-doomgeneric-latency-color")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3042")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3042-latency-color")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3042-latency-color-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3042-input.state")
        self.assertEqual(runner.LOOP_FRAME_MS, 33)
        self.assertIn(b"a90.doomgeneric.v3042.frame_color=rb-swap-to-xbgr8888", runner.REQUIRED_STRINGS)
        self.assertIn(b"a90.doomgeneric.v3042.loop=input-state-file-to-DG_GetKey-33ms", runner.REQUIRED_STRINGS)

    def test_adapter_source_swaps_red_blue_before_xbgr8888_dump(self) -> None:
        source = runner.v3042_adapter_source()

        self.assertIn("a90.doomgeneric.v3042.latency_color=33ms-loop-rb-swap-xbgr8888", source)
        self.assertIn("a90.doomgeneric.v3042.frame_color=rb-swap-to-xbgr8888", source)
        self.assertIn("a90_doomgeneric_swap_rb_to_xbgr8888", source)
        self.assertIn("((pixel & (pixel_t)0x00ff0000U) >> 16)", source)
        self.assertIn("((pixel & (pixel_t)0x000000ffU) << 16)", source)
        self.assertIn("frame_sink[i] = a90_doomgeneric_swap_rb_to_xbgr8888(DG_ScreenBuffer[i]);", source)
        self.assertNotIn("memcpy(frame_sink, DG_ScreenBuffer", source)

    def test_native_presenter_loop_frame_ms_is_build_flag_overridable(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("#ifndef VIDEO_DEMO_DOOMGENERIC_LOOP_FRAME_MS", source)
        self.assertIn("#ifdef A90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS", source)
        self.assertIn("#define VIDEO_DEMO_DOOMGENERIC_LOOP_FRAME_MS ((int)A90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS)", source)

    def test_report_template_records_v3043_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3042.img",
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
                "helper_loop_command": "helper --wad-frame-loop --frame-ms 33",
                "loop_start_command": "video demo doom loop-start 300 --wad runtime-private",
                "host_keyboard_bridge": "workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py",
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "frame_width": runner.FRAME_WIDTH,
                "frame_height": runner.FRAME_HEIGHT,
                "frame_stride": runner.FRAME_STRIDE,
                "frame_bytes": runner.FRAME_BYTES,
                "loop_frame_ms": runner.LOOP_FRAME_MS,
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3042/doom",
                "engine_binary_sha256": "engine-sha",
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
            },
            "v3033_marker_strings": [
                "v3042-doomgeneric-latency-color",
                "a90.doomgeneric.v3042.frame_color=rb-swap-to-xbgr8888",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3042 DOOMGENERIC Latency Color Source Build", report)
        self.assertIn("33ms", report)
        self.assertIn("rb-swap-to-xbgr8888", report)
        self.assertIn("Run ID: `V3043`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
