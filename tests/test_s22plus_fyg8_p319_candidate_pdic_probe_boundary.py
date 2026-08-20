import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_candidate_pdic_probe_boundary.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p319_candidate_pdic_probe_boundary", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319CandidatePdicProbeBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = load_module()
        cls.module = cls.bootstrap.load_bound_auditor()
        cls.inputs = cls.module.load_inputs(materialize=False)
        cls.manifest = cls.module.parse_corpus_manifest(cls.inputs["corpus_manifest"])
        cls.corpus = cls.module.load_corpus(cls.manifest)
        cls.result = cls.module.build_result(cls.inputs, cls.corpus)
        cls.payload = cls.module.encode(cls.result)

    def test_exact_s7a2_ap_contains_the_ordered_module_plan(self):
        candidate = self.result["s7a2_candidate_ap"]
        self.assertEqual(candidate["module_count"], 86)
        self.assertEqual(
            candidate["module_positions_one_based"],
            {
                "msm-geni-se.ko": 30,
                "gpi.ko": 31,
                "i2c-msm-geni.ko": 62,
                "mfd_max77705.ko": 82,
                "spu_verify.ko": 83,
                "pdic_max77705.ko": 84,
            },
        )
        self.assertTrue(candidate["plan_presence_is_not_live_load_proof"])

    def test_historical_loader_records_attempts_but_does_not_stop_on_failure(self):
        loader = self.result["s7a2_loader"]
        self.assertTrue(loader["finit_module_rc_emitted_for_each_attempt"])
        self.assertTrue(loader["failure_does_not_stop_later_attempts"])
        self.assertTrue(loader["attempt_counter_is_not_success_counter"])
        self.assertFalse(loader["durable_candidate_module_receipt"])
        self.assertEqual(loader["module_evidence_sink"], "/dev/kmsg only")

    def test_candidate_loader_mutation_is_rejected(self):
        source = self.inputs["historical_loader_source"]
        mutated = source.replace(
            b"emit_module_result(name, rc);",
            b"/* result intentionally dropped */",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_candidate_loader(mutated)

    def test_probe_source_orders_init_detect_before_unmask(self):
        source = self.result["probe_source"]
        self.assertTrue(source["initial_detect_precedes_parent_usbc_unmask"])
        self.assertTrue(source["initial_detect_sets_ready_then_reads_and_classifies_status"])
        self.assertTrue(source["muic_probe_error_is_not_propagated_by_usbc_probe"])
        self.assertTrue(source["probing_complete_is_not_an_unmask_write_success_receipt"])

    def test_probe_call_consumption_mutation_is_rejected(self):
        mutated = self.inputs["usbc_source"].replace(
            b"\tmax77705_muic_probe(usbc_data);",
            b"\tret = max77705_muic_probe(usbc_data);",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_probe_sources(self.inputs["muic_source"], mutated)

    def test_pdic_machine_code_proves_the_ignored_return_and_unmask_gap(self):
        binary = self.result["pdic_binary"]
        self.assertTrue(binary["muic_probe_return_value_discarded"])
        self.assertTrue(binary["parent_mask_read_failure_skips_bit_clear"])
        self.assertTrue(binary["parent_mask_write_return_value_discarded"])
        self.assertTrue(binary["platform_probe_still_returns_zero_after_unmask_read_failure"])

    def test_pdic_discard_instruction_mutation_is_rejected(self):
        payload = bytearray(self.inputs["pdic_module"])
        elf = self.module.Elf64(bytes(payload), "fixture")
        text = elf.section(".text")
        offset = text.offset + 0xD4F4 - text.address
        payload[offset : offset + 4] = b"\x1f\x20\x03\xd5"
        with self.assertRaises(self.module.AuditError):
            self.module.audit_pdic_binary(bytes(payload))

    def test_irq_free_initial_probe_is_the_no_chgtyp_ap_capture_set(self):
        stock = self.result["stock_initial_probe"]
        self.assertEqual(stock["corpus_distinct_captures"], 121)
        self.assertEqual(stock["captures_with_ap_path"], 10)
        self.assertEqual(stock["captures_with_chgtyp_irq"], 2)
        self.assertEqual(stock["captures_with_irq_free_initial_probe"], 8)
        self.assertTrue(stock["irq_free_initial_probe_set_equals_ap_without_chgtyp_set"])
        self.assertFalse(stock["initial_attach_requires_chgtyp_irq"])
        self.assertEqual(
            {value["process"] for value in stock["per_capture"].values()},
            {"modprobe"},
        )

    def test_initial_status_mutation_is_rejected(self):
        corpus = dict(self.corpus)
        digest = next(
            key for key, body in corpus.items() if self.module.PROBE in body
        )
        corpus[digest] = corpus[digest].replace(
            self.module.STATUS,
            self.module.STATUS.replace(b"BC:0x82", b"BC:0x80"),
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_stock_initial_probe(corpus)

    def test_added_chgtyp_irq_breaks_the_irq_free_set_identity(self):
        corpus = dict(self.corpus)
        digest = next(
            key for key, body in corpus.items() if self.module.PROBE in body
        )
        corpus[digest] = corpus[digest] + b"\n(muic-chgtyp)\n"
        with self.assertRaises(self.module.AuditError):
            self.module.audit_stock_initial_probe(corpus)

    def test_five_historical_reports_do_not_prove_live_module_load(self):
        evidence = self.result["historical_candidate_evidence"]
        self.assertTrue(evidence["prior_wording_that_all_five_did_load_pdic_is_not_supported"])
        self.assertEqual(set(evidence["campaigns"]), {"s7a2", "m7", "m11", "m12", "m18"})
        for value in evidence["campaigns"].values():
            self.assertFalse(value["actual_pdic_finit_module_rc_known"])
            self.assertFalse(value["platform_bind_proven"])
            self.assertFalse(value["initial_detect_proven"])
            self.assertFalse(value["unmask_write_success_proven"])

    def test_historical_report_boundary_mutation_is_rejected(self):
        inputs = dict(self.inputs)
        inputs["report_m7"] = inputs["report_m7"].replace(
            b"does not prove whether M7 reached the module loop",
            b"proves M7 reached the complete module loop",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_historical_reports(inputs)

    def test_unbound_import_cannot_build_an_authoritative_result(self):
        with self.assertRaises(self.bootstrap.AuditError):
            self.bootstrap.build_result(self.inputs, self.corpus)

    def test_receipt_is_exact_and_private(self):
        output = self.module.OUTPUT
        self.assertEqual(output.read_bytes(), self.payload)
        state = output.stat()
        self.assertTrue(stat.S_ISREG(state.st_mode))
        self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
        self.assertEqual(state.st_nlink, 1)
        parsed = json.loads(self.payload)
        self.assertEqual(parsed["verdict"], self.module.VERDICT)
        self.assertFalse(parsed["scope"]["device_contact"])
        self.assertFalse(parsed["scope"]["live_authority_created"])
        ledger = (ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md").read_text(
            encoding="utf-8"
        )
        rows = [
            line
            for line in ledger.splitlines()
            if "h0-candidate-pdic-probe-boundary-5" in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "P319_CANDIDATE_PDIC_PROBE_BOUNDARY_IMPLEMENTED_REVIEW_PENDING",
            rows[0],
        )
        self.assertIn("| H0 |", rows[0])
        self.assertIn("| 0/0 |", rows[0])

    def test_publication_rejects_widened_existing_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_bytes(b"{}\n")
            path.chmod(0o600)
            with self.assertRaises(self.module.AuditError):
                self.module.publish_exclusive(path, b"{}\n")


if __name__ == "__main__":
    unittest.main()
