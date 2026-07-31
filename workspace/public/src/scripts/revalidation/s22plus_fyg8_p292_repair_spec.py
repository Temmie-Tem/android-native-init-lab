#!/usr/bin/env python3
"""P2.92 phase-2 exact-slot and publication-errno contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

import s22plus_fyg8_p292_checkpoint_sot as phase1


SCHEMA = "s22plus_fyg8_p292_repair_spec_v1"
PHASE = "exact-active-slot-and-errno-repair"
PROFILE = phase1.PROFILE
OUTCOME_FAILURE = phase1.OUTCOME_FAILURE
ERRNO_MAX = 0xFFF
OPERATION_NONE = 0
OPERATION_OPEN = 1
OPERATION_WRITE = 2
OPERATION_CLOSE = 3
OPERATION_BASES = {
    OPERATION_OPEN: 0x4000,
    OPERATION_WRITE: 0x5000,
    OPERATION_CLOSE: 0x6000,
}
ACTIVE_STATE_REPRESENTATION = "exact-committed-active-slot"
ACTIVE_STATE_FIELDS = (
    "ready",
    "terminal",
    "active_slot",
    "profile",
    "active",
    "seed_idx",
    "seed_boot_cnt",
    "proof_pos",
    "header",
)
RUNTIME_ERRNO_POLICY = (
    "exact-open-write-close-errno-with-operation-aware-fallback"
)
REPAIR_ARTIFACT_KEYS = frozenset(
    {
        "candidate_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "p290_e3_runtime_include",
        "p290_checkpoint_header",
    }
)


class RepairSpecError(ValueError):
    pass


@dataclass(frozen=True)
class PublicationOperation:
    name: str
    value: int
    detail_base: int


PUBLICATION_OPERATIONS = (
    PublicationOperation("openat", OPERATION_OPEN, OPERATION_BASES[OPERATION_OPEN]),
    PublicationOperation("write", OPERATION_WRITE, OPERATION_BASES[OPERATION_WRITE]),
    PublicationOperation("close", OPERATION_CLOSE, OPERATION_BASES[OPERATION_CLOSE]),
)


def encode_publication_error(operation: int, error: int) -> int:
    if operation not in OPERATION_BASES:
        raise RepairSpecError("publication operation is invalid")
    if error >= 0 or error < -ERRNO_MAX:
        raise RepairSpecError("publication errno is outside Linux errno range")
    return OPERATION_BASES[operation] + (-error)


def decode_publication_error(detail: int) -> tuple[int, int]:
    if isinstance(detail, bool) or not isinstance(detail, int):
        raise RepairSpecError("publication detail is not an integer")
    for operation, base in OPERATION_BASES.items():
        if base < detail <= base + ERRNO_MAX:
            return operation, -(detail - base)
    raise RepairSpecError("detail is not a publication-error detail")


def is_publication_error_detail(outcome: int, detail: int) -> bool:
    if outcome != OUTCOME_FAILURE:
        return False
    try:
        decode_publication_error(detail)
    except RepairSpecError:
        return False
    return True


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "phase": PHASE,
        "phase1_descriptor_sha256": phase1.descriptor_sha256(),
        "profile": PROFILE,
        "record": phase1.descriptor()["record"],
        "request": phase1.descriptor()["request"],
        "positions": phase1.descriptor()["positions"],
        "terminal_generation": phase1.TERMINAL_GENERATION,
        "terminal_position": list(phase1.TERMINAL_POSITION),
        "active_state": {
            "representation": ACTIVE_STATE_REPRESENTATION,
            "fields": list(ACTIVE_STATE_FIELDS),
            "exact_slot_includes_commit_crc": True,
            "seed_update_required": True,
            "every_successful_commit_update_required": True,
        },
        "publication_errno": {
            "errno_max": ERRNO_MAX,
            "operation_none": OPERATION_NONE,
            "operations": [
                asdict(operation) for operation in PUBLICATION_OPERATIONS
            ],
            "runtime_policy": RUNTIME_ERRNO_POLICY,
            "fallback_outcome": OUTCOME_FAILURE,
            "fallback_detail_is_operation_and_exact_errno": True,
            "total_channel_failure_volatile_evidence_required": True,
        },
        "repair_artifact_keys": sorted(REPAIR_ARTIFACT_KEYS),
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def descriptor_sha256() -> str:
    return hashlib.sha256(_canonical(descriptor())).hexdigest()


def validate() -> dict[str, Any]:
    phase1_result = phase1.validate()
    if not phase1_result["verified"]:
        raise RepairSpecError("phase-1 checkpoint SoT did not validate")
    ranges = tuple(
        (operation.detail_base + 1, operation.detail_base + ERRNO_MAX)
        for operation in PUBLICATION_OPERATIONS
    )
    if any(
        left[0] <= right[1] and right[0] <= left[1]
        for index, left in enumerate(ranges)
        for right in ranges[index + 1 :]
    ):
        raise RepairSpecError("publication-error detail ranges overlap")
    for operation in PUBLICATION_OPERATIONS:
        for error in (-1, -5, -116, -ERRNO_MAX):
            detail = encode_publication_error(operation.value, error)
            if decode_publication_error(detail) != (operation.value, error):
                raise RepairSpecError("publication-error detail round trip failed")
    if (
        phase1.LONG_RECORD_SIZE != 45
        or phase1.SLOT_COUNT != 2
        or phase1.TERMINAL_GENERATION != 107
        or len(REPAIR_ARTIFACT_KEYS) != 5
    ):
        raise RepairSpecError("repair scope or retained ABI drifted")
    return {
        "schema": SCHEMA,
        "phase": PHASE,
        "descriptor_sha256": descriptor_sha256(),
        "phase1_descriptor_sha256": phase1.descriptor_sha256(),
        "position_count": len(phase1.POSITIONS),
        "repair_artifact_count": len(REPAIR_ARTIFACT_KEYS),
        "active_state_representation": ACTIVE_STATE_REPRESENTATION,
        "runtime_errno_policy": RUNTIME_ERRNO_POLICY,
        "publication_error_ranges": [list(value) for value in ranges],
        "retained_record_size": phase1.LONG_RECORD_SIZE,
        "retained_slot_count": phase1.SLOT_COUNT,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
