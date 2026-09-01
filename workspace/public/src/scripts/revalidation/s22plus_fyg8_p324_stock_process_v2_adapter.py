#!/usr/bin/env python3
"""P3.24 Process-v2 Carrier adapter, host-only.

The exact P3.23 ACM-primary adapter is loaded once by stable bytes.  Its
execution-critical decoder, fixture generator, and retained encoder-failure
classification are rebound to the fresh P3.24 identity and output overlay;
the observer behavior itself is unchanged.  P3.19--P3.23 run IDs and AP
identities remain predecessor inputs and are rejected.  No device, ADB, or
Odin action is reachable from this module.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
P323_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p323_stock_process_v2_adapter.py"
P323_ADAPTER_IDENTITY = {
    "size": 21_168,
    "sha256": "e53e79e4d0bcd149a3968778d270c0196af775d418ab14456c73c068b9dbffbe",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P323_RUN_ID = bytes.fromhex(P323_RUN_ID_HEX)
P324_RUN_ID = bytes.fromhex(P324_RUN_ID_HEX)

P319_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p319-stock-witness-carrier-v1"
P320_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P321_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p321-observer-v4-carrier-v1"
P322_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p322-observer-v4-carrier-v1"
P323_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p323-observer-v4-carrier-v1"
P324_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p324-observer-v4-carrier-v1"
P324_DECODER_ID = "s22plus_fyg8_p324_observer_v4_carrier_v1"
P324_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p324-observer-error-v1"
P324_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P324_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "intermediate=92:8f:0:4:0->93:90:2:0:6726|"
    "parent=unavailable|w5=unavailable|run="
    + P324_RUN_ID_HEX
    + "|causal=false|usb=false"
)
P324_POLICY_ID = hashlib.sha256(P324_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
P323_PREDECESSOR_RUN_ID = P323_RUN_ID
P323_PREDECESSOR_RUN_ID_HEX = P323_RUN_ID_HEX


class AdapterIdentityError(ValueError):
    """The exact P3.23 delegate or P3.24 binding is not available."""


class DecodeError(ValueError):
    """A P3.24 Carrier record or retained raw snapshot is not exact."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_source(path: Path, label: str, expected: Mapping[str, Any]) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(int(expected["size"]) + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError(f"{label} is unavailable") from exc

    def inode(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_nlink,
            value.st_uid,
            value.st_gid,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or identity(payload) != dict(expected)
    ):
        raise AdapterIdentityError(f"{label} identity differs")
    return payload


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(
        P323_ADAPTER_SOURCE,
        "P3.23 Process-v2 adapter source",
        P323_ADAPTER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p323_adapter_bound_for_p324")
    module.__file__ = str(P323_ADAPTER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P323_ADAPTER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.23 adapter failed to load") from exc
    if getattr(module, "P323_RUN_ID_HEX", None) != P323_RUN_ID_HEX:
        raise AdapterIdentityError("P3.23 adapter current identity differs")
    for name in (
        "decode_record",
        "classify_observation",
        "proof_class",
        "acceptance_fixture",
        "validate_acceptance_item",
    ):
        if not callable(getattr(module, name, None)):
            raise AdapterIdentityError(f"P3.23 adapter lacks {name}")
    return module


_P323 = _load_delegate()
_P322 = _P323._P322_MODULE
_P321 = _P323._P321_MODULE
_P320 = _P323._P320_MODULE


def _set(module: types.ModuleType, values: Mapping[str, Any]) -> None:
    for name, value in values.items():
        if hasattr(module, name):
            setattr(module, name, value)


# All decoder layers capture run IDs in globals and keyword defaults.  Rebind
# their current slot together, while keeping P323 as the truthful immediate
# predecessor in the public wrapper below.
_set(
    _P320,
    {
        "P320_RUN_ID": P324_RUN_ID,
        "P320_STOCK_RUN_ID": P324_RUN_ID,
        "STOCK_RUN_ID": P324_RUN_ID,
        "RUN_ID": P324_RUN_ID,
        "P319_STOCK_RUN_ID": P323_RUN_ID,
        "SCHEMA": "s22plus_fyg8_p324_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P324_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P324_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P324_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P324_POLICY_PREIMAGE,
        "POLICY_ID": P324_POLICY_ID,
    },
)
_set(
    _P321,
    {
        "P321_RUN_ID": P324_RUN_ID,
        "P322_RUN_ID": P324_RUN_ID,
        "P320_RUN_ID": P324_RUN_ID,
        "P320_STOCK_RUN_ID": P324_RUN_ID,
        "STOCK_RUN_ID": P324_RUN_ID,
        "RUN_ID": P324_RUN_ID,
        "P319_STOCK_RUN_ID": P323_RUN_ID,
        "SCHEMA": "s22plus_fyg8_p324_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P324_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P324_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P324_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P324_POLICY_PREIMAGE,
        "POLICY_ID": P324_POLICY_ID,
    },
)
_set(
    _P322,
    {
        "P321_RUN_ID_HEX": P324_RUN_ID_HEX,
        "P321_RUN_ID": P324_RUN_ID,
        "P322_RUN_ID_HEX": P324_RUN_ID_HEX,
        "P322_RUN_ID": P324_RUN_ID,
        "P320_RUN_ID": P324_RUN_ID,
        "P320_STOCK_RUN_ID": P324_RUN_ID,
        "STOCK_RUN_ID": P324_RUN_ID,
        "RUN_ID": P324_RUN_ID,
        "P319_STOCK_RUN_ID": P323_RUN_ID,
        "SCHEMA": "s22plus_fyg8_p324_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P324_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P324_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P324_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P324_POLICY_PREIMAGE,
        "POLICY_ID": P324_POLICY_ID,
    },
)
_set(
    _P323,
    {
        "P323_RUN_ID_HEX": P324_RUN_ID_HEX,
        "P323_RUN_ID": P324_RUN_ID,
        "P323_STOCK_RUN_ID": P324_RUN_ID,
        "P322_RUN_ID_HEX": P324_RUN_ID_HEX,
        "P322_RUN_ID": P324_RUN_ID,
        "P320_RUN_ID": P324_RUN_ID,
        "P320_STOCK_RUN_ID": P324_RUN_ID,
        "STOCK_RUN_ID": P324_RUN_ID,
        "RUN_ID": P324_RUN_ID,
        "P319_STOCK_RUN_ID": P323_RUN_ID,
        "SCHEMA": "s22plus_fyg8_p324_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P324_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P324_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P324_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P324_POLICY_PREIMAGE,
        "POLICY_ID": P324_POLICY_ID,
    },
)

for module in (_P323, _P322, _P321, _P320):
    for value in module.__dict__.values():
        if not callable(value):
            continue
        defaults = getattr(value, "__kwdefaults__", None)
        if not defaults:
            continue
        updated = dict(defaults)
        changed = False
        for key in ("expected_run_id", "run_id"):
            if key in updated:
                updated[key] = P324_RUN_ID
                changed = True
        if changed:
            value.__kwdefaults__ = updated


# Export the stable P320 carrier/spec/source closure expected by the common
# evidence verifier.  The delegate globals above are already rebound to P324;
# the explicit P324 names below remain authoritative where they overlap.
for _name, _value in _P320.__dict__.items():
    if not _name.startswith("__"):
        globals().setdefault(_name, _value)


SCHEMA = "s22plus_fyg8_p324_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P324_OVERLAY_CONTRACT_ID
DECODER_ID = P324_DECODER_ID
OBSERVER_CONTRACT_ID = P324_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P324_POLICY_PREIMAGE
POLICY_ID = P324_POLICY_ID
RUN_ID = P324_RUN_ID
STOCK_RUN_ID = P324_RUN_ID
P324_STOCK_RUN_ID = P324_RUN_ID
P323_STOCK_RUN_ID = P323_RUN_ID
P323_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p323_stock_process_v2_adapter.py"
P323_ADAPTER_IDENTITY = dict(P323_ADAPTER_IDENTITY)
P323_DECODER_ID = "s22plus_fyg8_p323_observer_v4_carrier_v1"
P323_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p323-observer-error-v1"
P323_POLICY_PREIMAGE = getattr(_P323, "P323_POLICY_PREIMAGE", "")
P323_POLICY_ID = getattr(_P323, "P323_POLICY_ID", "")
PARENT_SOURCE_CONTRACT_ID = _P320.PARENT_SOURCE_CONTRACT_ID
PROFILE = _P320.PROFILE
RAW_SIZE = _P320.RAW_SIZE
carrier = _P320.carrier
ContractError = getattr(_P320, "ContractError", ValueError)

# Keep the predecessor identity bytes available to the nested classes, but
# never accept an old record as a P3.24 observation.
_STALE_IDS = tuple(
    bytes.fromhex(value)
    for value in (
        P319_RUN_ID_HEX,
        P320_RUN_ID_HEX,
        P321_RUN_ID_HEX,
        P322_RUN_ID_HEX,
        P323_RUN_ID_HEX,
    )
)


def _bound(expected_run_id: bytes | None) -> bytes:
    bound = P324_RUN_ID if expected_run_id is None else expected_run_id
    if bound != P324_RUN_ID:
        raise DecodeError("P324 Carrier run ID is not bound to the P324 run")
    return bound


def _reject_stale_record(record: bytes) -> None:
    if type(record) is not bytes:
        return
    if any(record.count(old) for old in _STALE_IDS):
        raise DecodeError("P324 Carrier record contains a predecessor run ID")


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale_record(record)
    try:
        value = _P323.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=P324_RUN_ID,
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    return value


def encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    try:
        return _P320.encode_fixture(*args, **kwargs)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def _empty_payload(value: object) -> bool:
    return value == b"" or value == {"encoding": "hex", "value": ""}


def _row_matches(row: object, expected: Mapping[str, int]) -> bool:
    return type(row) is dict and all(
        type(row.get(key)) is int and row[key] == value
        for key, value in expected.items()
    )


def _encoder_failure_shape(value: object) -> bool:
    if type(value) is not dict:
        return False
    records = value.get("records")
    if (
        value.get("accepted") is not False
        or value.get("integrity_issue") is not False
        or value.get("integrity_issues") != []
        or value.get("long_record_count") != 1
        or value.get("exact_record_count") != 1
        or value.get("foreign_count") != 0
        or value.get("contradiction_count") != 1
        or type(records) is not list
        or len(records) != 1
        or type(records[0]) is not dict
    ):
        return False
    slots = records[0].get("valid_slots")
    prior = {"slot_id": 0, "generation": 92, "stage": 0x8F, "outcome": 0, "item_index": 4, "detail": 0, "payload_kind": 0}
    active = {"slot_id": 1, "generation": 93, "stage": 0x90, "outcome": 2, "item_index": 0, "detail": 0x6726, "payload_kind": 0}
    return (
        records[0].get("profile") == PROFILE
        and records[0].get("run_id") == P324_RUN_ID_HEX
        and records[0].get("header_crc_valid") is True
        and records[0].get("slot_status") == ["valid", "valid"]
        and type(slots) is list
        and len(slots) == 2
        and _row_matches(slots[0], prior)
        and _row_matches(slots[1], active)
        and _empty_payload(slots[0].get("payload"))
        and _empty_payload(slots[1].get("payload"))
        and _row_matches(records[0].get("active"), active)
        and _empty_payload(records[0]["active"].get("payload"))
        and records[0].get("fallback_used") is False
        and records[0].get("terminal_success") is False
    )


def _is_p324_encoder_failure_value(value: object) -> bool:
    if not _encoder_failure_shape(value):
        return False
    expected = {
        "schema": SCHEMA,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": PROFILE,
        "run_id": P324_RUN_ID_HEX,
        "classification": "P324_STOCK_ENCODER_FAILURE",
        "proof_class": "P324_STOCK_ENCODER_FAILURE",
        "producer_failure": True,
        "stock_encoder_failure": True,
        "stock_encoder_failed_before_bridge": True,
        "candidate_native_arrival_supported": True,
        "candidate_success": False,
        "causal_result_allowed": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
        "acm_primary": True,
        "carrier_supplemental": True,
        "acm_supplemental": False,
        "acm_required_for_acceptance": True,
        "acm_required_for_arrival_proof": True,
        "max77705_scientific_result": "NOT_PRODUCED",
        "exact_encoder_predicate": "UNKNOWN_NOT_RETAINED",
    }
    return all(
        type(value.get(key)) is type(wanted) and value.get(key) == wanted
        for key, wanted in expected.items()
    )


def _normalize_failure(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "run_id": P324_RUN_ID_HEX,
            "classification": "P324_STOCK_ENCODER_FAILURE",
            "proof_class": "P324_STOCK_ENCODER_FAILURE",
        }
    )
    return result


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P324_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale_record(payload)
    try:
        value = _P323.classify_observation(
            payload,
            expected_profile=expected_profile,
            expected_run_id=P324_RUN_ID,
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    value = dict(value)
    if value.get("classification") == "P323_STOCK_ENCODER_FAILURE":
        value = _normalize_failure(value)
    else:
        value.update(
            {
                "schema": SCHEMA,
                "overlay_contract_id": OVERLAY_CONTRACT_ID,
                "decoder": DECODER_ID,
                "policy_id": POLICY_ID,
                "run_id": P324_RUN_ID_HEX,
            }
        )
    value.update(
        {
            "acm_primary": True,
            "carrier_supplemental": True,
            "acm_supplemental": False,
            "acm_required_for_acceptance": True,
            "acm_required_for_arrival_proof": True,
        }
    )
    return value


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    if _is_p324_encoder_failure_value(value):
        result = "P324_STOCK_ENCODER_FAILURE"
        if expected is not None and expected != result:
            raise DecodeError("P324 proof class does not match expected state")
        return result
    try:
        result = _P323.proof_class(value, expected=None)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    if expected is not None and result != expected:
        raise DecodeError("P324 proof class does not match expected state")
    return result


def _proof_class_for_value(value: dict[str, Any]) -> str:
    if _is_p324_encoder_failure_value(value):
        return "P324_STOCK_ENCODER_FAILURE"
    try:
        return _P323._proof_class_for_value(value)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P324_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    try:
        value = _P323.classify_clean_baseline(
            payload,
            expected_profile=expected_profile,
            expected_run_id=P324_RUN_ID,
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    return value


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P323.acceptance_fixture())
    contract = dict(value.get("contract", {}))
    for key in ("candidate_static", "run_manifest", "static_check"):
        entry = dict(contract.get(key, {}))
        entry["path"] = "p324-stock-observer-v4-fixture"
        contract[key] = entry
    value.update(
        {
            "contract": contract,
            "schema": SCHEMA,
            "run_id": P324_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
        }
    )
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    return _P320.validate_contract(value)


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    return _P320.validate_acceptance_item(value)


def bind_exact_sources() -> dict[str, Any]:
    value = dict(_P320.bind_exact_sources())
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P324_RUN_ID_HEX,
            "predecessor_run_id_rejected": P323_RUN_ID_HEX,
            "source_adapter": {
                "path": str(P323_ADAPTER_SOURCE.relative_to(ROOT)),
                **P323_ADAPTER_IDENTITY,
            },
        }
    )
    return value


bind_lineage = bind_exact_sources


def audit() -> dict[str, Any]:
    value = dict(_P323.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P324_STOCK_PROCESS_V2_ADAPTER_H0",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P323_RUN_ID_HEX,
            "run_id": P324_RUN_ID_HEX,
            "encoder_failure_class": "P324_STOCK_ENCODER_FAILURE",
            "encoder_failure_is_success": False,
            "encoder_failure_is_causal": False,
        }
    )
    return value


__all__ = [
    "AdapterIdentityError",
    "ContractError",
    "DecodeError",
    "DECODER_ID",
    "OVERLAY_CONTRACT_ID",
    "P319_OVERLAY_CONTRACT_ID",
    "P320_OVERLAY_CONTRACT_ID",
    "P321_OVERLAY_CONTRACT_ID",
    "P322_OVERLAY_CONTRACT_ID",
    "P323_ADAPTER_IDENTITY",
    "P323_ADAPTER_SOURCE",
    "P323_DECODER_ID",
    "P323_OBSERVER_CONTRACT_ID",
    "P323_OVERLAY_CONTRACT_ID",
    "P323_POLICY_ID",
    "P323_POLICY_PREIMAGE",
    "P323_PREDECESSOR_RUN_ID",
    "P323_PREDECESSOR_RUN_ID_HEX",
    "P323_RUN_ID",
    "P323_RUN_ID_HEX",
    "P323_STOCK_RUN_ID",
    "P319_RUN_ID",
    "P319_RUN_ID_HEX",
    "P320_RUN_ID",
    "P320_RUN_ID_HEX",
    "P321_RUN_ID",
    "P321_RUN_ID_HEX",
    "P322_RUN_ID",
    "P322_RUN_ID_HEX",
    "P324_DECODER_ID",
    "P324_OBSERVER_CONTRACT_ID",
    "P324_OVERLAY_CONTRACT_ID",
    "P324_POLICY_ID",
    "P324_POLICY_PREIMAGE",
    "P324_RUN_ID",
    "P324_RUN_ID_HEX",
    "P324_STOCK_RUN_ID",
    "PARENT_SOURCE_CONTRACT_ID",
    "POLICY_ID",
    "POLICY_PREIMAGE",
    "PROFILE",
    "RAW_SIZE",
    "RUN_ID",
    "SCHEMA",
    "STOCK_RUN_ID",
    "acceptance_fixture",
    "audit",
    "bind_exact_sources",
    "bind_lineage",
    "carrier",
    "classify_clean_baseline",
    "classify_observation",
    "decode_record",
    "encode_fixture",
    "identity",
    "proof_class",
    "validate_acceptance_item",
    "validate_contract",
]
