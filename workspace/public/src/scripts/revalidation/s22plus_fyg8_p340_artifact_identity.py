#!/usr/bin/env python3
"""Host-only P3.40 boot-only artifact identity.

P3.40 is an identity-only successor to the consumed P3.39 build.  The
verified P3.39 artifact helper is loaded into a private module graph; only the
fresh run ID is rebound.  The Image transform is deliberately local because
the predecessor Image, rather than the original P3.19 Image, is the input.
No device, ADB, Odin, or live-authority operation is exposed here.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
import zlib
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).with_name("s22plus_fyg8_p339_artifact_identity.py")
P339_SOURCE = SOURCE
P339_SOURCE_IDENTITY = {"size": 10_570, "sha256": "bb07485760f3f564d4d044c45ea7b12afd2ff8ab29e05fb19b0be276fe1a623b"}
P339_PREDECESSOR_RUN_ID_HEX = "c339f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P339_PREDECESSOR_RUN_ID = bytes.fromhex(P339_PREDECESSOR_RUN_ID_HEX)
P339_AP_IDENTITY = {"size": 28_631_081, "sha256": "80830eed6818528577e3dd5d68af79743b55a014b1dd4e2c8a3c5f54711b47d3"}
P340_RUN_ID_HEX = "c340f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P340_RUN_ID = bytes.fromhex(P340_RUN_ID_HEX)


class ArtifactIdentityError(ValueError):
    """The exact P3.39 artifact or fresh P3.40 binding differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _load_p339() -> types.ModuleType:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(2 * 1024 * 1024 + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ArtifactIdentityError("P3.39 artifact helper is unavailable") from exc
    if (
        direct != resolved or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
        or _inode(before) != _inode(inside) or _inode(before) != _inode(after)
        or len(payload) != before.st_size or len(payload) > 2 * 1024 * 1024
        or identity(payload) != P339_SOURCE_IDENTITY
    ):
        raise ArtifactIdentityError("P3.39 artifact helper identity differs")
    module = types.ModuleType("s22plus_fyg8_p339_artifact_bound_for_p340")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise ArtifactIdentityError("P3.39 artifact helper failed to load") from exc
    if getattr(module, "P339_RUN_ID_HEX", None) != P339_PREDECESSOR_RUN_ID_HEX:
        raise ArtifactIdentityError("P3.39 artifact binding differs")
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
            if (name.startswith("_P") or name in {"_BASE", "_INNER"}) and isinstance(value, types.ModuleType):
                pending.append(value)
    return result


_P339 = _load_p339()
for _module in _modules(_P339):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P339_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P340_RUN_ID)
        elif _value == P339_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P340_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            defaults = dict(_value.__kwdefaults__)
            changed = False
            for key, current in tuple(defaults.items()):
                if current == P339_PREDECESSOR_RUN_ID:
                    defaults[key] = P340_RUN_ID
                    changed = True
                elif current == P339_PREDECESSOR_RUN_ID_HEX:
                    defaults[key] = P340_RUN_ID_HEX
                    changed = True
            if changed:
                _value.__kwdefaults__ = defaults


_BASE = _P339._BASE
_INNER = _BASE._INNER
RUN_CONFIG_KEY = _INNER.RUN_CONFIG_KEY
UNSAT_CONFIG_KEY = _INNER.UNSAT_CONFIG_KEY
IKCONFIG_ST = _INNER.IKCONFIG_ST
IKCONFIG_ED = _INNER.IKCONFIG_ED
P339_UNSAT_TAG_HEX = _INNER.P319_UNSAT_TAG_HEX
P339_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "7c73b3803d67eec03968ebaa45c51d7f757853c4edefa21845c48a8455465a3e",
}
_ORIGINAL_REJECT = _BASE._reject_stale_image_ids
_ORIGINAL_VALIDATE_INIT = _BASE._validate_init


def _reject_stale_image_ids(image: bytes) -> None:
    _ORIGINAL_REJECT(image)
    try:
        start, end, _compressed, _config = _INNER._gzip_config(image, "P340 Image")
    except Exception:
        return
    if P339_PREDECESSOR_RUN_ID_HEX.encode("ascii") in image[:start] + image[end:]:
        raise ArtifactIdentityError("P3.39 Image contains the predecessor run ID")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    if expected_run_id != P340_RUN_ID:
        raise ArtifactIdentityError("P3.40 init run ID differs")
    if P339_PREDECESSOR_RUN_ID in init:
        raise ArtifactIdentityError("P3.40 init contains the predecessor run ID")
    try:
        return _ORIGINAL_VALIDATE_INIT(init, P340_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


_BASE._reject_stale_image_ids = _reject_stale_image_ids
_BASE._validate_init = _validate_init
_INNER.validate_image = _BASE.validate_image
_INNER._validate_init = _validate_init
_P339.STALE_AP_IDENTITIES = tuple((*_P339.STALE_AP_IDENTITIES, dict(P339_AP_IDENTITY)))

for _function_name, _updates in (
    ("validate_image", {"expected_run_id": P340_RUN_ID}),
    ("inspect_ap", {"expected_run_id": P340_RUN_ID, "label": "P340 candidate AP"}),
):
    _function = getattr(_INNER, _function_name, None)
    if _function is not None:
        defaults = dict(getattr(_function, "__kwdefaults__", {}) or {})
        defaults.update(_updates)
        _function.__kwdefaults__ = defaults

for _name in getattr(_P339, "__all__", ()):
    if hasattr(_P339, _name):
        globals()[_name] = getattr(_P339, _name)

SOURCE = Path(__file__).with_name("s22plus_fyg8_p339_artifact_identity.py")
SOURCE_IDENTITY = dict(P339_SOURCE_IDENTITY)
P339_RUN_ID_HEX = P340_RUN_ID_HEX
P339_RUN_ID = P340_RUN_ID
P340_ARTIFACT_SOURCE = Path(__file__).resolve()
P339_ARTIFACT_SOURCE = P340_ARTIFACT_SOURCE
STALE_AP_IDENTITIES = _P339.STALE_AP_IDENTITIES


def validate_image(image: bytes, *, expected_run_id: bytes = P340_RUN_ID) -> dict[str, Any]:
    if expected_run_id != P340_RUN_ID:
        raise ArtifactIdentityError("P3.40 Image run ID differs")
    try:
        return _P339.validate_image(image, expected_run_id=P340_RUN_ID)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Change only the P339 run ID and its exact embedded IKCONFIG stream."""
    if identity(original) != P339_IMAGE_IDENTITY:
        raise ArtifactIdentityError("P3.39 source Image identity differs")
    compressed_start, end, compressed, config = _INNER._gzip_config(original, "P3.39 source Image")
    values = _INNER._config_values(config, "P3.39 source Image")
    old_line = f'{RUN_CONFIG_KEY}="{P339_PREDECESSOR_RUN_ID_HEX}"'.encode("ascii")
    new_line = f'{RUN_CONFIG_KEY}="{P340_RUN_ID_HEX}"'.encode("ascii")
    if config.count(old_line) != 1 or config.count(new_line):
        raise ArtifactIdentityError("P3.39 source IKCONFIG run-ID line is not exact")
    if values[UNSAT_CONFIG_KEY] != f'"{P339_UNSAT_TAG_HEX}"':
        raise ArtifactIdentityError("P3.39 source UNSAT tag differs")
    old_raw = P339_PREDECESSOR_RUN_ID_HEX.encode("ascii")
    new_raw = P340_RUN_ID_HEX.encode("ascii")
    outside = original[:compressed_start] + original[end:]
    if outside.count(old_raw) != 1 or outside.count(new_raw):
        raise ArtifactIdentityError("P3.39 source raw run-ID occurrence is not unique")
    raw_offset = original.find(old_raw)
    if raw_offset < 0 or compressed_start <= raw_offset < end:
        raise ArtifactIdentityError("P3.39 source raw run-ID is inside IKCONFIG")
    transformed_config = config.replace(old_line, new_line, 1)
    transformed_compressed = _INNER._recompress_config(transformed_config)
    if (
        len(transformed_compressed) != len(compressed)
        or transformed_compressed[: len(GZIP_HEADER)] != GZIP_HEADER
        or zlib.decompress(transformed_compressed, 31) != transformed_config
    ):
        raise ArtifactIdentityError("P3.40 IKCONFIG gzip transform is not same-length exact")
    transformed = original[:compressed_start] + transformed_compressed + original[end:]
    transformed = transformed[:raw_offset] + new_raw + transformed[raw_offset + len(old_raw):]
    if len(transformed) != len(original):
        raise ArtifactIdentityError("P3.40 Image size changed during transform")
    checked = validate_image(transformed)
    return transformed, {
        "method": "identity_only_post_link_v1",
        "source": {"run_id_hex": P339_PREDECESSOR_RUN_ID_HEX, **identity(original)},
        "target": {"run_id_hex": P340_RUN_ID_HEX, **identity(transformed)},
        "raw_rodata": {
            "offset": raw_offset, "size": len(old_raw),
            "old_ascii": P339_PREDECESSOR_RUN_ID_HEX, "new_ascii": P340_RUN_ID_HEX,
            "old_count_outside_ikconfig": 1, "new_count_outside_ikconfig": 1,
        },
        "ikconfig": {
            "start_offset": compressed_start - len(IKCONFIG_ST), "end_offset": end,
            "compressed_size": len(compressed), "old_compressed": identity(compressed),
            "new_compressed": identity(transformed_compressed),
            "decompressed_old": identity(config), "decompressed_new": identity(transformed_config),
            "gzip_header_hex": GZIP_HEADER.hex(), "gzip_level": 9, "gzip_wbits": 31,
            "gzip_mem_level": 8, "gzip_strategy": "Z_DEFAULT_STRATEGY", "os_byte": GZIP_HEADER[-1],
            "old_line_count": 1, "new_line_count": 1,
        },
        "preserved": {
            "image_size": True, "ikconfig_offsets": True, "ikconfig_markers": True,
            "section_layout_and_sha256": True, "prel32_export_and_crc_regions": True,
            "outside_declared_spans": True, "ab_reproduction": True,
        },
        "validated": checked["identity"] == identity(transformed),
    }


def inspect_ap(
    ap_path: Path, *, expected_run_id: bytes = P340_RUN_ID,
    expected_image: bytes | None = None, expected_init: bytes | None = None,
    expected_child: bytes | None = None, expected_ap: Mapping[str, Any] | None = None,
    label: str = "P340 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P340_RUN_ID:
        raise ArtifactIdentityError("P3.40 AP run ID differs")
    try:
        return _P339.inspect_ap(
            ap_path, expected_run_id=P340_RUN_ID, expected_image=expected_image,
            expected_init=expected_init, expected_child=expected_child,
            expected_ap=expected_ap, label=label,
        )
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_rollback_ap(
    ap_path: Path, expected: Mapping[str, Any], *, label: str = "P340 exact rollback AP"
) -> dict[str, Any]:
    if dict(expected) == P339_AP_IDENTITY:
        raise ArtifactIdentityError("consumed P339 candidate AP is not rollback")
    try:
        return _P339.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_p340_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p340_artifact_identity_v1",
        "run_id_hex": P340_RUN_ID_HEX,
        "predecessor_run_id_rejected": P339_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P339_AP_IDENTITY),
        "boot_only": True, "ab_must_match": True,
        "auth_key_schema": AUTH_KEY_SCHEMA, "auth_key_size": AUTH_KEY_SIZE,
        "auth_key_path_published": False,
    }


__all__ = sorted(
    set(getattr(_P339, "__all__", ()))
    | {
        "ArtifactIdentityError", "P339_AP_IDENTITY", "P339_ARTIFACT_SOURCE",
        "P339_PREDECESSOR_RUN_ID", "P339_PREDECESSOR_RUN_ID_HEX",
        "P339_RUN_ID", "P339_RUN_ID_HEX", "P339_SOURCE", "P339_SOURCE_IDENTITY",
        "P340_ARTIFACT_SOURCE", "P340_RUN_ID", "P340_RUN_ID_HEX", "STALE_AP_IDENTITIES",
        "SOURCE", "SOURCE_IDENTITY", "inspect_ap", "transform_image", "validate_image",
        "validate_p340_identity", "validate_rollback_ap",
    }
)
