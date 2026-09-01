#!/usr/bin/env python3
"""P3.25 boot/AP identity binding, host-only.

The exact P3.24 artifact helper is loaded by stable bytes and its existing
identity-only Image/AP machinery is rebound to one fresh P3.25 run ID.  The
Image geometry, gzip layout, userspace join, and exact stock rollback remain
unchanged; only the declared run-bound Image/IKCONFIG and ``/init`` identity
are rotated.  This module has no device, ADB, or Odin path.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent

P324_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p324_artifact_identity.py"
P324_ARTIFACT_IDENTITY = {
    "size": 10_839,
    "sha256": "a572846e7bd8c725e9449aaa07dbd22d6cb278015301a6b9a63f59bf08b8e4c6",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_RUN_ID_HEX = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P323_RUN_ID = bytes.fromhex(P323_RUN_ID_HEX)
P324_RUN_ID = bytes.fromhex(P324_RUN_ID_HEX)
P325_RUN_ID = bytes.fromhex(P325_RUN_ID_HEX)

P324_PREDECESSOR_RUN_ID_HEX = P324_RUN_ID_HEX
P324_PREDECESSOR_RUN_ID = P324_RUN_ID
# The inherited phase-2 engine still names its immediate predecessor slot
# P323.  Keep that compatibility spelling bound to the real P3.24 input.
P323_PREDECESSOR_RUN_ID_HEX = P324_RUN_ID_HEX
P323_PREDECESSOR_RUN_ID = P324_RUN_ID
P321_PREDECESSOR_RUN_ID_HEX = P324_RUN_ID_HEX
P321_PREDECESSOR_RUN_ID = P324_RUN_ID


class ArtifactIdentityError(ValueError):
    """The exact P3.24 delegate or P3.25 identity is not available."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_source(
    path: Path, label: str, expected: Mapping[str, Any]
) -> bytes:
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
        P324_ARTIFACT_SOURCE,
        "P3.24 artifact helper source",
        P324_ARTIFACT_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p324_artifact_bound_for_p325")
    module.__file__ = str(P324_ARTIFACT_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P324_ARTIFACT_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.24 artifact helper failed to load") from exc
    if getattr(module, "P324_RUN_ID_HEX", None) != P324_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.24 artifact current identity differs")
    for name in (
        "transform_image",
        "validate_image",
        "inspect_ap",
        "validate_rollback_ap",
    ):
        if not callable(getattr(module, name, None)):
            raise ArtifactIdentityError(f"P3.24 artifact helper lacks {name}")
    return module


_P324 = _load_delegate()
_INNER = _P324._INNER
_ORIGINAL_VALIDATE_IMAGE = _P324._ORIGINAL_VALIDATE_IMAGE
_ORIGINAL_VALIDATE_INIT = _P324._ORIGINAL_VALIDATE_INIT


# The nested P3.21 engine calls its current slot P321 (and some helper paths
# retain a P322 alias).  Rebind both to P3.25 while keeping P3.24 explicit as
# the immediate predecessor exposed by this wrapper.
for name, value in (
    ("P321_RUN_ID_HEX", P325_RUN_ID_HEX),
    ("P321_RUN_ID", P325_RUN_ID),
    ("P322_RUN_ID_HEX", P325_RUN_ID_HEX),
    ("P322_RUN_ID", P325_RUN_ID),
):
    setattr(_INNER, name, value)


def _reject_stale_image_ids(image: bytes) -> None:
    if type(image) is not bytes:
        return
    try:
        compressed_start, end, _compressed, _config = _INNER._gzip_config(
            image, "P325 Image"
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
    ):
        if outside.count(old.encode("ascii")):
            raise ArtifactIdentityError(f"P325 Image contains stale run ID {old}")


def validate_image(
    image: bytes,
    *,
    expected_run_id: bytes = P325_RUN_ID,
) -> dict[str, Any]:
    if expected_run_id != P325_RUN_ID:
        raise ArtifactIdentityError("P325 Image run ID is not bound to the P325 run")
    _reject_stale_image_ids(image)
    try:
        return _ORIGINAL_VALIDATE_IMAGE(image, expected_run_id=P325_RUN_ID)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P325_RUN_ID:
        raise ArtifactIdentityError("P325 /init run ID is not bound to the P325 run")
    if type(init) is bytes:
        for old, raw in (
            (P319_RUN_ID_HEX, P319_RUN_ID),
            (P320_RUN_ID_HEX, P320_RUN_ID),
            (P321_RUN_ID_HEX, P321_RUN_ID),
            (P322_RUN_ID_HEX, P322_RUN_ID),
            (P323_RUN_ID_HEX, P323_RUN_ID),
            (P324_RUN_ID_HEX, P324_RUN_ID),
        ):
            if init.count(raw):
                raise ArtifactIdentityError(f"P325 /init contains stale run ID {old}")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P325_RUN_ID)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


_INNER.validate_image = validate_image
_INNER._validate_init = _validate_init
for function_name, updates in (
    ("validate_image", {"expected_run_id": P325_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P325_RUN_ID, "label": "P325 candidate AP"}),
    ("validate_rollback_ap", {"label": "P325 exact rollback AP"}),
):
    function = getattr(_INNER, function_name, None)
    if function is None:
        raise ArtifactIdentityError(f"P3.24 delegate lacks {function_name}")
    defaults = dict(getattr(function, "__kwdefaults__", {}) or {})
    defaults.update(updates)
    function.__kwdefaults__ = defaults


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Transform the fixed P3.19 Image to the fresh P3.25 run identity."""
    try:
        transformed, receipt = _INNER.transform_image(original)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P325_RUN_ID_HEX:
        raise ArtifactIdentityError("P325 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P325_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P325 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P325_RUN_ID:
        raise ArtifactIdentityError("P325 AP run ID is not bound to the P325 run")
    try:
        return _INNER.inspect_ap(
            ap_path,
            expected_run_id=P325_RUN_ID,
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
    label: str = "P325 exact rollback AP",
) -> dict[str, Any]:
    try:
        return _INNER.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


# Stable geometry/tool identities remain inherited from the exact P3.24
# source.  They are not run-bound identity data.
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
    globals()[_name] = getattr(_P324, _name)


__all__ = [
    "ArtifactIdentityError",
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
    "P319_RUN_ID",
    "P319_RUN_ID_HEX",
    "P320_RUN_ID",
    "P320_RUN_ID_HEX",
    "P321_RUN_ID",
    "P321_RUN_ID_HEX",
    "P322_RUN_ID",
    "P322_RUN_ID_HEX",
    "P323_RUN_ID",
    "P323_RUN_ID_HEX",
    "P323_PREDECESSOR_RUN_ID",
    "P323_PREDECESSOR_RUN_ID_HEX",
    "P324_ARTIFACT_IDENTITY",
    "P324_ARTIFACT_SOURCE",
    "P324_PREDECESSOR_RUN_ID",
    "P324_PREDECESSOR_RUN_ID_HEX",
    "P324_RUN_ID",
    "P324_RUN_ID_HEX",
    "P325_RUN_ID",
    "P325_RUN_ID_HEX",
    "P321_PREDECESSOR_RUN_ID",
    "P321_PREDECESSOR_RUN_ID_HEX",
    "identity",
    "inspect_ap",
    "stable_bytes",
    "tool_identities",
    "transform_image",
    "validate_image",
    "validate_rollback_ap",
]
