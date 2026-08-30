#!/usr/bin/env python3
"""P3.22 boot/AP identity wrapper, host-only.

P3.22 keeps the reviewed P3.21 artifact-identity implementation and changes
only its identity binding.  The P3.21 source is loaded by exact bytes and
hash, then its internal current slot is rebound to the fresh P3.22 run ID.
The public predecessor constants remain available for explicit rejection
checks.  The transform still starts from the fixed P3.19 Image, and the
delegate continues to inspect only a boot-only AP and the exact rollback AP.

This module never contacts a device or invokes Odin.
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

P321_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p321_artifact_identity.py"
P321_ARTIFACT_IDENTITY = {
    "size": 26_923,
    "sha256": "dc303ef20175a7a6cbe350328fff499ef585edfba995735a990d0891e3570055",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P321_PREDECESSOR_RUN_ID_HEX = P321_RUN_ID_HEX
P321_PREDECESSOR_RUN_ID = P321_RUN_ID


class ArtifactIdentityError(ValueError):
    """The P3.21 delegate or the P3.22 identity binding is not exact."""


def _stable_source(path: Path, label: str, expected: Mapping[str, Any]) -> bytes:
    """Read one exact regular source file without following an indirect path."""
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
    before_id = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_uid,
        before.st_gid,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    inside_id = (
        inside.st_dev,
        inside.st_ino,
        inside.st_mode,
        inside.st_nlink,
        inside.st_uid,
        inside.st_gid,
        inside.st_size,
        inside.st_mtime_ns,
        inside.st_ctime_ns,
    )
    after_id = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_uid,
        after.st_gid,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before_id != inside_id
        or before_id != after_id
        or len(payload) != before.st_size
        or actual != dict(expected)
    ):
        raise ArtifactIdentityError(f"{label} identity differs")
    return payload


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(
        P321_ARTIFACT_SOURCE,
        "P3.21 artifact helper source",
        P321_ARTIFACT_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p321_artifact_bound_for_p322")
    module.__file__ = str(P321_ARTIFACT_SOURCE)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(P321_ARTIFACT_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.21 artifact helper failed to load") from exc

    expected_predecessors = {
        "P319_RUN_ID_HEX": P319_RUN_ID_HEX,
        "P320_RUN_ID_HEX": P320_RUN_ID_HEX,
        "P321_RUN_ID_HEX": P321_RUN_ID_HEX,
        "P319_RUN_ID": P319_RUN_ID,
        "P320_RUN_ID": P320_RUN_ID,
        "P321_RUN_ID": P321_RUN_ID,
    }
    if any(getattr(module, name, None) != value for name, value in expected_predecessors.items()):
        raise ArtifactIdentityError("P3.21 artifact predecessor identities differ")

    # Keep the old P3.21 values in named delegate aliases, while the names
    # referenced by the inherited implementation become the P3.22 current
    # slot.  The outer module restores public P3.21 constants below.
    module.P321_PREDECESSOR_RUN_ID_HEX = P321_RUN_ID_HEX
    module.P321_PREDECESSOR_RUN_ID = P321_RUN_ID
    module.P322_RUN_ID_HEX = P322_RUN_ID_HEX
    module.P322_RUN_ID = P322_RUN_ID
    module.P321_RUN_ID_HEX = P322_RUN_ID_HEX
    module.P321_RUN_ID = P322_RUN_ID

    # Rebind every run-bearing default.  Defaults are evaluated when the
    # delegate is compiled, so changing globals alone does not change them.
    for function_name, updates in (
        ("validate_image", {"expected_run_id": P322_RUN_ID}),
        ("inspect_ap", {"expected_run_id": P322_RUN_ID, "label": "P322 candidate AP"}),
        ("validate_rollback_ap", {"label": "P322 exact rollback AP"}),
    ):
        function = getattr(module, function_name, None)
        if function is None:
            raise ArtifactIdentityError(f"P3.21 artifact helper lacks {function_name}")
        defaults = dict(getattr(function, "__kwdefaults__", {}) or {})
        defaults.update(updates)
        function.__kwdefaults__ = defaults
    return module


_DELEGATE = _load_delegate()
_ORIGINAL_VALIDATE_IMAGE = _DELEGATE.validate_image
_ORIGINAL_VALIDATE_INIT = _DELEGATE._validate_init


def _reject_p321_image_id(image: bytes) -> None:
    """Reject stale P3.21 raw identity while retaining delegate geometry checks."""
    if type(image) is not bytes:
        return
    try:
        compressed_start, end, _compressed, _config = _DELEGATE._gzip_config(
            image, "P322 Image"
        )
    except Exception:
        # The original validator supplies the authoritative malformed-image
        # error; this precheck is only for the additional predecessor ID.
        return
    outside = image[:compressed_start] + image[end:]
    if outside.count(P321_PREDECESSOR_RUN_ID_HEX.encode("ascii")) != 0:
        raise ArtifactIdentityError("P322 Image contains the predecessor P3.21 run ID")


def validate_image(
    image: bytes,
    *,
    expected_run_id: bytes = P322_RUN_ID,
) -> dict[str, Any]:
    """Validate an Image only when its run ID is exactly P3.22."""
    if expected_run_id != P322_RUN_ID:
        raise ArtifactIdentityError("P322 Image run ID is not bound to the P322 run")
    _reject_p321_image_id(image)
    return _ORIGINAL_VALIDATE_IMAGE(image, expected_run_id=P322_RUN_ID)


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P322_RUN_ID:
        raise ArtifactIdentityError("P322 /init run ID is not bound to the P322 run")
    if type(init) is bytes and init.count(P321_PREDECESSOR_RUN_ID) != 0:
        raise ArtifactIdentityError("/init contains the predecessor P3.21 run ID")
    return _ORIGINAL_VALIDATE_INIT(init, P322_RUN_ID)


# Rewire the delegate's internal calls so transform_image and inspect_ap use
# the additional P3.21 rejection as well as the inherited P3.19/P3.20 checks.
_DELEGATE.validate_image = validate_image
_DELEGATE._validate_init = _validate_init

# Export the inherited helper surface.  Its functions retain their own
# delegate globals, which are now bound to P3.22 internally.
for _name, _value in _DELEGATE.__dict__.items():
    if not _name.startswith("__"):
        globals()[_name] = _value

# Public lineage is deliberately truthful: P3.21 is the predecessor, while
# the delegate's private globals use the P3.22 current slot for inherited code.
ArtifactIdentityError = _DELEGATE.ArtifactIdentityError
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)
P322_RUN_ID = bytes.fromhex(P322_RUN_ID_HEX)
P321_PREDECESSOR_RUN_ID = P321_RUN_ID
P321_PREDECESSOR_RUN_ID_HEX = P321_RUN_ID_HEX
P322_RUN_ID_HEX = P322_RUN_ID.hex()
P321_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p321_artifact_identity.py"
P321_ARTIFACT_IDENTITY = dict(P321_ARTIFACT_IDENTITY)

# The rewired delegate globals point at these function objects after export.
validate_image = _DELEGATE.validate_image
_validate_init = _DELEGATE._validate_init


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
    "P321_ARTIFACT_IDENTITY",
    "P321_ARTIFACT_SOURCE",
    "P321_PREDECESSOR_RUN_ID",
    "P321_PREDECESSOR_RUN_ID_HEX",
    "P321_RUN_ID",
    "P321_RUN_ID_HEX",
    "P322_RUN_ID",
    "P322_RUN_ID_HEX",
    "identity",
    "inspect_ap",
    "stable_bytes",
    "tool_identities",
    "transform_image",
    "validate_image",
    "validate_rollback_ap",
]
