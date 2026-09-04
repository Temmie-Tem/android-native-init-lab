#!/usr/bin/env python3
"""Host-only P3.39 boot-only artifact identity.

This is an isolated exact load of the consumed P3.38 artifact identity
helper.  Its only authority-bearing change is the fresh P339 run identity;
the AP remains A/B-equal, contains exactly one ``boot.img.lz4`` member, and
the inherited exact Magisk rollback remains the sole recovery artifact.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p338_artifact_identity.py")
P338_SOURCE = SOURCE
P338_SOURCE_IDENTITY: dict[str, Any] = {
    "size": 10_383,
    "sha256": "7be955b0c90c98bae333e2fc2d3ffb83df8f987a1b76608723e35c309bee8a88",
}
P338_PREDECESSOR_RUN_ID_HEX = "c338f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P338_PREDECESSOR_RUN_ID = bytes.fromhex(P338_PREDECESSOR_RUN_ID_HEX)
P338_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "2f6dc740d06e6b7aef65423ba167fa7ac641d6374583322206dd4a5259a6d2e8",
}
P339_RUN_ID_HEX = "c339f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P339_RUN_ID = bytes.fromhex(P339_RUN_ID_HEX)


class ArtifactIdentityError(ValueError):
    """The exact P3.38 artifact or fresh P3.39 identity differs."""


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


def _load_p338() -> types.ModuleType:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(2 * 1024 * 1024 + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ArtifactIdentityError("P3.38 artifact helper is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or len(payload) > 2 * 1024 * 1024
        or identity(payload) != P338_SOURCE_IDENTITY
    ):
        raise ArtifactIdentityError("P3.38 artifact helper identity differs")
    module = types.ModuleType("s22plus_fyg8_p338_artifact_bound_for_p339")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.38 artifact helper failed to load") from exc
    if getattr(module, "P338_RUN_ID_HEX", None) != P338_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.38 artifact binding differs")
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


_P338 = _load_p338()
for _module in _modules(_P338):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P338_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P339_RUN_ID)
        elif _value == P338_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P339_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            defaults = dict(_value.__kwdefaults__)
            changed = False
            for key, current in tuple(defaults.items()):
                if current == P338_PREDECESSOR_RUN_ID:
                    defaults[key] = P339_RUN_ID
                    changed = True
                elif current == P338_PREDECESSOR_RUN_ID_HEX:
                    defaults[key] = P339_RUN_ID_HEX
                    changed = True
            if changed:
                _value.__kwdefaults__ = defaults


_BASE = _P338._BASE
_ORIGINAL_REJECT = _BASE._reject_stale_image_ids
_ORIGINAL_VALIDATE_INIT = _BASE._validate_init


def _reject_stale_image_ids(image: bytes) -> None:
    _ORIGINAL_REJECT(image)
    try:
        start, end, _compressed, _config = _BASE._INNER._gzip_config(image, "P339 Image")
    except Exception:
        return
    if P338_PREDECESSOR_RUN_ID_HEX.encode("ascii") in image[:start] + image[end:]:
        raise ArtifactIdentityError("P3.38 Image contains the predecessor run ID")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P339_RUN_ID:
        raise ArtifactIdentityError("P3.39 init run ID differs")
    if P338_PREDECESSOR_RUN_ID in init:
        raise ArtifactIdentityError("P3.39 init contains the predecessor run ID")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P339_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_BASE._reject_stale_image_ids = _reject_stale_image_ids
_BASE._validate_init = _validate_init
_BASE._INNER.validate_image = _BASE.validate_image
_BASE._INNER._validate_init = _validate_init
_P338.STALE_AP_IDENTITIES = tuple((*_P338.STALE_AP_IDENTITIES, dict(P338_AP_IDENTITY)))
for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P339_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P339_RUN_ID, "label": "P339 candidate AP"}),
    ("validate_rollback_ap", {"label": "P339 exact rollback AP"}),
):
    _function = getattr(_BASE._INNER, _function_name, None)
    if _function is not None:
        defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
        defaults.update(_updates)
        _function.__kwdefaults__ = defaults


for _name in getattr(_P338, "__all__", ()):
    if hasattr(_P338, _name):
        globals()[_name] = getattr(_P338, _name)

# Re-pin inherited compatibility exports after the copied __all__ table.
SOURCE = Path(__file__).with_name("s22plus_fyg8_p338_artifact_identity.py")
SOURCE_IDENTITY = dict(P338_SOURCE_IDENTITY)
P338_RUN_ID_HEX = P339_RUN_ID_HEX
P338_RUN_ID = P339_RUN_ID
P337_RUN_ID_HEX = P339_RUN_ID_HEX
P337_RUN_ID = P339_RUN_ID
P336_RUN_ID_HEX = P339_RUN_ID_HEX
P336_RUN_ID = P339_RUN_ID
P335_RUN_ID_HEX = P339_RUN_ID_HEX
P335_RUN_ID = P339_RUN_ID
P334_RUN_ID_HEX = P339_RUN_ID_HEX
P334_RUN_ID = P339_RUN_ID
P339_ARTIFACT_SOURCE = Path(__file__).resolve()
P338_ARTIFACT_SOURCE = P339_ARTIFACT_SOURCE
P337_ARTIFACT_SOURCE = P339_ARTIFACT_SOURCE
P336_ARTIFACT_SOURCE = P339_ARTIFACT_SOURCE
P335_ARTIFACT_SOURCE = P339_ARTIFACT_SOURCE
P334_ARTIFACT_SOURCE = P339_ARTIFACT_SOURCE
STALE_AP_IDENTITIES = _P338.STALE_AP_IDENTITIES


def validate_image(image: bytes, *, expected_run_id: bytes = P339_RUN_ID) -> dict[str, Any]:
    if expected_run_id != P339_RUN_ID:
        raise ArtifactIdentityError("P3.39 Image run ID differs")
    try:
        return _P338.validate_image(image, expected_run_id=P339_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        transformed, receipt = _P338.transform_image(original)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P339_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.39 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P339_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P339 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P339_RUN_ID:
        raise ArtifactIdentityError("P3.39 AP run ID differs")
    try:
        return _P338.inspect_ap(
            ap_path,
            expected_run_id=P339_RUN_ID,
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
    label: str = "P339 exact rollback AP",
) -> dict[str, Any]:
    if dict(expected) in (
        P338_AP_IDENTITY,
        getattr(_P338, "P336_AP_IDENTITY", {}),
        getattr(_P338, "P334_AP_IDENTITY", {}),
    ):
        raise ArtifactIdentityError("consumed predecessor AP is not rollback")
    try:
        return _P338.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_p339_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p339_artifact_identity_v1",
        "run_id_hex": P339_RUN_ID_HEX,
        "predecessor_run_id_rejected": P338_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P338_AP_IDENTITY),
        "boot_only": True,
        "ab_must_match": True,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key_size": AUTH_KEY_SIZE,
        "auth_key_path_published": False,
    }


__all__ = sorted(
    set(getattr(_P338, "__all__", ()))
    | {
        "ArtifactIdentityError",
        "P338_AP_IDENTITY",
        "P338_ARTIFACT_SOURCE",
        "P338_PREDECESSOR_RUN_ID",
        "P338_PREDECESSOR_RUN_ID_HEX",
        "P338_RUN_ID",
        "P338_RUN_ID_HEX",
        "P337_ARTIFACT_SOURCE",
        "P337_RUN_ID",
        "P337_RUN_ID_HEX",
        "P339_ARTIFACT_SOURCE",
        "P339_RUN_ID",
        "P339_RUN_ID_HEX",
        "SOURCE",
        "P338_SOURCE",
        "P338_SOURCE_IDENTITY",
        "P339_SOURCE_IDENTITY",
        "STALE_AP_IDENTITIES",
        "inspect_ap",
        "transform_image",
        "validate_image",
        "validate_p339_identity",
        "validate_rollback_ap",
    }
)
