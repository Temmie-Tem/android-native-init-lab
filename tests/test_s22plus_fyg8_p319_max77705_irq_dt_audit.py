#!/usr/bin/env python3
"""Adversarial tests for the P3.19 MAX77705 DT/nested-IRQ audit."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_max77705_irq_dt_audit.py"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load_module():
    spec = importlib.util.spec_from_file_location("p319_max77705_irq_dt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def mutate_word(module, data: bytes, address: int, word: int) -> bytes:
    elf = module.Elf64(data, "mutation")
    text = elf.section(".text")
    changed = bytearray(data)
    struct.pack_into("<I", changed, text.offset + address - text.address, word)
    return bytes(changed)


class P319Max77705IrqDtAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.inputs = cls.module.load_inputs(materialize=False)

    def test_exact_static_chain_matches_the_stock_positive_control(self):
        result = self.module.build_result(self.inputs)
        self.assertEqual(result["dtbo"]["i2c_address"], 0x66)
        self.assertEqual(result["dtbo"]["parent_gpio_pin"], 5)
        self.assertTrue(result["dtbo"]["parent_gpio_active_low"])
        self.assertEqual(
            result["binary_semantics"]["pdic_max77705"]["nested_irqs"]["chgtyp"],
            26,
        )
        self.assertEqual(result["stock_observation"]["nested_irq_base"], 324)
        self.assertEqual(result["conclusion"]["observed_chgtyp_nested_irq"], 350)
        self.assertTrue(
            result["stock_observation"][
                "each_attach_has_nested_chgtyp_to_i2c_0609_to_notifier_order"
            ]
        )
        self.assertEqual(result["stock_observation"]["i2c_write_failure_logs"], 0)
        self.assertTrue(
            result["conclusion"][
                "observed_stock_cdp_attach_attempts_i2c_06_09_without_negative_return"
            ]
        )
        self.assertFalse(
            result["conclusion"][
                "candidate_reached_pdic_probe_completion_and_unmask_proven"
            ]
        )

    def test_selected_dt_gpio_cell_drift_is_rejected(self):
        original_image = self.inputs["stock_dtbo"]
        image = bytearray(original_image)
        selected = self.module._fdt_blobs(original_image)[10]
        cell = bytes.fromhex("000000110000000500000001")
        self.assertEqual(selected.data.count(cell), 1)
        relative = selected.data.index(cell)
        struct.pack_into(">I", image, selected.offset + relative + 4, 6)
        changed = dict(self.inputs)
        changed["stock_dtbo"] = bytes(image)
        with self.assertRaisesRegex(self.module.AuditError, "DT property differs"):
            self.module.build_result(changed, enforce_identity=False)

        image = bytearray(original_image)
        compatible = b"qcom,pm8350c-gpio\0"
        self.assertEqual(selected.data.count(compatible), 1)
        relative = selected.data.index(compatible)
        image[selected.offset + relative + len(compatible) - 2] = ord("z")
        changed["stock_dtbo"] = bytes(image)
        with self.assertRaisesRegex(self.module.AuditError, "GPIO controller differs"):
            self.module.build_result(changed, enforce_identity=False)

    def test_parent_irq_action_name_drift_is_rejected(self):
        data = self.inputs["mfd_max77705_module"]
        elf = self.module.Elf64(data, "mfd")
        rodata = elf.section(".rodata")
        changed = bytearray(data)
        changed[rodata.offset + 0x50B] = ord("n")
        with self.assertRaisesRegex(self.module.AuditError, "action name differs"):
            self.module.audit_mfd_binary(bytes(changed))

    def test_nested_dispatch_bound_drift_is_rejected(self):
        changed = mutate_word(
            self.module, self.inputs["mfd_max77705_module"], 0x32A0, 0xF100AE9F
        )
        with self.assertRaisesRegex(self.module.AuditError, "binary symbol identity"):
            self.module.audit_mfd_binary(changed)

    def test_pdic_parent_unmask_polarity_drift_is_rejected(self):
        changed = mutate_word(
            self.module, self.inputs["pdic_max77705_module"], 0xD8A4, 0x321C7902
        )
        with self.assertRaisesRegex(self.module.AuditError, "binary symbol identity"):
            self.module.audit_pdic_binary(changed)

    def test_chgtyp_nested_offset_drift_is_rejected(self):
        changed = mutate_word(
            self.module, self.inputs["pdic_max77705_module"], 0x167F0, 0x11006EC0
        )
        with self.assertRaisesRegex(self.module.AuditError, "binary symbol identity"):
            self.module.audit_pdic_binary(changed)

    def test_stock_parent_tuple_drift_is_rejected(self):
        raw = self.inputs["stock_live_raw"]
        match = self.module.PARENT_RE.search(raw)
        self.assertIsNotNone(match)
        original = match.group(0)
        replacement = original.replace(b"324", b"325", 1)
        self.assertNotEqual(replacement, original)
        changed = raw[: match.start()] + replacement + raw[match.end() :]
        with self.assertRaisesRegex(self.module.AuditError, "parent IRQ tuple"):
            self.module.audit_stock_raw(changed)

    def test_stock_nested_irq_number_drift_is_rejected(self):
        raw = self.inputs["stock_live_raw"]
        changed = raw.replace(
            b"max77705_muic_irq irq:350 (muic-chgtyp)",
            b"max77705_muic_irq irq:351 (muic-chgtyp)",
            1,
        )
        self.assertNotEqual(changed, raw)
        with self.assertRaisesRegex(self.module.AuditError, "nested IRQ inventory"):
            self.module.audit_stock_raw(changed)

    def test_stock_i2c_command_drift_breaks_the_ordered_positive_control(self):
        raw = self.inputs["stock_live_raw"]
        changed = raw.replace(
            b"opcode_write: 00000000: 06 09",
            b"opcode_write: 00000000: 06 08",
            1,
        )
        self.assertNotEqual(changed, raw)
        with self.assertRaisesRegex(self.module.AuditError, "source order seam"):
            self.module.audit_stock_raw(changed)

        injected = raw + b"\nmax77705: i2c write fail. dequeue opcode\n"
        with self.assertRaisesRegex(self.module.AuditError, "write failure log"):
            self.module.audit_stock_raw(injected)

    def test_source_unmask_bit_drift_is_rejected(self):
        changed = dict(self.inputs)
        changed["max77705_usbc_source"] = changed[
            "max77705_usbc_source"
        ].replace(b"i2c_data &= ~((1 << 3));", b"i2c_data &= ~((1 << 2));", 1)
        with self.assertRaisesRegex(self.module.AuditError, "semantic seam differs"):
            self.module.build_result(changed, enforce_identity=False)

        changed = dict(self.inputs)
        changed["max77705_usbc_source"] = changed[
            "max77705_usbc_source"
        ].replace(
            b"ret = max77705_bulk_write(usbc_data->muic, OPCODE_WRITE,",
            b"ret = max77705_bulk_read(usbc_data->muic, OPCODE_WRITE, ",
            1,
        )
        with self.assertRaisesRegex(self.module.AuditError, "semantic seam differs"):
            self.module.build_result(changed, enforce_identity=False)

    def test_private_receipt_is_exact_regeneration(self):
        self.assertTrue(self.module.OUTPUT.exists(), "run the audited producer first")
        expected = self.module.encode(self.module.build_result(self.inputs))
        actual = self.module.OUTPUT.read_bytes()
        self.assertEqual(actual, expected)
        info = self.module.OUTPUT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(self.module.OUTPUT_ROOT.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.module.SNAPSHOT_ROOT.stat().st_mode), 0o700)
        parsed = json.loads(actual)
        self.assertEqual(parsed["verdict"], self.module.VERDICT)
        self.assertEqual(hashlib.sha256(actual).hexdigest(), hashlib.sha256(expected).hexdigest())
        predecessor = self.module.PREDECESSOR_OUTPUT.read_bytes()
        predecessor_info = self.module.PREDECESSOR_OUTPUT.stat()
        self.assertEqual(len(predecessor), 8_370)
        self.assertEqual(
            hashlib.sha256(predecessor).hexdigest(),
            "6c3d25a778837462365bd463cc6789342174f2467ee4901245c23c81c3171db9",
        )
        self.assertEqual(stat.S_IMODE(predecessor_info.st_mode), 0o400)
        self.assertEqual(predecessor_info.st_nlink, 1)
        initial = self.module.INITIAL_OUTPUT.read_bytes()
        initial_info = self.module.INITIAL_OUTPUT.stat()
        self.assertEqual(len(initial), 8_187)
        self.assertEqual(
            hashlib.sha256(initial).hexdigest(),
            "25be452a9b54ddabe3c1ad0d6e13257614483ef295ea3a3647be8886a77a0902",
        )
        self.assertEqual(stat.S_IMODE(initial_info.st_mode), 0o400)
        self.assertEqual(initial_info.st_nlink, 1)

    def test_report_and_ledger_record_the_scoped_result(self):
        report = " ".join(REPORT.read_text(encoding="utf-8").split())
        for token in (
            "pm8350c GPIO5",
            "nested IRQ base `324`",
            "`324 + 26 = 350`",
            "`06 09`",
            "candidate-side module load, platform bind",
        ):
            self.assertIn(token, report)
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-max77705-irq-dt-3 " in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("| H0 |", rows[0])
        self.assertIn("| 0/0 |", rows[0])


if __name__ == "__main__":
    unittest.main()
