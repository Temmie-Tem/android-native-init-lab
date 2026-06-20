"""Static checks for V3001 DOOM status stub live handoff."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doom_status_stub_live_handoff_v3001.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doom_status_stub_live_handoff_v3001 as runner  # noqa: E402


class TestNativeDoomStatusStubLiveHandoffV3001(unittest.TestCase):
    def test_runner_targets_v3000_status_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V3001"', text)
        self.assertIn('CANDIDATE_VERSION = "0.10.68"', text)
        self.assertIn('CANDIDATE_TAG = "v3000-doom-status-stub"', text)
        self.assertIn("boot_linux_v3000_doom_status_stub.img", text)
        self.assertIn("bca4afa1300dac66499c71a45774547eb9625fdf07e7be09f76259c08e1e8e2d", text)
        self.assertEqual(runner.BUILD_TAG, "v3001-doom-status-stub-live")

    def test_runner_preserves_flash_and_status_only_boundaries(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("native_init_flash.py", text)
        self.assertIn("base.rollback_v2321", text)
        self.assertIn("no doominputmux sample, input read window, playback, or sysfs writes", text)
        self.assertIn("The validation path is status-only over the serial command bridge.", text)
        self.assertNotIn("run_timeout_doominputmux", text)
        self.assertNotIn("read_manual_step", text)
        self.assertNotIn("EVIOCGRAB)", text)
        self.assertNotIn("O_WRONLY", text)
        self.assertNotIn("sendevent", text)

    def test_marker_summary_and_pass_contract(self) -> None:
        video_text = "\n".join(runner.VIDEO_STATUS_MARKERS)
        doom_text = "\n".join(runner.DOOM_STATUS_MARKERS)
        video_summary = runner.marker_summary(video_text, runner.VIDEO_STATUS_MARKERS)
        doom_summary = runner.marker_summary(doom_text, runner.DOOM_STATUS_MARKERS)
        self.assertTrue(runner.all_markers_present(video_summary))
        self.assertTrue(runner.all_markers_present(doom_summary))
        result = {
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "video_status_rc": 0,
            "video_status_markers": video_summary,
            "doom_status_rc": 0,
            "doom_status_markers": doom_summary,
            "candidate_selftest_after_status_fail0": True,
        }
        self.assertTrue(runner.status_surface_pass(result))
        result["doom_status_markers"] = dict(doom_summary)
        result["doom_status_markers"]["video.demo.input=not-proven"] = False
        self.assertFalse(runner.status_surface_pass(result))

    def test_preflight_ok_requires_candidate_and_rollbacks(self) -> None:
        state = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
            "flash_helper": {"exists": True},
        }
        self.assertTrue(runner.preflight_ok(state))
        state["fallback_v2237"]["sha256_ok"] = False
        self.assertFalse(runner.preflight_ok(state))

    def test_dry_run_contract_is_status_only(self) -> None:
        args = Namespace()
        state = {
            "candidate": {"sha256_ok": True},
            "rollback": {"sha256_ok": True},
            "fallback_v2237": {"sha256_ok": True},
            "fallback_v48": {"exists": True},
            "flash_helper": {"exists": True},
        }
        payload = runner.dry_run_payload(args, state)
        joined = "\n".join(payload["commands"])
        self.assertEqual(payload["decision"], "v3001-doom-status-stub-dry-run")
        self.assertTrue(payload["ok"])
        self.assertIn("video status", joined)
        self.assertIn("video demo doom status", joined)
        self.assertIn("v2999 doominputmux handoff markers", joined)
        self.assertNotIn("operator presses", joined)
        self.assertNotIn("doominputmux event3,event0 24 45000", joined)

    def test_render_report_describes_status_only_live_handoff(self) -> None:
        result = {
            "decision": "v3001-doom-status-stub-dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": {
                "candidate": {"sha256_ok": True},
                "rollback": {"sha256_ok": True},
                "fallback_v2237": {"sha256_ok": True},
                "fallback_v48": {"exists": True},
                "flash_helper": {"exists": True},
                "operator_prerequisite": "none; status-only live validation does not require button/touch input",
            },
            "preflight_ok": True,
            "rollback_attempted": False,
        }
        report = runner.render_report(result)
        self.assertIn("Native Init V3001 DOOM Status Stub Live Handoff Dry Run", report)
        self.assertIn("Operator prerequisite: `none; status-only live validation does not require button/touch input`", report)
        self.assertIn("does not run `doominputmux`", report)
        self.assertIn("status-only over the serial command bridge", report)
        self.assertIn("v2999", report)


if __name__ == "__main__":
    unittest.main()
