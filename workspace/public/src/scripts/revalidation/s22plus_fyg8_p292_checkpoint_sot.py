#!/usr/bin/env python3
"""P2.92 checkpoint source of truth, phase 1 P2.90 zero-delta form."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

import s22plus_fyg8_p290_contract_spec as legacy_spec
import s22plus_fyg8_p290_latest_stage_model as legacy_model


SCHEMA = "s22plus_fyg8_p292_checkpoint_sot_v1"
PHASE = "p290-zero-delta"
PROFILE = "E2"
PROFILE_NUMBER = 3
LONG_FAMILY = b"S22E1L1|"
UNSAT_FAMILY = b"S22E1U1|"
LEGACY_FAMILIES = (b"[[S22P1U|", b"S22UNS1|")
CRC_DOMAIN = b"S22PLUS-FYG8-P232-SLOT-V1\x00"
REQUEST_MAGIC = b"S22Q"
REQUEST_VERSION = 2
FORMAT_VERSION = 1
OUTCOME_PROGRESS = 0
OUTCOME_SUCCESS = 1
OUTCOME_FAILURE = 2
LONG_RECORD_SIZE = 45
LONG_HEADER_SIZE = 25
SLOT_SIZE = 10
SLOT_COUNT = 2
REQUEST_SIZE = 32
RUN_ID_SIZE = 16
TERMINAL_GENERATION = 107
TERMINAL_POSITION = (0x93, 0)
STATE_REPRESENTATION = "p290-field-subset-without-outcome-detail"
RUNTIME_ERRNO_POLICY = "publication-error-discarded-before-quiet-park"
PUBLICATION_OPERATIONS = ("openat", "write", "close")


class SotError(ValueError):
    pass


@dataclass(frozen=True)
class Field:
    name: str
    offset: int
    size: int


@dataclass(frozen=True)
class Position:
    name: str
    stage: int
    item_index: int
    kind: int
    gate_index: int | None


SLOT_FIELDS = (
    Field("generation", 0, 1),
    Field("stage", 1, 1),
    Field("outcome", 2, 1),
    Field("item_index", 3, 1),
    Field("detail", 4, 2),
    Field("commit_crc", 6, 4),
)
REQUEST_FIELDS = (
    Field("magic", 0, 4),
    Field("version", 4, 1),
    Field("profile", 5, 1),
    Field("stage", 6, 1),
    Field("outcome", 7, 1),
    Field("detail", 8, 2),
    Field("item_index", 10, 1),
    Field("reserved", 11, 1),
    Field("run_id", 12, 16),
    Field("crc32", 28, 4),
)
ACTIVE_STATE_FIELDS = (
    "ready",
    "terminal",
    "active_slot",
    "profile",
    "generation",
    "stage",
    "item_index",
    "seed_idx",
    "seed_boot_cnt",
    "proof_pos",
    "header",
)
POSITIONS = tuple(
    Position(
        position.name,
        position.stage,
        position.item_index,
        position.kind,
        position.gate_index,
    )
    for position in legacy_spec.POSITIONS
)
EXACT_DETAIL_RULES = tuple(legacy_spec.exact_detail_rules())


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "phase": PHASE,
        "profile": PROFILE,
        "profile_number": PROFILE_NUMBER,
        "families": {
            "long": LONG_FAMILY.decode("ascii"),
            "unsat": UNSAT_FAMILY.decode("ascii"),
            "legacy": [value.decode("ascii") for value in LEGACY_FAMILIES],
        },
        "format_version": FORMAT_VERSION,
        "crc_domain_hex": CRC_DOMAIN.hex(),
        "record": {
            "size": LONG_RECORD_SIZE,
            "header_size": LONG_HEADER_SIZE,
            "slot_size": SLOT_SIZE,
            "slot_count": SLOT_COUNT,
            "slot_fields": [asdict(field) for field in SLOT_FIELDS],
        },
        "request": {
            "magic": REQUEST_MAGIC.decode("ascii"),
            "version": REQUEST_VERSION,
            "size": REQUEST_SIZE,
            "run_id_size": RUN_ID_SIZE,
            "fields": [asdict(field) for field in REQUEST_FIELDS],
        },
        "outcomes": {
            "progress": OUTCOME_PROGRESS,
            "success": OUTCOME_SUCCESS,
            "failure": OUTCOME_FAILURE,
        },
        "positions": [asdict(position) for position in POSITIONS],
        "terminal_generation": TERMINAL_GENERATION,
        "terminal_position": list(TERMINAL_POSITION),
        "exact_detail_rules": [list(rule) for rule in EXACT_DETAIL_RULES],
        "active_state": {
            "representation": STATE_REPRESENTATION,
            "fields": list(ACTIVE_STATE_FIELDS),
        },
        "publication": {
            "operations": list(PUBLICATION_OPERATIONS),
            "runtime_errno_policy": RUNTIME_ERRNO_POLICY,
        },
    }


def descriptor_sha256() -> str:
    return hashlib.sha256(_canonical(descriptor())).hexdigest()


def validate() -> dict[str, Any]:
    legacy_spec.validate()
    position_pairs = tuple(
        (position.stage, position.item_index) for position in POSITIONS
    )
    checks = {
        "profile": legacy_model.PROFILE == PROFILE,
        "profile_number": (
            legacy_model.PROFILE_NUMBERS[PROFILE] == PROFILE_NUMBER
        ),
        "long_family": legacy_model.LONG_FAMILY == LONG_FAMILY,
        "unsat_family": legacy_model.UNSAT_FAMILY == UNSAT_FAMILY,
        "legacy_families": legacy_model.LEGACY_FAMILIES == LEGACY_FAMILIES,
        "format_version": legacy_model.FORMAT_VERSION == FORMAT_VERSION,
        "request_version": legacy_model.REQUEST_VERSION == REQUEST_VERSION,
        "record_size": legacy_model.LONG_RECORD_SIZE == LONG_RECORD_SIZE,
        "header_size": legacy_model.LONG_HEADER_SIZE == LONG_HEADER_SIZE,
        "slot_size": legacy_model.SLOT_SIZE == SLOT_SIZE,
        "slot_count": legacy_model.SLOT_COUNT == SLOT_COUNT,
        "request_size": legacy_model.REQUEST_STRUCT.size == REQUEST_SIZE,
        "request_format": (
            legacy_model.REQUEST_STRUCT.format == "<4sBBBBHBB16sI"
        ),
        "slot_format": legacy_model.SLOT_BODY_STRUCT.format == "<BBBBH",
        "outcomes": (
            legacy_model.OUTCOME_PROGRESS,
            legacy_model.OUTCOME_SUCCESS,
            legacy_model.OUTCOME_FAILURE,
        )
        == (OUTCOME_PROGRESS, OUTCOME_SUCCESS, OUTCOME_FAILURE),
        "positions": position_pairs == legacy_spec.POSITION_SEQUENCE,
        "terminal_generation": (
            legacy_spec.TERMINAL_GENERATION == TERMINAL_GENERATION
        ),
        "terminal_position": legacy_spec.TERMINAL_POSITION == TERMINAL_POSITION,
        "detail_rules": EXACT_DETAIL_RULES == legacy_spec.exact_detail_rules(),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise SotError(f"P2.92 phase-1 SoT mismatch: {failed}")
    if len(POSITIONS) != TERMINAL_GENERATION:
        raise SotError("P2.92 phase-1 position count drifted")
    if len(set(position_pairs)) != len(position_pairs):
        raise SotError("P2.92 phase-1 position pairs are not unique")
    if SLOT_FIELDS[-1].offset + SLOT_FIELDS[-1].size != SLOT_SIZE:
        raise SotError("P2.92 slot field geometry is incomplete")
    if REQUEST_FIELDS[-1].offset + REQUEST_FIELDS[-1].size != REQUEST_SIZE:
        raise SotError("P2.92 request field geometry is incomplete")
    return {
        "schema": SCHEMA,
        "phase": PHASE,
        "descriptor_sha256": descriptor_sha256(),
        "position_count": len(POSITIONS),
        "exact_detail_rule_count": len(EXACT_DETAIL_RULES),
        "state_representation": STATE_REPRESENTATION,
        "runtime_errno_policy": RUNTIME_ERRNO_POLICY,
        "legacy_contract_checks": len(checks),
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
