#!/usr/bin/env python3
"""P3.30 Process-v2 adapter with bounded pre-auth diagnostics.

This is a host-only, exact-source successor of the consumed P3.29 adapter.
The existing udev-settle, auth-key, endpoint, rollback, and Process-v2 bounds
remain in force; only the run identity and the diagnostic observer labels are
rotated.  It never opens a device endpoint or invokes a transfer tool.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p329_stock_process_v2_adapter.py")
SOURCE_IDENTITY = {
    "size": 8_843,
    "sha256": "c6894dbbcc8eaf2369a288f16d8379bf59e936517edc2c68d727cfd13b1ac16c",
}
P329_PREDECESSOR_RUN_ID_HEX = "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P329_PREDECESSOR_RUN_ID = bytes.fromhex(P329_PREDECESSOR_RUN_ID_HEX)
P330_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_RUN_ID = bytes.fromhex(P330_RUN_ID_HEX)
P330_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p330-authenticated-exec-udev-settle-diagnostic-v1"
P330_DECODER_ID = "s22plus_fyg8_p330_authenticated_exec_udev_settle_diagnostic_v1"
P330_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p330-observer-authenticated-diagnostic-settle-v1"
P330_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P330_STOCK_OBSERVER_V1|protocol=p328-auth-v1|"
    "diagnostic=open-parsed,rng-status,eagain-only-finite|"
    "udev-settle=500ms,25ms,both-mm-flags-required|run="
    + P330_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P330_POLICY_ID = hashlib.sha256(P330_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The exact P3.29 adapter or fresh P3.30 binding differs."""


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


def _load() -> types.ModuleType:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError("P3.29 adapter source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != SOURCE_IDENTITY
    ):
        raise AdapterIdentityError("P3.29 adapter source identity differs")
    module = types.ModuleType("s22plus_fyg8_p329_adapter_bound_for_p330")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.29 adapter source failed to load") from exc
    if getattr(module, "P329_RUN_ID_HEX", None) != P329_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.29 adapter binding differs")
    return module


def _modules(root: types.ModuleType) -> list[types.ModuleType]:
    result: list[types.ModuleType] = []
    pending = [root]
    while pending:
        module = pending.pop()
        if module in result:
            continue
        result.append(module)
        for name, value in vars(module).items():
            if name.startswith("_P") and isinstance(value, types.ModuleType):
                pending.append(value)
    return result


_P329 = _load()
for _module in _modules(_P329):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P329_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P330_RUN_ID)
        elif _value == P329_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P330_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            defaults = dict(_value.__kwdefaults__)
            for _key, _default in tuple(defaults.items()):
                if _default == P329_PREDECESSOR_RUN_ID:
                    defaults[_key] = P330_RUN_ID
                elif _default == P329_PREDECESSOR_RUN_ID_HEX:
                    defaults[_key] = P330_RUN_ID_HEX
            _value.__kwdefaults__ = defaults

_P329.P329_OVERLAY_CONTRACT_ID = P330_OVERLAY_CONTRACT_ID
_P329.P329_DECODER_ID = P330_DECODER_ID
_P329.P329_OBSERVER_CONTRACT_ID = P330_OBSERVER_CONTRACT_ID
_P329.P329_POLICY_PREIMAGE = P330_POLICY_PREIMAGE
_P329.P329_POLICY_ID = P330_POLICY_ID
_P329.SCHEMA = "s22plus_fyg8_p330_stock_process_v2_adapter_v1"
_P329.OVERLAY_CONTRACT_ID = P330_OVERLAY_CONTRACT_ID
_P329.DECODER_ID = P330_DECODER_ID
_P329.OBSERVER_CONTRACT_ID = P330_OBSERVER_CONTRACT_ID
_P329.POLICY_PREIMAGE = P330_POLICY_PREIMAGE
_P329.POLICY_ID = P330_POLICY_ID
_P329.P329_ADAPTER_SOURCE = Path(__file__).resolve()
_P329._P328._STALE_IDS = tuple(
    dict.fromkeys((*_P329._P328._STALE_IDS, P329_PREDECESSOR_RUN_ID))
)
for _module in (
    _P329._P328,
    _P329._P328._P327,
    _P329._P328._P327._P326,
    _P329._P328._P327_BASE,
):
    if hasattr(_module, "_STALE_IDS"):
        _module._STALE_IDS = _P329._P328._STALE_IDS
for _module in _modules(_P329):
    for _name, _value in {
        "SCHEMA": _P329.SCHEMA,
        "OVERLAY_CONTRACT_ID": P330_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P330_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P330_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P330_POLICY_PREIMAGE,
        "POLICY_ID": P330_POLICY_ID,
        "RUN_ID": P330_RUN_ID,
        "STOCK_RUN_ID": P330_RUN_ID,
    }.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)

_original_public = _P329._public


def _public(value: Any) -> Any:
    result = _original_public(value)
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": _P329.SCHEMA,
            "overlay_contract_id": P330_OVERLAY_CONTRACT_ID,
            "decoder": P330_DECODER_ID,
            "policy_id": P330_POLICY_ID,
            "run_id": P330_RUN_ID_HEX,
            "udev_guard_settle_bounded": True,
            "preauth_diagnostics_bounded": True,
        }
    )
    for key in ("classification", "proof_class"):
        if item.get(key) in ("P329_STOCK_ENCODER_FAILURE", "P328_STOCK_ENCODER_FAILURE"):
            item[key] = "P330_STOCK_ENCODER_FAILURE"
    return item


_P329._public = _public
for _name in getattr(_P329, "__all__", ()):
    globals()[_name] = getattr(_P329, _name)

SCHEMA = _P329.SCHEMA
OVERLAY_CONTRACT_ID = P330_OVERLAY_CONTRACT_ID
DECODER_ID = P330_DECODER_ID
OBSERVER_CONTRACT_ID = P330_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P330_POLICY_PREIMAGE
POLICY_ID = P330_POLICY_ID
RUN_ID = P330_RUN_ID
STOCK_RUN_ID = P330_RUN_ID
P329_RUN_ID = P330_RUN_ID
P329_RUN_ID_HEX = P330_RUN_ID_HEX
P330_STOCK_RUN_ID = P330_RUN_ID
P330_ADAPTER_SOURCE = Path(__file__).resolve()


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P329.acceptance_fixture())
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P330_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "preauth_diagnostics": {
                "frame_type": 0x86,
                "stages": ["open-parsed", "rng"],
                "eagain_only_retry": True,
            },
        }
    )
    if isinstance(value.get("observer_contract"), dict):
        value["observer_contract"] = dict(value["observer_contract"])
        value["observer_contract"]["id"] = OBSERVER_CONTRACT_ID
    for entry in value.get("contract", {}).values():
        if isinstance(entry, dict):
            entry["path"] = "p330-authenticated-diagnostic-udev-settle-v1-fixture"
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    value = dict(_P329.bind_exact_sources(auth_key))
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P330_RUN_ID_HEX,
            "predecessor_run_id_rejected": P329_PREDECESSOR_RUN_ID_HEX,
            "udev_guard_settle_bounded": True,
            "preauth_diagnostics_bounded": True,
        }
    )
    return value


def audit() -> dict[str, Any]:
    value = dict(_P329.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P330_STOCK_PROCESS_V2_ADAPTER_H0_DIAGNOSTIC_UDEV_SETTLE",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P329_PREDECESSOR_RUN_ID_HEX,
            "run_id": P330_RUN_ID_HEX,
            "encoder_failure_class": "P330_STOCK_ENCODER_FAILURE",
            "udev_guard_settle_bounded": True,
            "preauth_diagnostics_bounded": True,
            "lineage": bind_exact_sources(),
        }
    )
    return value


bind_lineage = bind_exact_sources
__all__ = [name for name in globals() if not name.startswith("_")]
