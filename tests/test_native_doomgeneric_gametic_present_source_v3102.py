from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/build_native_init_boot_v3102_doomgeneric_gametic_present.py")
REPO_ROOT = Path(__file__).resolve().parents[1]


class NativeDoomgenericGameticPresentSourceV3102Tests(unittest.TestCase):
    def test_builder_contract_pins_v3102_candidate(self) -> None:
        self.assertEqual(runner.CYCLE, "V3102")
        self.assertEqual(runner.INIT_VERSION, "0.10.107")
        self.assertEqual(runner.INIT_BUILD, "v3102-doomgeneric-gametic-present")
        self.assertEqual(runner.ENGINE_RAMDISK_PATH, "bin/a90_doomgeneric_private_engine_v3102")
        self.assertEqual(runner.ENGINE_NAME, "doomgeneric-private-link-v3102-gametic-present")
        self.assertEqual(runner.FRAME_PATH, "/tmp/a90-doomgeneric-v3102-raw-fallback-frame.xbgr8888")
        self.assertEqual(runner.SHARED_FRAME_PATH, "/tmp/a90-doomgeneric-v3102-shared-frame.bin")
        self.assertEqual(runner.INPUT_STATE_PATH, "/tmp/a90-doomgeneric-v3102-input.state")
        self.assertEqual(runner.INPUT_SOCKET_PATH, "/tmp/a90-doomgeneric-v3102-input.sock")
        self.assertEqual(runner.PACE_SOCKET_PATH, "/tmp/a90-doomgeneric-v3102-pace.sock")
        self.assertEqual(runner.TICK_TELEMETRY_PATH, "/tmp/a90-doomgeneric-v3102-tick-telemetry.txt")
        self.assertEqual(runner.GAMETIC_PRESENT_ONLY, 1)
        self.assertEqual(runner.TICK_PACE_INTERVAL_US, 14286)
        self.assertIn(runner.GAMETIC_PRESENT_MARKER.encode("ascii"), runner.REQUIRED_STRINGS)
        self.assertIn(b"dump_gametic.emitted_changed_only=%u", runner.REQUIRED_STRINGS)
        self.assertIn(b"dump_gametic.skipped_same_gametic=%u", runner.REQUIRED_STRINGS)
        self.assertIn(b"video.demo.doom.loop.pace_socket.idle_tokens_sent=%u", runner.REQUIRED_STRINGS)

    def test_v3102_adapter_emits_only_changed_gametic_frames(self) -> None:
        source = runner.v3102_adapter_source()

        self.assertIn(runner.GAMETIC_PRESENT_MARKER, source)
        self.assertIn("a90_doomgeneric_v3102_gametic_present_policy", source)
        self.assertIn("dump_emit_previous_gametic", source)
        self.assertIn("dump_gametic_emitted_changed_only", source)
        self.assertIn("dump_gametic_skipped_same_gametic", source)
        self.assertIn("gametic == dump_emit_previous_gametic", source)
        self.assertIn("emit_frame = 0;", source)
        self.assertIn('"gametic_present_only=changed-gametic-only\\n"', source)
        self.assertIn('"dump_gametic.emitted_changed_only=%u\\n"', source)
        self.assertIn('"dump_gametic.skipped_same_gametic=%u\\n"', source)
        self.assertIn("a90_doomgeneric_record_loop_tick_phase(", source)
        self.assertIn("a90_doomgeneric_write_shared_frame(&shared_frame)", source)
        self.assertEqual(source.count('"dump_gametic.samples=%u\\n"'), 1)
        self.assertNotIn("/tmp/a90-doomgeneric-v3100", source)

    def test_native_presenter_has_gametic_present_only_pace_policy(self) -> None:
        source = (REPO_ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c").read_text(
            encoding="utf-8"
        )

        self.assertIn("#define VIDEO_DEMO_DOOMGENERIC_GAMETIC_PRESENT_ONLY 0", source)
        self.assertIn("#define VIDEO_DEMO_DOOMGENERIC_TICK_PACE_INTERVAL_US 16667U", source)
        self.assertIn("video.demo.doom.presenter.gametic_present_only=%d", source)
        self.assertIn("video.demo.doom.loop.presenter.gametic_present_only=%d", source)
        self.assertIn("video.demo.doom.loop.pace_socket.idle_tokens_sent=%u", source)
        self.assertIn("tick_pace_interval_ns", source)
        self.assertIn("next_pace_token_ns", source)
        self.assertIn("!VIDEO_DEMO_DOOMGENERIC_GAMETIC_PRESENT_ONLY", source)
        self.assertIn("++idle_pace_tokens;", source)

    def test_v3102_apply_globals_enables_presenter_flags(self) -> None:
        v3033 = runner.v3033_module()
        saved_adapter = runner.V3059.v3059_adapter_source
        saved_v3081_adapter = runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source
        saved_gametic = getattr(v3033, "GAMETIC_PRESENT_ONLY", None)
        saved_interval = getattr(v3033, "TICK_PACE_INTERVAL_US", None)
        saved_shared = getattr(v3033, "SHARED_FRAME_PATH", None)
        saved_pace = getattr(v3033, "PACE_SOCKET_PATH", None)
        large_frame_modules = [
            runner.v3100.v3098.v3096.v3086,
            runner.v3100.v3098.v3096.v3086.v3084,
            runner.v3100.v3098.v3096.v3086.v3084.v3083,
            runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081,
            runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3079,
            runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3079.v3077,
            runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3079.v3077.v3074,
            runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3079.v3077.v3074.v3071,
            v3033,
        ]
        saved_large = [getattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", None) for module in large_frame_modules]
        try:
            runner.apply_v3102_globals()

            self.assertEqual(runner.v3100.v3098.v3096.v3086.CYCLE, runner.CYCLE)
            self.assertEqual(runner.v3100.v3098.v3096.v3086.INIT_VERSION, runner.INIT_VERSION)
            self.assertEqual(v3033.SHARED_FRAME_PATH, runner.SHARED_FRAME_PATH)
            self.assertEqual(v3033.PACE_SOCKET_PATH, runner.PACE_SOCKET_PATH)
            self.assertEqual(v3033.GAMETIC_PRESENT_ONLY, 1)
            self.assertEqual(v3033.TICK_PACE_INTERVAL_US, runner.TICK_PACE_INTERVAL_US)
            self.assertIs(runner.V3059.v3059_adapter_source, runner.v3102_adapter_source)
        finally:
            runner.V3059.v3059_adapter_source = saved_adapter
            runner.v3100.v3098.v3096.v3086.v3084.v3083.v3081.v3081_adapter_source = saved_v3081_adapter
            if saved_gametic is not None:
                v3033.GAMETIC_PRESENT_ONLY = saved_gametic
            if saved_interval is not None:
                v3033.TICK_PACE_INTERVAL_US = saved_interval
            if saved_shared is not None:
                v3033.SHARED_FRAME_PATH = saved_shared
            if saved_pace is not None:
                v3033.PACE_SOCKET_PATH = saved_pace
            for module, value in zip(large_frame_modules, saved_large):
                if value is not None:
                    module.NATIVE_DASHBOARD_LARGE_FRAME = value

    def test_report_template_records_v3103_live_gate(self) -> None:
        manifest = {
            "decision": runner.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3102.img",
            "boot_sha256": "boot-sha",
            "init_version": runner.INIT_VERSION,
            "init_build": runner.INIT_BUILD,
            "doomgeneric_visible_loop": {
                "runtime_wad_path": runner.RUNTIME_WAD_PATH,
                "expected_wad_sha256": runner.EXPECTED_WAD_SHA256,
                "helper_loop_command": "helper --gametic-present",
            },
            "v3033_marker_strings": [
                runner.INIT_BUILD,
                runner.GAMETIC_PRESENT_MARKER,
                runner.TICK_TELEMETRY_MARKER,
            ],
        }

        report = runner.render_report(manifest, ("helper-flag",), ("init-flag",))

        self.assertIn("Native Init V3102 DOOMGENERIC Gametic Present Source Build", report)
        self.assertIn(f"Gametic-present marker: `{runner.GAMETIC_PRESENT_MARKER}`", report)
        self.assertIn("dump_gametic.skipped_same_gametic", report)
        self.assertIn("pace_socket.idle_tokens_sent", report)
        self.assertIn("Run ID: `V3103`", report)
        self.assertIn("native_init_flash.py", report)


if __name__ == "__main__":
    unittest.main()
