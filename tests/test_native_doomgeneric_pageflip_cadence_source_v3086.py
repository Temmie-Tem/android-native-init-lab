from __future__ import annotations

import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3086_doomgeneric_pageflip_cadence.py")


class NativeDoomgenericPageflipCadenceSourceV3086Tests(unittest.TestCase):
    def test_builder_contract_pins_v3086_pageflip_cadence_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3086")
        self.assertEqual(runner.INIT_VERSION, "0.10.100")
        self.assertEqual(runner.INIT_BUILD, "v3086-doomgeneric-pageflip-cadence")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3086")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3086-pageflip-cadence")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3086-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3086-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3086-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3086-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3086-pace.sock")
        self.assertEqual(runner.BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS, 18)
        self.assertEqual(runner.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS, 0)
        self.assertEqual(runner.CANDIDATE_BACKGROUND_CANCEL, "disabled-serial-preserve")
        self.assertIn(
            b"video.demo.doom.presenter.pageflip_min_submit_interval_ms=%d",
            runner.REQUIRED_STRINGS,
        )
        self.assertIn(
            b"video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
            runner.REQUIRED_STRINGS,
        )
        self.assertIn(b"video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy", runner.REQUIRED_STRINGS)

    def test_v3086_mutates_build_surface_and_pageflip_guard(self) -> None:
        v3033 = runner.v3033_module()
        pageflip_modules = [
            runner.v3084,
            runner.v3084.v3083,
            runner.v3084.v3083.v3081,
            runner.v3084.v3083.v3081.v3079,
            v3033,
        ]
        large_frame_modules = [
            runner.v3084.v3083,
            runner.v3084.v3083.v3081,
            runner.v3084.v3083.v3081.v3079,
            runner.v3084.v3083.v3081.v3079.v3077,
            runner.v3084.v3083.v3081.v3079.v3077.v3074,
            runner.v3084.v3083.v3081.v3079.v3077.v3074.v3071,
            v3033,
        ]
        saved_pageflip = [
            getattr(module, "PAGEFLIP_MIN_SUBMIT_INTERVAL_MS", None)
            for module in pageflip_modules
        ]
        saved_large_frame = [
            getattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", None)
            for module in large_frame_modules
        ]
        saved_paths = {
            "shared": getattr(v3033, "SHARED_FRAME_PATH", None),
            "pace": getattr(v3033, "PACE_SOCKET_PATH", None),
        }
        try:
            runner.apply_v3086_globals()

            self.assertEqual(runner.v3084.v3083.v3081.v3079.v3077.v3074.v3071.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3084.v3083.v3081.v3079.v3077.v3074.v3071.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(runner.v3084.v3083.v3081.v3079.v3077.v3074.v3071.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            for module in pageflip_modules:
                self.assertEqual(module.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS, 0)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3084.v3083.v3081.v3081_adapter_source)
        finally:
            for module, value in zip(pageflip_modules, saved_pageflip):
                if value is not None:
                    module.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = value
            for module, value in zip(large_frame_modules, saved_large_frame):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value
            if saved_paths["shared"] is not None:
                v3033.SHARED_FRAME_PATH = saved_paths["shared"]
            if saved_paths["pace"] is not None:
                v3033.PACE_SOCKET_PATH = saved_paths["pace"]

    def test_report_template_records_v3087_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3086.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --pace-socket /tmp/a90-doomgeneric-v3086-pace.sock",
            },
            "v3033_marker_strings": [
                "v3086-doomgeneric-pageflip-cadence",
                "video.demo.doom.presenter.pageflip_min_submit_interval_ms=%d",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3086 DOOMGENERIC Pageflip Cadence Source Build", report)
        self.assertIn("Baseline pageflip min submit interval ms: `18`", report)
        self.assertIn("Candidate pageflip min submit interval ms: `0`", report)
        self.assertIn("Run ID: `V3087`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
