from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


d3a = load_script("workspace/public/src/scripts/server-distro/prepare_d3_sysvinit_rootfs.py")


class ServerDistroD3SysvinitRootfsTests(unittest.TestCase):
    def test_firstboot_contract_has_recovery_before_network_and_dropbear(self) -> None:
        script = d3a.firstboot_script("192.168.7.2", "192.168.7.1", 120, 2222)

        autoreboot_pos = script.index("sleep 120")
        ncm_pos = script.index("$IP addr replace 192.168.7.2/24 dev ncm0")
        dropbear_pos = script.index("/usr/sbin/dropbear")
        marker_pos = script.index("A90D3_MARKER")

        self.assertLess(autoreboot_pos, ncm_pos)
        self.assertLess(ncm_pos, marker_pos)
        self.assertLess(marker_pos, dropbear_pos)
        self.assertIn("/sbin/reboot -f", script)
        self.assertIn("/proc/sysrq-trigger", script)
        self.assertIn("IP=/usr/bin/ip", script)
        self.assertIn("-s -j -k", script)
        self.assertIn("/root/.ssh/authorized_keys", script)
        self.assertIn("pid1_comm=$(cat /proc/1/comm", script)

    def test_firstboot_contract_does_not_touch_userdata_or_public_tunnel(self) -> None:
        script = d3a.firstboot_script("192.168.7.2", "192.168.7.1", 120, 2222)

        self.assertNotIn("/dev/block/sda33", script)
        self.assertNotIn("mkfs", script)
        self.assertNotIn("userdata", script)
        self.assertNotIn("cloudflared", script)
        self.assertNotIn("tunnel", script)

    def test_sysv_package_set_is_minimal_and_explicit(self) -> None:
        self.assertEqual(
            d3a.SYSV_PACKAGES,
            ("insserv", "startpar", "initscripts", "sysv-rc", "sysvinit-core"),
        )

    def test_usrmerge_links_are_restored_after_package_extract(self) -> None:
        self.assertEqual(
            d3a.USR_MERGE_LINKS,
            (("bin", "usr/bin"), ("sbin", "usr/sbin"), ("lib", "usr/lib")),
        )
        source = Path("workspace/public/src/scripts/server-distro/prepare_d3_sysvinit_rootfs.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("def restore_usrmerge_links", source)
        self.assertIn("merge_tree_contents(link, target)", source)
        self.assertIn("restore_usrmerge_links(d3_rootfs)", source)

    def test_d3_contract_stages_dpublic_wifi_sta_helper_without_enabling_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            (rootfs / "etc").mkdir()
            (rootfs / "run").mkdir()
            (rootfs / "root" / ".ssh").mkdir(parents=True)
            args = argparse.Namespace(ncm_ip="192.168.7.2", ncm_peer="192.168.7.1", autoreboot_sec=120, ssh_port=2222)

            d3a.install_d3_contract(args, rootfs)

            helper = rootfs / d3a.DPUBLIC_WIFI_STA_TARGET
            self.assertTrue(helper.is_file())
            self.assertEqual(helper.stat().st_mode & 0o777, 0o755)
            self.assertTrue((rootfs / "etc/a90-dpublic").is_dir())
            self.assertFalse((rootfs / "etc/a90-dpublic/wifi-sta-enable").exists())
            marker = (rootfs / "etc/a90-server-distro-stage").read_text(encoding="utf-8")
            self.assertIn("wifi-sta=opt-in via /etc/a90-dpublic/wifi-sta-enable", marker)
            self.assertIn("wifi-sta-helper=/usr/local/bin/a90-dpublic-wifi-sta", marker)


if __name__ == "__main__":
    unittest.main()
