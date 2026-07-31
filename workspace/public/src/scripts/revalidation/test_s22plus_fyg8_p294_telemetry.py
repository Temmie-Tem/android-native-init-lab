#!/usr/bin/env python3
"""Focused tests for the P2.94 two-slot DWC3 telemetry contract."""

from __future__ import annotations

from pathlib import Path
import unittest

import s22plus_fyg8_p292_accept_to_resume as closure
import s22plus_fyg8_p292_identity_tiers as identity
import s22plus_fyg8_p292_repair_generator as baseline
import s22plus_fyg8_p292_repair_spec as repair
import s22plus_fyg8_p294_telemetry_decoder as decoder
import s22plus_fyg8_p294_telemetry_generator as generator
import s22plus_fyg8_p294_telemetry_model as model
import s22plus_fyg8_p294_telemetry_spec as spec


ROOT = Path(__file__).resolve().parents[5]


def generated() -> dict[str, bytes]:
    return generator.generate_bytes(
        ROOT,
        run_id=identity.SOURCE_CHECK_RUN_ID,
        unsat_tag=identity.SOURCE_CHECK_UNSAT_TAG,
        profile=repair.PROFILE,
    )


class P294TelemetryTests(unittest.TestCase):
    def test_budget_and_partition(self) -> None:
        result = spec.validate()
        self.assertEqual(result["link_state_value_count"], 16)
        self.assertEqual(result["final_state_value_count"], 132)
        self.assertEqual(result["fixed_mismatch_value_count"], 15)
        self.assertEqual(result["contradiction_value_count"], 2)
        self.assertEqual(result["position_count"], 107)

    def test_generator_changes_only_declared_artifacts(self) -> None:
        source = baseline.generate_bytes(
            ROOT,
            run_id=identity.SOURCE_CHECK_RUN_ID,
            unsat_tag=identity.SOURCE_CHECK_UNSAT_TAG,
            profile=repair.PROFILE,
        )
        result = generated()
        changed = {
            key for key in result if result[key] != source[key]
        }
        self.assertEqual(changed, generator.TELEMETRY_ARTIFACT_KEYS)

    def test_pair_is_adjacent_in_materialized_runtime(self) -> None:
        result = closure.audit_pair_publication_adjacency(
            generated()["p290_e3_runtime_include"],
            helper_name="p294_publish_final_pair",
            first_publish_expression=(
                b"s22_p294_checkpoint_progress_position(\n"
                b"        &g_checkpoint, "
                b"S22_P294_POSITION_USBLNKST, first_detail)"
            ),
            terminal_publish_expression=(
                b"s22_p294_checkpoint_terminal_position(\n"
                b"        &g_checkpoint, "
                b"S22_P294_POSITION_FINAL_STATE, terminal_detail)"
            ),
        )
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["calls_between_first_return_and_terminal_invocation"], 0
        )

    def test_all_terminal_values_round_trip_through_model(self) -> None:
        run_id = bytes.fromhex("1234567890abcdef1234567890abcdef")
        record = model.initialize_record(spec.PROFILE, run_id)
        for generation, position in enumerate(spec.POSITIONS[:105], 1):
            detail = (
                0xC18
                if generation == 88
                else 0xC40
                if generation == 104
                else 0
            )
            record = model.apply_request(
                record,
                model.encode_request(
                    spec.PROFILE,
                    position.stage,
                    run_id=run_id,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=position.item_index,
                    detail=detail,
                ),
            )
        link_position = spec.POSITIONS[spec.LINK_STATE_ORDINAL]
        terminal_position = spec.POSITIONS[spec.FINAL_STATE_ORDINAL]
        terminal_details = [
            *(spec.FINAL_STATE_DETAIL_BASE + index for index in range(132)),
            *(
                spec.encode_fixed_mismatch(mask)
                for mask in range(1, 16)
            ),
            spec.STATE_SPEED_CONTRADICTION_DETAIL,
            spec.CONNECT_SPEED_CONTRADICTION_DETAIL,
        ]
        for link_state in range(16):
            first = model.apply_request(
                record,
                model.encode_request(
                    spec.PROFILE,
                    link_position.stage,
                    run_id=run_id,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=link_position.item_index,
                    detail=spec.encode_link_state(link_state),
                ),
            )
            for detail in terminal_details:
                terminal = model.apply_request(
                    first,
                    model.encode_request(
                        spec.PROFILE,
                        terminal_position.stage,
                        run_id=run_id,
                        outcome=spec.expected_terminal_outcome(detail),
                        item_index=terminal_position.item_index,
                        detail=detail,
                    ),
                )
                decoded = decoder.decode_record(
                    terminal, expected_run_id=run_id
                )
                self.assertEqual(decoded["active"]["detail"], detail)
                self.assertEqual(
                    decoded["valid_slots"][0]["detail"],
                    spec.encode_link_state(link_state),
                )

    def test_all_raw_snapshot_values_classify_into_declared_terminal_set(self) -> None:
        declared = {
            detail
            for ordinal, _outcome, detail in spec.exact_detail_rules()
            if ordinal == spec.FINAL_STATE_ORDINAL
        }
        observed = set()
        for run_stop in range(2):
            for devctrlhlt in range(2):
                for coreidle in range(2):
                    for prtcap in range(4):
                        for susphy in range(2):
                            for connect_speed in range(8):
                                for vbus_valid in range(2):
                                    for state in range(len(spec.UDC_STATES)):
                                        for speed in range(len(spec.USB_SPEEDS)):
                                            classification = spec.classify(
                                                spec.Snapshot(
                                                    0,
                                                    run_stop,
                                                    devctrlhlt,
                                                    coreidle,
                                                    prtcap,
                                                    susphy,
                                                    connect_speed,
                                                    vbus_valid,
                                                    state,
                                                    speed,
                                                )
                                            )
                                            observed.add(classification.detail)
                                            self.assertIn(
                                                (
                                                    spec.FINAL_STATE_ORDINAL,
                                                    classification.outcome,
                                                    classification.detail,
                                                ),
                                                spec._exact_rule_set(),  # noqa: SLF001
                                            )
        self.assertEqual(observed, declared)


if __name__ == "__main__":
    unittest.main()
