import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_candidate_witness_transport.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p319_candidate_witness_transport", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319CandidateWitnessTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = load_module()
        cls.module = cls.bootstrap.load_bound_auditor()
        cls.inputs = cls.module.load_inputs(materialize=False)
        cls.result = cls.module.build_result(cls.inputs)
        cls.payload = cls.module.encode(cls.result)

    def test_current_candidate_has_no_printk_to_retained_sink(self):
        static = self.result["candidate_static_closure"]
        plan = self.result["effective_plan"]
        self.assertTrue(static["sec_log_buf_absent"])
        self.assertTrue(static["candidate_printk_has_no_sec_log_buf_retained_sink"])
        self.assertFalse(plan["sec_log_buf_in_plan"])
        self.assertFalse(plan["mfd_max77705_in_plan"])
        self.assertFalse(plan["pdic_max77705_in_plan"])
        self.assertFalse(plan["current_p318_can_emit_stock_pdic_witnesses"])

    def test_direct_carrier_requires_the_reserved_idx_to_stay_fixed(self):
        carrier = self.result["direct_carrier"]
        self.assertEqual(carrier["reserved_region_payload_bytes"], 2_097_136)
        self.assertTrue(carrier["carrier_seed_is_reserved_header_idx"])
        self.assertTrue(carrier["carrier_writes_reserved_bytes_directly"])
        self.assertTrue(carrier["carrier_does_not_advance_header_idx"])
        self.assertTrue(carrier["every_carrier_update_requires_idx_equal_seed"])

    def test_samsung_logger_advances_the_idx_the_carrier_freezes(self):
        logger = self.result["samsung_retained_logger"]
        self.assertTrue(logger["positive_write_advances_header_idx_by_count"])
        self.assertTrue(logger["probe_imports_early_printk_before_registering_live_logger"])
        self.assertTrue(logger["accepted_console_printk_routes_to_retained_writer"])
        self.assertTrue(logger["adding_logger_after_carrier_seed_can_invalidate_idx_stability"])

    def test_existing_live_kmsg_reader_is_the_reusable_transport(self):
        kmsg = self.result["existing_live_kmsg_transport"]
        self.assertTrue(kmsg["opens_dev_kmsg_before_module_loop"])
        self.assertTrue(kmsg["starts_at_live_tail"])
        self.assertTrue(kmsg["drains_after_complete_module_loop"])
        self.assertFalse(kmsg["drains_after_each_module"])
        self.assertTrue(kmsg["epipe_ring_loss_is_fail_closed"])
        self.assertTrue(kmsg["sequence_gap_is_fail_closed"])
        self.assertFalse(kmsg["cumulative_bytes_counted"])
        self.assertFalse(kmsg["raw_kmsg_persisted"])

    def test_successor_rule_uses_live_kmsg_then_structured_carrier(self):
        conclusion = self.result["conclusion"]
        self.assertFalse(conclusion["stock_pr_info_survival_proves_candidate_retention"])
        self.assertFalse(conclusion["current_p318_printk_witnesses_reach_retained_carrier"])
        self.assertFalse(conclusion["two_mib_sec_log_byte_budget_applies_to_current_direct_carrier"])
        self.assertFalse(conclusion["adding_sec_log_buf_without_carrier_redesign_is_allowed"])
        self.assertTrue(conclusion["reuse_existing_live_kmsg_reader"])
        self.assertTrue(conclusion["drain_after_each_relevant_module"])
        self.assertTrue(conclusion["count_cumulative_kmsg_record_bytes"])
        self.assertTrue(conclusion["publish_structured_witness_summary_through_direct_carrier"])

    def test_sec_log_buf_presence_mutation_is_rejected(self):
        value = json.loads(self.inputs["p318_static"])
        value["candidate"]["module_closure"]["sec_log_buf_absent"] = False
        mutated = (json.dumps(value, sort_keys=True) + "\n").encode()
        with self.assertRaises(self.module.AuditError):
            self.module.audit_static_closure(mutated)

    def test_plan_injection_is_rejected(self):
        anchor = b"static const struct s22plus_o2_module_plan_entry s22plus_o2_module_plan[] = {\n"
        mutated = self.inputs["plan"].replace(
            anchor,
            anchor + b'    {"sec_log_buf.ko", "sec_log_buf", ""},\n',
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_effective_plan(mutated)

    def test_carrier_idx_gate_mutation_is_rejected(self):
        mutated = self.inputs["candidate_patch"].replace(
            b"READ_ONCE(head->idx) == s22_fyg8_e1_state.seed_idx",
            b"READ_ONCE(head->idx) != s22_fyg8_e1_state.seed_idx",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_direct_carrier(mutated)

    def test_live_kmsg_loss_gate_mutation_is_rejected(self):
        mutated = self.inputs["runtime_include"].replace(
            b"if (amount == -P303_EPIPE) return P303_DETAIL_KMSG_RING_LOSS;",
            b"if (amount == -P303_EPIPE) return 0;",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_live_kmsg_transport(
                self.inputs["runtime_wrapper"], mutated
            )

    def test_samsung_idx_increment_mutation_is_rejected(self):
        mutated = self.inputs["sec_log_main"].replace(
            b"s_log_buf->idx += (uint32_t)count;",
            b"s_log_buf->idx += 0;",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_sec_log_writer(
                mutated,
                self.inputs["sec_log_console"],
                self.inputs["sec_log_header"],
            )

    def test_receipt_and_inputs_are_exact_private_files(self):
        self.assertEqual(self.module.OUTPUT.read_bytes(), self.payload)
        for path in [self.module.OUTPUT, *self.module.INPUT_ROOT.iterdir()]:
            state = path.stat()
            self.assertTrue(stat.S_ISREG(state.st_mode))
            self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
            self.assertEqual(state.st_nlink, 1)
        for path in (self.module.OUTPUT_ROOT, self.module.INPUT_ROOT):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertFalse(self.result["scope"]["live_authority_created"])

    def test_writer_normalizes_hostile_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            old = os.umask(0o777)
            try:
                self.module._write_exclusive(path, b"{}\n")  # noqa: SLF001
            finally:
                os.umask(old)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)

    def test_unbound_import_cannot_build_an_authoritative_result(self):
        with self.assertRaises(self.bootstrap.AuditError):
            self.bootstrap.build_result(self.inputs)


if __name__ == "__main__":
    unittest.main()
