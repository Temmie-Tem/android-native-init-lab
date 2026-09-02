#!/usr/bin/env python3
"""Fresh P3.28 Image/AP identity and exact host auth-key binding.

This is a deliberately small successor boundary.  The consumed P3.27
artifact helper is loaded from its pinned source bytes, while the same-length
Image transform and boot-only AP checks are delegated to that helper.  The
only new host input is the purpose-bound 32-byte authentication key.  This
module never creates a key, contacts a device, or invokes Odin.
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
P327_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p327_artifact_identity.py"
P327_ARTIFACT_IDENTITY = {
    "size": 8_450,
    "sha256": "f228e6a8a3938dd3f14c555b4fab144b43d1fcd48c7e7647a2a34faabead2955",
}

P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P322_RUN_ID_HEX = "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_RUN_ID_HEX = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P326_RUN_ID_HEX = "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P327_RUN_ID_HEX = "c327f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P328_RUN_ID_HEX = "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P327_RUN_ID = bytes.fromhex(P327_RUN_ID_HEX)
P328_RUN_ID = bytes.fromhex(P328_RUN_ID_HEX)
P327_PREDECESSOR_RUN_ID_HEX = P327_RUN_ID_HEX
P327_PREDECESSOR_RUN_ID = P327_RUN_ID
# Compatibility names consumed by the nested P3.27/P3.26 builders.
P326_PREDECESSOR_RUN_ID_HEX = P327_PREDECESSOR_RUN_ID_HEX
P326_PREDECESSOR_RUN_ID = P327_PREDECESSOR_RUN_ID
P325_PREDECESSOR_RUN_ID_HEX = P327_PREDECESSOR_RUN_ID_HEX
P325_PREDECESSOR_RUN_ID = P327_PREDECESSOR_RUN_ID
P324_PREDECESSOR_RUN_ID_HEX = P327_PREDECESSOR_RUN_ID_HEX
P324_PREDECESSOR_RUN_ID = P327_PREDECESSOR_RUN_ID
P323_PREDECESSOR_RUN_ID_HEX = P327_PREDECESSOR_RUN_ID_HEX
P323_PREDECESSOR_RUN_ID = P327_PREDECESSOR_RUN_ID
P321_PREDECESSOR_RUN_ID_HEX = P327_PREDECESSOR_RUN_ID_HEX
P321_PREDECESSOR_RUN_ID = P327_PREDECESSOR_RUN_ID

DEFAULT_AUTH_KEY_PATH = ROOT / (
    "workspace/private/inputs/s22plus_fyg8_p328/auth-key-v1.bin"
)
AUTH_KEY_SIZE = 32
AUTH_KEY_MODE = 0o400
AUTH_KEY_SCHEMA = "s22plus_fyg8_p328_auth_key_v1"


class ArtifactIdentityError(ValueError):
    """The P3.27 delegate, P3.28 identity, or auth key is not exact."""


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


def _stable_source(path: Path, label: str, expected: Mapping[str, Any]) -> bytes:
    """Read exact regular bytes while rejecting path and inode substitution."""
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
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != dict(expected)
    ):
        raise ArtifactIdentityError(f"{label} identity differs")
    return payload


def read_auth_key(path: Path | str = DEFAULT_AUTH_KEY_PATH) -> bytes:
    """Read one direct 0400, single-link, exactly 32-byte auth key.

    Key bytes are returned only to the host-side runtime transformer.  Callers
    that publish a result must use :func:`auth_key_identity`; that projection
    intentionally contains no path or key bytes.
    """
    direct = Path(path).absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(AUTH_KEY_SIZE + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ArtifactIdentityError("P328 auth key is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or stat.S_IMODE(before.st_mode) != AUTH_KEY_MODE
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or before.st_size != AUTH_KEY_SIZE
        or len(payload) != AUTH_KEY_SIZE
    ):
        raise ArtifactIdentityError("P328 auth key identity differs")
    return payload


def auth_key_identity(path: Path | str = DEFAULT_AUTH_KEY_PATH) -> dict[str, Any]:
    """Return the path-free public identity of one exact auth key."""
    return identity(read_auth_key(path))


def validate_auth_key(value: bytes) -> dict[str, Any]:
    """Validate already-read key bytes and return only its public identity."""
    if type(value) is not bytes or len(value) != AUTH_KEY_SIZE:
        raise ArtifactIdentityError("P328 auth key bytes differ")
    return identity(value)


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(
        P327_ARTIFACT_SOURCE, "P3.27 artifact helper", P327_ARTIFACT_IDENTITY
    )
    module = types.ModuleType("s22plus_fyg8_p327_artifact_bound_for_p328")
    module.__file__ = str(P327_ARTIFACT_SOURCE)
    module.__package__ = ""
    try:
        exec(  # noqa: S102 - exact, hash-pinned source closure loading
            compile(payload, str(P327_ARTIFACT_SOURCE), "exec", dont_inherit=True),
            module.__dict__,
        )
    except Exception as exc:
        raise ArtifactIdentityError("P3.27 artifact helper failed to load") from exc
    if getattr(module, "P327_RUN_ID_HEX", None) != P327_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.27 artifact identity differs")
    return module


_P327 = _load_delegate()
_INNER = _P327._INNER
for _module in (
    _P327,
    _P327._P326,
    _P327._P326._P325,
    _P327._P326._P325._P324,
    _INNER,
):
    for _name in (
        "P321_RUN_ID_HEX",
        "P322_RUN_ID_HEX",
        "P323_RUN_ID_HEX",
        "P324_RUN_ID_HEX",
        "P325_RUN_ID_HEX",
        "P326_RUN_ID_HEX",
        "P327_RUN_ID_HEX",
    ):
        if hasattr(_module, _name):
            setattr(_module, _name, P328_RUN_ID_HEX)
    for _name in (
        "P321_RUN_ID",
        "P322_RUN_ID",
        "P323_RUN_ID",
        "P324_RUN_ID",
        "P325_RUN_ID",
        "P326_RUN_ID",
        "P327_RUN_ID",
    ):
        if hasattr(_module, _name):
            setattr(_module, _name, P328_RUN_ID)


def _reject_stale_image_ids(image: bytes) -> None:
    try:
        compressed_start, end, _compressed, _config = _INNER._gzip_config(
            image, "P328 Image"
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
        P326_RUN_ID_HEX,
        P327_RUN_ID_HEX,
    ):
        if old.encode("ascii") in outside:
            raise ArtifactIdentityError(f"P328 Image contains stale run ID {old}")


def validate_image(
    image: bytes, *, expected_run_id: bytes = P328_RUN_ID
) -> dict[str, Any]:
    if expected_run_id != P328_RUN_ID:
        raise ArtifactIdentityError("P328 Image run ID differs")
    _reject_stale_image_ids(image)
    try:
        return _P327._P326._P325._ORIGINAL_VALIDATE_IMAGE(
            image, expected_run_id=P328_RUN_ID
        )
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P328_RUN_ID:
        raise ArtifactIdentityError("P328 init run ID differs")
    for old in (
        P319_RUN_ID_HEX,
        P320_RUN_ID_HEX,
        P321_RUN_ID_HEX,
        P322_RUN_ID_HEX,
        P323_RUN_ID_HEX,
        P324_RUN_ID_HEX,
        P325_RUN_ID_HEX,
        P326_RUN_ID_HEX,
        P327_RUN_ID_HEX,
    ):
        if bytes.fromhex(old) in init:
            raise ArtifactIdentityError(f"P328 init contains stale run ID {old}")
    try:
        return _P327._P326._P325._ORIGINAL_VALIDATE_INIT(init, P328_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_INNER.validate_image = validate_image
_INNER._validate_init = _validate_init
for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P328_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P328_RUN_ID, "label": "P328 candidate AP"}),
    ("validate_rollback_ap", {"label": "P328 exact rollback AP"}),
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
    if receipt.get("target", {}).get("run_id_hex") != P328_RUN_ID_HEX:
        raise ArtifactIdentityError("P328 Image transform target differs")
    validate_image(transformed)
    return transformed, receipt


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P328_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P328 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P328_RUN_ID:
        raise ArtifactIdentityError("P328 AP run ID differs")
    try:
        return _INNER.inspect_ap(
            ap_path,
            expected_run_id=P328_RUN_ID,
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
    label: str = "P328 exact rollback AP",
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
    globals()[_name] = getattr(_P327, _name)


__all__ = [name for name in globals() if not name.startswith("_")]
