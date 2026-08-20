#!/usr/bin/env python3
"""Focused tests for the P3.19 direct-ELF MUIC guard audit."""

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
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_pdic_muic_guard_audit.py"
)
REPORT = (
    ROOT
    / "docs/reports/"
    "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load_module():
    spec = importlib.util.spec_from_file_location("p319_pdic_guard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def mutate_word(module, data: bytes, address: int, word: int) -> bytes:
    elf = module.Elf64(data, "mutation")
    text = elf.section(".text")
    changed = bytearray(data)
    struct.pack_into("<I", changed, text.offset + address - text.address, word)
    return bytes(changed)


class P319PdicMuicGuardAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.inputs = cls.module.load_inputs(materialize=False)

    def test_exact_modules_prove_the_cdp_to_com_usb_path(self):
        result = self.module.build_result(self.inputs)
        pdic = result["binary_semantics"]["pdic_max77705"]
        common = result["binary_semantics"]["common_muic"]
        self.assertEqual(pdic["attached_dev_dispatch"]["cdp"], 0x18198)
        self.assertEqual(pdic["usb_path_guard"]["ap_target"], 0x17C64)
        self.assertEqual(pdic["com_to_usb_ap"]["control1_value"], 0x09)
        self.assertEqual(pdic["com_to_usb_ap"]["opcode"], 0x06)
        self.assertEqual(pdic["com_to_usb_ap"]["early_conditional_branches"], [])
        self.assertEqual(common["no_parameter_usb_path"], 0)
        self.assertEqual(common["stock_parameter_3_usb_path"], 0)
        self.assertFalse(result["conclusion"]["these_guards_explain_prior_candidate_silence"])

    def test_cdp_jump_table_drift_is_rejected(self):
        data = self.inputs["pdic_max77705_module"]
        elf = self.module.Elf64(data, "pdic")
        rodata = elf.section(".rodata")
        changed = bytearray(data)
        # Value 2 uses the second halfword at .rodata+0x5de.  Point it at
        # com_to_usb_ap directly rather than the required usb_path guard.
        struct.pack_into("<H", changed, rodata.offset + 0x5DE + 2, 0)
        with self.assertRaisesRegex(self.module.AuditError, "USB/CDP attach dispatch differs"):
            self.module.audit_pdic_semantics(bytes(changed))

    def test_usb_path_guard_direction_is_rejected(self):
        changed = mutate_word(
            self.module,
            self.inputs["pdic_max77705_module"],
            0x181C4,
            0x35FFD508,  # CBNZ rather than CBZ for MUIC_PATH_USB_AP == 0.
        )
        with self.assertRaisesRegex(self.module.AuditError, "usb_path guard instruction differs"):
            self.module.audit_pdic_semantics(changed)

    def test_com_usb_value_drift_is_rejected(self):
        changed = mutate_word(
            self.module,
            self.inputs["pdic_max77705_module"],
            0x17C94,
            0x52801497,  # COM_USB_CP 0xa4 instead of COM_USB 0x09.
        )
        with self.assertRaisesRegex(self.module.AuditError, "COM_USB command value"):
            self.module.audit_pdic_semantics(changed)

    def test_fac_water_skip_polarity_is_rejected(self):
        changed = mutate_word(
            self.module,
            self.inputs["pdic_max77705_module"],
            0x17CBC,
            0x34001702,  # CBZ rather than CBNZ.
        )
        with self.assertRaisesRegex(self.module.AuditError, "fac_water_enable guard"):
            self.module.audit_pdic_semantics(changed)

    def test_a_third_fac_water_writer_is_rejected(self):
        changed = mutate_word(
            self.module,
            self.inputs["pdic_max77705_module"],
            0x9C44,
            0xB9045668,
        )
        with self.assertRaisesRegex(self.module.AuditError, "store set differs"):
            self.module.audit_pdic_semantics(changed)

    def test_common_muic_default_and_ap_formula_are_not_assumed(self):
        data = self.inputs["common_muic_module"]
        elf = self.module.Elf64(data, "common")
        symbol = elf.symbol("muic_param_pmic_info")
        section = elf.sections[symbol.section_index]
        changed = bytearray(data)
        offset = section.offset + symbol.value - section.address
        struct.pack_into("<I", changed, offset, 0)
        with self.assertRaisesRegex(self.module.AuditError, "default differs"):
            self.module.audit_common_semantics(bytes(changed))

        changed = mutate_word(self.module, data, 0x5D4, 0x2A1603E8)
        with self.assertRaisesRegex(self.module.AuditError, "usb_path initializer"):
            self.module.audit_common_semantics(changed)

    def test_source_writer_census_is_not_a_literal_only_claim(self):
        changed = dict(self.inputs)
        changed["max77705_usbc_source"] = changed["max77705_usbc_source"].replace(
            b"usbpd_data->fac_water_enable = 1;",
            b"usbpd_data->fac_water_enable = 2;",
            1,
        )
        with self.assertRaisesRegex(self.module.AuditError, "semantic seam differs"):
            self.module.build_result(changed, enforce_identity=False)

    def test_private_receipt_is_exact_regeneration(self):
        self.assertTrue(self.module.OUTPUT.exists(), "run the audited producer first")
        expected = self.module.encode(self.module.build_result(self.inputs))
        actual = self.module.OUTPUT.read_bytes()
        info = self.module.OUTPUT.stat()
        self.assertEqual(actual, expected)
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(self.module.OUTPUT_ROOT.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.module.SNAPSHOT_ROOT.stat().st_mode), 0o700)
        parsed = json.loads(actual)
        self.assertEqual(parsed["verdict"], self.module.VERDICT)

    def test_predecessor_receipt_is_preserved_after_directory_mode_repair(self):
        payload = self.module.PREDECESSOR_OUTPUT.read_bytes()
        info = self.module.PREDECESSOR_OUTPUT.stat()
        self.assertEqual(len(payload), 5_160)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "fc8b107ad974f2006cef5c1171f5183de9415001fa4c8fcfedb84129bd245dbc",
        )
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)

    def test_report_and_append_only_ledger_record_the_bounded_result(self):
        report = REPORT.read_text(encoding="utf-8")
        flat = " ".join(report.split())
        for token in (
            "CDP value `2` enters the USB-path block",
            "`usb_path == 0` branches to AP",
            "`fac_water_enable` is the only surviving post-AP suppression",
            "do not explain the earlier candidate silence",
        ):
            self.assertIn(token, flat)
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-pdic-muic-guard-2 " in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("| H0 |", rows[0])
        self.assertIn("| 0/0 |", rows[0])

    def test_audit_only_bytes_match_preserved_receipt(self):
        self.assertTrue(self.module.OUTPUT.exists(), "run the audited producer first")
        expected = self.module.encode(self.module.build_result(self.inputs))
        self.assertEqual(hashlib.sha256(expected).hexdigest(), hashlib.sha256(self.module.OUTPUT.read_bytes()).hexdigest())
        self.assertFalse(any(value for key, value in json.loads(expected)["scope"].items() if key.endswith("authorized")))


if __name__ == "__main__":
    unittest.main()
