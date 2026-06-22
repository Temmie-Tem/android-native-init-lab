from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3065_doomgeneric_large_scale_off.py")


class NativeDoomgenericLargeScaleOffSourceV3065Tests(unittest.TestCase):
    def test_builder_contract_pins_v3065_large_scale_off_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3065")
        self.assertEqual(runner.INIT_VERSION, "0.10.90")
        self.assertEqual(runner.INIT_BUILD, "v3065-doomgeneric-large-scale-off")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3065")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3065-large-scale-off")
        self.assertEqual(
            runner.FRAME_PATH,
            "/tmp/a90-doomgeneric-v3065-large-scale-off-frame.xbgr8888",
        )
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3065-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3065-input.sock")
        self.assertEqual(runner.INPUT_UDP_PORT, 30570)
        self.assertEqual(runner.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.PRESENTER_POLL_MS, 4)
        self.assertEqual(runner.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.BASELINE_NATIVE_DASHBOARD_LARGE_FRAME, 1)
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertIn(b"v3065-doomgeneric-large-scale-off", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.large_frame=0", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.frame_scale=1:1", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.presenter.pacing=helper-frame-mtime", runner.REQUIRED_STRINGS)

    def test_native_dashboard_reports_large_frame_off_markers(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video.demo_doom_blit_raw_frame_scaled", hud_source.replace("video_demo", "video.demo"))
        self.assertIn("video.demo.doom.dashboard.large_frame=0", hud_source)
        self.assertIn("video.demo.doom.dashboard.frame_mode=standard-dashboard", hud_source)
        self.assertIn("video.demo.doom.dashboard.frame_scale=1:1", hud_source)

    def test_v3065_mutates_v3063_build_surface_without_changing_input_or_pacing(self) -> None:
        runner.apply_v3065_globals()

        self.assertEqual(runner.v3063.CYCLE, runner.CYCLE)
        self.assertEqual(runner.v3063.INIT_VERSION, runner.INIT_VERSION)
        self.assertEqual(runner.v3063.INIT_BUILD, runner.INIT_BUILD)
        self.assertEqual(runner.v3063.LOOP_FRAME_MS, 28)
        self.assertEqual(runner.v3063.PRESENTER_POLL_MS, 4)
        self.assertEqual(runner.v3063.INPUT_UDP_PORT, 30570)
        self.assertEqual(runner.v3063.NATIVE_DASHBOARD, 1)
        self.assertEqual(runner.v3063.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.v3063.FRAME_PATH, runner.FRAME_PATH)
        self.assertIs(runner.v3063.render_report, runner.render_report)

    def test_report_template_records_v3066_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3065.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "input_path": "udp-ncm-to-DG_GetKey-with-serial-doompad-fallback",
                "input_udp_port": runner.INPUT_UDP_PORT,
                "input_socket_path": runner.INPUT_SOCKET_PATH,
                "input_state_path": runner.INPUT_STATE_PATH,
                "frame_path": runner.FRAME_PATH,
                "helper_loop_command": "helper --frame-ms 28 --input-udp 30570",
                "loop_frame_ms": runner.LOOP_FRAME_MS,
                "presenter_poll_ms": runner.PRESENTER_POLL_MS,
                "presenter_pacing": "helper-frame-mtime",
            },
            "v3033_marker_strings": [
                "v3065-doomgeneric-large-scale-off",
                "video.demo.doom.dashboard.large_frame=0",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3065 DOOMGENERIC Large Scale Off Source Build", report)
        self.assertIn("Baseline large dashboard frame: `1`", report)
        self.assertIn("Candidate large dashboard frame: `0`", report)
        self.assertIn("Candidate frame scale: `1:1`", report)
        self.assertIn("Run ID: `V3066`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
