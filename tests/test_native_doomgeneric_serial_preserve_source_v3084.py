from __future__ import annotations

import unittest

from _loader import REPO_ROOT, load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3084_doomgeneric_serial_preserve.py")


class NativeDoomgenericSerialPreserveSourceV3084Tests(unittest.TestCase):
    def test_builder_contract_pins_v3084_serial_preserve_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3084")
        self.assertEqual(runner.INIT_VERSION, "0.10.99")
        self.assertEqual(runner.INIT_BUILD, "v3084-doomgeneric-serial-preserve")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3084")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3084-serial-preserve")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3084-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3084-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3084-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3084-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3084-pace.sock")
        self.assertEqual(runner.BASELINE_BACKGROUND_CANCEL, "background-child-reads-serial-cancel")
        self.assertEqual(runner.CANDIDATE_BACKGROUND_CANCEL, "disabled-serial-preserve")
        self.assertIn(
            b"video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
            runner.REQUIRED_STRINGS,
        )
        self.assertIn(b"video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy", runner.REQUIRED_STRINGS)
        self.assertIn(b"shared-mmap-copy", runner.REQUIRED_STRINGS)

    def test_native_loop_cancels_only_foreground_loops(self) -> None:
        hud_source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(encoding="utf-8")

        self.assertIn("video.demo.doom.loop_start.background_cancel=disabled-serial-preserve", hud_source)
        self.assertIn("if (!background_child) {\n            enum a90_cancel_kind cancel = a90_console_poll_cancel(1);", hud_source)
        self.assertNotIn("\n        cancel = a90_console_poll_cancel(1);\n", hud_source)
        self.assertIn('return a90_console_cancelled("doomgeneric-loop", cancel);', hud_source)

    def test_v3084_mutates_v3083_build_surface_and_base_paths(self) -> None:
        v3033 = runner.v3033_module()
        large_frame_modules = [
            runner.v3083,
            runner.v3083.v3081,
            runner.v3083.v3081.v3079,
            runner.v3083.v3081.v3079.v3077,
            runner.v3083.v3081.v3079.v3077.v3074,
            runner.v3083.v3081.v3079.v3077.v3074.v3071,
            v3033,
        ]
        saved_large_frame = [
            getattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", None)
            for module in large_frame_modules
        ]
        saved = {
            "shared": getattr(v3033, "SHARED_FRAME_PATH", None),
            "pace": getattr(v3033, "PACE_SOCKET_PATH", None),
        }
        try:
            runner.apply_v3084_globals()

            self.assertEqual(runner.v3083.v3081.v3079.v3077.v3074.v3071.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3083.v3081.v3079.v3077.v3074.v3071.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(runner.v3083.v3081.v3079.v3077.v3074.v3071.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            self.assertEqual(v3033.NATIVE_DASHBOARD_LARGE_FRAME, 1)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3083.v3081.v3081_adapter_source)
        finally:
            for module, value in zip(large_frame_modules, saved_large_frame):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value
            if saved["shared"] is not None:
                v3033.SHARED_FRAME_PATH = saved["shared"]
            if saved["pace"] is not None:
                v3033.PACE_SOCKET_PATH = saved["pace"]

    def test_report_template_records_v3085_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3084.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --shared-frame /tmp/a90-doomgeneric-v3084-shared-frame.bin",
            },
            "v3033_marker_strings": [
                "v3084-doomgeneric-serial-preserve",
                "video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3084 DOOMGENERIC Serial Preserve Source Build", report)
        self.assertIn("Baseline background cancel: `background-child-reads-serial-cancel`", report)
        self.assertIn("Candidate background cancel: `disabled-serial-preserve`", report)
        self.assertIn("Run ID: `V3085`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
