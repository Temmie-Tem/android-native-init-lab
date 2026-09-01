#!/usr/bin/env python3
"""P3.24 boot/AP identity binding, host-only.

The P3.23 artifact helper is loaded by exact bytes and its inner reviewed
Image/AP implementation is rebound to one fresh, same-length P3.24 run ID.
Only the Image's fixed rodata/IKCONFIG identity and the compiled ``/init``
identity change.  All AP inspection, boot-only member checks, and rollback
validation remain delegated to the reviewed implementation.  No function in
this module contacts a device or invokes Odin.
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

P323_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p323_artifact_identity.py"
P323_ARTIFACT_IDENTITY = {
    "size": 10_397,
    "sha256": "22a175eb09532b3e1df785d1550883a3503a166444e96f1c5d70ae6cba2e9021",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P323_RUN_ID = bytes.fromhex(P323_RUN_ID_HEX)
P324_RUN_ID = bytes.fromhex(P324_RUN_ID_HEX)

# The nested P3.21 implementation names its current slot P321.  Keep the
# aliases explicit so the P3.24 builder can reuse its phase-2 machinery while
# retaining truthful immediate-predecessor metadata.
P323_PREDECESSOR_RUN_ID_HEX = P323_RUN_ID_HEX
P323_PREDECESSOR_RUN_ID = P323_RUN_ID
P321_PREDECESSOR_RUN_ID_HEX = P323_RUN_ID_HEX
P321_PREDECESSOR_RUN_ID = P323_RUN_ID


class ArtifactIdentityError(ValueError):
    """The exact P3.23 delegate or P3.24 identity binding is not available."""


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
        P323_ARTIFACT_SOURCE,
        "P3.23 artifact helper source",
        P323_ARTIFACT_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p323_artifact_bound_for_p324")
    module.__file__ = str(P323_ARTIFACT_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P323_ARTIFACT_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.23 artifact helper failed to load") from exc
    if getattr(module, "P323_RUN_ID_HEX", None) != P323_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.23 artifact current identity differs")
    for name in ("transform_image", "validate_image", "inspect_ap", "validate_rollback_ap"):
        if not callable(getattr(module, name, None)):
            raise ArtifactIdentityError(f"P3.23 artifact helper lacks {name}")
    return module


_P323 = _load_delegate()
_INNER = _P323._INNER
_ORIGINAL_VALIDATE_IMAGE = _P323._ORIGINAL_VALIDATE_IMAGE
_ORIGINAL_VALIDATE_INIT = _P323._ORIGINAL_VALIDATE_INIT

# Rebind the nested P3.21 implementation's captured current slot.  Its
# transform is identity-only and therefore remains the real deterministic
# builder for P3.24 after this one explicit update.
for name, value in (
    ("P321_RUN_ID_HEX", P324_RUN_ID_HEX),
    ("P321_RUN_ID", P324_RUN_ID),
    ("P322_RUN_ID_HEX", P324_RUN_ID_HEX),
    ("P322_RUN_ID", P324_RUN_ID),
    ("P321_PREDECESSOR_RUN_ID_HEX", P323_RUN_ID_HEX),
    ("P321_PREDECESSOR_RUN_ID", P323_RUN_ID),
):
    setattr(_INNER, name, value)


def _reject_stale_image_ids(image: bytes) -> None:
    if type(image) is not bytes:
        return
    try:
        compressed_start, end, _compressed, _config = _INNER._gzip_config(
            image, "P324 Image"
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
    ):
        if outside.count(old.encode("ascii")):
            raise ArtifactIdentityError(f"P324 Image contains stale run ID {old}")


def validate_image(
    image: bytes,
    *,
    expected_run_id: bytes = P324_RUN_ID,
) -> dict[str, Any]:
    if expected_run_id != P324_RUN_ID:
        raise ArtifactIdentityError("P324 Image run ID is not bound to the P324 run")
    _reject_stale_image_ids(image)
    try:
        return _ORIGINAL_VALIDATE_IMAGE(image, expected_run_id=P324_RUN_ID)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P324_RUN_ID:
        raise ArtifactIdentityError("P324 /init run ID is not bound to the P324 run")
    if type(init) is bytes:
        for old, raw in (
            (P319_RUN_ID_HEX, P319_RUN_ID),
            (P320_RUN_ID_HEX, P320_RUN_ID),
            (P321_RUN_ID_HEX, P321_RUN_ID),
            (P322_RUN_ID_HEX, P322_RUN_ID),
            (P323_RUN_ID_HEX, P323_RUN_ID),
        ):
            if init.count(raw):
                raise ArtifactIdentityError(f"P324 /init contains stale run ID {old}")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P324_RUN_ID)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


# The inner AP inspector resolves these names from its own module globals.
_INNER.validate_image = validate_image
_INNER._validate_init = _validate_init
for function_name, updates in (
    ("validate_image", {"expected_run_id": P324_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P324_RUN_ID, "label": "P324 candidate AP"}),
    ("validate_rollback_ap", {"label": "P324 exact rollback AP"}),
):
    function = getattr(_INNER, function_name, None)
    if function is None:
        raise ArtifactIdentityError(f"P3.23 delegate lacks {function_name}")
    defaults = dict(getattr(function, "__kwdefaults__", {}) or {})
    defaults.update(updates)
    function.__kwdefaults__ = defaults


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Transform the fixed P3.19 Image to the fresh P3.24 run identity."""
    try:
        transformed, receipt = _INNER.transform_image(original)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc
    if receipt.get("target", {}).get("run_id_hex") != P324_RUN_ID_HEX:
        raise ArtifactIdentityError("P324 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P324_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P324 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P324_RUN_ID:
        raise ArtifactIdentityError("P324 AP run ID is not bound to the P324 run")
    try:
        return _INNER.inspect_ap(
            ap_path,
            expected_run_id=P324_RUN_ID,
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
    label: str = "P324 exact rollback AP",
) -> dict[str, Any]:
    try:
        return _INNER.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        if isinstance(exc, ArtifactIdentityError):
            raise
        raise ArtifactIdentityError(str(exc)) from exc


# Stable geometry/tool identities are inherited from the exact P3.23 source.
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
    globals()[_name] = getattr(_P323, _name)


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
    "P323_ARTIFACT_IDENTITY",
    "P323_ARTIFACT_SOURCE",
    "P323_PREDECESSOR_RUN_ID",
    "P323_PREDECESSOR_RUN_ID_HEX",
    "P323_RUN_ID",
    "P323_RUN_ID_HEX",
    "P324_RUN_ID",
    "P324_RUN_ID_HEX",
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
