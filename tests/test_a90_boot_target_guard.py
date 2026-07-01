"""Fault-injection tests for the fail-closed boot-target guard.

Covers the Codex-review sharpest-test set: every wrong/forbidden/mismatched target and the TOCTOU
and concurrency cases must refuse BEFORE any write is authorized. Only the exact pinned boot
partition may be accepted.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "workspace", "public", "src", "scripts", "revalidation"))

from a90_boot_target_guard import (  # noqa: E402
    BOOT_PARTITION_SIZE_BYTES,
    FORBIDDEN_PARTNAMES,
    BlockIdentity,
    BootFlashBusy,
    BootFlashClaim,
    BootTargetPin,
    authorize_write,
    evaluate_boot_target,
)


def boot_identity(**over):
    base = dict(canonical_path="/dev/block/sda24", rdev_major=8, rdev_minor=24,
                partname="boot", size_bytes=BOOT_PARTITION_SIZE_BYTES, is_block=True)
    base.update(over)
    return BlockIdentity(**base)


class HappyPathTests(unittest.TestCase):
    def test_correct_boot_accepts_with_unconfirmed_pin(self):
        self.assertTrue(evaluate_boot_target(boot_identity()).ok)

    def test_correct_boot_accepts_with_confirmed_pin(self):
        pin = BootTargetPin(canonical_path="/dev/block/sda24", rdev_major=8, rdev_minor=24)
        self.assertTrue(evaluate_boot_target(boot_identity(), pin).ok)


class FaultInjectionRefusals(unittest.TestCase):
    def test_not_a_block_device(self):
        self.assertFalse(evaluate_boot_target(boot_identity(is_block=False)).ok)

    def test_empty_partname(self):
        self.assertFalse(evaluate_boot_target(boot_identity(partname="")).ok)

    def test_wrong_partname_userdata(self):
        r = evaluate_boot_target(boot_identity(partname="userdata"))
        self.assertFalse(r.ok)
        self.assertIn("userdata", r.reason)

    def test_wrong_partname_system(self):
        self.assertFalse(evaluate_boot_target(boot_identity(partname="system")).ok)

    def test_every_forbidden_partname_refuses(self):
        for name in FORBIDDEN_PARTNAMES:
            r = evaluate_boot_target(boot_identity(partname=name))
            self.assertFalse(r.ok, f"{name!r} must be refused")

    def test_forbidden_partname_case_insensitive(self):
        self.assertFalse(evaluate_boot_target(boot_identity(partname="MODEM")).ok)
        self.assertFalse(evaluate_boot_target(boot_identity(partname="VBMeta")).ok)

    def test_wrong_size(self):
        r = evaluate_boot_target(boot_identity(size_bytes=BOOT_PARTITION_SIZE_BYTES - 4096))
        self.assertFalse(r.ok)
        self.assertIn("size", r.reason)

    def test_wrong_major_minor_when_pinned(self):
        pin = BootTargetPin(rdev_major=8, rdev_minor=24)
        # a partition named 'boot' but at a different device node (rdev) is refused
        self.assertFalse(evaluate_boot_target(boot_identity(rdev_minor=48), pin).ok)
        self.assertFalse(evaluate_boot_target(boot_identity(rdev_major=259), pin).ok)

    def test_wrong_canonical_path_when_pinned(self):
        pin = BootTargetPin(canonical_path="/dev/block/sda24")
        self.assertFalse(evaluate_boot_target(boot_identity(canonical_path="/dev/block/sda30"), pin).ok)


class ToctouTests(unittest.TestCase):
    def test_swap_to_forbidden_between_check_and_write(self):
        good = boot_identity()
        swapped = boot_identity(partname="modem", canonical_path="/dev/block/sda40", rdev_minor=40)
        r = authorize_write(good, swapped)
        self.assertFalse(r.ok)

    def test_subtle_rdev_swap_same_partname(self):
        # symlink swapped to a different device that still claims PARTNAME=boot -> identity differs
        good = boot_identity()
        swapped = boot_identity(rdev_minor=99, canonical_path="/dev/block/sda99")
        r = authorize_write(good, swapped)
        self.assertFalse(r.ok)
        self.assertIn("TOCTOU", r.reason)

    def test_identical_identity_authorizes(self):
        good = boot_identity()
        self.assertTrue(authorize_write(good, good).ok)

    def test_open_identity_already_bad_refuses_before_write(self):
        bad = boot_identity(partname="vbmeta")
        self.assertFalse(authorize_write(bad, bad).ok)


class ConcurrencyTests(unittest.TestCase):
    def test_second_concurrent_claim_refused(self):
        with BootFlashClaim():
            with self.assertRaises(BootFlashBusy):
                with BootFlashClaim():
                    pass

    def test_claim_released_after_use(self):
        with BootFlashClaim():
            pass
        # should be re-acquirable
        with BootFlashClaim():
            pass


if __name__ == "__main__":
    unittest.main()
