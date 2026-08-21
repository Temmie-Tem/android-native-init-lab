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
try:
    import s22plus_fyg8_p319_result_contract_arming as c_arming
except ModuleNotFoundError as exc:
    if exc.name != "s22plus_fyg8_p319_result_contract_arming":
        raise
    import importlib.util

    _arming_spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p319_result_contract_arming", Path(__file__).with_name(
            "s22plus_fyg8_p319_result_contract_arming.py"
        )
    )
    if _arming_spec is None or _arming_spec.loader is None:
        raise
    c_arming = importlib.util.module_from_spec(_arming_spec)
    _arming_spec.loader.exec_module(c_arming)


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
PROOF_CLASS_BY_STATE = {
    "COMPLETE": "NONCAUSAL_SUCCESS_PATH",
    "INCOMPLETE": "NO_PROOF_EXPERIMENT_PRECONDITION",
    "AMBIGUOUS": "NO_PROOF_OBSERVER",
}
ARMING_SCHEMA = "s22plus_fyg8_p319_result_contract_arming_v1"
ARMING_VERDICT = "PASS_P319_RESULT_CONTRACT_ARMING_H0"
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


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


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
    required_module_validity = (1 << 3) | (1 << 4) | (1 << 5)
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
        "validity_mask": payload[2],
        "required_module_results_present": (
            payload[2] & required_module_validity
        ) == required_module_validity,
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
    detail = next(code for code, name in DETAILS.items() if name == state)
    return _encode_carrier_envelope(envelope, detail=detail)


def _encode_carrier_envelope(envelope: bytes, *, detail: int) -> bytes:
    if not isinstance(envelope, bytes) or len(envelope) != ENVELOPE_SIZE:
        raise DecodeError("P3.19 Carrier envelope size differs")
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
        terminal_position.item_index, detail, carrier.PAYLOAD_RAW_EXCERPT,
        envelope[64:],
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


def _record_accounting_gap_free(stock: dict[str, Any]) -> bool:
    fields = tuple(
        stock.get(name)
        for name in ("record_count", "record_bytes", "first_sequence", "last_sequence")
    )
    if any(isinstance(item, bool) or not isinstance(item, int) for item in fields):
        return False
    record_count, record_bytes, first_sequence, last_sequence = fields
    if record_count <= 0 or record_count > 4096 or record_bytes < 0 or record_bytes > 1_048_576:
        return False
    return (
        record_bytes >= record_count
        and last_sequence >= first_sequence
        and last_sequence - first_sequence + 1 == record_count
    )


def _exact_required_module_results(stock: dict[str, Any]) -> tuple[bool, bool]:
    results = stock.get("module_results")
    if (
        stock.get("required_module_results_present") is not True
        or not isinstance(results, list)
        or len(results) != 3
        or any(isinstance(item, bool) or not isinstance(item, int) for item in results)
    ):
        return False, False
    all_zero = all(item == 0 for item in results)
    if stock.get("module_results_all_zero") is not all_zero:
        return False, False
    return True, all_zero


def _proof_class_for_value(value: dict[str, Any]) -> str:
    """Derive a truthful result class from the retained decoded predicates."""
    if not isinstance(value, dict):
        return "NO_PROOF_OBSERVER"
    if (
        value.get("long_record_count") != 1
        or value.get("exact_record_count") != 1
        or value.get("unsat_count") != 0
        or value.get("foreign_count") != 0
        or value.get("minimum_candidate_boots") != 1
        or value.get("integrity_issue") is True
    ):
        return "NO_PROOF_OBSERVER"
    records = value.get("records")
    if not isinstance(records, list) or len(records) != 1:
        return "NO_PROOF_OBSERVER"
    if not isinstance(records[0], dict):
        return "NO_PROOF_OBSERVER"
    stock_container = records[0].get("p319_stock")
    if not isinstance(stock_container, dict):
        return "NO_PROOF_OBSERVER"
    stock = stock_container.get("stock", {})
    if not isinstance(stock, dict):
        return "NO_PROOF_OBSERVER"
    state = stock.get("state")
    modules_exact, modules_all_zero = _exact_required_module_results(stock)
    accounting_gap_free = _record_accounting_gap_free(stock)
    if state == "COMPLETE":
        if (
            value.get("accepted") is True
            and stock.get("chain_complete") is True
            and stock.get("chain_ambiguous") is False
            and modules_exact
            and modules_all_zero
        ):
            # The stock witness is internally complete, but the adapter's
            # causal_result_allowed contract remains permanently false.
            return "NONCAUSAL_SUCCESS_PATH"
        return "NO_PROOF_OBSERVER"
    if state == "INCOMPLETE":
        # This bucket admits either an exact required-module failure or a
        # clean, exact, unambiguous retained witness whose chain is
        # mechanically short of completion with gap-free accounting.
        if (
            value.get("accepted") is False
            and stock.get("chain_complete") is False
            and stock.get("chain_ambiguous") is False
            and isinstance(stock.get("chain_stage"), int)
            and 0 <= stock["chain_stage"] < 4
            and modules_exact
            and (
                not modules_all_zero
                or (modules_all_zero and accounting_gap_free)
            )
            and accounting_gap_free
        ):
            return "NO_PROOF_EXPERIMENT_PRECONDITION"
        return "NO_PROOF_OBSERVER"
    if state == "AMBIGUOUS":
        return "NO_PROOF_OBSERVER"
    return "NO_PROOF_OBSERVER"


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
    value["proof_class"] = _proof_class_for_value(value)
    return _json_safe(value)


def _full_fixture(*, state: str) -> bytes:
    """Put the Python-only deterministic fixture in one exact retained raw."""
    record = encode_fixture(state=state)
    if len(record) != carrier.LONG_RECORD_SIZE:
        raise DecodeError("P3.19 encoded Carrier record has the wrong size")
    return bytes(RAW_SIZE - len(record)) + record


def _full_c_fixture(envelope: bytes, *, detail: int) -> bytes:
    """Put an exact envelope emitted by the bound C encoder into Carrier."""
    record = _encode_carrier_envelope(envelope, detail=detail)
    if len(record) != carrier.LONG_RECORD_SIZE:
        raise DecodeError("P3.19 C-encoded Carrier record has the wrong size")
    return bytes(RAW_SIZE - len(record)) + record


def _decoded_stock_state(value: dict[str, Any]) -> str:
    records = value.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise DecodeError("P3.19 arming terminal does not contain one Carrier record")
    if not isinstance(records[0], dict):
        raise DecodeError("P3.19 arming terminal record is not an object")
    stock_container = records[0].get("p319_stock")
    if not isinstance(stock_container, dict):
        raise DecodeError("P3.19 arming terminal stock record is not an object")
    stock = stock_container.get("stock", {})
    if not isinstance(stock, dict):
        raise DecodeError("P3.19 arming terminal stock payload is not an object")
    state = stock.get("state")
    if state not in PROOF_CLASS_BY_STATE:
        raise DecodeError("P3.19 arming terminal state is not supported")
    return state


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    """Derive, and optionally require, the result-contract proof class."""
    state = _decoded_stock_state(value)
    result = _proof_class_for_value(value)
    if result != PROOF_CLASS_BY_STATE[state]:
        raise DecodeError("P3.19 decoded state predicates do not admit a proof class")
    if "proof_class" in value and value["proof_class"] != result:
        raise DecodeError("P3.19 proof class field differs from decoded predicates")
    if expected is not None and result != expected:
        raise DecodeError("P3.19 proof class does not match decoded terminal state")
    return result


def _mutate_terminal_detail(raw: bytes, detail: int) -> bytes:
    offset = len(raw) - carrier.LONG_RECORD_SIZE
    record = bytearray(raw[offset:])
    body_size = carrier.SLOT_SIZE - 4
    slot_offset = carrier.LONG_HEADER_SIZE + carrier.SLOT_SIZE
    body = list(carrier.SLOT_BODY_STRUCT.unpack(record[slot_offset:slot_offset + body_size]))
    body[7] = detail
    encoded = carrier.SLOT_BODY_STRUCT.pack(*body)
    record[slot_offset:slot_offset + body_size] = encoded
    struct.pack_into(
        "<I", record, slot_offset + body_size,
        carrier._slot_crc(bytes(record[:carrier.LONG_HEADER_SIZE]), 1, encoded),
    )
    return raw[:offset] + bytes(record) + raw[offset + carrier.LONG_RECORD_SIZE:]


def _mutate_envelope_state(raw: bytes, state: str) -> bytes:
    if state not in {"COMPLETE", "INCOMPLETE", "AMBIGUOUS"}:
        raise DecodeError("P3.19 mutation state is not supported")
    offset = len(raw) - carrier.LONG_RECORD_SIZE
    record = bytearray(raw[offset:])
    body_size = carrier.SLOT_SIZE - 4
    pieces: list[bytearray] = []
    for slot_id in (0, 1):
        slot_offset = carrier.LONG_HEADER_SIZE + slot_id * carrier.SLOT_SIZE
        body = carrier.SLOT_BODY_STRUCT.unpack(record[slot_offset:slot_offset + body_size])
        pieces.append(bytearray(body[-1][:64]))
    envelope = bytearray(pieces[0] + pieces[1])
    magic_version = bytes(envelope[:5])
    envelope[PAYLOAD_OFFSET + 3] = {
        "COMPLETE": 0x2C, "INCOMPLETE": 0x20, "AMBIGUOUS": 0x34
    }[state]
    if bytes(envelope[:5]) != magic_version or magic_version != b"MXD5\x05":
        raise DecodeError("P3.19 state mutation changed envelope magic/version")
    struct.pack_into("<I", envelope, CRC_OFFSET, _crc(bytes(envelope)))
    for slot_id in (0, 1):
        slot_offset = carrier.LONG_HEADER_SIZE + slot_id * carrier.SLOT_SIZE
        body = list(carrier.SLOT_BODY_STRUCT.unpack(record[slot_offset:slot_offset + body_size]))
        body[-1] = bytes(envelope[slot_id * 64:(slot_id + 1) * 64])
        encoded = carrier.SLOT_BODY_STRUCT.pack(*body)
        record[slot_offset:slot_offset + body_size] = encoded
        struct.pack_into(
            "<I", record, slot_offset + body_size,
            carrier._slot_crc(bytes(record[:carrier.LONG_HEADER_SIZE]), slot_id, encoded),
        )
    return raw[:offset] + bytes(record) + raw[offset + carrier.LONG_RECORD_SIZE:]


def _rejected(raw: bytes, *, expected: str | None = None) -> bool:
    try:
        value = classify_observation(raw)
        if value.get("accepted") is True:
            if expected is None:
                return False
            proof_class(value, expected=expected)
            return False
        return True
    except (DecodeError, KeyError, TypeError, ValueError):
        return True


def audit_result_contract_arming() -> dict[str, Any]:
    """Qualify every terminal emitted by the bound P3.19 C publisher path."""
    actual = c_arming.execute_actual_stock_encoder()
    if (
        not isinstance(actual, dict)
        or actual.get("executed") is not True
        or actual.get("publisher_selector_verified") is not True
        or actual.get("publisher_reachability_verified") is not True
        or actual.get("encoder_rejected_checked_mismatches") is not True
        or actual.get("publisher_selector_proves_unreachable") is not True
    ):
        raise DecodeError("P3.19 actual C encoder did not execute")
    compiler_identity = actual.get("compiler_identity")
    if (
        not isinstance(compiler_identity, dict)
        or compiler_identity.get("realpath") != c_arming.PINNED_COMPILER_REALPATH
        or compiler_identity.get("size") != c_arming.PINNED_COMPILER_SIZE
        or compiler_identity.get("sha256") != c_arming.PINNED_COMPILER_SHA256
        or not isinstance(compiler_identity.get("version"), str)
        or not compiler_identity["version"].strip()
        or compiler_identity.get("version_sha256")
        != c_arming.PINNED_COMPILER_VERSION_SHA256
    ):
        raise DecodeError("P3.19 C compiler identity differs from pinned qualification tool")
    unreachable = actual.get("publisher_unreachable_direct_combinations")
    if (
        not isinstance(unreachable, dict)
        or set(unreachable) != {"INCOMPLETE_PLUS_AMBIGUOUS", "COMPLETE_PLUS_AMBIGUOUS"}
        or any(
            not isinstance(item, dict)
            or item.get("publisher_selected_state") != 2
            or item.get("publisher_unreachable") is not True
            for item in unreachable.values()
        )
    ):
        raise DecodeError("P3.19 ambiguous direct-state reachability proof is incomplete")
    encoded_states = actual.get("states")
    if not isinstance(encoded_states, list) or not encoded_states:
        raise DecodeError("P3.19 actual C encoder emitted no publisher states")
    admitted: list[dict[str, Any]] = []
    raw_by_state: dict[str, bytes] = {}
    seen_states: set[str] = set()
    for encoded in encoded_states:
        if not isinstance(encoded, dict):
            raise DecodeError("P3.19 actual C encoder state row is not an object")
        detail = encoded.get("terminal_detail")
        envelope = encoded.get("envelope")
        if not isinstance(detail, int) or not isinstance(envelope, bytes):
            raise DecodeError("P3.19 actual C encoder row is not typed")
        state = DETAILS.get(detail)
        if state is None or state in seen_states:
            raise DecodeError("P3.19 actual C encoder emitted unsupported/duplicate detail")
        if PROOF_CLASS_BY_STATE.get(state) is None:
            raise DecodeError("P3.19 terminal detail has no proof-class mapping")
        raw = _full_c_fixture(envelope, detail=detail)
        decoded = classify_observation(raw)
        actual_state = _decoded_stock_state(decoded)
        if actual_state != state:
            raise DecodeError("P3.19 C-encoded terminal decoded to a different state")
        if decoded.get("proof_class") != PROOF_CLASS_BY_STATE[state]:
            raise DecodeError("P3.19 C-encoded terminal proof class differs")
        seen_states.add(state)
        raw_by_state[state] = raw
        admitted.append({
            "terminal_detail": detail,
            "state": actual_state,
            "publisher_terminal_state": encoded.get("publisher_terminal_state"),
            "proof_class": proof_class(decoded),
            "adapter_classification": decoded["classification"],
            "accepted": decoded["accepted"],
            "envelope_sha256": hashlib.sha256(envelope).hexdigest(),
            "decoder": decoded["decoder"],
            "policy_id": decoded["policy_id"],
        })
    required = {
        "NONCAUSAL_SUCCESS_PATH",
        "NO_PROOF_OBSERVER",
        "NO_PROOF_EXPERIMENT_PRECONDITION",
    }
    if {item["proof_class"] for item in admitted} != required:
        raise DecodeError("P3.19 result contract does not contain three distinct proof classes")
    if seen_states != set(DETAILS.values()):
        raise DecodeError("P3.19 actual C encoder did not cover all terminal states")
    if len(admitted) != len(DETAILS) or len({item["terminal_detail"] for item in admitted}) != len(admitted):
        raise DecodeError("P3.19 admitted terminal enumeration is not one-to-one")

    incomplete_detail = next(code for code, name in DETAILS.items() if name == "INCOMPLETE")
    hostile = {
        "detail_state_swap_rejected": _rejected(
            _mutate_terminal_detail(raw_by_state["COMPLETE"], incomplete_detail)
        ),
        "carrier_state_swap_rejected": _rejected(
            _mutate_envelope_state(raw_by_state["COMPLETE"], "INCOMPLETE")
        ),
    }
    try:
        proof_class(classify_observation(raw_by_state["COMPLETE"]), expected="NO_PROOF_OBSERVER")
    except DecodeError:
        hostile["proof_class_swap_rejected"] = True
    else:
        hostile["proof_class_swap_rejected"] = False
    if not all(hostile.values()):
        raise DecodeError("P3.19 result-contract hostile mutation was accepted")
    return {
        "schema": ARMING_SCHEMA,
        "verdict": ARMING_VERDICT,
        "profile": PROFILE,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "enumeration_source": "bound P3.19 C publisher selector -> exact C stock encoder -> 128-byte envelope -> real Carrier -> classify_observation",
        "encoder": actual.get("encoder"),
        "carrier_representation": "full retained Carrier record at exact RAW_SIZE",
        "admitted_terminals": admitted,
        "admitted_terminal_count": len(admitted),
        "unsynthesizable_or_undecodable_excluded": True,
        "publisher_reachable_states_only": True,
        "publisher_reachability_verified": actual.get(
            "publisher_reachability_verified"
        ) is True,
        "encoder_rejected_checked_mismatches": actual.get(
            "encoder_rejected_checked_mismatches"
        ) is True,
        "publisher_selector_proves_unreachable": actual.get(
            "publisher_selector_proves_unreachable"
        ) is True,
        "publisher_unreachable_direct_combinations": unreachable,
        "compiler_identity": compiler_identity,
        "hostile_tests": hostile,
        "c_encoder_fixture_path": actual.get("source_identity"),
        "causal_result_allowed": False,
        "candidate_success": False,
        "device_contact": False,
    }


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
    arming = audit_result_contract_arming()
    return {
        "schema": SCHEMA, "decoder": DECODER_ID, "policy_id": POLICY_ID,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "carrier_authority": PARENT_SOURCE_CONTRACT_ID, "profile": PROFILE,
        "positions": [FIRST_POSITION, TERMINAL_POSITION], "full_record_required": True,
        "result_contract_arming": arming,
        "acm_supplemental": True, "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
