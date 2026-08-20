from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_candidate_witness_parser_v2.py"
)
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-witness-parser-v2-20260820-14"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_CANDIDATE_WITNESS_PARSER_PREDECESSOR_H0_2026-08-20.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("p319_witness_parser_v2", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load witness parser")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319WitnessParserV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = load_bootstrap()
        cls.module = cls.bootstrap.load_bound_auditor()
        cls.inputs = cls.module.load_inputs(False, OUTPUT)
        cls.base = cls.module._base_sources(cls.inputs)
        cls.generated = cls.module.materialized_bytes(cls.base)
        cls.result = cls.module.build_result(cls.inputs)
        cls.fixture = cls._compile_parser_fixture()

    @classmethod
    def _compile_parser_fixture(cls) -> Path:
        compiler = cls.module.shutil_which("gcc")
        if compiler is None:
            raise AssertionError("host C compiler unavailable")
        directory = Path(tempfile.mkdtemp(prefix="p319-witness-c-fixture-"))
        source = directory / "fixture.c"
        parser = cls.module.P319_C_PARSER_SOURCE
        source.write_text(
            "#include <stdint.h>\n"
            "#include <stddef.h>\n"
            "#include <stdint.h>\n"
            "#include <limits.h>\n"
            "#include <string.h>\n"
            "#include <stdio.h>\n"
            "static size_t cstr_len(const char *s) { return strlen(s); }\n"
            "static int p260_bytes_equal(const char *a, const char *b, size_t n) { return memcmp(a, b, n) == 0; }\n"
            "struct p303_kmsg_capture { int fd; uint8_t started; uint8_t final; uint8_t path_seen; uint8_t reset_mask; uint8_t sequence_seen; uint32_t readback_count; uint32_t first_offset; uint64_t previous_sequence; uint64_t first_sequence; uint64_t record_count; uint64_t record_bytes; uint32_t drain_count; uint32_t module_count; uint32_t module_drain_count; uint32_t drain_record_count; uint32_t drain_bytes; };\n"
            "static struct p303_kmsg_capture g_p303_kmsg;\n"
            + parser
            + "\nint main(int argc, char **argv) {\n"
            "  for (int i = 1; i < argc; ++i) {\n"
            "    long rc = p319_witness_observe_v1(argv[i], strlen(argv[i]));\n"
            "    if (rc != 0) { printf(\"ERR %ld\\n\", rc); return 2; }\n"
            "  }\n"
            "  printf(\"OK %u %u %u %u %u %u %u\\n\", g_p319_witness.witness_mask, g_p319_witness.probe_count, g_p319_witness.irq_count, g_p319_witness.initial_status_count, g_p319_witness.classification_form1_count, g_p319_witness.classification_form2_count, g_p319_witness.deferred_status_count);\n"
            "  return 0;\n}\n",
            encoding="ascii",
        )
        binary = directory / "fixture"
        completed = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(binary), str(source)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if completed.returncode != 0:
            raise AssertionError((completed.stdout + completed.stderr).decode())
        return binary

    def run_c(self, *messages: str) -> str:
        completed = subprocess.run(
            [str(self.fixture), *messages], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False,
        )
        if completed.returncode != 0:
            self.fail(f"C parser rejected fixture: {completed.stdout}{completed.stderr}")
        return completed.stdout.strip()

    def test_source_derived_grammars_bind_all_sites_and_header_macro(self):
        value = self.result["source_bound_grammar"]
        self.assertTrue(value["source_bound_before_grammar"])
        self.assertEqual(value["probe_prefix"], "max77705: max77705_usbc_probe: ")
        self.assertEqual(value["muic_prefix"], "pdic_max77705: ")
        self.assertEqual(set(value["sites"]), {"probe", "irq", "initial", "classification_form1", "classification_form2", "deferred"})
        self.assertEqual(value["initial_status_bytes"], 3)
        self.assertEqual(value["deferred_status_bytes"], 7)
        self.assertTrue(value["deferred_status_is_auxiliary_only"])

    def test_manifest_binding_is_strict_and_selects_one_raw_capture(self):
        value = self.result["corpus_manifest_binding"]
        self.assertEqual(value["schema"], "s22plus-fyg8-p319-abl-capture-manifest-v3")
        self.assertEqual(value["selected_row_count"], 1)
        self.assertTrue(value["selected_row_bound"])
        manifest = self.inputs["abl-capture-manifest.json"]
        with self.assertRaises(self.module.AuditError):
            self.module.strict_json(b'{"schema":"x","schema":"y"}', "duplicate")
        with self.assertRaises(self.module.AuditError):
            self.module.strict_json(b'{"value":NaN}', "nonfinite")
        with self.assertRaises(self.module.AuditError):
            self.module.audit_capture_manifest(manifest.replace(
                b"post_recovery_last_kmsg.bin", b"changed.bin", 1
            ))

    def test_c_parser_executes_probe_irq_initial_and_both_classifications(self):
        output = self.run_c(
            "max77705: max77705_usbc_probe: probing Complete..",
            "pdic_max77705: max77705_muic_irq_init uiadc(355), chgtyp(354), dcdtmo(352), vbadc(351), vbusdet(350)",
            "pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82",
            "pdic_max77705: max77705_muic_check_new_dev vps table match found at i(9), CDP",
            "pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(9), CDP",
        )
        self.assertTrue(output.startswith("OK "))
        fields = output.split()
        self.assertEqual(fields[1], str(0x1F))
        self.assertEqual(fields[2:7], ["1", "1", "1", "1", "1"])

    def test_deferred_seven_byte_line_is_auxiliary_not_initial(self):
        output = self.run_c(
            "pdic_max77705: max77705_muic_print_reg_log USBC1:0x27, USBC2:0x05, BC:0x82, CC0:0xa1, CC1:0x8, PD0:0x19, PD1:0x47 attached_dev:2"
        )
        fields = output.split()
        self.assertEqual(fields[1], str(0x20))
        self.assertEqual(fields[4], "0")
        self.assertEqual(fields[7], "1")

    def test_only_one_classification_form_remains_valid(self):
        output = self.run_c(
            "pdic_max77705: max77705_muic_check_new_dev vps table match found at i(7), USB"
        )
        self.assertEqual(output.split()[5], "1")
        self.assertEqual(output.split()[6], "0")

    def test_c_parser_rejects_grammar_mutations_and_ranges(self):
        for message in (
            "pdic_max77705: max77705_muic_detect_dev USBC1:0X27, USBC2:0x05, BC:0x82",
            "pdic_max77705: max77705_muic_irq_init uiadc(1), chgtyp(2), dcdtmo(3), vbadc(4)",
            "pdic_max77705: max77705_muic_check_new_dev vps table match found at i(01), USB",
            "pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(9), USB ",
        ):
            completed = subprocess.run([str(self.fixture), message], check=False, text=True, stdout=subprocess.PIPE)
            self.assertNotEqual(completed.returncode, 0, message)

    def test_python_transport_preserves_sequences_and_accounts_before_parse(self):
        transport = self.module.BoundedTransport()
        transport.observe_drain([
            b"6,10,1,-;max77705: max77705_usbc_probe: probing Complete..\n",
            b"6,11,2,-;pdic_max77705: max77705_muic_irq_init uiadc(1), chgtyp(2), dcdtmo(3), vbadc(4), vbusdet(5)\n",
        ])
        summary = transport.summary()
        self.assertEqual(summary["first_sequence"], 10)
        self.assertEqual(summary["last_sequence"], 11)
        self.assertEqual(summary["record_count"], 2)
        self.assertEqual(summary["record_bytes"], 159)

    def test_python_transport_rejects_gap_and_limits(self):
        transport = self.module.BoundedTransport()
        transport.observe_drain([b"6,10,1,-;x\n"])
        with self.assertRaises(self.module.AuditError):
            transport.observe(b"6,12,2,-;x\n")
        limit = self.module.BoundedTransport()
        limit.begin_drain()
        with self.assertRaises(self.module.AuditError):
            limit.observe(b"6,1,1,;" + b"x" * (self.module.MAX_DRAIN_BYTES + 1))

    def test_materialization_covers_direct_and_folded_post_load_paths(self):
        value = self.result["materialization"]
        self.assertEqual(value["direct_post_load_drain_calls"], 1)
        self.assertEqual(value["folded_post_load_drain_calls"], 1)
        self.assertTrue(value["per_module_drain_is_shared"])
        self.assertTrue(value["eud_hook_follows_shared_drain"])
        wrapper = self.generated["s22plus_fyg8_p290_e3_runtime.c"]
        self.assertEqual(wrapper.count(b"p319_after_module_load(index,"), 2)
        self.assertEqual(wrapper.count(b"p319_after_module_load(index, 0L);"), 1)
        self.assertEqual(wrapper.count(b"p319_after_module_load(index, p305_folded_load_rc);"), 1)
        helper = wrapper[wrapper.index(b"static long p319_after_module_load"):]
        self.assertLess(helper.find(b"p303_kmsg_drain()"), helper.find(b"p307_read_eud_cache()"))

    def test_loss_and_all_bounds_are_fail_closed_in_generated_c(self):
        runtime = self.generated["s22plus_fyg8_p290_e3_runtime.inc.c"]
        self.assertIn(b"if (amount == -P303_EPIPE) return P303_DETAIL_KMSG_RING_LOSS;", runtime)
        self.assertIn(b"P319_KMSG_MAX_DRAIN_BYTES", runtime)
        self.assertIn(b"P319_KMSG_MAX_TOTAL_BYTES", runtime)
        self.assertIn(b"sequence != g_p303_kmsg.previous_sequence + 1U", runtime)

    def test_envelope_v4_audit_rejects_any_runtime_abi_mutation(self):
        runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
        mutated = dict(self.generated)
        token = b"#define S22PLUS_MAX77705_P318_TIME_MASK 0xffU"
        self.assertEqual(mutated[runtime_name].count(token), 1)
        mutated[runtime_name] = mutated[runtime_name].replace(
            token, b"#define S22PLUS_MAX77705_P318_TIME_MASK 0xfeU", 1
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_materialization(self.base, mutated)

    def test_corpus_qualifies_without_defining_grammar(self):
        value = self.result["corpus_qualification"]
        self.assertTrue(value["source_grammar_not_derived_from_corpus"])
        self.assertGreater(value["classification_form1_count"], 0)
        self.assertGreater(value["classification_form2_count"], 0)
        self.assertGreater(value["deferred_status_count"], 0)
        self.assertTrue(value["deferred_is_not_initial"])

    def test_receipt_records_native_c_parser_execution_and_semantic_fields(self):
        value = self.result["native_parser_qualification"]
        self.assertTrue(value["compiled"])
        self.assertTrue(value["executed"])
        self.assertEqual(value["positive_forms"], 6)
        self.assertEqual(value["malformed_negative_count"], 9)
        self.assertEqual(value["mask"], 0x3F)
        self.assertTrue(value["numeric_printf_range_qualified"])
        self.assertTrue(value["parser_source_extracted_from_generated_runtime"])
        self.assertTrue(value["row72_chain_qualified"])
        self.assertTrue(value["wrong_contexts_fail_closed"])
        self.assertTrue(value["auxiliary_does_not_advance_initial_chain"])
        state = self.module.WitnessState()
        self.module.parse_witness_message(
            "pdic_max77705: max77705_muic_check_new_dev vps table match found at i(9), DCD Timeout",
            state,
        )
        self.module.parse_witness_message(
            "pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(9), CDP",
            state,
        )
        self.assertEqual(state.class_form1_index, 9)
        self.assertEqual(state.class_form1_name, "DCD Timeout")
        self.assertEqual(state.class_form2_attached_dev, 2)
        self.assertEqual(state.class_form2_index, 9)
        self.assertEqual(state.class_form2_name, "CDP")

    def test_native_transport_triggers_each_limit_independently(self):
        value = self.result["native_transport_qualification"]
        for key in (
            "per_drain_byte_limit_negative", "per_drain_record_limit_negative",
            "cumulative_byte_limit_negative", "cumulative_record_limit_negative",
            "drain_counter_overflow_negative",
        ):
            self.assertTrue(value[key])
        cases = value["limit_case_stats"]
        self.assertEqual(cases["per_drain_bytes"]["records"], 64)
        self.assertEqual(cases["per_drain_records"]["records"], 256)
        self.assertEqual(cases["cumulative_bytes"]["records"], 256)
        self.assertEqual(cases["cumulative_records"]["records"], 4096)
        self.assertEqual(cases["drain_overflow"]["rc"], 24609)

    def test_temp_regeneration_is_byte_identical_to_canonical_receipt(self):
        with tempfile.TemporaryDirectory(prefix="p319-witness-regenerate-") as directory:
            result, payload = self.module.run(True, Path(directory) / "successor")
            self.assertEqual(payload, (OUTPUT / "result.json").read_bytes())
            self.assertEqual(result, self.result)

    def test_python_kmsg_requires_exact_terminal_newline(self):
        for record in (
            b"6,10,1,-;x", b"6,10,1,-;x\ntrailing", b"6,10,1,-;x\ny\n",
            b"6,010,1,-;x\n", b"6,10,1,;x\n", b"6,10,1,-;\xff\n",
        ):
            with self.assertRaises(self.module.AuditError):
                self.module.parse_kmsg_record(record)

    def test_python_printf_numeric_parity(self):
        parse_dec = self.module._parse_dec
        self.assertEqual(parse_dec("2147483647", signed=True, maximum=2147483647), 2147483647)
        self.assertEqual(parse_dec("-2147483648", signed=True, maximum=2147483647), -2147483648)
        for value in ("+1", "-0", "2147483648"):
            with self.assertRaises(ValueError):
                parse_dec(value, signed=True, maximum=2147483647)
        self.assertEqual(self.module._parse_hex("01", width=2), 1)
        self.assertEqual(self.module._parse_hex("0", width=None), 0)
        with self.assertRaises(ValueError):
            self.module._parse_hex("01", width=None)

    def test_python_form2_and_deferred_are_auxiliary_in_active_row72(self):
        transport = self.module.BoundedTransport()
        transport.active_module_index = 72
        transport.observe_drain([
            b"6,10,1,-;pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(9), CDP\n",
            b"6,11,2,-;pdic_max77705: max77705_muic_print_reg_log USBC1:0x27, USBC2:0x05, BC:0x82, CC0:0xa1, CC1:0x8, PD0:0x19, PD1:0x47 attached_dev:2\n",
        ])
        self.assertEqual(transport.initial_chain_stage, 0)
        self.assertFalse(transport.initial_chain_complete)
        self.assertFalse(transport.initial_chain_ambiguous)

    def test_driver_or_macro_mutation_is_rejected_before_qualification(self):
        mutated = dict(self.inputs)
        mutated["max77705_usbc.h"] = mutated["max77705_usbc.h"].replace(b"max77705: %s: ", b"changed: %s: ", 1)
        with self.assertRaises(self.module.AuditError):
            self.module.audit_bound_driver_sources(mutated)

    def test_summary_abi_does_not_claim_carrier_or_envelope_publication(self):
        summary = self.result["structured_summary_state"]
        self.assertTrue(summary["host_qualified"])
        self.assertTrue(summary["candidate_source_compiled"])
        self.assertFalse(summary["canonical_encoding_defined"])
        self.assertFalse(summary["carrier_published"])
        self.assertFalse(summary["envelope_v4_reinterpreted"])
        self.assertFalse(summary["envelope_v5_defined"])
        self.assertFalse(self.result["conclusion"]["existing_candidate_witness_transport_obligation_resolved"])

    def test_private_successor_receipt_and_inputs_are_mode0400_single_link(self):
        result = OUTPUT / "result.json"
        self.assertEqual(result.read_bytes(), self.module.encode(self.result))
        for directory in (OUTPUT / "inputs", OUTPUT / "base-sources", OUTPUT / "materialized-sources"):
            for path in directory.iterdir():
                self.assertTrue(path.is_file())
                state = path.stat()
                self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
                self.assertEqual(state.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(result.stat().st_mode), 0o400)
        self.assertEqual(result.stat().st_nlink, 1)

    def test_writer_refuses_clobber_and_hostile_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt"
            old = os.umask(0o777)
            try:
                self.module._write_exclusive(path, b"{}\n")
            finally:
                os.umask(old)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            with self.assertRaises(FileExistsError):
                self.module._write_exclusive(path, b"changed\n")

    def test_report_records_predecessor_and_carrier_boundary(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "INDEPENDENTLY REVIEWED SCOPED PASS; H0 ONLY; TRANSPORT OBLIGATION UNRESOLVED",
            "Only the immediate drain for successful row 72 may build",
            "per-drain records | 256 | 2,982 | 1 | 24,610",
            "`TIME_MASK=0xff`",
            "14ca869c411a5940ecffbc24cd2231bc1d10e0bc410ad379d6914809b0debaf0",
            "opens no second obligation",
            "found no blocking fail-open",
            "does not resolve `candidate-witness-transport`",
        ):
            with self.subTest(token=token):
                self.assertIn(token, report)

    def test_ledger_records_implementation_under_existing_obligation(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-candidate-witness-parser-v2-10" in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("UNDER_EXISTING_TRANSPORT_REVIEW_OBLIGATION", row)
        self.assertIn("15478-byte 14ca869c", row)
        self.assertIn("25/25", row)
        self.assertIn("no second obligation", row)
        self.assertNotIn("PASS_GO_", row)
        review_rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "h0-candidate-witness-parser-v2-independent-review-10" in line
        ]
        self.assertEqual(len(review_rows), 1)
        review = review_rows[0]
        self.assertIn("SCOPED_INDEPENDENT_PASS_NO_TRANSPORT_RESOLUTION", review)
        self.assertIn("15478-byte 14ca869c", review)
        self.assertIn("candidate-witness-transport remains unresolved", review)
        self.assertNotIn("PASS_GO_", review.split(" | ")[4])

    def test_goal_keeps_encoding_build_and_live_authority_closed(self):
        goal = GOAL.read_text(encoding="utf-8")
        self.assertIn("parser predecessor receipt `14ca869c` has scoped independent H0 review", goal)
        self.assertIn("no canonical Carrier encoding exists", goal)
        self.assertIn("No successor candidate build exists yet.", goal)
        self.assertLessEqual(len(goal.splitlines()), 900)


if __name__ == "__main__":
    unittest.main()
