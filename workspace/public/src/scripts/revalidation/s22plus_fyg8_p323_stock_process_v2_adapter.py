#!/usr/bin/env python3
"""P3.23 stock Carrier adapter with an explicit encoder-failure class.

The normal P3.22 ABI-v4 decoder remains the execution-critical decoder for
clean/incomplete/ambiguous stock envelopes.  This wrapper adds one narrow
post-live interpretation for the CRC-valid intermediate shape observed when
the stock encoder rejects its witness before the repaired bridge can run:

``generation 92 / 0x8f / progress -> generation 93 / 0x90 / failure 0x6726``.

The additional class is diagnostic only.  It is never a scientific success,
candidate-success, USB-causality, or live-authority result.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p313_postlive_decoder as p313  # noqa: E402


P322_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p322_stock_process_v2_adapter.py"
P322_ADAPTER_IDENTITY = {
    "size": 12_739,
    "sha256": "574f88d966b091fb24a3feb6ea7cbdde54f630fcaab688ca25d10c8181cd4bda",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P323_RUN_ID = bytes.fromhex(P323_RUN_ID_HEX)

P319_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p319-stock-witness-carrier-v1"
P320_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P321_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p321-observer-v4-carrier-v1"
P322_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p322-observer-v4-carrier-v1"
P323_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p323-observer-v4-carrier-v1"
P323_DECODER_ID = "s22plus_fyg8_p323_observer_v4_carrier_v1"
P323_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p323-observer-error-v1"
P323_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P323_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "intermediate=92:8f:0:4:0->93:90:2:0:6726|"
    "parent=unavailable|w5=unavailable|run="
    + P323_RUN_ID_HEX
    + "|causal=false|usb=false"
)
P323_POLICY_ID = hashlib.sha256(P323_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]

P322_PREDECESSOR_RUN_ID = P322_RUN_ID
P322_PREDECESSOR_RUN_ID_HEX = P322_RUN_ID_HEX


class AdapterIdentityError(ValueError):
    """The exact P3.22 delegate or P3.23 binding is not available."""


class DecodeError(ValueError):
    """A Carrier record or retained raw snapshot is not exact."""


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

    actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or actual != dict(expected)
    ):
        raise AdapterIdentityError(f"{label} identity differs")
    return payload


def _load_delegate() -> tuple[types.ModuleType, types.ModuleType, types.ModuleType]:
    payload = _stable_source(
        P322_ADAPTER_SOURCE,
        "P3.22 Process-v2 adapter source",
        P322_ADAPTER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p322_adapter_bound_for_p323")
    module.__file__ = str(P322_ADAPTER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P322_ADAPTER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.22 adapter failed to load") from exc
    expected = {
        "P319_RUN_ID_HEX": P319_RUN_ID_HEX,
        "P320_RUN_ID_HEX": P320_RUN_ID_HEX,
        "P321_RUN_ID_HEX": P321_RUN_ID_HEX,
        "P322_RUN_ID_HEX": P322_RUN_ID_HEX,
        "P319_RUN_ID": P319_RUN_ID,
        "P320_RUN_ID": P320_RUN_ID,
        "P321_RUN_ID": P321_RUN_ID,
        "P322_RUN_ID": P322_RUN_ID,
    }
    if any(getattr(module, name, None) != value for name, value in expected.items()):
        raise AdapterIdentityError("P3.22 adapter predecessor identities differ")
    p321_module = module._DELEGATE
    p320_module = p321_module._DELEGATE

    # P322's current slot is P321's wrapper and P320's decoder.  Rebind both
    # layers explicitly; changing only the outer module would leave the
    # captured keyword defaults decoding the predecessor.
    p321_values = {
        "P321_RUN_ID_HEX": P323_RUN_ID_HEX,
        "P321_RUN_ID": P323_RUN_ID,
        "P322_RUN_ID_HEX": P323_RUN_ID_HEX,
        "P322_RUN_ID": P323_RUN_ID,
        "P320_RUN_ID": P323_RUN_ID,
        "P320_STOCK_RUN_ID": P323_RUN_ID,
        "P319_STOCK_RUN_ID": P322_RUN_ID,
        "STOCK_RUN_ID": P323_RUN_ID,
        "RUN_ID": P323_RUN_ID,
        "SCHEMA": "s22plus_fyg8_p323_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P323_OVERLAY_CONTRACT_ID,
        "P321_OVERLAY_CONTRACT_ID": P323_OVERLAY_CONTRACT_ID,
        "P320_OVERLAY_CONTRACT_ID": P322_OVERLAY_CONTRACT_ID,
        "P319_OVERLAY_CONTRACT_ID": P321_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P323_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P323_OBSERVER_CONTRACT_ID,
        "P321_DECODER_ID": P323_DECODER_ID,
        "P321_OBSERVER_CONTRACT_ID": P323_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P323_POLICY_PREIMAGE,
        "POLICY_ID": P323_POLICY_ID,
        "P321_POLICY_PREIMAGE": P323_POLICY_PREIMAGE,
        "P321_POLICY_ID": P323_POLICY_ID,
    }
    for name, value in p321_values.items():
        setattr(p321_module, name, value)

    p320_values = {
        "P320_STOCK_RUN_ID": P323_RUN_ID,
        "P320_RUN_ID": P323_RUN_ID,
        "STOCK_RUN_ID": P323_RUN_ID,
        "RUN_ID": P323_RUN_ID,
        "P319_STOCK_RUN_ID": P322_RUN_ID,
        "SCHEMA": "s22plus_fyg8_p323_stock_process_v2_adapter_v1",
        "OVERLAY_CONTRACT_ID": P323_OVERLAY_CONTRACT_ID,
        "P319_OVERLAY_CONTRACT_ID": P322_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P323_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P323_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P323_POLICY_PREIMAGE,
        "POLICY_ID": P323_POLICY_ID,
    }
    for name, value in p320_values.items():
        setattr(p320_module, name, value)

    outer_values = {
        "P321_RUN_ID_HEX": P323_RUN_ID_HEX,
        "P321_RUN_ID": P323_RUN_ID,
        "P322_RUN_ID_HEX": P323_RUN_ID_HEX,
        "P322_RUN_ID": P323_RUN_ID,
        "P320_RUN_ID": P323_RUN_ID,
        "P320_STOCK_RUN_ID": P323_RUN_ID,
        "P319_STOCK_RUN_ID": P322_RUN_ID,
        "P321_OVERLAY_CONTRACT_ID": P323_OVERLAY_CONTRACT_ID,
        "P320_OVERLAY_CONTRACT_ID": P322_OVERLAY_CONTRACT_ID,
        "P319_OVERLAY_CONTRACT_ID": P321_OVERLAY_CONTRACT_ID,
        "P321_DECODER_ID": P323_DECODER_ID,
        "P321_OBSERVER_CONTRACT_ID": P323_OBSERVER_CONTRACT_ID,
        "P321_POLICY_PREIMAGE": P323_POLICY_PREIMAGE,
        "P321_POLICY_ID": P323_POLICY_ID,
    }
    for name, value in outer_values.items():
        setattr(module, name, value)

    for current in (module, p321_module, p320_module):
        for value in current.__dict__.values():
            if callable(value):
                defaults = getattr(value, "__kwdefaults__", None)
                if not defaults:
                    continue
                updated = dict(defaults)
                changed = False
                for key in ("expected_run_id", "run_id"):
                    if key in updated:
                        updated[key] = P323_RUN_ID
                        changed = True
                if changed:
                    value.__kwdefaults__ = updated
    return module, p321_module, p320_module


_P322_MODULE, _P321_MODULE, _P320_MODULE = _load_delegate()

# Use the P320 core's names for the ordinary P322 ABI-v4 fixture/decoder.  Its
# globals were rebound above, so all nested calls remain P323-bound.
for _name, _value in _P320_MODULE.__dict__.items():
    if not _name.startswith("__"):
        globals().setdefault(_name, _value)

SCHEMA = "s22plus_fyg8_p323_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P323_OVERLAY_CONTRACT_ID
DECODER_ID = P323_DECODER_ID
OBSERVER_CONTRACT_ID = P323_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P323_POLICY_PREIMAGE
POLICY_ID = P323_POLICY_ID
RUN_ID = P323_RUN_ID
STOCK_RUN_ID = P323_RUN_ID
P323_STOCK_RUN_ID = P323_RUN_ID
P322_STOCK_RUN_ID = P322_RUN_ID
PREDECESSOR_P322_RUN_ID = P322_RUN_ID
P322_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p322_stock_process_v2_adapter.py"
P322_ADAPTER_IDENTITY = dict(P322_ADAPTER_IDENTITY)


def _bound(expected_run_id: bytes | None) -> bytes:
    bound = P323_RUN_ID if expected_run_id is None else expected_run_id
    if bound != P323_RUN_ID:
        raise DecodeError("P323 Carrier run ID is not bound to the P323 run")
    return bound


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    _bound(expected_run_id)
    try:
        return _P322_MODULE.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=P323_RUN_ID,
        )
    except Exception as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError(str(exc)) from exc


def _empty_payload(value: object) -> bool:
    return value == b"" or value == {"encoding": "hex", "value": ""}


def _row_matches(row: object, expected: Mapping[str, int]) -> bool:
    return type(row) is dict and all(
        type(row.get(key)) is int and row[key] == value
        for key, value in expected.items()
    )


def _encoder_failure_shape(value: object) -> bool:
    """Return true only for the retained CRC-valid P322 failure transition."""
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
    prior = {
        "slot_id": 0,
        "generation": 92,
        "stage": 0x8F,
        "outcome": 0,
        "item_index": 4,
        "detail": 0,
        "payload_kind": 0,
    }
    active = {
        "slot_id": 1,
        "generation": 93,
        "stage": 0x90,
        "outcome": 2,
        "item_index": 0,
        "detail": 0x6726,
        "payload_kind": 0,
    }
    return (
        records[0].get("profile") == PROFILE
        and records[0].get("run_id") == P323_RUN_ID_HEX
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


def _encoder_failure_classification(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any] | None:
    """Recognize only the P313 CRC-valid intermediate failure shape."""
    try:
        value = p313.classify_observation(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except Exception:
        return None
    if (
        value.get("classification") != "P313_OBSERVER_CONTRADICTION"
        or not _encoder_failure_shape(value)
    ):
        return None
    result = dict(value)
    result.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "profile": expected_profile,
            "run_id": expected_run_id.hex(),
            "classification": "P323_STOCK_ENCODER_FAILURE",
            "accepted": False,
            "proof_class": "P323_STOCK_ENCODER_FAILURE",
            "producer_failure": True,
            "stock_encoder_failure": True,
            "stock_encoder_failed_before_bridge": True,
            "failure_transition": "generation92_to_generation93_stage90_item0_detail6726",
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
    )
    return result


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P323_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    failure = _encoder_failure_classification(
        payload,
        expected_profile=expected_profile,
        expected_run_id=P323_RUN_ID,
    )
    if failure is not None:
        return failure
    try:
        value = _P322_MODULE.classify_observation(
            payload,
            expected_profile=expected_profile,
            expected_run_id=P323_RUN_ID,
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    # The delegated P322 result has already been validated against the exact
    # P323 slot after rebinding.  Normalize its public lineage labels here.
    value = dict(value)
    value.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "run_id": P323_RUN_ID_HEX,
            "acm_primary": True,
            "carrier_supplemental": True,
            "acm_supplemental": False,
            "acm_required_for_acceptance": True,
            "acm_required_for_arrival_proof": True,
        }
    )
    return value


def _is_p323_encoder_failure_value(value: object) -> bool:
    if not _encoder_failure_shape(value):
        return False
    expected = {
        "schema": SCHEMA,
        "overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": PROFILE,
        "run_id": P323_RUN_ID_HEX,
        "classification": "P323_STOCK_ENCODER_FAILURE",
        "proof_class": "P323_STOCK_ENCODER_FAILURE",
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


def _proof_class_for_value(value: dict[str, Any]) -> str:
    """Keep the exact producer failure distinct from generic observer damage."""
    if _is_p323_encoder_failure_value(value):
        return "P323_STOCK_ENCODER_FAILURE"
    return _P322_MODULE._proof_class_for_value(value)  # noqa: SLF001


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    """Validate and return the P323 proof class without P320 re-decoding."""
    if _is_p323_encoder_failure_value(value):
        result = "P323_STOCK_ENCODER_FAILURE"
        if expected is not None and expected != result:
            raise DecodeError("P323 proof class does not match expected state")
        return result
    try:
        return _P322_MODULE.proof_class(value, expected=expected)
    except Exception as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError(str(exc)) from exc


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P323_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    return _P322_MODULE.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=P323_RUN_ID,
    )


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P322_MODULE.acceptance_fixture())
    contract = dict(value.get("contract", {}))
    for key in ("candidate_static", "run_manifest", "static_check"):
        entry = dict(contract.get(key, {}))
        entry["path"] = "p323-stock-observer-v4-fixture"
        contract[key] = entry
    value["contract"] = contract
    value["schema"] = SCHEMA
    value["run_id"] = P323_RUN_ID_HEX
    value["overlay_contract_id"] = OVERLAY_CONTRACT_ID
    value["decoder"] = DECODER_ID
    value["policy_id"] = POLICY_ID
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    return _P320_MODULE.validate_contract(value)


def bind_exact_sources() -> dict[str, Any]:
    value = dict(_P320_MODULE.bind_exact_sources())
    value["overlay_contract_id"] = OVERLAY_CONTRACT_ID
    value["observer_contract_id"] = OBSERVER_CONTRACT_ID
    value["run_id"] = P323_RUN_ID_HEX
    value["predecessor_run_id_rejected"] = P322_RUN_ID_HEX
    value["source_adapter"] = {
        "path": str(P322_ADAPTER_SOURCE.relative_to(ROOT)),
        **P322_ADAPTER_IDENTITY,
    }
    return value


bind_lineage = bind_exact_sources


def audit() -> dict[str, Any]:
    value = dict(_P320_MODULE.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P323_STOCK_PROCESS_V2_ADAPTER_H0",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P322_RUN_ID_HEX,
            "run_id": P323_RUN_ID_HEX,
            "encoder_failure_class": "P323_STOCK_ENCODER_FAILURE",
            "encoder_failure_is_success": False,
            "encoder_failure_is_causal": False,
        }
    )
    return value


__all__ = [
    "AdapterIdentityError",
    "DecodeError",
    "DECODER_ID",
    "OVERLAY_CONTRACT_ID",
    "P319_OVERLAY_CONTRACT_ID",
    "P320_OVERLAY_CONTRACT_ID",
    "P321_OVERLAY_CONTRACT_ID",
    "P322_ADAPTER_IDENTITY",
    "P322_ADAPTER_SOURCE",
    "P322_PREDECESSOR_RUN_ID",
    "P322_PREDECESSOR_RUN_ID_HEX",
    "P322_RUN_ID",
    "P322_RUN_ID_HEX",
    "P323_DECODER_ID",
    "P323_OBSERVER_CONTRACT_ID",
    "P323_OVERLAY_CONTRACT_ID",
    "P323_POLICY_ID",
    "P323_POLICY_PREIMAGE",
    "P323_RUN_ID",
    "P323_RUN_ID_HEX",
    "P323_STOCK_RUN_ID",
    "P319_RUN_ID",
    "P319_RUN_ID_HEX",
    "P320_RUN_ID",
    "P320_RUN_ID_HEX",
    "P321_RUN_ID",
    "P321_RUN_ID_HEX",
    "RUN_ID",
    "SCHEMA",
    "STOCK_RUN_ID",
    "acceptance_fixture",
    "audit",
    "bind_exact_sources",
    "bind_lineage",
    "classify_clean_baseline",
    "classify_observation",
    "decode_record",
    "encode_fixture",
    "identity",
    "proof_class",
    "validate_acceptance_item",
    "validate_contract",
]
