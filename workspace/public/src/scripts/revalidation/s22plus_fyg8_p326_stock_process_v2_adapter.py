#!/usr/bin/env python3
"""P3.26 Process-v2 Carrier adapter with fresh identity (host-only)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from collections.abc import Mapping
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
P325_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p325_stock_process_v2_adapter.py"
P325_ADAPTER_IDENTITY = {
    "size": 16_978,
    "sha256": "6c4ae9a981ac30523275bc261857605d4c263113ceb9a4a3e079508d408919f0",
}
P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_RUN_ID_HEX = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P326_RUN_ID_HEX = "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_PREDECESSOR_RUN_ID_HEX = P325_RUN_ID_HEX
P325_RUN_ID = bytes.fromhex(P325_RUN_ID_HEX)
P326_RUN_ID = bytes.fromhex(P326_RUN_ID_HEX)

P326_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p326-observer-v4-carrier-v1"
P326_DECODER_ID = "s22plus_fyg8_p326_observer_v4_carrier_v1"
P326_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p326-observer-error-v1"
P326_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P326_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "acm=pid1-ping-pong+busybox-ash|run="
    + P326_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P326_POLICY_ID = hashlib.sha256(P326_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    pass


class DecodeError(ValueError):
    pass


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable(path: Path, label: str, expected: Mapping[str, Any]) -> bytes:
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
    inode = lambda value: (  # noqa: E731
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
    payload = _stable(P325_ADAPTER_SOURCE, "P325 adapter", P325_ADAPTER_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p325_adapter_bound_for_p326")
    module.__file__ = str(P325_ADAPTER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P325_ADAPTER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P325 adapter failed to load") from exc
    if getattr(module, "P325_RUN_ID_HEX", None) != P325_RUN_ID_HEX:
        raise AdapterIdentityError("P325 adapter identity differs")
    return module


_P325 = _load_delegate()
_CURRENT = {
    "P320_RUN_ID": P326_RUN_ID,
    "P321_RUN_ID": P326_RUN_ID,
    "P322_RUN_ID": P326_RUN_ID,
    "P323_RUN_ID": P326_RUN_ID,
    "P324_RUN_ID": P326_RUN_ID,
    "P325_RUN_ID": P326_RUN_ID,
    "P320_STOCK_RUN_ID": P326_RUN_ID,
    "P323_STOCK_RUN_ID": P326_RUN_ID,
    "P325_STOCK_RUN_ID": P326_RUN_ID,
    "STOCK_RUN_ID": P326_RUN_ID,
    "RUN_ID": P326_RUN_ID,
    "SCHEMA": "s22plus_fyg8_p326_stock_process_v2_adapter_v1",
    "OVERLAY_CONTRACT_ID": P326_OVERLAY_CONTRACT_ID,
    "DECODER_ID": P326_DECODER_ID,
    "OBSERVER_CONTRACT_ID": P326_OBSERVER_CONTRACT_ID,
    "POLICY_PREIMAGE": P326_POLICY_PREIMAGE,
    "POLICY_ID": P326_POLICY_ID,
}
for _module in (_P325, _P325._P320, _P325._P321, _P325._P322, _P325._P323, _P325._P324):
    for _name, _value in _CURRENT.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)
    for _value in _module.__dict__.values():
        if callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            for _key in ("expected_run_id", "run_id"):
                if _key in _defaults:
                    _defaults[_key] = P326_RUN_ID
            _value.__kwdefaults__ = _defaults

_STALE_IDS = tuple(
    bytes.fromhex(value)
    for value in (
        P319_RUN_ID_HEX,
        P320_RUN_ID_HEX,
        P321_RUN_ID_HEX,
        P322_RUN_ID_HEX,
        P323_RUN_ID_HEX,
        P324_RUN_ID_HEX,
        P325_RUN_ID_HEX,
    )
)
_P325._STALE_IDS = _STALE_IDS
_P325._P324._STALE_IDS = _STALE_IDS

for _name, _value in _P325._P320.__dict__.items():
    if not _name.startswith("__"):
        globals().setdefault(_name, _value)

SCHEMA = "s22plus_fyg8_p326_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P326_OVERLAY_CONTRACT_ID
DECODER_ID = P326_DECODER_ID
OBSERVER_CONTRACT_ID = P326_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P326_POLICY_PREIMAGE
POLICY_ID = P326_POLICY_ID
RUN_ID = P326_RUN_ID
STOCK_RUN_ID = P326_RUN_ID
P326_STOCK_RUN_ID = P326_RUN_ID
P326_ADAPTER_SOURCE = Path(__file__).resolve()
PROFILE = _P325.PROFILE
RAW_SIZE = _P325.RAW_SIZE
PARENT_SOURCE_CONTRACT_ID = _P325.PARENT_SOURCE_CONTRACT_ID
carrier = _P325.carrier
ContractError = _P325.ContractError


def _bound(expected_run_id: bytes | None) -> None:
    if (P326_RUN_ID if expected_run_id is None else expected_run_id) != P326_RUN_ID:
        raise DecodeError("P326 Carrier run ID differs")


def _reject_stale(payload: bytes) -> None:
    if type(payload) is bytes and any(old in payload for old in _STALE_IDS):
        raise DecodeError("P326 Carrier contains a predecessor run ID")


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
            "run_id": P326_RUN_ID_HEX,
            "acm_primary": True,
            "acm_bidirectional_primary": True,
            "busybox_shell_primary": True,
            "carrier_supplemental": True,
            "acm_required_for_acceptance": True,
            "acm_required_for_arrival_proof": True,
        }
    )
    for key in ("classification", "proof_class"):
        if result.get(key) == "P325_STOCK_ENCODER_FAILURE":
            result[key] = "P326_STOCK_ENCODER_FAILURE"
    return result


def decode_record(
    record: bytes, *, expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale(record)
    try:
        return _public(_P325.decode_record(record, expected_profile=expected_profile, expected_run_id=P326_RUN_ID))
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    try:
        payload = _P325.encode_fixture(*args, **kwargs)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    _reject_stale(payload)
    return payload


def classify_observation(
    payload: bytes, *, expected_profile: str = PROFILE,
    expected_run_id: bytes = P326_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale(payload)
    try:
        return _public(_P325.classify_observation(payload, expected_profile=expected_profile, expected_run_id=P326_RUN_ID))
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str = PROFILE,
    expected_run_id: bytes = P326_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale(payload)
    try:
        return _public(_P325.classify_clean_baseline(payload, expected_profile=expected_profile, expected_run_id=P326_RUN_ID))
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    try:
        result = _P325.proof_class(value, expected=None)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    if result == "P325_STOCK_ENCODER_FAILURE":
        result = "P326_STOCK_ENCODER_FAILURE"
    if expected is not None and result != expected:
        raise DecodeError("P326 proof class differs")
    return result


validate_contract = _P325.validate_contract
validate_acceptance_item = _P325.validate_acceptance_item


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P325.acceptance_fixture())
    contract = dict(value.get("contract", {}))
    for key in ("candidate_static", "run_manifest", "static_check"):
        entry = dict(contract.get(key, {}))
        entry["path"] = "p326-stock-observer-v4-fixture"
        contract[key] = entry
    value.update(
        {
            "contract": contract,
            "schema": SCHEMA,
            "run_id": P326_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
        }
    )
    return value


def bind_exact_sources() -> dict[str, Any]:
    value = dict(_P325.bind_exact_sources())
    payload = P326_ADAPTER_SOURCE.read_bytes()
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P326_RUN_ID_HEX,
            "predecessor_run_id_rejected": P325_RUN_ID_HEX,
            "source_adapter": {
                "path": str(P326_ADAPTER_SOURCE.relative_to(ROOT)),
                **identity(payload),
            },
        }
    )
    return value


def audit() -> dict[str, Any]:
    value = dict(_P325.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P326_STOCK_PROCESS_V2_ADAPTER_H0",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P325_RUN_ID_HEX,
            "run_id": P326_RUN_ID_HEX,
            "encoder_failure_class": "P326_STOCK_ENCODER_FAILURE",
            "encoder_failure_is_success": False,
            "encoder_failure_is_causal": False,
        }
    )
    return value


bind_lineage = bind_exact_sources
__all__ = [name for name in globals() if not name.startswith("_")]
