"""Static checks for V3017 DOOMPAD gameplay-loop live validation runner."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doompad_gameplay_loop_live_validation_v3017 as runner  # noqa: E402


class TestNativeDoompadGameplayLoopLiveV3017(unittest.TestCase):
    def test_identity_and_assets(self) -> None:
        self.assertEqual(runner.RUN_ID, "V3017")
        self.assertEqual(runner.CANDIDATE_VERSION, "0.10.71")
        self.assertEqual(runner.CANDIDATE_TAG, "v3016-doompad-gameplay-loop")
        self.assertEqual(
            runner.CANDIDATE_SHA256,
            "e5303f7b79b8ebc100ffd5361c965753c6e325a94d3b6f3316d13ebcd22006e6",
        )
        self.assertTrue(str(runner.CANDIDATE_IMAGE).endswith("boot_linux_v3016_doompad_gameplay_loop.img"))
        self.assertTrue(str(runner.REPORT_PATH).endswith("NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md"))

    def test_flash_command_uses_checked_helper_and_pinned_sha(self) -> None:
        command = runner.flash_command(
            runner.CANDIDATE_IMAGE,
            runner.CANDIDATE_VERSION,
            runner.CANDIDATE_SHA256,
            from_native=True,
        )
        joined = " ".join(command)
        self.assertIn("native_init_flash.py", joined)
        self.assertIn("boot_linux_v3016_doompad_gameplay_loop.img", joined)
        self.assertIn("--expect-version", command)
        self.assertIn(runner.CANDIDATE_VERSION, command)
        self.assertIn("--expect-sha256", command)
        self.assertIn(runner.CANDIDATE_SHA256, command)
        self.assertIn("--expect-readback-sha256", command)
        self.assertIn("--verify-protocol", command)
        self.assertIn("selftest", command)
        self.assertIn("--from-native", command)

    def test_doompad_and_doomplay_contract(self) -> None:
        setup_names = [name for name, _command, _markers in runner.DOOMPAD_SETUP_STEPS]
        cleanup_names = [name for name, _command, _markers in runner.DOOMPAD_CLEANUP_STEPS]
        setup_commands = [" ".join(command) for _name, command, _markers in runner.DOOMPAD_SETUP_STEPS]
        cleanup_commands = [" ".join(command) for _name, command, _markers in runner.DOOMPAD_CLEANUP_STEPS]
        self.assertEqual(setup_names[0], "doompad-reset-before-play")
        self.assertIn("doompad-forward-down", setup_names)
        self.assertIn("doompad-fire-down", setup_names)
        self.assertIn("doompad key forward 1", setup_commands)
        self.assertIn("doompad key fire 1", setup_commands)
        self.assertIn("doompad-fire-up", cleanup_names)
        self.assertIn("doompad-forward-up", cleanup_names)
        self.assertIn("doompad-reset-after-play", cleanup_names)
        self.assertIn("doompad key fire 0", cleanup_commands)
        self.assertIn("doompad key forward 0", cleanup_commands)
        self.assertEqual(runner.DOOMPLAY_COMMAND, ["video", "demo", "doom", "play", "8"])
        self.assertIn("doomplay.input.forward=1 back=0 left=0 right=0 fire=1", runner.DOOMPLAY_MARKERS)
        self.assertIn("doomplay.frames_presented=8", runner.DOOMPLAY_MARKERS)

    def test_doomplay_position_parser_requires_forward_movement(self) -> None:
        parsed = runner._parse_player_positions(
            "doomplay.initial.x=540 y=1200\r\n"
            "doomplay.player.x=540 y=1128\r\n"
        )
        self.assertTrue(parsed["parsed"])
        self.assertTrue(parsed["moved_forward"])
        self.assertEqual(parsed["initial_y"], 1200)
        self.assertEqual(parsed["player_y"], 1128)
        not_forward = runner._parse_player_positions(
            "doomplay.initial.x=540 y=1200\r\n"
            "doomplay.player.x=540 y=1200\r\n"
        )
        self.assertFalse(not_forward["moved_forward"])

    def test_live_pass_requires_status_doomplay_movement_and_cleanup(self) -> None:
        result = {
            "candidate_version_ok": True,
            "candidate_selftest_fail0": True,
            "video_status_rc": 0,
            "video_status_markers": {marker: True for marker in runner.VIDEO_STATUS_MARKERS},
            "doom_status_rc": 0,
            "doom_status_markers": {marker: True for marker in runner.DOOM_STATUS_MARKERS},
            "doompad_setup_steps": {
                name: {"rc": 0, "markers": {marker: True for marker in markers}}
                for name, _command, markers in runner.DOOMPAD_SETUP_STEPS
            },
            "doomplay_rc": 0,
            "doomplay_markers": {marker: True for marker in runner.DOOMPLAY_MARKERS},
            "doomplay_position": {
                "parsed": True,
                "initial_x": 540,
                "initial_y": 1200,
                "player_x": 540,
                "player_y": 1128,
                "moved_forward": True,
            },
            "doompad_cleanup_steps": {
                name: {"rc": 0, "markers": {marker: True for marker in markers}}
                for name, _command, markers in runner.DOOMPAD_CLEANUP_STEPS
            },
            "candidate_selftest_after_doomplay_fail0": True,
        }
        self.assertTrue(runner.live_pass(result))
        result["doomplay_position"]["moved_forward"] = False
        self.assertFalse(runner.live_pass(result))

    def test_preflight_and_report_contract(self) -> None:
        args = argparse.Namespace(live=False, flash_timeout=900.0)
        state = runner.preflight_state(args)
        self.assertTrue(runner.preflight_ok(state))
        self.assertEqual(state["operator_prerequisite"], "none; gameplay-loop validation uses only the serial command bridge")
        report = runner.render_report({
            "decision": "dry-run",
            "pass": False,
            "live_executed": False,
            "out_dir": "workspace/private/runs/video/example",
            "preflight": state,
            "preflight_ok": True,
            "rollback_attempted": False,
        })
        self.assertIn("Native Init V3017 DOOMPAD Gameplay Loop", report)
        self.assertIn("video demo doom play 8", report)
        self.assertIn("bounded foreground KMS proof surface", report)
        self.assertIn("native_init_flash.py", report)
        self.assertIn("raw command output stays private", report.lower())


if __name__ == "__main__":
    unittest.main()
