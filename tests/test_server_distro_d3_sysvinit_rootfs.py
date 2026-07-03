from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
