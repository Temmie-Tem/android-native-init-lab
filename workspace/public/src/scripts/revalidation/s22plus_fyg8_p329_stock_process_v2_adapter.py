#!/usr/bin/env python3
"""P3.29 Process-v2 adapter with a fresh run and bounded udev settle."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p328_stock_process_v2_adapter.py")
SOURCE_IDENTITY = {
    "size": 15_396,
    "sha256": "e0339f87daea4c911e999f07b769fc258ff7908ba6e7341c7955d04e13c8e750",
}
P328_PREDECESSOR_RUN_ID_HEX = "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P328_PREDECESSOR_RUN_ID = bytes.fromhex(P328_PREDECESSOR_RUN_ID_HEX)
P329_RUN_ID_HEX = "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P329_RUN_ID = bytes.fromhex(P329_RUN_ID_HEX)
P329_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p329-authenticated-exec-udev-settle-v1"
P329_DECODER_ID = "s22plus_fyg8_p329_authenticated_exec_udev_settle_v1"
P329_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p329-observer-authenticated-settle-v1"
P329_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P329_STOCK_OBSERVER_V1|protocol=p328-auth-v1|"
    "udev-settle=500ms,25ms,both-mm-flags-required|run="
    + P329_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P329_POLICY_ID = hashlib.sha256(P329_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The exact P3.28 adapter or fresh P3.29 binding differs."""


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
        raise AdapterIdentityError("P3.28 adapter source is unavailable") from exc
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
        raise AdapterIdentityError("P3.28 adapter source identity differs")
    module = types.ModuleType("s22plus_fyg8_p328_adapter_bound_for_p329")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.28 adapter source failed to load") from exc
    if getattr(module, "P328_RUN_ID_HEX", None) != P328_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.28 adapter binding differs")
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


_P328 = _load()
for _module in _modules(_P328):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P328_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P329_RUN_ID)
        elif _value == P328_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P329_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            defaults = dict(_value.__kwdefaults__)
            for _key, _default in tuple(defaults.items()):
                if _default == P328_PREDECESSOR_RUN_ID:
                    defaults[_key] = P329_RUN_ID
                elif _default == P328_PREDECESSOR_RUN_ID_HEX:
                    defaults[_key] = P329_RUN_ID_HEX
            _value.__kwdefaults__ = defaults

_P328.P328_OVERLAY_CONTRACT_ID = P329_OVERLAY_CONTRACT_ID
_P328.P328_DECODER_ID = P329_DECODER_ID
_P328.P328_OBSERVER_CONTRACT_ID = P329_OBSERVER_CONTRACT_ID
_P328.P328_POLICY_PREIMAGE = P329_POLICY_PREIMAGE
_P328.P328_POLICY_ID = P329_POLICY_ID
_P328.SCHEMA = "s22plus_fyg8_p329_stock_process_v2_adapter_v1"
_P328.OVERLAY_CONTRACT_ID = P329_OVERLAY_CONTRACT_ID
_P328.DECODER_ID = P329_DECODER_ID
_P328.OBSERVER_CONTRACT_ID = P329_OBSERVER_CONTRACT_ID
_P328.POLICY_PREIMAGE = P329_POLICY_PREIMAGE
_P328.POLICY_ID = P329_POLICY_ID
_P328.P328_ADAPTER_SOURCE = Path(__file__).resolve()
_P328._STALE_IDS = tuple(dict.fromkeys((*_P328._STALE_IDS, P328_PREDECESSOR_RUN_ID)))
for _module in (_P328._P327, _P328._P327._P326, _P328._P327_BASE):
    _module._STALE_IDS = _P328._STALE_IDS
for _module in _modules(_P328):
    for _name, _value in {
        "SCHEMA": _P328.SCHEMA,
        "OVERLAY_CONTRACT_ID": P329_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P329_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P329_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P329_POLICY_PREIMAGE,
        "POLICY_ID": P329_POLICY_ID,
        "RUN_ID": P329_RUN_ID,
        "STOCK_RUN_ID": P329_RUN_ID,
    }.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)

_original_public = _P328._public


def _public(value: Any) -> Any:
    result = _original_public(value)
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": _P328.SCHEMA,
            "overlay_contract_id": P329_OVERLAY_CONTRACT_ID,
            "decoder": P329_DECODER_ID,
            "policy_id": P329_POLICY_ID,
            "run_id": P329_RUN_ID_HEX,
            "udev_guard_settle_bounded": True,
        }
    )
    for key in ("classification", "proof_class"):
        if item.get(key) == "P328_STOCK_ENCODER_FAILURE":
            item[key] = "P329_STOCK_ENCODER_FAILURE"
    return item


_P328._public = _public
for _name in getattr(_P328, "__all__", ()):
    globals()[_name] = getattr(_P328, _name)

SCHEMA = _P328.SCHEMA
OVERLAY_CONTRACT_ID = P329_OVERLAY_CONTRACT_ID
DECODER_ID = P329_DECODER_ID
OBSERVER_CONTRACT_ID = P329_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P329_POLICY_PREIMAGE
POLICY_ID = P329_POLICY_ID
RUN_ID = P329_RUN_ID
STOCK_RUN_ID = P329_RUN_ID
P328_RUN_ID = P329_RUN_ID
P328_RUN_ID_HEX = P329_RUN_ID_HEX
P329_STOCK_RUN_ID = P329_RUN_ID
P329_ADAPTER_SOURCE = Path(__file__).resolve()


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P328.acceptance_fixture())
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P329_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
        }
    )
    if isinstance(value.get("observer_contract"), dict):
        value["observer_contract"] = dict(value["observer_contract"])
        value["observer_contract"]["id"] = OBSERVER_CONTRACT_ID
    for entry in value.get("contract", {}).values():
        if isinstance(entry, dict):
            entry["path"] = "p329-authenticated-udev-settle-v1-fixture"
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    value = dict(_P328.bind_exact_sources(auth_key))
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P329_RUN_ID_HEX,
            "predecessor_run_id_rejected": P328_PREDECESSOR_RUN_ID_HEX,
            "udev_guard_settle_bounded": True,
        }
    )
    return value


def audit() -> dict[str, Any]:
    value = dict(_P328.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P329_STOCK_PROCESS_V2_ADAPTER_H0_UDEV_SETTLE",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P328_PREDECESSOR_RUN_ID_HEX,
            "run_id": P329_RUN_ID_HEX,
            "encoder_failure_class": "P329_STOCK_ENCODER_FAILURE",
            "udev_guard_settle_bounded": True,
            "lineage": bind_exact_sources(),
        }
    )
    return value


bind_lineage = bind_exact_sources
__all__ = [name for name in globals() if not name.startswith("_")]
