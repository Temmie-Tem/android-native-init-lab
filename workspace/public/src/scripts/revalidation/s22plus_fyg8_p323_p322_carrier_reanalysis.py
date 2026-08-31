#!/usr/bin/env python3
"""Reclassify the retained P3.22 Carrier record with its actual P3.13 ABI.

The frozen P3.22 adapter delegated slot semantics to the older P3.10/P3.08
model.  That model checks CRC correctly but rejects a P3.13 intermediate
contradiction as ``bad-body``.  This host-only reducer uses the existing P3.13
post-live decoder and recognizes only the exact P3.22 transition that was
retained after the consumed run:

``generation 92 progress -> generation 93 failure 0x6726``.

It distinguishes a valid stock-encoder failure receipt from byte corruption.
It cannot identify which internal encoder predicate rejected the witness and
does not promote the Max77705 experiment to success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p313_postlive_decoder as decoder  # noqa: E402


SCHEMA = "s22plus_fyg8_p323_p322_carrier_reanalysis_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
PROFILE = "E2"
EXPECTED_PRIOR = {
    "slot_id": 0,
    "generation": 92,
    "stage": 0x8F,
    "outcome": 0,
    "item_index": 4,
    "detail": 0,
    "payload_kind": 0,
}
EXPECTED_ACTIVE = {
    "slot_id": 1,
    "generation": 93,
    "stage": 0x90,
    "outcome": 2,
    "item_index": 0,
    "detail": 0x6726,
    "payload_kind": 0,
}


class ReanalysisError(ValueError):
    """The retained bytes are not the one exact P3.22 failure shape."""


def identity(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes:
        raise ReanalysisError("observer payload must be bytes")
    return {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _matches(row: object, expected: dict[str, int]) -> bool:
    return type(row) is dict and all(type(row.get(key)) is int and row[key] == value for key, value in expected.items())


def _empty_payload(value: object) -> bool:
    return value == b"" or value == {"encoding": "hex", "value": ""}


def reanalyze(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise ReanalysisError("observer payload must be nonempty bytes")
    try:
        classified = decoder.classify_observation(
            value,
            expected_profile=PROFILE,
            expected_run_id=P322_RUN_ID,
        )
    except Exception as exc:
        raise ReanalysisError("P3.22 Carrier bytes do not decode under P3.13 semantics") from exc
    records = classified.get("records")
    if (
        classified.get("classification") != "P313_OBSERVER_CONTRADICTION"
        or classified.get("accepted") is not False
        or classified.get("integrity_issue") is not False
        or classified.get("integrity_issues") != []
        or classified.get("long_record_count") != 1
        or classified.get("exact_record_count") != 1
        or classified.get("foreign_count") != 0
        or classified.get("contradiction_count") != 1
        or type(records) is not list
        or len(records) != 1
    ):
        raise ReanalysisError("P3.22 Carrier classification shape differs")
    record = records[0]
    slots = record.get("valid_slots")
    if (
        record.get("slot_status") != ["valid", "valid"]
        or type(slots) is not list
        or len(slots) != 2
        or not _matches(slots[0], EXPECTED_PRIOR)
        or not _matches(slots[1], EXPECTED_ACTIVE)
        or not _empty_payload(slots[0].get("payload"))
        or not _empty_payload(slots[1].get("payload"))
    ):
        raise ReanalysisError("P3.22 committed slot transition differs")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "run_id": P322_RUN_ID_HEX,
        "classification": "P322_VALID_INTERMEDIATE_STOCK_ENCODER_FAILURE",
        "raw_observer": identity(value),
        "carrier_record_offset": record["observer_offset"],
        "slot_status": ["valid", "valid"],
        "prior": {**EXPECTED_PRIOR, "payload_size": 0},
        "active": {**EXPECTED_ACTIVE, "payload_size": 0},
        "carrier_crc_valid": True,
        "observer_byte_corruption": False,
        "stock_encoder_failed_before_bridge": True,
        "exact_encoder_predicate": "UNKNOWN_NOT_RETAINED",
        "candidate_native_arrival_supported": True,
        "max77705_scientific_result": "NOT_PRODUCED",
        "candidate_success_promoted": False,
        "device_contact": False,
        "live_authority_created": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = args.input.read_bytes()
        result = reanalyze(payload)
    except (OSError, ReanalysisError) as exc:
        print(json.dumps({"schema": SCHEMA, "classification": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
