#!/usr/bin/env python3
"""Decode P2.45 E2 retained records without mutating the legacy stage model."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import asdict
from typing import Any

import s22plus_fyg8_p232_e1_latest_stage_design as model
import s22plus_fyg8_p244_e2_provider_sources as provider_sources


SCHEMA = "s22plus_fyg8_p245_e2_decoder_v1"
DECODER_ID = "s22plus_fyg8_p245_e2_latest_stage_v1"
PROFILE = "E2"
STAGE_SEQUENCE = (
    model.E1_LOCAL_SEQUENCE
    + tuple(
        range(
            provider_sources.MODULE_STAGE_FIRST,
            provider_sources.MODULE_STAGE_LAST + 1,
        )
    )
    + tuple(
        range(
            provider_sources.GATE_STAGE_FIRST,
            provider_sources.GATE_STAGE_LAST + 1,
        )
    )
    + (provider_sources.SUCCESS_STAGE,)
)
TERMINAL_STAGE = provider_sources.SUCCESS_STAGE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P245_E2_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|unsat=S22E1U1-24|"
    "baseline=all-related-families-absent|"
    "accept=one-or-more-p245-e2-terminal-success|"
    "reject=foreign,malformed,partial|zero=ambiguous|"
    f"stages={','.join(f'{stage:02x}' for stage in STAGE_SEQUENCE)}|"
    f"model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]


class DecodeError(ValueError):
    pass


def _require_identity(profile: str, run_id: bytes) -> None:
    if profile != PROFILE:
        raise DecodeError(f"unsupported P2.45 profile: {profile}")
    if len(run_id) != model.RUN_ID_SIZE or not any(run_id):
        raise DecodeError("P2.45 run ID must be one nonzero 128-bit value")


def _expected_item_index(stage: int) -> int:
    if (
        provider_sources.MODULE_STAGE_FIRST
        <= stage
        <= provider_sources.MODULE_STAGE_LAST
    ):
        return stage - provider_sources.MODULE_STAGE_FIRST
    if (
        provider_sources.GATE_STAGE_FIRST
        <= stage
        <= provider_sources.GATE_STAGE_LAST
    ):
        return stage - provider_sources.GATE_STAGE_FIRST
    return 0


def _validate_stage(
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> int:
    try:
        generation = STAGE_SEQUENCE.index(stage) + 1
    except ValueError as exc:
        raise DecodeError(f"stage 0x{stage:02x} is not valid for P2.45 E2") from exc
    if not 0 <= detail <= 4095:
        raise DecodeError("checkpoint detail is outside 0..4095")
    if item_index != _expected_item_index(stage):
        raise DecodeError("checkpoint item index does not match its stage")
    if stage == TERMINAL_STAGE:
        if outcome != model.OUTCOME_SUCCESS or detail != 0:
            raise DecodeError("P2.45 terminal must be zero-detail success")
    elif not (
        (outcome == model.OUTCOME_PROGRESS and detail == 0)
        or (outcome == model.OUTCOME_FAILURE and detail != 0)
    ):
        raise DecodeError("P2.45 nonterminal outcome/detail is invalid")
    return generation


def _slot_crc(header: bytes, slot_id: int, body: bytes) -> int:
    value = model.crc32(
        b"S22PLUS-FYG8-P232-SLOT-V1\0"
        + header
        + bytes([slot_id])
        + body
    )
    if value == 0:
        raise DecodeError("slot CRC zero is reserved")
    return value


def encode_slot(
    header: bytes,
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> bytes:
    slot_id = generation & 1
    if generation == 0:
        if (
            stage != model.STAGES["ENTRY"]
            or outcome != model.OUTCOME_PROGRESS
            or item_index != 0
            or detail != 0
        ):
            raise DecodeError("generation zero must be the kernel ENTRY state")
    elif generation != _validate_stage(stage, outcome, item_index, detail):
        raise DecodeError("slot generation does not match P2.45 stage ordinal")
    body = model.SLOT_BODY_STRUCT.pack(
        generation,
        stage,
        outcome,
        item_index,
        detail,
    )
    return body + struct.pack("<I", _slot_crc(header, slot_id, body))


def _decode_slot(
    header: bytes, slot_id: int, raw: bytes
) -> tuple[model.Slot | None, str]:
    if len(raw) != model.SLOT_SIZE:
        raise DecodeError("compact slot size mismatch")
    body = raw[: model.SLOT_BODY_STRUCT.size]
    recorded_crc = struct.unpack("<I", raw[model.SLOT_BODY_STRUCT.size :])[0]
    if recorded_crc == 0:
        return None, "uncommitted"
    try:
        expected_crc = _slot_crc(header, slot_id, body)
    except DecodeError:
        return None, "bad-crc"
    if recorded_crc != expected_crc:
        return None, "bad-crc"
    generation, stage, outcome, item_index, detail = (
        model.SLOT_BODY_STRUCT.unpack(body)
    )
    if (generation & 1) != slot_id:
        return None, "bad-body"
    try:
        encoded = encode_slot(
            header,
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item_index,
            detail=detail,
        )
    except DecodeError:
        return None, "bad-body"
    if encoded != raw:
        return None, "bad-body"
    return (
        model.Slot(slot_id, generation, stage, outcome, item_index, detail),
        "valid",
    )


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    if len(record) != model.LONG_RECORD_SIZE or not record.startswith(
        model.LONG_FAMILY
    ):
        raise DecodeError("compact record family or size mismatch")
    try:
        model._validate_record_families(record)
    except model.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    format_profile = record[8]
    if format_profile >> 4 != model.FORMAT_VERSION:
        raise DecodeError("compact record format version mismatch")
    profile = model.PROFILE_BY_NUMBER.get(format_profile & 0x0F)
    if profile != expected_profile or profile != PROFILE:
        raise DecodeError("compact record profile mismatch")
    run_id = record[9:25]
    _require_identity(profile, run_id)
    if expected_run_id is not None and run_id != expected_run_id:
        raise DecodeError("compact record run ID mismatch")

    header = record[: model.LONG_HEADER_SIZE]
    valid: list[model.Slot] = []
    slot_status: list[str] = []
    for slot_id in range(model.SLOT_COUNT):
        start = model.LONG_HEADER_SIZE + slot_id * model.SLOT_SIZE
        slot, status = _decode_slot(
            header, slot_id, record[start : start + model.SLOT_SIZE]
        )
        slot_status.append(status)
        if slot is not None:
            valid.append(slot)
    if not valid:
        raise DecodeError("compact record has no valid committed slot")
    valid.sort(key=lambda slot: slot.generation)
    if len(valid) == 2:
        older, newer = valid
        if newer.generation != older.generation + 1:
            raise DecodeError("A/B slot generations are not adjacent")
        if older.outcome != model.OUTCOME_PROGRESS:
            raise DecodeError("checkpoint advanced after a terminal slot")
    active = valid[-1]
    terminal = active.outcome in {model.OUTCOME_SUCCESS, model.OUTCOME_FAILURE}
    return {
        "profile": profile,
        "run_id": run_id.hex(),
        "active": asdict(active),
        "valid_slots": [asdict(slot) for slot in valid],
        "slot_status": slot_status,
        "fallback_used": len(valid) == 1 and active.generation > 0,
        "terminal": terminal,
        "terminal_success": (
            active.outcome == model.OUTCOME_SUCCESS
            and active.stage == TERMINAL_STAGE
        ),
    }


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
