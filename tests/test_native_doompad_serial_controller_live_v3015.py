"""Static checks for V3015 DOOMPAD serial-controller live validation runner."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doompad_serial_controller_live_validation_v3015 as runner  # noqa: E402


class TestNativeDoompadSerialControllerLiveV3015(unittest.TestCase):
    def test_identity_and_assets(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3015")
        self.assertEqual(runner.CANDIDATE_VERSION, "0.10.70")
        self.assertEqual(runner.CANDIDATE_TAG, "v3014-doompad-serial-controller")
        self.assertEqual(
            runner.CANDIDATE_SHA256,
            "5bdcab90807fe03f1f97717e4b371bce6c3567ad1f7635b51babb77b83b61455",
        )
        self.assertTrue(str(runner.CANDIDATE_IMAGE).endswith("boot_linux_v3014_doompad_serial_controller.img"))
        self.assertTrue(str(runner.REPORT_PATH).endswith("NATIVE_INIT_V3015_DOOMPAD_SERIAL_CONTROLLER_LIVE_2026-06-21.md"))

    def test_flash_command_uses_checked_helper_and_pinned_sha(self) -> None:
        command = runner.flash_command(
            runner.CANDIDATE_IMAGE,
            runner.CANDIDATE_VERSION,
            runner.CANDIDATE_SHA256,
            from_native=True,
        )
        joined = " ".join(command)
        self.assertIn("native_init_flash.py", joined)
        self.assertIn("boot_linux_v3014_doompad_serial_controller.img", joined)
        self.assertIn("--expect-version", command)
        self.assertIn(runner.CANDIDATE_VERSION, command)
        self.assertIn("--expect-sha256", command)
        self.assertIn(runner.CANDIDATE_SHA256, command)
        self.assertIn("--expect-readback-sha256", command)
        self.assertIn("--verify-protocol", command)
        self.assertIn("selftest", command)
        self.assertIn("--from-native", command)

    def test_doompad_step_contract(self) -> None:
        names = [name for name, _command, _markers in runner.DOOMPAD_STEPS]
        self.assertEqual(names[0], "doompad-status-initial")
        self.assertIn("doompad-forward-down", names)
        self.assertIn("doompad-fire-down", names)
        self.assertIn("doompad-fire-up", names)
        self.assertIn("doompad-forward-up", names)
        self.assertIn("doompad-use-tap", names)
        self.assertIn("doompad-reset", names)
        commands = [" ".join(command) for _name, command, _markers in runner.DOOMPAD_STEPS]
        self.assertIn("doompad key forward 1", commands)
        self.assertIn("doompad key fire 1", commands)
        self.assertIn("doompad key fire 0", commands)
        self.assertIn("doompad key forward 0", commands)
        self.assertIn("doompad tap use", commands)
        self.assertIn("doompad reset", commands)

    def test_live_pass_requires_status_and_doompad_markers(self) -> None:
        result = {
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "video_status_rc": 0,
            "video_status_markers": {marker: True for marker in runner.VIDEO_STATUS_MARKERS},
            "doom_status_rc": 0,
            "doom_status_markers": {marker: True for marker in runner.DOOM_STATUS_MARKERS},
            "doompad_steps": {
                name: {"rc": 0, "markers": {marker: True for marker in markers}}
                for name, _command, markers in runner.DOOMPAD_STEPS
            },
            "candidate_selftest_after_doompad_fail0": True,
        }
        self.assertTrue(runner.live_pass(result))
        result["doompad_steps"]["doompad-fire-down"]["markers"]["fire=1"] = False
        self.assertFalse(runner.live_pass(result))

    def test_preflight_and_report_contract(self) -> None:
        args = argparse.Namespace(live=False, flash_timeout=900.0)
        state = runner.preflight_state(args)
        self.assertTrue(runner.preflight_ok(state))
        self.assertEqual(state["operator_prerequisite"], "none; serial doompad validation uses only the command bridge")
        report = runner.render_report({
            "decision": "dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": state,
            "preflight_ok": True,
            "rollback_attempted": False,
        })
        self.assertIn("Native Init V3015 DOOMPAD Serial Controller", report)
        self.assertIn("serial-controlled in-memory DOOM input state", report)
        self.assertIn("native_init_flash.py", report)
        self.assertIn("No input injection", report)
        self.assertIn("raw command output stays private", report.lower())


if __name__ == "__main__":
    unittest.main()
