from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3108_doomgeneric_hw_plane_scale.py")


class NativeDoomgenericHwPlaneScaleSourceV3108Tests(unittest.TestCase):
    def test_builder_contract_pins_v3108_hw_plane_scale_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3108")
        self.assertEqual(runner.INIT_VERSION, "0.10.109")
        self.assertEqual(runner.INIT_BUILD, "v3108-doomgeneric-hw-plane-scale")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3108")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3108-hw-plane-scale")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3108-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3108-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3108-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3108-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3108-pace.sock")
        self.assertEqual(runner.TICK_TELEMETRY_PATH, "/tmp/a90-doomgeneric-v3108-tick-telemetry.txt")
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 1)
        self.assertEqual(runner.HW_PLANE_SCALE, 1)
        self.assertEqual(runner.FRAME_SCALE, "3:2-hw-plane")
        self.assertEqual(runner.SCALE_PATH, "drm-plane-srcdst")
        self.assertEqual(runner.FALLBACK_SCALE_PATH, "fast-3to2-rowcopy")
        self.assertIn(b"video.demo.doom.dashboard.hw_plane_scale=1", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.scale_path=drm-plane-srcdst", runner.REQUIRED_STRINGS)

    def test_kms_source_adds_bounded_scaled_plane_api(self) -> None:
        kms_source = (REPO_ROOT / "workspace/public/src/native-init/a90_kms.c").read_text(encoding="utf-8")
        kms_header = (REPO_ROOT / "workspace/public/src/native-init/a90_kms.h").read_text(encoding="utf-8")

        self.assertIn("a90_kms_present_scaled_plane_xbgr8888", kms_header)
        self.assertIn("a90_kms_disable_scaled_plane", kms_header)
        self.assertIn("DRM_IOCTL_MODE_GETPLANERESOURCES", kms_source)
        self.assertIn("DRM_IOCTL_MODE_GETPLANE", kms_source)
        self.assertIn("DRM_IOCTL_MODE_SETPLANE", kms_source)
        self.assertIn("idle = plane.crtc_id == 0 && plane.fb_id == 0", kms_source)
        self.assertIn("DRM_FORMAT_XBGR8888", kms_source)
        self.assertNotIn("backlight", kms_source.lower())
        self.assertNotIn("regulator", kms_source.lower())
        self.assertNotIn("gdsc", kms_source.lower())

    def test_native_hud_uses_hw_plane_scale_with_cpu_fallback(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("VIDEO_DEMO_DOOMGENERIC_HW_PLANE_SCALE", hud_source)
        self.assertIn("video_demo_doom_present_large_frame_path", hud_source)
        self.assertIn("a90_kms_present_scaled_plane_xbgr8888", hud_source)
        self.assertIn("video.demo.doom.dashboard.scale_path=drm-plane-srcdst", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy", hud_source)
        self.assertIn("a90_kms_disable_scaled_plane", hud_source)
        self.assertIn("video_demo_doom_blit_raw_frame_scaled(fb", hud_source)

    def test_v3108_adapter_keeps_original_cadence_not_paced_tic(self) -> None:
        source = runner.v3108_adapter_source()

        self.assertIn(runner.SCALE_MARKER, source)
        self.assertIn(runner.TICK_TELEMETRY_MARKER, source)
        self.assertIn("fake_time_model=DG_SleepMs-accumulated", source)
        self.assertIn("scale_path=drm-plane-srcdst", source)
        self.assertNotIn("paced_time_model=presenter-token-doom-tic-quantum", source)
        self.assertNotIn("a90_doomgeneric_advance_paced_time", source)
        self.assertNotIn("/tmp/a90-doomgeneric-v3100", source)

    def test_v3108_apply_globals_enables_large_hw_plane_flag(self) -> None:
        v3033 = runner.v3033_module()
        saved_adapter = runner.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source
        saved_large = getattr(v3033, "NATIVE_DASHBOARD_LARGE_FRAME", None)
        saved_hw = getattr(v3033, "HW_PLANE_SCALE", None)
        saved_shared = getattr(v3033, "SHARED_FRAME_PATH", None)
        saved_pace = getattr(v3033, "PACE_SOCKET_PATH", None)
        try:
            runner.apply_v3108_globals()

            self.assertEqual(runner.v3100.v3098.v3096.v3086.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3100.v3098.v3096.v3086.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(v3033.NATIVE_DASHBOARD_LARGE_FRAME, 1)
            self.assertEqual(v3033.HW_PLANE_SCALE, 1)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3108_adapter_source)
        finally:
            runner.V3059.v3059_adapter_source = saved_adapter
            runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            if saved_large is not None:
                v3033.NATIVE_DASHBOARD_LARGE_FRAME = saved_large
            if saved_hw is not None:
                v3033.HW_PLANE_SCALE = saved_hw
            if saved_shared is not None:
                v3033.SHARED_FRAME_PATH = saved_shared
            if saved_pace is not None:
                v3033.PACE_SOCKET_PATH = saved_pace

    def test_report_template_records_v3109_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3108.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --shared-frame --hw-plane",
            },
            "v3033_marker_strings": [
                runner.INIT_BUILD,
                runner.SCALE_MARKER,
                "video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3108 DOOMGENERIC Hardware Plane Scale Source Build", report)
        self.assertIn("Candidate scale path: `drm-plane-srcdst`", report)
        self.assertIn("Additional Cause Check", report)
        self.assertIn("hw_plane.presented=0", report)
        self.assertIn("DOOM 35 Hz game-tic cadence", report)
        self.assertIn("not real DOOM music/SFX", report)
        self.assertIn("fallback", report)
        self.assertIn("Run ID: `V3109`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
