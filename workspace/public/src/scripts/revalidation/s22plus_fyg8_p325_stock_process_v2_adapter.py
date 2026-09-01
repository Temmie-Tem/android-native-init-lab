#!/usr/bin/env python3
"""P3.25 Process-v2 Carrier adapter, host-only.

The exact P3.24 Carrier adapter is loaded by stable bytes.  Its nested
decoder/spec/fixture machinery is rebound to the fresh P3.25 run and overlay
identity while preserving the reviewed Carrier semantics.  P3.19--P3.24
identities remain predecessor inputs and are rejected.  This adapter performs
no device, ADB, or Odin action.
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
P324_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p324_stock_process_v2_adapter.py"
P324_ADAPTER_IDENTITY = {
    "size": 21_154,
    "sha256": "3f888926d98dffda159706bd92eaa74631793b46ea200302d1e61833d7fb13a3",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_RUN_ID_HEX = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P323_RUN_ID = bytes.fromhex(P323_RUN_ID_HEX)
P324_RUN_ID = bytes.fromhex(P324_RUN_ID_HEX)
P325_RUN_ID = bytes.fromhex(P325_RUN_ID_HEX)

P319_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p319-stock-witness-carrier-v1"
P320_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P321_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p321-observer-v4-carrier-v1"
P322_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p322-observer-v4-carrier-v1"
P323_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p323-observer-v4-carrier-v1"
P324_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p324-observer-v4-carrier-v1"
P325_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p325-observer-v4-carrier-v1"
P325_DECODER_ID = "s22plus_fyg8_p325_observer_v4_carrier_v1"
P325_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p325-observer-error-v1"
P325_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P325_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "intermediate=92:8f:0:4:0->93:90:2:0:6726|"
    "parent=unavailable|w5=unavailable|run="
    + P325_RUN_ID_HEX
    + "|causal=false|usb=false"
)
P325_POLICY_ID = hashlib.sha256(P325_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
P324_PREDECESSOR_RUN_ID_HEX = P324_RUN_ID_HEX
P324_PREDECESSOR_RUN_ID = P324_RUN_ID


class AdapterIdentityError(ValueError):
    """The exact P3.24 delegate or P3.25 binding is not available."""


class DecodeError(ValueError):
    """A P3.25 Carrier record or retained raw snapshot is not exact."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_source(
    path: Path, label: str, expected: Mapping[str, Any]
) -> bytes:
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


def _stable_self_source() -> bytes:
    direct = P325_ADAPTER_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(2 * 1024 * 1024 + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError("P3.25 adapter source is unavailable") from exc

    def inode(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
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
        or len(payload) > 2 * 1024 * 1024
    ):
        raise AdapterIdentityError("P3.25 adapter source changed")
    return payload


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(
        P324_ADAPTER_SOURCE,
        "P3.24 Process-v2 adapter source",
        P324_ADAPTER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p324_adapter_bound_for_p325")
    module.__file__ = str(P324_ADAPTER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P324_ADAPTER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.24 adapter failed to load") from exc
    if getattr(module, "P324_RUN_ID_HEX", None) != P324_RUN_ID_HEX:
        raise AdapterIdentityError("P3.24 adapter current identity differs")
    for name in (
        "decode_record",
        "classify_observation",
        "proof_class",
        "acceptance_fixture",
        "validate_acceptance_item",
        "bind_exact_sources",
    ):
        if not callable(getattr(module, name, None)):
            raise AdapterIdentityError(f"P3.24 adapter lacks {name}")
    return module


_P324 = _load_delegate()
_P323 = _P324._P323
_P322 = _P324._P322
_P321 = _P324._P321
_P320 = _P324._P320


def _set(module: types.ModuleType, values: Mapping[str, Any]) -> None:
    for name, value in values.items():
        if hasattr(module, name):
            setattr(module, name, value)


_CURRENT = {
    "P320_RUN_ID": P325_RUN_ID,
    "P321_RUN_ID": P325_RUN_ID,
    "P322_RUN_ID": P325_RUN_ID,
    "P323_RUN_ID": P325_RUN_ID,
    "P324_RUN_ID": P325_RUN_ID,
    "P320_STOCK_RUN_ID": P325_RUN_ID,
    "P323_STOCK_RUN_ID": P325_RUN_ID,
    "STOCK_RUN_ID": P325_RUN_ID,
    "RUN_ID": P325_RUN_ID,
    "SCHEMA": "s22plus_fyg8_p325_stock_process_v2_adapter_v1",
    "OVERLAY_CONTRACT_ID": P325_OVERLAY_CONTRACT_ID,
    "DECODER_ID": P325_DECODER_ID,
    "OBSERVER_CONTRACT_ID": P325_OBSERVER_CONTRACT_ID,
    "POLICY_PREIMAGE": P325_POLICY_PREIMAGE,
    "POLICY_ID": P325_POLICY_ID,
}
for _module in (_P320, _P321, _P322, _P323, _P324):
    _set(_module, _CURRENT)

for _module in (_P320, _P321, _P322, _P323, _P324):
    for _value in _module.__dict__.values():
        if not callable(_value):
            continue
        _defaults = getattr(_value, "__kwdefaults__", None)
        if not _defaults:
            continue
        _updated = dict(_defaults)
        _changed = False
        for _key in ("expected_run_id", "run_id"):
            if _key in _updated:
                _updated[_key] = P325_RUN_ID
                _changed = True
        if _changed:
            _value.__kwdefaults__ = _updated

_STALE_IDS = tuple(
    bytes.fromhex(value)
    for value in (
        P319_RUN_ID_HEX,
        P320_RUN_ID_HEX,
        P321_RUN_ID_HEX,
        P322_RUN_ID_HEX,
        P323_RUN_ID_HEX,
        P324_RUN_ID_HEX,
    )
)
_P324._STALE_IDS = _STALE_IDS


# Export the stable P320 carrier/spec/source surface required by callers.
for _name, _value in _P320.__dict__.items():
    if not _name.startswith("__"):
        globals().setdefault(_name, _value)


SCHEMA = "s22plus_fyg8_p325_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P325_OVERLAY_CONTRACT_ID
DECODER_ID = P325_DECODER_ID
OBSERVER_CONTRACT_ID = P325_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P325_POLICY_PREIMAGE
POLICY_ID = P325_POLICY_ID
RUN_ID = P325_RUN_ID
STOCK_RUN_ID = P325_RUN_ID
P325_STOCK_RUN_ID = P325_RUN_ID
P324_STOCK_RUN_ID = P324_RUN_ID
P324_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p324_stock_process_v2_adapter.py"
P325_ADAPTER_SOURCE = Path(__file__).resolve()
P324_DECODER_ID = "s22plus_fyg8_p324_observer_v4_carrier_v1"
P324_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p324-observer-error-v1"
P324_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p324-observer-v4-carrier-v1"
P324_POLICY_PREIMAGE = getattr(_P324, "P324_POLICY_PREIMAGE", "")
P324_POLICY_ID = getattr(_P324, "P324_POLICY_ID", "")
PARENT_SOURCE_CONTRACT_ID = _P320.PARENT_SOURCE_CONTRACT_ID
PROFILE = _P320.PROFILE
RAW_SIZE = _P320.RAW_SIZE
carrier = _P320.carrier
ContractError = getattr(_P320, "ContractError", ValueError)


def _bound(expected_run_id: bytes | None) -> bytes:
    bound = P325_RUN_ID if expected_run_id is None else expected_run_id
    if bound != P325_RUN_ID:
        raise DecodeError("P325 Carrier run ID is not bound to the P325 run")
    return bound


def _reject_stale_record(record: bytes) -> None:
    if type(record) is bytes and any(record.count(old) for old in _STALE_IDS):
        raise DecodeError("P325 Carrier record contains a predecessor run ID")


def _public(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    result = dict(value)
    result.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "run_id": P325_RUN_ID_HEX,
        }
    )
    if result.get("classification") == "P324_STOCK_ENCODER_FAILURE":
        result["classification"] = "P325_STOCK_ENCODER_FAILURE"
    if result.get("proof_class") == "P324_STOCK_ENCODER_FAILURE":
        result["proof_class"] = "P325_STOCK_ENCODER_FAILURE"
    result.update(
        {
            "acm_primary": True,
            "carrier_supplemental": True,
            "acm_supplemental": False,
            "acm_required_for_acceptance": True,
            "acm_required_for_arrival_proof": True,
        }
    )
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale_record(record)
    try:
        return _public(
            _P324.decode_record(
                record,
                expected_profile=expected_profile,
                expected_run_id=P325_RUN_ID,
            )
        )
    except Exception as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError(str(exc)) from exc


def encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    try:
        payload = _P324.encode_fixture(*args, **kwargs)
        _reject_stale_record(payload)
        return payload
    except Exception as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError(str(exc)) from exc


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P325_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale_record(payload)
    try:
        return _public(
            _P324.classify_observation(
                payload,
                expected_profile=expected_profile,
                expected_run_id=P325_RUN_ID,
            )
        )
    except Exception as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError(str(exc)) from exc


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P325_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale_record(payload)
    try:
        return _public(
            _P324.classify_clean_baseline(
                payload,
                expected_profile=expected_profile,
                expected_run_id=P325_RUN_ID,
            )
        )
    except Exception as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError(str(exc)) from exc


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    try:
        result = _P324.proof_class(value, expected=None)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    if result == "P324_STOCK_ENCODER_FAILURE":
        result = "P325_STOCK_ENCODER_FAILURE"
    if expected is not None and result != expected:
        raise DecodeError("P325 proof class does not match expected state")
    return result


def validate_contract(value: Any) -> dict[str, Any]:
    return _P320.validate_contract(value)


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    return _P320.validate_acceptance_item(value)


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P324.acceptance_fixture())
    contract = dict(value.get("contract", {}))
    for key in ("candidate_static", "run_manifest", "static_check"):
        entry = dict(contract.get(key, {}))
        entry["path"] = "p325-stock-observer-v4-fixture"
        contract[key] = entry
    value.update(
        {
            "contract": contract,
            "schema": SCHEMA,
            "run_id": P325_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
        }
    )
    return value


def bind_exact_sources() -> dict[str, Any]:
    value = dict(_P324.bind_exact_sources())
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P325_RUN_ID_HEX,
            "predecessor_run_id_rejected": P324_RUN_ID_HEX,
            "source_adapter": {
                "path": str(P325_ADAPTER_SOURCE.relative_to(ROOT)),
            },
        }
    )
    payload = _stable_self_source()
    value["source_adapter"] = {
        "path": str(P325_ADAPTER_SOURCE.relative_to(ROOT)),
        **identity(payload),
    }
    return value


def audit() -> dict[str, Any]:
    value = dict(_P324.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P325_STOCK_PROCESS_V2_ADAPTER_H0",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P324_RUN_ID_HEX,
            "run_id": P325_RUN_ID_HEX,
            "encoder_failure_class": "P325_STOCK_ENCODER_FAILURE",
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
    "P323_OVERLAY_CONTRACT_ID",
    "P324_ADAPTER_IDENTITY",
    "P324_ADAPTER_SOURCE",
    "P324_DECODER_ID",
    "P324_OBSERVER_CONTRACT_ID",
    "P324_OVERLAY_CONTRACT_ID",
    "P324_POLICY_ID",
    "P324_POLICY_PREIMAGE",
    "P324_PREDECESSOR_RUN_ID",
    "P324_PREDECESSOR_RUN_ID_HEX",
    "P324_RUN_ID",
    "P324_RUN_ID_HEX",
    "P324_STOCK_RUN_ID",
    "P325_ADAPTER_SOURCE",
    "P325_DECODER_ID",
    "P325_OBSERVER_CONTRACT_ID",
    "P325_OVERLAY_CONTRACT_ID",
    "P325_POLICY_ID",
    "P325_POLICY_PREIMAGE",
    "P325_RUN_ID",
    "P325_RUN_ID_HEX",
    "P325_STOCK_RUN_ID",
    "P319_RUN_ID",
    "P319_RUN_ID_HEX",
    "P320_RUN_ID",
    "P320_RUN_ID_HEX",
    "P321_RUN_ID",
    "P321_RUN_ID_HEX",
    "P322_RUN_ID",
    "P322_RUN_ID_HEX",
    "P323_RUN_ID",
    "P323_RUN_ID_HEX",
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


bind_lineage = bind_exact_sources
