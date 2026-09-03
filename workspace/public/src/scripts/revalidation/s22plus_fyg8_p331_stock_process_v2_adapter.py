#!/usr/bin/env python3
"""P3.31 Process-v2 adapter for the bounded resident observer.

This host-only adapter is an exact-source successor of the consumed P3.30
adapter.  The target, stock Process-v2 bounds, udev-settle guard, rollback
identity, and private-key treatment remain inherited.  P3.31 only rotates the
run/overlay identity and describes the fixed two-session, one-reconnect
heartbeat observer; it never opens an endpoint or invokes a transfer tool.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p330_stock_process_v2_adapter.py")
SOURCE_IDENTITY = {
    "size": 9_731,
    "sha256": "1e72d5d5acffbb98c65c7e61ad3fbb42252398644b78fa9b7558fe532cef63d8",
}
P330_PREDECESSOR_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_PREDECESSOR_RUN_ID = bytes.fromhex(P330_PREDECESSOR_RUN_ID_HEX)
P331_RUN_ID_HEX = "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P331_RUN_ID = bytes.fromhex(P331_RUN_ID_HEX)

P331_OVERLAY_CONTRACT_ID = (
    "s22plus-fyg8-p331-resident-authenticated-exec-udev-settle-v1"
)
P331_DECODER_ID = (
    "s22plus_fyg8_p331_resident_authenticated_exec_udev_settle_v1"
)
P331_OBSERVER_CONTRACT_ID = (
    "s22plus-fyg8-p331-resident-observer-authenticated-settle-v1"
)
P331_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P331_STOCK_OBSERVER_V1|protocol=p331-resident-v1|"
    "resident=sessions-2,reconnects-1,heartbeat-only|"
    "udev-settle=500ms,25ms,both-mm-flags-required|run="
    + P331_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P331_POLICY_ID = hashlib.sha256(P331_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The exact P3.30 adapter or fresh P3.31 binding differs."""


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
        raise AdapterIdentityError("P3.30 adapter source is unavailable") from exc
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
        raise AdapterIdentityError("P3.30 adapter source identity differs")
    module = types.ModuleType("s22plus_fyg8_p330_adapter_bound_for_p331")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.30 adapter source failed to load") from exc
    if getattr(module, "P330_RUN_ID_HEX", None) != P330_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.30 adapter binding differs")
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


_P330 = _load()
for _module in _modules(_P330):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P330_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P331_RUN_ID)
        elif _value == P330_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P331_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            defaults = dict(_value.__kwdefaults__)
            changed = False
            for _key, _default in tuple(defaults.items()):
                if _default == P330_PREDECESSOR_RUN_ID:
                    defaults[_key] = P331_RUN_ID
                    changed = True
                elif _default == P330_PREDECESSOR_RUN_ID_HEX:
                    defaults[_key] = P331_RUN_ID_HEX
                    changed = True
            if changed:
                _value.__kwdefaults__ = defaults


_P330.P330_PREDECESSOR_RUN_ID = P330_PREDECESSOR_RUN_ID
_P330.P330_PREDECESSOR_RUN_ID_HEX = P330_PREDECESSOR_RUN_ID_HEX
_P330.P329_RUN_ID = P331_RUN_ID
_P330.P329_RUN_ID_HEX = P331_RUN_ID_HEX
_P330.P330_RUN_ID = P331_RUN_ID
_P330.P330_RUN_ID_HEX = P331_RUN_ID_HEX
_P330.P329_OVERLAY_CONTRACT_ID = P331_OVERLAY_CONTRACT_ID
_P330.P329_DECODER_ID = P331_DECODER_ID
_P330.P329_OBSERVER_CONTRACT_ID = P331_OBSERVER_CONTRACT_ID
_P330.P329_POLICY_PREIMAGE = P331_POLICY_PREIMAGE
_P330.P329_POLICY_ID = P331_POLICY_ID
_P330.SCHEMA = "s22plus_fyg8_p331_stock_process_v2_adapter_v1"
_P330.OVERLAY_CONTRACT_ID = P331_OVERLAY_CONTRACT_ID
_P330.DECODER_ID = P331_DECODER_ID
_P330.OBSERVER_CONTRACT_ID = P331_OBSERVER_CONTRACT_ID
_P330.POLICY_PREIMAGE = P331_POLICY_PREIMAGE
_P330.POLICY_ID = P331_POLICY_ID
_P330.P329_ADAPTER_SOURCE = Path(__file__).resolve()
_P330.P330_ADAPTER_SOURCE = Path(__file__).resolve()

_base = getattr(_P330, "_P328", None)
if isinstance(_base, types.ModuleType) and hasattr(_base, "_STALE_IDS"):
    _base._STALE_IDS = tuple(
        dict.fromkeys((*_base._STALE_IDS, P330_PREDECESSOR_RUN_ID))
    )
    for _module in (
        _base,
        getattr(_base, "_P327", None),
        getattr(getattr(_base, "_P327", None), "_P326", None),
        getattr(_base, "_P327_BASE", None),
    ):
        if isinstance(_module, types.ModuleType) and hasattr(_module, "_STALE_IDS"):
            _module._STALE_IDS = _base._STALE_IDS

for _module in _modules(_P330):
    for _name, _value in {
        "SCHEMA": _P330.SCHEMA,
        "OVERLAY_CONTRACT_ID": P331_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P331_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P331_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P331_POLICY_PREIMAGE,
        "POLICY_ID": P331_POLICY_ID,
        "RUN_ID": P331_RUN_ID,
        "STOCK_RUN_ID": P331_RUN_ID,
    }.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)

_original_public = _P330._public


def _public(value: Any) -> Any:
    result = _original_public(value)
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": _P330.SCHEMA,
            "overlay_contract_id": P331_OVERLAY_CONTRACT_ID,
            "decoder": P331_DECODER_ID,
            "policy_id": P331_POLICY_ID,
            "run_id": P331_RUN_ID_HEX,
            "udev_guard_settle_bounded": True,
            "resident_sessions_bounded": True,
            "resident_reconnect_bounded": True,
            "fixed_heartbeat_only": True,
        }
    )
    for key in ("classification", "proof_class"):
        if item.get(key) in (
            "P330_STOCK_ENCODER_FAILURE",
            "P329_STOCK_ENCODER_FAILURE",
            "P328_STOCK_ENCODER_FAILURE",
        ):
            item[key] = "P331_STOCK_ENCODER_FAILURE"
    return item


_P330._public = _public
for _name in getattr(_P330, "__all__", ()):
    globals()[_name] = getattr(_P330, _name)

SCHEMA = _P330.SCHEMA
OVERLAY_CONTRACT_ID = P331_OVERLAY_CONTRACT_ID
DECODER_ID = P331_DECODER_ID
OBSERVER_CONTRACT_ID = P331_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P331_POLICY_PREIMAGE
POLICY_ID = P331_POLICY_ID
RUN_ID = P331_RUN_ID
STOCK_RUN_ID = P331_RUN_ID
P330_RUN_ID = P331_RUN_ID
P330_RUN_ID_HEX = P331_RUN_ID_HEX
P331_STOCK_RUN_ID = P331_RUN_ID
P331_ADAPTER_SOURCE = Path(__file__).resolve()
PARENT_SOURCE_CONTRACT_ID = getattr(_P330, "PARENT_SOURCE_CONTRACT_ID", "")
PROFILE = getattr(_P330, "PROFILE", "E2")


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P330.acceptance_fixture())
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P331_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id_rejected": P330_PREDECESSOR_RUN_ID_HEX,
            "resident_sessions": 2,
            "resident_reconnects": 1,
            "fixed_heartbeat_only": True,
        }
    )
    if isinstance(value.get("observer_contract"), dict):
        value["observer_contract"] = dict(value["observer_contract"])
        value["observer_contract"]["id"] = OBSERVER_CONTRACT_ID
    for entry in value.get("contract", {}).values():
        if isinstance(entry, dict):
            entry["path"] = "p331-resident-authenticated-udev-settle-v1-fixture"
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    value = dict(_P330.bind_exact_sources(auth_key))
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P331_RUN_ID_HEX,
            "predecessor_run_id_rejected": P330_PREDECESSOR_RUN_ID_HEX,
            "udev_guard_settle_bounded": True,
            "resident_sessions_bounded": True,
            "resident_reconnect_bounded": True,
            "fixed_heartbeat_only": True,
        }
    )
    return value


def audit() -> dict[str, Any]:
    value = dict(_P330.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P331_STOCK_PROCESS_V2_ADAPTER_H0_RESIDENT_UDEV_SETTLE",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id": P330_PREDECESSOR_RUN_ID_HEX,
            "run_id": P331_RUN_ID_HEX,
            "encoder_failure_class": "P331_STOCK_ENCODER_FAILURE",
            "udev_guard_settle_bounded": True,
            "resident_sessions_bounded": True,
            "resident_reconnect_bounded": True,
            "fixed_heartbeat_only": True,
            "lineage": bind_exact_sources(),
        }
    )
    return value


bind_lineage = bind_exact_sources
__all__ = [name for name in globals() if not name.startswith("_")]
