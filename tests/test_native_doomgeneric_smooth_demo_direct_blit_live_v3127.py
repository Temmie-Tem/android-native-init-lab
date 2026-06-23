from __future__ import annotations

import argparse
import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_smooth_demo_direct_blit_live_validation_v3127.py")


class NativeDoomgenericSmoothDemoDirectBlitLiveV3127Tests(unittest.TestCase):
    def test_identity_and_candidate_contract(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3127")
        self.assertEqual(runner.CANDIDATE_VERSION, "0.10.117")
        self.assertEqual(runner.CANDIDATE_TAG, "v3126-doomgeneric-smooth-demo-direct-blit")
        self.assertEqual(
            runner.CANDIDATE_SHA256,
            "bda5dffce49ae0e590d2dc629f299e39d54c097ce60d63aa022f146d2fa1f75d",
        )
        self.assertEqual(runner.EXPECTED_SMOOTH_MODE, "non-original-smooth-demo")
        self.assertEqual(runner.EXPECTED_TICK_QUANTUM_US, 28571)
        self.assertIn("boot_linux_v3126_doomgeneric_smooth_demo_direct_blit.img", str(runner.CANDIDATE_IMAGE))

    def test_parse_loop_output_accepts_smooth_demo_clean_path(self) -> None:
        parsed = runner.parse_loop_output(
            "\r\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.loop.foreground_frame_log=0",
                "video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit",
                "video.demo.doom.dashboard.pre_scaled_large_frame=1",
                "video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer",
                "video.demo.doom.dashboard.frame_scale=1:1-pre-scaled",
                "video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy",
                "video.demo.doom.dashboard.full_clear=0",
                "video.demo.doom.dashboard.clear_path=dirty-dashboard-regions",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.rc=0",
                "video.demo.doom.loop.timing.read.avg_us=3",
                "video.demo.doom.loop.timing.draw.avg_us=4300",
                "video.demo.doom.loop.timing.total.avg_us=6300",
                "video.demo.doom.loop.seq.shared_missed_frames=0",
                "video.demo.doom.loop.seq.shared_max_sequence_gap_frames=1",
                "video.demo.doom.loop.flip_events=180",
                "video.demo.doom.loop.flip_delta_avg_us=16670",
                "video.demo.doom.loop.flip_delta_max_us=21000",
                "video.demo.doom.loop.tick_telemetry.summary=1",
                "video.demo.doom.loop.tick_telemetry.open_rc=0",
                f"video.demo.doom.loop.tick_telemetry.marker={runner.EXPECTED_TICK_TELEMETRY_MARKER}",
                f"video.demo.doom.loop.tick_telemetry.paced_time_marker={runner.EXPECTED_PACED_TIME_MARKER}",
                f"video.demo.doom.loop.tick_telemetry.paced_time_model={runner.EXPECTED_PACED_TIME_MODEL}",
                f"video.demo.doom.loop.tick_telemetry.smooth_demo_mode={runner.EXPECTED_SMOOTH_MODE}",
                "video.demo.doom.loop.tick_telemetry.paced_time.quantum_us=28571",
                "video.demo.doom.loop.tick_telemetry.paced_time.advance_calls=180",
                "video.demo.doom.loop.tick_telemetry.paced_time.advance_us_total=5142780",
                "video.demo.doom.loop.tick_telemetry.loop_tick.gametic_changed=179",
                "video.demo.doom.loop.tick_telemetry.loop_tick.gametic_repeated=1",
                "video.demo.doom.loop.tick_telemetry.loop_tick.gametic_max_delta=1",
                "video.demo.doom.loop.tick_telemetry.draw_gametic.changed_transitions=179",
                "video.demo.doom.loop.tick_telemetry.draw_gametic.repeated_transitions=1",
                "video.demo.doom.loop.tick_telemetry.draw_gametic.max_same_run=2",
                "video.demo.doom.loop.tick_telemetry.dump_gametic.changed_transitions=179",
                "video.demo.doom.loop.tick_telemetry.dump_gametic.repeated_transitions=1",
                "video.demo.doom.loop.tick_telemetry.dump_gametic.max_same_run=2",
                "video.demo.doom.loop.tick_telemetry.dump_gametic.max_delta=1",
                "video.demo.doom.loop.tick_telemetry.close_rc=0",
                "video.demo.doom.loop.tick_telemetry.lines=20",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )

        self.assertTrue(parsed["direct_shared_blit_markers_ok"])
        self.assertTrue(parsed["summary_only_markers_ok"])
        self.assertTrue(parsed["telemetry_available"])
        self.assertTrue(parsed["paced_time_markers_ok"])
        self.assertTrue(parsed["paced_time_quantum_ok"])
        self.assertTrue(parsed["gametic_repetition_bounded"])
        self.assertEqual(runner.loop_classification(parsed, 180), "smooth-demo-cadence-clean")
        self.assertTrue(runner.live_pass({
            "preflash_selftest_fail0": True,
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "candidate_hide_before_loop_ok": True,
            "doom_loop_rc": 0,
            "doom_loop_protocol_end_present": True,
            "loop_classification": runner.loop_classification(parsed, 180),
            "candidate_selftest_after_loop_fail0": True,
            "doom_loop": parsed,
        }))

    def test_missing_telemetry_is_not_live_pass(self) -> None:
        parsed = runner.parse_loop_output(
            "\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.loop.foreground_frame_log=0",
                "video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit",
                "video.demo.doom.dashboard.pre_scaled_large_frame=1",
                "video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer",
                "video.demo.doom.dashboard.frame_scale=1:1-pre-scaled",
                "video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy",
                "video.demo.doom.dashboard.full_clear=0",
                "video.demo.doom.dashboard.clear_path=dirty-dashboard-regions",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.rc=0",
                "video.demo.doom.loop.seq.shared_missed_frames=0",
                "video.demo.doom.loop.flip_delta_avg_us=16670",
                "video.demo.doom.loop.flip_delta_max_us=21000",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )
        result = {
            "preflash_selftest_fail0": True,
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "candidate_hide_before_loop_ok": True,
            "doom_loop_rc": 0,
            "doom_loop_protocol_end_present": True,
            "loop_classification": runner.loop_classification(parsed, 180),
            "candidate_selftest_after_loop_fail0": True,
            "doom_loop": parsed,
        }

        self.assertEqual(result["loop_classification"], "paced-time-telemetry-missing")
        self.assertFalse(runner.live_pass(result))

    def test_preflight_and_report_contract(self) -> None:
        args = argparse.Namespace(live=False, frames=180, flash_timeout=900.0, loop_timeout=180.0)
        state = runner.preflight_state(args)
        self.assertTrue(runner.preflight_ok(state))
        self.assertEqual(state["candidate_version"], runner.CANDIDATE_VERSION)
        self.assertEqual(state["expected_smooth_mode"], runner.EXPECTED_SMOOTH_MODE)
        self.assertEqual(state["expected_tick_quantum_us"], runner.EXPECTED_TICK_QUANTUM_US)
        report = runner.render_report({
            "decision": "dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": state,
            "preflight_ok": True,
            "rollback_attempted": False,
        })

        self.assertIn("Native Init V3127 DOOMGENERIC Smooth Demo Direct Blit Live Validation", report)
        self.assertIn("boot_linux_v3126_doomgeneric_smooth_demo_direct_blit.img", report)
        self.assertIn(runner.CANDIDATE_SHA256, report)
        self.assertIn("Smooth Telemetry", report)
        payload = runner.dry_run_payload(args, state)
        commands = " ".join(payload["commands"])
        self.assertIn("flash exact V3126 image", commands)
        self.assertIn("bounded tick telemetry", commands)
        self.assertIn("rollback v2321", commands)


if __name__ == "__main__":
    unittest.main()
