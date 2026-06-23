from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3114_doomgeneric_hw_plane_atomic.py")


class NativeDoomgenericHwPlaneAtomicSourceV3114Tests(unittest.TestCase):
    def test_builder_contract_pins_v3114_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3114")
        self.assertEqual(runner.INIT_VERSION, "0.10.112")
        self.assertEqual(runner.INIT_BUILD, "v3114-doomgeneric-hw-plane-atomic")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3114")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3114-hw-plane-atomic")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3114-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3114-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3114-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3114-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3114-pace.sock")
        self.assertEqual(runner.TICK_TELEMETRY_PATH, "/tmp/a90-doomgeneric-v3114-tick-telemetry.txt")
        self.assertEqual(runner.FRAME_SCALE, "3:2-hw-plane-atomic")
        self.assertEqual(runner.SCALE_PATH, "drm-plane-srcdst-atomic")
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.atomic_attempted=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.atomic_props_rc=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.atomic_commit_rc=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.hw_plane.legacy_setplane_rc=", runner.REQUIRED_STRINGS)
        self.assertIn(b"atomic-props", runner.REQUIRED_STRINGS)
        self.assertIn(b"atomic-commit", runner.REQUIRED_STRINGS)

    def test_kms_source_adds_atomic_commit_and_preserves_cached_diagnostics(self) -> None:
        kms_source = (REPO_ROOT / "workspace/public/src/native-init/a90_kms.c").read_text(encoding="utf-8")
        kms_header = (REPO_ROOT / "workspace/public/src/native-init/a90_kms.h").read_text(encoding="utf-8")

        self.assertIn("struct a90_kms_atomic_plane_props", kms_source)
        self.assertIn("kms_scaled_plane.select = select", kms_source)
        self.assertIn("kms_scaled_plane_copy_cached_select_result", kms_source)
        self.assertIn("DRM_IOCTL_MODE_OBJ_GETPROPERTIES", kms_source)
        self.assertIn("DRM_IOCTL_MODE_GETPROPERTY", kms_source)
        self.assertIn("DRM_IOCTL_MODE_ATOMIC", kms_source)
        self.assertIn("FB_ID", kms_source)
        self.assertIn("CRTC_ID", kms_source)
        self.assertIn("SRC_W", kms_source)
        self.assertIn("A90_KMS_SCALED_PLANE_STAGE_ATOMIC_PROPS", kms_header)
        self.assertIn("A90_KMS_SCALED_PLANE_STAGE_ATOMIC_COMMIT", kms_header)
        self.assertIn("atomic_attempted", kms_header)
        self.assertIn("atomic_props_rc", kms_header)
        self.assertIn("atomic_commit_rc", kms_header)
        self.assertIn("legacy_setplane_rc", kms_header)
        self.assertNotIn("backlight", kms_source.lower())
        self.assertNotIn("regulator", kms_source.lower())
        self.assertNotIn("gdsc", kms_source.lower())

    def test_native_hud_emits_atomic_plane_diagnostics(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video.demo.doom.dashboard.hw_plane.atomic_attempted=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.atomic_props_rc=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.atomic_prop_count=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.atomic_commit_rc=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.legacy_setplane_rc=", hud_source)
        self.assertIn("video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy", hud_source)

    def test_adapter_source_uses_v3114_paths_and_atomic_marker(self) -> None:
        source = runner.v3114_adapter_source()

        self.assertIn(runner.SCALE_MARKER, source)
        self.assertIn(runner.TICK_TELEMETRY_MARKER, source)
        self.assertIn("scale_path=drm-plane-srcdst-atomic", source)
        self.assertIn(runner.TICK_TELEMETRY_PATH, source)
        self.assertNotIn("/tmp/a90-doomgeneric-v3108", source)
        self.assertNotIn("/tmp/a90-doomgeneric-v3112", source)
        self.assertNotIn("a90.doomgeneric.v3108", source)
        self.assertNotIn("a90.doomgeneric.v3112", source)

    def test_apply_globals_enables_v3114_identity(self) -> None:
        v3033 = runner.v3033_module()
        saved_parent_adapter = runner.v3112.v3112_adapter_source
        saved_parent_report = runner.v3112.render_report
        saved_large = getattr(v3033, "NATIVE_DASHBOARD_LARGE_FRAME", None)
        saved_hw = getattr(v3033, "HW_PLANE_SCALE", None)
        saved_shared = getattr(v3033, "SHARED_FRAME_PATH", None)
        saved_pace = getattr(v3033, "PACE_SOCKET_PATH", None)
        try:
            runner.apply_v3114_globals()
            base = runner.v3112.v3108.v3100.v3098.v3096.v3086

            self.assertEqual(base.CYCLE, runner.CYCLE)
            self.assertEqual(base.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(base.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(base.BOOT_IMAGE, runner.BOOT_IMAGE)
            self.assertEqual(v3033.NATIVE_DASHBOARD_LARGE_FRAME, 1)
            self.assertEqual(v3033.HW_PLANE_SCALE, 1)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertIs(runner.v3112.v3112_adapter_source, runner.v3114_adapter_source)
        finally:
            runner.v3112.v3112_adapter_source = saved_parent_adapter
            runner.v3112.render_report = saved_parent_report
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
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3114.img",
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

        self.assertIn("Native Init V3114 DOOMGENERIC Hardware Plane Atomic Source Build", report)
        self.assertIn("DRM_IOCTL_MODE_ATOMIC", report)
        self.assertIn("atomic_commit_rc", report)
        self.assertIn("legacy `SETPLANE` failed", report)
        self.assertIn("Run ID: `V3115`", report)
        self.assertIn("pre-scaled producer fallback", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
