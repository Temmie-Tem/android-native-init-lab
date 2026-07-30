#!/usr/bin/env python3
"""Pair-aware P2.88 retained latest-stage model with unchanged wire layout."""

from __future__ import annotations

import struct
from dataclasses import asdict
from typing import Any

import s22plus_fyg8_p232_e1_latest_stage_design as base
import s22plus_fyg8_p288_contract_spec as spec


SCHEMA = "s22plus_fyg8_p288_latest_stage_position_model_v1"
PROFILE = spec.PROFILE

LONG_FAMILY = base.LONG_FAMILY
UNSAT_FAMILY = base.UNSAT_FAMILY
LEGACY_FAMILIES = base.LEGACY_FAMILIES
FORMAT_VERSION = base.FORMAT_VERSION
REQUEST_VERSION = base.REQUEST_VERSION
LONG_RECORD_SIZE = base.LONG_RECORD_SIZE
LONG_HEADER_SIZE = base.LONG_HEADER_SIZE
SLOT_SIZE = base.SLOT_SIZE
SLOT_COUNT = base.SLOT_COUNT
UNSAT_SIZE = base.UNSAT_SIZE
RUN_ID_SIZE = base.RUN_ID_SIZE
OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_SUCCESS = base.OUTCOME_SUCCESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE
PROFILE_NUMBERS = base.PROFILE_NUMBERS
PROFILE_BY_NUMBER = base.PROFILE_BY_NUMBER
STAGES = base.STAGES
REQUEST_STRUCT = base.REQUEST_STRUCT
SLOT_BODY_STRUCT = base.SLOT_BODY_STRUCT
Request = base.Request
Slot = base.Slot
DesignError = base.DesignError
crc32 = base.crc32
_record_header = base._record_header
_slot_crc = base._slot_crc
_validate_record_families = base._validate_record_families
_edge_family_partial = base._edge_family_partial
_family_positions = base._family_positions
unsat_record = base.unsat_record
model_run_id = base.model_run_id

PROFILE_POSITION_SEQUENCES = {PROFILE: spec.POSITION_SEQUENCE}
PROFILE_TERMINAL_POSITIONS = {PROFILE: spec.TERMINAL_POSITION}
PROFILE_TERMINALS = {PROFILE: spec.TERMINAL_STAGE}


def _require_run_id(run_id: bytes) -> None:
    if len(run_id) != RUN_ID_SIZE or not any(run_id):
        raise DesignError("P2.88 run ID must be one nonzero 128-bit value")


def _sequence(profile: str) -> tuple[tuple[int, int], ...]:
    try:
        return PROFILE_POSITION_SEQUENCES[profile]
    except KeyError as exc:
        raise DesignError(f"unsupported P2.88 profile: {profile}") from exc


def generation_for_position(
    profile: str, stage: int, item_index: int
) -> int:
    if profile != PROFILE:
        raise DesignError(f"unsupported P2.88 profile: {profile}")
    try:
        return spec.generation_for_position(stage, item_index)
    except spec.SpecError as exc:
        raise DesignError(str(exc)) from exc


def _validate_position_semantics(
    profile: str,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    if profile != PROFILE:
        raise DesignError(f"unsupported P2.88 profile: {profile}")
    try:
        spec.validate_slot(
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item_index,
            detail=detail,
        )
    except spec.SpecError as exc:
        raise DesignError(str(exc)) from exc


def encode_request(
    profile: str,
    stage: int,
    *,
    run_id: bytes,
    outcome: int = OUTCOME_PROGRESS,
    item_index: int = 0,
    detail: int = 0,
) -> bytes:
    _require_run_id(run_id)
    generation = generation_for_position(profile, stage, item_index)
    _validate_position_semantics(
        profile, generation, stage, outcome, item_index, detail
    )
    prefix = REQUEST_STRUCT.pack(
        b"S22Q",
        REQUEST_VERSION,
        PROFILE_NUMBERS[profile],
        stage,
        outcome,
        detail,
        item_index,
        0,
        run_id,
        0,
    )[:-4]
    return prefix + struct.pack("<I", crc32(prefix))


def decode_request(data: bytes) -> Request:
    if len(data) != REQUEST_STRUCT.size:
        raise DesignError("P2.88 checkpoint request size mismatch")
    (
        magic,
        version,
        profile_number,
        stage,
        outcome,
        detail,
        item_index,
        reserved,
        run_id,
        recorded_crc,
    ) = REQUEST_STRUCT.unpack(data)
    if magic != b"S22Q" or version != REQUEST_VERSION or reserved != 0:
        raise DesignError("P2.88 checkpoint request header mismatch")
    if crc32(data[:-4]) != recorded_crc:
        raise DesignError("P2.88 checkpoint request CRC mismatch")
    profile = PROFILE_BY_NUMBER.get(profile_number)
    if profile != PROFILE:
        raise DesignError("P2.88 checkpoint request profile mismatch")
    _require_run_id(run_id)
    generation = generation_for_position(profile, stage, item_index)
    _validate_position_semantics(
        profile, generation, stage, outcome, item_index, detail
    )
    return Request(profile, stage, outcome, item_index, detail, run_id)


def _encode_slot(header: bytes, slot: Slot) -> bytes:
    if slot.slot_id not in {0, 1} or not 0 <= slot.generation <= 0xFF:
        raise DesignError("P2.88 slot identity or generation is invalid")
    if (slot.generation & 1) != slot.slot_id:
        raise DesignError("P2.88 slot generation parity mismatch")
    profile = PROFILE_BY_NUMBER[header[8] & 0x0F]
    if slot.generation == 0:
        if (
            slot.stage != STAGES["ENTRY"]
            or slot.outcome != OUTCOME_PROGRESS
            or slot.item_index != 0
            or slot.detail != 0
        ):
            raise DesignError("generation zero is not the kernel ENTRY state")
    else:
        _validate_position_semantics(
            profile,
            slot.generation,
            slot.stage,
            slot.outcome,
            slot.item_index,
            slot.detail,
        )
    body = SLOT_BODY_STRUCT.pack(
        slot.generation,
        slot.stage,
        slot.outcome,
        slot.item_index,
        slot.detail,
    )
    return body + struct.pack(
        "<I", _slot_crc(header, slot.slot_id, body)
    )


def _decode_slot(
    header: bytes, slot_id: int, raw: bytes
) -> tuple[Slot | None, str]:
    if len(raw) != SLOT_SIZE:
        raise DesignError("P2.88 compact slot size mismatch")
    body = raw[: SLOT_BODY_STRUCT.size]
    recorded_crc = struct.unpack("<I", raw[SLOT_BODY_STRUCT.size :])[0]
    if recorded_crc == 0:
        return None, "uncommitted"
    try:
        expected_crc = _slot_crc(header, slot_id, body)
    except DesignError:
        return None, "bad-crc"
    if recorded_crc != expected_crc:
        return None, "bad-crc"
    generation, stage, outcome, item_index, detail = SLOT_BODY_STRUCT.unpack(
        body
    )
    slot = Slot(slot_id, generation, stage, outcome, item_index, detail)
    try:
        if _encode_slot(header, slot) != raw:
            return None, "bad-body"
    except DesignError:
        return None, "bad-body"
    return slot, "valid"


def initialize_record(profile: str, run_id: bytes) -> bytes:
    if profile != PROFILE:
        raise DesignError(f"unsupported P2.88 profile: {profile}")
    header = _record_header(profile, run_id)
    entry = _encode_slot(
        header,
        Slot(0, 0, STAGES["ENTRY"], OUTCOME_PROGRESS, 0, 0),
    )
    record = header + entry + bytes(SLOT_SIZE)
    if len(record) != LONG_RECORD_SIZE:
        raise DesignError("P2.88 retained record size changed")
    _validate_record_families(record)
    decode_record(record, expected_profile=profile, expected_run_id=run_id)
    return record


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    if len(record) != LONG_RECORD_SIZE or not record.startswith(LONG_FAMILY):
        raise DesignError("P2.88 compact record family or size mismatch")
    _validate_record_families(record)
    format_profile = record[8]
    if format_profile >> 4 != FORMAT_VERSION:
        raise DesignError("P2.88 compact record format mismatch")
    profile = PROFILE_BY_NUMBER.get(format_profile & 0x0F)
    if profile != expected_profile or profile != PROFILE:
        raise DesignError("P2.88 compact record profile mismatch")
    run_id = record[9:25]
    _require_run_id(run_id)
    if expected_run_id is not None and run_id != expected_run_id:
        raise DesignError("P2.88 compact record run ID mismatch")

    header = record[:LONG_HEADER_SIZE]
    valid: list[Slot] = []
    slot_status: list[str] = []
    for slot_id in range(SLOT_COUNT):
        start = LONG_HEADER_SIZE + slot_id * SLOT_SIZE
        slot, status = _decode_slot(
            header, slot_id, record[start : start + SLOT_SIZE]
        )
        slot_status.append(status)
        if slot is not None:
            valid.append(slot)
    if not valid:
        raise DesignError("P2.88 record has no valid committed slot")
    valid.sort(key=lambda slot: slot.generation)
    if len(valid) == 2:
        older, newer = valid
        if newer.generation != older.generation + 1:
            raise DesignError("P2.88 A/B generations are not adjacent")
        if older.outcome != OUTCOME_PROGRESS:
            raise DesignError("checkpoint advanced after a terminal slot")
    active = valid[-1]
    terminal = active.outcome in {OUTCOME_SUCCESS, OUTCOME_FAILURE}
    terminal_success = (
        active.generation == spec.TERMINAL_GENERATION
        and (active.stage, active.item_index) == spec.TERMINAL_POSITION
        and active.outcome == OUTCOME_SUCCESS
        and active.detail == 0
    )
    return {
        "profile": profile,
        "run_id": run_id.hex(),
        "active": asdict(active),
        "valid_slots": [asdict(slot) for slot in valid],
        "slot_status": slot_status,
        "fallback_used": len(valid) == 1 and active.generation > 0,
        "terminal": terminal,
        "terminal_success": terminal_success,
    }


def apply_request(
    record: bytes, request_data: bytes, *, stop_after: str = "commit"
) -> bytes:
    if stop_after not in {"invalidate", "body", "commit"}:
        raise DesignError("unknown P2.88 modeled write stop point")
    decoded = decode_record(record)
    request = decode_request(request_data)
    if decoded["terminal"]:
        raise DesignError("checkpoint record is already terminal")
    if (
        request.profile != decoded["profile"]
        or request.run_id.hex() != decoded["run_id"]
    ):
        raise DesignError("P2.88 request changes record identity")
    active = Slot(**decoded["active"])
    sequence = _sequence(request.profile)
    requested = (request.stage, request.item_index)
    if (
        active.generation >= len(sequence)
        or requested != sequence[active.generation]
    ):
        raise DesignError("checkpoint request is not the exact next position")

    target_id = active.slot_id ^ 1
    next_slot = Slot(
        target_id,
        active.generation + 1,
        request.stage,
        request.outcome,
        request.item_index,
        request.detail,
    )
    header = record[:LONG_HEADER_SIZE]
    encoded = _encode_slot(header, next_slot)
    start = LONG_HEADER_SIZE + target_id * SLOT_SIZE
    updated = bytearray(record)
    updated[start + SLOT_BODY_STRUCT.size : start + SLOT_SIZE] = bytes(4)
    if stop_after == "invalidate":
        return bytes(updated)
    updated[start : start + SLOT_BODY_STRUCT.size] = encoded[
        : SLOT_BODY_STRUCT.size
    ]
    if stop_after == "body":
        return bytes(updated)
    updated[start + SLOT_BODY_STRUCT.size : start + SLOT_SIZE] = encoded[
        SLOT_BODY_STRUCT.size :
    ]
    final = bytes(updated)
    checked = decode_record(
        final,
        expected_profile=request.profile,
        expected_run_id=request.run_id,
    )
    if checked["active"]["generation"] != next_slot.generation:
        raise DesignError("P2.88 committed checkpoint did not become active")
    return final


def _classify(
    baseline: bytes,
    observed: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    _require_run_id(expected_run_id)
    all_families = (LONG_FAMILY, UNSAT_FAMILY, *LEGACY_FAMILIES)
    if any(family in baseline for family in all_families) or _edge_family_partial(
        baseline, all_families
    ):
        raise DesignError("P2.88 baseline contains related evidence")

    integrity_issues: list[str] = []
    records: list[dict[str, Any]] = []
    for position in _family_positions(observed, LONG_FAMILY):
        end = position + LONG_RECORD_SIZE
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
        except DesignError as exc:
            integrity_issues.append(str(exc))

    expected_unsat = unsat_record(expected_profile, expected_run_id)
    unsat_count = observed.count(expected_unsat)
    if observed.count(UNSAT_FAMILY) != unsat_count:
        integrity_issues.append("foreign-or-malformed-unsat-record")
    for family in LEGACY_FAMILIES:
        if family in observed:
            integrity_issues.append("legacy-or-foreign-evidence-family")
    if _edge_family_partial(observed, all_families):
        integrity_issues.append("partial-family-at-snapshot-edge")

    success_count = sum(record["terminal_success"] for record in records)
    failure_count = sum(
        record["active"]["outcome"] == OUTCOME_FAILURE for record in records
    )
    progress_count = sum(
        record["active"]["generation"] > 0
        and record["active"]["outcome"] == OUTCOME_PROGRESS
        for record in records
    )
    entry_count = sum(
        record["active"]["generation"] == 0 for record in records
    )
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
        "fallback_record_count": sum(
            record["fallback_used"] for record in records
        ),
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
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    try:
        _classify(
            payload,
            b"",
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except DesignError as exc:
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
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    return _classify(
        b"",
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
