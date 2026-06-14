"""Host-only tests for the V2378 native speaker route recipe planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path

from _loader import load_revalidation


v2378 = load_revalidation("native_audio_speaker_route_recipe_v2378")


def default_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "evidence_dir": v2378.DEFAULT_EVIDENCE_DIR,
        "duration_ms": 1000,
        "amplitude": 0.02,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class NativeSpeakerRouteRecipe(unittest.TestCase):
    def test_v2377_evidence_verifies_audio_stimulus_and_rollback(self) -> None:
        state = v2378.verify_evidence(v2378.ROOT / v2378.DEFAULT_EVIDENCE_DIR)

        self.assertTrue(state["ok"])
        self.assertTrue(state["rolled_back"])
        self.assertTrue(state["marker_ok"])
        self.assertEqual(state["marker_counts"]["A90_AUDIO_STIMULUS_ERROR"], 0)
        self.assertEqual(state["marker_counts"]["REVIEW_PERMISSIONS"], 0)
        self.assertTrue(state["audio_framework_ok"])

    def test_route_delta_extracts_expected_speaker_controls(self) -> None:
        delta = v2378.route_delta(v2378.ROOT / v2378.DEFAULT_EVIDENCE_DIR)

        self.assertTrue(delta["ok"], delta["findings"])
        by_name = {item["name"]: item for item in delta["controls"]}
        self.assertEqual(by_name["SLIMBUS_0_RX Audio Mixer MultiMedia1"]["command_values_active"], ["1", "0"])
        self.assertEqual(by_name["SLIM RX0 MUX"]["command_values_active"], ["AIF1_PB"])
        self.assertEqual(by_name["RX INT7_1 MIX1 INP0"]["command_values_active"], ["RX0"])
        self.assertEqual(by_name["COMP7 Switch"]["command_values_active"], ["1"])
        self.assertEqual(by_name["SpkrLeft SWR DAC_Port Switch"]["command_values_active"], ["1"])
        self.assertEqual(by_name["SLIMBUS_0_RX Audio Mixer MultiMedia1"]["command_values_baseline"], ["0", "0"])
        self.assertEqual(by_name["SLIM RX0 MUX"]["command_values_baseline"], ["ZERO"])
        self.assertEqual(by_name["ADSP Path Latency 0"]["role"], "observe_only")

    def test_future_plan_is_host_only_and_bounded(self) -> None:
        payload = v2378.dry_run_payload(default_args())

        self.assertTrue(payload["ok"], payload["command_safety"])
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        future = payload["future_plan"]
        self.assertIn("AUD-4-native-speaker-pilot go:", future["approval_phrase_required_for_future_live"])
        self.assertEqual(future["playback"]["amplitude"], 0.02)
        self.assertEqual(future["playback"]["duration_ms"], 1000)
        self.assertTrue(all(command["not_executed_by_v2378"] for command in future["route_apply_commands"]))
        self.assertTrue(all(command["not_executed_by_v2378"] for command in future["route_reset_commands"]))

    def test_command_safety_rejects_over_amplitude_and_forbidden_token(self) -> None:
        bad_plan = {"route_apply_commands": [{"argv": ["fastboot", "flash"]}], "playback": {}, "route_reset_commands": []}
        safety = v2378.command_safety(bad_plan, amplitude=0.2, duration_ms=2000)

        self.assertFalse(safety["ok"])
        self.assertTrue(any("amplitude" in finding for finding in safety["findings"]))
        self.assertTrue(any("duration" in finding for finding in safety["findings"]))
        self.assertTrue(any("fastboot" in finding for finding in safety["findings"]))

    def test_cli_dry_run_outputs_ready_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_speaker_route_recipe_v2378.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2378.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2378-native-speaker-route-recipe-ready")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
