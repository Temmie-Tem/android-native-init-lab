from __future__ import annotations

import unittest

from _loader import load_script


d1 = load_script("workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py")


class ServerDistroD1ChrootMvpTests(unittest.TestCase):
    def test_relative_run_dir_normalizes_under_repo_root(self) -> None:
        run_dir = d1.normalize_run_dir(d1.Path("workspace/private/runs/server-distro/example"))

        self.assertTrue(run_dir.is_absolute())
        self.assertEqual(
            run_dir,
            d1.REPO_ROOT / "workspace/private/runs/server-distro/example",
        )

    def test_d1_proof_script_is_sd_only_and_cleans_up_loop_mount(self) -> None:
        script = d1.d1_proof_script(
            "/mnt/sdext/a90/runtime/debian.img",
            "/mnt/sdext/a90/runtime/distro-root",
        )

        self.assertIn("A90D1_CHROOT_BEGIN", script)
        self.assertIn("A90D1_CHROOT_DONE", script)
        self.assertIn("/bin/busybox chroot", script)
        self.assertIn("/bin/busybox losetup \"$LOOP\" \"$IMG\"", script)
        self.assertIn("/bin/busybox mount -t ext4 -o rw \"$LOOP\" \"$MNT\"", script)
        self.assertIn("/bin/busybox umount \"$MNT\"", script)
        self.assertIn("/bin/busybox losetup -d \"$LOOP\"", script)
        self.assertIn("/bin/busybox rm -f \"$LOOP\"", script)
        self.assertIn("cleanup_mount_absent=1", script)
        self.assertIn("cleanup_loop_node_absent=1", script)
        self.assertNotIn("/dev/block/sda33", script)
        self.assertNotIn("mkfs", script)
        self.assertNotIn(" userdata", script)

    def test_parse_proof_extracts_chroot_and_cleanup_markers(self) -> None:
        text = """
A90D1_BEGIN
A90D1 loop_major=7
A90D1 loop_node_created=1
A90D1 mounted=1
A90D1_CHROOT_BEGIN
debian_version=12.5
kernel=Linux a90 4.14
stage_marker=present
A90D1_CHROOT_DONE
A90D1 cleanup_mount_absent=1
A90D1 cleanup_loop_node_absent=1
A90D1_DONE
"""
        parsed = d1.parse_proof(text)

        self.assertTrue(parsed["chroot_begin"])
        self.assertTrue(parsed["chroot_done"])
        self.assertTrue(parsed["done"])
        self.assertTrue(parsed["mount_cleanup_ok"])
        self.assertTrue(parsed["loop_cleanup_ok"])
        self.assertTrue(parsed["stage_marker_present"])
        self.assertEqual(parsed["debian_version"], "12.5")
        self.assertEqual(parsed["loop_major"], "7")
        self.assertTrue(parsed["loop_node_created"])


if __name__ == "__main__":
    unittest.main()
