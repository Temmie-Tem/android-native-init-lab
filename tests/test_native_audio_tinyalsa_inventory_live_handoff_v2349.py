"""Host-only tests for the V2349 tinyalsa inventory live handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path

from _loader import load_revalidation

v2349 = load_revalidation("native_audio_tinyalsa_inventory_live_handoff_v2349")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "approval": "",
        "manifest": v2349.inv.MANIFEST,
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "device_ip": "192.168.7.2",
        "tcp_port": 2325,
        "command_timeout": 60.0,
        "tcp_timeout": 30.0,
        "flash_timeout": 900.0,
        "card_timeout": 70.0,
        "poll_interval": 2.0,
        "menu_settle_sec": 1.0,
        "transfer_port": 18149,
        "transfer_delay": 1.0,
        "transfer_timeout": 120.0,
        "inventory_timeout": 60.0,
        "card": 0,
        "pcm_device": [0],
        "allow_pcm_query_error": True,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TinyalsaInventoryLiveHandoff(unittest.TestCase):
    def test_dry_run_composes_materialization_upload_and_read_only_inventory(self) -> None:
        payload = v2349.dry_run_payload(args())

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "v2349-audio-tinyalsa-inventory-live-dry-run")
        self.assertIn("AUD-3C-tinyalsa-inventory go:", payload["approval_phrase_required"])
        self.assertEqual([step["tool"] for step in payload["tool_install_plan"]], ["tinymix", "tinypcminfo"])
        inventory_names = [step["name"] for step in payload["inventory_plan"]]
        self.assertEqual(inventory_names, [
            "tinymix-list-card0",
            "tinymix-list-card0-all-values",
            "tinypcminfo-card0-device0",
        ])
        flat = json.dumps(payload, sort_keys=True)
        self.assertIn("snd-materialize-once", flat)
        self.assertIn("--install-control-channel", flat)
        self.assertNotIn("tinyplay", " ".join(step["command"][0] for step in payload["inventory_plan"]))

    def test_inventory_commands_are_safe_under_v2346_safety_checker(self) -> None:
        commands = v2349.planned_inventory_commands(args(pcm_device=[0, 1]))
        safety = v2349.command_safety(commands)

        self.assertTrue(safety["ok"])
        self.assertEqual(safety["excluded_tools"], ["tinyplay"])
        self.assertFalse(any("tinyplay" in " ".join(item["argv"]) for item in commands))
        self.assertFalse(any(len(item["argv"]) > 4 and item["argv"][0].endswith("tinymix") for item in commands))

    def test_wrong_live_approval_exits_before_flash(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py",
                "--run-live",
                "--approval",
                "wrong",
            ],
            cwd=v2349.snd.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("exact --approval phrase required", completed.stderr)
        self.assertIn(v2349.APPROVAL_PHRASE, completed.stderr)
        self.assertNotIn("native_init_flash.py", completed.stdout)

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2349.snd.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2349-audio-tinyalsa-inventory-live-dry-run")
        self.assertTrue(payload["preflight"]["tinyalsa_manifest"]["ok"])


if __name__ == "__main__":
    unittest.main()
