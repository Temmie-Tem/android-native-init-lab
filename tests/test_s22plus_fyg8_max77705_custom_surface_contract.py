import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_custom_surface_contract.py"
)
FULL_STOCK_INPUTS = (
    ROOT
    / "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)
DIAG_SOURCE = (
    ROOT
    / "workspace/public/src/kernel-modules/s22plus_max77705_mux_diag/"
    "s22plus_max77705_mux_diag.c"
)
DIAG_BUILD_RECEIPT = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "custom-module-build-20260812-07/build-audit.json"
)


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_max77705_custom_surface_contract_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


def valid_diag_source():
    return DIAG_SOURCE.read_text(encoding="utf-8")


class S22PlusFyg8Max77705CustomSurfaceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_parse_firmware_array(self):
        self.assertEqual(
            self.module.parse_firmware_array(
                "const uint8_t BOOT_FLASH_FW_PASS2[] = {0xc1, 0x6e, 0x40};"
            ),
            [0xC1, 0x6E, 0x40],
        )

    def test_full_stack_surface_is_rejected(self):
        with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
            self.module.validate_diag_source_text(
                valid_diag_source() + "\nmfd_add_devices(parent, 0, cells, 1, 0, 0, 0);"
            )

    def test_firmware_and_reset_surface_is_rejected(self):
        for token in ("BOOT_FLASH_FW_PASS2", "max77705_reset_ic"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
                    self.module.validate_diag_source_text(valid_diag_source() + token)

    def test_irq_and_workqueue_surface_is_rejected(self):
        for token in ("request_threaded_irq(", "queue_work("):
            with self.subTest(token=token):
                with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
                    self.module.validate_diag_source_text(valid_diag_source() + token)

    def test_notifier_power_and_protocol_surface_is_rejected(self):
        for token in (
            "blocking_notifier_call_chain(",
            "power_supply_",
            "max77705_alternate",
            "max77705_muic_afc",
            "DCD",
        ):
            with self.subTest(token=token):
                with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
                    self.module.validate_diag_source_text(valid_diag_source() + token)

    def test_writable_export_surface_is_rejected(self):
        mutated = valid_diag_source().replace("0444", "0644", 1)
        with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
            self.module.validate_diag_source_text(mutated)

    def test_full_com_usb_byte_is_required(self):
        mutated = valid_diag_source().replace(
            "#define S22PLUS_MAX77705_COM_USB 0x09",
            "#define S22PLUS_MAX77705_COM_USB 0x01",
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
            self.module.validate_diag_source_text(mutated)

    def test_exact_parent_i2c_address_is_required_before_claim(self):
        source = valid_diag_source()
        mutations = (
            (
                "#define S22PLUS_MAX77705_PARENT_ADDR 0x66",
                "#define S22PLUS_MAX77705_PARENT_ADDR 0x67",
            ),
            (
                "if (parent->addr != S22PLUS_MAX77705_PARENT_ADDR)\n\t\treturn -ENODEV;\n\tif (atomic_cmpxchg",
                "if (atomic_cmpxchg",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                with self.assertRaises(self.module.SurfaceError):
                    self.module.validate_diag_source_text(source.replace(old, new, 1))

    def test_pmic_revision_uses_stock_low_three_bit_identity(self):
        source = valid_diag_source()
        mutations = (
            (
                "#define S22PLUS_MAX77705_EXPECTED_PMIC_REV_LOW3 0x02",
                "#define S22PLUS_MAX77705_EXPECTED_PMIC_REV_LOW3 0x03",
            ),
            (
                "(result->pmic_rev & 0x7U) !=",
                "result->pmic_rev !=",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                with self.assertRaises(self.module.SurfaceError):
                    self.module.validate_diag_source_text(source.replace(old, new, 1))

    def test_write_must_remain_conditional_on_pre_value(self):
        mutated = valid_diag_source().replace(
            "if (pre != S22PLUS_MAX77705_COM_USB)", "if (true)", 1
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
            self.module.validate_diag_source_text(mutated)

    def test_ambiguous_write_retry_is_rejected(self):
        mutated = valid_diag_source().replace(
            "u8 command[2] = { S22PLUS_MAX77705_CONTROL1_WRITE, value };",
            "u8 command[2] = { S22PLUS_MAX77705_CONTROL1_WRITE, value }; "
            "for (;;) { break; }",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "loop|retry"):
            self.module.validate_diag_source_text(mutated)

    def test_second_write_call_site_is_rejected(self):
        needle = "rc = s22plus_max77705_control1_write_once("
        duplicate = (
            "rc = s22plus_max77705_control1_write_once(\n"
            "\t\t\t\tmuic, result, S22PLUS_MAX77705_COM_USB);\n\t\t"
        )
        mutated = valid_diag_source().replace(needle, duplicate + needle, 1)
        with self.assertRaisesRegex(self.module.SurfaceError, "one call site"):
            self.module.validate_diag_source_text(mutated)

    def test_post1_read_cannot_be_synthesized_or_moved_inside_write_branch(self):
        source = valid_diag_source()
        mutated = source.replace(
            "S22PLUS_MAX77705_SLOT_POST1, &post1",
            "S22PLUS_MAX77705_SLOT_PRE, &pre",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "order|after|synthesized"):
            self.module.validate_diag_source_text(mutated)

    def test_post2_and_retention_window_are_mandatory(self):
        source = valid_diag_source()
        mutations = (
            (
                "#define S22PLUS_MAX77705_RETENTION_MS 30000U",
                "#define S22PLUS_MAX77705_RETENTION_MS 1U",
            ),
            ("msleep(S22PLUS_MAX77705_RETENTION_MS);", ""),
            (
                "S22PLUS_MAX77705_SLOT_POST2, &post2",
                "S22PLUS_MAX77705_SLOT_POST1, &post1",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                mutated = source.replace(old, new, 1)
                with self.assertRaises(self.module.SurfaceError):
                    self.module.validate_diag_source_text(mutated)

    def test_extra_i2c_effect_is_rejected(self):
        mutated = valid_diag_source().replace(
            "result->stage = S22PLUS_MAX77705_STAGE_COMPLETE;",
            "i2c_smbus_write_word_data(muic, 0x10, 0);\n\t"
            "result->stage = S22PLUS_MAX77705_STAGE_COMPLETE;",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "I2C call surface"):
            self.module.validate_diag_source_text(mutated)

    def test_cached_result_getter_cannot_touch_i2c(self):
        mutated = valid_diag_source().replace(
            "return scnprintf(buffer, PAGE_SIZE, \"%s\", cached_result);",
            "i2c_smbus_read_byte_data(client, 0); "
            "return scnprintf(buffer, PAGE_SIZE, \"%s\", cached_result);",
            1,
        )
        with self.assertRaisesRegex(
            self.module.SurfaceError, "I2C call surface|external effect"
        ):
            self.module.validate_diag_source_text(mutated)

    def test_cached_result_requires_terminal_release_acquire_publication(self):
        source = valid_diag_source()
        mutations = (
            ("smp_store_release(&cached_result_ready, 1);", "cached_result_ready = 1;"),
            (
                "if (!smp_load_acquire(&cached_result_ready))",
                "if (!cached_result_ready)",
            ),
            ("return -EAGAIN;", "return 0;"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                with self.assertRaises(self.module.SurfaceError):
                    self.module.validate_diag_source_text(source.replace(old, new, 1))

    def test_cached_result_publication_must_follow_complete_encoding(self):
        source = valid_diag_source()
        publication = "\tsmp_store_release(&cached_result_ready, 1);\n"
        mutated = source.replace(publication, "", 1).replace(
            "\tchar *cursor = cached_result;\n",
            "\tchar *cursor = cached_result;\n" + publication,
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "publication"):
            self.module.validate_diag_source_text(mutated)

    def test_probe_must_remain_force_synchronous(self):
        mutated = valid_diag_source().replace(
            "PROBE_FORCE_SYNCHRONOUS", "PROBE_PREFER_ASYNCHRONOUS", 1
        )
        with self.assertRaisesRegex(
            self.module.SurfaceError, "force-synchronous|missing required"
        ):
            self.module.validate_diag_source_text(mutated)

    def test_post_readback_values_cannot_be_terminal_errors(self):
        mutated = valid_diag_source().replace(
            "result->stage = S22PLUS_MAX77705_STAGE_COMPLETE;",
            "if (post2 != S22PLUS_MAX77705_COM_USB)\n\t\treturn -EPROTO;\n\t"
            "result->stage = S22PLUS_MAX77705_STAGE_COMPLETE;",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "diagnostic results"):
            self.module.validate_diag_source_text(mutated)

    def test_successful_uic_poll_bytes_must_be_retained(self):
        mutated = valid_diag_source().replace(
            "result->poll_bytes[slot][attempt] = (u8)status;",
            "result->poll_bytes[slot][attempt] = 0U;",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
            self.module.validate_diag_source_text(mutated)

    def test_attempted_probe_must_cache_and_suppress_reprobe(self):
        mutated = valid_diag_source().replace(
            "/* Keep the one attempted probe bound so the I2C core cannot retry it. */\n\treturn 0;",
            "return rc;",
            1,
        )
        with self.assertRaisesRegex(
            self.module.SurfaceError, "missing required|cached terminal return"
        ):
            self.module.validate_diag_source_text(mutated)

    def test_kernel_callback_signatures_are_fixed(self):
        mutations = (
            (
                "struct i2c_client *parent, const struct i2c_device_id *id)",
                "struct i2c_client *parent)",
            ),
            (
                "char *buffer, const struct kernel_param *parameter)",
                "char *buffer, const void *parameter)",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                mutated = valid_diag_source().replace(old, new, 1)
                with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
                    self.module.validate_diag_source_text(mutated)

    def test_preferred_custom_shape_is_65_modules(self):
        result = self.module.validate_diag_source_text(valid_diag_source())
        self.assertEqual(result["preferred_total_module_count"], 65)
        self.assertEqual(result["exact_parent_i2c_address"], "0x66")
        self.assertEqual(result["control1_read_command_count"], 3)
        self.assertEqual(result["control1_write_maximum_count"], 1)
        self.assertEqual(result["stale_uic_latch_clear_count"], 1)
        self.assertTrue(result["post1_read_is_unconditional"])
        self.assertTrue(result["post2_read_is_after_retention_window"])
        self.assertEqual(result["retention_window_ms"], 30_000)
        self.assertTrue(result["ambiguous_write_retry_forbidden"])
        self.assertEqual(
            result["exact_pmic_identity"],
            {
                "pmic_id": "0x15",
                "pmic_rev_low3": "0x02",
                "pmic_rev_raw_retained": True,
            },
        )
        self.assertTrue(result["terminal_cache_release_acquire"])
        self.assertTrue(result["probe_force_synchronous"])

    def test_runtime_integration_arithmetic_and_arming_gate_are_fail_closed(self):
        parser_receipt = self.module.validate_runtime_parser_receipt(ROOT)
        diagnostic = {
            "runtime_integration": {
                "base_module_count": 61,
                "early_substrate_module_count": 3,
                "generic_early_load_count": 64,
                "diagnostic_staged_payload_count": 1,
                "total_packaged_module_count": 65,
                "diagnostic_forbidden_in_generic_load_loop": True,
                "inherited_bind_gate_timeout_sec": 20,
                "bind_gate_must_close_before_late_load": True,
                "late_load_forbidden_inside_bind_gate": True,
                "late_load_minimum_lifetime_sec": 31,
                "late_load_lifetime_exceeds_retention_window": True,
                "gadget_path_ready_before_late_load": True,
                "host_sidecar_armed_before_late_load": True,
                "dedicated_finit_module_callsite_count": 1,
                "successful_synchronous_finit_module_is_completion_witness": True,
                "probe_force_synchronous": True,
                "result_sample_may_precede_completion_but_parse_classify_publish_require_success": True,
                "result_read_error_yields_to_child_finit_module_failure_and_loader_deadline": True,
                "eagain_is_distinct_from_terminal_diagnostic_failure": True,
                "future_async_or_missing-client_drift_must_not_expose_cache": True,
            },
            "result_contract_arming_precondition": {
                "status": "REGISTERED_NOT_SATISFIED",
                "required_terminal_buckets": self.module.DIAG_RUNTIME_TERMINAL_BUCKETS,
                "eagain_binding_witness_fields": (
                    self.module.DIAG_EAGAIN_BINDING_WITNESS_FIELDS
                ),
                "eagain_observable_rows": self.module.DIAG_EAGAIN_OBSERVABLE_ROWS,
                "eagain_negative_invariants": (
                    self.module.DIAG_EAGAIN_NEGATIVE_INVARIANTS
                ),
                "eagain_classification_priority": (
                    self.module.DIAG_EAGAIN_CLASSIFICATION_PRIORITY
                ),
                "eagain_is_a_standalone_terminal": False,
                "eagain_binding_witness_cross_axis_required": True,
                "binding_witness_values_retained_end_to_end": True,
                "observable_obligation_surjectivity_required": True,
                "negative_invariant_decode_preimage_must_be_empty": True,
                "unique_retained_vector_reverse_map_required": True,
                "real_encoder_carrier_decoder_round_trip_required": True,
                "synthesized_retained_representation_required": True,
                "physical_condition_reproduction_required": False,
                "every_existing_mux_result_row_also_required": True,
                "blocks_packaging_and_f1_approval_until_receipted": True,
            },
            "terminal_row_admission_rule": (
                self.module.DIAG_TERMINAL_ROW_ADMISSION_RULE
            ),
            "retained_payload_contract": (
                self.module.DIAG_RETAINED_PAYLOAD_CONTRACT
            ),
            "post2_retention_matrix": self.module.DIAG_POST2_RETENTION_MATRIX,
            "runtime_result_parser": {
                "status": "HOST_EXECUTED_NOT_SYSFS_INTEGRATED",
                "receipt": parser_receipt,
                "allocation_free": True,
                "io_free": True,
                "strict_canonical_module_string_grammar": True,
                "python_summary_matches_actual_c": True,
                "aarch64_freestanding_compile": True,
                "sysfs_and_driver_override_require_fresh_d0": True,
                "blocks_packaging_until_live_callsite_is_wired_and_tested": True,
            },
        }
        self.assertTrue(self.module.validate_runtime_integration_contract(diagnostic))
        self.assertEqual(len(self.module.DIAG_RUNTIME_TERMINAL_BUCKETS), 9)
        self.assertEqual(
            len(set(self.module.DIAG_RUNTIME_TERMINAL_BUCKETS.values())), 9
        )
        self.assertEqual(len(self.module.DIAG_EAGAIN_OBSERVABLE_ROWS), 6)
        self.assertEqual(len(self.module.DIAG_EAGAIN_NEGATIVE_INVARIANTS), 1)
        for key, value in (
            ("generic_early_load_count", 65),
            ("late_load_minimum_lifetime_sec", 30),
            ("dedicated_finit_module_callsite_count", 2),
        ):
            with self.subTest(key=key):
                mutated = copy.deepcopy(diagnostic)
                mutated["runtime_integration"][key] = value
                with self.assertRaises(self.module.SurfaceError):
                    self.module.validate_runtime_integration_contract(mutated)
        mutated = copy.deepcopy(diagnostic)
        del mutated["result_contract_arming_precondition"][
            "required_terminal_buckets"
        ]["result_read_timeout"]
        with self.assertRaisesRegex(self.module.SurfaceError, "arming gate"):
            self.module.validate_runtime_integration_contract(mutated)
        for key in (
            "eagain_binding_witness_fields",
            "eagain_observable_rows",
            "eagain_negative_invariants",
            "eagain_classification_priority",
        ):
            with self.subTest(key=key):
                mutated = copy.deepcopy(diagnostic)
                del mutated["result_contract_arming_precondition"][key]
                with self.assertRaisesRegex(self.module.SurfaceError, "arming gate"):
                    self.module.validate_runtime_integration_contract(mutated)
        mutated = copy.deepcopy(diagnostic)
        mutated["result_contract_arming_precondition"][
            "eagain_is_a_standalone_terminal"
        ] = True
        with self.assertRaisesRegex(self.module.SurfaceError, "arming gate"):
            self.module.validate_runtime_integration_contract(mutated)
        mutated = copy.deepcopy(diagnostic)
        mutated["result_contract_arming_precondition"][
            "negative_invariant_decode_preimage_must_be_empty"
        ] = False
        with self.assertRaisesRegex(self.module.SurfaceError, "arming gate"):
            self.module.validate_runtime_integration_contract(mutated)
        mutated = copy.deepcopy(diagnostic)
        mutated["terminal_row_admission_rule"]["common_process_v2_gate"] = True
        with self.assertRaisesRegex(self.module.SurfaceError, "admission rule"):
            self.module.validate_runtime_integration_contract(mutated)
        mutated = copy.deepcopy(diagnostic)
        mutated["retained_payload_contract"]["record_count"] = 2
        with self.assertRaisesRegex(self.module.SurfaceError, "retained-payload"):
            self.module.validate_runtime_integration_contract(mutated)

    def test_atomic_json_replaces_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            self.module.atomic_json(output, {"value": 1})
            self.module.atomic_json(output, {"value": 2})
            self.assertEqual(output.read_text(encoding="utf-8"), '{\n  "value": 2\n}\n')

    def test_inventory_parser_rejects_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "inventory.tsv"
            inventory.write_text(
                "filename\tsize_bytes\tsha256\n"
                "one.ko\t1\ta\n"
                "one.ko\t1\ta\n",
                encoding="ascii",
            )
            digest = self.module.sha256_file(inventory)
            with self.assertRaisesRegex(self.module.SurfaceError, "duplicate"):
                self.module.parse_inventory(
                    inventory, expected_sha256=digest, expected_rows=2
                )

    def test_missing_linked_build_receipt_blocks_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                self.module.SurfaceError, "diagnostic linked-build receipt"
            ):
                self.module.validate_diag_build_receipt(
                    Path(directory),
                    {
                        "size": DIAG_SOURCE.stat().st_size,
                        "sha256": self.module.sha256_file(DIAG_SOURCE),
                    },
                )

    @unittest.skipUnless(
        DIAG_BUILD_RECEIPT.is_file(), "private diagnostic build receipt unavailable"
    )
    def test_linked_build_payload_is_bound_and_semantic(self):
        payload = json.loads(DIAG_BUILD_RECEIPT.read_text(encoding="ascii"))
        source_receipt = {
            "size": DIAG_SOURCE.stat().st_size,
            "sha256": self.module.sha256_file(DIAG_SOURCE),
            "validation": self.module.validate_diag_source_text(valid_diag_source()),
        }
        result = self.module.validate_diag_build_payload(payload, source_receipt)
        self.assertTrue(result["linked_build_satisfied"])
        self.assertTrue(result["source_contract_verified_before_compile"])
        self.assertEqual(result["module_sha256"], self.module.DIAG_MODULE_IDENTITY[1])

        mutated = copy.deepcopy(payload)
        mutated["modules"]["a"]["cfi"][
            "callback_relocations_target_cfi_jump_tables"
        ] = False
        with self.assertRaisesRegex(self.module.SurfaceError, "CFI mismatch"):
            self.module.validate_diag_build_payload(mutated, source_receipt)

    @unittest.skipUnless(FULL_STOCK_INPUTS.is_file(), "private FYG8 corpus unavailable")
    def test_full_stock_union_and_exclusive_consumers(self):
        result = self.module.audit(ROOT)
        self.assertEqual(
            result["stock_module_union"]["union_unique_module_count"], 491
        )
        self.assertEqual(
            result["stock_module_union"]["vendor_dlkm_only"][
                "vendor_dlkm_only_count"
            ],
            50,
        )
        self.assertEqual(
            set(result["stock_surface"]["exclusive_consumers"]),
            set(self.module.MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC),
        )
        self.assertTrue(
            all(
                consumers == ["pdic_max77705.ko"]
                for consumers in result["stock_surface"][
                    "exclusive_consumers"
                ].values()
            )
        )
        self.assertEqual(
            result["custom_contract"]["status"],
            "SOURCE_AND_LINKED_AB_ABI_QUALIFIED_RUNTIME_NOT_SATISFIED",
        )
        self.assertEqual(
            result["custom_contract"]["selected_design"],
            "POLLING_SINGLE_MODULE_MUX_DIAGNOSTIC",
        )
        self.assertEqual(result["custom_contract"]["preferred_total_module_count"], 65)
        self.assertEqual(
            result["custom_contract"]["rejected_full_pdic_custom_design"]["module_count"],
            66,
        )
        self.assertEqual(result["p315_plan"]["module_count"], 61)
        self.assertEqual(
            result["stock_surface"]["pdic_control_export_consumers"],
            self.module.PDIC_CONTROL_EXPORT_CONSUMERS,
        )
        self.assertEqual(
            result["stock_surface"]["if_cb_export_consumers"],
            self.module.IF_CB_EXPORT_CONSUMERS,
        )
        self.assertEqual(
            result["stock_surface"]["common_muic_sysfs"][
                "tree_wide_driver_c_definition_only"
            ],
            ["drivers/muic/common/muic_sysfs.c"],
        )
        self.assertEqual(
            result["custom_contract"]["write_inventory"]["status"],
            "BOUNDED_DIAGNOSTIC_EFFECT_SET_LINKED_ABI_AUDITED_NOT_PACKAGED",
        )
        self.assertTrue(
            result["diagnostic_linked_build"]["validation"][
                "linked_build_satisfied"
            ]
        )
        diagnostic = result["custom_contract"]["diagnostic"]
        self.assertEqual(
            diagnostic["load_timing"],
            "after gadget path activation and host sidecar arming; the probe "
            "then owns one bounded 30000-ms retention/correlation dwell",
        )
        integration = diagnostic["runtime_integration"]
        self.assertEqual(integration["generic_early_load_count"], 64)
        self.assertEqual(integration["total_packaged_module_count"], 65)
        self.assertEqual(integration["inherited_bind_gate_timeout_sec"], 20)
        self.assertEqual(integration["late_load_minimum_lifetime_sec"], 31)
        self.assertTrue(integration["diagnostic_forbidden_in_generic_load_loop"])
        self.assertTrue(integration["bind_gate_must_close_before_late_load"])
        arming = diagnostic["result_contract_arming_precondition"]
        self.assertEqual(arming["status"], "REGISTERED_NOT_SATISFIED")
        self.assertEqual(
            arming["required_terminal_buckets"],
            self.module.DIAG_RUNTIME_TERMINAL_BUCKETS,
        )
        self.assertEqual(
            tuple(arming["eagain_binding_witness_fields"]),
            self.module.DIAG_EAGAIN_BINDING_WITNESS_FIELDS,
        )
        self.assertEqual(
            arming["eagain_observable_rows"],
            self.module.DIAG_EAGAIN_OBSERVABLE_ROWS,
        )
        self.assertEqual(
            arming["eagain_negative_invariants"],
            self.module.DIAG_EAGAIN_NEGATIVE_INVARIANTS,
        )
        self.assertEqual(
            tuple(arming["eagain_classification_priority"]),
            self.module.DIAG_EAGAIN_CLASSIFICATION_PRIORITY,
        )
        self.assertFalse(arming["eagain_is_a_standalone_terminal"])
        self.assertTrue(arming["eagain_binding_witness_cross_axis_required"])
        self.assertTrue(arming["binding_witness_values_retained_end_to_end"])
        self.assertTrue(arming["observable_obligation_surjectivity_required"])
        self.assertTrue(arming["negative_invariant_decode_preimage_must_be_empty"])
        self.assertTrue(arming["unique_retained_vector_reverse_map_required"])
        self.assertTrue(arming["blocks_packaging_and_f1_approval_until_receipted"])
        self.assertEqual(
            diagnostic["terminal_row_admission_rule"],
            self.module.DIAG_TERMINAL_ROW_ADMISSION_RULE,
        )
        self.assertEqual(
            diagnostic["retained_payload_contract"],
            self.module.DIAG_RETAINED_PAYLOAD_CONTRACT,
        )
        self.assertEqual(
            diagnostic["post2_retention_matrix"],
            self.module.DIAG_POST2_RETENTION_MATRIX,
        )
        self.assertEqual(
            diagnostic["runtime_result_parser"]["status"],
            "HOST_EXECUTED_NOT_SYSFS_INTEGRATED",
        )
        self.assertFalse(
            diagnostic["runtime_result_parser"]["receipt"]["payload"]
            ["sysfs_path_or_driver_override_integrated"]
        )
        self.assertTrue(
            diagnostic["initial_uic_read_scope"][
                "whole_register_read_to_clear_accepted"
            ]
        )
        self.assertTrue(
            diagnostic["initial_uic_read_scope"]["raw_initial_byte_must_be_retained"]
        )
        self.assertFalse(
            diagnostic["interpretation_ceiling"][
                "control1_readback_proves_physical_switch_contact"
            ]
        )
        self.assertFalse(
            diagnostic["interpretation_ceiling"][
                "silent_result_refutes_physical_mux_hypothesis"
            ]
        )
        self.assertTrue(
            diagnostic["interpretation_ceiling"][
                "host_attach_is_independent_physical_witness"
            ]
        )
        self.assertEqual(
            result["custom_contract"]["write_inventory"]["retention_window_ms"],
            30_000,
        )


if __name__ == "__main__":
    unittest.main()
