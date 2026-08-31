#!/usr/bin/env python3
"""P3.23 boot/AP identity binding, host-only.

This is a small successor binding around the reviewed P3.22 artifact helper.
The inherited parser and real AP unpack/join checks are loaded from one exact
regular source file, then their current run slot is rebound to P3.23.  The
fixed P3.19 Image is transformed once more to a fresh same-length identity;
the only allowed AP member remains ``boot.img.lz4`` and the rollback AP is
never rewritten.

No function in this module contacts a device or invokes Odin.
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

P322_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p322_artifact_identity.py"
P322_ARTIFACT_IDENTITY = {
    "size": 9_453,
    "sha256": "8e77653fa23f47f48980fb2eae906118239e53e763d4e9643be27a71b0749975",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P323_RUN_ID = bytes.fromhex(P323_RUN_ID_HEX)
P322_PREDECESSOR_RUN_ID_HEX = P322_RUN_ID_HEX
P322_PREDECESSOR_RUN_ID = P322_RUN_ID
# The P3.22 builder's compatibility field is named for its P3.21 wrapper
# predecessor.  When that builder is reopened for P3.23, the same field must
# resolve to the actual immediate predecessor, P3.22.
P321_PREDECESSOR_RUN_ID_HEX = P322_RUN_ID_HEX
P321_PREDECESSOR_RUN_ID = P322_RUN_ID


class ArtifactIdentityError(ValueError):
    """The P3.22 delegate or P3.23 identity binding is not exact."""


def _stable_source(path: Path, label: str, expected: Mapping[str, Any]) -> bytes:
    """Read one direct, unchanged regular source file."""
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

    actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or actual != dict(expected)
    ):
        raise ArtifactIdentityError(f"{label} identity differs")
    return payload


def _load_delegate() -> tuple[types.ModuleType, types.ModuleType]:
    payload = _stable_source(
        P322_ARTIFACT_SOURCE,
        "P3.22 artifact helper source",
        P322_ARTIFACT_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p322_artifact_bound_for_p323")
    module.__file__ = str(P322_ARTIFACT_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P322_ARTIFACT_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.22 artifact helper failed to load") from exc
    # P322 loads its P321 inner module under a private name.  It is retained by
    # object reference for exact execution but is not left import-registered.
    for name in ("s22plus_fyg8_p321_artifact_bound_for_p322",):
        sys.modules.pop(name, None)

    expected = {
        "P319_RUN_ID_HEX": P319_RUN_ID_HEX,
        "P320_RUN_ID_HEX": P320_RUN_ID_HEX,
        "P321_RUN_ID_HEX": P321_RUN_ID_HEX,
        "P322_RUN_ID_HEX": P322_RUN_ID_HEX,
        "P319_RUN_ID": P319_RUN_ID,
        "P320_RUN_ID": P320_RUN_ID,
        "P321_RUN_ID": P321_RUN_ID,
        "P322_RUN_ID": P322_RUN_ID,
    }
    if any(getattr(module, name, None) != value for name, value in expected.items()):
        raise ArtifactIdentityError("P3.22 artifact predecessor identities differ")
    inner = module._DELEGATE
    # The P322 wrapper uses its P321 delegate's names as the current slot.
    # Keep P322 as the explicit predecessor in the private slot so the added
    # stale-ID guard catches a P322 Image/init even after the rebind.
    inner.P321_RUN_ID_HEX = P323_RUN_ID_HEX
    inner.P321_RUN_ID = P323_RUN_ID
    inner.P322_RUN_ID_HEX = P323_RUN_ID_HEX
    inner.P322_RUN_ID = P323_RUN_ID
    inner.P321_PREDECESSOR_RUN_ID_HEX = P322_RUN_ID_HEX
    inner.P321_PREDECESSOR_RUN_ID = P322_RUN_ID
    return module, inner


_P322_MODULE, _INNER = _load_delegate()
_ORIGINAL_VALIDATE_IMAGE = _P322_MODULE._ORIGINAL_VALIDATE_IMAGE
_ORIGINAL_VALIDATE_INIT = _P322_MODULE._ORIGINAL_VALIDATE_INIT


def _reject_stale_image_ids(image: bytes) -> None:
    if type(image) is not bytes:
        return
    try:
        compressed_start, end, _compressed, _config = _INNER._gzip_config(
            image, "P323 Image"
        )
    except Exception:
        return
    outside = image[:compressed_start] + image[end:]
    for old in (P319_RUN_ID_HEX, P320_RUN_ID_HEX, P321_RUN_ID_HEX, P322_RUN_ID_HEX):
        if outside.count(old.encode("ascii")):
            raise ArtifactIdentityError(f"P323 Image contains stale run ID {old}")


def validate_image(image: bytes, *, expected_run_id: bytes = P323_RUN_ID) -> dict[str, Any]:
    if expected_run_id != P323_RUN_ID:
        raise ArtifactIdentityError("P323 Image run ID is not bound to the P323 run")
    _reject_stale_image_ids(image)
    return _ORIGINAL_VALIDATE_IMAGE(image, expected_run_id=P323_RUN_ID)


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P323_RUN_ID:
        raise ArtifactIdentityError("P323 /init run ID is not bound to the P323 run")
    if type(init) is bytes:
        for old, raw in (
            (P319_RUN_ID_HEX, P319_RUN_ID),
            (P320_RUN_ID_HEX, P320_RUN_ID),
            (P321_RUN_ID_HEX, P321_RUN_ID),
            (P322_RUN_ID_HEX, P322_RUN_ID),
        ):
            if init.count(raw):
                raise ArtifactIdentityError(f"/init contains stale run ID {old}")
    return _ORIGINAL_VALIDATE_INIT(init, P323_RUN_ID)


# Rewire the P322 delegate's internal transform/AP join to the P323 guards.
_INNER.validate_image = validate_image
_INNER._validate_init = _validate_init
for function_name, updates in (
    ("validate_image", {"expected_run_id": P323_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P323_RUN_ID, "label": "P323 candidate AP"}),
    ("validate_rollback_ap", {"label": "P323 exact rollback AP"}),
):
    function = getattr(_INNER, function_name, None)
    if function is None:
        raise ArtifactIdentityError(f"P322 delegate lacks {function_name}")
    defaults = dict(getattr(function, "__kwdefaults__", {}) or {})
    defaults.update(updates)
    function.__kwdefaults__ = defaults


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Transform the fixed P3.19 Image to the fresh P3.23 run identity."""
    transformed, receipt = _INNER.transform_image(original)
    # The inherited transform reads the current slot we rebound above.  Make
    # the public receipt explicit and reject any accidental predecessor text.
    if receipt.get("target", {}).get("run_id_hex") != P323_RUN_ID_HEX:
        raise ArtifactIdentityError("P323 Image transform target differs")
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P323_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P323 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P323_RUN_ID:
        raise ArtifactIdentityError("P323 AP run ID is not bound to the P323 run")
    return _INNER.inspect_ap(
        ap_path,
        expected_run_id=P323_RUN_ID,
        expected_image=expected_image,
        expected_init=expected_init,
        expected_child=expected_child,
        expected_ap=expected_ap,
        label=label,
    )


def validate_rollback_ap(
    ap_path: Path,
    expected: Mapping[str, Any],
    *,
    label: str = "P323 exact rollback AP",
) -> dict[str, Any]:
    return _INNER.validate_rollback_ap(ap_path, expected, label=label)


# Stable inherited geometry/tool identities are deliberately exported.  Only
# the current identity and the source binding are P323-specific here.
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
    "identity",
):
    globals()[_name] = getattr(_P322_MODULE, _name)


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
    "P322_ARTIFACT_IDENTITY",
    "P322_ARTIFACT_SOURCE",
    "P322_PREDECESSOR_RUN_ID",
    "P322_PREDECESSOR_RUN_ID_HEX",
    "P321_PREDECESSOR_RUN_ID",
    "P321_PREDECESSOR_RUN_ID_HEX",
    "P322_RUN_ID",
    "P322_RUN_ID_HEX",
    "P323_RUN_ID",
    "P323_RUN_ID_HEX",
    "identity",
    "inspect_ap",
    "stable_bytes",
    "tool_identities",
    "transform_image",
    "validate_image",
    "validate_rollback_ap",
]
