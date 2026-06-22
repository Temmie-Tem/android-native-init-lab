from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3071_doomgeneric_frame_timing.py")


class NativeDoomgenericFrameTimingSourceV3071Tests(unittest.TestCase):
    def test_builder_contract_pins_v3071_frame_timing_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3071")
        self.assertEqual(runner.INIT_VERSION, "0.10.93")
        self.assertEqual(runner.INIT_BUILD, "v3071-doomgeneric-frame-timing")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3071")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3071-frame-timing")
        self.assertEqual(
            runner.FRAME_PATH,
            "/tmp/a90-doomgeneric-v3071-frame-timing-frame.xbgr8888",
        )
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3071-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3071-input.sock")
        self.assertEqual(runner.INPUT_UDP_PORT, 30570)
        self.assertEqual(runner.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.PRESENTER_POLL_MS, 4)
        self.assertEqual(runner.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.REUSE_FRAME_BUFFER, 1)
        self.assertEqual(runner.DASHBOARD_METRICS_INTERVAL_FRAMES, 30)
        self.assertEqual(runner.BASELINE_FRAME_TIMING_PROBE, 0)
        self.assertEqual(runner.FRAME_TIMING_PROBE, 1)
        self.assertIn(b"v3071-doomgeneric-frame-timing", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.presenter.reader=reused-loop-buffer", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.metrics_interval_frames=", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.metrics_pacing=cached-frame-interval", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.loop.timing_probe=1", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.loop.timing=frame-ipc-kms-stage-us", runner.REQUIRED_STRINGS)

    def test_native_presenter_records_stage_timing(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("VIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE", hud_source)
        self.assertIn("struct video_demo_doom_present_timing", hud_source)
        self.assertIn("struct video_demo_doom_timing_stats", hud_source)
        self.assertIn("video_demo_doom_timing_stats_add", hud_source)
        self.assertIn("video_demo_doom_timing_stats_print", hud_source)
        self.assertIn("timing->read_ns = video_demo_doom_elapsed_ns(t_after_alloc, t_after_read)", hud_source)
        self.assertIn("timing->present_ns = video_demo_doom_elapsed_ns(t_after_draw, t_after_present)", hud_source)
        self.assertIn("video.demo.doom.loop.timing=frame-ipc-kms-stage-us", hud_source)

    def test_base_builder_exposes_timing_probe_compile_flag(self) -> None:
        base_source = (
            REPO_ROOT
            / "workspace/public/src/scripts/revalidation/build_native_init_boot_v3033_doomgeneric_visible_loop.py"
        ).read_text(encoding="utf-8")

        self.assertIn("FRAME_TIMING_PROBE = 0", base_source)
        self.assertIn("VIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE", base_source)

    def test_v3071_mutates_v3069_build_surface_without_changing_input_or_reader(self) -> None:
        runner.apply_v3071_globals()
        v3033 = runner.v3033_module()

        self.assertEqual(runner.v3069.CYCLE, runner.CYCLE)
        self.assertEqual(runner.v3069.INIT_VERSION, runner.INIT_VERSION)
        self.assertEqual(runner.v3069.INIT_BUILD, runner.INIT_BUILD)
        self.assertEqual(runner.v3069.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.v3069.PRESENTER_POLL_MS, 4)
        self.assertEqual(runner.v3069.INPUT_UDP_PORT, 30570)
        self.assertEqual(runner.v3069.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.v3069.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.v3069.FRAME_PATH, runner.FRAME_PATH)
        self.assertEqual(v3033.REUSE_FRAME_BUFFER, 1)
        self.assertEqual(v3033.DASHBOARD_METRICS_INTERVAL_FRAMES, 30)
        self.assertEqual(v3033.FRAME_TIMING_PROBE, 1)
        self.assertIs(runner.v3069.render_report, runner.render_report)

    def test_report_template_records_v3072_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3071.img",
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
                "v3071-doomgeneric-frame-timing",
                "video.demo.doom.loop.timing_probe=1",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3071 DOOMGENERIC Frame Timing Source Build", report)
        self.assertIn("Baseline frame timing probe: `0`", report)
        self.assertIn("Candidate frame timing probe: `1`", report)
        self.assertIn("Timing marker: `frame-ipc-kms-stage-us`", report)
        self.assertIn("Run ID: `V3072`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
