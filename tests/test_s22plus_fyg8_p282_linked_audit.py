from __future__ import annotations

import subprocess
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p280_linked_audit as p280_linked  # noqa: E402
import s22plus_fyg8_p280_source_contract as p280  # noqa: E402
import s22plus_fyg8_p282_linked_audit as linked  # noqa: E402
import s22plus_fyg8_p282_source_contract as p282  # noqa: E402


class P282LinkedAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addresses = {
            "s22_fyg8_e2_sequence": 0x200100,
            "s22_fyg8_e2_items": 0x200200,
            "s22_fyg8_e2_kinds": 0x200300,
            "s22_fyg8_e2_classifier_stages": 0x200400,
            "s22_fyg8_e2_classifier_details": 0x200500,
            "s22_fyg8_p282_inherited_role_details": 0x200600,
            "s22_fyg8_p282_details": 0x200700,
        }
        self.disassembly = {
            "s22_fyg8_e1_expected_item": """
1000: 90000008 adrp x8, 200000
1004: 91080108 add x8, x8, #0x200
1008: 38616908 ldrb w8, [x8, x1]
100c: d65f03c0 ret
""",
            "s22_fyg8_e1_detail_allowed": """
1100: 90000008 adrp x8, 200000
1104: 91040108 add x8, x8, #0x100
1108: 38616908 ldrb w8, [x8, x1]
110c: 90000009 adrp x9, 200000
1110: 910c0129 add x9, x9, #0x300
1114: 38616929 ldrb w9, [x9, x1]
1118: 9000000a adrp x10, 200000
111c: 9110014a add x10, x10, #0x400
1120: 08dffd4a ldarb w10, [x10]
1124: 9000000b adrp x11, 200000
1128: 9114016b add x11, x11, #0x500
112c: 48dffd6b ldarh w11, [x11]
1130: 94000001 bl 1600 <s22_fyg8_p282_detail_allowed>
1134: 94000002 bl 1700 <s22_fyg8_p282_tuple_allowed>
1138: d65f03c0 ret
""",
            "s22_fyg8_p282_detail_allowed": """
1600: 90000008 adrp x8, 200000
1604: 91180108 add x8, x8, #0x600
1608: 78616908 ldrh w8, [x8, x1]
160c: 90000009 adrp x9, 200000
1610: 911c0129 add x9, x9, #0x700
1614: 78616929 ldrh w9, [x9, x1]
1618: d65f03c0 ret
""",
            "s22_fyg8_p282_tuple_allowed": """
1700: 7102481f cmp w0, #0x92
1704: 514d0048 sub w8, w2, #0xd00
1708: 7108d91f cmp w8, #0x236
170c: d65f03c0 ret
""",
            "s22_fyg8_e1_request_allowed": """
1200: 94000001 bl 1000 <s22_fyg8_e1_expected_item>
1204: 94000002 bl 1100 <s22_fyg8_e1_detail_allowed>
1208: d65f03c0 ret
""",
            "s22_fyg8_e1_write": """
1300: 94000001 bl 1200 <s22_fyg8_e1_request_allowed>
1304: 360000e0 tbz w0, #0, 1320 <s22_fyg8_e1_write+0x20>
1308: 94000002 bl 1400 <s22_fyg8_e1_head>
130c: aa0003f3 mov x19, x0
1310: b9000261 str w1, [x19]
1314: 94000003 bl 1500 <__pi___flush_dcache_area>
1318: d2800400 mov x0, #0x20
131c: d65f03c0 ret
1320: 92800420 mov x0, #0xffffffffffffffde
1324: d65f03c0 ret
""",
        }
        self.calls = {
            name: repro._calls(text)
            for name, text in self.disassembly.items()
        }

    def test_adapter_identity_and_exact_versioned_symbols(self):
        self.assertEqual(
            linked.EXPECTED_SOURCE_CONTRACT_ID, p282.CONTRACT_ID
        )
        self.assertEqual(
            linked.ADAPTER_ID, "s22plus-fyg8-p282-linked-audit-v1"
        )
        self.assertIn(
            "s22_fyg8_p282_detail_allowed",
            linked.LINKED_VALIDATOR_SYMBOLS,
        )
        self.assertIn(
            "s22_fyg8_p282_tuple_allowed",
            linked.LINKED_VALIDATOR_SYMBOLS,
        )

    def test_exact_p282_storage_is_four_byte_abi_without_padding(self):
        logical = p282.linked_table_bytes()
        physical = linked.linked_table_storage_bytes(logical)
        self.assertEqual(physical, logical)
        for name, layout in linked.P282_TABLE_LAYOUTS.items():
            with self.subTest(table=name):
                self.assertEqual(layout.logical_stride, 4)
                self.assertEqual(layout.physical_stride, 4)
                self.assertEqual(len(physical[name]), layout.physical_size)
        normalized, evidence = linked.normalize_linked_table_storage(
            physical, logical
        )
        self.assertEqual(normalized, logical)
        self.assertTrue(evidence["p280_style_tail_padding_absent"])
        self.assertTrue(evidence["verified"])

    def test_rejects_legacy_logical_to_physical_padding_mutation(self):
        logical = p282.linked_table_bytes()
        physical = linked.linked_table_storage_bytes(logical)
        name = linked.P282_DETAIL_TABLE
        value = physical[name]
        padded = b"".join(
            value[offset : offset + 4] + b"\0\0"
            for offset in range(0, len(value), 4)
        )
        with self.assertRaisesRegex(
            linked.AuditError, "physical table size differs"
        ):
            linked.normalize_linked_table_storage(
                {**physical, name: padded}, logical
            )

    def test_rejects_exact_table_byte_mutation(self):
        logical = p282.linked_table_bytes()
        physical = linked.linked_table_storage_bytes(logical)
        name = linked.P282_INHERITED_DETAIL_TABLE
        changed = bytearray(physical[name])
        changed[0] ^= 1
        with self.assertRaisesRegex(
            linked.AuditError, "physical table bytes differ"
        ):
            linked.normalize_linked_table_storage(
                {**physical, name: bytes(changed)}, logical
            )

    def test_validator_loads_all_p282_tables_and_tuple_dispatch(self):
        result = linked.audit_linked_validator(
            self.disassembly, self.calls, self.addresses
        )
        self.assertTrue(result["verified"])
        self.assertTrue(result["p282_generated_sequence_loaded"])
        self.assertTrue(result["p282_generated_items_loaded"])
        self.assertTrue(result["p282_generated_kinds_loaded"])
        self.assertTrue(result["p282_inherited_role_details_loaded"])
        self.assertTrue(result["p282_exact_c_details_loaded"])
        self.assertEqual(result["p282_exact_c_detail_count"], 46)
        self.assertEqual(
            result["p282_tuple_dispatch"]["tuple_count"], 567
        )
        self.assertTrue(
            result["p282_tuple_dispatch"]["range_dispatch_verified"]
        )

    def test_rejects_sequence_load_from_wrong_table(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_detail_allowed"] = changed[
            "s22_fyg8_e1_detail_allowed"
        ].replace("#0x100", "#0x101")
        with self.assertRaisesRegex(
            linked.AuditError, "s22_fyg8_e2_sequence"
        ):
            linked.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_missing_exact_detail_helper_dispatch(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_detail_allowed"] = changed[
            "s22_fyg8_e1_detail_allowed"
        ].replace(
            "1130: 94000001 bl 1600 <s22_fyg8_p282_detail_allowed>",
            "1130: d503201f nop",
        )
        calls = {
            name: repro._calls(text) for name, text in changed.items()
        }
        with self.assertRaisesRegex(
            linked.AuditError, "exact-detail dispatch"
        ):
            linked.audit_linked_validator(changed, calls, self.addresses)

    def test_rejects_tuple_range_mutation(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_p282_tuple_allowed"] = changed[
            "s22_fyg8_p282_tuple_allowed"
        ].replace("#0x236", "#0x235")
        with self.assertRaisesRegex(
            linked.AuditError, "tuple range dispatch differs"
        ):
            linked.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_inherited_or_c_detail_table_load_mutation(self):
        for token, table in (
            ("#0x600", linked.P282_INHERITED_DETAIL_TABLE),
            ("#0x700", linked.P282_DETAIL_TABLE),
        ):
            with self.subTest(table=table):
                changed = dict(self.disassembly)
                changed["s22_fyg8_p282_detail_allowed"] = changed[
                    "s22_fyg8_p282_detail_allowed"
                ].replace(token, f"#0x{int(token[1:], 16) + 1:x}")
                with self.assertRaisesRegex(linked.AuditError, table):
                    linked.audit_linked_validator(
                        changed, self.calls, self.addresses
                    )

    def test_gnu_aarch64_tool_gate_accepts_only_cross_binutils(self):
        versions = (
            subprocess.CompletedProcess(
                [], 0, "GNU nm (GNU Binutils for Debian) 2.40\n"
            ),
            subprocess.CompletedProcess(
                [], 0, "GNU objdump (GNU Binutils for Debian) 2.40\n"
            ),
        )
        args = Namespace(
            nm=Path("/usr/bin/aarch64-linux-gnu-nm"),
            objdump=Path("/usr/bin/aarch64-linux-gnu-objdump"),
        )
        with mock.patch.object(
            linked.subprocess, "run", side_effect=versions
        ):
            result = linked.require_gnu_aarch64_tools(args)
        self.assertIn("GNU nm", result["nm"])
        self.assertIn("GNU objdump", result["objdump"])

    def test_gnu_tool_gate_rejects_llvm(self):
        args = Namespace(
            nm=Path("/opt/llvm/bin/llvm-nm"),
            objdump=Path("/opt/llvm/bin/llvm-objdump"),
        )
        with self.assertRaisesRegex(linked.AuditError, "LLVM nm"):
            linked.require_gnu_aarch64_tools(args)

    def test_central_storage_owner_preserves_p280_and_p282_layouts(self):
        p280_logical, p280_storage = repro._linked_table_storage_bytes(
            p280, p280_linked
        )
        self.assertEqual(
            len(p280_logical[p280_linked.P280_DETAIL_TABLE]),
            len(p280.spec.DIAGNOSTIC_DETAILS)
            * p280_linked.P280_DETAIL_LOGICAL_STRIDE,
        )
        self.assertEqual(
            len(p280_storage[p280_linked.P280_DETAIL_TABLE]),
            len(p280.spec.DIAGNOSTIC_DETAILS)
            * p280_linked.P280_DETAIL_STORAGE_STRIDE,
        )
        p282_logical, p282_storage = repro._linked_table_storage_bytes(
            p282, linked
        )
        self.assertEqual(p282_storage, p282_logical)


if __name__ == "__main__":
    unittest.main()
