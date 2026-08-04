#!/usr/bin/env python3
"""Focused tests for the P3.01 userspace-only subtype refinement."""

from __future__ import annotations

from pathlib import Path
import unittest

import s22plus_fyg8_p300_telemetry_generator as p300_generator
import s22plus_fyg8_p301_telemetry_closure as closure
import s22plus_fyg8_p301_telemetry_decoder as decoder
import s22plus_fyg8_p301_telemetry_generator as generator
import s22plus_fyg8_p301_telemetry_model as model
import s22plus_fyg8_p301_telemetry_spec as spec


ROOT = Path(__file__).resolve().parents[5]
RUN_ID = bytes.fromhex("1234567890abcdef1234567890abcdef")
UNSAT_TAG = model.unsat_record(spec.PROFILE, RUN_ID)[len(model.UNSAT_FAMILY) :]


def generated() -> dict[str, bytes]:
    return generator.generate_bytes(
        ROOT,
        run_id=RUN_ID,
        unsat_tag=UNSAT_TAG,
        profile=spec.PROFILE,
    )


def prefix(ordinal: int) -> bytes:
    record = model.initialize_record(spec.PROFILE, RUN_ID)
    for index, position in enumerate(spec.POSITIONS[:ordinal]):
        detail = 0xC18 if index == 87 else 0xC40 if index == 103 else 0
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                position.stage,
                run_id=RUN_ID,
                outcome=model.OUTCOME_PROGRESS,
                item_index=position.item_index,
                detail=detail,
            ),
        )
    return record


class P301TelemetryTests(unittest.TestCase):
    def test_complete_4032_value_subtype_space_round_trips(self) -> None:
        details = set()
        for mask in range(1, 64):
            for info in range(16):
                for bucket in range(4):
                    detail = spec.encode_subtype(mask, info, bucket)
                    details.add(detail)
                    self.assertEqual(
                        spec.decode_subtype(detail),
                        (mask, info, bucket),
                    )
        self.assertEqual(details, set(range(0x4001, 0x4FC1)))
        self.assertNotIn(0x4000, details)
        self.assertNotIn(spec.UNKNOWN_SUBTYPE_DETAIL, details)

    def test_unknown_subtype_is_dedicated_and_mask_zero_cannot_encode(self) -> None:
        self.assertEqual(spec.UNKNOWN_SUBTYPE_DETAIL, 0x4FC1)
        with self.assertRaises(ValueError):
            spec.encode_subtype(0, 0, 0)
        telemetry = decoder.decode_detail(
            spec.UNKNOWN_SUBTYPE_DETAIL,
            outcome=spec.OUTCOME_FAILURE,
            generation=spec.FINAL_STATE_GENERATION,
        )["telemetry"]
        self.assertEqual(telemetry["kind"], "device-event-unknown-subtype")
        self.assertTrue(telemetry["unknown_subtype_seen"])
        self.assertTrue(telemetry["known_mask_not_claimed"])

    def test_a_is_hard_bound_to_ordinal_105_and_progress(self) -> None:
        detail = spec.encode_ingress_link(spec.DEVICE_OTHER_ONLY_CLASS, 0)
        position = spec.POSITIONS[spec.EVENT_LINK_ORDINAL]
        spec.validate_slot(
            generation=spec.EVENT_LINK_GENERATION,
            stage=position.stage,
            outcome=spec.OUTCOME_PROGRESS,
            item_index=position.item_index,
            detail=detail,
        )
        for ordinal in (104, 106):
            wrong = spec.POSITIONS[ordinal]
            with self.assertRaises(spec.SpecError):
                spec.validate_slot(
                    generation=ordinal + 1,
                    stage=wrong.stage,
                    outcome=spec.OUTCOME_PROGRESS,
                    item_index=wrong.item_index,
                    detail=detail,
                )
        with self.assertRaises(spec.SpecError):
            spec.validate_slot(
                generation=spec.EVENT_LINK_GENERATION,
                stage=position.stage,
                outcome=spec.OUTCOME_FAILURE,
                item_index=position.item_index,
                detail=detail,
            )
        exact = set(spec.exact_detail_rules())
        self.assertEqual(
            {
                row
                for row in exact
                if row[0] == 105
                and row[1] == spec.OUTCOME_PROGRESS
                and 0xD00 <= row[2] <= 0xDAF
            },
            {(105, spec.OUTCOME_PROGRESS, value) for value in range(0xD00, 0xDB0)},
        )

    def test_adjacent_a_b_record_and_contextual_decoder(self) -> None:
        record = prefix(spec.EVENT_LINK_ORDINAL)
        a_position = spec.POSITIONS[spec.EVENT_LINK_ORDINAL]
        a_detail = spec.encode_ingress_link(spec.DEVICE_OTHER_ONLY_CLASS, 0)
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                a_position.stage,
                run_id=RUN_ID,
                outcome=spec.OUTCOME_PROGRESS,
                item_index=a_position.item_index,
                detail=a_detail,
            ),
        )
        b_position = spec.POSITIONS[spec.FINAL_STATE_ORDINAL]
        b_detail = spec.encode_subtype(1, 3, 0)
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                b_position.stage,
                run_id=RUN_ID,
                outcome=spec.OUTCOME_FAILURE,
                item_index=b_position.item_index,
                detail=b_detail,
            ),
        )
        result = decoder.decode_record(record, expected_run_id=RUN_ID)
        self.assertEqual(result["active"]["generation"], 107)
        self.assertTrue(result["p301_pair"]["a_ordinal_105_progress"])
        self.assertTrue(result["p301_pair"]["b_ordinal_106_failure"])
        self.assertEqual(
            result["active_semantics"]["telemetry"]["event_type_names"],
            ["DISCONNECT"],
        )
        self.assertEqual(
            result["active_semantics"]["telemetry"]["first_event_info"], 3
        )
        classified = decoder.classify_observation(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertTrue(classified["accepted"])
        self.assertEqual(classified["classification"], "P301_TELEMETRY_ONE_OR_MORE_BOOTS")
        self.assertEqual(classified["telemetry_count"], 1)
        self.assertEqual(classified["contradiction_count"], 0)

    def test_terminal_contradiction_is_information_but_not_accepted(self) -> None:
        record = prefix(spec.EVENT_LINK_ORDINAL)
        a_position = spec.POSITIONS[spec.EVENT_LINK_ORDINAL]
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                a_position.stage,
                run_id=RUN_ID,
                outcome=spec.OUTCOME_PROGRESS,
                item_index=a_position.item_index,
                detail=spec.encode_ingress_link(spec.DEVICE_OTHER_ONLY_CLASS, 0),
            ),
        )
        b_position = spec.POSITIONS[spec.FINAL_STATE_ORDINAL]
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                b_position.stage,
                run_id=RUN_ID,
                outcome=spec.OUTCOME_FAILURE,
                item_index=b_position.item_index,
                detail=min(spec.CONTRADICTION_DETAIL_NAMES),
            ),
        )
        classified = decoder.classify_observation(
            record,
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertFalse(classified["accepted"])
        self.assertEqual(classified["classification"], "P301_TELEMETRY_CONTRADICTION")
        self.assertEqual(classified["telemetry_count"], 0)
        self.assertEqual(classified["contradiction_count"], 1)

    def test_old_p300_terminal_detail_is_rejected_at_b(self) -> None:
        record = prefix(spec.EVENT_LINK_ORDINAL)
        a_position = spec.POSITIONS[spec.EVENT_LINK_ORDINAL]
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                a_position.stage,
                run_id=RUN_ID,
                outcome=spec.OUTCOME_PROGRESS,
                item_index=a_position.item_index,
                detail=spec.encode_ingress_link(7, 0),
            ),
        )
        b_position = spec.POSITIONS[spec.FINAL_STATE_ORDINAL]
        with self.assertRaises(model.DesignError):
            model.apply_request(
                record,
                model.encode_request(
                    spec.PROFILE,
                    b_position.stage,
                    run_id=RUN_ID,
                    outcome=spec.OUTCOME_FAILURE,
                    item_index=b_position.item_index,
                    detail=spec.EXPECTED_FINAL_STATE_DETAIL,
                ),
            )

    def test_drift_space_round_trips_all_132_states(self) -> None:
        for index in range(spec.FINAL_DRIFT_VALUE_COUNT):
            detail = spec.encode_final_drift(index)
            self.assertEqual(
                spec.decode_final_drift(detail),
                spec.base.decode_final_state(spec.base.FINAL_STATE_DETAIL_BASE + index),
            )
        self.assertEqual(spec.encode_final_drift(0), 0x5001)
        self.assertEqual(spec.encode_final_drift(131), 0x5084)

    def test_generator_changes_runtime_only_and_closure_executes(self) -> None:
        baseline = p300_generator.generate_bytes(
            ROOT,
            run_id=RUN_ID,
            unsat_tag=UNSAT_TAG,
            profile=spec.PROFILE,
        )
        actual = generated()
        changed = {key for key in actual if actual[key] != baseline[key]}
        self.assertEqual(changed, generator.P300_DELTA_KEYS)
        runtime = actual["p290_e3_runtime_include"]
        self.assertLess(
            runtime.index(b"if (result->other_type_mask == 0U)"),
            runtime.index(b"((unsigned int)result->other_type_mask - 1U)"),
        )
        self.assertIn(b"S22_P294_POSITION_USBLNKST == 105U", runtime)
        result = closure.run_closure(ROOT)
        self.assertEqual(result["verdict"], closure.VERDICT)
        self.assertTrue(result["subtype_ordinal"]["unknown_type_8_executed"])
        self.assertTrue(result["subtype_ordinal"]["unknown_type_12_executed"])
        self.assertTrue(result["integrated_build"]["userspace"]["two_link_reproducible"])


if __name__ == "__main__":
    unittest.main()
