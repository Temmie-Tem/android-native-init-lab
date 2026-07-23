#!/usr/bin/env python3
"""Decode P2.48 E2 records with descriptor-derived failure semantics."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p232_e1_latest_stage_design as model
import s22plus_fyg8_p245_e1_decoder as p245
import s22plus_fyg8_p248_contract_spec as spec


SCHEMA = "s22plus_fyg8_p248_e2_decoder_v1"
DECODER_ID = "s22plus_fyg8_p248_e2_latest_stage_v1"
PROFILE = spec.PROFILE
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
TERMINAL_STAGE = spec.TERMINAL_STAGE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P248_E2_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "unsat=S22E1U1-24|"
    "baseline=all-related-families-absent|"
    "accept=one-or-more-p248-e2-terminal-success|"
    "reject=foreign,malformed,partial,reserved-detail|zero=ambiguous|"
    "detail=001-7ff-errno,800-8ff-regression,900-9ff-read-error|"
    f"stages={','.join(f'{stage:02x}' for stage in STAGE_SEQUENCE)}|"
    f"spec={spec.SCHEMA}|model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]


class DecodeError(ValueError):
    pass


def _require_identity(profile: str, run_id: bytes) -> None:
    if profile != PROFILE:
        raise DecodeError(f"unsupported P2.48 profile: {profile}")
    if len(run_id) != model.RUN_ID_SIZE or not any(run_id):
        raise DecodeError("P2.48 run ID must be one nonzero 128-bit value")


def _validate_slot_dict(slot: dict[str, Any]) -> None:
    generation = slot.get("generation")
    if generation == 0:
        if slot != {
            "slot_id": slot.get("slot_id"),
            "generation": 0,
            "stage": model.STAGES["ENTRY"],
            "outcome": model.OUTCOME_PROGRESS,
            "item_index": 0,
            "detail": 0,
        }:
            raise DecodeError("generation zero is not the kernel ENTRY state")
        return
    try:
        spec.validate_slot(
            generation=generation,
            stage=slot["stage"],
            outcome=slot["outcome"],
            item_index=slot["item_index"],
            detail=slot["detail"],
        )
    except (KeyError, TypeError, spec.SpecError) as exc:
        raise DecodeError(str(exc)) from exc


def encode_slot(
    header: bytes,
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> bytes:
    if generation != 0:
        try:
            spec.validate_slot(
                generation=generation,
                stage=stage,
                outcome=outcome,
                item_index=item_index,
                detail=detail,
            )
        except spec.SpecError as exc:
            raise DecodeError(str(exc)) from exc
    try:
        return p245.encode_slot(
            header,
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item_index,
            detail=detail,
        )
    except p245.DecodeError as exc:
        raise DecodeError(str(exc)) from exc


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    try:
        result = p245.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except p245.DecodeError as exc:
        raise DecodeError(str(exc)) from exc
    for slot in result["valid_slots"]:
        _validate_slot_dict(slot)
    return result


def _classify(
    baseline: bytes,
    observed: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    _require_identity(expected_profile, expected_run_id)
    all_families = (
        model.LONG_FAMILY,
        model.UNSAT_FAMILY,
        *model.LEGACY_FAMILIES,
    )
    if any(family in baseline for family in all_families) or model._edge_family_partial(
        baseline, all_families
    ):
        raise DecodeError("baseline is not clean for all related evidence families")

    integrity_issues: list[str] = []
    records: list[dict[str, Any]] = []
    for position in model._family_positions(observed, model.LONG_FAMILY):
        end = position + model.LONG_RECORD_SIZE
        if end > len(observed):
            integrity_issues.append("truncated-long-record")
            continue
        try:
            decoded = decode_record(
                observed[position:end],
                expected_profile=expected_profile,
                expected_run_id=expected_run_id,
            )
            decoded["observer_offset"] = position
            records.append(decoded)
        except DecodeError as exc:
            integrity_issues.append(str(exc))

    expected_unsat = model.unsat_record(expected_profile, expected_run_id)
    unsat_count = observed.count(expected_unsat)
    if observed.count(model.UNSAT_FAMILY) != unsat_count:
        integrity_issues.append("foreign-or-malformed-unsat-record")
    for family in model.LEGACY_FAMILIES:
        if family in observed:
            integrity_issues.append("legacy-or-foreign-evidence-family")
    if model._edge_family_partial(observed, all_families):
        integrity_issues.append("partial-family-at-snapshot-edge")

    success_count = sum(record["terminal_success"] for record in records)
    failure_count = sum(
        record["active"]["outcome"] == model.OUTCOME_FAILURE
        for record in records
    )
    progress_count = sum(
        record["active"]["generation"] > 0
        and record["active"]["outcome"] == model.OUTCOME_PROGRESS
        for record in records
    )
    entry_count = sum(record["active"]["generation"] == 0 for record in records)
    if integrity_issues:
        classification = "AMBIGUOUS_INTEGRITY_FAILURE"
        accepted = False
    elif success_count:
        classification = "E2_SUCCESS_ONE_OR_MORE_BOOTS"
        accepted = True
    elif failure_count:
        classification = "E2_FAILURE_OBSERVED"
        accepted = False
    elif progress_count:
        classification = "E2_PROGRESS_OBSERVED"
        accepted = False
    elif entry_count:
        classification = "ENTRY_ONLY_ONE_OR_MORE_BOOTS"
        accepted = False
    elif unsat_count:
        classification = "UNSAT_VALID_MAGIC_ONE_OR_MORE_BOOTS"
        accepted = False
    else:
        classification = "ZERO_AMBIGUOUS"
        accepted = False
    return {
        "classification": classification,
        "accepted": accepted,
        "integrity_issue": bool(integrity_issues),
        "integrity_issues": integrity_issues,
        "long_record_count": len(records),
        "unsat_count": unsat_count,
        "entry_count": entry_count,
        "progress_count": progress_count,
        "failure_count": failure_count,
        "success_count": success_count,
        "fallback_record_count": sum(record["fallback_used"] for record in records),
        "minimum_candidate_boots": (
            len(records) + unsat_count if not integrity_issues else 0
        ),
        "records": records,
        "residual_zero_meanings": (
            [
                "candidate or post-exec hook not reached",
                "path, PID, target, layout, or magic guard rejected",
                "valid magic with idx below 24",
                "entry initialization, flush, readback, or header check failed",
                "later overwrite, loss, or observer failure",
            ]
            if classification == "ZERO_AMBIGUOUS"
            else []
        ),
    }


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    try:
        _classify(
            payload,
            b"",
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except DecodeError as exc:
        return {
            "classification": "BASELINE_RELATED_EVIDENCE_PRESENT",
            "baseline_clean": False,
            "integrity_issue": True,
            "error": str(exc),
        }
    return {
        "classification": "BASELINE_CLEAN",
        "baseline_clean": True,
        "integrity_issue": False,
        "error": None,
    }


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    return _classify(
        b"",
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
