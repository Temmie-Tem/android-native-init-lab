"""Host-only tests for the V2346 tinyalsa inventory gate planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path

from _loader import load_revalidation

v2346 = load_revalidation("native_audio_tinyalsa_inventory_gate_v2346")


class TinyalsaInventoryGate(unittest.TestCase):
    def test_manifest_verification_accepts_v2345_tools_and_excludes_tinyplay(self) -> None:
        state = v2346.verify_manifest()

        self.assertTrue(state["ok"])
        self.assertEqual(state["source_commit"], v2346.TINYALSA_COMMIT)
        self.assertTrue(state["tools"]["tinymix"]["sha256_ok"])
        self.assertTrue(state["tools"]["tinypcminfo"]["sha256_ok"])
        self.assertTrue(state["prohibited_tools"]["tinyplay"]["present_in_manifest"])
        self.assertFalse(state["prohibited_tools"]["tinyplay"]["used_by_v2346"])

    def test_planned_commands_are_read_only_inventory_only(self) -> None:
        commands = v2346.planned_inventory_commands(card=0, pcm_devices=(0, 1))
        safety = v2346.command_safety(commands)

        self.assertTrue(safety["ok"])
        self.assertEqual(safety["excluded_tools"], ["tinyplay"])
        self.assertTrue(all(command["mutates_audio_state"] is False for command in commands))
        self.assertTrue(all(command["opens_alsa"] is True for command in commands))
        flat = " ".join(" ".join(command["argv"]) for command in commands)
        self.assertIn("tinymix", flat)
        self.assertIn("tinypcminfo", flat)
        self.assertNotIn("tinyplay", flat)

    def test_tinymix_extra_value_operand_is_rejected(self) -> None:
        bad = [{
            "name": "bad-set",
            "argv": [v2346.REMOTE_TOOLS["tinymix"], "-D", "0", "Some Control", "1"],
        }]

        safety = v2346.command_safety(bad)

        self.assertFalse(safety["ok"])
        self.assertIn("extra operands", safety["findings"][0]["reason"])

    def test_dry_run_payload_requires_prior_materialization_and_exact_future_gate(self) -> None:
        payload = v2346.dry_run_payload(argparse.Namespace(manifest=v2346.MANIFEST, card=0, pcm_device=[0]))

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertIn("AUD-3C-tinyalsa-inventory go:", payload["approval_phrase_required_for_future_live"])
        self.assertIn("V2346 is not a substitute", payload["requires_prior_materialization"]["note"])

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_gate_v2346.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2346.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2346-audio-tinyalsa-inventory-gate-dry-run")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
