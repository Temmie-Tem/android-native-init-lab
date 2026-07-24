import sys
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p253_linked_audit as p253  # noqa: E402


class S22PlusFyg8P253LinkedAuditTest(unittest.TestCase):
    def setUp(self):
        self.addresses = {
            "s22_fyg8_e2_items": 0x20032F,
            "s22_fyg8_e2_classifier_stages": 0x20031E,
            "s22_fyg8_e2_classifier_details": 0x2002FC,
        }
        self.disassembly = {
            "s22_fyg8_e1_expected_item": """
1000: 90000008 adrp x8, 200000
1004: 910cbd08 add x8, x8, #0x32f
1008: 38616908 ldrb w8, [x8, x1]
""",
            "s22_fyg8_e1_detail_allowed": """
1100: 9000000a adrp x10, 200000
1104: 9000000b adrp x11, 200000
1108: 910bf14a add x10, x10, #0x2fc
110c: 910c796b add x11, x11, #0x31e
110e: aa1f03e8 mov x8, xzr
1110: 8b08016c add x12, x11, x8
1114: 08dffd8c ldarb w12, [x12]
1118: 48dffd4c ldarh w12, [x10]
""",
            "s22_fyg8_e1_request_allowed": """
1200: 94000001 bl 1000 <s22_fyg8_e1_expected_item>
1204: 94000002 bl 1100 <s22_fyg8_e1_detail_allowed>
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

    def test_accepts_actual_full_lto_acquire_load_lowering(self):
        result = p253.audit_linked_validator(
            self.disassembly, self.calls, self.addresses
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["audit_adapter"], p253.ADAPTER_ID)
        self.assertEqual(
            result["accepted_load_lowerings"]["classifier_stage"][0][
                "mnemonic"
            ],
            "ldarb",
        )
        self.assertEqual(
            result["accepted_load_lowerings"]["classifier_detail"][0][
                "mnemonic"
            ],
            "ldarh",
        )

    def test_rejects_wrong_table_address(self):
        changed = dict(self.addresses)
        changed["s22_fyg8_e2_classifier_stages"] += 1
        with self.assertRaisesRegex(p253.AuditError, "classifier_stage"):
            p253.audit_linked_validator(
                self.disassembly, self.calls, changed
            )

    def test_rejects_displaced_table_origin(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_expected_item"] = changed[
            "s22_fyg8_e1_expected_item"
        ].replace(
            "add x8, x8, #0x32f",
            "add x8, x8, #0x132f",
        )
        with self.assertRaisesRegex(p253.AuditError, "item table"):
            p253.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_intra_table_byte_displacement(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_expected_item"] = changed[
            "s22_fyg8_e1_expected_item"
        ].replace("#0x32f", "#0x330")
        with self.assertRaisesRegex(p253.AuditError, "item table"):
            p253.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_intra_table_halfword_displacement(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_detail_allowed"] = changed[
            "s22_fyg8_e1_detail_allowed"
        ].replace("#0x2fc", "#0x2fe")
        with self.assertRaisesRegex(p253.AuditError, "classifier_detail"):
            p253.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_caller_clobbered_table_origin(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_expected_item"] = changed[
            "s22_fyg8_e1_expected_item"
        ].replace(
            "1008: 38616908 ldrb",
            "1008: 94000001 bl 1800 <unknown_helper>\n"
            "100c: 38616908 ldrb",
        )
        with self.assertRaisesRegex(p253.AuditError, "item table"):
            p253.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_unreachable_table_origin(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_expected_item"] = (
            "0ff0: 14000008 b 1010 <done>\n"
            + changed["s22_fyg8_e1_expected_item"]
            + "1010: d65f03c0 ret\n"
        )
        with self.assertRaisesRegex(p253.AuditError, "item table"):
            p253.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_wrong_load_width(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_detail_allowed"] = changed[
            "s22_fyg8_e1_detail_allowed"
        ].replace("ldarh w12", "ldarb w12")
        with self.assertRaisesRegex(p253.AuditError, "classifier_detail"):
            p253.audit_linked_validator(changed, self.calls, self.addresses)

    def test_rejects_missing_request_call(self):
        changed = {name: list(value) for name, value in self.calls.items()}
        changed["s22_fyg8_e1_write"] = []
        with self.assertRaisesRegex(p253.AuditError, "does not call"):
            p253.audit_linked_validator(
                self.disassembly, changed, self.addresses
            )

    def test_rejects_wrong_validator_result_guard(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_write"] = changed[
            "s22_fyg8_e1_write"
        ].replace("tbz w0, #0", "tbz w1, #0")
        calls = dict(self.calls)
        calls["s22_fyg8_e1_write"] = repro._calls(
            changed["s22_fyg8_e1_write"]
        )
        with self.assertRaisesRegex(p253.AuditError, "branch on validator"):
            p253.audit_linked_validator(changed, calls, self.addresses)

    def test_rejects_retained_flush_before_guard(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_write"] = changed[
            "s22_fyg8_e1_write"
        ].replace(
            "1300: 94000001 bl 1200 <s22_fyg8_e1_request_allowed>",
            "12fc: 94000003 bl 1500 <__pi___flush_dcache_area>\n"
            "1300: 94000001 bl 1200 <s22_fyg8_e1_request_allowed>",
        )
        calls = dict(self.calls)
        calls["s22_fyg8_e1_write"] = repro._calls(
            changed["s22_fyg8_e1_write"]
        )
        with self.assertRaisesRegex(p253.AuditError, "does not dominate"):
            p253.audit_linked_validator(changed, calls, self.addresses)

    def test_rejects_retained_store_before_guard(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_write"] = changed[
            "s22_fyg8_e1_write"
        ].replace(
            "1300: 94000001 bl 1200 <s22_fyg8_e1_request_allowed>",
            "12f4: 94000002 bl 1400 <s22_fyg8_e1_head>\n"
            "12f8: aa0003f3 mov x19, x0\n"
            "12fc: b9000261 str w1, [x19]\n"
            "1300: 94000001 bl 1200 <s22_fyg8_e1_request_allowed>",
        )
        calls = dict(self.calls)
        calls["s22_fyg8_e1_write"] = repro._calls(
            changed["s22_fyg8_e1_write"]
        )
        with self.assertRaisesRegex(
            p253.AuditError, "retained writes|retained stores"
        ):
            p253.audit_linked_validator(changed, calls, self.addresses)

    def test_rejects_failure_path_without_negative_return(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_write"] = changed[
            "s22_fyg8_e1_write"
        ].replace(
            "mov x0, #0xffffffffffffffde",
            "mov x0, #0x0",
        )
        calls = dict(self.calls)
        calls["s22_fyg8_e1_write"] = repro._calls(
            changed["s22_fyg8_e1_write"]
        )
        with self.assertRaisesRegex(p253.AuditError, "return an error"):
            p253.audit_linked_validator(changed, calls, self.addresses)

    def test_rejects_failure_edge_rejoining_retained_store(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_write"] = changed[
            "s22_fyg8_e1_write"
        ].replace(
            "1320: 92800420 mov x0, #0xffffffffffffffde",
            "1320: 17fffffc b 1310 <s22_fyg8_e1_write+0x10>",
        )
        calls = dict(self.calls)
        calls["s22_fyg8_e1_write"] = repro._calls(
            changed["s22_fyg8_e1_write"]
        )
        with self.assertRaisesRegex(p253.AuditError, "return an error"):
            p253.audit_linked_validator(changed, calls, self.addresses)

    def test_rejects_stale_eight_item_compare(self):
        changed = dict(self.disassembly)
        changed["s22_fyg8_e1_expected_item"] += (
            "1010: f100211f cmp x8, #0x8\n"
        )
        with self.assertRaisesRegex(p253.AuditError, "stale eight-item"):
            p253.audit_linked_validator(changed, self.calls, self.addresses)

    def test_preserves_existing_repro_result_contract(self):
        self.assertEqual(p253.SCHEMA, repro.SCHEMA)
        self.assertEqual(p253.VERDICT, repro.VERDICT)
        self.assertEqual(p253.TARGET, repro.TARGET)

    def test_both_cli_import_directions_are_cycle_free(self):
        commands = (
            "import s22plus_fyg8_p234_build_repro_check; "
            "import s22plus_fyg8_p253_linked_audit",
            "import s22plus_fyg8_p253_linked_audit; "
            "import s22plus_fyg8_p234_build_repro_check",
        )
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, "-c", command],
                    cwd=ROOT,
                    env={"PYTHONPATH": str(SCRIPTS)},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
