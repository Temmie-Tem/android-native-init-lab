#!/usr/bin/env python3
"""P3.19 stock-witness Process-v2 adapter.

The outer record is the reviewed P310 Carrier-v2 record.  Only the two
positions introduced by the P3.19 stock runtime are new: generations 106 and
107 (positions 105 and 106) carry the two halves of an MXD5 stock envelope.
This module classifies the full retained Carrier byte string, not a
stand-alone envelope.  It does not import or call the P3.18 diagnostic
decoder.  ACM remains supplemental and never gates the stock result.
"""

from __future__ import annotations

import binascii
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
from typing import Any

import s22plus_fyg8_p308_telemetry_spec as spec
import s22plus_fyg8_p310_carrier_model as carrier


SCHEMA = "s22plus_fyg8_p319_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p319-stock-witness-carrier-v1"
PARENT_SOURCE_CONTRACT_ID = "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
PROFILE = spec.PROFILE
DECODER_ID = "s22plus_fyg8_p319_stock_witness_carrier_v1"
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P319_STOCK_WITNESS_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=3|"
    "status_width=3|chain=irq,status,class,probe|parent=unavailable|"
    "w5=unavailable|acm=supplemental"
)
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
LONG_FAMILY = carrier.LONG_FAMILY
UNSAT_FAMILY = carrier.UNSAT_FAMILY
ENVELOPE_MAGIC = b"MXD5"
ENVELOPE_VERSION = 5
ENVELOPE_SIZE = 128
CRC_DOMAIN = b"S22PLUS-FYG8-MAX77705-STOCK-V1\0"
CRC_OFFSET = 124
PAYLOAD_OFFSET = 48
PAYLOAD_SIZE = 76
ENCODING = 4
PAYLOAD_ABI = 3
STATUS_WIDTH = 3
CHAIN = ("irq", "initial_status", "classification", "probe")
DETAILS = {0x6724: "COMPLETE", 0x6725: "INCOMPLETE", 0x6726: "AMBIGUOUS"}
FIRST_GENERATION = 106
TERMINAL_GENERATION = 107
FIRST_POSITION = 105
TERMINAL_POSITION = 106
TERMINAL_STAGE = spec.TERMINAL_STAGE
CHECKPOINT_SOURCE = "/proc/last_kmsg"
STOCK_RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")
RAW_SIZE = 2_097_136
ROOT = Path(__file__).resolve().parents[5]
SOURCE_PATHS = {
    "stock_process_v2_adapter": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_stock_process_v2_adapter.py",
    "p310_carrier_model": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p310_carrier_model.py",
    "p308_telemetry_spec": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p308_telemetry_spec.py",
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)


class DecodeError(ValueError):
    """A retained P3.19 stock Carrier record is not exact."""


def source_bytes(root: Path | None = None) -> dict[str, bytes]:
    base = ROOT if root is None else root.resolve()
    values: dict[str, bytes] = {}
    for name, logical_path in SOURCE_PATHS.items():
        path = base / logical_path
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise DecodeError(f"P3.19 source {name} is not a direct regular file")
        with path.open("rb") as stream:
            data = stream.read(512 * 1024 + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
        if (
            len(data) != before.st_size or len(data) > 512 * 1024
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise DecodeError(f"P3.19 source {name} changed while reading")
        values[name] = data
    return values


# The Process-v2 source-binding path records ``model.__file__``.  Keep the
# actual P310 carrier module as the model rather than wrapping it in a fake
# object.  Only the P319 terminal metadata is an adapter-level annotation.
model = carrier


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _crc(envelope: bytes) -> int:
    return binascii.crc32(CRC_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF


def _decode_stock_envelope(envelope: bytes, *, detail: int) -> dict[str, Any]:
    if not isinstance(envelope, bytes) or len(envelope) != ENVELOPE_SIZE:
        raise DecodeError("P3.19 stock envelope size differs")
    if envelope[:4] != ENVELOPE_MAGIC or envelope[4] != ENVELOPE_VERSION:
        raise DecodeError("P3.19 stock envelope magic/version differs")
    if envelope[43] != ENCODING or envelope[46] != PAYLOAD_SIZE:
        raise DecodeError("P3.19 stock encoding or payload extent differs")
    if (
        envelope[5:7] + envelope[8:43] + envelope[44:46] + envelope[47:48]
        != bytes(2 + 35 + 2 + 1)
    ):
        raise DecodeError("P3.19 stock header reserved fields differ")
    if envelope[7] != (1 << 5):
        raise DecodeError("P3.19 stock witness flag differs")
    if struct.unpack_from("<I", envelope, CRC_OFFSET)[0] != _crc(envelope):
        raise DecodeError("P3.19 stock envelope CRC differs")
    payload = envelope[PAYLOAD_OFFSET:CRC_OFFSET]
    if len(payload) != PAYLOAD_SIZE or payload[0] != PAYLOAD_ABI:
        raise DecodeError("P3.19 stock payload ABI differs")
    if payload[56] != STATUS_WIDTH or payload[57] != 1 or payload[58] != 1:
        raise DecodeError("P3.19 parent/W5/status-width evidence differs")
    if not payload[3] & (1 << 5) or payload[3] & 0xC0:
        raise DecodeError("P3.19 stock chain reserved bits are set")
    stage = payload[3] & 0x07
    complete = bool(payload[3] & (1 << 3))
    ambiguous = bool(payload[3] & (1 << 4))
    if stage > 4 or (complete and stage != 4) or (complete and ambiguous):
        raise DecodeError("P3.19 stock chain state is inconsistent")
    state = "AMBIGUOUS" if ambiguous else "COMPLETE" if complete else "INCOMPLETE"
    if DETAILS.get(detail) != state:
        raise DecodeError("P3.19 terminal detail and stock state differ")
    expected_mask = 0
    if payload[10]:
        expected_mask |= 1 << 0
    if payload[11]:
        expected_mask |= 1 << 1
    if payload[12]:
        expected_mask |= 1 << 2
    if payload[13]:
        expected_mask |= 1 << 3
    if payload[59]:
        expected_mask |= 1 << 4
    if payload[60]:
        expected_mask |= 1 << 5
    if payload[1] != expected_mask or payload[1] & (1 << 6):
        raise DecodeError("P3.19 stock witness mask differs")
    expected_validity = (1 << 3) | (1 << 4) | (1 << 5)
    if payload[12]:
        expected_validity |= 1 << 6
    if payload[13]:
        expected_validity |= 1 << 7
    if payload[2] != expected_validity:
        raise DecodeError("P3.19 stock validity mask differs")
    if stage >= 1 and payload[11] == 0:
        raise DecodeError("P3.19 IRQ stage count is absent")
    if stage >= 2 and payload[12] == 0:
        raise DecodeError("P3.19 status stage count is absent")
    if stage >= 3 and payload[13] == 0:
        raise DecodeError("P3.19 classification stage count is absent")
    if stage >= 4 and payload[10] == 0:
        raise DecodeError("P3.19 probe stage count is absent")
    if payload[12] == 0 and any(payload[14:17]):
        raise DecodeError("P3.19 absent status carries bytes")
    module_results = [struct.unpack_from("<h", payload, 4 + i * 2)[0] for i in range(3)]
    irqs = [struct.unpack_from("<h", payload, 17 + i * 2)[0] for i in range(5)]
    if any(value < 0 for value in irqs):
        raise DecodeError("P3.19 IRQ value is negative")
    record_count = struct.unpack_from("<H", payload, 35)[0]
    record_bytes = int.from_bytes(payload[37:40], "little")
    first_sequence = int.from_bytes(payload[40:48], "little")
    last_sequence = int.from_bytes(payload[48:56], "little")
    if record_count == 0:
        if record_bytes or first_sequence or last_sequence:
            raise DecodeError("P3.19 empty record accounting is nonzero")
    elif (
        record_bytes < record_count or last_sequence < first_sequence
        or last_sequence - first_sequence + 1 != record_count
    ):
        raise DecodeError("P3.19 record accounting is not monotonic")
    if record_count > 4096 or record_bytes > 1_048_576:
        raise DecodeError("P3.19 record accounting exceeds source bounds")
    if state == "COMPLETE" and (stage != 4 or any(module_results)):
        raise DecodeError("P3.19 complete state lacks zero module results")
    if any(payload[61:76]):
        raise DecodeError("P3.19 stock payload tail is nonzero")
    return _json_safe({
        "encoding": ENCODING,
        "payload_abi": PAYLOAD_ABI,
        "status_width": STATUS_WIDTH,
        "parent_unavailable": True,
        "w5_unavailable": True,
        "chain": list(CHAIN),
        "chain_stage": stage,
        "chain_complete": complete,
        "chain_ambiguous": ambiguous,
        "state": state,
        "terminal_detail": detail,
        "module_results": module_results,
        "module_results_all_zero": not any(module_results),
        "probe_count": payload[10],
        "irq_count": payload[11],
        "initial_status_count": payload[12],
        "classification_form1_count": payload[13],
        "initial_status": list(payload[14:17]),
        "irq": irqs,
        "classification_form1_index": int.from_bytes(payload[27:35], "little"),
        "record_count": record_count,
        "record_bytes": record_bytes,
        "first_sequence": first_sequence,
        "last_sequence": last_sequence,
        "classification_form2_count": payload[59],
        "deferred_status_count": payload[60],
        "envelope_sha256": hashlib.sha256(envelope).hexdigest(),
    })


def _fixture_envelope(state: str = "COMPLETE") -> bytes:
    detail = {name: code for code, name in DETAILS.items()}.get(state)
    if detail is None:
        raise DecodeError("P3.19 fixture state differs")
    envelope = bytearray(ENVELOPE_SIZE)
    envelope[:4] = ENVELOPE_MAGIC
    envelope[4] = ENVELOPE_VERSION
    envelope[7] = 1 << 5
    envelope[43] = ENCODING
    envelope[46] = PAYLOAD_SIZE
    payload = memoryview(envelope)[PAYLOAD_OFFSET:CRC_OFFSET]
    payload[0] = PAYLOAD_ABI
    payload[1] = 0x3F
    payload[2] = 0xF8
    payload[3] = {"COMPLETE": 0x2C, "INCOMPLETE": 0x20, "AMBIGUOUS": 0x34}[state]
    payload[10:14] = bytes((1, 1, 1, 1))
    payload[14:17] = bytes((1, 2, 3))
    for index, value in enumerate((22, 23, 26, 0, 0)):
        struct.pack_into("<H", payload, 17 + index * 2, value)
    struct.pack_into("<Q", payload, 27, 7)
    struct.pack_into("<H", payload, 35, 1)
    payload[37:40] = (1).to_bytes(3, "little")
    struct.pack_into("<Q", payload, 40, 1)
    struct.pack_into("<Q", payload, 48, 1)
    payload[56:61] = bytes((STATUS_WIDTH, 1, 1, 2, 1))
    struct.pack_into("<I", envelope, CRC_OFFSET, _crc(bytes(envelope)))
    return bytes(envelope)


def encode_fixture(*, state: str = "COMPLETE") -> bytes:
    """Build a deterministic full Carrier fixture for Process-v2 tests."""
    envelope = _fixture_envelope(state)
    header = carrier._header(PROFILE, STOCK_RUN_ID)  # noqa: SLF001
    first_position = spec.POSITIONS[FIRST_POSITION]
    terminal_position = spec.POSITIONS[TERMINAL_POSITION]
    first = carrier.Slot(
        0, FIRST_GENERATION, first_position.stage, carrier.OUTCOME_PROGRESS,
        first_position.item_index, 0x0DA3, carrier.PAYLOAD_RAW_EXCERPT,
        envelope[:64],
    )
    terminal = carrier.Slot(
        1, TERMINAL_GENERATION, terminal_position.stage, carrier.OUTCOME_FAILURE,
        terminal_position.item_index, DETAILS and next(
            code for code, name in DETAILS.items() if name == state
        ), carrier.PAYLOAD_RAW_EXCERPT, envelope[64:],
    )
    return header + carrier._encode_slot(header, first) + carrier._encode_slot(header, terminal)  # noqa: SLF001


def _decode_stock_carrier(
    record: bytes, *, expected_profile: str, expected_run_id: bytes | None
) -> dict[str, Any]:
    if len(record) != carrier.LONG_RECORD_SIZE:
        raise DecodeError("P3.19 Carrier record size differs")
    try:
        header_profile, run_id = carrier._decode_header(  # noqa: SLF001
            record[: carrier.LONG_HEADER_SIZE], expected_profile, expected_run_id
        )
    except carrier.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    slots: list[dict[str, Any]] = []
    statuses: list[str] = []
    for slot_id in range(carrier.SLOT_COUNT):
        start = carrier.LONG_HEADER_SIZE + slot_id * carrier.SLOT_SIZE
        raw = record[start : start + carrier.SLOT_SIZE]
        body, recorded_raw = raw[:-4], raw[-4:]
        recorded = struct.unpack("<I", recorded_raw)[0]
        if recorded == 0:
            statuses.append("uncommitted")
            continue
        if recorded != carrier._slot_crc(  # noqa: SLF001
            record[: carrier.LONG_HEADER_SIZE], slot_id, body
        ):
            statuses.append("bad-crc")
            continue
        generation, stage, outcome, item, kind, length, reserved, detail, padded = carrier.SLOT_BODY_STRUCT.unpack(body)
        if reserved or length > carrier.REQUEST_PAYLOAD_SIZE or any(padded[length:]):
            statuses.append("bad-body")
            continue
        if generation not in (FIRST_GENERATION, TERMINAL_GENERATION):
            statuses.append("foreign")
            continue
        slots.append({
            "slot_id": slot_id, "generation": generation, "stage": stage,
            "outcome": outcome, "item_index": item, "detail": detail,
            "payload_kind": kind, "payload": padded[:length],
        })
        statuses.append("valid")
    if {row["generation"] for row in slots} != {FIRST_GENERATION, TERMINAL_GENERATION}:
        raise DecodeError("P3.19 stock Carrier pair is incomplete")
    rows = {row["generation"]: row for row in slots}
    first, terminal = rows[FIRST_GENERATION], rows[TERMINAL_GENERATION]
    first_position = spec.POSITIONS[FIRST_POSITION]
    terminal_position = spec.POSITIONS[TERMINAL_POSITION]
    if (
        first["outcome"] != carrier.OUTCOME_PROGRESS
        or (first["stage"], first["item_index"])
        != (first_position.stage, first_position.item_index)
        or first["detail"] != 0x0DA3
        or terminal["outcome"] != carrier.OUTCOME_FAILURE
        or (terminal["stage"], terminal["item_index"])
        != (terminal_position.stage, terminal_position.item_index)
        or terminal["detail"] not in DETAILS
        or first["payload_kind"] != carrier.PAYLOAD_RAW_EXCERPT
        or terminal["payload_kind"] != carrier.PAYLOAD_RAW_EXCERPT
        or len(first["payload"]) != 64
        or len(terminal["payload"]) != 64
        or statuses != ["valid", "valid"]
    ):
        raise DecodeError("P3.19 stock Carrier slot semantics differ")
    stock = _decode_stock_envelope(
        first["payload"] + terminal["payload"], detail=terminal["detail"]
    )
    return {
        "profile": header_profile,
        "run_id": run_id.hex(),
        "header_crc_valid": True,
        "slot_status": statuses,
        "valid_slots": _json_safe(slots),
        "active": _json_safe(terminal),
        "fallback_used": False,
        "terminal_success": False,
        "stock": stock,
    }


def decode_record(
    record: bytes, *, expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return _json_safe({
        "schema": SCHEMA,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": expected_profile,
        "carrier": _decode_stock_carrier(
            record, expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        ),
    })


def _base_classification(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    try:
        base = carrier.classify_observation(
            payload, expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except carrier.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    base_shape_valid = (
        base.get("long_record_count") == 1
        and base.get("exact_record_count") == 1
        and base.get("unsat_count") == 0
        and base.get("foreign_count") == 0
        and base.get("minimum_candidate_boots") == 1
        and base.get("integrity_issue") is not True
    )
    if not base_shape_valid:
        base["records"] = []
        base["classification"] = "P319_STOCK_WITNESS_BASE_SHAPE_FAILURE"
        base["accepted"] = False
        base["telemetry_count"] = 0
        base["contradiction_count"] = 0
        base["stock_result_count"] = 0
        return base
    attached: list[dict[str, Any]] = []
    for row in base.get("records", ()):
        if not isinstance(row, dict) or not isinstance(row.get("observer_offset"), int):
            raise DecodeError("P3.19 Carrier classifier record shape differs")
        start = row["observer_offset"]
        raw = payload[start : start + carrier.LONG_RECORD_SIZE]
        attached_row = dict(row)
        try:
            attached_row["p319_stock"] = _decode_stock_carrier(
                raw, expected_profile=expected_profile,
                expected_run_id=expected_run_id,
            )
        except DecodeError as exc:
            base.setdefault("integrity_issues", []).append("stock-envelope-shape")
            base["integrity_issue"] = True
            attached_row["p319_stock_error"] = str(exc)
        attached.append(attached_row)
    base["records"] = attached
    complete = sum(
        row.get("p319_stock", {}).get("stock", {}).get("state") == "COMPLETE"
        for row in attached
    )
    if base.get("integrity_issue") or len(attached) != 1:
        base["classification"] = (
            "AMBIGUOUS_INTEGRITY_FAILURE"
            if base.get("integrity_issue")
            else "P319_STOCK_WITNESS_MULTIPLICITY"
        )
        base["accepted"] = False
    elif complete == 1:
        base["classification"] = "P319_STOCK_WITNESS_COMPLETE"
        base["accepted"] = True
    else:
        states = {
            row.get("p319_stock", {}).get("stock", {}).get("state")
            for row in attached
        }
        base["classification"] = (
            "P319_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
            if "AMBIGUOUS" in states else "P319_STOCK_WITNESS_INCOMPLETE_NO_PROOF"
        )
        base["accepted"] = False
    base["telemetry_count"] = complete if len(attached) == 1 else 0
    base["contradiction_count"] = max(0, len(attached) - complete)
    base["stock_result_count"] = len(attached)
    return base


def classify_observation(
    payload: bytes, *, expected_profile: str = PROFILE,
    expected_run_id: bytes = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d"),
) -> dict[str, Any]:
    if not isinstance(payload, bytes) or len(payload) != RAW_SIZE:
        raise DecodeError("P3.19 observer payload must be one exact retained raw")
    value = _base_classification(
        payload, expected_profile=expected_profile, expected_run_id=expected_run_id
    )
    value.update({
        "schema": SCHEMA, "decoder": DECODER_ID, "policy_id": POLICY_ID,
        "profile": expected_profile, "run_id": expected_run_id.hex(),
        "telemetry_count": value.get("telemetry_count", 0),
        "contradiction_count": value.get("contradiction_count", 0),
        "stock_result_count": value.get("stock_result_count", value["exact_record_count"]),
        "acm_supplemental": True, "acm_required_for_acceptance": False,
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
    })
    return _json_safe(value)


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str = PROFILE,
    expected_run_id: bytes = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d"),
) -> dict[str, Any]:
    if not isinstance(payload, bytes) or len(payload) != 2_097_136:
        raise DecodeError("P3.19 baseline bound differs")
    probe = _base_classification(
        payload, expected_profile=expected_profile, expected_run_id=expected_run_id
    )
    if probe["long_record_count"] or probe["unsat_count"] or probe["integrity_issue"]:
        raise DecodeError("P3.19 baseline is not marker-free")
    return {
        "classification": "ZERO_AMBIGUOUS", "accepted": False,
        "records": [], "baseline_size": len(payload),
        "baseline_clean": True, "integrity_issue": False,
    }


def validate_contract(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecodeError("P3.19 overlay contract is not an object")
    required = {
        "userspace_overlay_contract_id", "decoder", "policy_id", "profile",
        "acm_supplemental", "source_contract_id",
    }
    if not required <= set(value):
        raise DecodeError("P3.19 overlay contract fields are incomplete")
    if (
        value["userspace_overlay_contract_id"] != OVERLAY_CONTRACT_ID
        or value["decoder"] != DECODER_ID
        or value["policy_id"] != POLICY_ID
        or value["profile"] != PROFILE
        or value["source_contract_id"] != PARENT_SOURCE_CONTRACT_ID
        or value["acm_supplemental"] is not True
        or value.get("p318_topology_causal_correlation") is True
    ):
        raise DecodeError("P3.19 overlay contract identity differs")
    return _json_safe(value)


def validate_acceptance_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise DecodeError("P3.19 acceptance is not an object")
    required = {
        "kind", "source", "decoder", "policy_id", "profile",
        "source_contract_id", "run_id", "long_family_hex", "unsat_family_hex",
        "terminal_stage", "minimum_success_count", "clean_baseline_required",
        "userspace_overlay_contract_id", "contract",
    }
    if set(item) != required:
        raise DecodeError("P3.19 acceptance key set differs")
    if (
        item["kind"] != "retained_e1_latest_stage_multiboot_after_rollback"
        or item["source"] != CHECKPOINT_SOURCE
        or item["decoder"] != DECODER_ID
        or item["policy_id"] != POLICY_ID
        or item["profile"] != PROFILE
        or item["source_contract_id"] != PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != OVERLAY_CONTRACT_ID
        or item["run_id"] != STOCK_RUN_ID.hex()
        or item["long_family_hex"] != LONG_FAMILY.hex()
        or item["unsat_family_hex"] != UNSAT_FAMILY.hex()
        or item["terminal_stage"] != TERMINAL_STAGE
        or item["minimum_success_count"] != 1
        or item["clean_baseline_required"] is not True
        or not isinstance(item["run_id"], str)
        or len(item["run_id"]) != 32
        or any(char not in "0123456789abcdef" for char in item["run_id"])
    ):
        raise DecodeError("P3.19 acceptance identity differs")
    contract = item["contract"]
    if not isinstance(contract, dict) or set(contract) != {"candidate_static", "run_manifest", "static_check"}:
        raise DecodeError("P3.19 acceptance contract differs")
    return _json_safe(item)


def acceptance_fixture() -> dict[str, Any]:
    return {
        "kind": "retained_e1_latest_stage_multiboot_after_rollback",
        "source": CHECKPOINT_SOURCE, "decoder": DECODER_ID,
        "policy_id": POLICY_ID, "profile": PROFILE,
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "run_id": bytes.fromhex("b9cc424d0d184f5accbce94a844e817d").hex(),
        "long_family_hex": LONG_FAMILY.hex(), "unsat_family_hex": UNSAT_FAMILY.hex(),
        "terminal_stage": TERMINAL_STAGE, "minimum_success_count": 1,
        "clean_baseline_required": True,
        "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
        "contract": {
            "candidate_static": {"path": "fixture", "size": 1, "sha256": "0" * 64},
            "run_manifest": {"path": "fixture", "size": 1, "sha256": "0" * 64},
            "static_check": {"path": "fixture", "size": 1, "sha256": "0" * 64},
        },
    }


def audit() -> dict[str, Any]:
    validate_contract({
        "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID, "policy_id": POLICY_ID, "profile": PROFILE,
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID, "acm_supplemental": True,
    })
    positive = encode_fixture()
    full = bytes(RAW_SIZE - len(positive)) + positive
    result = classify_observation(full)
    if result["accepted"] is not True or result["telemetry_count"] != 1:
        raise DecodeError("P3.19 full Carrier positive fixture differs")
    for state in ("INCOMPLETE", "AMBIGUOUS"):
        negative = classify_observation(bytes(RAW_SIZE - len(positive)) + encode_fixture(state=state))
        if negative["accepted"] is not False or negative["contradiction_count"] != 1:
            raise DecodeError("P3.19 no-proof fixture differs")
    def assert_base_shape_failure(raw: bytes, label: str) -> None:
        value = classify_observation(raw)
        if (
            value.get("accepted") is not False
            or value.get("classification") != "P319_STOCK_WITNESS_BASE_SHAPE_FAILURE"
            or value.get("telemetry_count") != 0
        ):
            raise DecodeError(f"P3.19 {label} base-shape negative was accepted")
    def with_prefix(prefix: bytes) -> bytes:
        if len(prefix) + len(positive) > RAW_SIZE:
            raise DecodeError("P3.19 negative fixture exceeds exact raw extent")
        return prefix + bytes(RAW_SIZE - len(prefix) - len(positive)) + positive
    assert_base_shape_failure(with_prefix(carrier.unsat_record(PROFILE, STOCK_RUN_ID)), "mixed exact+UNSAT")
    assert_base_shape_failure(with_prefix(carrier.LEGACY_FAMILIES[0] + b"legacy"), "legacy-family")
    assert_base_shape_failure(with_prefix(positive), "duplicate-long")
    try:
        decode_record(bytes(128), expected_profile=PROFILE, expected_run_id=STOCK_RUN_ID)
    except DecodeError:
        pass
    else:
        raise DecodeError("standalone MXD5 bytes were accepted as Carrier evidence")
    shifted = bytearray(full)
    shifted[-carrier.SLOT_SIZE - 20] ^= 1
    shifted_result = classify_observation(bytes(shifted))
    if shifted_result["accepted"] is True or not shifted_result["integrity_issue"]:
        raise DecodeError("P3.19 one-entry shifted CRC mutation was accepted")
    for bad in (positive, full[:-1], bytes(RAW_SIZE - 100) + positive[:100]):
        try:
            value = classify_observation(bad)
        except DecodeError:
            continue
        if value["accepted"] is True or value.get("integrity_issue") is not True:
            raise DecodeError("P3.19 truncated/edge raw was accepted")
    return {
        "schema": SCHEMA, "decoder": DECODER_ID, "policy_id": POLICY_ID,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "carrier_authority": PARENT_SOURCE_CONTRACT_ID, "profile": PROFILE,
        "positions": [FIRST_POSITION, TERMINAL_POSITION], "full_record_required": True,
        "acm_supplemental": True, "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
