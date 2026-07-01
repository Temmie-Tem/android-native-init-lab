"""Fault-injection tests for the fail-closed boot-target guard.

Covers the Codex-review sharpest-test set: every wrong/forbidden/mismatched target and the TOCTOU,
concurrency, unconfirmed-pin, forbidden-rdev, and diskseq cases must refuse BEFORE any write is
authorized. Only the exact pinned, auditor-confirmed boot partition may be write-authorized.
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
    pin_is_confirmed,
)

# Codex note: live evidence has sda24 as rdev 259:8 (not 8:24); the auditor is the true source.
BOOT_MAJOR, BOOT_MINOR = 259, 8
BOOT_CANON = "/dev/block/sda24"
# A fully auditor-confirmed pin (what a WRITE path requires).
CONFIRMED_PIN = BootTargetPin(canonical_path=BOOT_CANON, rdev_major=BOOT_MAJOR, rdev_minor=BOOT_MINOR)


def boot_identity(**over):
    base = dict(canonical_path=BOOT_CANON, rdev_major=BOOT_MAJOR, rdev_minor=BOOT_MINOR,
                partname="boot", size_bytes=BOOT_PARTITION_SIZE_BYTES, is_block=True)
    base.update(over)
    return BlockIdentity(**base)


class HappyPathTests(unittest.TestCase):
    def test_correct_boot_accepts_with_unconfirmed_pin(self):
        # evaluate (auditor/discovery mode) accepts on attributes; write mode does NOT (see below).
        self.assertTrue(evaluate_boot_target(boot_identity()).ok)

    def test_correct_boot_accepts_with_confirmed_pin(self):
        self.assertTrue(evaluate_boot_target(boot_identity(), CONFIRMED_PIN).ok)


class FaultInjectionRefusals(unittest.TestCase):
    def test_not_a_block_device(self):
        self.assertFalse(evaluate_boot_target(boot_identity(is_block=False)).ok)

    def test_empty_partname(self):
        self.assertFalse(evaluate_boot_target(boot_identity(partname="")).ok)

    def test_whitespace_only_partname(self):
        self.assertFalse(evaluate_boot_target(boot_identity(partname="   \n")).ok)

    def test_wrong_partname_userdata(self):
        r = evaluate_boot_target(boot_identity(partname="userdata"))
        self.assertFalse(r.ok)

    def test_wrong_partname_system(self):
        self.assertFalse(evaluate_boot_target(boot_identity(partname="system")).ok)

    def test_prefix_names_boot_a_and_recovery(self):
        for name in ("boot_a", "boot_b", "recovery", "recovery_a"):
            self.assertFalse(evaluate_boot_target(boot_identity(partname=name)).ok,
                             f"{name!r} must be refused (not exactly 'boot')")

    def test_numeric_partnames(self):
        for name in ("24", "0", "8"):
            self.assertFalse(evaluate_boot_target(boot_identity(partname=name)).ok)

    def test_every_forbidden_partname_refuses(self):
        for name in FORBIDDEN_PARTNAMES:
            self.assertFalse(evaluate_boot_target(boot_identity(partname=name)).ok,
                             f"{name!r} must be refused")

    def test_forbidden_partname_case_insensitive(self):
        self.assertFalse(evaluate_boot_target(boot_identity(partname="MODEM")).ok)
        self.assertFalse(evaluate_boot_target(boot_identity(partname="VBMeta")).ok)

    def test_wrong_size(self):
        r = evaluate_boot_target(boot_identity(size_bytes=BOOT_PARTITION_SIZE_BYTES - 4096))
        self.assertFalse(r.ok)

    def test_wrong_major_minor_when_pinned(self):
        self.assertFalse(evaluate_boot_target(boot_identity(rdev_minor=40), CONFIRMED_PIN).ok)
        self.assertFalse(evaluate_boot_target(boot_identity(rdev_major=253), CONFIRMED_PIN).ok)

    def test_wrong_canonical_path_when_pinned(self):
        self.assertFalse(
            evaluate_boot_target(boot_identity(canonical_path="/dev/block/sda30"), CONFIRMED_PIN).ok)

    def test_forbidden_rdev_set(self):
        # numeric denylist (e.g. modem's rdev) refuses regardless of PARTNAME
        pin = BootTargetPin(canonical_path=BOOT_CANON, rdev_major=BOOT_MAJOR, rdev_minor=BOOT_MINOR,
                            forbidden_rdevs=frozenset({(259, 20)}))
        self.assertFalse(
            evaluate_boot_target(boot_identity(rdev_minor=20, partname="boot"), pin).ok)

    def test_diskseq_mismatch_when_pinned(self):
        pin = BootTargetPin(canonical_path=BOOT_CANON, rdev_major=BOOT_MAJOR, rdev_minor=BOOT_MINOR,
                            diskseq=7)
        self.assertFalse(evaluate_boot_target(boot_identity(diskseq=9), pin).ok)
        self.assertTrue(evaluate_boot_target(boot_identity(diskseq=7), pin).ok)


class WriteAuthorizationTests(unittest.TestCase):
    """The Codex sharpest case: a write path must NEVER accept an unconfirmed pin, even on a
    perfect-looking PARTNAME=boot / 64 MiB node on the wrong disk."""

    def test_pin_is_confirmed_helper(self):
        self.assertFalse(pin_is_confirmed(BootTargetPin()))
        self.assertTrue(pin_is_confirmed(CONFIRMED_PIN))

    def test_write_refuses_unconfirmed_pin_even_if_attrs_perfect(self):
        # PARTNAME=boot, 64 MiB, but on /dev/block/dm-0 with a DEFAULT (unconfirmed) pin -> REFUSE
        fake = boot_identity(canonical_path="/dev/block/dm-0", rdev_major=253, rdev_minor=0)
        r = authorize_write(fake, fake)  # default pin unconfirmed, require_confirmed_pin=True
        self.assertFalse(r.ok)
        self.assertIn("confirmed pin", r.reason)

    def test_write_refuses_confirmed_pin_but_wrong_disk(self):
        fake = boot_identity(canonical_path="/dev/block/dm-0", rdev_major=253, rdev_minor=0)
        self.assertFalse(authorize_write(fake, fake, CONFIRMED_PIN).ok)

    def test_write_accepts_confirmed_pin_matching_identity(self):
        good = boot_identity()
        self.assertTrue(authorize_write(good, good, CONFIRMED_PIN).ok)

    def test_no_confirmed_pin_bypass_parameter_exists(self):
        # The require_confirmed_pin override was removed entirely (Codex review 3, P2). Passing it
        # must raise rather than silently authorize an unconfirmed write.
        good = boot_identity()
        with self.assertRaises(TypeError):
            authorize_write(good, good, require_confirmed_pin=False)  # type: ignore[call-arg]


class ToctouTests(unittest.TestCase):
    def test_swap_to_forbidden_between_check_and_write(self):
        good = boot_identity()
        swapped = boot_identity(partname="modem", canonical_path="/dev/block/sda40", rdev_minor=40)
        self.assertFalse(authorize_write(good, swapped, CONFIRMED_PIN).ok)

    def test_subtle_rdev_swap_same_partname(self):
        good = boot_identity()
        swapped = boot_identity(rdev_minor=99, canonical_path="/dev/block/sda99")
        r = authorize_write(good, swapped, CONFIRMED_PIN)
        self.assertFalse(r.ok)
        self.assertIn("TOCTOU", r.reason)

    def test_identical_identity_authorizes(self):
        good = boot_identity()
        self.assertTrue(authorize_write(good, good, CONFIRMED_PIN).ok)

    def test_open_identity_already_bad_refuses_before_write(self):
        bad = boot_identity(partname="vbmeta")
        self.assertFalse(authorize_write(bad, bad, CONFIRMED_PIN).ok)


class ConcurrencyTests(unittest.TestCase):
    def test_second_concurrent_claim_refused(self):
        with BootFlashClaim():
            with self.assertRaises(BootFlashBusy):
                with BootFlashClaim():
                    pass

    def test_claim_released_after_use(self):
        with BootFlashClaim():
            pass
        with BootFlashClaim():
            pass


if __name__ == "__main__":
    unittest.main()
