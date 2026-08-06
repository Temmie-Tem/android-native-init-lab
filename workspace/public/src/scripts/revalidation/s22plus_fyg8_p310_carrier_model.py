#!/usr/bin/env python3
"""Model the S22+ FYG8 Carrier v2 retained-record ABI."""

from __future__ import annotations

import binascii
from dataclasses import asdict, dataclass
import hashlib
import struct
from typing import Any, Iterable

import s22plus_fyg8_p308_telemetry_spec as spec
import s22plus_fyg8_retained_snapshot_model as retained


SCHEMA = "s22plus_fyg8_p310_carrier_model_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

LONG_FAMILY = b"S22E1L2|"
UNSAT_FAMILY = b"S22E1U2|"
LEGACY_FAMILIES = (b"S22E1L1|", b"S22E1U1|", b"[[S22P1U|", b"S22UNS1|")
ALL_FAMILIES = (LONG_FAMILY, UNSAT_FAMILY, *LEGACY_FAMILIES)
FORMAT_VERSION = 2
REQUEST_VERSION_V2 = 2
REQUEST_VERSION_V3 = 3
LONG_RECORD_SIZE = 192
LONG_HEADER_SIZE = 32
SLOT_SIZE = 80
SLOT_COUNT = 2
SLOT_PAYLOAD_SIZE = 66
REQUEST_PAYLOAD_SIZE = 64
UNSAT_SIZE = 24
RUN_ID_SIZE = 16

PAYLOAD_NONE = 0
PAYLOAD_RAW_EXCERPT = 1

OUTCOME_PROGRESS = 0
OUTCOME_SUCCESS = 1
OUTCOME_FAILURE = 2
PROFILE_NUMBERS = {"E1A": 1, "E1B": 2, "E2": 3}
PROFILE_BY_NUMBER = {value: key for key, value in PROFILE_NUMBERS.items()}

HEADER_PREFIX_STRUCT = struct.Struct("<8sBBH16s")
HEADER_STRUCT = struct.Struct("<8sBBH16sI")
SLOT_BODY_STRUCT = struct.Struct("<HBBBBBBH66s")
REQUEST_V2_STRUCT = struct.Struct("<4sBBBBHBB16sI")
REQUEST_V3_STRUCT = struct.Struct("<4sBBBBHBBB3s16s64sI")

HEADER_CRC_DOMAIN = b"S22PLUS-FYG8-P310-HEADER-V2\0"
SLOT_CRC_DOMAIN = b"S22PLUS-FYG8-P310-SLOT-V2\0"
UNSAT_DOMAIN = b"S22PLUS-FYG8-P310-UNSAT-V2\0"


class DesignError(ValueError):
    pass


@dataclass(frozen=True)
class Request:
    profile: str
    stage: int
    outcome: int
    item_index: int
    detail: int
    run_id: bytes
    payload_kind: int = PAYLOAD_NONE
    payload: bytes = b""
    version: int = REQUEST_VERSION_V2


@dataclass(frozen=True)
class Slot:
    slot_id: int
    generation: int
    stage: int
    outcome: int
    item_index: int
    detail: int
    payload_kind: int = PAYLOAD_NONE
    payload: bytes = b""


def crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def _require_run_id(run_id: bytes) -> None:
    if len(run_id) != RUN_ID_SIZE or not any(run_id):
        raise DesignError("run ID must be one nonzero 128-bit value")


def _validate_payload(kind: int, payload: bytes) -> None:
    if kind == PAYLOAD_NONE:
        if payload:
            raise DesignError("payload-none request carries bytes")
        return
    if kind == PAYLOAD_RAW_EXCERPT:
        if not 1 <= len(payload) <= REQUEST_PAYLOAD_SIZE:
            raise DesignError("raw excerpt is outside 1..64 bytes")
        return
    raise DesignError("payload kind is not allowlisted")


def _validate_semantics(request: Request, generation: int) -> None:
    if request.profile != spec.PROFILE:
        raise DesignError("only the E2 carrier profile is supported")
    try:
        spec.validate_slot(
            generation=generation,
            stage=request.stage,
            outcome=request.outcome,
            item_index=request.item_index,
            detail=request.detail,
        )
    except spec.SpecError as exc:
        raise DesignError(str(exc)) from exc
    _validate_payload(request.payload_kind, request.payload)


def model_run_id(profile: str = spec.PROFILE) -> bytes:
    if profile != spec.PROFILE:
        raise DesignError("unsupported model profile")
    return hashlib.sha256(b"S22PLUS-FYG8-P310-CARRIER-MODEL-V2\0" + profile.encode()).digest()[:16]


def _header(profile: str, run_id: bytes) -> bytes:
    _require_run_id(run_id)
    number = PROFILE_NUMBERS.get(profile)
    if number is None:
        raise DesignError("record profile is not allowlisted")
    prefix = HEADER_PREFIX_STRUCT.pack(
        LONG_FAMILY,
        (FORMAT_VERSION << 4) | number,
        LONG_HEADER_SIZE,
        LONG_RECORD_SIZE,
        run_id,
    )
    value = crc32(HEADER_CRC_DOMAIN + prefix)
    if value == 0:
        raise DesignError("zero header CRC is reserved")
    return prefix + struct.pack("<I", value)


def _decode_header(raw: bytes, expected_profile: str | None, expected_run_id: bytes | None) -> tuple[str, bytes]:
    if len(raw) != LONG_HEADER_SIZE:
        raise DesignError("carrier header size mismatch")
    family, format_profile, header_size, record_size, run_id, recorded = HEADER_STRUCT.unpack(raw)
    if family != LONG_FAMILY or format_profile >> 4 != FORMAT_VERSION:
        raise DesignError("carrier header family or version mismatch")
    if header_size != LONG_HEADER_SIZE or record_size != LONG_RECORD_SIZE:
        raise DesignError("carrier header shape mismatch")
    if recorded == 0 or crc32(HEADER_CRC_DOMAIN + raw[:-4]) != recorded:
        raise DesignError("carrier header CRC mismatch")
    profile = PROFILE_BY_NUMBER.get(format_profile & 0x0F)
    if profile is None:
        raise DesignError("carrier profile is not allowlisted")
    _require_run_id(run_id)
    if expected_profile is not None and profile != expected_profile:
        raise DesignError("carrier profile mismatch")
    if expected_run_id is not None and run_id != expected_run_id:
        raise DesignError("carrier run ID mismatch")
    return profile, run_id


def _slot_crc(header: bytes, slot_id: int, body: bytes) -> int:
    value = crc32(SLOT_CRC_DOMAIN + header + bytes([slot_id]) + body)
    if value == 0:
        raise DesignError("zero slot CRC is reserved")
    return value


def _slot_body(slot: Slot) -> bytes:
    if slot.slot_id not in {0, 1} or not 0 <= slot.generation <= 0xFFFF:
        raise DesignError("slot identity or generation is invalid")
    if (slot.generation & 1) != slot.slot_id:
        raise DesignError("slot parity differs from its generation")
    _validate_payload(slot.payload_kind, slot.payload)
    padded = slot.payload + bytes(SLOT_PAYLOAD_SIZE - len(slot.payload))
    return SLOT_BODY_STRUCT.pack(
        slot.generation,
        slot.stage,
        slot.outcome,
        slot.item_index,
        slot.payload_kind,
        len(slot.payload),
        0,
        slot.detail,
        padded,
    )


def _encode_slot(header: bytes, slot: Slot) -> bytes:
    body = _slot_body(slot)
    return body + struct.pack("<I", _slot_crc(header, slot.slot_id, body))


def _decode_slot(header: bytes, slot_id: int, raw: bytes, profile: str) -> tuple[Slot | None, str]:
    if len(raw) != SLOT_SIZE:
        raise DesignError("carrier slot size mismatch")
    body, recorded_raw = raw[:-4], raw[-4:]
    recorded = struct.unpack("<I", recorded_raw)[0]
    if recorded == 0:
        return None, "uncommitted"
    try:
        expected = _slot_crc(header, slot_id, body)
    except DesignError:
        return None, "bad-crc"
    if recorded != expected:
        return None, "bad-crc"
    generation, stage, outcome, item, kind, length, reserved, detail, padded = SLOT_BODY_STRUCT.unpack(body)
    if reserved or length > REQUEST_PAYLOAD_SIZE or any(padded[length:]):
        return None, "bad-body"
    payload = padded[:length]
    slot = Slot(slot_id, generation, stage, outcome, item, detail, kind, payload)
    try:
        if generation == 0:
            if slot != Slot(0, 0, 0, OUTCOME_PROGRESS, 0, 0):
                raise DesignError("generation zero differs")
        else:
            _validate_semantics(
                Request(profile, stage, outcome, item, detail, b"x" * 16, kind, payload),
                generation,
            )
        if _encode_slot(header, slot) != raw:
            raise DesignError("slot canonical encoding differs")
    except DesignError:
        return None, "bad-body"
    return slot, "valid"


def initialize_record(profile: str, run_id: bytes) -> bytes:
    header = _header(profile, run_id)
    entry = _encode_slot(header, Slot(0, 0, 0, OUTCOME_PROGRESS, 0, 0))
    record = header + entry + bytes(SLOT_SIZE)
    if len(record) != LONG_RECORD_SIZE:
        raise DesignError("carrier record size changed")
    decode_record(record, expected_profile=profile, expected_run_id=run_id)
    return record


def unsat_record(profile: str, run_id: bytes) -> bytes:
    header = _header(profile, run_id)
    tag = hashlib.sha256(UNSAT_DOMAIN + header).digest()[:16]
    return UNSAT_FAMILY + tag


def encode_request(
    profile: str,
    stage: int,
    *,
    run_id: bytes,
    outcome: int = OUTCOME_PROGRESS,
    item_index: int = 0,
    detail: int = 0,
    payload_kind: int = PAYLOAD_NONE,
    payload: bytes = b"",
    version: int | None = None,
) -> bytes:
    _require_run_id(run_id)
    request_version = REQUEST_VERSION_V2 if version is None and payload_kind == PAYLOAD_NONE and not payload else REQUEST_VERSION_V3 if version is None else version
    request = Request(profile, stage, outcome, item_index, detail, run_id, payload_kind, payload, request_version)
    # The current generation is validated when the request is applied.
    _validate_payload(payload_kind, payload)
    number = PROFILE_NUMBERS[profile]
    if request_version == REQUEST_VERSION_V2:
        if payload_kind != PAYLOAD_NONE or payload:
            raise DesignError("v2 request cannot carry a payload")
        prefix = REQUEST_V2_STRUCT.pack(b"S22Q", request_version, number, stage, outcome, detail, item_index, 0, run_id, 0)[:-4]
    elif request_version == REQUEST_VERSION_V3:
        padded = payload + bytes(REQUEST_PAYLOAD_SIZE - len(payload))
        prefix = REQUEST_V3_STRUCT.pack(
            b"S22Q", request_version, number, stage, outcome, detail,
            item_index, payload_kind, len(payload), bytes(3), run_id, padded, 0,
        )[:-4]
    else:
        raise DesignError("request version is not supported")
    return prefix + struct.pack("<I", crc32(prefix))


def decode_request(data: bytes) -> Request:
    if len(data) == REQUEST_V2_STRUCT.size:
        magic, version, number, stage, outcome, detail, item, reserved, run_id, recorded = REQUEST_V2_STRUCT.unpack(data)
        kind, payload = PAYLOAD_NONE, b""
        valid_header = version == REQUEST_VERSION_V2 and reserved == 0
    elif len(data) == REQUEST_V3_STRUCT.size:
        magic, version, number, stage, outcome, detail, item, kind, length, reserved, run_id, padded, recorded = REQUEST_V3_STRUCT.unpack(data)
        valid_header = version == REQUEST_VERSION_V3 and reserved == bytes(3) and length <= REQUEST_PAYLOAD_SIZE and not any(padded[length:])
        payload = padded[:length] if length <= REQUEST_PAYLOAD_SIZE else b""
    else:
        raise DesignError("checkpoint request size mismatch")
    if magic != b"S22Q" or not valid_header or crc32(data[:-4]) != recorded:
        raise DesignError("checkpoint request header or CRC mismatch")
    profile = PROFILE_BY_NUMBER.get(number)
    if profile is None:
        raise DesignError("checkpoint request profile is not allowlisted")
    _require_run_id(run_id)
    _validate_payload(kind, payload)
    return Request(profile, stage, outcome, item, detail, run_id, kind, payload, version)


def decode_record(record: bytes, *, expected_profile: str | None = None, expected_run_id: bytes | None = None) -> dict[str, Any]:
    if len(record) != LONG_RECORD_SIZE:
        raise DesignError("carrier record size mismatch")
    header = record[:LONG_HEADER_SIZE]
    profile, run_id = _decode_header(header, expected_profile, expected_run_id)
    valid: list[Slot] = []
    statuses: list[str] = []
    for slot_id in range(SLOT_COUNT):
        start = LONG_HEADER_SIZE + slot_id * SLOT_SIZE
        slot, status = _decode_slot(header, slot_id, record[start : start + SLOT_SIZE], profile)
        statuses.append(status)
        if slot is not None:
            valid.append(slot)
    if not valid:
        raise DesignError("carrier has no valid committed slot")
    valid.sort(key=lambda row: row.generation)
    if len(valid) == 2:
        older, newer = valid
        if newer.generation != older.generation + 1:
            raise DesignError("carrier A/B generations are not adjacent")
        if older.outcome != OUTCOME_PROGRESS:
            raise DesignError("carrier advanced after a terminal slot")
    active = valid[-1]
    return {
        "profile": profile,
        "run_id": run_id.hex(),
        "header_crc_valid": True,
        "slot_status": statuses,
        "valid_slots": [asdict(row) for row in valid],
        "active": asdict(active),
        "fallback_used": len(valid) == 1 and active.generation > 0,
        "terminal_success": (
            active.outcome == OUTCOME_SUCCESS
            and (active.stage, active.item_index) == spec.TERMINAL_POSITION.pair
        ),
    }


def apply_request(record: bytes, request_data: bytes, *, stop_after: str | None = None) -> bytes:
    decoded = decode_record(record)
    request = decode_request(request_data)
    if bytes.fromhex(decoded["run_id"]) != request.run_id or decoded["profile"] != request.profile:
        raise DesignError("request identity differs from record")
    active = Slot(**decoded["active"])
    if active.outcome != OUTCOME_PROGRESS:
        raise DesignError("terminal carrier cannot advance")
    generation = active.generation + 1
    _validate_semantics(request, generation)
    slot_id = active.slot_id ^ 1
    next_slot = Slot(slot_id, generation, request.stage, request.outcome, request.item_index, request.detail, request.payload_kind, request.payload)
    header = record[:LONG_HEADER_SIZE]
    encoded = _encode_slot(header, next_slot)
    start = LONG_HEADER_SIZE + slot_id * SLOT_SIZE
    value = bytearray(record)
    value[start + SLOT_SIZE - 4 : start + SLOT_SIZE] = bytes(4)
    if stop_after == "invalidate":
        return bytes(value)
    value[start : start + SLOT_SIZE - 4] = encoded[:-4]
    if stop_after == "body":
        return bytes(value)
    if stop_after not in {None, "commit"}:
        raise DesignError("unknown torn-write phase")
    value[start + SLOT_SIZE - 4 : start + SLOT_SIZE] = encoded[-4:]
    result = bytes(value)
    decode_record(result, expected_profile=request.profile, expected_run_id=request.run_id)
    return result


def _positions(payload: bytes, family: bytes) -> list[int]:
    rows: list[int] = []
    cursor = 0
    while True:
        position = payload.find(family, cursor)
        if position < 0:
            return rows
        rows.append(position)
        cursor = position + 1


def _inside(position: int, spans: Iterable[tuple[int, int]], *, allow_start: bool = False) -> bool:
    return any(start <= position < end and (allow_start or position != start) for start, end in spans)


def classify_clean_baseline(payload: bytes, *, expected_profile: str, expected_run_id: bytes) -> dict[str, Any]:
    del expected_profile, expected_run_id
    hits = {family.decode("ascii", "replace"): len(_positions(payload, family)) for family in ALL_FAMILIES}
    if any(hits.values()):
        raise DesignError("baseline contains a current or legacy evidence family")
    return {"classification": "CLEAN_BASELINE", "family_hits": hits, "verified": True}


def classify_observation(payload: bytes, *, expected_profile: str, expected_run_id: bytes) -> dict[str, Any]:
    candidates: list[tuple[int, dict[str, Any]]] = []
    malformed_positions: list[int] = []
    for position in _positions(payload, LONG_FAMILY):
        end = position + LONG_RECORD_SIZE
        if end > len(payload):
            malformed_positions.append(position)
            continue
        try:
            decoded = decode_record(payload[position:end], expected_profile=expected_profile, expected_run_id=expected_run_id)
        except DesignError:
            malformed_positions.append(position)
        else:
            decoded["observer_offset"] = position
            candidates.append((position, decoded))
    spans = [(position, position + LONG_RECORD_SIZE) for position, _row in candidates]
    integrity: list[str] = []
    outside_malformed = [position for position in malformed_positions if not _inside(position, spans)]
    if outside_malformed:
        integrity.append("foreign-or-malformed-v2-long-record")
    expected_unsat = unsat_record(expected_profile, expected_run_id)
    outside_unsat_positions = [position for position in _positions(payload, UNSAT_FAMILY) if not _inside(position, spans)]
    unsat_count = sum(payload[position : position + UNSAT_SIZE] == expected_unsat for position in outside_unsat_positions)
    if unsat_count != len(outside_unsat_positions):
        integrity.append("foreign-or-malformed-v2-unsat-record")
    legacy_outside = {
        family: [position for position in _positions(payload, family) if not _inside(position, spans)]
        for family in LEGACY_FAMILIES
    }
    if any(legacy_outside.values()):
        integrity.append("legacy-or-foreign-evidence-family")
    records = [row for _position, row in candidates]
    success_count = sum(row["terminal_success"] for row in records)
    failure_count = sum(row["active"]["outcome"] == OUTCOME_FAILURE for row in records)
    progress_count = sum(row["active"]["generation"] > 0 and row["active"]["outcome"] == OUTCOME_PROGRESS for row in records)
    entry_count = sum(row["active"]["generation"] == 0 for row in records)
    if integrity:
        classification, accepted = "AMBIGUOUS_INTEGRITY_FAILURE", False
    elif success_count:
        classification, accepted = f"{expected_profile}_SUCCESS_ONE_OR_MORE_BOOTS", True
    elif failure_count:
        classification, accepted = f"{expected_profile}_FAILURE_OBSERVED", False
    elif progress_count:
        classification, accepted = f"{expected_profile}_PROGRESS_OBSERVED", False
    elif entry_count:
        classification, accepted = "ENTRY_ONLY_ONE_OR_MORE_BOOTS", False
    elif unsat_count:
        classification, accepted = "UNSAT_VALID_MAGIC_ONE_OR_MORE_BOOTS", False
    else:
        classification, accepted = "ZERO_AMBIGUOUS", False
    outside_family_count = (
        len(outside_malformed) + len(candidates) + len(outside_unsat_positions)
        + sum(len(rows) for rows in legacy_outside.values())
    )
    exact_record_count = len(records) + unsat_count
    return {
        "classification": classification,
        "accepted": accepted,
        "integrity_issue": bool(integrity),
        "integrity_issues": integrity,
        "long_record_count": len(records),
        "unsat_count": unsat_count,
        "entry_count": entry_count,
        "progress_count": progress_count,
        "failure_count": failure_count,
        "success_count": success_count,
        "fallback_record_count": sum(row["fallback_used"] for row in records),
        "minimum_candidate_boots": exact_record_count if not integrity else 0,
        "family_count": outside_family_count,
        "exact_record_count": exact_record_count,
        "foreign_count": max(0, outside_family_count - exact_record_count),
        "embedded_family_count": sum(
            len(_positions(payload[start:end], family)) - (1 if family == LONG_FAMILY else 0)
            for start, end in spans for family in ALL_FAMILIES
        ),
        "records": records,
    }


def simulate_initial_visibility(
    profile: str,
    run_id: bytes,
    *,
    idx: int,
    payload_size: int = 512,
) -> dict[str, Any]:
    if payload_size < LONG_RECORD_SIZE:
        raise DesignError("simulation payload is smaller than Carrier v2")
    if idx < UNSAT_SIZE:
        proof, state = b"", "NONE"
    elif idx < LONG_RECORD_SIZE:
        proof, state = unsat_record(profile, run_id), "UNSAT"
    else:
        proof, state = initialize_record(profile, run_id), "ENTRY"
    payload = b"\xa5" * payload_size
    if proof:
        payload, offset = retained.place_precursor(payload, idx, proof)
    else:
        offset = None
    result = classify_observation(
        payload,
        expected_profile=profile,
        expected_run_id=run_id,
    )
    return {
        "idx": idx,
        "selected_state": state,
        "proof_offset": offset,
        "changed_bytes": len(proof),
        **result,
    }


def validate() -> dict[str, Any]:
    if HEADER_STRUCT.size != LONG_HEADER_SIZE or SLOT_BODY_STRUCT.size + 4 != SLOT_SIZE or REQUEST_V2_STRUCT.size != 32 or REQUEST_V3_STRUCT.size != 100:
        raise DesignError("Carrier v2 structure sizes differ")
    run_id = model_run_id()
    record = initialize_record(spec.PROFILE, run_id)
    first_position = spec.POSITIONS[0]
    request = encode_request(spec.PROFILE, first_position.stage, run_id=run_id, item_index=first_position.item_index)
    advanced = apply_request(record, request)
    for phase in ("invalidate", "body"):
        torn = decode_record(apply_request(record, request, stop_after=phase), expected_profile=spec.PROFILE, expected_run_id=run_id)
        if torn["active"]["generation"] != 0:
            raise DesignError("torn update did not retain the previous slot")
    excerpt = b"prefix-" + LONG_FAMILY + b"-" + LEGACY_FAMILIES[0] + b"-suffix"
    request3 = encode_request(spec.PROFILE, first_position.stage, run_id=run_id, item_index=first_position.item_index, payload_kind=PAYLOAD_RAW_EXCERPT, payload=excerpt, version=REQUEST_VERSION_V3)
    with_excerpt = apply_request(record, request3)
    observed = b"left" + with_excerpt + b"right"
    classified = classify_observation(observed, expected_profile=spec.PROFILE, expected_run_id=run_id)
    if classified["foreign_count"] or classified["integrity_issue"] or classified["embedded_family_count"] < 2:
        raise DesignError("embedded family exclusion contract failed")
    if decode_record(advanced)["active"]["generation"] != 1:
        raise DesignError("committed update did not advance")
    boundary = {
        idx: simulate_initial_visibility(spec.PROFILE, run_id, idx=idx)["classification"]
        for idx in (0, 23, 24, 191, 192, 511, 512, 513)
    }
    expected_boundary = {
        0: "ZERO_AMBIGUOUS",
        23: "ZERO_AMBIGUOUS",
        24: "UNSAT_VALID_MAGIC_ONE_OR_MORE_BOOTS",
        191: "UNSAT_VALID_MAGIC_ONE_OR_MORE_BOOTS",
        192: "ENTRY_ONLY_ONE_OR_MORE_BOOTS",
        511: "ENTRY_ONLY_ONE_OR_MORE_BOOTS",
        512: "ENTRY_ONLY_ONE_OR_MORE_BOOTS",
        513: "ENTRY_ONLY_ONE_OR_MORE_BOOTS",
    }
    if boundary != expected_boundary:
        raise DesignError("Carrier v2 wrap boundary matrix failed")
    return {
        "schema": SCHEMA,
        "record_size": LONG_RECORD_SIZE,
        "header_size": LONG_HEADER_SIZE,
        "slot_size": SLOT_SIZE,
        "slot_count": SLOT_COUNT,
        "request_v2_size": REQUEST_V2_STRUCT.size,
        "request_v3_size": REQUEST_V3_STRUCT.size,
        "raw_excerpt_max": REQUEST_PAYLOAD_SIZE,
        "header_crc": True,
        "double_slot_recovery": True,
        "legacy_decoding_boundary": "historical-v1-decoder-unchanged-current-v2-rejects-v1",
        "foreign_count_excludes_valid_v2_record_spans": True,
        "boundary_matrix": boundary,
        "verified": True,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(validate(), sort_keys=True))
