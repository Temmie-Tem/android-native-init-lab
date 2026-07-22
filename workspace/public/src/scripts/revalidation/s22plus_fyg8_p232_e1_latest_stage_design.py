#!/usr/bin/env python3
"""Model the compact P2.32 E1 latest-stage carrier host-only."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_retained_snapshot_model as retained  # noqa: E402


SCHEMA = "s22plus_fyg8_p232_e1_latest_stage_design_v1"
VERDICT = "PASS_P232_E1_LATEST_STAGE_DESIGN_HOST_ONLY"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

LONG_FAMILY = b"S22E1L1|"
UNSAT_FAMILY = b"S22E1U1|"
LEGACY_FAMILIES = (b"[[S22P1U|", b"S22UNS1|")
FORMAT_VERSION = 1
REQUEST_VERSION = 2
LONG_RECORD_SIZE = 45
LONG_HEADER_SIZE = 25
SLOT_SIZE = 10
SLOT_COUNT = 2
UNSAT_SIZE = 24
RUN_ID_SIZE = 16

OUTCOME_PROGRESS = 0
OUTCOME_SUCCESS = 1
OUTCOME_FAILURE = 2

PROFILE_NUMBERS = {"E1A": 1, "E1B": 2, "E2": 3}
PROFILE_BY_NUMBER = {value: key for key, value in PROFILE_NUMBERS.items()}

STAGES = {
    "ENTRY": 0x00,
    "PROC_MOUNTED": 0x10,
    "SYS_MOUNTED": 0x11,
    "DEV_TMPFS_MOUNTED": 0x12,
    "RUN_TMPFS_MOUNTED": 0x13,
    "DEV_NODES_VERIFIED": 0x14,
    "CHILD_EXEC_STARTED": 0x20,
    "CHILD_TOKEN_VERIFIED": 0x21,
    "CHILD_REAPED": 0x22,
    "E1A_SUCCESS": 0x2F,
    "WDT_MODULE_0": 0x30,
    "WDT_MODULE_1": 0x31,
    "WDT_MODULE_2": 0x32,
    "WDT_MODULE_3": 0x33,
    "WDT_MODULE_4": 0x34,
    "WDT_MODULES_VERIFIED": 0x35,
    "E1B_SUCCESS": 0x3F,
    "E2_MODULE_0": 0x40,
    "E2_MODULE_58": 0x7A,
    "E2_GATE_0": 0x7B,
    "E2_GATE_7": 0x82,
    "E2_SUCCESS": 0x8F,
}

E1_LOCAL_SEQUENCE = (
    STAGES["PROC_MOUNTED"],
    STAGES["SYS_MOUNTED"],
    STAGES["DEV_TMPFS_MOUNTED"],
    STAGES["RUN_TMPFS_MOUNTED"],
    STAGES["DEV_NODES_VERIFIED"],
    STAGES["CHILD_EXEC_STARTED"],
    STAGES["CHILD_TOKEN_VERIFIED"],
    STAGES["CHILD_REAPED"],
)
PROFILE_STAGE_SEQUENCES = {
    "E1A": E1_LOCAL_SEQUENCE + (STAGES["E1A_SUCCESS"],),
    "E1B": E1_LOCAL_SEQUENCE
    + (
        STAGES["WDT_MODULE_0"],
        STAGES["WDT_MODULE_1"],
        STAGES["WDT_MODULE_2"],
        STAGES["WDT_MODULE_3"],
        STAGES["WDT_MODULE_4"],
        STAGES["WDT_MODULES_VERIFIED"],
        STAGES["E1B_SUCCESS"],
    ),
    "E2": E1_LOCAL_SEQUENCE
    + tuple(range(STAGES["E2_MODULE_0"], STAGES["E2_MODULE_58"] + 1))
    + tuple(range(STAGES["E2_GATE_0"], STAGES["E2_GATE_7"] + 1))
    + (STAGES["E2_SUCCESS"],),
}
PROFILE_TERMINALS = {
    "E1A": STAGES["E1A_SUCCESS"],
    "E1B": STAGES["E1B_SUCCESS"],
    "E2": STAGES["E2_SUCCESS"],
}

REQUEST_STRUCT = struct.Struct("<4sBBBBHBB16sI")
SLOT_BODY_STRUCT = struct.Struct("<BBBBH")

MODEL_CONTRACT = (
    b"MODEL-ONLY|S22PLUS-FYG8|P2.32|compact-ab-latest-stage-v1|"
    b"not-an-artifact-identity"
)


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


@dataclass(frozen=True)
class Slot:
    slot_id: int
    generation: int
    stage: int
    outcome: int
    item_index: int
    detail: int


def crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def model_run_id(profile: str) -> bytes:
    if profile not in PROFILE_NUMBERS:
        raise DesignError(f"unknown profile: {profile}")
    return hashlib.sha256(
        MODEL_CONTRACT + b"\0" + profile.encode("ascii")
    ).digest()[:16]


def _require_run_id(run_id: bytes) -> None:
    if len(run_id) != RUN_ID_SIZE or not any(run_id):
        raise DesignError("run ID must be one nonzero 128-bit value")


def _sequence(profile: str) -> tuple[int, ...]:
    try:
        return PROFILE_STAGE_SEQUENCES[profile]
    except KeyError as exc:
        raise DesignError(f"unknown profile: {profile}") from exc


def _stage_generation(profile: str, stage: int) -> int:
    try:
        return _sequence(profile).index(stage) + 1
    except ValueError as exc:
        raise DesignError(f"stage 0x{stage:02x} is not valid for {profile}") from exc


def _expected_item_index(stage: int) -> int:
    if STAGES["WDT_MODULE_0"] <= stage <= STAGES["WDT_MODULE_4"]:
        return stage - STAGES["WDT_MODULE_0"]
    if STAGES["E2_MODULE_0"] <= stage <= STAGES["E2_MODULE_58"]:
        return stage - STAGES["E2_MODULE_0"]
    if STAGES["E2_GATE_0"] <= stage <= STAGES["E2_GATE_7"]:
        return stage - STAGES["E2_GATE_0"]
    return 0


def _validate_stage_semantics(
    profile: str,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    _stage_generation(profile, stage)
    if not 0 <= detail <= 4095:
        raise DesignError("checkpoint detail is outside 0..4095")
    if item_index != _expected_item_index(stage):
        raise DesignError("checkpoint item index does not match its stage")
    terminal = PROFILE_TERMINALS[profile]
    if stage == terminal:
        if outcome != OUTCOME_SUCCESS or detail != 0:
            raise DesignError("profile terminal must be zero-detail success")
        return
    if outcome == OUTCOME_PROGRESS and detail == 0:
        return
    if outcome == OUTCOME_FAILURE and detail != 0:
        return
    raise DesignError("nonterminal outcome/detail combination is invalid")


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
    _validate_stage_semantics(profile, stage, outcome, item_index, detail)
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
        raise DesignError("checkpoint request size mismatch")
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
        raise DesignError("checkpoint request header mismatch")
    if crc32(data[:-4]) != recorded_crc:
        raise DesignError("checkpoint request CRC mismatch")
    profile = PROFILE_BY_NUMBER.get(profile_number)
    if profile is None:
        raise DesignError("checkpoint request profile is not allowlisted")
    _require_run_id(run_id)
    _validate_stage_semantics(profile, stage, outcome, item_index, detail)
    return Request(profile, stage, outcome, item_index, detail, run_id)


def _record_header(profile: str, run_id: bytes) -> bytes:
    _require_run_id(run_id)
    profile_number = PROFILE_NUMBERS.get(profile)
    if profile_number is None or profile_number > 0x0F:
        raise DesignError("record profile cannot fit the format/profile byte")
    header = LONG_FAMILY + bytes([(FORMAT_VERSION << 4) | profile_number]) + run_id
    if len(header) != LONG_HEADER_SIZE:
        raise DesignError("compact record header size changed")
    return header


def _slot_crc(header: bytes, slot_id: int, body: bytes) -> int:
    value = crc32(b"S22PLUS-FYG8-P232-SLOT-V1\0" + header + bytes([slot_id]) + body)
    if value == 0:
        raise DesignError("slot CRC zero is reserved for an uncommitted slot")
    return value


def _encode_slot(header: bytes, slot: Slot) -> bytes:
    if slot.slot_id not in {0, 1} or not 0 <= slot.generation <= 0xFF:
        raise DesignError("slot identity or generation is invalid")
    if (slot.generation & 1) != slot.slot_id:
        raise DesignError("slot generation parity does not match A/B identity")
    profile = PROFILE_BY_NUMBER[header[8] & 0x0F]
    if slot.generation == 0:
        if (
            slot.stage != STAGES["ENTRY"]
            or slot.outcome != OUTCOME_PROGRESS
            or slot.item_index != 0
            or slot.detail != 0
        ):
            raise DesignError("generation zero must be the kernel ENTRY state")
    else:
        _validate_stage_semantics(
            profile, slot.stage, slot.outcome, slot.item_index, slot.detail
        )
        if slot.generation != _stage_generation(profile, slot.stage):
            raise DesignError("slot generation does not match stage ordinal")
    body = SLOT_BODY_STRUCT.pack(
        slot.generation,
        slot.stage,
        slot.outcome,
        slot.item_index,
        slot.detail,
    )
    return body + struct.pack("<I", _slot_crc(header, slot.slot_id, body))


def _decode_slot(header: bytes, slot_id: int, raw: bytes) -> tuple[Slot | None, str]:
    if len(raw) != SLOT_SIZE:
        raise DesignError("compact slot size mismatch")
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
    generation, stage, outcome, item_index, detail = SLOT_BODY_STRUCT.unpack(body)
    slot = Slot(slot_id, generation, stage, outcome, item_index, detail)
    try:
        _encode_slot(header, slot)
    except DesignError:
        return None, "bad-body"
    return slot, "valid"


def _validate_record_families(record: bytes) -> None:
    if record.count(LONG_FAMILY) != 1:
        raise DesignError("long record contains a colliding long family")
    for family in (UNSAT_FAMILY, *LEGACY_FAMILIES):
        if family in record:
            raise DesignError("long record collides with another evidence family")


def initialize_record(profile: str, run_id: bytes) -> bytes:
    header = _record_header(profile, run_id)
    entry = _encode_slot(
        header,
        Slot(0, 0, STAGES["ENTRY"], OUTCOME_PROGRESS, 0, 0),
    )
    record = header + entry + bytes(SLOT_SIZE)
    if len(record) != LONG_RECORD_SIZE:
        raise DesignError("compact A/B record shape changed")
    _validate_record_families(record)
    decode_record(record, expected_profile=profile, expected_run_id=run_id)
    return record


def unsat_record(profile: str, run_id: bytes) -> bytes:
    header = _record_header(profile, run_id)
    tag = hashlib.sha256(b"S22PLUS-FYG8-P232-UNSAT-V1\0" + header).digest()[:16]
    record = UNSAT_FAMILY + tag
    if len(record) != UNSAT_SIZE:
        raise DesignError("UNSAT record size changed")
    if record.count(UNSAT_FAMILY) != 1 or any(
        family in record for family in (LONG_FAMILY, *LEGACY_FAMILIES)
    ):
        raise DesignError("UNSAT record collides with an evidence family")
    return record


def decode_record(
    record: bytes,
    *,
    expected_profile: str | None = None,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    if len(record) != LONG_RECORD_SIZE or not record.startswith(LONG_FAMILY):
        raise DesignError("compact record family or size mismatch")
    _validate_record_families(record)
    format_profile = record[8]
    if format_profile >> 4 != FORMAT_VERSION:
        raise DesignError("compact record format version mismatch")
    profile = PROFILE_BY_NUMBER.get(format_profile & 0x0F)
    if profile is None:
        raise DesignError("compact record profile is not allowlisted")
    run_id = record[9:25]
    _require_run_id(run_id)
    if expected_profile is not None and profile != expected_profile:
        raise DesignError("compact record profile mismatch")
    if expected_run_id is not None and run_id != expected_run_id:
        raise DesignError("compact record run ID mismatch")

    header = record[:LONG_HEADER_SIZE]
    valid: list[Slot] = []
    slot_status: list[str] = []
    for slot_id in range(SLOT_COUNT):
        start = LONG_HEADER_SIZE + slot_id * SLOT_SIZE
        slot, status = _decode_slot(header, slot_id, record[start : start + SLOT_SIZE])
        slot_status.append(status)
        if slot is not None:
            valid.append(slot)
    if not valid:
        raise DesignError("compact record has no valid committed slot")
    valid.sort(key=lambda slot: slot.generation)
    if len(valid) == 2:
        older, newer = valid
        if newer.generation != older.generation + 1:
            raise DesignError("A/B slot generations are not adjacent")
        if older.outcome != OUTCOME_PROGRESS:
            raise DesignError("checkpoint advanced after a terminal slot")
    active = valid[-1]
    terminal = active.outcome in {OUTCOME_SUCCESS, OUTCOME_FAILURE}
    return {
        "profile": profile,
        "run_id": run_id.hex(),
        "active": asdict(active),
        "valid_slots": [asdict(slot) for slot in valid],
        "slot_status": slot_status,
        "fallback_used": len(valid) == 1 and active.generation > 0,
        "terminal": terminal,
        "terminal_success": (
            active.outcome == OUTCOME_SUCCESS
            and active.stage == PROFILE_TERMINALS[profile]
        ),
    }


def apply_request(
    record: bytes, request_data: bytes, *, stop_after: str = "commit"
) -> bytes:
    if stop_after not in {"invalidate", "body", "commit"}:
        raise DesignError("unknown modeled write stop point")
    decoded = decode_record(record)
    request = decode_request(request_data)
    if decoded["terminal"]:
        raise DesignError("checkpoint record is already terminal")
    if (
        request.profile != decoded["profile"]
        or request.run_id.hex() != decoded["run_id"]
    ):
        raise DesignError("checkpoint request changes the record identity")
    active = Slot(**decoded["active"])
    sequence = _sequence(request.profile)
    if (
        active.generation >= len(sequence)
        or request.stage != sequence[active.generation]
    ):
        raise DesignError("checkpoint request is not the exact next stage")

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
    updated[start : start + SLOT_BODY_STRUCT.size] = encoded[:SLOT_BODY_STRUCT.size]
    if stop_after == "body":
        return bytes(updated)
    updated[start + SLOT_BODY_STRUCT.size : start + SLOT_SIZE] = encoded[
        SLOT_BODY_STRUCT.size :
    ]
    final = bytes(updated)
    _validate_record_families(final)
    checked = decode_record(
        final, expected_profile=request.profile, expected_run_id=request.run_id
    )
    if checked["active"]["generation"] != next_slot.generation:
        raise DesignError("committed checkpoint did not become active")
    return final


def _edge_family_partial(payload: bytes, families: tuple[bytes, ...]) -> bool:
    for family in families:
        for length in range(4, len(family)):
            if (
                not payload.startswith(family)
                and payload.startswith(family[-length:])
            ) or (
                not payload.endswith(family)
                and payload.endswith(family[:length])
            ):
                return True
    return False


def _family_positions(payload: bytes, family: bytes) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        position = payload.find(family, start)
        if position < 0:
            return positions
        positions.append(position)
        start = position + 1


def classify_observation(
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
        raise DesignError("baseline is not clean for all related evidence families")

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
    entry_count = sum(record["active"]["generation"] == 0 for record in records)

    if integrity_issues:
        classification = "AMBIGUOUS_INTEGRITY_FAILURE"
        accepted = False
    elif success_count:
        classification = f"{expected_profile}_SUCCESS_ONE_OR_MORE_BOOTS"
        accepted = True
    elif failure_count:
        classification = f"{expected_profile}_FAILURE_OBSERVED"
        accepted = False
    elif progress_count:
        classification = f"{expected_profile}_PROGRESS_OBSERVED"
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


def simulate_initial_visibility(
    profile: str,
    run_id: bytes,
    *,
    idx: int,
    payload_size: int = 128,
    magic: int = retained.LOG_MAGIC,
    selected: bool = True,
) -> dict[str, Any]:
    header = retained.Header(boot_cnt=7, magic=magic, idx=idx, prev_idx=3)
    if not selected or magic != retained.LOG_MAGIC or idx < UNSAT_SIZE:
        proof = b""
        state = "NONE"
    elif idx < LONG_RECORD_SIZE:
        proof = unsat_record(profile, run_id)
        state = "UNSAT"
    else:
        proof = initialize_record(profile, run_id)
        state = "ENTRY"
    payload = b"\xa5" * payload_size
    if proof:
        payload, _ = retained.place_precursor(payload, idx, proof)
    snapshot = retained.stock_snapshot(payload, header)
    result = classify_observation(
        b"",
        snapshot.data,
        expected_profile=profile,
        expected_run_id=run_id,
    )
    return {
        "idx": idx,
        "selected_state": state,
        "snapshot_branch": snapshot.branch,
        "snapshot_size": len(snapshot.data),
        **result,
    }


def _complete_profile(profile: str, run_id: bytes) -> bytes:
    record = initialize_record(profile, run_id)
    for stage in _sequence(profile):
        terminal = stage == PROFILE_TERMINALS[profile]
        request = encode_request(
            profile,
            stage,
            run_id=run_id,
            outcome=OUTCOME_SUCCESS if terminal else OUTCOME_PROGRESS,
            item_index=_expected_item_index(stage),
        )
        record = apply_request(record, request)
    return record


def build_result() -> dict[str, Any]:
    profile_results: dict[str, Any] = {}
    for profile in PROFILE_NUMBERS:
        run_id = model_run_id(profile)
        final = _complete_profile(profile, run_id)
        decoded = decode_record(
            final, expected_profile=profile, expected_run_id=run_id
        )
        if not decoded["terminal_success"]:
            raise DesignError(f"{profile} did not reach modeled terminal success")
        profile_results[profile] = {
            "stage_count": len(_sequence(profile)),
            "terminal_stage": PROFILE_TERMINALS[profile],
            "active": decoded["active"],
        }

    run_id = model_run_id("E1A")
    first = apply_request(
        initialize_record("E1A", run_id),
        encode_request("E1A", STAGES["PROC_MOUNTED"], run_id=run_id),
    )
    second_request = encode_request("E1A", STAGES["SYS_MOUNTED"], run_id=run_id)
    torn = {
        phase: decode_record(
            apply_request(first, second_request, stop_after=phase),
            expected_profile="E1A",
            expected_run_id=run_id,
        )["active"]
        for phase in ("invalidate", "body")
    }
    if any(active["stage"] != STAGES["PROC_MOUNTED"] for active in torn.values()):
        raise DesignError("torn update did not preserve the prior valid stage")

    success = _complete_profile("E1A", run_id)
    multiboot = classify_observation(
        b"clean",
        initialize_record("E1A", run_id) + b"gap" + success,
        expected_profile="E1A",
        expected_run_id=run_id,
    )
    if not multiboot["accepted"] or multiboot["success_count"] != 1:
        raise DesignError("valid multiboot success was not accepted")

    boundary_indices = (0, 23, 24, 44, 45, 127, 128, 129, 511)
    boundary = [
        simulate_initial_visibility("E1A", run_id, idx=idx)
        for idx in boundary_indices
    ]
    expected = {
        idx: (
            "ZERO_AMBIGUOUS"
            if idx < UNSAT_SIZE
            else "UNSAT_VALID_MAGIC_ONE_OR_MORE_BOOTS"
            if idx < LONG_RECORD_SIZE
            else "ENTRY_ONLY_ONE_OR_MORE_BOOTS"
        )
        for idx in boundary_indices
    }
    if any(row["classification"] != expected[row["idx"]] for row in boundary):
        raise DesignError("initial visibility boundary matrix failed")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "host_only": True,
        "record_layout": {
            "long_family_bytes": len(LONG_FAMILY),
            "format_profile_bytes": 1,
            "run_id_bytes": RUN_ID_SIZE,
            "slot_count": SLOT_COUNT,
            "slot_bytes": SLOT_SIZE,
            "slot_body_bytes": SLOT_BODY_STRUCT.size,
            "slot_crc_bytes": 4,
            "long_record_bytes": LONG_RECORD_SIZE,
            "unsat_record_bytes": UNSAT_SIZE,
            "binding_bits": RUN_ID_SIZE * 8,
        },
        "profiles": profile_results,
        "torn_update_fallback": torn,
        "multiboot_acceptance": {
            key: multiboot[key]
            for key in (
                "classification",
                "accepted",
                "long_record_count",
                "success_count",
                "minimum_candidate_boots",
            )
        },
        "boundary_matrix": boundary,
        "safety": {
            "candidate_artifact_created": False,
            "image_built": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
        "next": "kernel/userspace/decoder static implementation only",
    }


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


def main() -> int:
    parse_args()
    print(json.dumps(build_result(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
