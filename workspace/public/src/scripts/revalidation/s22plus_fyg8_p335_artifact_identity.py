#!/usr/bin/env python3
"""Fresh P3.35 Image/init/AP identity over the exact P3.34 helper.

P3.35 keeps the existing boot-only packaging seam.  This module deliberately
loads the reviewed P3.34 helper from an isolated module graph and adds only
the new run identity and consumed-candidate rejection.  It does not contact a
device or publish an auth key.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p334_artifact_identity.py")
SOURCE_IDENTITY = {
    "size": 9_600,
    "sha256": "9beaccfb9c7843e1afc96d5955f125d9b30ff30652b784768e98436ffb4bca22",
}
P334_PREDECESSOR_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_PREDECESSOR_RUN_ID = bytes.fromhex(P334_PREDECESSOR_RUN_ID_HEX)
P335_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P335_RUN_ID = bytes.fromhex(P335_RUN_ID_HEX)
P334_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc",
}


class ArtifactIdentityError(ValueError):
    """The P3.34 helper or fresh P3.35 identity differs."""


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


def _stable_source() -> bytes:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ArtifactIdentityError("P3.34 artifact helper is unavailable") from exc
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
        raise ArtifactIdentityError("P3.34 artifact helper identity differs")
    return payload


def _load_p334() -> types.ModuleType:
    payload = _stable_source()
    module = types.ModuleType("s22plus_fyg8_p334_artifact_bound_for_p335")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.34 artifact helper failed to load") from exc
    if getattr(module, "P334_RUN_ID_HEX", None) != P334_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.34 artifact binding differs")
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


_P334 = _load_p334()
for _module in _modules(_P334):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P334_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P335_RUN_ID)
        elif _value == P334_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P335_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            _changed = False
            for _key, _default in tuple(_defaults.items()):
                if _default == P334_PREDECESSOR_RUN_ID:
                    _defaults[_key] = P335_RUN_ID
                    _changed = True
                elif _default == P334_PREDECESSOR_RUN_ID_HEX:
                    _defaults[_key] = P335_RUN_ID_HEX
                    _changed = True
            if _changed:
                _value.__kwdefaults__ = _defaults


_BASE = _P334._BASE
_ORIGINAL_REJECT_IMAGE = _BASE._reject_stale_image_ids
_ORIGINAL_VALIDATE_INIT = _BASE._validate_init


def _reject_stale_image_ids(image: bytes) -> None:
    _ORIGINAL_REJECT_IMAGE(image)
    try:
        start, end, _compressed, _config = _BASE._INNER._gzip_config(
            image, "P335 Image"
        )
    except Exception:
        return
    if P334_PREDECESSOR_RUN_ID_HEX.encode() in image[:start] + image[end:]:
        raise ArtifactIdentityError("P3.35 Image contains the P3.34 run ID")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P335_RUN_ID:
        raise ArtifactIdentityError("P3.35 init run ID differs")
    if P334_PREDECESSOR_RUN_ID in init:
        raise ArtifactIdentityError("P3.35 init contains the P3.34 run ID")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P335_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_BASE._reject_stale_image_ids = _reject_stale_image_ids
_BASE._validate_init = _validate_init
_BASE._INNER.validate_image = _BASE.validate_image
_BASE._INNER._validate_init = _validate_init
_P334.STALE_AP_IDENTITIES = tuple(
    (*_P334.STALE_AP_IDENTITIES, dict(P334_AP_IDENTITY))
)
for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P335_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P335_RUN_ID, "label": "P335 candidate AP"}),
    ("validate_rollback_ap", {"label": "P335 exact rollback AP"}),
):
    _function = getattr(_BASE._INNER, _function_name, None)
    if _function is not None:
        _defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
        _defaults.update(_updates)
        _function.__kwdefaults__ = _defaults


for _name in getattr(_P334, "__all__", ()):
    if hasattr(_P334, _name):
        globals()[_name] = getattr(_P334, _name)

# Re-pin names after inherited __all__ projection.  P334's inherited aliases
# are compatibility labels only; they must never become P335 authority.
SOURCE = Path(__file__).with_name("s22plus_fyg8_p334_artifact_identity.py")
SOURCE_IDENTITY = {
    "size": 9_600,
    "sha256": "9beaccfb9c7843e1afc96d5955f125d9b30ff30652b784768e98436ffb4bca22",
}
P334_RUN_ID_HEX = P335_RUN_ID_HEX
P334_RUN_ID = P335_RUN_ID
P335_ARTIFACT_SOURCE = Path(__file__).resolve()
P334_ARTIFACT_SOURCE = P335_ARTIFACT_SOURCE
STALE_AP_IDENTITIES = _P334.STALE_AP_IDENTITIES


def validate_image(
    image: bytes, *, expected_run_id: bytes = P335_RUN_ID
) -> dict[str, Any]:
    if expected_run_id != P335_RUN_ID:
        raise ArtifactIdentityError("P3.35 Image run ID differs")
    try:
        return _P334.validate_image(image, expected_run_id=P335_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        transformed, receipt = _P334.transform_image(original)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P335_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.35 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P335_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P335 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P335_RUN_ID:
        raise ArtifactIdentityError("P3.35 AP run ID differs")
    try:
        return _P334.inspect_ap(
            ap_path,
            expected_run_id=P335_RUN_ID,
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
    label: str = "P335 exact rollback AP",
) -> dict[str, Any]:
    if dict(expected) == P334_AP_IDENTITY:
        raise ArtifactIdentityError("P3.34 candidate AP is not rollback")
    try:
        return _P334.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_p335_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p335_artifact_identity_v1",
        "run_id_hex": P335_RUN_ID_HEX,
        "predecessor_run_id_rejected": P334_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P334_AP_IDENTITY),
        "boot_only": True,
        "ab_must_match": True,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key_size": AUTH_KEY_SIZE,
        "auth_key_path_published": False,
    }


__all__ = sorted(
    set(getattr(_P334, "__all__", ()))
    | {
        "ArtifactIdentityError",
        "P334_AP_IDENTITY",
        "P334_ARTIFACT_SOURCE",
        "P334_PREDECESSOR_RUN_ID",
        "P334_PREDECESSOR_RUN_ID_HEX",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P335_ARTIFACT_SOURCE",
        "P335_RUN_ID",
        "P335_RUN_ID_HEX",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STALE_AP_IDENTITIES",
        "inspect_ap",
        "transform_image",
        "validate_image",
        "validate_p335_identity",
        "validate_rollback_ap",
    }
)
