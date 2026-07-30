#!/usr/bin/env python3
"""Focused tests for the P2.88 source/ELF post-build audit."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p288_candidate_static_checker as static_checker  # noqa: E402
import s22plus_fyg8_p288_postbuild_linked_audit as audit  # noqa: E402
import s22plus_fyg8_p288_source_contract as source_contract  # noqa: E402


class P288PostbuildLinkedAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = source_contract.generate(ROOT)["patch"]

    def test_production_validator_span_is_exact_and_complete(self):
        source = audit.production_validator_source(self.patch)
        self.assertEqual(
            source.count(b"s22_fyg8_e1_request_allowed("), 1
        )
        self.assertEqual(
            source.count(b"request->stage != sequence[ordinal]"), 1
        )
        self.assertEqual(
            source.count(b"request->item_index != expected_item"), 1
        )

    def test_host_native_pair_domain_is_exhaustive(self):
        result = audit.run_host_validator_tu(
            audit.host_validator_tu(self.patch)
        )
        self.assertEqual(result["checked_pairs"], 6_815_744)
        self.assertEqual(result["accepted_pairs"], 103)
        self.assertTrue(result["register_allocation_independent"])

    def test_host_native_rejects_production_pair_guard_mutation(self):
        tu = audit.host_validator_tu(self.patch)
        changed = tu.replace(
            b"request->item_index != expected_item",
            b"request->item_index == expected_item",
        )
        self.assertNotEqual(changed, tu)
        with self.assertRaisesRegex(
            audit.AuditError, "exhaustive evaluation failed"
        ):
            audit.run_host_validator_tu(changed)

    def test_direct_elf_table_bytes_match_without_objdump(self):
        expected = source_contract.linked_table_bytes()
        result = audit.verify_linked_table_data(
            self._tiny_tables_elf(expected), expected
        )
        self.assertEqual(
            result["symbols"]["s22_fyg8_e2_sequence"]["symbol_size"],
            103,
        )
        self.assertEqual(
            result["symbols"]["s22_fyg8_p288_detail_rules"]["symbol_size"],
            832,
        )
        self.assertTrue(result["objdump_text_not_used"])
        self.assertTrue(result["stage_and_item_bytes_equal_position_sequence"])
        self.assertTrue(
            result["kind_and_detail_rule_bytes_equal_source_contract"]
        )

    def test_direct_elf_table_comparison_rejects_data_drift(self):
        expected = source_contract.linked_table_bytes()
        changed = dict(expected)
        items = expected["s22_fyg8_e2_items"]
        changed["s22_fyg8_e2_items"] = (
            bytes([items[0] ^ 1]) + items[1:]
        )
        with self.assertRaisesRegex(
            audit.AuditError,
            "linked table bytes differ: s22_fyg8_e2_items",
        ):
            audit.verify_linked_table_data(
                self._tiny_tables_elf(changed), expected
            )

    @staticmethod
    def _tiny_tables_elf(tables: dict[str, bytes]) -> bytes:
        declarations = []
        for symbol_name in audit.LINKED_DATA_SYMBOLS:
            body = ", ".join(str(value) for value in tables[symbol_name])
            declarations.append(
                "__attribute__((used)) "
                f"const uint8_t {symbol_name}[] = {{{body}}};"
            )
        source = "\n".join(
            ("#include <stdint.h>", *declarations, "int main(void) { return 0; }")
        )
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source_path = work / "tables.c"
            binary = work / "tables"
            source_path.write_text(source, encoding="ascii")
            subprocess.run(
                ("cc", "-std=c11", "-O2", str(source_path), "-o", str(binary)),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            return binary.read_bytes()

    def test_static_checker_dispatches_fresh_postbuild_replay(self):
        static_checker._configure()
        self.assertIs(
            static_checker.base.verify_repro,
            static_checker.verify_repro,
        )
        self.assertEqual(audit.ADAPTER_ID, audit.legacy.ADAPTER_ID)
        self.assertNotEqual(audit.IMPLEMENTATION_ID, audit.ADAPTER_ID)


if __name__ == "__main__":
    unittest.main()
