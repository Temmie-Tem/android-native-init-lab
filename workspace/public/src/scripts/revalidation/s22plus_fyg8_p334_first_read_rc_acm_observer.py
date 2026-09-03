#!/usr/bin/env python3
"""P3.34 ACM observer: exact P3.33 protocol under the fresh run identity."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any

import s22plus_fyg8_p334_first_read_rc_runtime as runtime


SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py"
)
SOURCE_IDENTITY = {
    "size": 12_840,
    "sha256": "fbb0f2a2c8bf3f0dded26b18de5ce83bae8202e3426a049cf2be23379e79dcf3",
}
SCHEMA = "s22plus_fyg8_p334_first_read_rc_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p334-first-read-rc-acm-observer-v1"


class P334ObserverBindingError(ValueError):
    """The exact P3.33 observer could not be rebound to P3.34."""


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
        raise P334ObserverBindingError("P3.33 observer source is unavailable") from exc
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
        raise P334ObserverBindingError("P3.33 observer source identity differs")
    module = types.ModuleType("s22plus_fyg8_p333_observer_bound_for_p334")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    runtime_name = "s22plus_fyg8_p333_open_entry_diag_runtime"
    previous_runtime = sys.modules.get(runtime_name)
    previous_module = sys.modules.get(module.__name__)
    sys.modules[runtime_name] = runtime
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P334ObserverBindingError("P3.33 observer source failed to load") from exc
    finally:
        if previous_runtime is None:
            sys.modules.pop(runtime_name, None)
        else:
            sys.modules[runtime_name] = previous_runtime
        if previous_module is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous_module
    if (
        getattr(module, "P333_RUN_ID_HEX", None) != runtime.P334_RUN_ID_HEX
        or module.runtime is not runtime
    ):
        raise P334ObserverBindingError("P3.33 observer rebind differs")
    module.SCHEMA = SCHEMA
    module.CONTRACT_ID = CONTRACT_ID
    module.P334_RUN_ID_HEX = runtime.P334_RUN_ID_HEX
    module.P334_RUN_ID = runtime.P334_RUN_ID
    return module


_P333 = _load()
for _name in getattr(_P333, "__all__", ()):
    if hasattr(_P333, _name):
        globals()[_name] = getattr(_P333, _name)

SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py"
)
SOURCE_IDENTITY = {
    "size": 12_840,
    "sha256": "fbb0f2a2c8bf3f0dded26b18de5ce83bae8202e3426a049cf2be23379e79dcf3",
}
SCHEMA = "s22plus_fyg8_p334_first_read_rc_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p334-first-read-rc-acm-observer-v1"
P334_RUN_ID_HEX = runtime.P334_RUN_ID_HEX
P334_RUN_ID = runtime.P334_RUN_ID
P333_RUN_ID_HEX = P334_RUN_ID_HEX
P333_RUN_ID = P334_RUN_ID
P332_RUN_ID_HEX = P334_RUN_ID_HEX
P332_RUN_ID = P334_RUN_ID
P328_RUN_ID_HEX = P334_RUN_ID_HEX
P328_RUN_ID = P334_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
P334ObserverBindingError = P334ObserverBindingError


def audit_binding() -> dict[str, Any]:
    if (
        _P333.SCHEMA != SCHEMA
        or _P333.CONTRACT_ID != CONTRACT_ID
        or _P333.P333_RUN_ID_HEX != P334_RUN_ID_HEX
        or _P333.runtime is not runtime
        or DEVICE_BANNER != runtime.DEVICE_BANNER
        or DEFAULT_COMMANDS != tuple(runtime.DEFAULT_COMMANDS)
    ):
        raise P334ObserverBindingError("P3.34 observer binding differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P334_RUN_ID_HEX,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "stage0_retained": True,
        "first_console_return_is_checkpoint_only": True,
        "protocol_changed": False,
        "retry_added": False,
    }


__all__ = sorted(
    {name for name in getattr(_P333, "__all__", ()) if name in globals()}
    | {
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P334ObserverBindingError",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "audit_binding",
        "identity",
    }
)
