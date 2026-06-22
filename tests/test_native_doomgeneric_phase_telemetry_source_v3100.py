from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3100_doomgeneric_phase_telemetry.py")
REPO_ROOT = Path(__file__).resolve().parents[1]


class NativeDoomgenericPhaseTelemetrySourceV3100Tests(unittest.TestCase):
    def test_builder_contract_pins_v3100_phase_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3100")
        self.assertEqual(runner.INIT_VERSION, "0.10.106")
        self.assertEqual(runner.INIT_BUILD, "v3100-doomgeneric-phase-telemetry")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3100")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3100-phase-telemetry")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3100-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3100-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3100-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3100-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3100-pace.sock")
        self.assertEqual(runner.TICK_TELEMETRY_PATH, "/tmp/a90-doomgeneric-v3100-tick-telemetry.txt")
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.FRAME_SCALE, "1:1")
        self.assertEqual(runner.SEQ_TELEMETRY, 1)
        self.assertIn(runner.TICK_TELEMETRY_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.PHASE_TELEMETRY_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.GAMETIC_FRAME_TELEMETRY_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(b"loop_tick.samples=%u", runner.REQUIRED_STRINGS)
        self.assertIn(b"loop_tick.draw_changed_iterations=%u", runner.REQUIRED_STRINGS)
        self.assertIn(b"draw_gametic.samples=%u", runner.REQUIRED_STRINGS)
        self.assertIn(b"dump_gametic.samples=%u", runner.REQUIRED_STRINGS)

    def test_v3100_adapter_splits_tick_draw_and_dump_phase_telemetry(self) -> None:
        source = runner.v3100_adapter_source()

        self.assertIn(runner.TICK_TELEMETRY_MARKER, source)
        self.assertIn(runner.PHASE_TELEMETRY_MARKER, source)
        self.assertIn("a90_doomgeneric_v3100_phase_policy", source)
        self.assertIn("static void a90_doomgeneric_record_phase_gametic(", source)
        self.assertIn("static void a90_doomgeneric_record_loop_tick_phase(", source)
        self.assertIn("a90_doomgeneric_record_loop_tick_phase(", source)
        self.assertIn("before_gametic", source)
        self.assertIn("before_draws", source)
        self.assertIn("draw_gametic_samples", source)
        self.assertIn('"loop_tick.samples=%u\\n"', source)
        self.assertIn('"loop_tick.gametic_changed=%u\\n"', source)
        self.assertIn('"loop_tick.draw_changed_iterations=%u\\n"', source)
        self.assertIn('"draw_gametic.samples=%u\\n"', source)
        self.assertIn('"draw_gametic.changed_transitions=%u\\n"', source)
        self.assertIn('"dump_gametic.samples=%u\\n"', source)
        self.assertIn("a90_doomgeneric_write_shared_frame(&shared_frame)", source)

    def test_v3100_apply_globals_mutates_build_surface(self) -> None:
        v3033 = runner.v3033_module()
        saved_adapter = runner.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source
        saved_seq_telemetry = getattr(v3033, "SEQ_TELEMETRY", None)
        saved_shared = getattr(v3033, "SHARED_FRAME_PATH", None)
        saved_pace = getattr(v3033, "PACE_SOCKET_PATH", None)
        large_frame_modules = [
            runner.v3098.v3096.v3086,
            runner.v3098.v3096.v3086.v3084,
            runner.v3098.v3096.v3086.v3084.v3083,
            runner.v3098.v3096.v3086.v3084.v3083.v3081,
            runner.v3098.v3096.v3086.v3084.v3083.v3081.v3079,
            runner.v3098.v3096.v3086.v3084.v3083.v3081.v3079.v3077,
            runner.v3098.v3096.v3086.v3084.v3083.v3081.v3079.v3077.v3074,
            runner.v3098.v3096.v3086.v3084.v3083.v3081.v3079.v3077.v3074.v3071,
            v3033,
        ]
        saved_large = [getattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", None) for module in large_frame_modules]
        try:
            runner.apply_v3100_globals()

            self.assertEqual(runner.v3098.v3096.v3086.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3098.v3096.v3086.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(runner.v3098.v3096.v3086.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            self.assertEqual(v3033.SEQ_TELEMETRY, 1)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3100_adapter_source)
            for module in large_frame_modules:
                self.assertEqual(module.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        finally:
            runner.V3059.v3059_adapter_source = saved_adapter
            runner.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            if saved_seq_telemetry is not None:
                v3033.SEQ_TELEMETRY = saved_seq_telemetry
            if saved_shared is not None:
                v3033.SHARED_FRAME_PATH = saved_shared
            if saved_pace is not None:
                v3033.PACE_SOCKET_PATH = saved_pace
            for module, value in zip(large_frame_modules, saved_large):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value

    def test_report_template_records_v3101_live_gate_and_phase_contract(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3100.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --pace-socket /tmp/a90-doomgeneric-v3100-pace.sock",
            },
            "v3033_marker_strings": [
                runner.INIT_BUILD,
                runner.TICK_TELEMETRY_MARKER,
                runner.PHASE_TELEMETRY_MARKER,
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3100 DOOMGENERIC Phase Telemetry Source Build", report)
        self.assertIn(f"Telemetry path: `{runner.TICK_TELEMETRY_PATH}`", report)
        self.assertIn(f"Phase telemetry marker: `{runner.PHASE_TELEMETRY_MARKER}`", report)
        self.assertIn("loop_tick.*", report)
        self.assertIn("draw_gametic.*", report)
        self.assertIn("dump_gametic.*", report)
        self.assertIn("Run ID: `V3101`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
