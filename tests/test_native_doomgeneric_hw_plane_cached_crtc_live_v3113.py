from __future__ import annotations

import argparse
import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_hw_plane_cached_crtc_live_validation_v3113.py")


class NativeDoomgenericHwPlaneCachedCrtcLiveV3113Tests(unittest.TestCase):
    def test_identity_and_flash_contract(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3113")
        self.assertEqual(runner.CANDIDATE_VERSION, "0.10.111")
        self.assertEqual(runner.CANDIDATE_TAG, "v3112-doomgeneric-hw-plane-cached-crtc")
        self.assertEqual(
            runner.CANDIDATE_SHA256,
            "e58d08d57de91831738b3fc48911e2c6da02e50059c77935203b03409df6e5b0",
        )
        command = runner.flash_command(
            runner.CANDIDATE_IMAGE,
            runner.CANDIDATE_VERSION,
            runner.CANDIDATE_SHA256,
            from_native=True,
        )
        joined = " ".join(command)
        self.assertIn("native_init_flash.py", joined)
        self.assertIn("boot_linux_v3112_doomgeneric_hw_plane_cached_crtc.img", joined)
        self.assertIn("--expect-version", command)
        self.assertIn(runner.CANDIDATE_VERSION, command)
        self.assertIn("--expect-sha256", command)
        self.assertIn(runner.CANDIDATE_SHA256, command)
        self.assertIn("--expect-readback-sha256", command)
        self.assertIn("--verify-protocol", command)
        self.assertIn("--from-native", command)

    def test_parse_loop_output_classifies_hw_plane_path(self) -> None:
        parsed = runner.parse_loop_output(
            "\r\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.dashboard.hw_plane_scale=1",
                "video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
                "video.demo.doom.dashboard.hw_plane.attempted=1",
                "video.demo.doom.dashboard.hw_plane.presented=1",
                "video.demo.doom.dashboard.hw_plane.id=84",
                "video.demo.doom.dashboard.hw_plane.fb_id=44",
                "video.demo.doom.dashboard.hw_plane.stage=presented",
                "video.demo.doom.dashboard.hw_plane.stage_id=12",
                "video.demo.doom.dashboard.hw_plane.crtc_index=0",
                "video.demo.doom.dashboard.hw_plane.cached_crtc_index=1",
                "video.demo.doom.dashboard.hw_plane.plane_count=16",
                "video.demo.doom.dashboard.hw_plane.compatible_count=16",
                "video.demo.doom.dashboard.hw_plane.idle_xbgr_count=1",
                "video.demo.doom.dashboard.hw_plane.universal_cap_rc=0",
                "video.demo.doom.dashboard.hw_plane.atomic_cap_rc=0",
                "video.demo.doom.dashboard.hw_plane.fetch_resources_rc=0",
                "video.demo.doom.dashboard.hw_plane.rc=0",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.display.rc=0",
                "video.demo.doom.loop.rc=0",
                "video.demo.doom.loop.timing.draw.avg_us=1200",
                "video.demo.doom.loop.timing.draw.max_us=2500",
                "video.demo.doom.loop.timing.total.avg_us=16600",
                "video.demo.doom.loop.timing.total.max_us=18000",
                "video.demo.doom.loop.seq.shared_missed_frames=0",
                "video.demo.doom.loop.seq.shared_max_sequence_gap_frames=1",
                "video.demo.doom.loop.flip_delta_avg_us=16620",
                "video.demo.doom.loop.flip_delta_max_us=16660",
                "video.demo.doom.loop.timing_probe=1",
                "video.demo.doom.loop.seq_telemetry=1",
                "video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )
        self.assertTrue(parsed["hw_plane_presented"])
        self.assertTrue(parsed["protocol_end_present"])
        self.assertEqual(parsed["hw_plane_presented_count"], 1)
        self.assertEqual(parsed["hw_plane_stage"], "presented")
        self.assertEqual(parsed["hw_plane_stage_id"], 12)
        self.assertEqual(parsed["hw_plane_setplane_count"], 0)
        self.assertEqual(parsed["hw_plane_presented_stage_count"], 1)
        self.assertEqual(parsed["hw_plane_crtc_index"], 0)
        self.assertEqual(parsed["hw_plane_cached_crtc_index"], 1)
        self.assertEqual(parsed["hw_plane_cached_crtc_index_count"], 1)
        self.assertTrue(parsed["hw_plane_cached_crtc_index_any"])
        self.assertTrue(parsed["hw_plane_cached_or_reuse_evidence"])
        self.assertEqual(parsed["hw_plane_plane_count"], 16)
        self.assertEqual(parsed["hw_plane_compatible_count"], 16)
        self.assertEqual(parsed["hw_plane_idle_xbgr_count"], 1)
        self.assertEqual(parsed["hw_plane_universal_cap_rc"], 0)
        self.assertEqual(parsed["hw_plane_atomic_cap_rc"], 0)
        self.assertEqual(parsed["hw_plane_fetch_resources_rc"], 0)
        self.assertFalse(parsed["hw_plane_fallback"])
        self.assertTrue(parsed["pageflip_stable"])
        self.assertTrue(parsed["shared_seq_clean"])
        self.assertTrue(runner.all_markers_present(parsed["markers"]))
        self.assertEqual(runner.loop_classification(parsed, 180), "hw-plane-presented")

    def test_parse_loop_output_classifies_cpu_fallback_path(self) -> None:
        parsed = runner.parse_loop_output(
            "\r\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.dashboard.hw_plane_scale=1",
                "video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
                "video.demo.doom.dashboard.hw_plane.attempted=0",
                "video.demo.doom.dashboard.hw_plane.presented=0",
                "video.demo.doom.dashboard.hw_plane.rc=-19",
                "video.demo.doom.dashboard.hw_plane.stage=scan-planes",
                "video.demo.doom.dashboard.hw_plane.stage_id=6",
                "video.demo.doom.dashboard.hw_plane.crtc_index=0",
                "video.demo.doom.dashboard.hw_plane.cached_crtc_index=1",
                "video.demo.doom.dashboard.hw_plane.plane_count=16",
                "video.demo.doom.dashboard.hw_plane.compatible_count=16",
                "video.demo.doom.dashboard.hw_plane.idle_xbgr_count=0",
                "video.demo.doom.dashboard.hw_plane.universal_cap_rc=0",
                "video.demo.doom.dashboard.hw_plane.atomic_cap_rc=0",
                "video.demo.doom.dashboard.hw_plane.fetch_resources_rc=0",
                "video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.rc=0",
                "video.demo.doom.loop.flip_delta_avg_us=29311",
                "video.demo.doom.loop.flip_delta_max_us=33264",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )
        self.assertFalse(parsed["hw_plane_presented"])
        self.assertTrue(parsed["hw_plane_fallback"])
        self.assertEqual(parsed["hw_plane_stage"], "scan-planes")
        self.assertEqual(parsed["hw_plane_setplane_count"], 0)
        self.assertEqual(parsed["hw_plane_scan_planes_count"], 1)
        self.assertEqual(parsed["hw_plane_last_rc"], -19)
        self.assertEqual(parsed["hw_plane_cached_crtc_index"], 1)
        self.assertEqual(parsed["hw_plane_cached_crtc_index_count"], 1)
        self.assertTrue(parsed["hw_plane_cached_or_reuse_evidence"])
        self.assertEqual(parsed["hw_plane_fetch_resources_rc"], 0)
        self.assertEqual(parsed["hw_plane_idle_xbgr_count"], 0)
        self.assertEqual(parsed["hw_plane_fallback_value"], "fast-3to2-rowcopy")
        self.assertEqual(runner.loop_classification(parsed, 180), "cpu-fallback-observed")

    def test_live_pass_accepts_presented_or_recorded_fallback(self) -> None:
        base = {
            "preflash_selftest_fail0": True,
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "candidate_hide_before_loop_ok": True,
            "doom_loop_rc": 0,
            "doom_loop_protocol_end_present": True,
            "candidate_selftest_after_loop_fail0": True,
        }
        presented = dict(base, doom_loop={"frames_presented": 180, "hw_plane_cached_or_reuse_evidence": True}, loop_classification="hw-plane-presented")
        fallback = dict(base, doom_loop={"frames_presented": 180, "hw_plane_cached_or_reuse_evidence": True}, loop_classification="cpu-fallback-observed")
        uncached = dict(base, doom_loop={"frames_presented": 180, "hw_plane_cached_or_reuse_evidence": False}, loop_classification="cpu-fallback-observed")
        unclear = dict(base, doom_loop={"frames_presented": 180, "hw_plane_cached_or_reuse_evidence": True}, loop_classification="hw-plane-not-classified")
        self.assertTrue(runner.live_pass(presented))
        self.assertTrue(runner.live_pass(fallback))
        self.assertFalse(runner.live_pass(uncached))
        self.assertFalse(runner.live_pass(unclear))
        presented["preflash_selftest_fail0"] = False
        self.assertFalse(runner.live_pass(presented))

    def test_escaped_protocol_error_still_parses_loop_but_not_transport_pass(self) -> None:
        escaped = (
            "RuntimeError('A90P1 END marker not found\\n"
            "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop\\r\\n"
            "video.demo.doom.loop.verify.ok=1\\r\\n"
            "video.demo.doom.dashboard.hw_plane_scale=1\\r\\n"
            "video.demo.doom.dashboard.scale_path=drm-plane-srcdst\\r\\n"
            "video.demo.doom.dashboard.hw_plane.attempted=0\\r\\n"
            "video.demo.doom.dashboard.hw_plane.presented=0\\r\\n"
            "video.demo.doom.dashboard.hw_plane.rc=-19\\r\\n"
            "video.demo.doom.dashboard.hw_plane.stage=scan-planes\\r\\n"
            "video.demo.doom.dashboard.hw_plane.stage_id=6\\r\\n"
            "video.demo.doom.dashboard.hw_plane.cached_crtc_index=1\\r\\n"
            "video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy\\r\\n"
            "video.demo.doom.loop.frames_presented=180\\r\\n"
            "video.demo.doom.loop.rc=0\\r\\n"
            "video.demo.doom.loop.seq.shared_missed_frames=0\\r\\n"
            "video.demo.doom.loop.seq.shared_max_sequence_gap_frames=1\\r\\n"
            "video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us\\r\\n"
            "')"
        )
        parsed = runner.parse_loop_output(escaped)
        self.assertEqual(parsed["loop_rc"], 0)
        self.assertEqual(parsed["frames_presented"], 180)
        self.assertTrue(parsed["hw_plane_fallback"])
        self.assertFalse(parsed["protocol_end_present"])
        self.assertEqual(runner.loop_classification(parsed, 180), "cpu-fallback-observed")
        self.assertFalse(runner.live_pass({
            "preflash_selftest_fail0": True,
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "candidate_hide_before_loop_ok": True,
            "doom_loop_rc": 0,
            "doom_loop_protocol_end_present": False,
            "loop_classification": "cpu-fallback-observed",
            "doom_loop": {"hw_plane_cached_or_reuse_evidence": True},
            "candidate_selftest_after_loop_fail0": True,
        }))

    def test_loop_summary_missing_with_protocol_end_is_separate_classification(self) -> None:
        parsed = runner.parse_loop_output(
            "\r\n".join([
                "video.demo.doom.loop.timing_probe=1",
                "video.demo.doom.dashboard.hw_plane_scale=1",
                "video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
                "video.demo.doom.dashboard.present_seq=163",
                "video.demo.doom.frame.display.presented=1",
                "video.demo.doom.dashboard.hw_plane.attempted=1",
                "video.demo.doom.dashboard.hw_plane.presented=0",
                "video.demo.doom.dashboard.hw_plane.id=84",
                "video.demo.doom.dashboard.hw_plane.fb_id=206",
                "video.demo.doom.dashboard.hw_plane.stage=setplane",
                "video.demo.doom.dashboard.hw_plane.stage_id=11",
                "video.demo.doom.dashboard.hw_plane.crtc_index=0",
                "video.demo.doom.dashboard.hw_plane.cached_crtc_index=0",
                "video.demo.doom.dashboard.hw_plane.fetch_resources_rc=0",
                "video.demo.doom.dashboard.hw_plane.rc=-22",
                "video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy",
                "video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=3188 flags=0x1 status=ok",
            ])
        )
        self.assertTrue(parsed["protocol_end_present"])
        self.assertFalse(parsed["loop_summary_present"])
        self.assertTrue(parsed["loop_summary_missing_with_protocol_end"])
        self.assertEqual(parsed["display_presented_count"], 1)
        self.assertEqual(parsed["dashboard_present_seq_max"], 163)
        self.assertEqual(parsed["hw_plane_setplane_count"], 1)
        self.assertEqual(parsed["hw_plane_einval_count"], 1)
        self.assertTrue(parsed["hw_plane_cached_or_reuse_evidence"])
        self.assertEqual(runner.loop_classification(parsed, 180), "loop-summary-missing")

    def test_preflight_and_report_contract(self) -> None:
        args = argparse.Namespace(live=False, frames=180, flash_timeout=900.0, loop_timeout=180.0)
        state = runner.preflight_state(args)
        self.assertTrue(runner.preflight_ok(state))
        self.assertIn("native_init_flash.py", state["recovery_gate"])
        self.assertIn("runtime-private WAD", state["operator_prerequisite"])
        self.assertIn("hide auto menu", " ".join(state["hard_boundary"]))
        report = runner.render_report({
            "decision": "dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": state,
            "preflight_ok": True,
            "rollback_attempted": False,
        })
        self.assertIn("Native Init V3113 DOOMGENERIC Hardware Plane Cached CRTC Live Validation", report)
        self.assertIn("hw-plane-presented", report)
        self.assertIn("Pre-flash current version", report)
        self.assertIn("Candidate hide-before-loop ok", report)
        self.assertIn("HW plane stage/id", report)
        self.assertIn("Loop summary present/missing-with-END", report)
        self.assertIn("HW plane stage counts", report)
        self.assertIn("reuse-evidence", report)
        self.assertIn("cached_crtc_index=1", report)
        self.assertIn("fetch-resources", report)
        self.assertIn("scan-planes", report)
        self.assertIn("loop-summary-missing", report)
        self.assertIn("cpu-fallback-observed", report)
        self.assertIn("DOOM 35 Hz game-tic cadence", report)
        self.assertIn("raw command output stays private", report.lower())


if __name__ == "__main__":
    unittest.main()
