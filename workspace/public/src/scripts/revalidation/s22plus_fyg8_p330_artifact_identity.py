#!/usr/bin/env python3
"""Fresh P3.30 boot/Image/AP identity and exact host auth-key binding.

The consumed P3.29 artifact helper is loaded from pinned source bytes.  Its
boot-only image transform, AP member grammar, rollback checks, and private
auth-key handling remain the implementation base; P3.30 rotates the run
identity and rejects the consumed P3.29 identity before any image is accepted.
This module performs host-only validation and never contacts a device or
invokes Odin.
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
SOURCE = REVALIDATION / "s22plus_fyg8_p329_artifact_identity.py"
SOURCE_IDENTITY = {
    "size": 6_077,
    "sha256": "4251bafc22db87846ddac24558d5c84a12eced56cc10cb70ee32e238cb1cf437",
}
P329_PREDECESSOR_RUN_ID_HEX = "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P329_PREDECESSOR_RUN_ID = bytes.fromhex(P329_PREDECESSOR_RUN_ID_HEX)
P330_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_RUN_ID = bytes.fromhex(P330_RUN_ID_HEX)


class ArtifactIdentityError(ValueError):
    """The exact P3.29 helper or fresh P3.30 identity is not available."""


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


def _stable_source(path: Path, label: str, expected: Mapping[str, Any]) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(int(expected["size"]) + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ArtifactIdentityError(f"{label} is unavailable") from exc
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
        raise ArtifactIdentityError(f"{label} identity differs")
    return payload


def _load() -> types.ModuleType:
    payload = _stable_source(SOURCE, "P3.29 artifact helper", SOURCE_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p329_artifact_bound_for_p330")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.29 artifact helper failed to load") from exc
    if getattr(module, "P329_RUN_ID_HEX", None) != P329_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.29 artifact identity differs")
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
            if (name.startswith("_P") or name == "_INNER") and isinstance(value, types.ModuleType):
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

_BASE = _P329._P328
_original_reject_image = _BASE._reject_stale_image_ids
_original_validate_init = _BASE._validate_init


def _reject_stale_image_ids(image: bytes) -> None:
    _original_reject_image(image)
    try:
        start, end, _compressed, _config = _BASE._INNER._gzip_config(image, "P330 Image")
    except Exception:
        return
    outside = image[:start] + image[end:]
    if P329_PREDECESSOR_RUN_ID_HEX.encode("ascii") in outside:
        raise ArtifactIdentityError("P330 Image contains the consumed P329 run ID")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P330_RUN_ID:
        raise ArtifactIdentityError("P330 init run ID differs")
    if P329_PREDECESSOR_RUN_ID in init:
        raise ArtifactIdentityError("P330 init contains the consumed P329 run ID")
    try:
        return _original_validate_init(init, P330_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_BASE._reject_stale_image_ids = _reject_stale_image_ids
_BASE._validate_init = _validate_init
_BASE._INNER.validate_image = _BASE.validate_image
_BASE._INNER._validate_init = _validate_init

for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P330_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P330_RUN_ID, "label": "P330 candidate AP"}),
    ("validate_rollback_ap", {"label": "P330 exact rollback AP"}),
):
    _function = getattr(_BASE._INNER, _function_name, None)
    if _function is not None:
        _defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
        _defaults.update(_updates)
        _function.__kwdefaults__ = _defaults

for _name in getattr(_BASE, "__all__", ()):
    globals()[_name] = getattr(_BASE, _name)

P329_RUN_ID_HEX = P330_RUN_ID_HEX
P329_RUN_ID = P330_RUN_ID
P330_ARTIFACT_SOURCE = Path(__file__).resolve()
P329_ARTIFACT_SOURCE = P330_ARTIFACT_SOURCE

DEFAULT_AUTH_KEY_PATH = _BASE.DEFAULT_AUTH_KEY_PATH
AUTH_KEY_SCHEMA = _BASE.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = _BASE.AUTH_KEY_SIZE
AUTH_KEY_MODE = _BASE.AUTH_KEY_MODE
read_auth_key = _BASE.read_auth_key
auth_key_identity = _BASE.auth_key_identity
validate_auth_key = _BASE.validate_auth_key
transform_image = _BASE.transform_image
validate_image = _BASE.validate_image
inspect_ap = _BASE.inspect_ap
validate_rollback_ap = _BASE.validate_rollback_ap


def validate_p330_identity() -> dict[str, Any]:
    """Return the path-free identity projection used by H0 callers."""

    return {
        "schema": "s22plus_fyg8_p330_artifact_identity_v1",
        "run_id_hex": P330_RUN_ID_HEX,
        "predecessor_run_id_rejected": P329_PREDECESSOR_RUN_ID_HEX,
        "boot_only": True,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key_size": AUTH_KEY_SIZE,
        "auth_key_path_published": False,
    }


__all__ = sorted(
    set(getattr(_BASE, "__all__", ()))
    | {
        "ArtifactIdentityError",
        "AUTH_KEY_MODE",
        "AUTH_KEY_SCHEMA",
        "AUTH_KEY_SIZE",
        "DEFAULT_AUTH_KEY_PATH",
        "P329_ARTIFACT_SOURCE",
        "P329_PREDECESSOR_RUN_ID",
        "P329_PREDECESSOR_RUN_ID_HEX",
        "P329_RUN_ID",
        "P329_RUN_ID_HEX",
        "P330_ARTIFACT_SOURCE",
        "P330_RUN_ID",
        "P330_RUN_ID_HEX",
        "SOURCE",
        "SOURCE_IDENTITY",
        "identity",
        "validate_p330_identity",
    }
)
