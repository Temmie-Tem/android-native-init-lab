#!/usr/bin/env python3
"""Additively decode the consumed P3.19 early Carrier, host-only.

The frozen Process-v2 result remains authoritative.  This helper only separates
Carrier byte integrity from the legacy semantic allowlist and prints a bounded
H0 interpretation of the exact retained reads.  It has no device or write path.
"""

from __future__ import annotations

import hashlib
import json
import stat
import struct
from pathlib import Path
from typing import Any

import s22plus_fyg8_p310_carrier_model as carrier


ROOT = Path(__file__).resolve().parents[5]
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-08-30T082903022444Z-1788078543022472744"
)
LIVE_RESULT = RUN_DIR / "live-result.json"
RETAINED = (
    RUN_DIR / "rollback-observer-1.bin",
    RUN_DIR / "rollback-observer-2.bin",
)

SCHEMA = "s22plus_fyg8_p319_postlive_decoder_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
FORMAL_VERDICT = "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
FORMAL_OBSERVER_PROOF = "NO_PROOF_OBSERVER"
LIVE_RESULT_SIZE = 10_081
LIVE_RESULT_SHA256 = "722391efa3305d6857bdcaab12e213439ff70b6264c73b217e437a146839e4b9"
RETAINED_SIZE = 2_097_136
RETAINED_SHA256 = "430508c7a6d95e477ff2b4a8ba1ce0007663274ba7409c4f1403218e7abd27e0"
EXPECTED_RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")

FIRST_GENERATION = 10
FIRST_STAGE = 0x41
FIRST_ITEM = 1
FAILURE_GENERATION = 11
FAILURE_STAGE = 0x42
FAILURE_ITEM = 2
FAILURE_DETAIL = 0x6020


class DecodeError(ValueError):
    """The exact retained evidence or Carrier structure differs."""


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bound(path: Path, *, size: int, digest: str, label: str) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise DecodeError(f"{label} is not a direct regular file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise DecodeError(f"{label} is unavailable") from exc
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
    )
    if (
        identity(before) != identity(after)
        or len(payload) != size
        or sha256(payload) != digest
    ):
        raise DecodeError(f"{label} identity differs")
    return payload


def _decode_slot(header: bytes, slot_id: int, raw: bytes) -> dict[str, Any]:
    if len(raw) != carrier.SLOT_SIZE:
        raise DecodeError("Carrier slot size differs")
    body, recorded_raw = raw[:-4], raw[-4:]
    recorded_crc = struct.unpack("<I", recorded_raw)[0]
    if recorded_crc == 0:
        raise DecodeError("Carrier slot is uncommitted")
    try:
        calculated_crc = carrier._slot_crc(header, slot_id, body)  # noqa: SLF001
    except carrier.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    if recorded_crc != calculated_crc:
        raise DecodeError("Carrier slot CRC differs")

    generation, stage, outcome, item, kind, length, reserved, detail, padded = (
        carrier.SLOT_BODY_STRUCT.unpack(body)
    )
    if (
        reserved != 0
        or length > carrier.REQUEST_PAYLOAD_SIZE
        or any(padded[length:])
        or (generation & 1) != slot_id
    ):
        raise DecodeError("Carrier slot structural body differs")
    payload = padded[:length]
    try:
        carrier._validate_payload(kind, payload)  # noqa: SLF001
    except carrier.DesignError as exc:
        raise DecodeError("Carrier slot payload structure differs") from exc

    legacy_status = "valid"
    legacy_error = None
    try:
        carrier.spec.validate_slot(
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item,
            detail=detail,
        )
    except carrier.spec.SpecError as exc:
        legacy_status = "semantic-out-of-domain"
        legacy_error = str(exc)

    return {
        "slot_id": slot_id,
        "structural_status": "valid",
        "recorded_crc": f"0x{recorded_crc:08x}",
        "calculated_crc": f"0x{calculated_crc:08x}",
        "generation": generation,
        "stage": f"0x{stage:02x}",
        "outcome": outcome,
        "item_index": item,
        "detail": f"0x{detail:04x}",
        "payload_kind": kind,
        "payload_length": length,
        "legacy_semantic_status": legacy_status,
        "legacy_semantic_error": legacy_error,
    }


def decode_carrier(
    record: bytes,
    *,
    expected_profile: str = "E2",
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    """Decode structural slots without accepting them as a formal result."""
    if len(record) != carrier.LONG_RECORD_SIZE:
        raise DecodeError("Carrier record size differs")
    header = record[: carrier.LONG_HEADER_SIZE]
    try:
        profile, run_id = carrier._decode_header(  # noqa: SLF001
            header, expected_profile, expected_run_id
        )
    except carrier.DesignError as exc:
        raise DecodeError(str(exc)) from exc

    slots = []
    for slot_id in range(carrier.SLOT_COUNT):
        start = carrier.LONG_HEADER_SIZE + slot_id * carrier.SLOT_SIZE
        slots.append(_decode_slot(header, slot_id, record[start : start + carrier.SLOT_SIZE]))
    if (
        slots[1]["generation"] != slots[0]["generation"] + 1
        or slots[0]["outcome"] != carrier.OUTCOME_PROGRESS
    ):
        raise DecodeError("Carrier committed generations differ")

    exact_incident = (
        slots[0]["generation"] == FIRST_GENERATION
        and slots[0]["stage"] == f"0x{FIRST_STAGE:02x}"
        and slots[0]["outcome"] == carrier.OUTCOME_PROGRESS
        and slots[0]["item_index"] == FIRST_ITEM
        and slots[0]["detail"] == "0x0000"
        and slots[1]["generation"] == FAILURE_GENERATION
        and slots[1]["stage"] == f"0x{FAILURE_STAGE:02x}"
        and slots[1]["outcome"] == carrier.OUTCOME_FAILURE
        and slots[1]["item_index"] == FAILURE_ITEM
        and slots[1]["detail"] == f"0x{FAILURE_DETAIL:04x}"
    )
    return {
        "profile": profile,
        "run_id_sha256": sha256(run_id),
        "header_crc_valid": True,
        "slots": slots,
        "exact_p319_early_incident": exact_incident,
        "formal_acceptance": False,
    }


def _find_exact_carrier(payload: bytes) -> tuple[int, dict[str, Any]]:
    matches: list[tuple[int, dict[str, Any]]] = []
    start = 0
    while True:
        offset = payload.find(carrier.LONG_FAMILY, start)
        if offset < 0:
            break
        record = payload[offset : offset + carrier.LONG_RECORD_SIZE]
        if len(record) == carrier.LONG_RECORD_SIZE:
            try:
                decoded = decode_carrier(
                    record,
                    expected_profile="E2",
                    expected_run_id=EXPECTED_RUN_ID,
                )
            except DecodeError:
                pass
            else:
                if decoded["exact_p319_early_incident"]:
                    matches.append((offset, decoded))
        start = offset + 1
    if len(matches) != 1:
        raise DecodeError("retained evidence lacks one exact P3.19 early Carrier")
    return matches[0]


def _formal_result(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DecodeError("formal live result is not JSON") from exc
    try:
        observer = value["live_state"]["final_evidence"]["observer"]
        valid = (
            value["current_state"] == "CLOSED"
            and value["verdict"] == FORMAL_VERDICT
            and value["live_state"]["p319_proof_class"] == FORMAL_OBSERVER_PROOF
            and value["live_state"]["candidate_completed"] is True
            and value["live_state"]["rollback_completed"] is True
            and value["live_state"]["final_verified"] is True
            and observer["byte_identical"] is True
            and observer["bytes"] == RETAINED_SIZE
            and observer["sha256"] == RETAINED_SHA256
        )
    except (KeyError, TypeError) as exc:
        raise DecodeError("formal live result shape differs") from exc
    if not valid:
        raise DecodeError("formal live result semantics differ")
    return {
        "current_state": "CLOSED",
        "verdict": FORMAL_VERDICT,
        "observer_proof_class": FORMAL_OBSERVER_PROOF,
        "candidate_completed": True,
        "rollback_completed": True,
        "final_verified": True,
        "unchanged_by_this_decoder": True,
    }


def build_actual_result() -> dict[str, Any]:
    live_payload = _read_bound(
        LIVE_RESULT,
        size=LIVE_RESULT_SIZE,
        digest=LIVE_RESULT_SHA256,
        label="formal live result",
    )
    retained = [
        _read_bound(path, size=RETAINED_SIZE, digest=RETAINED_SHA256, label=path.name)
        for path in RETAINED
    ]
    if retained[0] != retained[1]:
        raise DecodeError("retained reads are not byte-identical")
    offset, decoded = _find_exact_carrier(retained[0])
    if decoded["slots"][1]["legacy_semantic_status"] != "semantic-out-of-domain":
        raise DecodeError("legacy semantic incident was not reproduced")

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "scope": {
            "host_only": True,
            "device_contact": False,
            "device_actions": False,
            "writes_evidence": False,
            "live_authority_created": False,
            "replay_authority_created": False,
        },
        "inputs": {
            "live_result": {"size": len(live_payload), "sha256": sha256(live_payload)},
            "retained_reads": {
                "count": 2,
                "byte_identical": True,
                "size_each": RETAINED_SIZE,
                "sha256": RETAINED_SHA256,
            },
        },
        "formal_result": _formal_result(live_payload),
        "carrier_offset": offset,
        "structural_decode": decoded,
        "additive_h0_interpretation": {
            "evidence_class": "SUPPORTED",
            "classification": "P319_EARLY_OBSERVER_CONTRACT_FAILURE_SUPPORTED",
            "last_proved_direct_module": {"index": 1, "name": "qcom_hwspinlock.ko"},
            "next_checkpoint": {"index": 2, "name": "smem.ko"},
            "smem_attempted_or_loaded": "UNKNOWN",
            "usb_stack_execution_claim_allowed": False,
            "detail": {
                "value": "0x6020",
                "candidate_name": "witness-grammar-contradiction",
                "publication_close_errno_alias": 32,
                "unique_root_cause": False,
                "body_shape_subclass": "UNKNOWN",
            },
        },
    }


def main() -> int:
    print(json.dumps(build_actual_result(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
