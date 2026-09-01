#!/usr/bin/env python3
"""Bind the P3.23 ACM-primary runtime without changing its bytes.

P3.24 is an identity-only successor to P3.23.  The P3.23 source is loaded
from one exact regular file and the already-reviewed ACM-primary publisher is
required to be byte-for-byte identical.  Only the surrounding P3.24 source
and artifact bindings change; this module never contacts a device or invokes
ADB/Odin.
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
P323_ACM_SOURCE = REVALIDATION / "s22plus_fyg8_p323_acm_primary_runtime.py"
P323_ACM_IDENTITY = {
    "size": 5_955,
    "sha256": "82e7a294b14251b484092e804f0d97569282f70715b2bd1941f0f7dc0daf0bba",
}
P323_RUNTIME_INCLUDE_IDENTITY = {
    "size": 454_072,
    "sha256": "6dd50438f01f241c020918c1f9774cfeabe4c15bc33da4dcc337cd6c517d5cf0",
}

CONTRACT_ID = "s22plus-fyg8-p324-acm-primary-runtime-v1"
SCHEMA = CONTRACT_ID
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
RUNTIME_KEY = "p290_e3_runtime_include"


class AcmPrimaryError(ValueError):
    """The exact P3.23 runtime or the P3.24 identity binding differs."""


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
        raise AcmPrimaryError(f"{label} is unavailable") from exc

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
        raise AcmPrimaryError(f"{label} identity differs")
    return payload


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(P323_ACM_SOURCE, "P3.23 ACM runtime source", P323_ACM_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p323_acm_runtime_bound_for_p324")
    module.__file__ = str(P323_ACM_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P323_ACM_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AcmPrimaryError("P3.23 ACM runtime failed to load") from exc
    for name in (
        "validate_p322_runtime",
        "validate_p323_runtime",
        "validate_transform",
        "transform_runtime_include",
        "transform_artifacts",
    ):
        if not callable(getattr(module, name, None)):
            raise AcmPrimaryError(f"P3.23 ACM runtime lacks {name}")
    return module


_P323 = _load_delegate()

# These anchors are deliberately exported unchanged.  Their presence and
# order are what proves that P3.24 retained the exact ACM-primary behavior.
P322_RUNTIME_MARKER = _P323.P322_RUNTIME_MARKER
PUBLISHER = _P323.PUBLISHER
BANNER_WRITER = _P323.BANNER_WRITER
P322_BRIDGE = _P323.P322_BRIDGE
P322_ENTRY_PREIMAGE = _P323.P322_ENTRY_PREIMAGE
P323_ENTRY_POSTIMAGE = _P323.P323_ENTRY_POSTIMAGE
P324_ENTRY_POSTIMAGE = P323_ENTRY_POSTIMAGE


def _bytes(value: bytes, label: str) -> None:
    if type(value) is not bytes:
        raise AcmPrimaryError(f"{label} must be bytes")


def validate_p323_runtime(value: bytes) -> dict[str, Any]:
    _bytes(value, "P323 runtime")
    if identity(value) != P323_RUNTIME_INCLUDE_IDENTITY:
        raise AcmPrimaryError("P323 runtime identity differs")
    try:
        result = _P323.validate_p323_runtime(value)
    except Exception as exc:
        raise AcmPrimaryError(str(exc)) from exc
    return result


def validate_p324_runtime(value: bytes) -> dict[str, Any]:
    """Validate the P3.23 ACM-primary runtime under the P3.24 contract."""
    result = validate_p323_runtime(value)
    result = dict(result)
    result.update(
        {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "target": TARGET,
            "runtime_byte_equivalent_to_p323": True,
            "acm_primary": True,
        }
    )
    return result


def validate_transform(before: bytes, after: bytes) -> dict[str, Any]:
    """Require an exact no-byte-delta P3.24 runtime transform."""
    validate_p323_runtime(before)
    if type(after) is not bytes:
        raise AcmPrimaryError("P324 runtime must be bytes")
    if after != before:
        raise AcmPrimaryError("P324 runtime changed outside the identity lane")
    result = validate_p324_runtime(after)
    return result | {
        "changed_anchor": None,
        "changed_only_in_anchor": False,
        "runtime_byte_equivalent_to_p323": True,
        "source_identity": identity(before),
        "target_identity": identity(after),
    }


def transform_runtime_include(value: bytes) -> bytes:
    validate_p323_runtime(value)
    # Returning the original immutable bytes keeps the source closure exactly
    # equal while still making the identity transform auditable.
    validate_transform(value, value)
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise AcmPrimaryError("P324 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY])
    if any(result[key] != source[key] for key in result):
        raise AcmPrimaryError("P324 source delta differs")
    return result


__all__ = [
    "AcmPrimaryError",
    "BANNER_WRITER",
    "CONTRACT_ID",
    "P322_BRIDGE",
    "P322_ENTRY_PREIMAGE",
    "P322_RUNTIME_MARKER",
    "P323_ACM_IDENTITY",
    "P323_ACM_SOURCE",
    "P323_RUNTIME_INCLUDE_IDENTITY",
    "P323_ENTRY_POSTIMAGE",
    "P324_ENTRY_POSTIMAGE",
    "PUBLISHER",
    "RUNTIME_KEY",
    "SCHEMA",
    "TARGET",
    "identity",
    "transform_artifacts",
    "transform_runtime_include",
    "validate_p323_runtime",
    "validate_p324_runtime",
    "validate_transform",
]
