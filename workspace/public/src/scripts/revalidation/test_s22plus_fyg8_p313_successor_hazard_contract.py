#!/usr/bin/env python3
"""Regression tests for the machine-enforced P3.13 successor hazards."""

from __future__ import annotations

from copy import deepcopy
import json
import unittest

import s22plus_fyg8_p313_successor_hazard_contract as contract


def compliant_fixture() -> dict[str, object]:
    successor_b = contract.MINIMUM_SUCCESSOR_B_OUTPUT_COUNT
    matrix_b = contract.MINIMUM_MATRIX_B_VALUE_COUNT
    return {
        "schema": contract.ARTIFACT_SCHEMA,
        "requirements_sha256": contract.requirements_sha256(),
        "hazards": {
            "source_derived_pair_geometry": {
                "stop_expected_counts": contract.STOP_EXPECTED_COUNTS,
                "final_expected_counts": contract.FINAL_EXPECTED_COUNTS,
                "clean_records": 41,
                "bounded_drift_records": 49,
                "record_capacity": 64,
                "generated_from_materialized_source": True,
                "verified": True,
            },
            "continuation_partition": {
                "expected_geometry_normalized_before_contradiction": True,
                "default_unclassified_contradiction_stops": True,
                "immediate_stop_conditions": list(
                    contract.IMMEDIATE_STOP_CONDITIONS
                ),
                "diagnostic_continue_predicates": list(
                    contract.DIAGNOSTIC_CONTINUE_PREDICATES
                ),
                "diagnostic_data_never_cycle_causal": True,
                "verified": True,
            },
            "carrier_value_position_matrix": {
                "inherited_a_outputs": contract.INHERITED_A_OUTPUT_COUNT,
                "inherited_b_outputs": contract.INHERITED_B_OUTPUT_COUNT,
                "progress_zero_outputs": contract.PROGRESS_ZERO_OUTPUT_COUNT,
                "positions": contract.POSITION_COUNT,
                "successor_b_outputs": successor_b,
                "matrix_b_values": matrix_b,
                "matrix_cells": (
                    contract.INHERITED_A_OUTPUT_COUNT
                    + matrix_b
                    + contract.PROGRESS_ZERO_OUTPUT_COUNT
                )
                * contract.POSITION_COUNT,
                "legacy_generic_multiplicity_decode_covered": True,
                "generated_from_actual_encoders": True,
                "accept_reject_derived_from_runtime_emit_sites": True,
                "real_process_v2_adapter_round_trip": True,
                "persistence_round_trip": True,
                "verified": True,
            },
            "pair_specific_multiplicity_detail": {
                "pair_names": list(contract.PAIR_NAMES),
                "detail_min": contract.PAIR_MASK_DETAIL_MIN,
                "detail_max": contract.PAIR_MASK_DETAIL_MAX,
                "output_count": contract.PAIR_MASK_VALUE_COUNT,
                "trace_record_cost": 0,
                "legacy_generic_0x6712_not_emitted": True,
                "historical_p311_range_disjoint": True,
                "all_masks_runtime_gate": True,
                "all_masks_checkpoint_gate": True,
                "all_masks_fixed_image_gate": True,
                "all_masks_model_decoder_adapter_round_trip": True,
                "verified": True,
            },
            "qualification_wiring": {
                "requirements_hash_in_source_closure": True,
                "validator_called_before_packaging": True,
                "missing_or_failed_artifact_blocks_packaging": True,
                "validated_artifact_receipted_by_qualification": True,
                "verified": True,
            },
        },
        "verified": True,
    }


class P313SuccessorHazardContractTests(unittest.TestCase):
    def test_pair_mask_names_every_violating_pair_without_trace_cost(self) -> None:
        seen = set()
        for mask in range(1, contract.PAIR_MASK_MAX + 1):
            detail = contract.encode_pair_mask(mask)
            self.assertGreaterEqual(detail, contract.PAIR_MASK_DETAIL_MIN)
            self.assertLessEqual(detail, contract.PAIR_MASK_DETAIL_MAX)
            self.assertTrue(contract.decode_pair_mask(detail))
            seen.add(detail)
        self.assertEqual(len(seen), 1_023)
        self.assertEqual(min(seen), 0x6C01)
        self.assertEqual(max(seen), 0x6FFF)
        self.assertTrue(seen.isdisjoint(range(0x6801, 0x680D)))
        requirement = contract.requirements()["hazards"][
            "pair_specific_multiplicity_detail"
        ]
        self.assertEqual(requirement["trace_record_cost"], 0)

    def test_registered_requirements_are_json_safe_and_not_satisfied(self) -> None:
        value = contract.requirements()
        self.assertEqual(value["status"], "registered-not-satisfied")
        self.assertEqual(len(contract.requirements_sha256()), 64)
        matrix = value["hazards"]["carrier_value_position_matrix"]
        self.assertEqual(matrix["minimum_successor_b_outputs"], 2_222)
        self.assertEqual(matrix["minimum_matrix_b_values"], 2_223)
        self.assertEqual(matrix["minimum_matrix_cells"], 251_450)
        json.dumps(value, sort_keys=True, allow_nan=False)

    def test_compliant_future_artifact_passes_structural_gate(self) -> None:
        result = contract.validate_successor_artifact(compliant_fixture())
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["successor_b_outputs"],
            contract.MINIMUM_SUCCESSOR_B_OUTPUT_COUNT,
        )

    def test_each_registered_hazard_is_mandatory(self) -> None:
        for hazard in (
            "source_derived_pair_geometry",
            "continuation_partition",
            "carrier_value_position_matrix",
            "pair_specific_multiplicity_detail",
            "qualification_wiring",
        ):
            with self.subTest(hazard=hazard):
                value = deepcopy(compliant_fixture())
                del value["hazards"][hazard]  # type: ignore[index]
                with self.assertRaises(contract.SuccessorHazardError):
                    contract.validate_successor_artifact(value)

    def test_load_bearing_proofs_fail_closed(self) -> None:
        mutations = (
            ("source_derived_pair_geometry", "clean_records", 37),
            (
                "continuation_partition",
                "default_unclassified_contradiction_stops",
                False,
            ),
            ("carrier_value_position_matrix", "real_process_v2_adapter_round_trip", False),
            ("pair_specific_multiplicity_detail", "trace_record_cost", 1),
            ("qualification_wiring", "validator_called_before_packaging", False),
        )
        for hazard, field, replacement in mutations:
            with self.subTest(hazard=hazard, field=field):
                value = deepcopy(compliant_fixture())
                value["hazards"][hazard][field] = replacement  # type: ignore[index]
                with self.assertRaises(contract.SuccessorHazardError):
                    contract.validate_successor_artifact(value)


if __name__ == "__main__":
    unittest.main()
