from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3040_doomgeneric_large_dashboard_quiet.py")


class NativeDoomgenericLargeDashboardQuietSourceV3040Tests(unittest.TestCase):
    def test_builder_contract_pins_v3040_quiet_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3040")
        self.assertEqual(runner.INIT_VERSION, "0.10.79")
        self.assertEqual(runner.INIT_BUILD, "v3040-doomgeneric-large-dashboard-quiet")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3040")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3040-large-dashboard-quiet")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3040-large-dashboard-frame.xbgr8888")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3040-input.state")
        self.assertEqual(runner.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 1)
        self.assertIn(b"video.demo.doom.dashboard.presenter_log=quiet-per-frame", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.frame_scale=3:2", runner.REQUIRED_STRINGS)

    def test_native_status_hud_uses_quiet_doomdash_presenter(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn('a90_kms_present("doomdash", false)', source)
        self.assertNotIn('a90_kms_present("doomdash", true)', source)
        self.assertIn("video.demo.doom.dashboard.presenter_log=quiet-per-frame", source)
        self.assertIn("video.demo.doom.dashboard.frame_mode=large-overlay-title", source)
        self.assertIn("video_demo_doom_blit_raw_frame_scaled", source)

    def test_v3040_adapter_source_updates_private_helper_markers(self) -> None:
        source = runner.v3040_adapter_source()

        self.assertIn(
            "a90.doomgeneric.v3040.large_dashboard_quiet=state-file-frame-loop-kms-large-overlay-title-quiet-present",
            source,
        )
        self.assertIn("a90.doomgeneric.v3040.loop=input-state-file-to-DG_GetKey", source)
        self.assertIn("a90_doomgeneric_run_wad_frame_loop", source)
        self.assertIn("--wad-frame-loop", source)
        self.assertNotIn("a90.doomgeneric.v3033.visible_loop=state-file-frame-loop", source)

    def test_configure_v3040_globals_sets_wrapped_builder(self) -> None:
        runner.configure_v3040_globals()

        self.assertEqual(runner.v3038.CYCLE, "V3040")
        self.assertEqual(runner.v3038.INIT_VERSION, "0.10.79")
        self.assertEqual(runner.v3038.INIT_BUILD, "v3040-doomgeneric-large-dashboard-quiet")
        self.assertEqual(runner.v3038.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3040")
        self.assertEqual(runner.v3038.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.v3038.NATIVE_DASHBOARD_LARGE_FRAME, 1)
        self.assertIs(runner.v3038.render_report, runner.render_report)
        self.assertEqual(runner.v3038.v3038_adapter_source(), runner.v3040_adapter_source())

    def test_report_template_records_quiet_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3040.img",
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
                "loop_start_command": "video demo doom loop-start 300 --wad runtime-private",
                "host_keyboard_bridge": "workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py",
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "frame_width": runner.FRAME_WIDTH,
                "frame_height": runner.FRAME_HEIGHT,
                "loop_frame_ms": runner.LOOP_FRAME_MS,
                "engine_ramdisk_path": runner.ENGINE_REMOTE_PATH,
                "engine_binary": "workspace/private/builds/native-init/v3040/doom",
                "engine_binary_sha256": "engine-sha",
                "engine_binary_bytes": 123,
                "helper_bundled_in_ramdisk": True,
            },
            "v3033_marker_strings": [
                "v3040-doomgeneric-large-dashboard-quiet",
                "video.demo.doom.dashboard.presenter_log=quiet-per-frame",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3040 DOOMGENERIC Large Dashboard Quiet Source Build", report)
        self.assertIn('a90_kms_present("doomdash", false)', report)
        self.assertIn("video.demo.doom.dashboard.presenter_log=quiet-per-frame", report)
        self.assertIn("Run ID: `V3041`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
