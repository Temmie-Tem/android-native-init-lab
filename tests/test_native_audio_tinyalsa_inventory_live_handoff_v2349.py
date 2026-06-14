"""Host-only tests for the V2349 tinyalsa inventory live handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2349 = load_revalidation("native_audio_tinyalsa_inventory_live_handoff_v2349")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "approval": "",
        "manifest": v2349.inv.MANIFEST,
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "device_ip": "192.168.7.2",
        "host_ip": "192.168.7.1",
        "host_prefix": 24,
        "tcp_port": 2325,
        "command_timeout": 60.0,
        "tcp_timeout": 30.0,
        "device_toolbox": v2349.DEFAULT_DEVICE_TOOLBOX,
        "flash_timeout": 900.0,
        "card_timeout": 70.0,
        "poll_interval": 2.0,
        "menu_settle_sec": 1.0,
        "transfer_port": 18149,
        "transfer_delay": 1.0,
        "transfer_timeout": 120.0,
        "repair_host_ncm": True,
        "ncm_setup_timeout": 120.0,
        "ncm_interface_timeout": 20.0,
        "ncm_setup_sudo": "sudo -n",
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
        self.assertIn("host_ncm_repair", payload["transfer_readiness_plan"])
        repair_command = payload["transfer_readiness_plan"]["host_ncm_repair"]
        self.assertIn("ncm_host_setup.py", " ".join(repair_command))
        self.assertIn("--allow-auto-interface", repair_command)
        self.assertIn("sudo -n", repair_command)
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
                self.assertIn("--toybox", command)
                self.assertEqual(
                    command[command.index("--toybox") + 1],
                    "/bin/toybox",
                )
                self.assertNotIn("/cache/bin/toybox", command)

    def test_tcpctl_commands_use_toybox_netcat_semantics(self) -> None:
        payload = v2349.dry_run_payload(args())

        self.assertEqual(payload["preflight"]["device_toolbox"], "/bin/toybox")
        flat = json.dumps(payload, sort_keys=True)
        self.assertIn("/bin/toybox", flat)
        self.assertNotIn("/cache/bin/toybox", flat)
        self.assertNotIn("/cache/bin/busybox", flat)

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

    def test_transfer_readiness_repairs_host_ncm_then_selects_tcpctl(self) -> None:
        calls: list[str] = []

        def fake_run_host_step(_out_dir, _steps, name, _command, **_kwargs):
            calls.append(name)
            if name == "transfer-host-ncm-ping":
                return {"rc": 1, "stdout_tail": ""}
            if name == "transfer-tcpctl-ping":
                return {"rc": 1, "stdout_tail": "timed out"}
            if name == "transfer-host-ncm-setup":
                return {"rc": 0, "stdout_path": "setup.txt"}
            if name == "transfer-host-ncm-ping-after-ncm-setup":
                return {"rc": 0, "stdout_tail": "1 packets transmitted, 1 received"}
            if name == "transfer-tcpctl-ping-after-ncm-setup":
                return {"rc": 0, "stdout_tail": "a90_tcpctl v1 ready\npong\nOK\n", "stdout_path": ""}
            raise AssertionError(name)

        with mock.patch.object(v2349, "run_host_step", side_effect=fake_run_host_step):
            readiness = v2349.probe_transfer_readiness(args(), Path("/tmp/out"), [])

        self.assertEqual(readiness["selected_transport"], "tcpctl")
        self.assertTrue(readiness["repair_attempted"])
        self.assertTrue(readiness["repair_ok"])
        self.assertEqual(readiness["initial_probe"]["host_ncm_ping_ok"], False)
        self.assertEqual(
            calls,
            [
                "transfer-host-ncm-ping",
                "transfer-tcpctl-ping",
                "transfer-host-ncm-setup",
                "transfer-host-ncm-ping-after-ncm-setup",
                "transfer-tcpctl-ping-after-ncm-setup",
            ],
        )

    def test_transfer_readiness_can_disable_host_ncm_repair(self) -> None:
        def fake_run_host_step(_out_dir, _steps, name, _command, **_kwargs):
            self.assertNotEqual(name, "transfer-host-ncm-setup")
            return {"rc": 1, "stdout_tail": ""}

        with mock.patch.object(v2349, "run_host_step", side_effect=fake_run_host_step), \
                self.assertRaisesRegex(RuntimeError, "neither tcpctl nor host NCM"):
            v2349.probe_transfer_readiness(args(repair_host_ncm=False), Path("/tmp/out"), [])

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
