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
from copy import deepcopy
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
        cls.manifest = cls.module.parse_corpus_manifest(
            cls.module.load_corpus_manifest()
        )
        cls.corpus = cls.module.load_corpus(cls.manifest)

    def build(self, inputs=None, manifest=None, corpus=None, *, enforce_identity=True):
        return self.module.build_result(
            self.inputs if inputs is None else inputs,
            self.manifest if manifest is None else manifest,
            self.corpus if corpus is None else corpus,
            enforce_identity=enforce_identity,
        )

    def test_exact_static_chain_matches_the_stock_positive_control(self):
        result = self.build()
        self.assertEqual(result["dtbo"]["i2c_address"], 0x66)
        self.assertEqual(result["dtbo"]["parent_gpio_pin"], 5)
        self.assertTrue(result["dtbo"]["parent_gpio_active_low"])
        self.assertEqual(
            result["binary_semantics"]["pdic_max77705"]["nested_irqs"]["chgtyp"],
            26,
        )
        observed = result["stock_observation"]
        self.assertGreater(observed["parent_irq"]["distinct_number_count"], 1)
        self.assertFalse(observed["parent_irq"]["absolute_number_is_stock_invariant"])
        self.assertEqual(
            observed["nested_irq"]["derived_offsets"],
            {"vbusdet": 22, "vbadc": 23, "chgtyp": 26},
        )
        ap = observed["ap_path"]
        self.assertEqual(ap["com_to_usb_ap"], ap["opcode_0609"])
        self.assertEqual(ap["com_to_usb_ap"], ap["notifier_attach_all_values"])
        self.assertEqual(
            ap["dump_before_attach"] + ap["attach_before_dump"],
            ap["com_to_usb_ap"],
        )
        self.assertGreater(ap["irq_context_ap"], 0)
        self.assertGreater(ap["non_irq_context_ap"], 0)
        self.assertEqual(ap["i2c_write_failure_logs"], 0)
        self.assertTrue(
            result["conclusion"][
                "observed_stock_ap_paths_attempt_i2c_06_09_without_negative_return"
            ]
        )
        self.assertFalse(
            result["conclusion"][
                "candidate_reached_pdic_probe_completion_and_unmask_proven"
            ]
        )

    def test_duplicate_path_population_drift_does_not_change_authority(self):
        changed = deepcopy(self.manifest)
        changed["matching_files"] += 1
        changed["duplicate_files_collapsed"] += 1
        changed["captures"][0]["paths"].append(
            "workspace/private/outputs/synthetic-duplicate/capture.bin"
        )
        reparsed = self.module.parse_corpus_manifest(
            (json.dumps(changed, sort_keys=True) + "\n").encode()
        )
        self.assertEqual(
            self.module.corpus_semantic_projection(reparsed),
            self.module.corpus_semantic_projection(self.manifest),
        )
        self.assertEqual(
            self.module.encode(self.build(manifest=reparsed)),
            self.module.encode(self.build()),
        )
        self.assertNotIn("abl_capture_manifest", self.inputs)

    def test_semantic_manifest_drift_is_rejected(self):
        changed = deepcopy(self.manifest)
        changed["counts"]["abl_stages"] += 1
        with self.assertRaisesRegex(
            self.module.AuditError, "semantic projection differs"
        ):
            self.build(manifest=changed)

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
            self.build(changed, enforce_identity=False)

        image = bytearray(original_image)
        compatible = b"qcom,pm8350c-gpio\0"
        self.assertEqual(selected.data.count(compatible), 1)
        relative = selected.data.index(compatible)
        image[selected.offset + relative + len(compatible) - 2] = ord("z")
        changed["stock_dtbo"] = bytes(image)
        with self.assertRaisesRegex(self.module.AuditError, "GPIO controller differs"):
            self.build(changed, enforce_identity=False)

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

    def test_direct_base_and_base_free_differences_both_hold(self):
        evidence = self.build()["stock_observation"]["nested_irq"]["evidence"]
        self.assertGreaterEqual(len(evidence), 2)
        for item in evidence.values():
            self.assertEqual(
                item["nested_irq_base_source"],
                "direct parent max77705_irq_thread log field",
            )
            self.assertEqual(
                item["base_free_pairwise_differences"],
                {"vbadc_minus_vbusdet": 1, "chgtyp_minus_vbusdet": 4},
            )

        synthetic = b"\n".join(
            (
                b"max77705_irq_thread: irq[900] 900/500/282 irq_src=0x08 pmic_rev=0x05",
                b"max77705_muic_irq irq:522 (muic-vbusdet)",
                b"max77705_muic_irq irq:523 (muic-vbadc)",
                b"max77705_muic_irq irq:526 (muic-chgtyp)",
            )
        )
        derived = self.module.audit_nested_offsets(synthetic)
        self.assertEqual(derived["nested_irq_base"], 500)
        self.assertEqual(derived["derived_offsets"], {"vbusdet": 22, "vbadc": 23, "chgtyp": 26})
        shifted = synthetic.replace(b"irq:526", b"irq:527")
        with self.assertRaisesRegex(self.module.AuditError, "nested IRQ offset"):
            self.module.audit_nested_offsets(shifted)

    def test_corpus_totals_are_recomputed_not_acceptance_constants(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "total_ap != 17",
            "total_dump != 17",
            "dump_before_attach != 16",
            "thread_capture_count != 111",
        ):
            self.assertNotIn(forbidden, source)
        for invariant in (
            "total_ap != total_dump",
            "total_ap != total_attach",
            "dump_before_attach + attach_before_dump != total_ap",
        ):
            self.assertIn(invariant, source)

    def test_stock_parent_base_drift_is_rejected_without_freezing_its_value(self):
        digest = "8069cece37209ce7ded62dc8ffc5d4405b9fb8cbe9020608a762e30baadd21ee"
        raw = self.corpus[digest]
        match = self.module.PARENT_RE.search(raw)
        self.assertIsNotNone(match)
        original = match.group(0)
        replacement = original.replace(b"324", b"325", 1)
        self.assertNotEqual(replacement, original)
        changed = raw[: match.start()] + replacement + raw[match.end() :]
        corpus = dict(self.corpus)
        corpus[digest] = changed
        with self.assertRaisesRegex(self.module.AuditError, "multiple bases|offset differs"):
            self.module.audit_stock_corpus(
                self.manifest, corpus, enforce_identity=False
            )

    def test_stock_nested_irq_offset_drift_is_rejected(self):
        digest = "8069cece37209ce7ded62dc8ffc5d4405b9fb8cbe9020608a762e30baadd21ee"
        raw = self.corpus[digest]
        changed = raw.replace(
            b"max77705_muic_irq irq:350 (muic-chgtyp)",
            b"max77705_muic_irq irq:351 (muic-chgtyp)",
            1,
        )
        self.assertNotEqual(changed, raw)
        corpus = dict(self.corpus)
        corpus[digest] = changed
        with self.assertRaisesRegex(self.module.AuditError, "nested IRQ offset"):
            self.module.audit_stock_corpus(
                self.manifest, corpus, enforce_identity=False
            )

    def test_stock_i2c_command_and_failure_drift_break_corpus_consistency(self):
        digest = "1ad451372ad5bf72fab681656249f07b4451df3255bd3a642759c4cbf5297df1"
        raw = self.corpus[digest]
        changed = raw.replace(
            b"opcode_write: 00000000: 06 09",
            b"opcode_write: 00000000: 06 08",
            1,
        )
        self.assertNotEqual(changed, raw)
        corpus = dict(self.corpus)
        corpus[digest] = changed
        with self.assertRaisesRegex(self.module.AuditError, "multiplicity differs"):
            self.module.audit_stock_corpus(
                self.manifest, corpus, enforce_identity=False
            )

        injected = raw + b"\nmax77705: i2c write fail. dequeue opcode\n"
        corpus[digest] = injected
        with self.assertRaisesRegex(self.module.AuditError, "corpus invariant"):
            self.module.audit_stock_corpus(
                self.manifest, corpus, enforce_identity=False
            )

    def test_source_unmask_bit_drift_is_rejected(self):
        changed = dict(self.inputs)
        changed["max77705_usbc_source"] = changed[
            "max77705_usbc_source"
        ].replace(b"i2c_data &= ~((1 << 3));", b"i2c_data &= ~((1 << 2));", 1)
        with self.assertRaisesRegex(self.module.AuditError, "semantic seam differs"):
            self.build(changed, enforce_identity=False)

        changed = dict(self.inputs)
        changed["max77705_usbc_source"] = changed[
            "max77705_usbc_source"
        ].replace(
            b"ret = max77705_bulk_write(usbc_data->muic, OPCODE_WRITE,",
            b"ret = max77705_bulk_read(usbc_data->muic, OPCODE_WRITE, ",
            1,
        )
        with self.assertRaisesRegex(self.module.AuditError, "semantic seam differs"):
            self.build(changed, enforce_identity=False)

    def test_private_receipt_is_exact_regeneration(self):
        self.assertTrue(self.module.OUTPUT.exists(), "run the audited producer first")
        expected = self.module.encode(self.build())
        actual = self.module.OUTPUT.read_bytes()
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 16_818)
        self.assertEqual(
            hashlib.sha256(actual).hexdigest(),
            "48c389e4e9afe369238359c48baba3057680bd1d06bebe76fdd7f254591ef3c6",
        )
        info = self.module.OUTPUT.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(self.module.OUTPUT_ROOT.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.module.SNAPSHOT_ROOT.stat().st_mode), 0o700)
        parsed = json.loads(actual)
        self.assertEqual(parsed["verdict"], self.module.VERDICT)
        self.assertEqual(
            parsed["corpus_manifest_semantics"]["semantic_projection"],
            self.module.CORPUS_SEMANTIC_IDENTITY,
        )
        self.assertEqual(hashlib.sha256(actual).hexdigest(), hashlib.sha256(expected).hexdigest())
        preserved = (
            (
                self.module.OUTPUT_V1,
                8_187,
                "25be452a9b54ddabe3c1ad0d6e13257614483ef295ea3a3647be8886a77a0902",
            ),
            (
                self.module.OUTPUT_V2,
                8_370,
                "6c3d25a778837462365bd463cc6789342174f2467ee4901245c23c81c3171db9",
            ),
            (
                self.module.OUTPUT_V3,
                8_545,
                "bc193d7e5a736ed59c4cd7c6fe289ec4dca83f8ba8f5abf431d76219e7217c66",
            ),
            (
                self.module.OUTPUT_V4,
                15_697,
                "fef955a4c744960183389f0d52fdf786e50d2a51d11ae0de1fc3ef3ffd4045a2",
            ),
            (
                self.module.OUTPUT_V5,
                15_697,
                "5c84bfc5fe9307a856f4bf74dba2751be3f3bf575936bb33b6b3a242cbb12a3a",
            ),
        )
        for path, size, digest in preserved:
            with self.subTest(path=path):
                body = path.read_bytes()
                info = path.stat()
                self.assertEqual(len(body), size)
                self.assertEqual(hashlib.sha256(body).hexdigest(), digest)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)

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
        repaired = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-max77705-irq-corpus-4 " in line
        ]
        self.assertEqual(len(repaired), 1)
        self.assertIn("5c84bfc5", repaired[0])
        self.assertIn("14 focused", repaired[0])
        reviewed = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-max77705-irq-corpus-review-4 " in line
        ]
        self.assertEqual(len(reviewed), 1)
        self.assertIn(
            "PASS_GO_P319_MAX77705_IRQ_DT_CORPUS_AUDIT_V2_H0_CAPABILITY",
            reviewed[0],
        )


if __name__ == "__main__":
    unittest.main()
