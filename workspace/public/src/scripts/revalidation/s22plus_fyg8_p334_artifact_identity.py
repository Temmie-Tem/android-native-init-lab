#!/usr/bin/env python3
"""Fresh P3.34 Image/init/AP identity over the exact P3.33 helper."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p333_artifact_identity.py")
SOURCE_IDENTITY = {
    "size": 9_402,
    "sha256": "a8d710a8209ce6c27ab3ab6db8910ed2721d75dbb303c6c40921a11120195735",
}
P333_PREDECESSOR_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_PREDECESSOR_RUN_ID = bytes.fromhex(P333_PREDECESSOR_RUN_ID_HEX)
P334_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_RUN_ID = bytes.fromhex(P334_RUN_ID_HEX)
P333_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "1a6036b688ae92c94f459aee66e06a817e767aa615c6a7a9cb2a22b7d13487b3",
}


class ArtifactIdentityError(ValueError):
    """The P3.33 helper or fresh P3.34 identity differs."""


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
        raise ArtifactIdentityError("P3.33 artifact helper is unavailable") from exc
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
        raise ArtifactIdentityError("P3.33 artifact helper identity differs")
    module = types.ModuleType("s22plus_fyg8_p333_artifact_bound_for_p334")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.33 artifact helper failed to load") from exc
    if getattr(module, "P333_RUN_ID_HEX", None) != P333_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.33 artifact binding differs")
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


_P333 = _load()
for _module in _modules(_P333):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P333_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P334_RUN_ID)
        elif _value == P333_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P334_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            _changed = False
            for _key, _default in tuple(_defaults.items()):
                if _default == P333_PREDECESSOR_RUN_ID:
                    _defaults[_key] = P334_RUN_ID
                    _changed = True
                elif _default == P333_PREDECESSOR_RUN_ID_HEX:
                    _defaults[_key] = P334_RUN_ID_HEX
                    _changed = True
            if _changed:
                _value.__kwdefaults__ = _defaults

_BASE = _P333._BASE
_ORIGINAL_REJECT_IMAGE = _BASE._reject_stale_image_ids
_ORIGINAL_VALIDATE_INIT = _BASE._validate_init


def _reject_stale_image_ids(image: bytes) -> None:
    _ORIGINAL_REJECT_IMAGE(image)
    try:
        start, end, _compressed, _config = _BASE._INNER._gzip_config(
            image, "P334 Image"
        )
    except Exception:
        return
    if P333_PREDECESSOR_RUN_ID_HEX.encode() in image[:start] + image[end:]:
        raise ArtifactIdentityError("P3.34 Image contains the P3.33 run ID")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P334_RUN_ID:
        raise ArtifactIdentityError("P3.34 init run ID differs")
    if P333_PREDECESSOR_RUN_ID in init:
        raise ArtifactIdentityError("P3.34 init contains the P3.33 run ID")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P334_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_BASE._reject_stale_image_ids = _reject_stale_image_ids
_BASE._validate_init = _validate_init
_BASE._INNER.validate_image = _BASE.validate_image
_BASE._INNER._validate_init = _validate_init
_P333.STALE_AP_IDENTITIES = tuple(
    (*_P333.STALE_AP_IDENTITIES, dict(P333_AP_IDENTITY))
)
for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P334_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P334_RUN_ID, "label": "P334 candidate AP"}),
    ("validate_rollback_ap", {"label": "P334 exact rollback AP"}),
):
    _function = getattr(_BASE._INNER, _function_name, None)
    if _function is not None:
        _defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
        _defaults.update(_updates)
        _function.__kwdefaults__ = _defaults

for _name in getattr(_P333, "__all__", ()):
    globals()[_name] = getattr(_P333, _name)

SOURCE = Path(__file__).with_name("s22plus_fyg8_p333_artifact_identity.py")
SOURCE_IDENTITY = {
    "size": 9_402,
    "sha256": "a8d710a8209ce6c27ab3ab6db8910ed2721d75dbb303c6c40921a11120195735",
}
P333_RUN_ID_HEX = P334_RUN_ID_HEX
P333_RUN_ID = P334_RUN_ID
P334_ARTIFACT_SOURCE = Path(__file__).resolve()
P333_ARTIFACT_SOURCE = P334_ARTIFACT_SOURCE
STALE_AP_IDENTITIES = _P333.STALE_AP_IDENTITIES


def validate_image(
    image: bytes, *, expected_run_id: bytes = P334_RUN_ID
) -> dict[str, Any]:
    if expected_run_id != P334_RUN_ID:
        raise ArtifactIdentityError("P3.34 Image run ID differs")
    try:
        return _P333.validate_image(image, expected_run_id=P334_RUN_ID)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        transformed, receipt = _P333.transform_image(original)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P334_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.34 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P334_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P334 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P334_RUN_ID:
        raise ArtifactIdentityError("P3.34 AP run ID differs")
    try:
        return _P333.inspect_ap(
            ap_path,
            expected_run_id=P334_RUN_ID,
            expected_image=expected_image,
            expected_init=expected_init,
            expected_child=expected_child,
            expected_ap=expected_ap,
            label=label,
        )
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_rollback_ap(
    ap_path: Path,
    expected: Mapping[str, Any],
    *,
    label: str = "P334 exact rollback AP",
) -> dict[str, Any]:
    if dict(expected) == P333_AP_IDENTITY:
        raise ArtifactIdentityError("P3.33 candidate AP is not rollback")
    try:
        return _P333.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_p334_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p334_artifact_identity_v1",
        "run_id_hex": P334_RUN_ID_HEX,
        "predecessor_run_id_rejected": P333_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P333_AP_IDENTITY),
        "boot_only": True,
        "ab_must_match": True,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key_size": AUTH_KEY_SIZE,
        "auth_key_path_published": False,
    }


__all__ = sorted(
    set(getattr(_P333, "__all__", ()))
    | {
        "ArtifactIdentityError",
        "P333_AP_IDENTITY",
        "P333_ARTIFACT_SOURCE",
        "P333_PREDECESSOR_RUN_ID",
        "P333_PREDECESSOR_RUN_ID_HEX",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "P334_ARTIFACT_SOURCE",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STALE_AP_IDENTITIES",
        "inspect_ap",
        "transform_image",
        "validate_image",
        "validate_p334_identity",
        "validate_rollback_ap",
    }
)
