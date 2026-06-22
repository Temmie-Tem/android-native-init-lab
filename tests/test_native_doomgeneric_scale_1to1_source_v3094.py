from __future__ import annotations

import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3094_doomgeneric_scale_1to1.py")


class NativeDoomgenericScale1to1SourceV3094Tests(unittest.TestCase):
    def test_builder_contract_pins_v3094_scale_1to1_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3094")
        self.assertEqual(runner.INIT_VERSION, "0.10.103")
        self.assertEqual(runner.INIT_BUILD, "v3094-doomgeneric-scale-1to1")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3094")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3094-scale-1to1")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3094-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3094-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3094-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3094-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3094-pace.sock")
        self.assertEqual(runner.TICK_TELEMETRY_PATH, "/tmp/a90-doomgeneric-v3094-tick-telemetry.txt")
        self.assertEqual(runner.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS, 0)
        self.assertEqual(runner.BASELINE_NATIVE_DASHBOARD_LARGE_FRAME, 1)
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.BASELINE_FRAME_SCALE, "3:2-minimal-fastscale")
        self.assertEqual(runner.FRAME_SCALE, "1:1")
        self.assertIn(runner.TICK_TELEMETRY_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.SCALE_1TO1_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.TICK_TELEMETRY_PATH.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.large_frame=0", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.frame_scale=1:1", runner.REQUIRED_STRINGS)
        self.assertIn(b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq", runner.REQUIRED_STRINGS)
        self.assertIn(b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback", runner.REQUIRED_STRINGS)

    def test_v3094_adapter_records_tick_telemetry_and_scale_marker(self) -> None:
        v3033 = runner.v3033_module()
        saved_adapter = runner.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3086.v3084.v3083.v3081.v3081_adapter_source
        large_frame_modules = [
            runner.v3086,
            runner.v3086.v3084,
            runner.v3086.v3084.v3083,
            runner.v3086.v3084.v3083.v3081,
            runner.v3086.v3084.v3083.v3081.v3079,
            runner.v3086.v3084.v3083.v3081.v3079.v3077,
            runner.v3086.v3084.v3083.v3081.v3079.v3077.v3074,
            runner.v3086.v3084.v3083.v3081.v3079.v3077.v3074.v3071,
            v3033,
        ]
        saved_large = [getattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", None) for module in large_frame_modules]
        try:
            runner.apply_v3094_globals()

            source = runner.v3094_adapter_source()
        finally:
            runner.V3059.v3059_adapter_source = saved_adapter
            runner.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            for module, value in zip(large_frame_modules, saved_large):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value

        self.assertIn("extern int I_GetTime(void);", source)
        self.assertIn("extern int gametic;", source)
        self.assertIn("a90_doomgeneric_v3094_tick_telemetry_policy", source)
        self.assertIn("a90_doomgeneric_v3094_scale_policy", source)
        self.assertIn(runner.TICK_TELEMETRY_MARKER, source)
        self.assertIn(runner.SCALE_1TO1_MARKER, source)
        self.assertIn(f'#define A90_DG_TICK_TELEMETRY_PATH "{runner.TICK_TELEMETRY_PATH}"', source)
        self.assertIn("static int a90_doomgeneric_write_tick_telemetry", source)
        self.assertIn("++tick_telemetry_sleep_calls;", source)
        self.assertIn("tick_telemetry_sleep_ms_total += ms;", source)
        self.assertIn("++tick_telemetry_getticks_calls;", source)
        self.assertIn('fprintf(fp, "i_get_time=%d\\n", i_time)', source)
        self.assertIn('fprintf(fp, "gametic=%d\\n", observed_gametic)', source)
        self.assertIn("a90_doomgeneric_write_tick_telemetry(", source)
        self.assertIn("A90_DG_TICK_TELEMETRY_PATH, frames, index, final_rc", source)
        self.assertIn("a90_doomgeneric_open_input_udp(input_udp_port)", source)
        self.assertIn("a90_doomgeneric_open_pace_socket(pace_socket_path)", source)
        self.assertIn("a90_doomgeneric_write_shared_frame(&shared_frame)", source)

    def test_v3094_mutates_build_surface_custom_adapter_and_large_frame_flag(self) -> None:
        v3033 = runner.v3033_module()
        saved_paths = {
            "shared": getattr(v3033, "SHARED_FRAME_PATH", None),
            "pace": getattr(v3033, "PACE_SOCKET_PATH", None),
        }
        saved_adapter = runner.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3086.v3084.v3083.v3081.v3081_adapter_source
        large_frame_modules = [
            runner.v3086,
            runner.v3086.v3084,
            runner.v3086.v3084.v3083,
            runner.v3086.v3084.v3083.v3081,
            runner.v3086.v3084.v3083.v3081.v3079,
            runner.v3086.v3084.v3083.v3081.v3079.v3077,
            runner.v3086.v3084.v3083.v3081.v3079.v3077.v3074,
            runner.v3086.v3084.v3083.v3081.v3079.v3077.v3074.v3071,
            v3033,
        ]
        saved_large = [getattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", None) for module in large_frame_modules]
        try:
            runner.apply_v3094_globals()

            self.assertEqual(runner.v3086.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3086.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(runner.v3086.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(runner.v3086.v3084.CYCLE, runner.CYCLE)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            for module in large_frame_modules:
                self.assertEqual(module.NATIVE_DASHBOARD_LARGE_FRAME, 0)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3094_adapter_source)
        finally:
            runner.V3059.v3059_adapter_source = saved_adapter
            runner.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            for module, value in zip(large_frame_modules, saved_large):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value
            if saved_paths["shared"] is not None:
                v3033.SHARED_FRAME_PATH = saved_paths["shared"]
            if saved_paths["pace"] is not None:
                v3033.PACE_SOCKET_PATH = saved_paths["pace"]

    def test_report_template_records_v3095_live_gate_and_scale_contract(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3094.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --pace-socket /tmp/a90-doomgeneric-v3094-pace.sock",
            },
            "v3033_marker_strings": [
                "v3094-doomgeneric-scale-1to1",
                runner.TICK_TELEMETRY_MARKER,
                runner.SCALE_1TO1_MARKER,
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3094 DOOMGENERIC 1:1 Scale Source Build", report)
        self.assertIn(f"Telemetry path: `{runner.TICK_TELEMETRY_PATH}`", report)
        self.assertIn(f"Scale marker: `{runner.SCALE_1TO1_MARKER}`", report)
        self.assertIn("Candidate large dashboard frame: `0`", report)
        self.assertIn("Candidate frame scale: `1:1`", report)
        self.assertIn("fake_ticks_ms", report)
        self.assertIn("Run ID: `V3095`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
