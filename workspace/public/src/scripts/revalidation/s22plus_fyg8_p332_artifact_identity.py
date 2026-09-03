#!/usr/bin/env python3
"""Fresh P3.32 boot/Image/AP identity and private-key binding.

P3.32 is a host-only logical-resident successor of the consumed P3.31
artifact helper.  The exact P3.31 helper is loaded from pinned bytes; its
boot-only Image transform, AP grammar, rollback checks, and private
authentication-key handling remain the implementation base.  P3.32 rotates
the run identity and rejects both consumed P3.30 and P3.31 candidate
identities before an Image or AP is accepted.
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
SOURCE = REVALIDATION / "s22plus_fyg8_p331_artifact_identity.py"
SOURCE_IDENTITY = {
    "size": 8_184,
    "sha256": "1a8d328cf6dac71e907381ce225c2d47f7e5f6de4c20f846cdbf63744a2d246b",
}

P330_PREDECESSOR_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_PREDECESSOR_RUN_ID = bytes.fromhex(P330_PREDECESSOR_RUN_ID_HEX)
P331_PREDECESSOR_RUN_ID_HEX = "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P331_PREDECESSOR_RUN_ID = bytes.fromhex(P331_PREDECESSOR_RUN_ID_HEX)
P332_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_RUN_ID = bytes.fromhex(P332_RUN_ID_HEX)

# Candidate AP identities are provenance guards, not new inputs.  A/B must
# be freshly built and identical to one another, while neither consumed AP
# may be accepted as the current candidate.
P330_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b",
}
P331_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "729b33c3bad602e1d5863fa8cfa6a4bdf22f194a74d378f7417879897bf4d08d",
}
STALE_AP_IDENTITIES = (P330_AP_IDENTITY, P331_AP_IDENTITY)


class ArtifactIdentityError(ValueError):
    """The exact P3.31 helper or fresh P3.32 identity is not available."""


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
    payload = _stable_source(SOURCE, "P3.31 artifact helper", SOURCE_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p331_artifact_bound_for_p332")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.31 artifact helper failed to load") from exc
    if getattr(module, "P331_RUN_ID_HEX", None) != P331_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.31 artifact identity differs")
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
            if (
                (name.startswith("_P") or name in {"_BASE", "_INNER"})
                and isinstance(value, types.ModuleType)
            ):
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


_BASE = _P331._BASE
_ORIGINAL_REJECT_IMAGE = _BASE._reject_stale_image_ids
_ORIGINAL_VALIDATE_INIT = _BASE._validate_init
_ORIGINAL_INSPECT_AP = _BASE.inspect_ap
_ORIGINAL_VALIDATE_ROLLBACK_AP = _BASE.validate_rollback_ap


def _reject_stale_image_ids(image: bytes) -> None:
    _ORIGINAL_REJECT_IMAGE(image)
    try:
        start, end, _compressed, _config = _BASE._INNER._gzip_config(image, "P332 Image")
    except Exception:
        return
    outside = image[:start] + image[end:]
    for old in (P330_PREDECESSOR_RUN_ID_HEX, P331_PREDECESSOR_RUN_ID_HEX):
        if old.encode("ascii") in outside:
            raise ArtifactIdentityError(f"P3.32 Image contains stale run ID {old}")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P332_RUN_ID:
        raise ArtifactIdentityError("P3.32 init run ID differs")
    for old in (P330_PREDECESSOR_RUN_ID, P331_PREDECESSOR_RUN_ID):
        if old in init:
            raise ArtifactIdentityError("P3.32 init contains a consumed predecessor run ID")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P332_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _read_ap_identity(ap_path: Path, label: str) -> dict[str, Any]:
    """Read a bounded AP receipt without invoking unpackers or device tools."""
    direct = Path(ap_path).absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(128 * 1024 * 1024 + 1)
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
        or len(payload) > 128 * 1024 * 1024
    ):
        raise ArtifactIdentityError(f"{label} identity differs")
    return identity(payload)


def _reject_stale_ap(ap_path: Path, label: str) -> dict[str, Any]:
    value = _read_ap_identity(ap_path, label)
    if value in STALE_AP_IDENTITIES:
        raise ArtifactIdentityError(f"{label} repeats a consumed P3.30/P3.31 AP")
    return value


_BASE._reject_stale_image_ids = _reject_stale_image_ids
_BASE._validate_init = _validate_init
_BASE._INNER.validate_image = _BASE.validate_image
_BASE._INNER._validate_init = _validate_init

for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P332_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P332_RUN_ID, "label": "P332 candidate AP"}),
    ("validate_rollback_ap", {"label": "P332 exact rollback AP"}),
):
    _function = getattr(_BASE._INNER, _function_name, None)
    if _function is not None:
        _defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
        _defaults.update(_updates)
        _function.__kwdefaults__ = _defaults


def validate_image(image: bytes, *, expected_run_id: bytes = P332_RUN_ID) -> dict[str, Any]:
    if expected_run_id != P332_RUN_ID:
        raise ArtifactIdentityError("P3.32 Image run ID differs")
    try:
        return _BASE.validate_image(image, expected_run_id=P332_RUN_ID)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        transformed, receipt = _BASE.transform_image(original)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P332_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.32 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P332_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P332 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P332_RUN_ID:
        raise ArtifactIdentityError("P3.32 AP run ID differs")
    current = _reject_stale_ap(ap_path, label)
    if expected_ap is not None and current != dict(expected_ap):
        raise ArtifactIdentityError(f"{label} AP identity differs")
    try:
        return _ORIGINAL_INSPECT_AP(
            ap_path,
            expected_run_id=P332_RUN_ID,
            expected_image=expected_image,
            expected_init=expected_init,
            expected_child=expected_child,
            expected_ap=expected_ap,
            label=label,
        )
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


def validate_rollback_ap(
    ap_path: Path,
    expected: Mapping[str, Any],
    *,
    label: str = "P332 exact rollback AP",
) -> dict[str, Any]:
    current = _reject_stale_ap(ap_path, label)
    if dict(expected) in STALE_AP_IDENTITIES or current in STALE_AP_IDENTITIES:
        raise ArtifactIdentityError(f"{label} is a consumed candidate AP")
    try:
        return _ORIGINAL_VALIDATE_ROLLBACK_AP(ap_path, expected, label=label)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


for _name in getattr(_BASE, "__all__", ()):
    if _name not in {"validate_image", "transform_image", "inspect_ap", "validate_rollback_ap"}:
        globals()[_name] = getattr(_BASE, _name)

DEFAULT_AUTH_KEY_PATH = _BASE.DEFAULT_AUTH_KEY_PATH
AUTH_KEY_SCHEMA = _BASE.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = _BASE.AUTH_KEY_SIZE
AUTH_KEY_MODE = _BASE.AUTH_KEY_MODE
read_auth_key = _BASE.read_auth_key
auth_key_identity = _BASE.auth_key_identity
validate_auth_key = _BASE.validate_auth_key

# The inherited engine uses compatibility names for its current run.  Keep
# explicit predecessor names above while exposing P332 names for callers.
P331_RUN_ID_HEX = P332_RUN_ID_HEX
P331_RUN_ID = P332_RUN_ID
P332_ARTIFACT_SOURCE = Path(__file__).resolve()
P331_ARTIFACT_SOURCE = P332_ARTIFACT_SOURCE
P331_PREDECESSOR_ARTIFACT_SOURCE = SOURCE
P330_ARTIFACT_SOURCE = getattr(_P331, "P330_ARTIFACT_SOURCE", SOURCE)


def validate_p332_identity() -> dict[str, Any]:
    """Return the path-free identity projection used by H0 callers."""

    return {
        "schema": "s22plus_fyg8_p332_artifact_identity_v1",
        "run_id_hex": P332_RUN_ID_HEX,
        "predecessor_run_ids_rejected": [
            P330_PREDECESSOR_RUN_ID_HEX,
            P331_PREDECESSOR_RUN_ID_HEX,
        ],
        "predecessor_ap_identities_rejected": [
            dict(P330_AP_IDENTITY),
            dict(P331_AP_IDENTITY),
        ],
        "boot_only": True,
        "ab_must_match": True,
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
        "P330_AP_IDENTITY",
        "P330_ARTIFACT_SOURCE",
        "P330_PREDECESSOR_RUN_ID",
        "P330_PREDECESSOR_RUN_ID_HEX",
        "P331_AP_IDENTITY",
        "P331_ARTIFACT_SOURCE",
        "P331_PREDECESSOR_ARTIFACT_SOURCE",
        "P331_PREDECESSOR_RUN_ID",
        "P331_PREDECESSOR_RUN_ID_HEX",
        "P331_RUN_ID",
        "P331_RUN_ID_HEX",
        "P332_ARTIFACT_SOURCE",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "ROOT",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STALE_AP_IDENTITIES",
        "auth_key_identity",
        "identity",
        "inspect_ap",
        "read_auth_key",
        "transform_image",
        "validate_auth_key",
        "validate_image",
        "validate_p332_identity",
        "validate_rollback_ap",
    }
)
