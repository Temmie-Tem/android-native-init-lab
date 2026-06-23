from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3112_doomgeneric_hw_plane_cached_crtc.py")


class NativeDoomgenericHwPlaneCachedCrtcSourceV3112Tests(unittest.TestCase):
    def test_builder_contract_pins_v3112_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3112")
        self.assertEqual(runner.INIT_VERSION, "0.10.111")
        self.assertEqual(runner.INIT_BUILD, "v3112-doomgeneric-hw-plane-cached-crtc")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3112")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3112-hw-plane-cached-crtc")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3112-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3112-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3112-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3112-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3112-pace.sock")
        self.assertEqual(runner.TICK_TELEMETRY_PATH, "/tmp/a90-doomgeneric-v3112-tick-telemetry.txt")
        self.assertEqual(runner.FRAME_SCALE, "3:2-hw-plane-cached-crtc")
        self.assertEqual(runner.SCALE_PATH, "drm-plane-srcdst-cached-crtc")
        self.assertEqual(runner.FALLBACK_SCALE_PATH, "fast-3to2-rowcopy")
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.stage=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.cached_crtc_index=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.atomic_cap_rc=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.fetch_resources_rc=", runner.REQUIRED_STRINGS)

    def test_kms_source_records_plane_diagnostic_stages(self) -> None:
        kms_source = (REPO_ROOT / "workspace/public/src/native-init/a90_kms.c").read_text(encoding="utf-8")
        kms_header = (REPO_ROOT / "workspace/public/src/native-init/a90_kms.h").read_text(encoding="utf-8")

        self.assertIn("a90_kms_scaled_plane_stage_name", kms_header)
        self.assertIn("A90_KMS_SCALED_PLANE_STAGE_FETCH_PLANES", kms_header)
        self.assertIn("A90_KMS_SCALED_PLANE_STAGE_SETPLANE", kms_header)
        self.assertIn("plane_count", kms_header)
        self.assertIn("compatible_count", kms_header)
        self.assertIn("idle_xbgr_count", kms_header)
        self.assertIn("crtc_index", kms_header)
        self.assertIn("used_cached_crtc_index", kms_header)
        self.assertIn("universal_cap_rc", kms_header)
        self.assertIn("atomic_cap_rc", kms_header)
        self.assertIn("fetch_resources_rc", kms_header)
        self.assertIn("DRM_CLIENT_CAP_ATOMIC", kms_source)
        self.assertIn("kms_state.crtc_index >= 0", kms_source)
        self.assertIn("select->used_cached_crtc_index = 1", kms_source)
        self.assertIn("A90_KMS_SCALED_PLANE_STAGE_FETCH_RESOURCES", kms_source)
        self.assertIn("A90_KMS_SCALED_PLANE_STAGE_SCAN_PLANES", kms_source)
        self.assertIn("A90_KMS_SCALED_PLANE_STAGE_SETPLANE", kms_source)
        self.assertIn("errno = ENODEV;", kms_source)
        self.assertNotIn("backlight", kms_source.lower())
        self.assertNotIn("regulator", kms_source.lower())
        self.assertNotIn("gdsc", kms_source.lower())

    def test_native_hud_emits_hw_plane_diagnostics(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video.demo.doom.dashboard.hw_plane.stage=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.stage_id=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.crtc_index=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.cached_crtc_index=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.plane_count=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.compatible_count=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.idle_xbgr_count=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.universal_cap_rc=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.atomic_cap_rc=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.fetch_resources_rc=", hud_source)
        self.assertIn("a90_kms_scaled_plane_stage_name", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy", hud_source)

    def test_adapter_source_uses_v3112_paths_and_diagnostic_marker(self) -> None:
        source = runner.v3112_adapter_source()

        self.assertIn(runner.SCALE_MARKER, source)
        self.assertIn(runner.TICK_TELEMETRY_MARKER, source)
        self.assertIn("scale_path=drm-plane-srcdst-cached-crtc", source)
        self.assertIn(runner.TICK_TELEMETRY_PATH, source)
        self.assertNotIn("/tmp/a90-doomgeneric-v3108", source)
        self.assertNotIn("a90.doomgeneric.v3108", source)

    def test_apply_globals_enables_v3112_identity_and_diagnostics(self) -> None:
        v3033 = runner.v3033_module()
        saved_adapter = runner.v3108.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3108.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source
        saved_large = getattr(v3033, "NATIVE_DASHBOARD_LARGE_FRAME", None)
        saved_hw = getattr(v3033, "HW_PLANE_SCALE", None)
        saved_shared = getattr(v3033, "SHARED_FRAME_PATH", None)
        saved_pace = getattr(v3033, "PACE_SOCKET_PATH", None)
        try:
            runner.apply_v3112_globals()
            base = runner.v3108.v3100.v3098.v3096.v3086

            self.assertEqual(base.CYCLE, runner.CYCLE)
            self.assertEqual(base.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(base.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(base.BOOT_IMAGE, runner.BOOT_IMAGE)
            self.assertEqual(v3033.NATIVE_DASHBOARD_LARGE_FRAME, 1)
            self.assertEqual(v3033.HW_PLANE_SCALE, 1)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertIs(runner.v3108.V3059.v3059_adapter_source, runner.v3112_adapter_source)
        finally:
            runner.v3108.V3059.v3059_adapter_source = saved_adapter
            runner.v3108.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            if saved_large is not None:
                v3033.NATIVE_DASHBOARD_LARGE_FRAME = saved_large
            if saved_hw is not None:
                v3033.HW_PLANE_SCALE = saved_hw
            if saved_shared is not None:
                v3033.SHARED_FRAME_PATH = saved_shared
            if saved_pace is not None:
                v3033.PACE_SOCKET_PATH = saved_pace

    def test_report_template_records_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3112.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --shared-frame --diagnostics",
            },
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3112 DOOMGENERIC Hardware Plane Cached CRTC Source Build", report)
        self.assertIn("V3111 proved", report)
        self.assertIn("stage=fetch-resources", report)
        self.assertIn("cached CRTC index", report)
        self.assertIn("DRM_CLIENT_CAP_ATOMIC", report)
        self.assertIn("Run ID: `V3113`", report)
        self.assertIn("pre-scaled producer", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
