#!/usr/bin/env python3
"""Regression for the committed P3.13 intermediate-contradiction slot."""

from __future__ import annotations

import json
import unittest

import s22plus_fyg8_p313_postlive_carrier_model as model
import s22plus_fyg8_p313_postlive_decoder as decoder
import s22plus_fyg8_p313_telemetry_spec as spec


RUN_ID = bytes.fromhex("1234567890abcdef1234567890abcdef")
STOP_CLASSIFIED_ORDINAL = 96
CYCLE_EVENT_MULTIPLICITY = 0x6712


def intermediate_contradiction_record() -> bytes:
    record = model.initialize_record(spec.PROFILE, RUN_ID)
    for generation, position in enumerate(spec.POSITIONS, 1):
        failure = generation == STOP_CLASSIFIED_ORDINAL + 1
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                position.stage,
                run_id=RUN_ID,
                outcome=(
                    model.OUTCOME_FAILURE if failure else model.OUTCOME_PROGRESS
                ),
                item_index=position.item_index,
                detail=CYCLE_EVENT_MULTIPLICITY if failure else 0,
            ),
        )
        if failure:
            return record
    raise AssertionError("P3.13 contradiction generation was not reached")


def normal_final_pair_record() -> bytes:
    record = model.initialize_record(spec.PROFILE, RUN_ID)
    for generation, position in enumerate(spec.POSITIONS, 1):
        if generation == spec.ATTR_ORDINAL + 1:
            outcome = model.OUTCOME_PROGRESS
            detail = spec.encode_a(cycle_attempted=1, state_index=0, speed_index=0)
        elif generation == spec.SUMMARY_ORDINAL + 1:
            outcome = model.OUTCOME_FAILURE
            detail = spec.encode_normal(0)
        else:
            outcome = model.OUTCOME_PROGRESS
            detail = 0
        record = model.apply_request(
            record,
            model.encode_request(
                spec.PROFILE,
                position.stage,
                run_id=RUN_ID,
                outcome=outcome,
                item_index=position.item_index,
                detail=detail,
            ),
        )
        if generation == spec.SUMMARY_ORDINAL + 1:
            return record
    raise AssertionError("P3.13 final pair was not reached")


class P313PostLiveDecoderTests(unittest.TestCase):
    def test_intermediate_contradiction_remains_a_valid_committed_slot(self) -> None:
        record = intermediate_contradiction_record()
        decoded = decoder.decode_record(record, expected_run_id=RUN_ID)
        self.assertEqual(decoded["slot_status"], ["valid", "valid"])
        self.assertFalse(decoded["fallback_used"])
        self.assertEqual(decoded["active"]["generation"], 97)
        self.assertEqual(decoded["active"]["stage"], 0x90)
        self.assertEqual(decoded["active"]["item_index"], 4)
        self.assertEqual(decoded["active"]["detail"], CYCLE_EVENT_MULTIPLICITY)
        self.assertEqual(
            decoded["active_semantics"]["detail_name"],
            "cycle-event-multiplicity",
        )
        self.assertTrue(
            decoded["active_semantics"]["telemetry"]["intermediate_generation"]
        )

    def test_observation_is_information_bearing_but_not_accepted(self) -> None:
        classified = decoder.classify_observation(
            intermediate_contradiction_record(),
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertFalse(classified["accepted"])
        self.assertFalse(classified["integrity_issue"])
        self.assertEqual(classified["classification"], "P313_OBSERVER_CONTRADICTION")
        self.assertEqual(classified["failure_count"], 1)
        self.assertEqual(classified["contradiction_count"], 1)
        self.assertEqual(classified["foreign_count"], 0)
        json.dumps(classified, sort_keys=True, allow_nan=False)

    def test_inherited_progress_and_normal_final_pair_still_decode(self) -> None:
        classified = decoder.classify_observation(
            normal_final_pair_record(),
            expected_profile=spec.PROFILE,
            expected_run_id=RUN_ID,
        )
        self.assertTrue(classified["accepted"])
        self.assertFalse(classified["integrity_issue"])
        self.assertEqual(classified["classification"], "P313_TELEMETRY_ONE_OR_MORE_BOOTS")
        self.assertEqual(classified["telemetry_count"], 1)
        self.assertEqual(classified["contradiction_count"], 0)
        self.assertEqual(classified["records"][0]["p313_pair"]["kind"], "normal-cycle")

    def test_frozen_live_decoder_reproduces_the_incident(self) -> None:
        import s22plus_fyg8_p313_telemetry_decoder as frozen

        decoded = frozen.decode_record(
            intermediate_contradiction_record(), expected_run_id=RUN_ID
        )
        self.assertEqual(decoded["slot_status"], ["valid", "bad-body"])
        self.assertTrue(decoded["fallback_used"])
        self.assertEqual(decoded["active"]["generation"], 96)

    def test_contradiction_detail_with_progress_outcome_fails_closed(self) -> None:
        record = model.initialize_record(spec.PROFILE, RUN_ID)
        position = spec.POSITIONS[0]
        with self.assertRaises(model.DesignError):
            model.apply_request(
                record,
                model.encode_request(
                    spec.PROFILE,
                    position.stage,
                    run_id=RUN_ID,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=position.item_index,
                    detail=CYCLE_EVENT_MULTIPLICITY,
                ),
            )


if __name__ == "__main__":
    unittest.main()
