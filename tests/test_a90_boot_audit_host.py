"""Tests for the host side of the read-only boot-target auditor (parse + assess).

Covers Codex review 3 (P4) adversarial cases: duplicate keys, injected lines outside the block,
trailing records after `end`, truncated output, wrong-rdev sysfs, unresolved canonical,
non-authoritative targets, and read-failure — none may produce a confirmed write pin.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "workspace", "public", "src", "scripts", "revalidation"))

from a90_boot_audit_host import (  # noqa: E402
    assess,
    audit_to_identity,
    parse_audit_output,
    pin_allowed,
    proposed_pin,
)
from a90_boot_target_guard import evaluate_boot_target, pin_is_confirmed  # noqa: E402

GOOD = """
A90BOOTAUDIT begin
A90BOOTAUDIT target=/dev/block/by-name/boot
A90BOOTAUDIT authoritative=1
A90BOOTAUDIT canonical=/dev/block/sda24
A90BOOTAUDIT open=ok
A90BOOTAUDIT is_block=1
A90BOOTAUDIT rdev=259:8
A90BOOTAUDIT size_bytes=67108864
A90BOOTAUDIT logical_sector=4096
A90BOOTAUDIT physical_sector=4096
A90BOOTAUDIT read=ok bytes=4096
A90BOOTAUDIT sysfs=/sys/dev/block/259:8
A90BOOTAUDIT partname=boot
A90BOOTAUDIT diskseq=12
A90BOOTAUDIT sysfs_sectors=131072
A90BOOTAUDIT end rc=0
"""

OPEN_FAIL = """
A90BOOTAUDIT begin
A90BOOTAUDIT target=/dev/block/by-name/boot
A90BOOTAUDIT authoritative=1
A90BOOTAUDIT canonical=unresolved errno=22
A90BOOTAUDIT open=fail errno=13 (Permission denied)
A90BOOTAUDIT end rc=-13
"""

FORBIDDEN = GOOD.replace("partname=boot", "partname=modem")


class ParseTests(unittest.TestCase):
    def test_parse_keys(self):
        p = parse_audit_output(GOOD)
        self.assertEqual(p["open"], "ok")
        self.assertEqual(p["rdev"], "259:8")
        self.assertEqual(p["size_bytes"], "67108864")
        self.assertEqual(p["partname"], "boot")
        self.assertEqual(p["diskseq"], "12")
        self.assertEqual(p["authoritative"], "1")
        self.assertEqual(p["_end_rc"], 0)

    def test_identity_fields(self):
        ident = audit_to_identity(parse_audit_output(GOOD))
        self.assertEqual((ident.rdev_major, ident.rdev_minor), (259, 8))
        self.assertEqual(ident.size_bytes, 67108864)
        self.assertTrue(ident.is_block)
        self.assertEqual(ident.diskseq, 12)


class AdversarialParseTests(unittest.TestCase):
    def test_duplicate_key_rejected(self):
        injected = GOOD.replace(
            "A90BOOTAUDIT rdev=259:8",
            "A90BOOTAUDIT rdev=259:8\nA90BOOTAUDIT rdev=253:0")
        with self.assertRaises(ValueError):
            parse_audit_output(injected)

    def test_line_before_begin_rejected(self):
        injected = "A90BOOTAUDIT rdev=253:0\n" + GOOD
        with self.assertRaises(ValueError):
            parse_audit_output(injected)

    def test_line_after_end_rejected(self):
        injected = GOOD + "A90BOOTAUDIT canonical=/dev/block/dm-0\n"
        with self.assertRaises(ValueError):
            parse_audit_output(injected)

    def test_second_begin_rejected(self):
        with self.assertRaises(ValueError):
            parse_audit_output(GOOD + GOOD)

    def test_truncated_no_end_rejected(self):
        truncated = GOOD.replace("A90BOOTAUDIT end rc=0\n", "")
        with self.assertRaises(ValueError):
            parse_audit_output(truncated)

    def test_missing_begin_rejected(self):
        with self.assertRaises(ValueError):
            parse_audit_output("A90BOOTAUDIT end rc=0\n")

    def test_replayed_fields_outside_block_are_rejected(self):
        # A synthetic replay of the good fields appended after the real end must not be absorbed.
        replay = GOOD + "A90BOOTAUDIT rdev=259:8\nA90BOOTAUDIT partname=boot\n"
        with self.assertRaises(ValueError):
            parse_audit_output(replay)


class IdentityCrossCheckTests(unittest.TestCase):
    def test_unresolved_canonical_rejected(self):
        with self.assertRaises(ValueError):
            audit_to_identity(parse_audit_output(OPEN_FAIL.replace(
                "open=fail errno=13 (Permission denied)", "open=ok\nA90BOOTAUDIT rdev=259:8\n"
                "A90BOOTAUDIT size_bytes=67108864\nA90BOOTAUDIT is_block=1")))

    def test_sysfs_rdev_mismatch_rejected(self):
        bad = GOOD.replace("sysfs=/sys/dev/block/259:8", "sysfs=/sys/dev/block/253:0")
        with self.assertRaises(ValueError):
            audit_to_identity(parse_audit_output(bad))

    def test_non_absolute_canonical_rejected(self):
        bad = GOOD.replace("canonical=/dev/block/sda24", "canonical=sda24")
        with self.assertRaises(ValueError):
            audit_to_identity(parse_audit_output(bad))


class AssessTests(unittest.TestCase):
    def test_good_boot_assessed_ok(self):
        r = assess(GOOD)
        self.assertTrue(r["ok"])
        self.assertTrue(r["evaluate_ok"])
        self.assertIsNotNone(r["proposed_pin"])

    def test_proposed_pin_is_confirmed_and_round_trips(self):
        ident = audit_to_identity(parse_audit_output(GOOD))
        pin = proposed_pin(ident)
        self.assertTrue(pin_is_confirmed(pin))
        self.assertTrue(evaluate_boot_target(ident, pin).ok)

    def test_open_fail_is_not_ok(self):
        r = assess(OPEN_FAIL)
        self.assertFalse(r["ok"])
        self.assertIn("open", r["error"])

    def test_forbidden_partname_refused(self):
        r = assess(FORBIDDEN)
        self.assertFalse(r["ok"])
        self.assertFalse(r["evaluate_ok"])
        self.assertIsNone(r["proposed_pin"])

    def test_non_authoritative_target_no_pin(self):
        # A read-only audit of a non-default target must never propose a write pin, even if the
        # attributes happen to look like the boot partition.
        na = GOOD.replace("authoritative=1", "authoritative=0")
        r = assess(na)
        self.assertIsNone(r["proposed_pin"])
        self.assertFalse(r["ok"])
        allowed, reason = pin_allowed(parse_audit_output(na), True)
        self.assertFalse(allowed)
        self.assertIn("authoritative", reason)

    def test_read_failure_no_pin(self):
        rf = GOOD.replace("read=ok bytes=4096", "read=fail errno=5 (I/O error)")
        r = assess(rf)
        self.assertIsNone(r["proposed_pin"])
        self.assertFalse(r["ok"])

    def test_injected_output_fails_assess(self):
        injected = GOOD + "A90BOOTAUDIT rdev=253:0\n"
        r = assess(injected)
        self.assertFalse(r["ok"])
        self.assertIn("parse", r["error"])


if __name__ == "__main__":
    unittest.main()
