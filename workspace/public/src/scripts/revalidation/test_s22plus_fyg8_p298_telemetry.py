#!/usr/bin/env python3
"""Focused tests for the P2.98 gadget-start/event telemetry contract."""

from __future__ import annotations

from pathlib import Path
import unittest

import s22plus_fyg8_p298_telemetry_closure as closure
import s22plus_fyg8_p298_telemetry_decoder as decoder
import s22plus_fyg8_p298_telemetry_generator as generator
import s22plus_fyg8_p298_telemetry_model as model
import s22plus_fyg8_p298_telemetry_spec as spec
import s22plus_fyg8_p298_identity_tiers as identity


ROOT = Path(__file__).resolve().parents[5]
RUN_ID = bytes.fromhex("1234567890abcdef1234567890abcdef")


def generated() -> dict[str, bytes]:
    return generator.generate_bytes(
        ROOT,
        run_id=identity.SOURCE_CHECK_RUN_ID,
        unsat_tag=identity.SOURCE_CHECK_UNSAT_TAG,
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


class P298TelemetryTests(unittest.TestCase):
    def test_budget_and_result_family(self) -> None:
        result = spec.validate()
        self.assertEqual(result["bind_event_count"], 12)
        self.assertEqual(result["event_link_value_count"], 64)
        self.assertEqual(result["final_state_value_count"], 132)
        for event_mask in range(4):
            for link in range(16):
                detail = spec.encode_event_link(event_mask, link)
                self.assertEqual(
                    spec.decode_event_link(detail), (event_mask, link)
                )
                decoded = decoder.decode_detail(detail)["telemetry"]
                self.assertTrue(decoded["probe_armed"])
                self.assertEqual(decoded["gadget_start_rc"], 0)
                self.assertEqual(decoded["ep_enable_hit_count"], 2)

    def test_superseded_p296_final_families_are_rejected(self) -> None:
        for generation, detail in ((106, 0xC60), (107, 0xC70), (107, 0xCC0)):
            position = spec.position_for_generation(generation)
            with self.assertRaises(spec.SpecError):
                spec.validate_slot(
                    generation=generation,
                    stage=position.stage,
                    outcome=(
                        model.OUTCOME_PROGRESS
                        if generation == 106
                        else model.OUTCOME_FAILURE
                    ),
                    item_index=position.item_index,
                    detail=detail,
                )

    def test_start_result_contract_attributes_out_and_in(self) -> None:
        expected = {
            (1, -22): spec.DETAIL_EP0_OUT_EINVAL,
            (1, -11): spec.DETAIL_EP0_OUT_EAGAIN,
            (1, -110): spec.DETAIL_EP0_OUT_ETIMEDOUT,
            (2, -22): spec.DETAIL_EP0_IN_EINVAL,
            (2, -11): spec.DETAIL_EP0_IN_EAGAIN,
            (2, -110): spec.DETAIL_EP0_IN_ETIMEDOUT,
        }
        for (hits, rc), detail in expected.items():
            self.assertEqual(
                spec.start_result_detail(
                    entered=True,
                    returned=True,
                    rc=rc,
                    ep_enable_hits=hits,
                ),
                detail,
            )
        self.assertEqual(
            spec.start_result_detail(
                entered=True, returned=True, rc=0, ep_enable_hits=2
            ),
            0,
        )
        self.assertEqual(
            spec.start_result_detail(
                entered=False, returned=False, rc=0, ep_enable_hits=0
            ),
            spec.DETAIL_GADGET_START_NOT_REACHED,
        )
        self.assertEqual(
            spec.start_result_detail(
                entered=True, returned=False, rc=0, ep_enable_hits=2
            ),
            spec.DETAIL_GADGET_START_NO_RETURN,
        )

    def test_all_observer_failure_routes_round_trip(self) -> None:
        for ordinal, details in (
            (101, spec.BIND_SETUP_FAILURE_DETAILS),
            (103, spec.BIND_RESULT_FAILURE_DETAILS),
            (spec.EVENT_LINK_ORDINAL, spec.FINAL_TRACE_FAILURE_DETAILS),
        ):
            record = prefix(ordinal)
            position = spec.POSITIONS[ordinal]
            for detail in details:
                failed = model.apply_request(
                    record,
                    model.encode_request(
                        spec.PROFILE,
                        position.stage,
                        run_id=RUN_ID,
                        outcome=model.OUTCOME_FAILURE,
                        item_index=position.item_index,
                        detail=detail,
                    ),
                )
                decoded = decoder.decode_record(
                    failed, expected_run_id=RUN_ID
                )
                self.assertEqual(decoded["active"]["detail"], detail)
                self.assertEqual(
                    decoded["active_semantics"]["telemetry"]["kind"],
                    "gadget-start-observer-failure",
                )

    def test_all_final_values_round_trip_after_new_a_family(self) -> None:
        record = prefix(spec.EVENT_LINK_ORDINAL)
        first_position = spec.POSITIONS[spec.EVENT_LINK_ORDINAL]
        terminal_position = spec.POSITIONS[spec.FINAL_STATE_ORDINAL]
        for event_mask in range(4):
            first_detail = spec.encode_event_link(event_mask, 0)
            first = model.apply_request(
                record,
                model.encode_request(
                    spec.PROFILE,
                    first_position.stage,
                    run_id=RUN_ID,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=first_position.item_index,
                    detail=first_detail,
                ),
            )
            for detail in range(
                spec.FINAL_STATE_DETAIL_BASE,
                spec.FINAL_STATE_DETAIL_BASE + spec.FINAL_STATE_VALUE_COUNT,
            ):
                terminal = model.apply_request(
                    first,
                    model.encode_request(
                        spec.PROFILE,
                        terminal_position.stage,
                        run_id=RUN_ID,
                        outcome=spec.expected_terminal_outcome(detail),
                        item_index=terminal_position.item_index,
                        detail=detail,
                    ),
                )
                decoded = decoder.decode_record(
                    terminal, expected_run_id=RUN_ID
                )
                self.assertEqual(decoded["active"]["detail"], detail)
                self.assertEqual(
                    decoded["valid_slots"][0]["detail"], first_detail
                )

    def test_generated_runtime_is_fail_closed_and_low_noise(self) -> None:
        artifacts = generated()
        result = closure.audit_result_contract(
            artifacts["p290_e3_runtime_include"]
        )
        self.assertTrue(result["verified"])
        descriptor = artifacts["trace_descriptor_header"]
        self.assertIn(b"P282_BIND_EVENT_COUNT 12U", descriptor)
        self.assertNotIn(b"dwc3_process_event_entry", descriptor)
        self.assertEqual(descriptor.count(b"dwc3_gadget_reset_interrupt"), 1)
        self.assertEqual(
            descriptor.count(b"dwc3_gadget_conndone_interrupt"), 1
        )

    def test_full_host_closure(self) -> None:
        result = closure.run_closure(ROOT)
        self.assertEqual(result["verdict"], closure.VERDICT)
        self.assertTrue(result["driver_source"]["byte_identical"])
        self.assertEqual(
            result["driver_source"]["claim"],
            "EP0_ENABLE_COMMAND_CHAIN_PROVED",
        )


if __name__ == "__main__":
    unittest.main()
