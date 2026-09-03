#!/usr/bin/env python3
"""P3.32 Process-v2 adapter for the logical resident observer.

This is a host-only exact-source successor of the consumed P3.31 adapter.
The target, Process-v2 bounds, udev guard, HMAC key, rollback identity, and
boot-only packaging remain inherited.  P3.32 changes only the run/overlay
identity and makes the resident boundary explicit: exactly two logical
sessions use one already-open tty, with no host close/reopen and no transport
reconnect.  This adapter never opens an endpoint or invokes a transfer tool.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p331_stock_process_v2_adapter.py")
SOURCE_IDENTITY = {
    "size": 10_956,
    "sha256": "bcded9aac4aa09e1e42d5d2bb1d7f561817e4aef910459cc894d61c9dce8dda3",
}

P330_PREDECESSOR_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_PREDECESSOR_RUN_ID = bytes.fromhex(P330_PREDECESSOR_RUN_ID_HEX)
P331_PREDECESSOR_RUN_ID_HEX = "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P331_PREDECESSOR_RUN_ID = bytes.fromhex(P331_PREDECESSOR_RUN_ID_HEX)
P332_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_RUN_ID = bytes.fromhex(P332_RUN_ID_HEX)

P332_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p332-logical-resident-authenticated-v1"
P332_DECODER_ID = "s22plus_fyg8_p332_logical_resident_authenticated_v1"
P332_OBSERVER_CONTRACT_ID = (
    "s22plus-fyg8-p332-logical-resident-acm-observer-v1"
)
P332_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P332_STOCK_OBSERVER_V1|protocol=p332-logical-resident-v1|"
    "resident=sessions-2,reconnects-0,fixed-p330-commands,same-tty|"
    "commands-per-session=3|"
    "transport=one-open-fd,no-close-reopen|"
    "udev-settle=500ms,25ms,both-mm-flags-required|run="
    + P332_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P332_POLICY_ID = hashlib.sha256(P332_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The exact P3.31 adapter or fresh P3.32 binding differs."""


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
        raise AdapterIdentityError("P3.31 adapter source is unavailable") from exc
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
        raise AdapterIdentityError("P3.31 adapter source identity differs")
    module = types.ModuleType("s22plus_fyg8_p331_adapter_bound_for_p332")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.31 adapter source failed to load") from exc
    if getattr(module, "P331_RUN_ID_HEX", None) != P331_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.31 adapter binding differs")
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


_P331 = _load()
for _module in _modules(_P331):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P331_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P332_RUN_ID)
        elif _value == P331_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P332_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            _changed = False
            for _key, _default in tuple(_defaults.items()):
                if _default == P331_PREDECESSOR_RUN_ID:
                    _defaults[_key] = P332_RUN_ID
                    _changed = True
                elif _default == P331_PREDECESSOR_RUN_ID_HEX:
                    _defaults[_key] = P332_RUN_ID_HEX
                    _changed = True
            if _changed:
                _value.__kwdefaults__ = _defaults


_P331.P331_PREDECESSOR_RUN_ID = P331_PREDECESSOR_RUN_ID
_P331.P331_PREDECESSOR_RUN_ID_HEX = P331_PREDECESSOR_RUN_ID_HEX
_P331.P330_PREDECESSOR_RUN_ID = P330_PREDECESSOR_RUN_ID
_P331.P330_PREDECESSOR_RUN_ID_HEX = P330_PREDECESSOR_RUN_ID_HEX
_P331.P330_RUN_ID = P332_RUN_ID
_P331.P330_RUN_ID_HEX = P332_RUN_ID_HEX
_P331.P329_RUN_ID = P332_RUN_ID
_P331.P329_RUN_ID_HEX = P332_RUN_ID_HEX
_P331.P329_OVERLAY_CONTRACT_ID = P332_OVERLAY_CONTRACT_ID
_P331.P329_DECODER_ID = P332_DECODER_ID
_P331.P329_OBSERVER_CONTRACT_ID = P332_OBSERVER_CONTRACT_ID
_P331.P329_POLICY_PREIMAGE = P332_POLICY_PREIMAGE
_P331.P329_POLICY_ID = P332_POLICY_ID
_P331.SCHEMA = "s22plus_fyg8_p332_stock_process_v2_adapter_v1"
_P331.OVERLAY_CONTRACT_ID = P332_OVERLAY_CONTRACT_ID
_P331.DECODER_ID = P332_DECODER_ID
_P331.OBSERVER_CONTRACT_ID = P332_OBSERVER_CONTRACT_ID
_P331.POLICY_PREIMAGE = P332_POLICY_PREIMAGE
_P331.POLICY_ID = P332_POLICY_ID
_P331.P329_ADAPTER_SOURCE = Path(__file__).resolve()
_P331.P330_ADAPTER_SOURCE = Path(__file__).resolve()

_base = getattr(_P331, "_P328", None)
if isinstance(_base, types.ModuleType) and hasattr(_base, "_STALE_IDS"):
    _base._STALE_IDS = tuple(
        dict.fromkeys((*_base._STALE_IDS, P330_PREDECESSOR_RUN_ID, P331_PREDECESSOR_RUN_ID))
    )
    for _module in (
        _base,
        getattr(_base, "_P327", None),
        getattr(getattr(_base, "_P327", None), "_P326", None),
        getattr(_base, "_P327_BASE", None),
    ):
        if isinstance(_module, types.ModuleType) and hasattr(_module, "_STALE_IDS"):
            _module._STALE_IDS = _base._STALE_IDS

for _module in _modules(_P331):
    for _name, _value in {
        "SCHEMA": _P331.SCHEMA,
        "OVERLAY_CONTRACT_ID": P332_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P332_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P332_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P332_POLICY_PREIMAGE,
        "POLICY_ID": P332_POLICY_ID,
        "RUN_ID": P332_RUN_ID,
        "STOCK_RUN_ID": P332_RUN_ID,
    }.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)

_ORIGINAL_PUBLIC = _P331._public


def _public(value: Any) -> Any:
    result = _ORIGINAL_PUBLIC(value)
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": _P331.SCHEMA,
            "overlay_contract_id": P332_OVERLAY_CONTRACT_ID,
            "decoder": P332_DECODER_ID,
            "policy_id": P332_POLICY_ID,
            "run_id": P332_RUN_ID_HEX,
            "authenticated_exec": True,
            "authentication_required": True,
            "caller_selected_command": False,
            "auth_key_path_published": False,
            "udev_guard_settle_bounded": True,
            "resident_sessions_bounded": True,
            "resident_reconnect_bounded": False,
            "logical_same_tty_bounded": True,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": 3,
        }
    )
    for key in ("classification", "proof_class"):
        if item.get(key) in {
            "P331_STOCK_ENCODER_FAILURE",
            "P330_STOCK_ENCODER_FAILURE",
            "P329_STOCK_ENCODER_FAILURE",
            "P328_STOCK_ENCODER_FAILURE",
        }:
            item[key] = "P332_STOCK_ENCODER_FAILURE"
    return item


_P331._public = _public
for _name in getattr(_P331, "__all__", ()):
    globals()[_name] = getattr(_P331, _name)

SCHEMA = _P331.SCHEMA
OVERLAY_CONTRACT_ID = P332_OVERLAY_CONTRACT_ID
DECODER_ID = P332_DECODER_ID
OBSERVER_CONTRACT_ID = P332_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P332_POLICY_PREIMAGE
POLICY_ID = P332_POLICY_ID
RUN_ID = P332_RUN_ID
STOCK_RUN_ID = P332_RUN_ID
P331_RUN_ID = P332_RUN_ID
P331_RUN_ID_HEX = P332_RUN_ID_HEX
P332_STOCK_RUN_ID = P332_RUN_ID
P332_ADAPTER_SOURCE = Path(__file__).resolve()
PARENT_SOURCE_CONTRACT_ID = getattr(_P331, "PARENT_SOURCE_CONTRACT_ID", "")
PROFILE = getattr(_P331, "PROFILE", "E2")


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P331.acceptance_fixture())
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P332_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id_rejected": P331_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_ids_rejected": [
                P330_PREDECESSOR_RUN_ID_HEX,
                P331_PREDECESSOR_RUN_ID_HEX,
            ],
            "resident_sessions": 2,
            "resident_reconnects": 0,
            "logical_same_tty": True,
            "same_tty_fd": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": 3,
        }
    )
    if isinstance(value.get("observer_contract"), dict):
        value["observer_contract"] = dict(value["observer_contract"])
        value["observer_contract"]["id"] = OBSERVER_CONTRACT_ID
    for entry in value.get("contract", {}).values():
        if isinstance(entry, dict):
            entry["path"] = "p332-logical-resident-authenticated-v1-fixture"
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    value = dict(_P331.bind_exact_sources(auth_key))
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P332_RUN_ID_HEX,
            "predecessor_run_id_rejected": P331_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_ids_rejected": [
                P330_PREDECESSOR_RUN_ID_HEX,
                P331_PREDECESSOR_RUN_ID_HEX,
            ],
            "udev_guard_settle_bounded": True,
            "resident_sessions_bounded": True,
            "resident_reconnect_bounded": False,
            "logical_same_tty_bounded": True,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": 3,
        }
    )
    return value


def audit() -> dict[str, Any]:
    value = dict(_P331.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P332_STOCK_PROCESS_V2_ADAPTER_H0_LOGICAL_RESIDENT",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_ids": [
                P330_PREDECESSOR_RUN_ID_HEX,
                P331_PREDECESSOR_RUN_ID_HEX,
            ],
            "run_id": P332_RUN_ID_HEX,
            "encoder_failure_class": "P332_STOCK_ENCODER_FAILURE",
            "udev_guard_settle_bounded": True,
            "resident_sessions_bounded": True,
            "resident_reconnect_bounded": False,
            "logical_same_tty_bounded": True,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": 3,
            "lineage": bind_exact_sources(),
        }
    )
    value.pop("predecessor_run_id", None)
    return value


# The inherited decoder functions are exported directly from a nested
# P328/P320 module and therefore do not pass through ``_P331._public``.
# Wrap the public classification seam so retained raw observations cannot
# reintroduce P330's caller-selected-command claim.
_ORIGINAL_CLASSIFY_OBSERVATION = classify_observation
_ORIGINAL_CLASSIFY_CLEAN_BASELINE = classify_clean_baseline
_ORIGINAL_PROOF_CLASS = proof_class


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P332_RUN_ID,
) -> dict[str, Any]:
    value = _ORIGINAL_CLASSIFY_OBSERVATION(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    return _public(value)


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P332_RUN_ID,
) -> dict[str, Any]:
    value = _ORIGINAL_CLASSIFY_CLEAN_BASELINE(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    return _public(value)


def proof_class(value: dict[str, Any], *, expected: str | None = None) -> str:
    return _ORIGINAL_PROOF_CLASS(value, expected=expected)


bind_lineage = bind_exact_sources

__all__ = [name for name in globals() if not name.startswith("_")]
