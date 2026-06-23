from __future__ import annotations

import argparse
import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_hw_plane_atomic_live_validation_v3115.py")


class NativeDoomgenericHwPlaneAtomicLiveV3115Tests(unittest.TestCase):
    def test_identity_and_candidate_contract(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3115")
        self.assertEqual(runner.CANDIDATE_VERSION, "0.10.112")
        self.assertEqual(runner.CANDIDATE_TAG, "v3114-doomgeneric-hw-plane-atomic")
        self.assertEqual(
            runner.CANDIDATE_SHA256,
            "c25090ecefe790ab680320a0cedebaa6b937155437dc37e52ca2485ffb8485c4",
        )
        self.assertIn("boot_linux_v3114_doomgeneric_hw_plane_atomic.img", str(runner.CANDIDATE_IMAGE))

    def test_parse_loop_output_records_atomic_success(self) -> None:
        parsed = runner.parse_loop_output(
            "\r\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.dashboard.hw_plane_scale=1",
                "video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
                "video.demo.doom.dashboard.hw_plane.attempted=1",
                "video.demo.doom.dashboard.hw_plane.presented=1",
                "video.demo.doom.dashboard.hw_plane.atomic_attempted=1",
                "video.demo.doom.dashboard.hw_plane.atomic_props_rc=0",
                "video.demo.doom.dashboard.hw_plane.atomic_prop_count=9",
                "video.demo.doom.dashboard.hw_plane.atomic_commit_rc=0",
                "video.demo.doom.dashboard.hw_plane.legacy_setplane_rc=-19",
                "video.demo.doom.dashboard.hw_plane.stage=presented",
                "video.demo.doom.dashboard.hw_plane.cached_crtc_index=1",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.rc=0",
                "video.demo.doom.loop.timing_probe=1",
                "video.demo.doom.loop.seq_telemetry=1",
                "video.demo.doom.loop.flip_telemetry=pageflip-event-delta-us",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )
        self.assertTrue(parsed["hw_plane_presented"])
        self.assertEqual(parsed["hw_plane_atomic_attempted_count"], 1)
        self.assertEqual(parsed["hw_plane_atomic_props_rc"], 0)
        self.assertEqual(parsed["hw_plane_atomic_prop_count"], 9)
        self.assertEqual(parsed["hw_plane_atomic_commit_rc"], 0)
        self.assertEqual(parsed["hw_plane_atomic_commit_success_count"], 1)
        self.assertEqual(parsed["hw_plane_legacy_setplane_rc"], -19)
        self.assertTrue(parsed["markers"]["video.demo.doom.dashboard.hw_plane.atomic_commit_rc="])
        self.assertEqual(runner.loop_classification(parsed, 180), "hw-plane-presented")

    def test_parse_loop_output_records_atomic_and_legacy_einval_fallback(self) -> None:
        parsed = runner.parse_loop_output(
            "\r\n".join([
                "video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop",
                "video.demo.doom.loop.verify.ok=1",
                "video.demo.doom.dashboard.hw_plane_scale=1",
                "video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
                "video.demo.doom.dashboard.hw_plane.attempted=1",
                "video.demo.doom.dashboard.hw_plane.presented=0",
                "video.demo.doom.dashboard.hw_plane.atomic_attempted=1",
                "video.demo.doom.dashboard.hw_plane.atomic_props_rc=0",
                "video.demo.doom.dashboard.hw_plane.atomic_prop_count=9",
                "video.demo.doom.dashboard.hw_plane.atomic_commit_rc=-22",
                "video.demo.doom.dashboard.hw_plane.legacy_setplane_rc=-22",
                "video.demo.doom.dashboard.hw_plane.stage=setplane",
                "video.demo.doom.dashboard.hw_plane.cached_crtc_index=1",
                "video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy",
                "video.demo.doom.loop.frames_presented=180",
                "video.demo.doom.loop.rc=0",
                "A90P1 END seq=7 cmd=video rc=0 errno=0 duration_ms=1 flags=0x1 status=ok",
            ])
        )
        self.assertFalse(parsed["hw_plane_presented"])
        self.assertTrue(parsed["hw_plane_fallback"])
        self.assertEqual(parsed["hw_plane_atomic_einval_count"], 1)
        self.assertEqual(parsed["hw_plane_legacy_setplane_einval_count"], 1)
        self.assertEqual(runner.loop_classification(parsed, 180), "cpu-fallback-observed")

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
        self.assertIn("Native Init V3115 DOOMGENERIC Hardware Plane Atomic Live Validation", report)
        self.assertIn("boot_linux_v3114_doomgeneric_hw_plane_atomic.img", report)
        self.assertIn(runner.CANDIDATE_SHA256, report)
        self.assertIn("Atomic Plane Evidence", report)
        self.assertIn("atomic_commit_rc=0", report)
        self.assertIn("pre-scaled producer path", report)
        self.assertIn("native_doomgeneric_hw_plane_atomic_live_validation_v3115.py", report)
        self.assertIn("tests.test_native_doomgeneric_hw_plane_atomic_live_v3115", report)
        self.assertNotIn("next unit should try atomic plane commit", report)
        self.assertNotIn("native_doomgeneric_hw_plane_cached_crtc_live_validation_v3113.py", report)
        payload = runner.dry_run_payload(args, state)
        commands = " ".join(payload["commands"])
        self.assertIn("flash exact V3114 image", commands)
        self.assertIn("boot_linux_v3114_doomgeneric_hw_plane_atomic.img", commands)
        self.assertIn("atomic/stage", commands)
        self.assertNotIn("V3112", commands)


if __name__ == "__main__":
    unittest.main()
