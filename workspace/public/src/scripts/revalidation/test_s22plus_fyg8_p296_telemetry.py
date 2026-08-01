#!/usr/bin/env python3
"""Focused tests for the P2.96 built-in-only DWC3 telemetry contract."""

from __future__ import annotations

from pathlib import Path
import unittest

import s22plus_fyg8_p292_identity_tiers as identity
import s22plus_fyg8_p292_repair_spec as repair
import s22plus_fyg8_p296_telemetry_closure as closure
import s22plus_fyg8_p296_telemetry_decoder as decoder
import s22plus_fyg8_p296_telemetry_generator as generator
import s22plus_fyg8_p296_telemetry_model as model
import s22plus_fyg8_p296_telemetry_spec as spec


ROOT = Path(__file__).resolve().parents[5]


def generated() -> dict[str, bytes]:
    return generator.generate_bytes(
        ROOT,
        run_id=identity.SOURCE_CHECK_RUN_ID,
        unsat_tag=identity.SOURCE_CHECK_UNSAT_TAG,
        profile=repair.PROFILE,
    )


class P296TelemetryTests(unittest.TestCase):
    def test_budget_and_delivery_scope(self) -> None:
        result = spec.validate()
        self.assertEqual(result["link_state_value_count"], 16)
        self.assertEqual(result["final_state_value_count"], 132)
        self.assertEqual(result["fixed_mismatch_value_count"], 7)
        self.assertEqual(result["external_module_symbol_count"], 0)

    def test_external_wrapper_is_absent(self) -> None:
        artifacts = generated()
        self.assertTrue(closure.audit_delivery(artifacts)["verified"])
        for value in artifacts.values():
            self.assertNotIn(b"wrapper_vbus_snapshot", value)
            self.assertNotIn(b"dwc3-msm-core.c", value)

    def test_pair_is_adjacent(self) -> None:
        result = closure.audit_pair_adjacency(
            generated()["p290_e3_runtime_include"]
        )
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["calls_between_first_return_and_terminal_invocation"], 0
        )

    def test_runtime_classifier_matches_python_sot(self) -> None:
        result = closure.audit_runtime_classifier(
            generated()["p290_e3_runtime_include"]
        )
        self.assertTrue(result["runtime_matches_python_sot"])

    def test_all_terminal_values_round_trip(self) -> None:
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
            *(spec.encode_fixed_mismatch(mask) for mask in range(1, 8)),
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
                    terminal,
                    expected_run_id=run_id,
                )
                self.assertEqual(decoded["active"]["detail"], detail)
                self.assertEqual(
                    decoded["valid_slots"][0]["detail"],
                    spec.encode_link_state(link_state),
                )


if __name__ == "__main__":
    unittest.main()
