from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3123_doomgeneric_summary_only_direct_blit.py")


class NativeDoomgenericSummaryOnlyDirectBlitSourceV3123Tests(unittest.TestCase):
    def test_builder_contract_pins_v3123_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3123")
        self.assertEqual(runner.INIT_VERSION, "0.10.116")
        self.assertEqual(runner.INIT_BUILD, "v3123-doomgeneric-summary-only-direct-blit")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3123")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3123-summary-only-direct-blit")
        self.assertEqual(runner.FRAME_WIDTH, 960)
        self.assertEqual(runner.FRAME_HEIGHT, 600)
        self.assertEqual(runner.NO_FULL_CLEAR, 1)
        self.assertEqual(runner.DIRECT_SHARED_BLIT, 1)
        self.assertEqual(runner.FOREGROUND_FRAME_LOG, 0)
        self.assertEqual(runner.FRAME_IPC, "shared-mmap-direct-blit-summary-only")
        self.assertIn(b"video.demo.doom.loop.foreground_frame_log=%d", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.presenter_log=%s", runner.REQUIRED_STRINGS)
        self.assertIn(b"summary-only", runner.REQUIRED_STRINGS)

    def test_native_sources_have_summary_only_foreground_log_gate(self) -> None:
        hud = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")
        base = (
            REPO_ROOT
            / "workspace/public/src/scripts/revalidation/build_native_init_boot_v3033_doomgeneric_visible_loop.py"
        ).read_text(encoding="utf-8")

        self.assertIn("VIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG", hud)
        self.assertIn("video.demo.doom.loop.foreground_frame_log=%d", hud)
        self.assertIn("video.demo.doom.dashboard.presenter_log=%s", hud)
        self.assertIn("summary-only", hud)
        self.assertIn("FOREGROUND_FRAME_LOG = 1", base)
        self.assertIn('numeric_define("VIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG", 0)', base)

    def test_adapter_source_uses_v3123_paths_and_markers(self) -> None:
        source = runner.v3123_adapter_source()

        self.assertIn(runner.SCALE_MARKER, source)
        self.assertIn(runner.TICK_TELEMETRY_MARKER, source)
        self.assertIn(runner.PHASE_TELEMETRY_MARKER, source)
        self.assertIn(runner.TICK_TELEMETRY_PATH, source)
        self.assertNotIn("/tmp/a90-doomgeneric-v3120", source)
        self.assertNotIn("a90.doomgeneric.v3120", source)

    def test_apply_globals_sets_direct_blit_and_summary_only_flag(self) -> None:
        v3033 = runner.v3120.v3118.v3116.v3033_module()
        saved_apply = runner.v3120.apply_v3120_globals
        saved_adapter = runner.v3120.v3120_adapter_source
        saved_report = runner.v3120.render_report
        saved_direct = getattr(v3033, "DIRECT_SHARED_BLIT", None)
        saved_foreground_log = getattr(v3033, "FOREGROUND_FRAME_LOG", None)
        try:
            runner.apply_v3123_globals()

            self.assertEqual(runner.v3120.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3120.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(runner.v3120.BOOT_IMAGE, runner.BOOT_IMAGE)
            self.assertEqual(v3033.DIRECT_SHARED_BLIT, 1)
            self.assertEqual(v3033.FOREGROUND_FRAME_LOG, 0)
            self.assertIs(runner.v3120.v3120_adapter_source, runner.v3123_adapter_source)
            self.assertIs(runner.v3120.render_report, runner.render_report)
        finally:
            runner.v3120.apply_v3120_globals = saved_apply
            runner.v3120.v3120_adapter_source = saved_adapter
            runner.v3120.render_report = saved_report
            if saved_direct is not None:
                v3033.DIRECT_SHARED_BLIT = saved_direct
            if saved_foreground_log is not None:
                v3033.FOREGROUND_FRAME_LOG = saved_foreground_log

    def test_report_template_records_v3124_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3123.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --shared-frame --direct",
            },
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3123 DOOMGENERIC Summary-Only Direct Blit Source Build", report)
        self.assertIn("VIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG=0", report)
        self.assertIn("Run ID: `V3124`", report)
        self.assertIn("shared-mmap-direct-blit", report)
        self.assertIn("summary-only", report)


if __name__ == "__main__":
    unittest.main()
