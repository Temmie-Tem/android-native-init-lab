import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import s22plus_fyg8_p252_contract_spec as p252_spec  # noqa: E402
import s22plus_fyg8_p252_e1_decoder as p252_decoder  # noqa: E402
import s22plus_fyg8_p253_e2_stock_closure as closure_selector  # noqa: E402
import s22plus_fyg8_p254_source_contract as p254  # noqa: E402
import s22plus_fyg8_p257_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p257_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p257_e2_stock_closure as closure  # noqa: E402
import s22plus_fyg8_p257_linked_audit as linked  # noqa: E402
import s22plus_fyg8_p257_source_contract as p257  # noqa: E402
import s22plus_fyg8_source_contracts as contracts  # noqa: E402


class S22PlusFyg8P257SourceContractTest(unittest.TestCase):
    RUN_ID = bytes.fromhex("57" * 16)

    @classmethod
    def setUpClass(cls):
        cls.implementation = p257.implementation_result(ROOT)
        cls.stock = closure.build_result(ROOT)
        cls.reachable = p257.validate_reachable_records(cls.RUN_ID)

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
            + S22PlusFyg8P257SourceContractTest.RUN_ID
        )

    def test_exact_60_module_and_81_step_geometry(self):
        self.assertEqual(len(spec.STEPS), 81)
        self.assertEqual((spec.MODULE_STAGE_FIRST, spec.MODULE_STAGE_LAST), (
            0x40,
            0x7B,
        ))
        self.assertEqual((spec.GATE_STAGE_FIRST, spec.GATE_STAGE_LAST), (
            0x7C,
            0x87,
        ))
        expected = {
            0x61: ("module", 33, 42),
            0x62: ("module", 34, 43),
            0x84: ("gate", 8, 77),
            0x85: ("gate", 9, 78),
            0x86: ("gate", 10, 79),
            0x87: ("gate", 11, 80),
            0x8F: ("terminal", 0, 81),
        }
        for stage, (kind, item, generation) in expected.items():
            with self.subTest(stage=stage):
                step = spec.step_for_stage(stage)
                self.assertEqual((step.kind, step.item_index), (kind, item))
                self.assertEqual(spec.ordinal_for_stage(stage) + 1, generation)

    def test_classifier_only_adds_three_exact_display_rows(self):
        historical = {
            row.value: (
                row.name,
                row.category,
                row.path,
                row.expected_symlink_basename,
            )
            for row in p252_spec.CLASSIFIER_DETAILS
        }
        current = {
            row.value: (
                row.name,
                row.category,
                row.path,
                row.expected_symlink_basename,
            )
            for row in spec.CLASSIFIER_DETAILS
        }
        self.assertEqual(
            set(current) - set(historical), {0xA0E, 0xA0F, 0xA11}
        )
        for value, identity in historical.items():
            self.assertEqual(current[value], identity)
        self.assertEqual(
            tuple(row.value for row in spec.BIND_CLASSIFIERS[:7]),
            (0xA01, 0xA02, 0xA03, 0xA0E, 0xA0F, 0xA11, 0xA04),
        )

    def test_generation_is_one_exact_plan_insertion(self):
        generated = p257.generate(ROOT)
        historical = p257.p254.generate(ROOT)
        old = p257._module_rows(historical["plan"])
        new = p257._module_rows(generated["plan"])
        index = spec.DISPCC_INSERTION.index
        self.assertEqual(len(old), spec.HISTORICAL_MODULE_PLAN_COUNT)
        self.assertEqual(len(new), spec.MODULE_PLAN_COUNT)
        self.assertEqual(new[:index], old[:index])
        self.assertEqual(new[index], spec.DISPCC_INSERTION.row)
        self.assertEqual(new[index + 1 :], old[index:])
        self.assertEqual(
            self.implementation["generated_semantics"]["module_count"], 60
        )
        self.assertTrue(
            self.implementation["reserved_details"][
                "unlisted_reserved_rejected"
            ]
        )

    def test_historical_generated_receipts_remain_pinned(self):
        actual = self.implementation["historical_generated_unchanged"]
        self.assertEqual(actual, p257.HISTORICAL_GENERATED_SHA256)

    def test_decoder_accepts_new_detail_only_at_shifted_ssusb(self):
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
            detail=0xA0E,
        )
        record = header + b"".join(slots)
        decoded = decoder.decode_record(
            record,
            expected_profile="E2",
            expected_run_id=self.RUN_ID,
        )
        self.assertEqual(decoded["active"]["stage"], 0x85)
        self.assertEqual(
            decoded["active_semantics"]["detail_name"],
            "display-clock-bind-absent",
        )
        with self.assertRaises(p252_decoder.DecodeError):
            p252_decoder.decode_record(
                record,
                expected_profile="E2",
                expected_run_id=self.RUN_ID,
            )

    def test_selector_build_and_proof_adapters_are_registered(self):
        selected = contracts.select(p257.CONTRACT_ID, "E2")
        self.assertIs(selected.module, p257)
        self.assertIs(selected.decoder, decoder)
        self.assertIs(closure_selector.select(p257.CONTRACT_ID), closure)
        self.assertEqual(
            repro.LINKED_VALIDATOR_ADAPTERS[p257.CONTRACT_ID],
            "s22plus_fyg8_p257_linked_audit",
        )
        self.assertEqual(linked.EXPECTED_SOURCE_CONTRACT_ID, p257.CONTRACT_ID)
        source, _receipts = p257.source_receipts(ROOT)
        self.assertEqual(set(source), p257.SOURCE_KEYS)

    def test_materialized_userspace_plan_requires_60_modules(self):
        with tempfile.TemporaryDirectory(prefix="s22-p257-plan-") as name:
            directory = Path(name)
            path = directory / p257.MATERIALIZED_FILENAMES["plan_header"]
            path.write_bytes(p257.generate(ROOT)["plan"])
            names = userspace._e2_module_files(
                ROOT, p257.CONTRACT_ID, directory
            )
        self.assertEqual(len(names), spec.MODULE_PLAN_COUNT)
        self.assertEqual(
            names[spec.DISPCC_INSERTION.index],
            spec.DISPCC_INSERTION.file,
        )

    def test_stale_59_module_materialized_plan_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="s22-p257-stale-plan-") as name:
            directory = Path(name)
            path = directory / p257.MATERIALIZED_FILENAMES["plan_header"]
            path.write_bytes(p254.generate(ROOT)["plan"])
            with self.assertRaises(userspace.BuildError):
                userspace._e2_module_files(
                    ROOT, p257.CONTRACT_ID, directory
                )

    def test_stale_80_step_linked_tables_are_rejected(self):
        with self.assertRaises(p257.SourceContractError):
            p257.audit_linked_tables(p254.linked_table_bytes())

    def test_historical_terminal_remains_historical_only(self):
        model = decoder.model
        header = self._header()
        generation = len(p252_spec.STEPS)
        previous = p252_spec.STEPS[generation - 2]
        terminal = p252_spec.STEPS[generation - 1]
        slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
        slots[(generation - 1) & 1] = p252_decoder.encode_slot(
            header,
            generation=generation - 1,
            stage=previous.stage,
            outcome=model.OUTCOME_PROGRESS,
            item_index=previous.item_index,
            detail=0,
        )
        slots[generation & 1] = p252_decoder.encode_slot(
            header,
            generation=generation,
            stage=terminal.stage,
            outcome=model.OUTCOME_SUCCESS,
            item_index=terminal.item_index,
            detail=0,
        )
        record = header + b"".join(slots)
        decoded = p252_decoder.decode_record(
            record,
            expected_profile="E2",
            expected_run_id=self.RUN_ID,
        )
        self.assertEqual(decoded["active"]["generation"], generation)
        with self.assertRaises(p252_decoder.DecodeError):
            decoder.decode_record(
                record,
                expected_profile="E2",
                expected_run_id=self.RUN_ID,
            )

    def test_stock_closure_pins_dispcc_and_full_digest(self):
        self.assertEqual(self.stock["module_count"], 60)
        self.assertEqual(self.stock["dispcc"], closure.EXPECTED_DISPCC)
        self.assertEqual(
            self.stock["module_closure_sha256"],
            closure.EXPECTED_MODULE_CLOSURE_SHA256,
        )
        self.assertEqual(
            self.stock["plan_header"],
            p257.receipt(p257.generate(ROOT)["plan"]),
        )

    def test_linked_table_bytes_match_descriptor(self):
        tables = p257.linked_table_bytes()
        self.assertEqual(len(tables["s22_fyg8_e2_sequence"]), 81)
        self.assertEqual(len(tables["s22_fyg8_e2_items"]), 81)
        self.assertEqual(len(tables["s22_fyg8_e2_kinds"]), 81)
        self.assertEqual(
            len(tables["s22_fyg8_e2_classifier_stages"]), 20
        )
        self.assertTrue(p257.audit_linked_tables(tables)["verified"])

    def test_reachable_contract_uses_p257_decoder(self):
        self.assertEqual(
            self.reachable["reachable_slot_variants"], p257.REACHABLE_VARIANTS
        )
        self.assertEqual(self.reachable["classifier_detail_count"], 20)
        self.assertEqual(
            self.reachable["decoder_policy_id"], decoder.POLICY_ID
        )


if __name__ == "__main__":
    unittest.main()
