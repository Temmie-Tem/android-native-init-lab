#!/usr/bin/env python3
"""Focused tests for the P3.00 event-ingress/IRQ telemetry."""

from __future__ import annotations

from pathlib import Path
import unittest

import s22plus_fyg8_p298_telemetry_generator as p298_generator
import s22plus_fyg8_p300_telemetry_closure as closure
import s22plus_fyg8_p300_telemetry_decoder as decoder
import s22plus_fyg8_p300_telemetry_generator as generator
import s22plus_fyg8_p300_telemetry_model as model
import s22plus_fyg8_p300_telemetry_spec as spec


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


class P300TelemetryTests(unittest.TestCase):
    def test_exact_11_by_16_detail_space_and_decoder(self) -> None:
        validation = spec.validate()
        self.assertEqual(validation["bind_event_count"], 15)
        self.assertEqual(validation["ingress_class_count"], 11)
        self.assertEqual(validation["ingress_link_value_count"], 176)
        details = set()
        for ingress_class, name in enumerate(spec.INGRESS_CLASSES):
            for link_state in range(16):
                detail = spec.encode_ingress_link(ingress_class, link_state)
                details.add(detail)
                self.assertEqual(
                    spec.decode_ingress_link(detail),
                    (ingress_class, link_state),
                )
                telemetry = decoder.decode_detail(detail)["telemetry"]
                self.assertEqual(telemetry["ingress_class_name"], name)
                self.assertEqual(telemetry["link_state"], link_state)
                self.assertTrue(telemetry["probe_armed"])
                self.assertEqual(telemetry["gadget_start_rc"], 0)
                self.assertEqual(telemetry["ep_enable_hit_count"], 2)
        self.assertEqual(details, set(range(0xD00, 0xDB0)))
        self.assertTrue(details.isdisjoint(range(0xE00, 0xE84)))

    def test_reset_presence_is_mandatory_in_connect_done_families(self) -> None:
        without_reset = decoder.decode_detail(
            spec.encode_ingress_link(9, 0)
        )["telemetry"]
        with_reset = decoder.decode_detail(
            spec.encode_ingress_link(10, 0)
        )["telemetry"]
        self.assertTrue(without_reset["connect_done_seen"])
        self.assertFalse(without_reset["reset_seen"])
        self.assertTrue(with_reset["connect_done_seen"])
        self.assertTrue(with_reset["reset_seen"])

    def test_new_observer_failures_round_trip_at_declared_positions(self) -> None:
        routes = (
            (101, spec.BIND_SETUP_FAILURE_DETAILS),
            (103, spec.BIND_RESULT_FAILURE_DETAILS),
            (spec.EVENT_LINK_ORDINAL, spec.FINAL_TRACE_FAILURE_DETAILS),
        )
        for ordinal, details in routes:
            position = spec.POSITIONS[ordinal]
            record = prefix(ordinal)
            for detail in set(details) & set(spec.NEW_FAILURE_DETAIL_NAMES):
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
                decoded = decoder.decode_record(failed, expected_run_id=RUN_ID)
                self.assertEqual(decoded["active"]["detail"], detail)
                self.assertEqual(
                    decoded["active_semantics"]["telemetry"]["kind"],
                    "event-ingress-irq-observer-failure",
                )

    def test_generator_changes_only_four_declared_p298_artifacts(self) -> None:
        baseline = p298_generator.generate_bytes(
            ROOT,
            run_id=RUN_ID,
            unsat_tag=UNSAT_TAG,
            profile=spec.PROFILE,
        )
        actual = generated()
        changed = {key for key in actual if actual[key] != baseline[key]}
        self.assertEqual(changed, generator.P298_DELTA_KEYS)
        descriptor = actual["trace_descriptor_header"]
        runtime = actual["p290_e3_runtime_include"]
        patch = actual["candidate_patch"]
        self.assertIn(b"#define P282_BIND_EVENT_COUNT 15U", descriptor)
        self.assertIn(b"r32:p282/irq_out", descriptor)
        self.assertIn(b"type=+0(%x1):b4@8/32", descriptor)
        self.assertIn(b"traceoff:1 if type == 2\\n", runtime)
        self.assertIn(b"!traceoff:1 if type == 2\\n", runtime)
        self.assertIn(b"p300_close_recording_window", runtime)
        self.assertIn(b"recording_window_closed", runtime)
        self.assertIn(b"parsed_records != result->entries_in_buffer", runtime)
        self.assertIn(
            b"@@ -2488,6 +2488,34 @@ static void __dwc3_gadget_set_speed",
            patch,
        )
        self.assertIn(
            b"@@ -2527,6 +2555,29 @@ static int dwc3_gadget_run_stop",
            patch,
        )

    def test_runtime_closure_executes_faults_and_integrated_build(self) -> None:
        result = closure.run_closure(ROOT)
        self.assertEqual(result["verdict"], closure.VERDICT)
        self.assertTrue(result["runtime_ingress"]["verified"])
        self.assertTrue(result["stream_parser"]["verified"])
        self.assertTrue(
            result["executable_lifecycle"]["actual_generated_cleanup_executed"]
        )
        self.assertTrue(
            result["executable_lifecycle"][
                "zero_tracefs_residue_after_failures"
            ]
        )
        self.assertTrue(result["integrated_build"]["verified"])
        self.assertTrue(
            result["integrated_build"]["candidate_patch"]["driver_clean_apply"]
        )
        self.assertFalse(result["baseline"]["same_f1_binding_complete"])
        self.assertFalse(result["slot_16"]["used"])


if __name__ == "__main__":
    unittest.main()
