from __future__ import annotations

import unittest

from _loader import load_script


d4a = load_script("workspace/public/src/scripts/server-distro/run_d4a_userdata_preflight.py")


class ServerDistroD4AUserdataPreflightTests(unittest.TestCase):
    def test_device_script_is_read_only(self) -> None:
        script = f" {d4a.D4A_DEVICE_SCRIPT} "

        self.assertIn("A90D4A_BEGIN", script)
        self.assertIn("no_format_performed=1", script)
        self.assertIn("no_mount_performed=1", script)
        self.assertIn("no_flash_performed=1", script)
        self.assertNotIn(" mkfs", script)
        self.assertNotIn(" mke2fs", script)
        self.assertNotIn(" dd ", script)
        self.assertNotIn(" of=", script)
        self.assertNotIn(" losetup ", script)
        self.assertNotIn(" mknod ", script)
        self.assertNotIn(" reboot", script)
        self.assertNotRegex(script, r"(^|[^2])>\s*/")

    def test_classify_passes_exact_userdata_identity(self) -> None:
        text = """
A90D4A_BEGIN
no_format_performed=1
no_mount_performed=1
no_flash_performed=1
target_by_name=/dev/block/by-name/userdata
target_real=/dev/block/sda33
target_block=sda33
target_uevent_DEVNAME=sda33
target_uevent_PARTNAME=userdata
target_size_sectors=244140625
target_dev=259:49
target_ro=0
__A90D4A_USERDATA_SCAN__
scan_block=sda33
scan_uevent_DEVNAME=sda33
scan_uevent_PARTNAME=userdata
scan_size_sectors=244140625
scan_dev=259:49
__A90D4A_BY_NAME__
byname_userdata=/dev/block/sda33
byname_efs=/dev/block/sda3
byname_modem=/dev/block/sda10
__A90D4A_MOUNTS__
/dev/block/mmcblk0p1 /mnt/sdext ext4 rw 0 0
proc /proc proc rw 0 0
__A90D4A_DF_K__
Filesystem 1K-blocks Used Available Use% Mounted on
/dev/block/mmcblk0p1 61407232 12750000 48600000 21% /mnt/sdext
__A90D4A_APPLETS__
df
grep
 mknod
mount
readlink
sha256sum
switch_root
tar
__A90D4A_FILESYSTEMS__
nodev	tmpfs
	ext4
__A90D4A_PARTITIONS__
major minor  #blocks  name
A90D4A_DONE
"""
        raw = {
            "baseline_ok": True,
            "device_observation": {"text": text},
            "host_artifacts": {
                "rollback_images": {
                    "v2321": {"exists": True, "sha256_match": True},
                    "v2237": {"exists": True, "sha256_match": True},
                    "v48": {"exists": True},
                },
                "d3_source_image": {"exists": True, "sha256_match": True},
                "d3_source_rootfs": {"exists": True, "sbin_init_exists": True},
                "d3b_report": {
                    "exists": True,
                    "switchroot_pass_evidence": True,
                    "twrp_recovery_evidence": True,
                },
                "adb_devices": {"recovery_currently_connected": False},
            },
        }

        summary = d4a.classify(raw)

        self.assertEqual(summary["decision"], "server-distro-d4a-userdata-preflight-pass")
        self.assertTrue(summary["preflight_ok"])
        self.assertEqual(summary["target"]["realpath"], "/dev/block/sda33")
        self.assertEqual(summary["target"]["source"], "by-name")
        self.assertEqual(summary["target"]["partname"], "userdata")
        self.assertEqual(summary["target"]["bytes"], 125000000000)
        self.assertFalse(summary["userdata_mounted"])
        self.assertEqual(summary["forbidden_collision"], {})
        self.assertEqual(summary["d4b_must_stage"], ["mkfs.ext4"])
        self.assertEqual(summary["d4b_must_materialize"], [])
        self.assertFalse(summary["d4c_allowed_now"])

    def test_classify_accepts_partname_scan_when_by_name_is_absent(self) -> None:
        text = """
A90D4A_BEGIN
no_format_performed=1
no_mount_performed=1
no_flash_performed=1
target_by_name=/dev/block/by-name/userdata
target_real=
target_block=
__A90D4A_USERDATA_SCAN__
scan_block=sda33
scan_node=/dev/block/sda33
scan_node_exists=0
scan_uevent_DEVNAME=sda33
scan_uevent_PARTNAME=userdata
scan_size_sectors=231577432
scan_dev=259:27
scan_ro=0
__A90D4A_BY_NAME__
__A90D4A_MOUNTS__
/dev/block/mmcblk0p1 /mnt/sdext ext4 rw 0 0
__A90D4A_DF_K__
Filesystem 1K-blocks Used Available Use% Mounted on
/dev/block/mmcblk0p1 61407232 12750000 48600000 21% /mnt/sdext
__A90D4A_APPLETS__
df
grep
mknod
mount
readlink
sha256sum
switch_root
tar
__A90D4A_FILESYSTEMS__
	ext4
"""
        raw = {
            "baseline_ok": True,
            "device_observation": {"text": text},
            "host_artifacts": {
                "rollback_images": {
                    "v2321": {"exists": True, "sha256_match": True},
                    "v2237": {"exists": True, "sha256_match": True},
                    "v48": {"exists": True},
                },
                "d3_source_image": {"exists": True, "sha256_match": True},
                "d3_source_rootfs": {"exists": True, "sbin_init_exists": True},
                "d3b_report": {
                    "exists": True,
                    "switchroot_pass_evidence": True,
                    "twrp_recovery_evidence": True,
                },
                "adb_devices": {"recovery_currently_connected": False},
            },
        }

        summary = d4a.classify(raw)

        self.assertTrue(summary["preflight_ok"])
        self.assertEqual(summary["target"]["source"], "partname-scan")
        self.assertEqual(summary["target"]["realpath"], "/dev/block/sda33")
        self.assertFalse(summary["target"]["node_exists"])
        self.assertFalse(summary["target"]["by_name_present"])
        self.assertEqual(summary["d4b_must_materialize"], ["userdata-block-node"])

    def test_classify_blocks_forbidden_collision(self) -> None:
        raw = {
            "baseline_ok": True,
            "device_observation": {
                "text": """
no_format_performed=1
no_mount_performed=1
no_flash_performed=1
target_real=/dev/block/sda33
target_block=sda33
target_uevent_DEVNAME=sda33
target_uevent_PARTNAME=userdata
target_size_sectors=244140625
target_ro=0
__A90D4A_USERDATA_SCAN__
scan_block=sda33
__A90D4A_BY_NAME__
byname_userdata=/dev/block/sda33
byname_efs=/dev/block/sda33
__A90D4A_MOUNTS__
__A90D4A_APPLETS__
df
grep
 mknod
mount
readlink
sha256sum
switch_root
tar
mkfs.ext4
__A90D4A_FILESYSTEMS__
	ext4
"""
            },
            "host_artifacts": {
                "rollback_images": {
                    "v2321": {"exists": True, "sha256_match": True},
                    "v2237": {"exists": True, "sha256_match": True},
                    "v48": {"exists": True},
                },
                "d3_source_image": {"exists": True, "sha256_match": True},
                "d3_source_rootfs": {"exists": True, "sbin_init_exists": True},
                "d3b_report": {
                    "exists": True,
                    "switchroot_pass_evidence": True,
                    "twrp_recovery_evidence": True,
                },
                "adb_devices": {"recovery_currently_connected": False},
            },
        }

        summary = d4a.classify(raw)

        self.assertFalse(summary["preflight_ok"])
        self.assertIn("userdata-target-identity-check-failed", summary["blockers"])
        self.assertEqual(summary["forbidden_collision"], {"efs": "/dev/block/sda33"})


if __name__ == "__main__":
    unittest.main()
