import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from copy import deepcopy
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
        cls.manifest = cls.module.parse_corpus_manifest(
            cls.module.load_corpus_manifest()
        )
        cls.corpus = cls.module.load_corpus(cls.manifest)
        cls.result = cls.module.build_result(cls.inputs, cls.manifest, cls.corpus)
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
        self.assertTrue(source["pre_muic_usbc_irq_handler_return_discarded"])
        self.assertEqual(
            source["pre_muic_usbc_irq_handler_families"],
            ["APC", "SYSMSG", "VDM0-VDM6", "VIR0"],
        )
        self.assertTrue(source["nonfinal_muic_irq_failure_can_be_masked_by_later_success"])
        self.assertTrue(source["final_vbusdet_irq_failure_blocks_initial_detect"])
        self.assertTrue(source["muic_probe_error_is_not_propagated_by_usbc_probe"])
        self.assertTrue(source["probing_complete_is_not_an_unmask_write_success_receipt"])
        self.assertEqual(source["unmask_source_call_sites_total"], 3)
        self.assertEqual(source["unmask_probe_call_sites_audited"], 1)
        self.assertEqual(source["unmask_recovery_call_sites_out_of_scope"], 2)
        conclusion = self.result["conclusion"]
        self.assertFalse(conclusion["pre_muic_usbc_irq_registration_failure_blocks_initial_mux"])
        self.assertTrue(conclusion["nonfinal_muic_irq_failure_can_be_masked_by_later_success"])
        self.assertTrue(conclusion["final_vbusdet_irq_failure_can_block_initial_detect"])
        self.assertFalse(conclusion["all_muic_irq_registration_failure_is_nonblocking"])
        self.assertFalse(
            conclusion["absence_of_chgtyp_interrupt_delivery_explains_initial_mux_silence"]
        )

    def test_probe_call_consumption_mutation_is_rejected(self):
        for call in (b"max77705_init_irq_handler", b"max77705_muic_probe"):
            with self.subTest(call=call):
                original = b"\t" + call + b"(usbc_data);"
                replacement = b"\tret = " + call + b"(usbc_data);"
                mutated = self.inputs["usbc_source"].replace(
                    original,
                    replacement,
                    1,
                )
                with self.assertRaises(self.module.AuditError):
                    self.module.audit_probe_sources(self.inputs["muic_source"], mutated)

    def test_pdic_machine_code_proves_the_ignored_return_and_unmask_gap(self):
        binary = self.result["pdic_binary"]
        self.assertTrue(binary["usbc_irq_handler_return_value_discarded"])
        self.assertTrue(binary["muic_probe_return_value_discarded"])
        self.assertTrue(binary["parent_mask_read_failure_skips_bit_clear"])
        self.assertTrue(binary["parent_mask_write_return_value_discarded"])
        self.assertTrue(binary["platform_probe_still_returns_zero_after_unmask_read_failure"])

    def test_pdic_discard_instruction_mutation_is_rejected(self):
        for address in (0xD4EC, 0xD4F4):
            with self.subTest(address=hex(address)):
                payload = bytearray(self.inputs["pdic_module"])
                elf = self.module.Elf64(bytes(payload), "fixture")
                text = elf.section(".text")
                offset = text.offset + address - text.address
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
            self.module.encode(
                self.module.build_result(self.inputs, reparsed, self.corpus)
            ),
            self.payload,
        )
        self.assertNotIn("corpus_manifest", self.inputs)

    def test_semantic_manifest_drift_is_rejected(self):
        changed = deepcopy(self.manifest)
        changed["muic_opcode_counts"]["0x06"] += 1
        with self.assertRaisesRegex(
            self.module.AuditError, "semantic projection differs"
        ):
            self.module.build_result(self.inputs, changed, self.corpus)

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
            self.bootstrap.build_result(self.inputs, self.manifest, self.corpus)

    def test_receipt_is_exact_and_private(self):
        output = self.module.OUTPUT
        self.assertEqual(output.read_bytes(), self.payload)
        self.assertEqual(len(self.payload), 15_563)
        self.assertEqual(
            self.module.sha256(self.payload),
            "7744d9e7c5d76148ad4038f59531dd686d6e8b3a1327e78206ae5c6ad4390025",
        )
        state = output.stat()
        self.assertTrue(stat.S_ISREG(state.st_mode))
        self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
        self.assertEqual(state.st_nlink, 1)
        parsed = json.loads(self.payload)
        self.assertEqual(
            parsed["schema"],
            "s22plus-fyg8-p319-candidate-pdic-probe-boundary-v3",
        )
        self.assertEqual(parsed["verdict"], self.module.VERDICT)
        self.assertFalse(parsed["scope"]["device_contact"])
        self.assertFalse(parsed["scope"]["live_authority_created"])
        self.assertEqual(
            parsed["corpus_manifest_semantics"]["semantic_projection"],
            self.module.CORPUS_SEMANTIC_IDENTITY,
        )
        preserved = self.module.OUTPUT_V4.read_bytes()
        preserved_state = self.module.OUTPUT_V4.stat()
        self.assertEqual(len(preserved), 14_440)
        self.assertEqual(
            self.module.sha256(preserved),
            "cd3969eb9de6da8342c2843895bf71c631997672d64e370d33dda2fe5b5ae7e3",
        )
        self.assertEqual(stat.S_IMODE(preserved_state.st_mode), 0o400)
        self.assertEqual(preserved_state.st_nlink, 1)
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
        successor = [
            line
            for line in ledger.splitlines()
            if "h0-candidate-pdic-probe-boundary-v2-6" in line
        ]
        self.assertEqual(len(successor), 1)
        self.assertIn(
            "P319_IRQ_REGISTRATION_FAILURE_SCOPE_CORRECTED_UNDER_EXISTING_REVIEW_OBLIGATION",
            successor[0],
        )
        self.assertIn("14440 bytes/SHA-256 cd3969eb", successor[0])
        self.assertIn("creates no second obligation or PASS_GO", successor[0])

    def test_publication_rejects_widened_existing_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_bytes(b"{}\n")
            path.chmod(0o600)
            with self.assertRaises(self.module.AuditError):
                self.module.publish_exclusive(path, b"{}\n")


if __name__ == "__main__":
    unittest.main()
