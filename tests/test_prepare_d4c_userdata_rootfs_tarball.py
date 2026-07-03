"""Regression tests for the D4C userdata rootfs tarball staging runner."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


d4c = load_script("workspace/public/src/scripts/server-distro/prepare_d4c_userdata_rootfs_tarball.py")


class PrepareD4CUserdataRootfsTarballTests(unittest.TestCase):
    def test_defaults_target_private_rootfs_and_sd_runtime_tarball(self) -> None:
        self.assertIn("d3-sysvinit-usrmerge", str(d4c.DEFAULT_ROOTFS))
        self.assertEqual(d4c.DEFAULT_REMOTE_TARBALL, "/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar")
        self.assertEqual(d4c.EXPECTED_STAGE_FILE, "etc/a90-server-distro-stage")
        self.assertEqual(d4c.EXPECTED_WIFI_STA_HELPER, "usr/local/bin/a90-dpublic-wifi-sta")
        self.assertEqual(d4c.EXPECTED_WIFI_STA_CONFIG_DIR, "etc/a90-dpublic")

    def test_tar_command_forces_root_owner_without_touching_userdata(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/prepare_d4c_userdata_rootfs_tarball.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"tar"', source)
        self.assertIn('"--owner=0"', source)
        self.assertIn('"--group=0"', source)
        self.assertIn('"--numeric-owner"', source)
        self.assertIn("DEFAULT_REMOTE_TARBALL", source)
        for forbidden in ("mkfs", "mke2fs", "userdata-appliance-format", "switch-root-to-userdata"):
            self.assertNotIn(forbidden, source)
        self.assertIn('"flash_performed": False', source)
        self.assertIn('"userdata_touched": False', source)

    def test_tarball_verification_requires_init_stage_and_inittab(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/prepare_d4c_userdata_rootfs_tarball.py").read_text(
            encoding="utf-8"
        )
        for marker in (
            "./sbin",
            "./usr/sbin/init",
            "./etc/debian_version",
            "./etc/inittab",
        ):
            self.assertIn(marker, source)
        self.assertIn('"./" + EXPECTED_STAGE_FILE', source)
        self.assertIn('"./" + EXPECTED_WIFI_STA_HELPER', source)
        self.assertIn("remote_tarball_sha", source)
        self.assertIn("stage_tarball", source)

    def test_rootfs_verification_requires_wifi_sta_helper(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/prepare_d4c_userdata_rootfs_tarball.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"wifi_sta_helper": rootfs / EXPECTED_WIFI_STA_HELPER', source)
        self.assertIn('"wifi_sta_config_dir": rootfs / EXPECTED_WIFI_STA_CONFIG_DIR', source)
        self.assertIn("Wi-Fi STA helper is not executable", source)


if __name__ == "__main__":
    unittest.main()
