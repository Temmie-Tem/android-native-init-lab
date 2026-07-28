from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p282_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p282_e1_decoder as decoder  # noqa: E402


class S22PlusFyg8P282E1DecoderTest(unittest.TestCase):
    RUN_ID = bytes.fromhex("82" * 16)

    def _header(self) -> bytes:
        model = decoder.model
        return (
            model.LONG_FAMILY
            + bytes(
                [
                    (model.FORMAT_VERSION << 4)
                    | model.PROFILE_NUMBERS[spec.PROFILE]
                ]
            )
            + self.RUN_ID
        )

    def _slot(self, stage: int, outcome: int, detail: int) -> bytes:
        generation = spec.ordinal_for_stage(stage) + 1
        return decoder.encode_slot(
            self._header(),
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=spec.expected_item(stage),
            detail=detail,
        )

    def _record(
        self,
        older_stage: int,
        older_outcome: int,
        older_detail: int,
        newer_stage: int,
        newer_outcome: int,
        newer_detail: int,
    ) -> bytes:
        slots = [bytes(decoder.model.SLOT_SIZE)] * 2
        for stage, outcome, detail in (
            (older_stage, older_outcome, older_detail),
            (newer_stage, newer_outcome, newer_detail),
        ):
            generation = spec.ordinal_for_stage(stage) + 1
            slots[generation & 1] = self._slot(stage, outcome, detail)
        return self._header() + b"".join(slots)

    def _decode_active(
        self, stage: int, outcome: int, detail: int
    ) -> dict:
        ordinal = spec.ordinal_for_stage(stage)
        previous = spec.STEPS[ordinal - 1]
        record = self._record(
            previous.stage,
            spec.OUTCOME_PROGRESS,
            0,
            stage,
            outcome,
            detail,
        )
        return decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=self.RUN_ID,
        )

    def test_decoder_covers_all_46_details(self) -> None:
        seen = set()
        for detail in spec.DIAGNOSTIC_DETAILS:
            result = self._decode_active(
                detail.stages[0],
                detail.outcomes[0],
                detail.value,
            )
            self.assertEqual(result["active"]["detail"], detail.value)
            self.assertEqual(
                result["active_semantics"]["detail_name"],
                detail.name,
            )
            self.assertEqual(
                result["active_semantics"]["detail_kind"],
                detail.category,
            )
            seen.add(detail.value)
        self.assertEqual(seen, set(spec.DETAIL_VALUES))

    def test_decoder_round_trips_all_567_tuples(self) -> None:
        seen = set()
        for detail in spec.tuple_values():
            decoded_tuple = spec.decode_tuple(detail)
            result = self._decode_active(
                spec.FINAL_STAGE,
                decoded_tuple.outcome,
                detail,
            )
            semantics = result["active_semantics"]
            self.assertEqual(semantics["detail"], detail)
            self.assertEqual(
                semantics["final_tuple"]["state"],
                decoded_tuple.state,
            )
            self.assertEqual(
                semantics["final_tuple"]["speed"],
                decoded_tuple.speed,
            )
            self.assertEqual(
                semantics["final_tuple"]["repair_index"],
                int(decoded_tuple.repair),
            )
            self.assertEqual(
                semantics["final_tuple"]["bind_index"],
                int(decoded_tuple.bind),
            )
            seen.add(detail)
        self.assertEqual(len(seen), 567)

    def test_changing_canonical_pair_is_exact_c4b(self) -> None:
        result = self._decode_active(
            spec.FINAL_STAGE,
            spec.OUTCOME_FAILURE,
            0xC4B,
        )
        self.assertEqual(
            result["active_semantics"]["detail_name"],
            "final-state-speed-unstable",
        )
        self.assertIsNone(result["active_semantics"]["final_tuple"])

    def test_terminal_preserves_adjacent_success_tuple(self) -> None:
        detail = spec.encode_tuple(
            spec.RepairClass.SOFTWARE_REINIT,
            spec.BindClass.DIRECT_RUN_STOP,
            "configured",
            "high-speed",
        )
        record = self._record(
            spec.FINAL_STAGE,
            spec.OUTCOME_PROGRESS,
            detail,
            spec.TERMINAL_STAGE,
            spec.OUTCOME_SUCCESS,
            0,
        )
        result = decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=self.RUN_ID,
        )
        self.assertTrue(result["terminal_success"])
        tuple_slots = [
            value
            for value in result["slot_semantics"]
            if value["final_tuple"] is not None
        ]
        self.assertEqual(len(tuple_slots), 1)
        self.assertEqual(tuple_slots[0]["final_tuple"]["state"], "configured")
        self.assertEqual(tuple_slots[0]["final_tuple"]["speed"], "high-speed")

    def test_warning_list_accepts_distinct_cycle_and_bind_warnings(self) -> None:
        record = self._record(
            spec.RESTART_STAGE,
            spec.OUTCOME_PROGRESS,
            0xC01,
            spec.BIND_STAGE,
            spec.OUTCOME_PROGRESS,
            0xC46,
        )
        result = decoder.decode_record(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=self.RUN_ID,
        )
        self.assertEqual(
            [value["detail"] for value in result["progress_warnings"]],
            [0xC01, 0xC46],
        )

    def test_initial_role_p280_detail_remains_decodable(self) -> None:
        result = self._decode_active(
            spec.ROLE_UDC_STAGE,
            spec.OUTCOME_FAILURE,
            0xB15,
        )
        self.assertEqual(result["active"]["detail"], 0xB15)
        self.assertEqual(
            result["active_semantics"]["detail_name"],
            spec.p280.detail_name(0xB15),
        )
        self.assertEqual(
            result["active_semantics"]["detail_kind"],
            spec.p280.detail_kind(0xB15),
        )


if __name__ == "__main__":
    unittest.main()
