from __future__ import annotations

import argparse
import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_summary_only_direct_blit_live_validation_v3124.py")


class NativeDoomgenericSummaryOnlyDirectBlitLiveV3124Tests(unittest.TestCase):
    def test_identity_and_candidate_contract(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3124")
        self.assertEqual(runner.CANDIDATE_VERSION, "0.10.116")
        self.assertEqual(runner.CANDIDATE_TAG, "v3123-doomgeneric-summary-only-direct-blit")
        self.assertEqual(
            runner.CANDIDATE_SHA256,
            "248af9a65bb9d4c30cd1c0cd11db642c1cbcb332697b0387372bd7465175b808",
        )
        self.assertEqual(runner.EXPECTED_READER, "shared-mmap-direct-blit")
        self.assertEqual(runner.EXPECTED_FOREGROUND_FRAME_LOG, 0)
        self.assertIn("boot_linux_v3123_doomgeneric_summary_only_direct_blit.img", str(runner.CANDIDATE_IMAGE))

    def test_parse_loop_output_accepts_summary_only_direct_clean_path(self) -> None:
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
                "video.demo.doom.loop.timing.alloc.avg_us=0",
                "video.demo.doom.loop.timing.read.avg_us=90",
                "video.demo.doom.loop.timing.draw.avg_us=4500",
                "video.demo.doom.loop.timing.draw.max_us=5500",
                "video.demo.doom.loop.timing.total.avg_us=6100",
                "video.demo.doom.loop.timing.total.max_us=17000",
                "video.demo.doom.loop.seq.shared_missed_frames=0",
                "video.demo.doom.loop.seq.shared_max_sequence_gap_frames=1",
                "video.demo.doom.loop.flip_events=180",
                "video.demo.doom.loop.flip_delta_avg_us=16670",
                "video.demo.doom.loop.flip_delta_max_us=21000",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )

        self.assertTrue(parsed["producer_markers_ok"])
        self.assertTrue(parsed["no_full_clear_markers_ok"])
        self.assertTrue(parsed["direct_shared_blit_markers_ok"])
        self.assertTrue(parsed["summary_only_markers_ok"])
        self.assertTrue(parsed["read_improved_vs_v3119"])
        self.assertEqual(runner.loop_classification(parsed, 180), "prescaled-producer-clean")

    def test_missing_summary_only_marker_is_not_live_pass(self) -> None:
        parsed = runner.parse_loop_output(
            "\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
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

        self.assertEqual(result["loop_classification"], "summary-only-marker-missing")
        self.assertFalse(runner.live_pass(result))

    def test_preflight_and_report_contract(self) -> None:
        args = argparse.Namespace(live=False, frames=180, flash_timeout=900.0, loop_timeout=180.0)
        state = runner.preflight_state(args)
        self.assertTrue(runner.preflight_ok(state))
        self.assertEqual(state["candidate_version"], runner.CANDIDATE_VERSION)
        self.assertEqual(state["candidate_tag"], runner.CANDIDATE_TAG)
        self.assertEqual(state["expected_summary_marker"], "video.demo.doom.loop.foreground_frame_log=0")
        report = runner.render_report({
            "decision": "dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": state,
            "preflight_ok": True,
            "rollback_attempted": False,
        })

        self.assertIn("Native Init V3124 DOOMGENERIC Summary-Only Direct Blit Live Validation", report)
        self.assertIn("boot_linux_v3123_doomgeneric_summary_only_direct_blit.img", report)
        self.assertIn(runner.CANDIDATE_SHA256, report)
        self.assertIn("Summary-only marker", report)
        self.assertIn("Read avg vs V3119", report)
        payload = runner.dry_run_payload(args, state)
        commands = " ".join(payload["commands"])
        self.assertIn("flash exact V3123 image", commands)
        self.assertIn("summary-only marker", commands)
        self.assertIn("rollback v2321", commands)


if __name__ == "__main__":
    unittest.main()
