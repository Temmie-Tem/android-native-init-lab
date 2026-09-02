#!/usr/bin/env python3
"""P3.29 host codec over the unchanged authenticated P3.28 wire protocol."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any

import s22plus_fyg8_p329_auth_exec_runtime as runtime


SOURCE = Path(__file__).with_name("s22plus_fyg8_p328_auth_acm_observer.py")
SOURCE_IDENTITY = {
    "size": 18_326,
    "sha256": "2ec10d550b575f69f91f2424d9a605b5635ed9d5a853b59bb24563c85c6a9e25",
}
SCHEMA = "s22plus_fyg8_p329_auth_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p329-auth-acm-observer-v1"


class P329ObserverBindingError(ValueError):
    """The exact P3.28 codec source could not be rebound to P3.29."""


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
        raise P329ObserverBindingError("P3.28 observer source is unavailable") from exc
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
        raise P329ObserverBindingError("P3.28 observer source identity differs")
    module = types.ModuleType("s22plus_fyg8_p328_observer_bound_for_p329")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    key = "s22plus_fyg8_p328_auth_exec_runtime"
    module_key = module.__name__
    previous = sys.modules.get(key)
    previous_module = sys.modules.get(module_key)
    sys.modules[key] = runtime
    sys.modules[module_key] = module
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P329ObserverBindingError("P3.28 observer source failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = previous
        if previous_module is None:
            sys.modules.pop(module_key, None)
        else:
            sys.modules[module_key] = previous_module
    module.runtime = runtime
    module.DEFAULT_COMMANDS = runtime.DEFAULT_COMMANDS
    module.CONTRACT_ID = CONTRACT_ID
    module.SCHEMA = SCHEMA
    return module


_P328 = _load()
for _name in getattr(_P328, "__all__", ()):
    globals()[_name] = getattr(_P328, _name)

DEFAULT_COMMANDS = runtime.DEFAULT_COMMANDS
AuthObserverError = _P328.AuthObserverError
validate_p329_default_proof = _P328.validate_default_proof

__all__ = sorted(
    set(getattr(_P328, "__all__", ()))
    | {
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "P329ObserverBindingError",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "validate_p329_default_proof",
    }
)
