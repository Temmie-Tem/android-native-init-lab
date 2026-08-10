#!/usr/bin/env python3
"""Exercise P3.15 Carrier-v2 through the real Process-v2 evidence adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_p315_carrier_model as model
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_overlay_contract as overlay
import s22plus_fyg8_p315_telemetry_decoder as decoder
import s22plus_fyg8_p315_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p315_process_v2_adapter_fixture_v1"
VERDICT = "PASS_P315_PROCESS_V2_ADAPTER_PERSISTENCE_HOST_ONLY"
STOP_TERMINAL_GENERATION = 97
RESTART_TERMINAL_GENERATION = 100


class FixtureError(ValueError):
    pass


def _record_at_generation(
    run_id: bytes,
    *,
    terminal: int,
    terminal_generation: int,
) -> bytes:
    record = model.initialize_record(overlay.PROFILE, run_id)
    for generation, position in enumerate(spec.POSITIONS, 1):
        if generation == terminal_generation:
            outcome = spec.OUTCOME_FAILURE
            detail = terminal
        elif generation == spec.ATTR_ORDINAL + 1:
            outcome = spec.OUTCOME_PROGRESS
            detail = spec.encode_a(
                cycle_attempted=1, state_index=0, speed_index=0
            )
        else:
            outcome = model.OUTCOME_PROGRESS
            detail = 0
        record = model.apply_request(
            record,
            model.encode_request(
                overlay.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=outcome,
                item_index=position.item_index,
                detail=detail,
            ),
        )
        if generation == terminal_generation:
            break
    return record


def _final_record(run_id: bytes, terminal: int) -> bytes:
    return _record_at_generation(
        run_id,
        terminal=terminal,
        terminal_generation=spec.SUMMARY_ORDINAL + 1,
    )


def _acceptance(contract: dict[str, Any]) -> dict[str, Any]:
    artifact = {"path": "fixture", "size": 1, "sha256": "0" * 64}
    return {
        "kind": evidence.E1_LATEST_STAGE_KIND,
        "source": evidence.CHECKPOINT_SOURCE,
        "decoder": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "profile": overlay.PROFILE,
        "run_id": contract["run_id"],
        "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "long_family_hex": model.LONG_FAMILY.hex(),
        "unsat_family_hex": model.UNSAT_FAMILY.hex(),
        "terminal_stage": evidence._latest_stage_terminal(  # noqa: SLF001
            decoder, overlay.PROFILE
        ),
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "contract": {
            "candidate_static": artifact,
            "run_manifest": artifact,
            "static_check": artifact,
        },
    }


def _persist(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def audit(
    root: Path | None = None,
    *,
    matrix_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import s22plus_fyg8_p315_matrix_fixture as matrix_fixture

    root = (root or Path(__file__).resolve().parents[5]).resolve()
    contract = overlay.verify_parent(root)
    run_id = bytes.fromhex(contract["run_id"])
    acceptance = _acceptance(contract)
    selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
        overlay.PARENT_SOURCE_CONTRACT_ID,
        overlay.PROFILE,
        overlay.CONTRACT_ID,
    )
    normal = _persist(
        evidence.classify_e1_latest_stage(
            _final_record(run_id, spec.encode_normal(0)), acceptance
        )
    )
    pair = normal.get("records", [{}])[0].get("p315_pair", {})
    if (
        selected is not decoder
        or normal.get("accepted") is not True
        or normal.get("telemetry_count") != 1
        or normal.get("foreign_count") != 0
        or pair.get("kind") != "normal-cycle"
        or pair.get("cycle_attempted") is not True
        or pair.get("observer_complete") is not True
    ):
        raise FixtureError("P3.15 Process-v2 normal round trip differs")

    cases = {
        "stop-0x6704": (0x6704, STOP_TERMINAL_GENERATION),
        "restart-0x6704": (0x6704, RESTART_TERMINAL_GENERATION),
        "profile-deficit-0x6705": (0x6705, STOP_TERMINAL_GENERATION),
        "unknown-phase-0x6707": (0x6707, RESTART_TERMINAL_GENERATION),
        "resume-precondition-0x671d": (0x671D, RESTART_TERMINAL_GENERATION),
        "profile-only-0x6721": (0x6721, RESTART_TERMINAL_GENERATION),
        "gadget-zero-0x6722": (0x6722, RESTART_TERMINAL_GENERATION),
        "run-provenance-0x6723": (0x6723, RESTART_TERMINAL_GENERATION),
    }
    observed: dict[str, dict[str, Any]] = {}
    for name, (detail, generation) in cases.items():
        classified = _persist(
            evidence.classify_e1_latest_stage(
                _record_at_generation(
                    run_id, terminal=detail, terminal_generation=generation
                ),
                acceptance,
            )
        )
        active = classified.get("records", [{}])[0].get("active_semantics", {})
        if (
            classified.get("accepted") is not False
            or classified.get("contradiction_count") != 1
            or classified.get("foreign_count") != 0
            or active.get("generation") != generation
            or active.get("detail") != detail
        ):
            raise FixtureError(f"P3.15 Process-v2 {name} round trip differs")
        if detail in spec.P315_RESERVED_NAMES and (
            active.get("detail_kind") != "p315-observer-contradiction"
            or active.get("detail_name") != spec.P315_RESERVED_NAMES[detail]
        ):
            raise FixtureError(f"P3.15 reserved semantics differ: {name}")
        observed[name] = {
            "detail": detail,
            "generation": generation,
            "detail_name": active.get("detail_name"),
        }

    mask = _persist(
        evidence.classify_e1_latest_stage(
            _final_record(run_id, spec.encode_pair_mask(1)), acceptance
        )
    )
    mask_pair = mask.get("records", [{}])[0].get("p315_pair", {})
    if (
        mask.get("accepted") is not False
        or mask.get("contradiction_count") != 1
        or mask.get("pair_excess_count") != 1
        or mask.get("foreign_count") != 0
        or mask_pair.get("kind") != "source-normalized-pair-excess"
        or mask_pair.get("cycle_causal_claim") is not False
    ):
        raise FixtureError("P3.15 Process-v2 pair-mask round trip differs")

    unknown = _acceptance(contract)
    unknown["userspace_overlay_contract_id"] = overlay.CONTRACT_ID + "-unknown"
    mixed = _acceptance(contract)
    mixed["decoder"] = "s22plus_fyg8_p314_carrier_v2_source_normalized_cycle_v1"
    rejections = 0
    for changed in (unknown, mixed):
        try:
            evidence.classify_e1_latest_stage(
                _final_record(run_id, spec.encode_normal(0)), changed
            )
        except evidence.EvidenceError:
            rejections += 1
    if rejections != 2:
        raise FixtureError("P3.15 unknown or mixed Carrier authority was accepted")

    matrix = matrix_result or matrix_fixture.audit(root)
    if (
        matrix.get("matrix_cells") != 251_450
        or matrix.get("real_process_v2_adapter_round_trip") is not True
        or matrix.get("persistence_round_trip") is not True
        or matrix.get("verified") is not True
    ):
        raise FixtureError("P3.15 Process-v2 matrix proof differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "decoder_id": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "carrier_v2_family": model.LONG_FAMILY.decode("ascii"),
        "json_safe": True,
        "foreign_count_zero": True,
        "actual_generation_cases": observed,
        "pair_mask_fail_closed": True,
        "unknown_overlay_rejected": True,
        "mixed_overlay_rejected": True,
        "matrix_cells": matrix["matrix_cells"],
        "matrix_sha256": matrix["matrix_sha256"],
        "real_process_v2_adapter_round_trip": True,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (FixtureError, evidence.EvidenceError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
