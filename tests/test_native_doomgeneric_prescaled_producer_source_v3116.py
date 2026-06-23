from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3116_doomgeneric_prescaled_producer.py")


class NativeDoomgenericPrescaledProducerSourceV3116Tests(unittest.TestCase):
    def test_builder_contract_pins_v3116_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3116")
        self.assertEqual(runner.INIT_VERSION, "0.10.113")
        self.assertEqual(runner.INIT_BUILD, "v3116-doomgeneric-prescaled-producer")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3116")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3116-prescaled-producer")
        self.assertEqual(runner.FRAME_WIDTH, 960)
        self.assertEqual(runner.FRAME_HEIGHT, 600)
        self.assertEqual(runner.FRAME_STRIDE, 3840)
        self.assertEqual(runner.FRAME_BYTES, 2304000)
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3116-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3116-shared-frame.bin")
        self.assertEqual(runner.FRAME_SCALE, "1:1-pre-scaled-producer")
        self.assertEqual(runner.SCALE_PATH, "producer-pre-scaled-raw-rowcopy")
        self.assertEqual(runner.HW_PLANE_SCALE, 0)
        self.assertEqual(runner.PRE_SCALED_LARGE_FRAME, 1)
        self.assertIn(b"video.demo.doom.dashboard.pre_scaled_large_frame=1", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.frame_scale=1:1-pre-scaled", runner.REQUIRED_STRINGS)
        self.assertNotIn(b"atomic-props", runner.REQUIRED_STRINGS)
        self.assertNotIn(b"atomic-commit", runner.REQUIRED_STRINGS)

    def test_native_sources_accept_prescaled_geometry_and_raw_rowcopy(self) -> None:
        bridge = (REPO_ROOT / "workspace/public/src/native-init/a90_doomgeneric_bridge.c").read_text(encoding="utf-8")
        hud = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")
        v3033 = (
            REPO_ROOT
            / "workspace/public/src/scripts/revalidation/build_native_init_boot_v3033_doomgeneric_visible_loop.py"
        ).read_text(encoding="utf-8")

        self.assertIn("VIDEO_DEMO_DOOMGENERIC_PRE_SCALED_LARGE_FRAME", hud)
        self.assertIn("video.demo.doom.dashboard.pre_scaled_large_frame=1", hud)
        self.assertIn("producer-pre-scaled-raw-rowcopy", hud)
        self.assertIn("frame_mode=minimal-large-pre-scaled-producer", hud)
        self.assertIn("dst_width != render->width || dst_height != render->height", hud)
        self.assertIn("return video_demo_doom_blit_raw_frame(fb, source, render, dst_x, dst_y);", hud)
        self.assertIn("render->width > 0U", bridge)
        self.assertIn("render->height > 0U", bridge)
        self.assertNotIn("render->width == 640U", bridge)
        self.assertNotIn("render->height == 400U", bridge)
        self.assertIn("PRE_SCALED_LARGE_FRAME = 0", v3033)
        self.assertIn("VIDEO_DEMO_DOOMGENERIC_PRE_SCALED_LARGE_FRAME", v3033)

    def test_adapter_source_uses_v3116_paths_and_producer_scale_marker(self) -> None:
        source = runner.v3116_adapter_source()

        self.assertIn(runner.SCALE_MARKER, source)
        self.assertIn(runner.TICK_TELEMETRY_MARKER, source)
        self.assertIn(runner.PHASE_TELEMETRY_MARKER, source)
        self.assertIn("scale_path=producer-pre-scaled-1to1", source)
        self.assertIn(runner.TICK_TELEMETRY_PATH, source)
        self.assertNotIn("/tmp/a90-doomgeneric-v3108", source)
        self.assertNotIn("/tmp/a90-doomgeneric-v3114", source)
        self.assertNotIn("a90.doomgeneric.v3108", source)
        self.assertNotIn("a90.doomgeneric.v3114", source)

    def test_apply_globals_enables_prescaled_geometry_and_helper_flags(self) -> None:
        v3033 = runner.v3033_module()
        saved_v3114_adapter = runner.v3114.v3114_adapter_source
        saved_v3114_report = runner.v3114.render_report
        saved_v3024_flags = (
            runner.v3024.COMMON_CFLAGS,
            runner.v3024.THIRD_PARTY_CFLAGS,
            runner.v3024.ADAPTER_CFLAGS,
        )
        saved_v3033 = {
            "FRAME_WIDTH": getattr(v3033, "FRAME_WIDTH", None),
            "FRAME_HEIGHT": getattr(v3033, "FRAME_HEIGHT", None),
            "FRAME_STRIDE": getattr(v3033, "FRAME_STRIDE", None),
            "FRAME_BYTES": getattr(v3033, "FRAME_BYTES", None),
            "PRE_SCALED_LARGE_FRAME": getattr(v3033, "PRE_SCALED_LARGE_FRAME", None),
            "HW_PLANE_SCALE": getattr(v3033, "HW_PLANE_SCALE", None),
        }
        try:
            runner.apply_v3116_globals()
            base = runner.v3114.v3112.v3108.v3100.v3098.v3096.v3086

            self.assertEqual(base.CYCLE, runner.CYCLE)
            self.assertEqual(base.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(base.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(base.BOOT_IMAGE, runner.BOOT_IMAGE)
            self.assertEqual(v3033.FRAME_WIDTH, runner.FRAME_WIDTH)
            self.assertEqual(v3033.FRAME_HEIGHT, runner.FRAME_HEIGHT)
            self.assertEqual(v3033.FRAME_STRIDE, runner.FRAME_STRIDE)
            self.assertEqual(v3033.FRAME_BYTES, runner.FRAME_BYTES)
            self.assertEqual(v3033.HW_PLANE_SCALE, 0)
            self.assertEqual(v3033.PRE_SCALED_LARGE_FRAME, 1)
            self.assertIn("-DDOOMGENERIC_RESX=960", runner.v3024.COMMON_CFLAGS)
            self.assertIn("-DDOOMGENERIC_RESY=600", runner.v3024.COMMON_CFLAGS)
            self.assertIs(runner.v3114.v3114_adapter_source, runner.v3116_adapter_source)
        finally:
            runner.v3114.v3114_adapter_source = saved_v3114_adapter
            runner.v3114.render_report = saved_v3114_report
            (
                runner.v3024.COMMON_CFLAGS,
                runner.v3024.THIRD_PARTY_CFLAGS,
                runner.v3024.ADAPTER_CFLAGS,
            ) = saved_v3024_flags
            for name, value in saved_v3033.items():
                if value is not None:
                    setattr(v3033, name, value)

    def test_report_template_records_next_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3116.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --shared-frame --pre-scaled",
            },
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3116 DOOMGENERIC Pre-Scaled Producer Source Build", report)
        self.assertIn("960x600", report)
        self.assertIn("VIDEO_DEMO_DOOMGENERIC_PRE_SCALED_LARGE_FRAME=1", report)
        self.assertIn("producer-pre-scaled-raw-rowcopy", report)
        self.assertIn("Run ID: `V3117`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
