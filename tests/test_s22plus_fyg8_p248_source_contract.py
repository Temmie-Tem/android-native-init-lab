import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p234_candidate_intent as candidate_intent  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as runner  # noqa: E402
import s22plus_fyg8_p244_e2_provider_sources as p244  # noqa: E402
import s22plus_fyg8_p245_source_contract as p245  # noqa: E402
import s22plus_fyg8_p248_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p248_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p248_source_contract as p248  # noqa: E402
import s22plus_fyg8_source_contracts as contracts  # noqa: E402


class S22PlusFyg8P248SourceContractTest(unittest.TestCase):
    RUN_ID = bytes.fromhex("48" * 16)

    def test_descriptor_is_exact_and_has_no_parallel_upper_bound(self):
        self.assertEqual(len(spec.STEPS), 80)
        self.assertEqual(spec.MODULE_START_ORDINAL, 8)
        self.assertEqual(spec.GATE_START_ORDINAL, 67)
        self.assertEqual(spec.GATE_COUNT, 12)
        self.assertEqual(spec.TERMINAL_ORDINAL, 79)
        self.assertEqual(spec.STAGE_SEQUENCE[-8:], tuple(range(0x80, 0x87)) + (0x8F,))
        self.assertEqual(
            tuple(
                step.item_index
                for step in spec.STEPS
                if step.kind == spec.KIND_GATE
            ),
            tuple(range(12)),
        )

    def test_detail_bands_are_disjoint_and_exhaustive(self):
        gate = spec.step_for_stage(0x83)
        allowed = {
            detail
            for detail in range(1, 0x1000)
            if spec.failure_detail_allowed(gate, detail)
        }
        expected = set(range(1, 0x800))
        expected.update(range(0x800, 0x808))
        expected.update(range(0x900, 0x909))
        self.assertEqual(allowed, expected)
        self.assertFalse(
            any(
                spec.failure_detail_allowed(gate, detail)
                for detail in range(0xA00, 0x1000)
            )
        )
        module = spec.step_for_stage(0x40)
        self.assertTrue(spec.failure_detail_allowed(module, 110))
        self.assertFalse(spec.failure_detail_allowed(module, 0x800))
        self.assertFalse(spec.failure_detail_allowed(module, 0x900))

    def test_frontier_flap_semantics_are_explicit(self):
        frontier = spec.step_for_stage(0x7E)
        self.assertEqual(frontier.gate_index, 3)
        self.assertTrue(
            spec.failure_detail_allowed(
                frontier, spec.regression_detail(0)
            )
        )
        self.assertTrue(
            spec.failure_detail_allowed(
                frontier, spec.regression_detail(2)
            )
        )
        self.assertFalse(
            spec.failure_detail_allowed(
                frontier, spec.regression_detail(3)
            )
        )
        self.assertTrue(
            spec.failure_detail_allowed(
                frontier, spec.read_error_detail(3)
            )
        )
        self.assertFalse(
            spec.failure_detail_allowed(
                frontier, spec.read_error_detail(4)
            )
        )
        self.assertTrue(spec.failure_detail_allowed(frontier, 110))

    def test_synthetic_stage_updates_tables_without_validator_range_edit(self):
        mutated = spec.build_mutated_steps(0x87)
        synthetic = mutated[-2]
        self.assertEqual(
            (synthetic.stage, synthetic.item_index, synthetic.gate_index),
            (0x87, 12, 12),
        )
        spec.validate_slot(
            generation=len(mutated) - 1,
            stage=0x87,
            outcome=spec.model.OUTCOME_PROGRESS,
            item_index=12,
            detail=0,
            steps=mutated,
        )
        tables = p248._render_kernel_tables(mutated).decode("ascii")
        validator = p248._render_kernel_validator(gate_count=13).decode("ascii")
        checkpoint = p248._render_checkpoint_steps(mutated).decode("ascii")
        self.assertIn("0x87", tables)
        self.assertIn("12", tables)
        self.assertIn("encoded_index >= 13", validator)
        self.assertNotIn("stage <= 0x86", validator)
        self.assertNotIn("stage <= 0x82", validator)
        self.assertIn("{0x87U, 12U, S22_P248_STEP_GATE}", checkpoint)
        mutated_patch = p248.transform_patch(
            p244.generate(ROOT)["patch"], mutated
        )
        self.assertIn(b"0x87", mutated_patch)
        with tempfile.TemporaryDirectory(prefix="p248-mutated-patch-") as name:
            audit = p248._audit_patch(
                ROOT, mutated_patch, Path(name), mutated
            )
            self.assertTrue(audit["verified"])

    def test_historical_generated_sources_remain_byte_exact(self):
        historical = p244.generate(ROOT)
        self.assertEqual(
            {
                name: p244.receipt(data)["sha256"]
                for name, data in historical.items()
            },
            p244.GENERATED_SHA256,
        )
        selected = contracts.select(p245.CONTRACT_ID, "E2")
        self.assertEqual(selected.source_bytes(ROOT), p245.source_bytes(ROOT))
        self.assertIn("decoder_layout_delegate", p248.SOURCE_KEYS)

    def test_generated_adapter_closes_both_source_defects(self):
        result = p248.implementation_result(ROOT)
        self.assertEqual(result["verdict"], p248.IMPLEMENTATION_VERDICT)
        self.assertTrue(result["patch"]["clean_apply"])
        self.assertTrue(result["linked_userspace"]["two_link_reproducible"])
        generated = p248.generate(ROOT)
        runtime = generated["runtime"].decode("ascii")
        checkpoint = generated["checkpoint"].decode("ascii")
        patch = generated["patch"].decode("ascii")
        self.assertIn(
            "S22_P241_GATE_STAGE_BASE + (uint8_t)completed", runtime
        )
        self.assertGreaterEqual(checkpoint.count("return -EINVAL;"), 4)
        self.assertLess(
            runtime.index("for (size_t index = 0; index <= completed; ++index)"),
            runtime.index("S22_P248_DETAIL_REGRESSION_BASE + (long)index"),
        )
        self.assertIn("k_p248_e2_steps[]", checkpoint)
        self.assertNotIn("S22_P244_STAGE_E2_GATE_11", checkpoint)
        self.assertNotIn("S22_P241_STAGE_E2_MODULE_58", checkpoint)
        self.assertIn("s22_fyg8_e2_items[] __used", patch)
        self.assertNotIn(
            "request->stage >= 0x7b && request->stage <= 0x82", patch
        )

    def test_decoder_accepts_structured_detail_and_rejects_reserved_band(self):
        model = decoder.model
        header = (
            model.LONG_FAMILY
            + bytes(
                [
                    (model.FORMAT_VERSION << 4)
                    | model.PROFILE_NUMBERS["E2"]
                ]
            )
            + self.RUN_ID
        )
        stage = 0x7E
        generation = spec.ordinal_for_stage(stage) + 1
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
            stage=stage,
            outcome=model.OUTCOME_FAILURE,
            item_index=3,
            detail=spec.regression_detail(1),
        )
        result = decoder.decode_record(
            header + b"".join(slots),
            expected_profile="E2",
            expected_run_id=self.RUN_ID,
        )
        self.assertEqual(result["active"]["detail"], 0x801)

        slots[generation & 1] = p245.decoder.encode_slot(
            header,
            generation=generation,
            stage=stage,
            outcome=model.OUTCOME_FAILURE,
            item_index=3,
            detail=0xA00,
        )
        with self.assertRaisesRegex(
            decoder.DecodeError, "outside the contract"
        ):
            decoder.decode_record(
                header + b"".join(slots),
                expected_profile="E2",
                expected_run_id=self.RUN_ID,
            )

    def test_linked_table_audit_is_exact_and_mutation_sensitive(self):
        expected = p248.linked_table_bytes()
        result = p248.audit_linked_tables(expected)
        self.assertTrue(result["descriptor_bytes_verified"])
        changed = dict(expected)
        changed["s22_fyg8_e2_items"] = (
            changed["s22_fyg8_e2_items"][:-2] + b"\x08\x00"
        )
        with self.assertRaisesRegex(
            p248.SourceContractError, "linked descriptor tables differ"
        ):
            p248.audit_linked_tables(changed)

    def test_linked_validator_requires_writer_call_and_descriptor_load(self):
        expected_item = """
ffffffc008021000 <s22_fyg8_e1_expected_item>:
ffffffc008021004: 90000008 adrp x8, ffffffc009ed3000 <s22_fyg8_e2_items>
ffffffc008021008: 91008108 add x8, x8, #0x20
ffffffc00802100c: 38696908 ldrb w8, [x8, x9]
"""
        writer = """
ffffffc008022000 <s22_fyg8_e1_write>:
ffffffc008022004: 94000001 bl ffffffc008021000 <s22_fyg8_e1_expected_item>
"""
        disassembly = {
            "s22_fyg8_e1_expected_item": expected_item,
            "s22_fyg8_e1_write": writer,
        }
        calls = {
            "s22_fyg8_e1_expected_item": [],
            "s22_fyg8_e1_write": ["s22_fyg8_e1_expected_item"],
        }
        addresses = {"s22_fyg8_e2_items": 0xFFFFFFC009ED3020}
        result = p248.audit_linked_validator(
            disassembly, calls, addresses
        )
        self.assertTrue(result["validator_loads_item_table"])
        changed_calls = dict(calls)
        changed_calls["s22_fyg8_e1_write"] = []
        with self.assertRaisesRegex(
            p248.SourceContractError, "does not call"
        ):
            p248.audit_linked_validator(
                disassembly, changed_calls, addresses
            )
        changed_disassembly = dict(disassembly)
        changed_disassembly["s22_fyg8_e1_expected_item"] += (
            "\ncmp w8, #0x8\n"
        )
        with self.assertRaisesRegex(
            p248.SourceContractError, "stale eight-item"
        ):
            p248.audit_linked_validator(
                changed_disassembly, calls, addresses
            )
        wrong_load = dict(disassembly)
        wrong_load["s22_fyg8_e1_expected_item"] = (
            expected_item.replace("[x8, x9]", "[x10, x9]")
        )
        with self.assertRaisesRegex(
            p248.SourceContractError, "does not load"
        ):
            p248.audit_linked_validator(wrong_load, calls, addresses)
        clobbered = dict(disassembly)
        clobbered["s22_fyg8_e1_expected_item"] = (
            expected_item.replace(
                "ffffffc00802100c: 38696908 ldrb",
                "ffffffc00802100a: aa0003e8 mov x8, x0\n"
                "ffffffc00802100c: 38696908 ldrb",
            )
        )
        with self.assertRaisesRegex(
            p248.SourceContractError, "does not load"
        ):
            p248.audit_linked_validator(clobbered, calls, addresses)
        stale_writer = dict(disassembly)
        stale_writer["s22_fyg8_e1_write"] += "\ncmp w14, #8\n"
        with self.assertRaisesRegex(
            p248.SourceContractError, "stale eight-item"
        ):
            p248.audit_linked_validator(stale_writer, calls, addresses)

    def test_selector_and_candidate_contract_round_trip_p248(self):
        selected = contracts.select(p248.CONTRACT_ID, "E2")
        self.assertEqual(selected.contract_id, p248.CONTRACT_ID)
        self.assertEqual(selected.decoder.DECODER_ID, decoder.DECODER_ID)
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="p248-roundtrip-", dir=private_tmp
        ) as temporary:
            output = Path(temporary) / "intent"
            created = candidate_intent.create(
                argparse.Namespace(
                    source=candidate_intent.DEFAULT_SOURCE,
                    base_patch=None,
                    out=output,
                    nonce_hex="58" * 16,
                    profile="E2",
                    source_contract_id=p248.CONTRACT_ID,
                )
            )
            reopened = candidate_contract.verify(
                ROOT,
                ROOT / candidate_intent.DEFAULT_SOURCE,
                output / "candidate-intent.json",
                output / "candidate.patch",
            )
            self.assertEqual(created["schema"], p248.INTENT_SCHEMA)
            self.assertEqual(reopened["schema"], p248.CONTRACT_SCHEMA)
            self.assertEqual(
                reopened["source_contract_id"], p248.CONTRACT_ID
            )
            materialized = output / "materialized-sources"
            self.assertEqual(
                {path.name for path in materialized.iterdir()},
                set(p248.MATERIALIZED_FILENAMES.values()),
            )
            value = json.loads(
                (output / "candidate-intent.json").read_text("ascii")
            )
            self.assertEqual(
                set(value["identity_preimage"]["sources"]),
                set(p248.SOURCE_KEYS),
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
                userspace_result["verdict"], p248.USERSPACE_VERDICT
            )
            self.assertTrue(userspace_result["two_build_byte_identical"])
            normalized = evidence.validate_candidate_source_preimage(
                reopened, "E2", reopened["run_id"]
            )
            acceptance = {
                "kind": evidence.E1_LATEST_STAGE_KIND,
                "source": evidence.CHECKPOINT_SOURCE,
                "decoder": decoder.DECODER_ID,
                "policy_id": decoder.POLICY_ID,
                "profile": "E2",
                "source_contract_id": p248.CONTRACT_ID,
                "run_id": reopened["run_id"],
                "long_family_hex": decoder.model.LONG_FAMILY.hex(),
                "unsat_family_hex": decoder.model.UNSAT_FAMILY.hex(),
                "terminal_stage": spec.TERMINAL_STAGE,
                "minimum_success_count": 1,
                "clean_baseline_required": True,
                "contract": {
                    name: {
                        "path": f"private/{name}.json",
                        "size": 1,
                        "sha256": "1" * 64,
                    }
                    for name in (
                        "candidate_static",
                        "run_manifest",
                        "static_check",
                    )
                },
            }
            self.assertEqual(
                evidence.validate_acceptance(acceptance)[
                    "source_contract_id"
                ],
                p248.CONTRACT_ID,
            )
            execution = runner.execution_critical_source_receipts(acceptance)
            self.assertIn("source_contract_selector", execution)
            runner.verify_candidate_source_binding(
                acceptance,
                {
                    "source_contract_id": p248.CONTRACT_ID,
                    "candidate_source_receipts": normalized,
                },
                execution,
            )


if __name__ == "__main__":
    unittest.main()
