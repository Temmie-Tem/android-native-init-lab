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
        "inventory_transport": "auto",
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
        self.assertIn("transfer_readiness_plan", payload)
        self.assertIn("host_ncm_ping", payload["transfer_readiness_plan"])
        self.assertIn("tcpctl_ping", payload["transfer_readiness_plan"])
        inventory_commands = []
        for step in payload["inventory_plan"]:
            inventory_commands.extend(step["auto_select"]["tcpctl"])
            inventory_commands.extend(step["auto_select"]["serial"])
        self.assertNotIn("tinyplay", " ".join(inventory_commands))

    def test_remote_tools_install_under_tcpctl_allowed_cache_root(self) -> None:
        payload = v2349.dry_run_payload(args())

        self.assertEqual(payload["preflight"]["remote_dir"], "/cache/bin")
        self.assertEqual(payload["preflight"]["remote_tools"]["tinymix"], "/cache/bin/tinymix")
        self.assertEqual(payload["preflight"]["remote_tools"]["tinypcminfo"], "/cache/bin/tinypcminfo")
        for step in payload["tool_install_plan"]:
            for command in step["auto_select"].values():
                self.assertIn("--device-binary", command)
                target = command[command.index("--device-binary") + 1]
                self.assertTrue(target.startswith("/cache/bin/"), target)

    def test_auto_transport_prefers_tcpctl_then_falls_back_to_serial_when_ncm_is_ready(self) -> None:
        self.assertEqual(
            v2349.choose_inventory_transport(args(), host_ncm_ready=True, tcpctl_ready=True),
            "tcpctl",
        )
        self.assertEqual(
            v2349.choose_inventory_transport(args(), host_ncm_ready=True, tcpctl_ready=False),
            "serial",
        )
        with self.assertRaisesRegex(RuntimeError, "neither tcpctl nor host NCM"):
            v2349.choose_inventory_transport(args(), host_ncm_ready=False, tcpctl_ready=False)

    def test_forced_transport_requires_matching_readiness(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requested tcpctl"):
            v2349.choose_inventory_transport(
                args(inventory_transport="tcpctl"),
                host_ncm_ready=True,
                tcpctl_ready=False,
            )
        with self.assertRaisesRegex(RuntimeError, "requested serial"):
            v2349.choose_inventory_transport(
                args(inventory_transport="serial"),
                host_ncm_ready=False,
                tcpctl_ready=False,
            )

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
