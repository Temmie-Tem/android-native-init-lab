#!/usr/bin/env python3
"""Fresh P3.29 artifact identity over the exact P3.28 helper.

The P3.28 authentication key and protocol bytes are reused.  The kernel
IKCONFIG/raw run identity and the userspace run identity are rotated so the
consumed P3.28 boot payload cannot be replayed as P3.29.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p328_artifact_identity.py")
SOURCE_IDENTITY = {
    "size": 11_503,
    "sha256": "e849578b1e7fcb9853ee0a07eaafb28922aa3e5f6b6f746851122f354cc00931",
}
P328_PREDECESSOR_RUN_ID_HEX = "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P328_PREDECESSOR_RUN_ID = bytes.fromhex(P328_PREDECESSOR_RUN_ID_HEX)
P329_RUN_ID_HEX = "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P329_RUN_ID = bytes.fromhex(P329_RUN_ID_HEX)


class ArtifactIdentityError(ValueError):
    """The exact P3.28 helper or the fresh P3.29 identity differs."""


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
        raise ArtifactIdentityError("P3.28 artifact helper is unavailable") from exc
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
        raise ArtifactIdentityError("P3.28 artifact helper identity differs")
    module = types.ModuleType("s22plus_fyg8_p328_artifact_bound_for_p329")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.28 artifact helper failed to load") from exc
    if getattr(module, "P328_RUN_ID_HEX", None) != P328_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.28 artifact helper binding differs")
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
            if name.startswith("_P") or name == "_INNER":
                if isinstance(value, types.ModuleType):
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

_original_reject_image = _P328._reject_stale_image_ids
_original_validate_init = _P328._validate_init


def _reject_stale_image_ids(image: bytes) -> None:
    _original_reject_image(image)
    try:
        start, end, _compressed, _config = _P328._INNER._gzip_config(
            image, "P329 Image"
        )
    except Exception:
        return
    outside = image[:start] + image[end:]
    if P328_PREDECESSOR_RUN_ID_HEX.encode("ascii") in outside:
        raise ArtifactIdentityError("P329 Image contains the consumed P328 run ID")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if P328_PREDECESSOR_RUN_ID in init:
        raise ArtifactIdentityError("P329 init contains the consumed P328 run ID")
    try:
        return _original_validate_init(init, expected_run_id)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_P328._reject_stale_image_ids = _reject_stale_image_ids
_P328._validate_init = _validate_init
_P328._INNER.validate_image = _P328.validate_image
_P328._INNER._validate_init = _validate_init

for _name in getattr(_P328, "__all__", ()):
    globals()[_name] = getattr(_P328, _name)

P328_RUN_ID_HEX = P329_RUN_ID_HEX
P328_RUN_ID = P329_RUN_ID
P329_ARTIFACT_SOURCE = Path(__file__).resolve()
DEFAULT_AUTH_KEY_PATH = _P328.DEFAULT_AUTH_KEY_PATH
AUTH_KEY_SCHEMA = _P328.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = _P328.AUTH_KEY_SIZE
AUTH_KEY_MODE = _P328.AUTH_KEY_MODE
read_auth_key = _P328.read_auth_key
auth_key_identity = _P328.auth_key_identity
validate_auth_key = _P328.validate_auth_key
transform_image = _P328.transform_image
validate_image = _P328.validate_image
inspect_ap = _P328.inspect_ap
validate_rollback_ap = _P328.validate_rollback_ap

__all__ = sorted(
    set(getattr(_P328, "__all__", ()))
    | {
        "P328_PREDECESSOR_RUN_ID",
        "P328_PREDECESSOR_RUN_ID_HEX",
        "P329_ARTIFACT_SOURCE",
        "P329_RUN_ID",
        "P329_RUN_ID_HEX",
        "SOURCE",
        "SOURCE_IDENTITY",
    }
)
