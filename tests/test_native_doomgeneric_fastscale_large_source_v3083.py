from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3083_doomgeneric_fastscale_large.py")


class NativeDoomgenericFastscaleLargeSourceV3083Tests(unittest.TestCase):
    def test_builder_contract_pins_v3083_fastscale_large_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3083")
        self.assertEqual(runner.INIT_VERSION, "0.10.98")
        self.assertEqual(runner.INIT_BUILD, "v3083-doomgeneric-fastscale-large")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3083")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3083-fastscale-large")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3083-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3083-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3083-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3083-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3083-pace.sock")
        self.assertEqual(runner.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.NATIVE_DASHBOARD_MINIMAL, 1)
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 1)
        self.assertEqual(runner.BASELINE_FRAME_SCALE, "1:1-minimal-dashboard")
        self.assertEqual(runner.CANDIDATE_FRAME_SCALE, "3:2-minimal-fastscale")
        self.assertEqual(runner.SCALE_PATH, "fast-3to2-rowcopy")
        self.assertIn(b"video.demo.doom.dashboard.large_frame=1", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.frame_mode=minimal-large-fastscale", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.frame_scale=3:2", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy", runner.REQUIRED_STRINGS)

    def test_native_hud_has_fast_3_to_2_scaler_and_minimal_large_markers(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video_demo_doom_scale_row_3_to_2", hud_source)
        self.assertIn("video_demo_doom_blit_raw_frame_scaled_3_to_2", hud_source)
        self.assertIn("video_demo_doom_blit_raw_frame_scaled(fb, source, render", hud_source)
        self.assertIn("A90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME", hud_source)
        self.assertIn("video.demo.doom.dashboard.frame_mode=minimal-large-fastscale", hud_source)
        self.assertIn("video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy", hud_source)
        self.assertIn("video.demo.doom.dashboard.scale_path=raw-rowcopy", hud_source)

    def test_v3083_mutates_v3081_build_surface_and_base_large_frame_flag(self) -> None:
        v3033 = runner.v3033_module()
        large_frame_modules = [
            runner.v3081,
            runner.v3081.v3079,
            runner.v3081.v3079.v3077,
            runner.v3081.v3079.v3077.v3074,
            runner.v3081.v3079.v3077.v3074.v3071,
            v3033,
        ]
        saved_large_frame = [
            getattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", None)
            for module in large_frame_modules
        ]
        saved_shared_frame_path = getattr(v3033, "SHARED_FRAME_PATH", None)
        saved_pace_socket_path = getattr(v3033, "PACE_SOCKET_PATH", None)
        try:
            runner.apply_v3083_globals()

            self.assertEqual(runner.v3081.v3079.v3077.v3074.v3071.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3081.v3079.v3077.v3074.v3071.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(runner.v3081.v3079.v3077.v3074.v3071.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(runner.v3081.v3079.v3077.v3074.NATIVE_DASHBOARD_LARGE_FRAME, 1)
            self.assertEqual(v3033.NATIVE_DASHBOARD_MINIMAL, 1)
            self.assertEqual(v3033.NATIVE_DASHBOARD_LARGE_FRAME, 1)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3081.v3081_adapter_source)
        finally:
            for module, value in zip(large_frame_modules, saved_large_frame):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value
            if saved_shared_frame_path is not None:
                v3033.SHARED_FRAME_PATH = saved_shared_frame_path
            if saved_pace_socket_path is not None:
                v3033.PACE_SOCKET_PATH = saved_pace_socket_path

    def test_report_template_records_v3084_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3083.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --shared-frame /tmp/a90-doomgeneric-v3083-shared-frame.bin",
            },
            "v3033_marker_strings": [
                "v3083-doomgeneric-fastscale-large",
                "video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3083 DOOMGENERIC Fastscale Large Source Build", report)
        self.assertIn("Baseline frame scale: `1:1-minimal-dashboard`", report)
        self.assertIn("Candidate frame scale: `3:2-minimal-fastscale`", report)
        self.assertIn("Scale path: `fast-3to2-rowcopy`", report)
        self.assertIn("Run ID: `V3084`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
