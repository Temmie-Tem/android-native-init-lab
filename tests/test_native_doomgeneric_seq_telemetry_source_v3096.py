from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3096_doomgeneric_seq_telemetry.py")
REPO_ROOT = Path(__file__).resolve().parents[1]


class NativeDoomgenericSeqTelemetrySourceV3096Tests(unittest.TestCase):
    def test_builder_contract_pins_v3096_seq_telemetry_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3096")
        self.assertEqual(runner.INIT_VERSION, "0.10.104")
        self.assertEqual(runner.INIT_BUILD, "v3096-doomgeneric-seq-telemetry")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3096")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3096-seq-telemetry")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3096-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3096-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3096-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3096-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3096-pace.sock")
        self.assertEqual(runner.TICK_TELEMETRY_PATH, "/tmp/a90-doomgeneric-v3096-tick-telemetry.txt")
        self.assertEqual(runner.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS, 0)
        self.assertEqual(runner.BASELINE_NATIVE_DASHBOARD_LARGE_FRAME, 1)
        self.assertEqual(runner.NATIVE_DASHBOARD_LARGE_FRAME, 0)
        self.assertEqual(runner.BASELINE_FRAME_SCALE, "3:2-minimal-fastscale")
        self.assertEqual(runner.FRAME_SCALE, "1:1")
        self.assertEqual(runner.SEQ_TELEMETRY, 1)
        self.assertIn(runner.TICK_TELEMETRY_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.SCALE_1TO1_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.SEQ_TELEMETRY_CONTRACT.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.SEQ_TELEMETRY_MODEL.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(runner.TICK_TELEMETRY_PATH.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.large_frame=0", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.dashboard.frame_scale=1:1", runner.REQUIRED_STRINGS)
        self.assertIn(b"%s.seq.new_frame_polls=%u", runner.REQUIRED_STRINGS)
        self.assertIn(b"%s.seq.shared_missed_frames=%u", runner.REQUIRED_STRINGS)
        self.assertIn(b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq", runner.REQUIRED_STRINGS)
        self.assertIn(b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback", runner.REQUIRED_STRINGS)

    def test_native_source_has_gated_seq_telemetry_contract(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(
            encoding="utf-8",
        )

        self.assertIn("#ifndef VIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY", source)
        self.assertIn("struct video_demo_doom_seq_stats", source)
        self.assertIn("video_demo_doom_seq_stats_record_read", source)
        self.assertIn("video_demo_doom_seq_stats_record_present", source)
        self.assertIn("video_demo_doom_seq_stats_print", source)
        self.assertIn('"video.demo.doom.presenter.seq_telemetry=1', source)
        self.assertIn('"video.demo.doom.loop.seq_telemetry=1', source)
        self.assertIn('"%s.seq.new_frame_polls=%u', source)
        self.assertIn('"%s.seq.duplicate_frame_polls=%u', source)
        self.assertIn('"%s.seq.polls_without_new_frame=%u', source)
        self.assertIn('"%s.seq.shared_missed_frames=%u', source)
        self.assertIn("frame-id-upper32-shared-seq", source)

    def test_v3096_adapter_records_tick_telemetry_and_scale_marker(self) -> None:
        v3033 = runner.v3033_module()
        saved_adapter = runner.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3086.v3084.v3083.v3081.v3081_adapter_source
        saved_seq_telemetry = getattr(v3033, "SEQ_TELEMETRY", None)
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
            runner.apply_v3096_globals()

            source = runner.v3096_adapter_source()
        finally:
            runner.V3059.v3059_adapter_source = saved_adapter
            runner.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            if saved_seq_telemetry is not None:
                v3033.SEQ_TELEMETRY = saved_seq_telemetry
            for module, value in zip(large_frame_modules, saved_large):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value

        self.assertIn("extern int I_GetTime(void);", source)
        self.assertIn("extern int gametic;", source)
        self.assertIn("a90_doomgeneric_v3096_tick_telemetry_policy", source)
        self.assertIn("a90_doomgeneric_v3096_scale_policy", source)
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

    def test_v3096_mutates_build_surface_custom_adapter_and_large_frame_flag(self) -> None:
        v3033 = runner.v3033_module()
        saved_paths = {
            "shared": getattr(v3033, "SHARED_FRAME_PATH", None),
            "pace": getattr(v3033, "PACE_SOCKET_PATH", None),
        }
        saved_adapter = runner.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3086.v3084.v3083.v3081.v3081_adapter_source
        saved_seq_telemetry = getattr(v3033, "SEQ_TELEMETRY", None)
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
            runner.apply_v3096_globals()

            self.assertEqual(runner.v3086.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3086.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(runner.v3086.INIT_BUILD, runner.INIT_BUILD)
            self.assertEqual(runner.v3086.v3084.CYCLE, runner.CYCLE)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            for module in large_frame_modules:
                self.assertEqual(module.NATIVE_DASHBOARD_LARGE_FRAME, 0)
            self.assertEqual(v3033.SEQ_TELEMETRY, 1)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3096_adapter_source)
        finally:
            runner.V3059.v3059_adapter_source = saved_adapter
            runner.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            if saved_seq_telemetry is not None:
                v3033.SEQ_TELEMETRY = saved_seq_telemetry
            for module, value in zip(large_frame_modules, saved_large):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value
            if saved_paths["shared"] is not None:
                v3033.SHARED_FRAME_PATH = saved_paths["shared"]
            if saved_paths["pace"] is not None:
                v3033.PACE_SOCKET_PATH = saved_paths["pace"]

    def test_report_template_records_v3097_live_gate_and_seq_contract(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3096.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --pace-socket /tmp/a90-doomgeneric-v3096-pace.sock",
            },
            "v3033_marker_strings": [
                "v3096-doomgeneric-seq-telemetry",
                runner.TICK_TELEMETRY_MARKER,
                runner.SCALE_1TO1_MARKER,
                runner.SEQ_TELEMETRY_CONTRACT,
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3096 DOOMGENERIC Sequence Telemetry Source Build", report)
        self.assertIn(f"Telemetry path: `{runner.TICK_TELEMETRY_PATH}`", report)
        self.assertIn(f"Scale marker: `{runner.SCALE_1TO1_MARKER}`", report)
        self.assertIn(f"Sequence telemetry contract: `{runner.SEQ_TELEMETRY_CONTRACT}`", report)
        self.assertIn(f"Sequence telemetry model: `{runner.SEQ_TELEMETRY_MODEL}`", report)
        self.assertIn("Candidate large dashboard frame: `0`", report)
        self.assertIn("Candidate frame scale: `1:1`", report)
        self.assertIn("Candidate sequence telemetry: `1`", report)
        self.assertIn("fake_ticks_ms", report)
        self.assertIn("Run ID: `V3097`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
