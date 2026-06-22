from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3069_doomgeneric_metrics_cache.py")


class NativeDoomgenericMetricsCacheSourceV3069Tests(unittest.TestCase):
    def test_builder_contract_pins_v3069_metrics_cache_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3069")
        self.assertEqual(runner.INIT_VERSION, "0.10.92")
        self.assertEqual(runner.INIT_BUILD, "v3069-doomgeneric-metrics-cache")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3069")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3069-metrics-cache")
        self.assertEqual(
            runner.FRAME_PATH,
            "/tmp/a90-doomgeneric-v3069-metrics-cache-frame.xbgr8888",
        )
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3069-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3069-input.sock")
        self.assertEqual(runner.INPUT_UDP_PORT, 30570)
        self.assertEqual(runner.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.PRESENTER_POLL_MS, 4)
        self.assertEqual(runner.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.REUSE_FRAME_BUFFER, 1)
        self.assertEqual(runner.BASELINE_DASHBOARD_METRICS_INTERVAL_FRAMES, 1)
        self.assertEqual(runner.DASHBOARD_METRICS_INTERVAL_FRAMES, 30)
        self.assertIn(b"v3069-doomgeneric-metrics-cache", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.presenter.reader=reused-loop-buffer", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.metrics_interval_frames=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.metrics_pacing=cached-frame-interval", runner.REQUIRED_STRINGS)

    def test_native_dashboard_caches_metrics_between_presented_frames(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("VIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES", hud_source)
        self.assertIn("static struct a90_metrics_snapshot metrics", hud_source)
        self.assertIn("static uint32_t metrics_frame = UINT32_MAX", hud_source)
        self.assertIn("static bool metrics_valid", hud_source)
        self.assertIn("frame_index - metrics_frame >= VIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES", hud_source)
        self.assertIn("video.demo.doom.dashboard.metrics_pacing=cached-frame-interval", hud_source)
        self.assertIn("video.demo.doom.dashboard.metrics_interval_frames=%u", hud_source)

    def test_base_builder_exposes_metrics_interval_compile_flag(self) -> None:
        base_source = (
            REPO_ROOT
            / "workspace/public/src/scripts/revalidation/build_native_init_boot_v3033_doomgeneric_visible_loop.py"
        ).read_text(encoding="utf-8")

        self.assertIn("DASHBOARD_METRICS_INTERVAL_FRAMES = 1", base_source)
        self.assertIn("VIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES", base_source)

    def test_v3069_mutates_v3067_build_surface_without_changing_input_or_reader(self) -> None:
        runner.apply_v3069_globals()
        v3033 = runner.v3033_module()

        self.assertEqual(runner.v3067.CYCLE, runner.CYCLE)
        self.assertEqual(runner.v3067.INIT_VERSION, runner.INIT_VERSION)
        self.assertEqual(runner.v3067.INIT_BUILD, runner.INIT_BUILD)
        self.assertEqual(runner.v3067.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.v3067.PRESENTER_POLL_MS, 4)
        self.assertEqual(runner.v3067.INPUT_UDP_PORT, 30570)
        self.assertEqual(runner.v3067.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.v3067.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.v3067.FRAME_PATH, runner.FRAME_PATH)
        self.assertEqual(v3033.REUSE_FRAME_BUFFER, 1)
        self.assertEqual(v3033.DASHBOARD_METRICS_INTERVAL_FRAMES, 30)
        self.assertIs(runner.v3067.render_report, runner.render_report)

    def test_report_template_records_v3070_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3069.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "frame_path": runner.FRAME_PATH,
                "helper_loop_command": "helper --frame-ms 28 --input-udp 30570",
                "loop_frame_ms": runner.LOOP_FRAME_MS,
                "presenter_poll_ms": runner.PRESENTER_POLL_MS,
            },
            "v3033_marker_strings": [
                "v3069-doomgeneric-metrics-cache",
                "video.demo.doom.dashboard.metrics_pacing=cached-frame-interval",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3069 DOOMGENERIC Metrics Cache Source Build", report)
        self.assertIn("Baseline metrics interval frames: `1`", report)
        self.assertIn("Candidate metrics interval frames: `30`", report)
        self.assertIn("Metrics pacing marker: `cached-frame-interval`", report)
        self.assertIn("Run ID: `V3070`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
