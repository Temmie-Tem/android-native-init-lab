#!/usr/bin/env python3
"""Focused tests for the P2.88 post-build switch-table audit."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p288_candidate_static_checker as static_checker  # noqa: E402
import s22plus_fyg8_p288_postbuild_linked_audit as audit  # noqa: E402


REQUEST_ALLOWED = """
ffffffc008020580: 39401400 ldrb w0, [x0, #5]
ffffffc008020590: 51000409 sub w9, w0, #0x1
ffffffc008020594: 7100093f cmp w9, #0x2
ffffffc008020598: 54000408 b.hi ffffffc008020618
ffffffc00802059c: 93401d28 sxtb x8, w9
ffffffc0080205a0: f000f589 adrp x9, ffffffc009ed3000 <nearby>
ffffffc0080205a4: 9115c129 add x9, x9, #0x570
ffffffc0080205a8: f8687936 ldr x22, [x9, x8, lsl #3]
ffffffc0080205ac: eb1502df cmp x22, x21
ffffffc0080205b0: 54000329 b.ls ffffffc008020614
ffffffc0080205b4: f000f589 adrp x9, ffffffc009ed3000 <nearby>
ffffffc0080205b8: 91162129 add x9, x9, #0x588
ffffffc0080205bc: f8687928 ldr x8, [x9, x8, lsl #3]
ffffffc0080205c0: 39401a83 ldrb w3, [x20, #6]
ffffffc0080205c4: 38756908 ldrb w8, [x8, x21]
ffffffc0080205c8: 6b08007f cmp w3, w8
ffffffc0080205cc: 54000241 b.ne ffffffc008020614
ffffffc008020628: 54000101 b.ne ffffffc008020648
"""


class P288PostbuildLinkedAuditTests(unittest.TestCase):
    def test_switch_structure_extracts_exact_bases_and_guards(self):
        value = audit._switch_table_structure(REQUEST_ALLOWED)
        self.assertEqual(value["count_base"], 0xFFFFFFC009ED3570)
        self.assertEqual(value["pointer_base"], 0xFFFFFFC009ED3588)
        self.assertEqual(value["profile_domain"], [1, 3])
        self.assertTrue(value["count_guard_before_pointer_load"])
        self.assertTrue(value["generation_indexed_byte_load"])
        self.assertTrue(value["request_stage_compare"])

    def test_switch_structure_rejects_profile_domain_drift(self):
        changed = REQUEST_ALLOWED.replace("cmp w9, #0x2", "cmp w9, #0x3")
        with self.assertRaisesRegex(
            audit.AuditError, "profile upper bound"
        ):
            audit._switch_table_structure(changed)

    def test_switch_structure_rejects_missing_count_guard(self):
        changed = REQUEST_ALLOWED.replace(
            "b.ls ffffffc008020614", "b.hi ffffffc008020614"
        )
        with self.assertRaisesRegex(
            audit.AuditError, "generation/count rejection"
        ):
            audit._switch_table_structure(changed)

    def test_exact_values_bind_e2_pointer_and_count(self):
        structure = audit._switch_table_structure(REQUEST_ALLOWED)
        symbols = (0x1000, 0x2000, 0x3000)
        value = audit._validate_switch_table_values(
            structure, (9, 15, 103), symbols, symbols
        )
        self.assertTrue(value["exact_e2_sequence_target"])
        self.assertEqual(value["e2_profile_index"], 2)
        self.assertEqual(value["e2_count"], 103)

    def test_exact_values_reject_pointer_redirection(self):
        structure = audit._switch_table_structure(REQUEST_ALLOWED)
        with self.assertRaisesRegex(
            audit.AuditError, "pointer switch differs"
        ):
            audit._validate_switch_table_values(
                structure,
                (9, 15, 103),
                (0x1000, 0x2000, 0x4000),
                (0x1000, 0x2000, 0x3000),
            )

    def test_exact_values_reject_e2_count_drift(self):
        structure = audit._switch_table_structure(REQUEST_ALLOWED)
        with self.assertRaisesRegex(
            audit.AuditError, "count switch differs"
        ):
            audit._validate_switch_table_values(
                structure,
                (9, 15, 102),
                (0x1000, 0x2000, 0x3000),
                (0x1000, 0x2000, 0x3000),
            )

    def test_static_checker_dispatches_fresh_postbuild_replay(self):
        static_checker._configure()
        self.assertIs(
            static_checker.base.verify_repro,
            static_checker.verify_repro,
        )
        self.assertEqual(audit.ADAPTER_ID, audit.legacy.ADAPTER_ID)
        self.assertNotEqual(
            audit.IMPLEMENTATION_ID, audit.ADAPTER_ID
        )


if __name__ == "__main__":
    unittest.main()
