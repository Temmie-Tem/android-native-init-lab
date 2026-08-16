import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))
SCRIPT = REVALIDATION / "s22plus_fyg8_p318_postlive_eud_index_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p318_postlive_eud_index_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_bound_auditor()


class P318PostliveEudIndexAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.receipt = cls.module.build_receipt()
        intent = cls.module.load_intent(
            cls.module.stable_bytes(
                cls.module.INTENT,
                cls.module.INTENT_SIZE,
                cls.module.INTENT_SHA256,
                "fixture intent",
            )
        )
        semantic_inputs = cls.module._semantic_inputs(intent)
        implementation = {
            "carrier_model": cls.module.current_regular_bytes(
                cls.module.POSTLIVE_MODEL, "fixture post-live carrier model"
            ),
            "decoder": cls.module.current_regular_bytes(
                cls.module.POSTLIVE_DECODER, "fixture post-live decoder"
            ),
            "auditor": cls.module.current_regular_bytes(
                cls.module.POSTLIVE_AUDITOR, "fixture post-live auditor"
            ),
        }
        cls.frozen_carrier, cls.carrier, cls.decoder = (
            cls.module._load_bound_decoders(semantic_inputs, implementation)
        )

    def test_actual_retained_failure_is_recovered_without_causal_authority(self):
        value = self.receipt
        self.assertEqual(value["verdict"], self.module.VERDICT)
        self.assertEqual(
            value["conclusion"]["effective_campaign_proof"],
            "NO_PROOF_EXPERIMENT_PRECONDITION",
        )
        self.assertEqual(value["frozen_decoder_incident"]["slot_status"], ["valid", "bad-body"])
        self.assertEqual(value["recovered_record"]["slot_status"], ["valid", "valid"])
        self.assertEqual(value["recovered_record"]["generation"], 47)
        self.assertEqual(value["recovered_record"]["stage"], 0x66)
        self.assertEqual(value["recovered_record"]["item_index"], 38)
        self.assertEqual(value["recovered_record"]["detail"], "0x6010")
        self.assertFalse(value["conclusion"]["max77705_diagnostic_reached"])
        self.assertFalse(value["conclusion"]["causal_result_allowed"])
        self.assertFalse(value["scope"]["device_contact"])
        self.assertFalse(value["scope"]["device_actions"])
        self.assertFalse(value["scope"]["live_authority_created"])

    def test_source_chain_proves_the_one_index_drift(self):
        chain = self.receipt["source_chain"]
        self.assertEqual(chain["runtime_eud_cache_index"], 37)
        self.assertEqual(chain["runtime_index_37_module"], "qmi_helpers")
        self.assertEqual(chain["explicit_eud_module_index"], 38)
        self.assertTrue(chain["cache_read_precedes_explicit_eud_load"])
        self.assertTrue(chain["cache_failure_publisher_is_noreturn"])
        self.assertTrue(chain["module_load_precedes_progress_checkpoint"])
        self.assertTrue(chain["progress_checkpoint_precedes_cache_read"])
        self.assertTrue(chain["max77705_entry_follows_cache_failure_site"])
        self.assertEqual(
            chain["failure_detail_publication_collision_range"],
            "0x6001..0x6fff",
        )
        self.assertTrue(chain["failure_detail_was_publishable"])
        self.assertTrue(
            chain["failure_detail_literal_unique_in_materialized_execution_sources"]
        )
        close_authority = chain["publication_close_alias_exclusion"]
        self.assertTrue(close_authority["close_minus_16_aliases_0x6010"])
        self.assertTrue(
            close_authority["kernel_slot_commit_precedes_sys_write_success_return"]
        )
        self.assertTrue(close_authority["kernel_active_generation_advances_before_client_close"])
        self.assertTrue(close_authority["kernel_failure_terminal_advances_before_client_close"])
        self.assertTrue(close_authority["stale_failure_retry_rejected_by_terminal"])
        self.assertTrue(close_authority["stale_progress_retry_rejected_by_generation_position"])
        self.assertFalse(close_authority["close_minus_16_fallback_can_replace_retained_slot"])
        self.assertTrue(close_authority["failure_detail_uniquely_attributed_to_eud_reader"])
        self.assertEqual(
            set(self.receipt["inputs"]["postlive_implementation"]),
            {"carrier_model", "decoder", "auditor"},
        )
        semantic_sources = set(self.receipt["inputs"]["frozen_semantic_sources"])
        self.assertEqual(len(semantic_sources), 36)
        self.assertIn("p318_frozen_decoder", semantic_sources)
        self.assertIn(
            "frozen_import__s22plus_fyg8_p310_carrier_model",
            semantic_sources,
        )
        self.assertIn(
            "frozen_import__s22plus_fyg8_p300_telemetry_spec",
            semantic_sources,
        )
        self.assertEqual(len(self.receipt["inputs"]["materialized_sources"]), 13)

    def test_runtime_index_and_plan_mutations_fail_closed(self):
        intent = self.module.load_intent(
            self.module.stable_bytes(
                self.module.INTENT,
                self.module.INTENT_SIZE,
                self.module.INTENT_SHA256,
                "fixture intent",
            )
        )
        inputs = self.module._materialized_inputs(intent)
        semantic_inputs = self.module._semantic_inputs(intent)
        runtime_mutated = dict(inputs)
        runtime_mutated["p290_e3_runtime_include"] = inputs[
            "p290_e3_runtime_include"
        ].replace(
            b"#define P307_EUD_MODULE_INDEX 37U",
            b"#define P307_EUD_MODULE_INDEX 38U",
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(runtime_mutated, semantic_inputs)

        loader_mutated = dict(inputs)
        loader_mutated["runtime_wrapper"] = inputs["runtime_wrapper"].replace(
            b"return p241_verify_module_prefix(index + 1U);",
            b"return 0; /* lost module verification */",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(loader_mutated, semantic_inputs)

        loader_domain_mutated = dict(inputs)
        loader_domain_mutated["runtime_wrapper"] = inputs[
            "runtime_wrapper"
        ].replace(
            b"if (!scan.eof_seen || scan.malformed || scan.found_count != count ||\n"
            b"        scan.lines_seen != count) {\n"
            b"        return -ENODEV;\n",
            b"if (!scan.eof_seen || scan.malformed || scan.found_count != count ||\n"
            b"        scan.lines_seen != count) {\n"
            b"        return 0x6000 + 16;\n",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(loader_domain_mutated, semantic_inputs)

        loader_value_mutated = dict(inputs)
        loader_value_mutated["runtime_wrapper"] = inputs[
            "runtime_wrapper"
        ].replace(
            b"    int path_rc = p241_build_module_path(\n"
            b"        path, sizeof(path), s22plus_o2_module_plan[index].filename);\n",
            b"    int path_rc = p241_build_module_path(\n"
            b"        path, sizeof(path), s22plus_o2_module_plan[index].filename);\n"
            b"    if (index == 38U) path_rc = 0x6000 + 16;\n",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(loader_value_mutated, semantic_inputs)

        syscall_mutated = dict(inputs)
        syscall_mutated["p288_legacy_runtime"] = inputs[
            "p288_legacy_runtime"
        ].replace(
            b"    return x0;\n}",
            b"    if (nr == NR_FINIT_MODULE) return 0x6000 + 16;\n"
            b"    return x0;\n}",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(syscall_mutated, semantic_inputs)

        noreturn_mutated = dict(inputs)
        noreturn_mutated["p290_e3_runtime_include"] = inputs[
            "p290_e3_runtime_include"
        ].replace(
            b"static __attribute__((noreturn)) void p290_fail_next(long detail)",
            b"static void p290_fail_next(long detail)",
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(noreturn_mutated, semantic_inputs)

        early_diagnostic_mutated = dict(inputs)
        early_diagnostic_mutated["runtime_wrapper"] = inputs[
            "runtime_wrapper"
        ].replace(
            b"    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {",
            b"    p318_run();\n"
            b"    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(early_diagnostic_mutated, semantic_inputs)

        extra_producer_mutated = dict(inputs)
        extra_producer_mutated["runtime_wrapper"] = inputs[
            "runtime_wrapper"
        ].replace(
            b"    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {\n"
            b"        E1_REQUIRE(\n",
            b"    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {\n"
            b"        if (index == 38U)\n"
            b"            p290_fail_next(P307_DETAIL_EUD_CACHE_READ_FAILED);\n"
            b"        E1_REQUIRE(\n",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(extra_producer_mutated, semantic_inputs)

        macro_mutated = dict(inputs)
        macro_mutated["p288_legacy_runtime"] = inputs[
            "p288_legacy_runtime"
        ].replace(
            b"long e1_operation_result = (operation);",
            b"long e1_operation_result = 0;",
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(macro_mutated, semantic_inputs)

        macro_bypass_mutated = dict(inputs)
        macro_bypass_mutated["p288_legacy_runtime"] = inputs[
            "p288_legacy_runtime"
        ].replace(
            b"        if (e1_operation_result != 0) {                       \\\n"
            b"            fail_at((stage), (item_index), e1_operation_result); \\\n",
            b"        if (e1_operation_result != 0) {                       \\\n"
            b"            fail_at((stage), (item_index), 0x6000 + 16);       \\\n"
            b"            fail_at((stage), (item_index), e1_operation_result); \\\n",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(macro_bypass_mutated, semantic_inputs)

        plan_mutated = dict(inputs)
        plan_mutated["plan_header"] = inputs["plan_header"].replace(
            b'{"qmi_helpers.ko", "qmi_helpers", ""},\n'
            b'    {"eud.ko", "eud", ""},',
            b'{"eud.ko", "eud", ""},\n'
            b'    {"qmi_helpers.ko", "qmi_helpers", ""},',
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(plan_mutated, semantic_inputs)

        header_mutated = dict(inputs)
        header_mutated["p290_checkpoint_header"] = inputs[
            "p290_checkpoint_header"
        ].replace(
            b"#define S22_P292_PUBLICATION_CLOSE_BASE 0x6000U",
            b"#define S22_P292_PUBLICATION_CLOSE_BASE 0x7000U",
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(header_mutated, semantic_inputs)

        semantic_mutated = dict(semantic_inputs)
        semantic_mutated["p318_frozen_decoder"] = semantic_inputs[
            "p318_frozen_decoder"
        ].replace(
            b"import s22plus_fyg8_p310_carrier_model as model",
            b"import s22plus_fyg8_p311_carrier_model as model",
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(inputs, semantic_mutated)

        release_mutated = dict(inputs)
        release_mutated["candidate_patch"] = inputs["candidate_patch"].replace(
            b"+\t.proc_write = s22_fyg8_e1_write,\n+};",
            b"+\t.proc_write = s22_fyg8_e1_write,\n"
            b"+\t.proc_release = s22_fyg8_e1_release,\n+};",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(release_mutated, semantic_inputs)

        terminal_mutated = dict(inputs)
        terminal_mutated["candidate_patch"] = inputs["candidate_patch"].replace(
            b"+\t\trequest.outcome != S22_FYG8_E1_PROGRESS;",
            b"+\t\tfalse;",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(terminal_mutated, semantic_inputs)

        postcommit_mutated = dict(inputs)
        postcommit_mutated["candidate_patch"] = inputs[
            "candidate_patch"
        ].replace(
            b"+\t\trequest.outcome != S22_FYG8_E1_PROGRESS;\n"
            b"+\t*position += count;",
            b"+\t\trequest.outcome != S22_FYG8_E1_PROGRESS;\n"
            b"+\ts22_fyg8_e1_state.terminal = false;\n"
            b"+\ts22_fyg8_e1_state.active.generation--;\n"
            b"+\t*position += count;",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(postcommit_mutated, semantic_inputs)

        stale_generation_mutated = dict(inputs)
        stale_generation_mutated["candidate_patch"] = inputs[
            "candidate_patch"
        ].replace(
            b"size_t ordinal = s22_fyg8_e1_state.active.generation;",
            b"size_t ordinal = s22_fyg8_e1_state.active.generation - 1U;",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(stale_generation_mutated, semantic_inputs)

        client_advance_mutated = dict(inputs)
        client_advance_mutated["checkpoint_client"] = inputs[
            "checkpoint_client"
        ].replace(
            b"long closed = sys_close((int)fd);",
            b"client->generation = (uint8_t)(ordinal + 1U);\n"
            b"    long closed = sys_close((int)fd);",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(client_advance_mutated, semantic_inputs)

        normalizer_mutated = dict(inputs)
        normalizer_mutated["checkpoint_client"] = inputs[
            "checkpoint_client"
        ].replace(
            b"static long p288_normalize_failure_detail(\n"
            b"    long operation_error, uint16_t *detail) {\n"
            b"    unsigned long value;\n",
            b"static long p288_normalize_failure_detail(\n"
            b"    long operation_error, uint16_t *detail) {\n"
            b"    if (operation_error == -5) {\n"
            b"        *detail = 0x6000 + 16;\n"
            b"        return 0;\n"
            b"    }\n"
            b"    unsigned long value;\n",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(normalizer_mutated, semantic_inputs)

        legacy_failure_mutated = dict(inputs)
        legacy_failure_mutated["checkpoint_client"] = inputs[
            "checkpoint_client"
        ].replace(
            b"    long rc = p288_normalize_failure_detail(operation_error, &detail);\n",
            b"    long rc = p288_normalize_failure_detail(operation_error, &detail);\n"
            b"    if (operation_error == -5) detail = 0x6000 + 16;\n",
            1,
        )
        with self.assertRaises(self.module.AuditError):
            self.module.audit_source_chain(legacy_failure_mutated, semantic_inputs)

    def test_exact_intermediate_failure_semantics_are_closed(self):
        model = self.carrier
        inherited = model.inherited

        run_id = b"p318-postlive!!!"  # one nonzero 128-bit fixture identity
        record = model.initialize_record("E2", run_id)
        for generation in range(1, model.FAILURE_GENERATION):
            position = inherited.position_for_generation(generation)
            record = model.apply_request(
                record,
                model.encode_request(
                    "E2",
                    position.stage,
                    run_id=run_id,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=position.item_index,
                    detail=0,
                ),
            )
        position = inherited.position_for_generation(model.FAILURE_GENERATION)
        for outcome, detail in (
            (model.OUTCOME_PROGRESS, model.FAILURE_DETAIL),
            (model.OUTCOME_FAILURE, model.FAILURE_DETAIL + 1),
        ):
            with self.subTest(outcome=outcome, detail=detail):
                with self.assertRaises(model.DesignError):
                    model.apply_request(
                        record,
                        model.encode_request(
                            "E2",
                            position.stage,
                            run_id=run_id,
                            outcome=outcome,
                            item_index=position.item_index,
                            detail=detail,
                        ),
                    )

    def test_retained_crc_mutation_fails_closed(self):
        payload = bytearray(
            self.module.stable_bytes(
                self.module.RETAINED[0],
                self.module.RETAINED_SIZE,
                self.module.RETAINED_SHA256,
                "fixture retained read",
            )
        )
        payload[self.module.RECORD_OFFSET + 120] ^= 1
        intent = self.module.load_intent(
            self.module.stable_bytes(
                self.module.INTENT,
                self.module.INTENT_SIZE,
                self.module.INTENT_SHA256,
                "fixture intent",
            )
        )
        with self.assertRaises(self.carrier.DesignError):
            self.module._record_result(
                bytes(payload),
                bytes.fromhex(intent["run_id"]),
                self.frozen_carrier,
                self.carrier,
                self.decoder,
            )

    def test_additional_unsat_family_cannot_share_the_recovered_observation(self):
        payload = self.module.stable_bytes(
            self.module.RETAINED[0],
            self.module.RETAINED_SIZE,
            self.module.RETAINED_SHA256,
            "fixture retained read",
        )
        intent = self.module.load_intent(
            self.module.stable_bytes(
                self.module.INTENT,
                self.module.INTENT_SIZE,
                self.module.INTENT_SHA256,
                "fixture intent",
            )
        )
        run_id = bytes.fromhex(intent["run_id"])
        mutated = payload + self.carrier.unsat_record("E2", run_id)
        with self.assertRaises(self.carrier.DesignError):
            self.decoder.classify_observation(
                mutated,
                expected_profile="E2",
                expected_run_id=run_id,
            )

    def test_receipted_source_bytes_are_the_modules_that_execute(self):
        intent = self.module.load_intent(
            self.module.stable_bytes(
                self.module.INTENT,
                self.module.INTENT_SIZE,
                self.module.INTENT_SHA256,
                "fixture intent",
            )
        )
        semantic_inputs = self.module._semantic_inputs(intent)
        implementation = {
            "carrier_model": self.module.current_regular_bytes(
                self.module.POSTLIVE_MODEL, "fixture post-live carrier model"
            ),
            "decoder": self.module.current_regular_bytes(
                self.module.POSTLIVE_DECODER, "fixture post-live decoder"
            ),
            "auditor": self.module.current_regular_bytes(
                self.module.POSTLIVE_AUDITOR, "fixture post-live auditor"
            ),
        }
        implementation["carrier_model"] = implementation["carrier_model"].replace(
            b"FAILURE_DETAIL = 0x6010",
            b"FAILURE_DETAIL = 0x6011",
        )
        frozen, carrier, decoder = self.module._load_bound_decoders(
            semantic_inputs, implementation
        )
        raw = self.module.stable_bytes(
            self.module.RETAINED[0],
            self.module.RETAINED_SIZE,
            self.module.RETAINED_SHA256,
            "fixture retained read",
        )
        with self.assertRaises(carrier.DesignError):
            self.module._record_result(
                raw,
                bytes.fromhex(intent["run_id"]),
                frozen,
                carrier,
                decoder,
            )

    def test_loaded_auditor_cannot_receipt_different_path_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "audit.py"
            changed.write_bytes(self.module._BOUND_AUDITOR_SOURCE + b"# drift\n")
            with mock.patch.object(self.module, "POSTLIVE_AUDITOR", changed):
                with self.assertRaisesRegex(
                    self.module.AuditError,
                    "executed post-live auditor bytes differ",
                ):
                    self.module.build_receipt()

    def test_preserved_receipt_is_exact_regeneration_and_mode(self):
        if not self.module.OUTPUT.exists():
            self.skipTest("private post-live receipt has not been published")
        payload = self.module.encode_receipt(self.receipt)
        self.assertEqual(
            self.module.stable_bytes(
                self.module.OUTPUT,
                len(payload),
                self.module.sha256(payload),
                "preserved post-live receipt",
            ),
            payload,
        )
        self.assertEqual(self.module.OUTPUT.stat().st_mode & 0o777, 0o400)

    def test_existing_receipt_mutation_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "receipt.json"
            target.write_bytes(b"foreign")
            before = target.read_bytes()
            with mock.patch.object(self.module, "OUTPUT", target):
                with self.assertRaises(self.module.AuditError):
                    self.module.write_receipt(self.receipt)
            self.assertEqual(target.read_bytes(), before)

    def test_receipt_mode_is_exact_under_umask_and_post_close_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "receipt.json"
            with mock.patch.object(self.module, "OUTPUT", target):
                previous = self.module.os.umask(0o777)
                try:
                    self.module.write_receipt(self.receipt)
                finally:
                    self.module.os.umask(previous)
            self.assertEqual(target.stat().st_mode & 0o777, 0o400)

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "receipt.json"
            original_close = self.module.os.close
            widened = False

            def close_then_widen(fd):
                nonlocal widened
                original_close(fd)
                if target.exists() and not widened:
                    target.chmod(0o600)
                    widened = True

            with mock.patch.object(self.module, "OUTPUT", target), mock.patch.object(
                self.module.os, "close", side_effect=close_then_widen
            ):
                with self.assertRaises(self.module.AuditError):
                    self.module.write_receipt(self.receipt)
            self.assertTrue(widened)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_auditor_has_no_device_or_command_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "os.system(",
            "Popen(",
            "check_output(",
            "adb ",
            "odin4",
            "--approval",
            "--device",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
