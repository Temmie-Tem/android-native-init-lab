import argparse
import dataclasses
import tempfile
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p245_e1_decoder as p245_decoder  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p234_candidate_intent as candidate_intent  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_fyg8_p248_contract_spec as p248_spec  # noqa: E402
import s22plus_fyg8_p248_e1_decoder as p248_decoder  # noqa: E402
import s22plus_fyg8_p248_source_contract as p248  # noqa: E402
import s22plus_fyg8_p251_ssusb_dependency_audit as p251  # noqa: E402
import s22plus_fyg8_p251b_phy_nested_closure_audit as p251b  # noqa: E402
import s22plus_fyg8_p252_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p252_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p252_source_contract as p252  # noqa: E402
import s22plus_fyg8_source_contracts as contracts  # noqa: E402


class S22PlusFyg8P252SourceContractTest(unittest.TestCase):
    RUN_ID = bytes.fromhex("52" * 16)

    @staticmethod
    def _header() -> bytes:
        model = decoder.model
        return (
            model.LONG_FAMILY
            + bytes(
                [
                    (model.FORMAT_VERSION << 4)
                    | model.PROFILE_NUMBERS["E2"]
                ]
            )
            + S22PlusFyg8P252SourceContractTest.RUN_ID
        )

    def test_descriptor_preserves_p248_and_matches_p251_audits(self):
        self.assertEqual(spec.STEPS, p248_spec.STEPS)
        self.assertEqual(spec.STAGE_SEQUENCE, p248_spec.STAGE_SEQUENCE)
        self.assertEqual(spec.TERMINAL_STAGE, p248_spec.TERMINAL_STAGE)
        self.assertEqual((spec.SSUSB_STAGE, spec.SSUSB_GATE_INDEX), (0x84, 9))
        self.assertEqual(len(spec.BIND_CLASSIFIERS), 15)
        self.assertEqual(len(spec.CLASSIFIER_DETAILS), 17)
        expected = [
            (int(detail, 16), path)
            for _name, path, detail in p251.PROVIDER_CHECKS
        ]
        expected.extend(
            (int(row["detail"], 16), row["path"])
            for row in p251b.nested_checks()
        )
        expected.extend(
            (int(detail, 16), path)
            for _name, path, detail in p251.PHY_CHECKS
        )
        self.assertEqual(
            [(row.value, row.path) for row in spec.BIND_CLASSIFIERS],
            expected,
        )
        self.assertEqual(
            tuple(row.value for row in spec.BIND_CLASSIFIERS),
            (
                0xA01,
                0xA02,
                0xA03,
                0xA04,
                0xA05,
                0xA06,
                0xA07,
                0xA08,
                0xA09,
                0xA0A,
                0xA0B,
                0xA0C,
                0xA0D,
                0xA20,
                0xA21,
            ),
        )

    def test_only_exact_classifier_details_are_added_at_ssusb(self):
        for step in spec.STEPS:
            added = set(spec.failure_details(step)) - set(
                p248_spec.failure_details(step)
            )
            self.assertEqual(
                added,
                set(spec.CLASSIFIER_VALUES)
                if step.stage == spec.SSUSB_STAGE
                else set(),
            )
            for detail in range(0xA00, 0x1000):
                self.assertEqual(
                    spec.failure_detail_allowed(step, detail),
                    step.stage == spec.SSUSB_STAGE
                    and detail in spec.CLASSIFIER_VALUES,
                )
        ssusb = spec.step_for_stage(spec.SSUSB_STAGE)
        self.assertTrue(spec.failure_detail_allowed(ssusb, 0xA30))
        self.assertFalse(spec.failure_detail_allowed(ssusb, 0xA31))
        self.assertFalse(spec.failure_detail_allowed(ssusb, 0xA00))
        self.assertEqual(spec.detail_name(0xA30), (
            "all-known-ready-parent-absent-after-grace"
        ))

    def test_descriptor_mutations_are_rejected(self):
        first = spec.CLASSIFIER_DETAILS[0]
        mutations = (
            dataclasses.replace(first, value=spec.CLASSIFIER_DETAILS[1].value),
            dataclasses.replace(first, name=spec.CLASSIFIER_DETAILS[1].name),
            dataclasses.replace(first, path="/tmp/not-sysfs"),
            dataclasses.replace(first, expected_symlink_basename="wrong"),
        )
        for changed in mutations:
            rows = (changed,) + spec.CLASSIFIER_DETAILS[1:]
            with self.subTest(changed=changed):
                with self.assertRaises(spec.SpecError):
                    spec.validate_classifier_details(rows)
        swapped = (
            spec.CLASSIFIER_DETAILS[1],
            spec.CLASSIFIER_DETAILS[0],
            *spec.CLASSIFIER_DETAILS[2:],
        )
        with self.assertRaisesRegex(spec.SpecError, "priority"):
            spec.validate_classifier_details(swapped)

    def test_decoder_accepts_a30_without_changing_raw_active_shape(self):
        model = decoder.model
        header = self._header()
        generation = spec.ordinal_for_stage(spec.SSUSB_STAGE) + 1
        previous = spec.STEPS[generation - 2]
        slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
        slots[(generation - 1) & 1] = decoder.encode_slot(
            header,
            generation=generation - 1,
            stage=previous.stage,
            outcome=model.OUTCOME_PROGRESS,
            item_index=previous.item_index,
            detail=0,
        )
        slots[generation & 1] = decoder.encode_slot(
            header,
            generation=generation,
            stage=spec.SSUSB_STAGE,
            outcome=model.OUTCOME_FAILURE,
            item_index=spec.SSUSB_GATE_INDEX,
            detail=0xA30,
        )
        record = header + b"".join(slots)
        result = decoder.decode_record(
            record,
            expected_profile="E2",
            expected_run_id=self.RUN_ID,
        )
        self.assertEqual(
            result["active"],
            {
                "slot_id": generation & 1,
                "generation": generation,
                "stage": 0x84,
                "outcome": model.OUTCOME_FAILURE,
                "item_index": 9,
                "detail": 0xA30,
            },
        )
        self.assertEqual(
            result["active_semantics"],
            {
                "detail_kind": "classifier",
                "detail_name": (
                    "all-known-ready-parent-absent-after-grace"
                ),
            },
        )
        with self.assertRaisesRegex(
            p248_decoder.DecodeError, "outside the contract"
        ):
            p248_decoder.decode_record(
                record,
                expected_profile="E2",
                expected_run_id=self.RUN_ID,
            )

    def test_unknown_reserved_detail_is_rejected_by_decoder(self):
        model = decoder.model
        header = self._header()
        generation = spec.ordinal_for_stage(spec.SSUSB_STAGE) + 1
        raw = p245_decoder.encode_slot(
            header,
            generation=generation,
            stage=spec.SSUSB_STAGE,
            outcome=model.OUTCOME_FAILURE,
            item_index=spec.SSUSB_GATE_INDEX,
            detail=0xA31,
        )
        slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
        slots[generation & 1] = raw
        with self.assertRaisesRegex(decoder.DecodeError, "outside the contract"):
            decoder.decode_record(
                header + b"".join(slots),
                expected_profile="E2",
                expected_run_id=self.RUN_ID,
            )

    def test_generated_sources_preserve_plan_and_band_first_dispatch(self):
        historical = p248.generate(ROOT)
        generated = p252.generate(ROOT)
        self.assertEqual(generated["plan"], historical["plan"])
        self.assertEqual(historical, p248.generate(ROOT))
        result = p252.audit_generated_semantics(generated, historical)
        self.assertTrue(result["common_finalizer_enforced"])

        checkpoint = generated["checkpoint"].decode("ascii")
        self.assertNotIn(
            "detail > S22_P248_DETAIL_READ_ERROR_MAX", checkpoint
        )
        self.assertLess(
            checkpoint.index(
                "detail >= S22_P248_DETAIL_REGRESSION_BASE"
            ),
            checkpoint.index(
                "detail == k_p252_classifier_details[index]"
            ),
        )
        patch = generated["patch"].decode("ascii")
        self.assertEqual(
            patch.count(
                "static noinline __used bool "
                "s22_fyg8_e1_request_allowed("
            ),
            1,
        )
        self.assertLess(
            patch.index("detail >= 0x800 && detail <= 0x8ff"),
            patch.index("s22_fyg8_e2_sequence[ordinal] =="),
        )

    def test_runtime_has_bounded_race_aware_classifier(self):
        runtime = p252.generate(ROOT)["runtime"].decode("ascii")
        self.assertEqual(
            runtime.count("#define S22_P241_GATE_TIMEOUT_SEC 20LL"), 1
        )
        self.assertEqual(
            runtime.count("#define S22_P252_GRACE_SEC 5LL"), 1
        )
        self.assertEqual(runtime.count("p252_classify_ssusb(1)"), 1)
        self.assertEqual(runtime.count("p252_classify_ssusb(0)"), 1)
        self.assertEqual(runtime.count("return p252_run_grace();"), 1)
        self.assertEqual(runtime.count("int post_grace_drain = 0;"), 1)
        self.assertEqual(runtime.count("post_grace_drain = 1;"), 1)
        self.assertIn(
            "if (post_grace_drain) {\n"
            "            if (advanced) {\n"
            "                continue;\n"
            "            }\n"
            "            fail_at(",
            runtime,
        )
        self.assertIn(
            "amount != 2 || extra_amount != 0 || value[1] != '\\n'",
            runtime,
        )
        self.assertIn(
            "for (size_t index = 0; "
            "index < S22_P252_SSUSB_GATE_INDEX; ++index)",
            runtime,
        )
        self.assertEqual(
            runtime.count(
                "fail_at(\n        S22_P252_SSUSB_STAGE,"
            ),
            2,
        )
        self.assertLess(
            runtime.index("p252_revalidate_prior_or_fail();"),
            runtime.index(
                "long parent_rc = p241_check_gate("
                "S22_P252_SSUSB_GATE_INDEX);"
            ),
        )
        self.assertLess(
            runtime.index("p252_read_waiting_for_supplier(&waiting)"),
            runtime.index("k_p252_bind_classifiers[index]"),
        )
        self.assertLess(
            runtime.index("k_p252_bind_classifiers[index]"),
            runtime.rindex("p252_read_waiting_for_supplier(&waiting)"),
        )

    def test_generated_semantic_mutations_are_rejected(self):
        historical = p248.generate(ROOT)
        generated = p252.generate(ROOT)
        mutations = (
            (
                "runtime",
                b'"/sys/bus/platform/drivers/gdsc/149004.qcom,gdsc",',
                b'"/sys/bus/platform/drivers/gdsc/149004.qcom,wrong",',
            ),
            (
                "runtime",
                b"#define S22_P252_GRACE_SEC 5LL",
                b"#define S22_P252_GRACE_SEC 6LL",
            ),
            (
                "runtime",
                b"amount != 2 || extra_amount != 0",
                b"amount != 3 || extra_amount != 0",
            ),
            (
                "runtime",
                b"return p252_classify_ssusb(0);",
                b"return p252_finalize_classifier(0xa30L);",
            ),
            (
                "runtime",
                b"return p252_finalize_classifier(classifier->detail);",
                b"fail_at(S22_P252_SSUSB_STAGE, "
                b"S22_P252_SSUSB_GATE_INDEX, classifier->detail);",
            ),
            (
                "runtime",
                b"post_grace_drain = 1;",
                b"post_grace_drain = 0;",
            ),
            (
                "checkpoint",
                b"0xa30U",
                b"0xa31U",
            ),
            (
                "patch",
                b"0xa30,",
                b"0xa31,",
            ),
        )
        for key, old, new in mutations:
            with self.subTest(key=key, old=old):
                changed = dict(generated)
                self.assertEqual(changed[key].count(old), 1)
                changed[key] = changed[key].replace(old, new)
                with self.assertRaises(p252.SourceContractError):
                    p252.audit_generated_semantics(changed, historical)

    def test_implementation_cross_compiles_and_patch_applies(self):
        result = p252.implementation_result(ROOT)
        self.assertEqual(result["verdict"], p252.IMPLEMENTATION_VERDICT)
        self.assertTrue(result["historical_p248_unchanged"])
        self.assertTrue(result["patch"]["clean_apply"])
        self.assertTrue(result["linked_userspace"]["static_aarch64"])
        self.assertTrue(
            result["linked_userspace"]["two_link_reproducible"]
        )
        self.assertTrue(result["path_map"]["p251_p251b_exact"])
        self.assertFalse(result["safety"]["kernel_built"])
        self.assertFalse(result["safety"]["candidate_created"])
        self.assertFalse(result["safety"]["device_contact"])

    def test_selector_and_source_inventory_register_p252_only_once(self):
        selected = contracts.select(p252.CONTRACT_ID, "E2")
        self.assertEqual(selected.contract_id, p252.CONTRACT_ID)
        self.assertEqual(selected.decoder.DECODER_ID, decoder.DECODER_ID)
        self.assertEqual(
            contracts.contract_ids().count(p252.CONTRACT_ID), 1
        )
        data = selected.source_bytes(ROOT)
        self.assertEqual(set(data), set(p252.SOURCE_KEYS))
        self.assertIn("p248_source_contract", data)
        self.assertIn("p251_dependency_audit", data)
        self.assertIn("p251b_nested_audit", data)

    def test_candidate_contract_round_trip_uses_p252_materialized_sources(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="p252-roundtrip-", dir=private_tmp
        ) as temporary:
            output = Path(temporary) / "intent"
            created = candidate_intent.create(
                argparse.Namespace(
                    source=candidate_intent.DEFAULT_SOURCE,
                    base_patch=None,
                    out=output,
                    nonce_hex="62" * 16,
                    profile="E2",
                    source_contract_id=p252.CONTRACT_ID,
                )
            )
            reopened = candidate_contract.verify(
                ROOT,
                ROOT / candidate_intent.DEFAULT_SOURCE,
                output / "candidate-intent.json",
                output / "candidate.patch",
            )
            self.assertEqual(created["schema"], p252.INTENT_SCHEMA)
            self.assertEqual(reopened["schema"], p252.CONTRACT_SCHEMA)
            self.assertEqual(
                reopened["source_contract_id"], p252.CONTRACT_ID
            )
            materialized = output / "materialized-sources"
            self.assertEqual(
                {path.name for path in materialized.iterdir()},
                set(p252.MATERIALIZED_FILENAMES.values()),
            )
            userspace_result = userspace.build_userspace(
                argparse.Namespace(
                    source=candidate_intent.DEFAULT_SOURCE,
                    intent=output / "candidate-intent.json",
                    patch=output / "candidate.patch",
                    out=Path(temporary) / "userspace",
                )
            )
            self.assertEqual(
                userspace_result["verdict"], p252.USERSPACE_VERDICT
            )
            self.assertTrue(userspace_result["two_build_byte_identical"])
            normalized = evidence.validate_candidate_source_preimage(
                reopened, "E2", reopened["run_id"]
            )
            self.assertEqual(set(normalized), set(p252.SOURCE_KEYS))

    def test_reachable_domain_adds_exactly_seventeen_variants(self):
        self.assertEqual(
            p252.REACHABLE_VARIANTS,
            p248.REACHABLE_VARIANTS + len(spec.CLASSIFIER_DETAILS),
        )
        result = p252.validate_reachable_records(self.RUN_ID)
        self.assertEqual(
            result["reachable_slot_variants"], p252.REACHABLE_VARIANTS
        )
        self.assertEqual(result["classifier_detail_count"], 17)
        self.assertTrue(result["verified"])

    def test_linked_classifier_tables_are_exact_and_mutation_sensitive(self):
        expected = p252.linked_table_bytes()
        result = p252.audit_linked_tables(expected)
        self.assertTrue(result["classifier_whitelist_verified"])
        self.assertEqual(
            expected["s22_fyg8_e2_classifier_stages"],
            bytes([spec.SSUSB_STAGE] * 17),
        )
        self.assertEqual(
            expected["s22_fyg8_e2_classifier_details"][-2:],
            (0xA30).to_bytes(2, "little"),
        )
        changed = dict(expected)
        changed["s22_fyg8_e2_classifier_details"] = (
            changed["s22_fyg8_e2_classifier_details"][:-2]
            + (0xA31).to_bytes(2, "little")
        )
        with self.assertRaisesRegex(
            p252.SourceContractError, "linked descriptor tables differ"
        ):
            p252.audit_linked_tables(changed)

    def test_linked_validator_requires_writer_call_and_both_whitelists(self):
        expected_item = """
0000000000100000 <s22_fyg8_e1_expected_item>:
0000000000100004: 90000008 adrp x8, 200000
0000000000100008: 91008108 add x8, x8, #0x20
000000000010000c: 38696908 ldrb w8, [x8, x9]
"""
        detail_validator = """
0000000000100100 <s22_fyg8_e1_detail_allowed>:
0000000000100104: 90000008 adrp x8, 200000
0000000000100108: 91010108 add x8, x8, #0x40
000000000010010c: 38696908 ldrb w8, [x8, x9]
0000000000100110: 9000000a adrp x10, 200000
0000000000100114: 9101814a add x10, x10, #0x60
0000000000100118: 7869794a ldrh w10, [x10, x9, lsl #1]
"""
        request_validator = """
0000000000100180 <s22_fyg8_e1_request_allowed>:
0000000000100184: 94000001 bl 100000 <s22_fyg8_e1_expected_item>
0000000000100188: 94000002 bl 100100 <s22_fyg8_e1_detail_allowed>
"""
        writer = """
0000000000100200 <s22_fyg8_e1_write>:
0000000000100204: 94000001 bl 100180 <s22_fyg8_e1_request_allowed>
"""
        disassembly = {
            "s22_fyg8_e1_expected_item": expected_item,
            "s22_fyg8_e1_request_allowed": request_validator,
            "s22_fyg8_e1_detail_allowed": detail_validator,
            "s22_fyg8_e1_write": writer,
        }
        calls = {
            "s22_fyg8_e1_expected_item": [],
            "s22_fyg8_e1_request_allowed": [
                "s22_fyg8_e1_expected_item",
                "s22_fyg8_e1_detail_allowed",
            ],
            "s22_fyg8_e1_detail_allowed": [],
            "s22_fyg8_e1_write": ["s22_fyg8_e1_request_allowed"],
        }
        addresses = {
            "s22_fyg8_e2_items": 0x200020,
            "s22_fyg8_e2_classifier_stages": 0x200040,
            "s22_fyg8_e2_classifier_details": 0x200060,
        }
        result = p252.audit_linked_validator(
            disassembly, calls, addresses
        )
        self.assertTrue(result["writer_calls_request_validator"])
        self.assertTrue(result["request_calls_detail_validator"])
        self.assertTrue(result["validator_loads_classifier_stage_table"])
        self.assertTrue(result["validator_loads_classifier_detail_table"])

        changed_calls = {name: list(value) for name, value in calls.items()}
        changed_calls["s22_fyg8_e1_write"].remove(
            "s22_fyg8_e1_request_allowed"
        )
        with self.assertRaisesRegex(
            p252.SourceContractError, "does not call"
        ):
            p252.audit_linked_validator(
                disassembly, changed_calls, addresses
            )
        changed_disassembly = dict(disassembly)
        changed_disassembly["s22_fyg8_e1_detail_allowed"] = (
            detail_validator.replace("ldrh w10", "ldrb w10")
        )
        with self.assertRaisesRegex(
            p252.SourceContractError, "detail whitelist"
        ):
            p252.audit_linked_validator(
                changed_disassembly, calls, addresses
            )


if __name__ == "__main__":
    unittest.main()
