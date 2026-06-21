from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3036_doomgeneric_native_dashboard.py")
host_dashboard = load_script("workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py")


class NativeDoomgenericNativeDashboardSourceV3036Tests(unittest.TestCase):
    def test_builder_contract_pins_v3036_native_dashboard_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3036")
        self.assertEqual(runner.INIT_VERSION, "0.10.77")
        self.assertEqual(runner.INIT_BUILD, "v3036-doomgeneric-native-dashboard")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3036")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3036-native-dashboard")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3036-dashboard-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3036-input.state")
        self.assertEqual(runner.DEFAULT_LOOP_FRAMES, 300)
        self.assertEqual(runner.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.LOOP_FRAME_MS, 50)
        self.assertEqual(host_dashboard.DEFAULT_LOOP_FRAME_MS, 33)
        self.assertIn(b"video.demo.doom.dashboard.native=1", runner.REQUIRED_STRINGS)
        self.assertIn(b"host_doompad_dashboard_v3035.py", runner.REQUIRED_STRINGS)

    def test_native_status_hud_has_dashboard_renderer_behind_build_flag(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("#define A90_DOOMGENERIC_NATIVE_DASHBOARD 0", source)
        self.assertIn("video_demo_doom_draw_native_dashboard", source)
        self.assertIn("DOOM LIVE DASHBOARD", source)
        self.assertIn("KEYBOARD / DOOMPAD INPUT", source)
        self.assertIn("video.demo.doom.dashboard.native=1", source)
        self.assertIn("top-frame-metrics-logs-input", source)
        self.assertIn("a90_metrics_read_snapshot(&metrics)", source)
        self.assertIn("video_demo_doom_dashboard_read_input_state", source)
        self.assertIn("host_doompad_dashboard_v3035.py", source)

    def test_v3036_adapter_source_updates_private_helper_markers(self) -> None:
        source = runner.v3036_adapter_source()

        self.assertIn(
            "a90.doomgeneric.v3036.native_dashboard=state-file-frame-loop-kms-dashboard",
            source,
        )
        self.assertIn("a90.doomgeneric.v3036.loop=input-state-file-to-DG_GetKey", source)
        self.assertIn("a90_doomgeneric_run_wad_frame_loop", source)
        self.assertIn("--wad-frame-loop", source)
        self.assertNotIn("a90.doomgeneric.v3033.visible_loop=state-file-frame-loop", source)

    def test_configure_v3036_globals_sets_base_builder_dashboard_flag(self) -> None:
        runner.configure_v3036_globals()

        self.assertEqual(runner.v3033.CYCLE, "V3036")
        self.assertEqual(runner.v3033.INIT_VERSION, "0.10.77")
        self.assertEqual(runner.v3033.INIT_BUILD, "v3036-doomgeneric-native-dashboard")
        self.assertEqual(runner.v3033.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3036")
        self.assertEqual(runner.v3033.NATIVE_DASHBOARD, 1)
        self.assertIs(runner.v3033.render_report, runner.render_report)
        self.assertEqual(runner.v3033.v3033_adapter_source(), runner.v3036_adapter_source())

    def test_report_template_records_native_dashboard_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3036.img",
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
                "loop_command": "video demo doom loop 300 --wad runtime-private",
                "loop_start_command": "video demo doom loop-start 300 --wad runtime-private",
                "host_keyboard_bridge": "workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py",
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "frame_width": runner.FRAME_WIDTH,
                "frame_height": runner.FRAME_HEIGHT,
                "frame_stride": runner.FRAME_STRIDE,
                "frame_bytes": runner.FRAME_BYTES,
                "default_loop_frames": runner.DEFAULT_LOOP_FRAMES,
                "loop_frame_ms": runner.LOOP_FRAME_MS,
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3036/doom",
                "engine_binary_sha256": "engine-sha",
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
            },
            "v3033_marker_strings": [
                "v3036-doomgeneric-native-dashboard",
                "video.demo.doom.dashboard.native=1",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3036 DOOMGENERIC Native Dashboard Source Build", report)
        self.assertIn("A90_DOOMGENERIC_NATIVE_DASHBOARD=1", report)
        self.assertIn("video.demo.doom.dashboard.layout=top-frame-metrics-logs-input", report)
        self.assertIn("host_doompad_dashboard_v3035.py", report)
        self.assertIn("Run ID: `V3037`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
