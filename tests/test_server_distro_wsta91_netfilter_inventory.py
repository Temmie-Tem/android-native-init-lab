from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta91_netfilter_inventory.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta91_netfilter_inventory.py")


class ServerDistroWsta91NetfilterInventoryTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta91"),
            *extra,
        ])

    def raw(self, config: str, tools: str, proc_text: str = "") -> dict:
        return {
            "observations": [
                {"name": "kernel_config_netfilter", "text": config},
                {"name": "userspace_filter_tools", "text": tools},
                {"name": "proc_netfilter_surfaces", "text": proc_text},
            ]
        }

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root))
            saved = json.loads((root / "wsta91" / "wsta91_netfilter_inventory.json").read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta91-blocked-live-readonly-netfilter-inventory-required")
        self.assertEqual(saved["decision"], result["decision"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["packet_filter_mutation"])
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["native_reboot"])
        self.assertFalse(result["safety"]["wifi_connect"])
        self.assertFalse(result["safety"]["public_tunnel"])

    def test_nftables_backend_when_config_and_tool_present(self) -> None:
        inventory = runner.classify_inventory(self.raw(
            "CONFIG_NETFILTER=y\nCONFIG_NF_TABLES=y\nCONFIG_NF_CONNTRACK=y\n",
            "__A90_WSTA91_BUSYBOX__\nnft\nlsmod\n",
            "__A90_WSTA91_PATH__=/proc/sys/net/netfilter\n__A90_WSTA91_DIR__\ntotal 0\n",
        ))

        self.assertEqual(inventory["decision"], runner.PASS_DECISION)
        self.assertEqual(inventory["backend_recommendation"], "nftables")
        self.assertTrue(inventory["default_drop_ready_for_source"])
        self.assertTrue(inventory["tools"]["nft"])
        self.assertTrue(inventory["proc_surfaces"]["netfilter_sysctl"])

    def test_legacy_iptables_backend_when_config_and_tool_present(self) -> None:
        inventory = runner.classify_inventory(self.raw(
            "CONFIG_NETFILTER=y\nCONFIG_IP_NF_IPTABLES=y\nCONFIG_NETFILTER_XTABLES=y\n",
            "__A90_WSTA91_BUSYBOX__\niptables\nip6tables\n",
            "__A90_WSTA91_PATH__=/proc/net/ip_tables_names\n__A90_WSTA91_READABLE__\n",
        ))

        self.assertEqual(inventory["backend_recommendation"], "legacy-iptables")
        self.assertTrue(inventory["default_drop_ready_for_source"])
        self.assertTrue(inventory["tools"]["iptables"])
        self.assertTrue(inventory["proc_surfaces"]["ip_tables_names"])

    def test_missing_backend_stays_not_proven(self) -> None:
        inventory = runner.classify_inventory(self.raw(
            "CONFIG_NETFILTER=y\n# CONFIG_NF_TABLES is not set\n",
            "__A90_WSTA91_BUSYBOX__\nlsmod\n",
            "__A90_WSTA91_PATH__=/proc/net/nf_conntrack\n__A90_WSTA91_MISSING__\n",
        ))

        self.assertEqual(inventory["backend_recommendation"], "not-proven")
        self.assertFalse(inventory["default_drop_ready_for_source"])
        self.assertFalse(inventory["proc_surfaces"]["nf_conntrack"])

    def test_observation_commands_are_read_only_inventory(self) -> None:
        joined = "\n".join(obs.command for obs in runner.OBSERVATIONS)
        forbidden = (
            "iptables -A",
            "iptables -I",
            "iptables -D",
            "iptables -F",
            "ip6tables -A",
            "ip6tables -I",
            "ip6tables -D",
            "ip6tables -F",
            "nft add",
            "nft delete",
            "nft flush",
            "nft insert",
            "nft replace",
            "modprobe ",
            "insmod ",
            "rmmod ",
            "mount ",
            "dd ",
            "reboot",
        )
        for item in forbidden:
            self.assertNotIn(item, joined)
        self.assertIn("/bin/busybox grep", joined)
        self.assertIn("cat \"$p\"", joined)
        self.assertIn("__A90_WSTA91_READABLE__", joined)
        self.assertIn("__A90_WSTA91_DIR__", joined)

    def test_source_keeps_packet_filter_mutation_out_of_scope(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
