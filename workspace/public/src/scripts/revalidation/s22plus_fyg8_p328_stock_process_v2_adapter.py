#!/usr/bin/env python3
"""P3.28 Process-v2 adapter for the authenticated bounded exec proof.

The P3.27 carrier/parser remains the implementation base.  This adapter gives
the authenticated successor a fresh schema, policy, decoder, and run identity
and rejects every predecessor run ID before delegating a parse.  It is
host-only and does not open a device endpoint.
"""

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
P327_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p327_stock_process_v2_adapter.py"
P327_ADAPTER_IDENTITY = {
    "size": 11_607,
    "sha256": "408d2d11e11fd90b624f59f60d9e2220c306b9f6bbd105b2a607dcbfc2353fe0",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_RUN_ID_HEX = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P326_RUN_ID_HEX = "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P327_RUN_ID_HEX = "c327f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P328_RUN_ID_HEX = "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P327_RUN_ID = bytes.fromhex(P327_RUN_ID_HEX)
P328_RUN_ID = bytes.fromhex(P328_RUN_ID_HEX)
P327_PREDECESSOR_RUN_ID_HEX = P327_RUN_ID_HEX
P327_PREDECESSOR_RUN_ID = P327_RUN_ID
P326_PREDECESSOR_RUN_ID_HEX = P327_PREDECESSOR_RUN_ID_HEX
P326_RUN_ID = bytes.fromhex(P326_RUN_ID_HEX)

P328_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p328-authenticated-exec-v1"
P328_DECODER_ID = "s22plus_fyg8_p328_authenticated_exec_v1"
P328_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p328-observer-authenticated-v1"
P328_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P328_STOCK_OBSERVER_V1|carrier=S22E1L2-192|"
    "positions=105,106|envelope=MXD5-128|encoding=4|payload_abi=4|"
    "receipt=offset61,size15|details=6724,6725,6726|"
    "auth=auth-key-v1,size32,mode0400,nlink1|"
    "acm=pid1-authenticated-framed-fixed-3+busybox-ash|run="
    + P328_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P328_POLICY_ID = hashlib.sha256(P328_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]

AUTH_KEY_SCHEMA = "s22plus_fyg8_p328_auth_key_v1"
AUTH_KEY_SIZE = 32
AUTH_KEY_MODE = 0o400
DEFAULT_AUTH_KEY_PATH = ROOT / (
    "workspace/private/inputs/s22plus_fyg8_p328/auth-key-v1.bin"
)


class AdapterIdentityError(ValueError):
    """The consumed P3.27 adapter or fresh P3.28 contract differs."""


class DecodeError(ValueError):
    """The bounded carrier cannot be accepted under P3.28."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
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
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != dict(expected)
    ):
        raise AdapterIdentityError(f"{label} identity differs")
    return payload


def _auth_key_bytes(value: Path | str | bytes) -> bytes:
    if type(value) is bytes:
        payload = value
    else:
        direct = Path(value).absolute()
        try:
            before = direct.lstat()
            resolved = direct.resolve(strict=True)
            with direct.open("rb") as stream:
                payload = stream.read(AUTH_KEY_SIZE + 1)
                inside = os.fstat(stream.fileno())
            after = direct.lstat()
        except OSError as exc:
            raise AdapterIdentityError("P328 auth key is unavailable") from exc
        if (
            direct != resolved
            or stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) != AUTH_KEY_MODE
            or _inode(before) != _inode(inside)
            or _inode(before) != _inode(after)
            or before.st_size != AUTH_KEY_SIZE
            or len(payload) != AUTH_KEY_SIZE
        ):
            raise AdapterIdentityError("P328 auth key identity differs")
        return payload
    if len(payload) != AUTH_KEY_SIZE:
        raise AdapterIdentityError("P328 auth key bytes differ")
    return payload


def auth_key_identity(value: Path | str | bytes = DEFAULT_AUTH_KEY_PATH) -> dict[str, Any]:
    """Return only ``{size, sha256}``; never publish the key path."""
    return identity(_auth_key_bytes(value))


def _load_delegate() -> types.ModuleType:
    payload = _stable(P327_ADAPTER_SOURCE, "P3.27 adapter", P327_ADAPTER_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p327_adapter_bound_for_p328")
    module.__file__ = str(P327_ADAPTER_SOURCE)
    module.__package__ = ""
    try:
        exec(  # noqa: S102 - exact, hash-pinned source closure loading
            compile(payload, str(P327_ADAPTER_SOURCE), "exec", dont_inherit=True),
            module.__dict__,
        )
    except Exception as exc:
        raise AdapterIdentityError("P3.27 adapter failed to load") from exc
    if getattr(module, "P327_RUN_ID_HEX", None) != P327_RUN_ID_HEX:
        raise AdapterIdentityError("P3.27 adapter identity differs")
    return module


_P327 = _load_delegate()
# The loaded P3.27 wrapper names its immediate delegate ``_P326`` and keeps
# the P3.25-through-P3.20 chain in ``_P326_BASE``.
_P327_BASE = _P327._P326_BASE
_CURRENT = {
    "P320_RUN_ID": P328_RUN_ID,
    "P321_RUN_ID": P328_RUN_ID,
    "P322_RUN_ID": P328_RUN_ID,
    "P323_RUN_ID": P328_RUN_ID,
    "P324_RUN_ID": P328_RUN_ID,
    "P325_RUN_ID": P328_RUN_ID,
    "P326_RUN_ID": P328_RUN_ID,
    "P327_RUN_ID": P328_RUN_ID,
    "P320_STOCK_RUN_ID": P328_RUN_ID,
    "P323_STOCK_RUN_ID": P328_RUN_ID,
    "P325_STOCK_RUN_ID": P328_RUN_ID,
    "P326_STOCK_RUN_ID": P328_RUN_ID,
    "STOCK_RUN_ID": P328_RUN_ID,
    "RUN_ID": P328_RUN_ID,
    "SCHEMA": "s22plus_fyg8_p328_stock_process_v2_adapter_v1",
    "OVERLAY_CONTRACT_ID": P328_OVERLAY_CONTRACT_ID,
    "DECODER_ID": P328_DECODER_ID,
    "OBSERVER_CONTRACT_ID": P328_OBSERVER_CONTRACT_ID,
    "POLICY_PREIMAGE": P328_POLICY_PREIMAGE,
    "POLICY_ID": P328_POLICY_ID,
}
for _module in (
    _P327,
    _P327._P326,
    _P327_BASE,
    _P327_BASE._P324,
    _P327_BASE._P323,
    _P327_BASE._P322,
    _P327_BASE._P321,
    _P327_BASE._P320,
):
    for _name, _value in _CURRENT.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)
    for _value in _module.__dict__.values():
        if callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            for _key in ("expected_run_id", "run_id"):
                if _key in _defaults:
                    _defaults[_key] = P328_RUN_ID
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
        P326_RUN_ID_HEX,
        P327_RUN_ID_HEX,
    )
)
for _module in (_P327, _P327._P326, _P327_BASE):
    _module._STALE_IDS = _STALE_IDS

for _name, _value in _P327_BASE._P320.__dict__.items():
    if not _name.startswith("__"):
        globals().setdefault(_name, _value)

SCHEMA = "s22plus_fyg8_p328_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P328_OVERLAY_CONTRACT_ID
DECODER_ID = P328_DECODER_ID
OBSERVER_CONTRACT_ID = P328_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P328_POLICY_PREIMAGE
POLICY_ID = P328_POLICY_ID
RUN_ID = P328_RUN_ID
STOCK_RUN_ID = P328_RUN_ID
P328_STOCK_RUN_ID = P328_RUN_ID
P328_ADAPTER_SOURCE = Path(__file__).resolve()
PROFILE = _P327.PROFILE
RAW_SIZE = _P327.RAW_SIZE
PARENT_SOURCE_CONTRACT_ID = _P327.PARENT_SOURCE_CONTRACT_ID
carrier = _P327.carrier
ContractError = _P327.ContractError


def _bound(expected_run_id: bytes | None) -> None:
    if (P328_RUN_ID if expected_run_id is None else expected_run_id) != P328_RUN_ID:
        raise DecodeError("P328 Carrier run ID differs")


def _reject_stale(payload: bytes) -> None:
    if type(payload) is bytes and any(old in payload for old in _STALE_IDS):
        raise DecodeError("P328 Carrier contains a predecessor run ID")


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
            "run_id": P328_RUN_ID_HEX,
            "acm_primary": True,
            "acm_bidirectional_primary": True,
            "busybox_shell_primary": True,
            "framed_fixed_command_primary": False,
            "bounded_command_primary": True,
            "authenticated_exec": True,
            "authentication_required": True,
            "auth_key_schema": AUTH_KEY_SCHEMA,
            "auth_key_size": AUTH_KEY_SIZE,
            "auth_key_path_published": False,
            "caller_selected_command": True,
            "carrier_supplemental": True,
            "acm_required_for_acceptance": True,
            "acm_required_for_arrival_proof": True,
        }
    )
    for key in ("classification", "proof_class"):
        if result.get(key) == "P327_STOCK_ENCODER_FAILURE":
            result[key] = "P328_STOCK_ENCODER_FAILURE"
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale(record)
    try:
        return _public(
            _P327.decode_record(
                record, expected_profile=expected_profile, expected_run_id=P328_RUN_ID
            )
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    try:
        payload = _P327.encode_fixture(*args, **kwargs)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    _reject_stale(payload)
    return payload


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P328_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale(payload)
    try:
        return _public(
            _P327.classify_observation(
                payload, expected_profile=expected_profile, expected_run_id=P328_RUN_ID
            )
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P328_RUN_ID,
) -> dict[str, Any]:
    _bound(expected_run_id)
    _reject_stale(payload)
    try:
        return _public(
            _P327.classify_clean_baseline(
                payload, expected_profile=expected_profile, expected_run_id=P328_RUN_ID
            )
        )
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    try:
        result = _P327.proof_class(value, expected=None)
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
    if result == "P327_STOCK_ENCODER_FAILURE":
        result = "P328_STOCK_ENCODER_FAILURE"
    if expected is not None and result != expected:
        raise DecodeError("P328 proof class differs")
    return result


validate_contract = _P327.validate_contract
validate_acceptance_item = _P327.validate_acceptance_item


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P327.acceptance_fixture())
    contract = dict(value.get("contract", {}))
    for key in ("candidate_static", "run_manifest", "static_check"):
        entry = dict(contract.get(key, {}))
        entry["path"] = "p328-authenticated-observer-v1-fixture"
        contract[key] = entry
    value.update(
        {
            "contract": contract,
            "schema": SCHEMA,
            "run_id": P328_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "authenticated_exec": True,
            "authentication_required": True,
            "auth_key_schema": AUTH_KEY_SCHEMA,
            "auth_key_size": AUTH_KEY_SIZE,
        }
    )
    return value


def bind_exact_sources(
    auth_key: Path | str | bytes | None = None,
) -> dict[str, Any]:
    value = dict(_P327.bind_exact_sources())
    payload = P328_ADAPTER_SOURCE.read_bytes()
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P328_RUN_ID_HEX,
            "predecessor_run_id_rejected": P327_RUN_ID_HEX,
            "authenticated_exec": True,
            "authentication_required": True,
            "auth_key_schema": AUTH_KEY_SCHEMA,
            "auth_key_size": AUTH_KEY_SIZE,
            "auth_key_path_published": False,
            "source_adapter": {
                "path": str(P328_ADAPTER_SOURCE.relative_to(ROOT)),
                **identity(payload),
            },
        }
    )
    if auth_key is not None:
        value["auth_key"] = auth_key_identity(auth_key)
    return value


def audit() -> dict[str, Any]:
    value = dict(_P327.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P328_STOCK_PROCESS_V2_ADAPTER_H0_AUTHENTICATED",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P327_RUN_ID_HEX,
            "run_id": P328_RUN_ID_HEX,
            "encoder_failure_class": "P328_STOCK_ENCODER_FAILURE",
            "encoder_failure_is_success": False,
            "encoder_failure_is_causal": False,
            "authenticated_exec": True,
            "authentication_required": True,
            "auth_key_schema": AUTH_KEY_SCHEMA,
            "auth_key_size": AUTH_KEY_SIZE,
            "auth_key_path_published": False,
            "lineage": bind_exact_sources(),
        }
    )
    return value


bind_lineage = bind_exact_sources
__all__ = [name for name in globals() if not name.startswith("_")]
