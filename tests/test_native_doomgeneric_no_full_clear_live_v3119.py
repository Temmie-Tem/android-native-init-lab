from __future__ import annotations

import argparse
import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_no_full_clear_live_validation_v3119.py")


class NativeDoomgenericNoFullClearLiveV3119Tests(unittest.TestCase):
    def test_identity_and_candidate_contract(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3119")
        self.assertEqual(runner.CANDIDATE_VERSION, "0.10.114")
        self.assertEqual(runner.CANDIDATE_TAG, "v3118-doomgeneric-no-full-clear")
        self.assertEqual(
            runner.CANDIDATE_SHA256,
            "579cb45707e1e7fd366fdfebf52d5d34befffc355e6e34d9cc167b03493a97a8",
        )
        self.assertIn("boot_linux_v3118_doomgeneric_no_full_clear.img", str(runner.CANDIDATE_IMAGE))

    def test_parse_loop_output_requires_no_full_clear_markers(self) -> None:
        parsed = runner.parse_loop_output(
            "\r\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.dashboard.pre_scaled_large_frame=1",
                "video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer",
                "video.demo.doom.dashboard.frame_scale=1:1-pre-scaled",
                "video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy",
                "video.demo.doom.dashboard.full_clear=0",
                "video.demo.doom.dashboard.clear_path=dirty-dashboard-regions",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.rc=0",
                "video.demo.doom.loop.timing.begin.avg_us=900",
                "video.demo.doom.loop.timing.draw.avg_us=1000",
                "video.demo.doom.loop.timing.draw.max_us=1600",
                "video.demo.doom.loop.timing.total.avg_us=15800",
                "video.demo.doom.loop.timing.total.max_us=18000",
                "video.demo.doom.loop.seq.shared_missed_frames=0",
                "video.demo.doom.loop.seq.shared_max_sequence_gap_frames=0",
                "video.demo.doom.loop.flip_events=180",
                "video.demo.doom.loop.flip_delta_avg_us=16670",
                "video.demo.doom.loop.flip_delta_max_us=21000",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )

        self.assertTrue(parsed["producer_markers_ok"])
        self.assertEqual(parsed["full_clear"], 0)
        self.assertEqual(parsed["clear_path"], runner.EXPECTED_CLEAR_PATH)
        self.assertTrue(parsed["no_full_clear_markers_ok"])
        self.assertTrue(parsed["begin_improved_vs_v3117"])
        self.assertEqual(runner.loop_classification(parsed, 180), "prescaled-producer-clean")

    def test_parse_loop_output_classifies_two_vblank_with_begin_improvement(self) -> None:
        parsed = runner.parse_loop_output(
            "\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.dashboard.pre_scaled_large_frame=1",
                "video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer",
                "video.demo.doom.dashboard.frame_scale=1:1-pre-scaled",
                "video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy",
                "video.demo.doom.dashboard.full_clear=0",
                "video.demo.doom.dashboard.clear_path=dirty-dashboard-regions",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.rc=0",
                "video.demo.doom.loop.timing.begin.avg_us=1100",
                "video.demo.doom.loop.seq.shared_missed_frames=0",
                "video.demo.doom.loop.flip_delta_avg_us=32802",
                "video.demo.doom.loop.flip_delta_max_us=33342",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )

        self.assertTrue(parsed["no_full_clear_markers_ok"])
        self.assertTrue(parsed["begin_improved_vs_v3117"])
        self.assertTrue(parsed["pageflip_30hz_stable"])
        self.assertEqual(runner.loop_classification(parsed, 180), "prescaled-producer-two-vblank")

    def test_missing_no_full_clear_marker_is_not_live_pass(self) -> None:
        parsed = runner.parse_loop_output(
            "\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.dashboard.pre_scaled_large_frame=1",
                "video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer",
                "video.demo.doom.dashboard.frame_scale=1:1-pre-scaled",
                "video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy",
                "video.demo.doom.dashboard.full_clear=1",
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

        self.assertEqual(result["loop_classification"], "no-full-clear-marker-missing")
        self.assertFalse(runner.live_pass(result))

    def test_preflight_and_report_contract(self) -> None:
        args = argparse.Namespace(live=False, frames=180, flash_timeout=900.0, loop_timeout=180.0)
        state = runner.preflight_state(args)
        self.assertTrue(runner.preflight_ok(state))
        self.assertEqual(state["candidate_version"], runner.CANDIDATE_VERSION)
        self.assertEqual(state["candidate_tag"], runner.CANDIDATE_TAG)
        report = runner.render_report({
            "decision": "dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": state,
            "preflight_ok": True,
            "rollback_attempted": False,
        })

        self.assertIn("Native Init V3119 DOOMGENERIC No-Full-Clear Live Validation", report)
        self.assertIn("boot_linux_v3118_doomgeneric_no_full_clear.img", report)
        self.assertIn(runner.CANDIDATE_SHA256, report)
        self.assertIn("No-full-clear markers", report)
        self.assertIn("Timing begin improved vs V3117", report)
        payload = runner.dry_run_payload(args, state)
        commands = " ".join(payload["commands"])
        self.assertIn("flash exact V3118 image", commands)
        self.assertIn("no-full-clear markers", commands)
        self.assertIn("rollback v2321", commands)


if __name__ == "__main__":
    unittest.main()
