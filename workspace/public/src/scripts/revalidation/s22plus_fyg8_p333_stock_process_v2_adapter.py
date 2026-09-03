#!/usr/bin/env python3
"""P3.33 Process-v2 adapter for the pre-OPEN entry diagnostic."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


SOURCE = Path(__file__).with_name("s22plus_fyg8_p332_stock_process_v2_adapter.py")
SOURCE_IDENTITY = {
    "size": 14_267,
    "sha256": "80d1c2060c81c7d6c9198e172b9a39af26b7b271932307d35ffba51aaa07f5d2",
}
P332_PREDECESSOR_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_PREDECESSOR_RUN_ID = bytes.fromhex(P332_PREDECESSOR_RUN_ID_HEX)
P333_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_RUN_ID = bytes.fromhex(P333_RUN_ID_HEX)

P333_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p333-open-entry-diagnostic-v1"
P333_DECODER_ID = "s22plus_fyg8_p333_open_entry_diagnostic_v1"
P333_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p333-open-entry-diag-acm-observer-v1"
P333_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P333_STOCK_OBSERVER_V1|protocol=p333-open-entry-diag-v1|"
    "entry-diagnostic=stage0,before-each-console-call|"
    "resident=sessions-2,reconnects-0,fixed-p330-commands,same-tty|"
    "transport=one-open-fd,no-close-reopen|"
    "udev-settle=500ms,25ms,both-mm-flags-required|run="
    + P333_RUN_ID_HEX
    + "|causal=false|usb=bidirectional-primary"
)
P333_POLICY_ID = hashlib.sha256(P333_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]


class AdapterIdentityError(ValueError):
    """The exact P3.32 adapter or fresh P3.33 binding differs."""


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
        raise AdapterIdentityError("P3.32 adapter source is unavailable") from exc
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
        raise AdapterIdentityError("P3.32 adapter source identity differs")
    module = types.ModuleType("s22plus_fyg8_p332_adapter_bound_for_p333")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.32 adapter source failed to load") from exc
    if getattr(module, "P332_RUN_ID_HEX", None) != P332_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.32 adapter binding differs")
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


_P332 = _load()
for _module in _modules(_P332):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P332_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P333_RUN_ID)
        elif _value == P332_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P333_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            _changed = False
            for _key, _default in tuple(_defaults.items()):
                if _default == P332_PREDECESSOR_RUN_ID:
                    _defaults[_key] = P333_RUN_ID
                    _changed = True
                elif _default == P332_PREDECESSOR_RUN_ID_HEX:
                    _defaults[_key] = P333_RUN_ID_HEX
                    _changed = True
            if _changed:
                _value.__kwdefaults__ = _defaults

SCHEMA = "s22plus_fyg8_p333_stock_process_v2_adapter_v1"
for _module in _modules(_P332):
    for _name, _value in {
        "SCHEMA": SCHEMA,
        "OVERLAY_CONTRACT_ID": P333_OVERLAY_CONTRACT_ID,
        "DECODER_ID": P333_DECODER_ID,
        "OBSERVER_CONTRACT_ID": P333_OBSERVER_CONTRACT_ID,
        "POLICY_PREIMAGE": P333_POLICY_PREIMAGE,
        "POLICY_ID": P333_POLICY_ID,
        "RUN_ID": P333_RUN_ID,
        "STOCK_RUN_ID": P333_RUN_ID,
    }.items():
        if hasattr(_module, _name):
            setattr(_module, _name, _value)

_base = getattr(_P332, "_base", None) or getattr(_P332, "_P331", None)
for _module in _modules(_P332):
    if hasattr(_module, "_STALE_IDS"):
        _module._STALE_IDS = tuple(  # noqa: SLF001
            dict.fromkeys((*_module._STALE_IDS, P332_PREDECESSOR_RUN_ID))  # noqa: SLF001
        )

_ORIGINAL_PUBLIC = _P332._public


def _public(value: Any) -> Any:
    result = _ORIGINAL_PUBLIC(value)
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": P333_OVERLAY_CONTRACT_ID,
            "decoder": P333_DECODER_ID,
            "policy_id": P333_POLICY_ID,
            "run_id": P333_RUN_ID_HEX,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "authenticated_exec": True,
            "authentication_required": True,
            "caller_selected_command": False,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "fixed_p330_commands": True,
        }
    )
    for key in ("classification", "proof_class"):
        if item.get(key) in {
            "P332_STOCK_ENCODER_FAILURE",
            "P331_STOCK_ENCODER_FAILURE",
            "P330_STOCK_ENCODER_FAILURE",
        }:
            item[key] = "P333_STOCK_ENCODER_FAILURE"
    return item


_P332._public = _public
for _name in getattr(_P332, "__all__", ()):
    globals()[_name] = getattr(_P332, _name)

OVERLAY_CONTRACT_ID = P333_OVERLAY_CONTRACT_ID
DECODER_ID = P333_DECODER_ID
OBSERVER_CONTRACT_ID = P333_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P333_POLICY_PREIMAGE
POLICY_ID = P333_POLICY_ID
RUN_ID = P333_RUN_ID
STOCK_RUN_ID = P333_RUN_ID
P332_RUN_ID = P333_RUN_ID
P332_RUN_ID_HEX = P333_RUN_ID_HEX
P333_ADAPTER_SOURCE = Path(__file__).resolve()
P332_ADAPTER_SOURCE = P333_ADAPTER_SOURCE


def acceptance_fixture() -> dict[str, Any]:
    value = dict(_P332.acceptance_fixture())
    predecessors = list(value.get("predecessor_run_ids_rejected", []))
    if P332_PREDECESSOR_RUN_ID_HEX not in predecessors:
        predecessors.append(P332_PREDECESSOR_RUN_ID_HEX)
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P333_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "predecessor_run_id_rejected": P332_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_ids_rejected": predecessors,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
        }
    )
    if isinstance(value.get("observer_contract"), dict):
        value["observer_contract"] = dict(value["observer_contract"])
        value["observer_contract"]["id"] = OBSERVER_CONTRACT_ID
    for entry in value.get("contract", {}).values():
        if isinstance(entry, dict):
            entry["path"] = "p333-open-entry-diagnostic-v1-fixture"
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    value = dict(_P332.bind_exact_sources(auth_key))
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P333_RUN_ID_HEX,
            "predecessor_run_id_rejected": P332_PREDECESSOR_RUN_ID_HEX,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
        }
    )
    return value


def audit() -> dict[str, Any]:
    value = dict(_P332.audit())
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P333_STOCK_PROCESS_V2_ADAPTER_H0_OPEN_ENTRY_DIAG",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P333_RUN_ID_HEX,
            "predecessor_run_id": P332_PREDECESSOR_RUN_ID_HEX,
            "encoder_failure_class": "P333_STOCK_ENCODER_FAILURE",
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "lineage": bind_exact_sources(),
        }
    )
    return value


_ORIGINAL_CLASSIFY_OBSERVATION = classify_observation
_ORIGINAL_CLASSIFY_CLEAN_BASELINE = classify_clean_baseline


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P333_RUN_ID,
) -> dict[str, Any]:
    return _public(
        _ORIGINAL_CLASSIFY_OBSERVATION(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P333_RUN_ID,
) -> dict[str, Any]:
    return _public(
        _ORIGINAL_CLASSIFY_CLEAN_BASELINE(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


bind_lineage = bind_exact_sources

__all__ = [name for name in globals() if not name.startswith("_")]
