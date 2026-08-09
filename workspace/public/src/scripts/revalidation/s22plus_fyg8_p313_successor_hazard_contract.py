#!/usr/bin/env python3
"""Machine-enforced hazard requirements for the P3.13 successor."""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA = "s22plus_fyg8_p313_successor_hazard_requirements_v1"
ARTIFACT_SCHEMA = "s22plus_fyg8_p313_successor_hazard_closure_v1"
REGISTRATION_VERDICT = "PASS_P313_SUCCESSOR_HAZARDS_REGISTERED_HOST_ONLY"

PAIR_NAMES = (
    "start_off",
    "start_on",
    "child_suspend",
    "child_resume",
    "phy_suspend_off",
    "phy_suspend_on",
    "power_off",
    "power_on",
    "phy_init",
    "notify_connect",
)
STOP_EXPECTED_COUNTS = {
    "start_off": 1,
    "start_on": 0,
    "child_suspend": 1,
    "child_resume": 0,
    "phy_suspend_off": 2,
    "phy_suspend_on": 0,
    "power_off": 1,
    "power_on": 0,
    "phy_init": 0,
    "notify_connect": 0,
}
FINAL_EXPECTED_COUNTS = {
    "start_off": 1,
    "start_on": 1,
    "child_suspend": 1,
    "child_resume": 1,
    "phy_suspend_off": 2,
    "phy_suspend_on": 2,
    "power_off": 1,
    "power_on": 1,
    "phy_init": 1,
    "notify_connect": 1,
}

PAIR_MASK_DETAIL_BASE = 0x6C00
PAIR_MASK_MAX = (1 << len(PAIR_NAMES)) - 1
PAIR_MASK_DETAIL_MIN = PAIR_MASK_DETAIL_BASE + 1
PAIR_MASK_DETAIL_MAX = PAIR_MASK_DETAIL_BASE + PAIR_MASK_MAX
PAIR_MASK_VALUE_COUNT = PAIR_MASK_MAX

INHERITED_A_OUTPUT_COUNT = 126
INHERITED_B_OUTPUT_COUNT = 1_200
PROGRESS_ZERO_OUTPUT_COUNT = 1
POSITION_COUNT = 107
MINIMUM_SUCCESSOR_B_OUTPUT_COUNT = (
    INHERITED_B_OUTPUT_COUNT - 1 + PAIR_MASK_VALUE_COUNT
)
MINIMUM_MATRIX_B_VALUE_COUNT = MINIMUM_SUCCESSOR_B_OUTPUT_COUNT + 1
MINIMUM_MATRIX_CELL_COUNT = (
    INHERITED_A_OUTPUT_COUNT
    + MINIMUM_MATRIX_B_VALUE_COUNT
    + PROGRESS_ZERO_OUTPUT_COUNT
) * POSITION_COUNT

IMMEDIATE_STOP_CONDITIONS = (
    "malformed-or-incomplete-pair",
    "pid-counter-or-order-contradiction",
    "profile-deficit-or-nmissed",
    "ring-loss-capacity-or-cleanup-failure",
    "timeout-or-unreaped-helper",
    "target-udc-unbind-pullup-or-force-drift",
    "negative-controller-return",
    "unclassified-count-or-topology-drift",
)
DIAGNOSTIC_CONTINUE_PREDICATES = (
    "pair-mask-nonzero-and-within-declared-ceiling",
    "all-affected-pairs-complete-and-ordered",
    "stop-helper-returned-zero",
    "udc-binding-survived",
    "child-and-parent-suspended",
    "no-immediate-stop-condition",
    "exactly-one-restorative-restart",
    "cycle-causal-claim-revoked",
)


class SuccessorHazardError(ValueError):
    pass


def encode_pair_mask(mask: int) -> int:
    if not 1 <= mask <= PAIR_MASK_MAX:
        raise ValueError("P3.13 successor pair mask differs")
    return PAIR_MASK_DETAIL_BASE + mask


def decode_pair_mask(detail: int) -> tuple[str, ...]:
    mask = detail - PAIR_MASK_DETAIL_BASE
    if not 1 <= mask <= PAIR_MASK_MAX:
        raise ValueError("P3.13 successor pair detail differs")
    return tuple(
        name for index, name in enumerate(PAIR_NAMES) if mask & (1 << index)
    )


def requirements() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "registered-not-satisfied",
        "hazards": {
            "source_derived_pair_geometry": {
                "stop_expected_counts": STOP_EXPECTED_COUNTS,
                "final_expected_counts": FINAL_EXPECTED_COUNTS,
                "clean_records": 41,
                "bounded_drift_records": 49,
                "record_capacity": 64,
                "normalize_before_contradiction": True,
            },
            "continuation_partition": {
                "default_unclassified_contradiction_stops": True,
                "immediate_stop_conditions": list(IMMEDIATE_STOP_CONDITIONS),
                "diagnostic_continue_predicates": list(
                    DIAGNOSTIC_CONTINUE_PREDICATES
                ),
                "diagnostic_data_never_cycle_causal": True,
            },
            "carrier_value_position_matrix": {
                "inherited_a_outputs": INHERITED_A_OUTPUT_COUNT,
                "inherited_b_outputs": INHERITED_B_OUTPUT_COUNT,
                "progress_zero_outputs": PROGRESS_ZERO_OUTPUT_COUNT,
                "positions": POSITION_COUNT,
                "minimum_successor_b_outputs": MINIMUM_SUCCESSOR_B_OUTPUT_COUNT,
                "minimum_matrix_b_values": MINIMUM_MATRIX_B_VALUE_COUNT,
                "minimum_matrix_cells": MINIMUM_MATRIX_CELL_COUNT,
                "legacy_generic_multiplicity_decode_required": True,
                "derive_successor_outputs_from_actual_encoders": True,
                "derive_accept_reject_from_runtime_emit_sites": True,
                "real_process_v2_adapter_and_persistence_required": True,
            },
            "pair_specific_multiplicity_detail": {
                "pair_names": list(PAIR_NAMES),
                "detail_base": PAIR_MASK_DETAIL_BASE,
                "detail_min": PAIR_MASK_DETAIL_MIN,
                "detail_max": PAIR_MASK_DETAIL_MAX,
                "mask_max": PAIR_MASK_MAX,
                "output_count": PAIR_MASK_VALUE_COUNT,
                "minimum_successor_b_outputs": MINIMUM_SUCCESSOR_B_OUTPUT_COUNT,
                "trace_record_cost": 0,
                "legacy_generic_0x6712_not_emitted": True,
                "historical_p311_range_disjoint": True,
            },
            "qualification_wiring": {
                "requirements_hash_in_source_closure": True,
                "validator_called_before_packaging": True,
                "missing_or_failed_artifact_blocks_packaging": True,
                "validated_artifact_receipted_by_qualification": True,
            },
        },
    }


def requirements_sha256() -> str:
    encoded = json.dumps(
        requirements(), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise SuccessorHazardError(f"{label} differs")


def validate_successor_artifact(value: dict[str, Any]) -> dict[str, Any]:
    """Reject a future qualification artifact missing any registered proof."""

    _require_equal(value.get("schema"), ARTIFACT_SCHEMA, "artifact schema")
    _require_equal(
        value.get("requirements_sha256"),
        requirements_sha256(),
        "requirements receipt",
    )
    hazards = value.get("hazards")
    if not isinstance(hazards, dict):
        raise SuccessorHazardError("artifact hazards missing")

    geometry = hazards.get("source_derived_pair_geometry", {})
    _require_equal(
        geometry.get("stop_expected_counts"),
        STOP_EXPECTED_COUNTS,
        "stop pair geometry",
    )
    _require_equal(
        geometry.get("final_expected_counts"),
        FINAL_EXPECTED_COUNTS,
        "final pair geometry",
    )
    for key, expected in (
        ("clean_records", 41),
        ("bounded_drift_records", 49),
        ("record_capacity", 64),
        ("generated_from_materialized_source", True),
        ("verified", True),
    ):
        _require_equal(geometry.get(key), expected, f"pair geometry {key}")

    continuation = hazards.get("continuation_partition", {})
    for key, expected in (
        ("expected_geometry_normalized_before_contradiction", True),
        ("default_unclassified_contradiction_stops", True),
        ("immediate_stop_conditions", list(IMMEDIATE_STOP_CONDITIONS)),
        (
            "diagnostic_continue_predicates",
            list(DIAGNOSTIC_CONTINUE_PREDICATES),
        ),
        ("diagnostic_data_never_cycle_causal", True),
        ("verified", True),
    ):
        _require_equal(continuation.get(key), expected, f"continuation {key}")

    matrix = hazards.get("carrier_value_position_matrix", {})
    for key, expected in (
        ("inherited_a_outputs", INHERITED_A_OUTPUT_COUNT),
        ("inherited_b_outputs", INHERITED_B_OUTPUT_COUNT),
        ("progress_zero_outputs", PROGRESS_ZERO_OUTPUT_COUNT),
        ("positions", POSITION_COUNT),
        ("legacy_generic_multiplicity_decode_covered", True),
        ("generated_from_actual_encoders", True),
        ("accept_reject_derived_from_runtime_emit_sites", True),
        ("real_process_v2_adapter_round_trip", True),
        ("persistence_round_trip", True),
        ("verified", True),
    ):
        _require_equal(matrix.get(key), expected, f"carrier matrix {key}")
    successor_b = matrix.get("successor_b_outputs")
    if not isinstance(successor_b, int) or successor_b < MINIMUM_SUCCESSOR_B_OUTPUT_COUNT:
        raise SuccessorHazardError("carrier matrix successor B extent differs")
    matrix_b = matrix.get("matrix_b_values")
    if not isinstance(matrix_b, int) or matrix_b < MINIMUM_MATRIX_B_VALUE_COUNT:
        raise SuccessorHazardError("carrier matrix B union differs")
    expected_cells = (
        INHERITED_A_OUTPUT_COUNT
        + matrix_b
        + PROGRESS_ZERO_OUTPUT_COUNT
    ) * POSITION_COUNT
    _require_equal(
        matrix.get("matrix_cells"), expected_cells, "carrier matrix cell count"
    )

    detail = hazards.get("pair_specific_multiplicity_detail", {})
    for key, expected in (
        ("pair_names", list(PAIR_NAMES)),
        ("detail_min", PAIR_MASK_DETAIL_MIN),
        ("detail_max", PAIR_MASK_DETAIL_MAX),
        ("output_count", PAIR_MASK_VALUE_COUNT),
        ("trace_record_cost", 0),
        ("legacy_generic_0x6712_not_emitted", True),
        ("historical_p311_range_disjoint", True),
        ("all_masks_runtime_gate", True),
        ("all_masks_checkpoint_gate", True),
        ("all_masks_fixed_image_gate", True),
        ("all_masks_model_decoder_adapter_round_trip", True),
        ("verified", True),
    ):
        _require_equal(detail.get(key), expected, f"pair detail {key}")

    wiring = hazards.get("qualification_wiring", {})
    for key in (
        "requirements_hash_in_source_closure",
        "validator_called_before_packaging",
        "missing_or_failed_artifact_blocks_packaging",
        "validated_artifact_receipted_by_qualification",
        "verified",
    ):
        _require_equal(wiring.get(key), True, f"qualification wiring {key}")

    _require_equal(value.get("verified"), True, "artifact verdict")
    return {
        "schema": ARTIFACT_SCHEMA,
        "requirements_sha256": requirements_sha256(),
        "successor_b_outputs": successor_b,
        "matrix_b_values": matrix_b,
        "matrix_cells": expected_cells,
        "verified": True,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "verdict": REGISTRATION_VERDICT,
                "requirements_sha256": requirements_sha256(),
                "requirements": requirements(),
            },
            indent=2,
            sort_keys=True,
        )
    )
