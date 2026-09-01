#!/usr/bin/env python3
"""Fresh P3.26 Image, init, AP, and rollback identity binding (host-only)."""

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
P325_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p325_artifact_identity.py"
P325_ARTIFACT_IDENTITY = {
    "size": 11_002,
    "sha256": "e6849bdd58b34859bf2b0415ece16a962dafdbd02471191ed3dcddd0db68b7af",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_RUN_ID_HEX = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P326_RUN_ID_HEX = "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P326_RUN_ID = bytes.fromhex(P326_RUN_ID_HEX)
P325_PREDECESSOR_RUN_ID_HEX = P325_RUN_ID_HEX
P325_PREDECESSOR_RUN_ID = bytes.fromhex(P325_RUN_ID_HEX)
# Compatibility names used by the inherited P3.22 phase-2 engine.
P324_PREDECESSOR_RUN_ID_HEX = P325_PREDECESSOR_RUN_ID_HEX
P324_PREDECESSOR_RUN_ID = P325_PREDECESSOR_RUN_ID
P323_PREDECESSOR_RUN_ID_HEX = P325_PREDECESSOR_RUN_ID_HEX
P323_PREDECESSOR_RUN_ID = P325_PREDECESSOR_RUN_ID
P321_PREDECESSOR_RUN_ID_HEX = P325_PREDECESSOR_RUN_ID_HEX
P321_PREDECESSOR_RUN_ID = P325_PREDECESSOR_RUN_ID


class ArtifactIdentityError(ValueError):
    """The P3.25 delegate or P3.26 identity differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


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

    def inode(value: os.stat_result) -> tuple[int, ...]:
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

    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or identity(payload) != dict(expected)
    ):
        raise ArtifactIdentityError(f"{label} identity differs")
    return payload


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(
        P325_ARTIFACT_SOURCE, "P3.25 artifact helper", P325_ARTIFACT_IDENTITY
    )
    module = types.ModuleType("s22plus_fyg8_p325_artifact_bound_for_p326")
    module.__file__ = str(P325_ARTIFACT_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P325_ARTIFACT_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.25 artifact helper failed to load") from exc
    if getattr(module, "P325_RUN_ID_HEX", None) != P325_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.25 artifact identity differs")
    return module


_P325 = _load_delegate()
_INNER = _P325._INNER
for _name, _value in (
    ("P321_RUN_ID_HEX", P326_RUN_ID_HEX),
    ("P321_RUN_ID", P326_RUN_ID),
    ("P322_RUN_ID_HEX", P326_RUN_ID_HEX),
    ("P322_RUN_ID", P326_RUN_ID),
):
    setattr(_INNER, _name, _value)


def _reject_stale_image_ids(image: bytes) -> None:
    try:
        compressed_start, end, _compressed, _config = _INNER._gzip_config(
            image, "P326 Image"
        )
    except Exception:
        return
    outside = image[:compressed_start] + image[end:]
    for old in (
        P319_RUN_ID_HEX,
        P320_RUN_ID_HEX,
        P321_RUN_ID_HEX,
        P322_RUN_ID_HEX,
        P323_RUN_ID_HEX,
        P324_RUN_ID_HEX,
        P325_RUN_ID_HEX,
    ):
        if outside.count(old.encode("ascii")):
            raise ArtifactIdentityError(f"P326 Image contains stale run ID {old}")


def validate_image(
    image: bytes, *, expected_run_id: bytes = P326_RUN_ID
) -> dict[str, Any]:
    if expected_run_id != P326_RUN_ID:
        raise ArtifactIdentityError("P326 Image run ID differs")
    _reject_stale_image_ids(image)
    try:
        return _P325._ORIGINAL_VALIDATE_IMAGE(image, expected_run_id=P326_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P326_RUN_ID:
        raise ArtifactIdentityError("P326 init run ID differs")
    for old in (
        P319_RUN_ID_HEX,
        P320_RUN_ID_HEX,
        P321_RUN_ID_HEX,
        P322_RUN_ID_HEX,
        P323_RUN_ID_HEX,
        P324_RUN_ID_HEX,
        P325_RUN_ID_HEX,
    ):
        if bytes.fromhex(old) in init:
            raise ArtifactIdentityError(f"P326 init contains stale run ID {old}")
    try:
        return _P325._ORIGINAL_VALIDATE_INIT(init, P326_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_INNER.validate_image = validate_image
_INNER._validate_init = _validate_init
for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P326_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P326_RUN_ID, "label": "P326 candidate AP"}),
    ("validate_rollback_ap", {"label": "P326 exact rollback AP"}),
):
    _function = getattr(_INNER, _function_name)
    _defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
    _defaults.update(_updates)
    _function.__kwdefaults__ = _defaults


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        transformed, receipt = _INNER.transform_image(original)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P326_RUN_ID_HEX:
        raise ArtifactIdentityError("P326 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P326_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P326 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P326_RUN_ID:
        raise ArtifactIdentityError("P326 AP run ID differs")
    try:
        return _INNER.inspect_ap(
            ap_path,
            expected_run_id=P326_RUN_ID,
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
    label: str = "P326 exact rollback AP",
) -> dict[str, Any]:
    try:
        return _INNER.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


for _name in (
    "GZIP_HEADER",
    "IMAGE_SECTION_LAYOUT",
    "IKCONFIG_COMPRESSED_SIZE",
    "IKCONFIG_END_OFFSET",
    "IKCONFIG_OFFSET",
    "LZ4",
    "LZ4_IDENTITY",
    "MAGISKBOOT",
    "MAGISKBOOT_IDENTITY",
    "P319_IMAGE",
    "P319_IMAGE_IDENTITY",
    "stable_bytes",
    "tool_identities",
):
    globals()[_name] = getattr(_P325, _name)


__all__ = [name for name in globals() if not name.startswith("_")]
