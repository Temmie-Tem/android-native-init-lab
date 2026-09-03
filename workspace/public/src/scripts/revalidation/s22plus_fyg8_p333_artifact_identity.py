#!/usr/bin/env python3
"""Fresh P3.33 Image/init/AP identity over the exact P3.32 helper."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p332_artifact_identity.py")
SOURCE_IDENTITY = {
    "size": 13_610,
    "sha256": "1b83ac1215bc5fafbaef44522695e87f5f4f1c558d16cfd39248e2d056c5804a",
}
P332_PREDECESSOR_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_PREDECESSOR_RUN_ID = bytes.fromhex(P332_PREDECESSOR_RUN_ID_HEX)
P333_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_RUN_ID = bytes.fromhex(P333_RUN_ID_HEX)
P332_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "e1309080879700445b88cef08eb3becb4e57e524f5467979857fc79ee36a9a9d",
}


class ArtifactIdentityError(ValueError):
    """The P3.32 helper or fresh P3.33 identity differs."""


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
        raise ArtifactIdentityError("P3.32 artifact helper is unavailable") from exc
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
        raise ArtifactIdentityError("P3.32 artifact helper identity differs")
    module = types.ModuleType("s22plus_fyg8_p332_artifact_bound_for_p333")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.32 artifact helper failed to load") from exc
    if getattr(module, "P332_RUN_ID_HEX", None) != P332_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.32 artifact binding differs")
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

_BASE = _P332._BASE
_ORIGINAL_REJECT_IMAGE = _BASE._reject_stale_image_ids
_ORIGINAL_VALIDATE_INIT = _BASE._validate_init


def _reject_stale_image_ids(image: bytes) -> None:
    _ORIGINAL_REJECT_IMAGE(image)
    try:
        start, end, _compressed, _config = _BASE._INNER._gzip_config(
            image, "P333 Image"
        )
    except Exception:
        return
    if P332_PREDECESSOR_RUN_ID_HEX.encode() in image[:start] + image[end:]:
        raise ArtifactIdentityError("P3.33 Image contains the P3.32 run ID")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P333_RUN_ID:
        raise ArtifactIdentityError("P3.33 init run ID differs")
    if P332_PREDECESSOR_RUN_ID in init:
        raise ArtifactIdentityError("P3.33 init contains the P3.32 run ID")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P333_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_BASE._reject_stale_image_ids = _reject_stale_image_ids
_BASE._validate_init = _validate_init
_BASE._INNER.validate_image = _BASE.validate_image
_BASE._INNER._validate_init = _validate_init
_P332.STALE_AP_IDENTITIES = tuple(
    (*_P332.STALE_AP_IDENTITIES, dict(P332_AP_IDENTITY))
)
for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P333_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P333_RUN_ID, "label": "P333 candidate AP"}),
    ("validate_rollback_ap", {"label": "P333 exact rollback AP"}),
):
    _function = getattr(_BASE._INNER, _function_name, None)
    if _function is not None:
        _defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
        _defaults.update(_updates)
        _function.__kwdefaults__ = _defaults

for _name in getattr(_P332, "__all__", ()):
    globals()[_name] = getattr(_P332, _name)

P332_RUN_ID_HEX = P333_RUN_ID_HEX
P332_RUN_ID = P333_RUN_ID
P333_ARTIFACT_SOURCE = Path(__file__).resolve()
P332_ARTIFACT_SOURCE = P333_ARTIFACT_SOURCE
STALE_AP_IDENTITIES = _P332.STALE_AP_IDENTITIES


def validate_image(
    image: bytes, *, expected_run_id: bytes = P333_RUN_ID
) -> dict[str, Any]:
    if expected_run_id != P333_RUN_ID:
        raise ArtifactIdentityError("P3.33 Image run ID differs")
    try:
        return _P332.validate_image(image, expected_run_id=P333_RUN_ID)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        transformed, receipt = _P332.transform_image(original)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P333_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.33 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P333_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P333 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P333_RUN_ID:
        raise ArtifactIdentityError("P3.33 AP run ID differs")
    try:
        return _P332.inspect_ap(
            ap_path,
            expected_run_id=P333_RUN_ID,
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
    label: str = "P333 exact rollback AP",
) -> dict[str, Any]:
    if dict(expected) == P332_AP_IDENTITY:
        raise ArtifactIdentityError("P3.32 candidate AP is not rollback")
    try:
        return _P332.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_p333_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p333_artifact_identity_v1",
        "run_id_hex": P333_RUN_ID_HEX,
        "predecessor_run_id_rejected": P332_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P332_AP_IDENTITY),
        "boot_only": True,
        "ab_must_match": True,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key_size": AUTH_KEY_SIZE,
        "auth_key_path_published": False,
    }


__all__ = sorted(
    set(getattr(_P332, "__all__", ()))
    | {
        "ArtifactIdentityError",
        "P332_AP_IDENTITY",
        "P332_ARTIFACT_SOURCE",
        "P332_PREDECESSOR_RUN_ID",
        "P332_PREDECESSOR_RUN_ID_HEX",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P333_ARTIFACT_SOURCE",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STALE_AP_IDENTITIES",
        "inspect_ap",
        "transform_image",
        "validate_image",
        "validate_p333_identity",
        "validate_rollback_ap",
    }
)
