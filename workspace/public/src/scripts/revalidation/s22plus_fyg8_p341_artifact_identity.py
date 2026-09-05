#!/usr/bin/env python3
"""Host-only P3.41 Image/AP identity binding.

P3.41 starts from the completed, consumed P3.40 Image.  The only Image
changes are the 32-byte run-ID string outside IKCONFIG and its exact
configuration line inside the existing gzip-9 stream.  The transform is
same-size and uses the already-qualified P340 identity helper primitives;
there is no device, ADB, Odin, or partition operation here.
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Mapping
import zlib

import s22plus_fyg8_p340_artifact_identity as predecessor


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 13_027,
    "sha256": "04dae7101d303a17c31ff494998df913d9f2ebde7e5582a2e703984197e4087f",
}
P340_PREDECESSOR_RUN_ID_HEX = "c340f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P340_PREDECESSOR_RUN_ID = bytes.fromhex(P340_PREDECESSOR_RUN_ID_HEX)
P341_RUN_ID_HEX = "c341f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P341_RUN_ID = bytes.fromhex(P341_RUN_ID_HEX)

P340_IMAGE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p340/stock-candidate-build-v1-20260905-01/"
    "inputs/fixed-Image"
)
P340_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "4c204f334800a13998c198471e274606878e057d84ce7c30b90c7fa6efd84f0a",
}
P340_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "114523aa5ca40dd66fbaa67301f2a91f7a5ecf79b1716f0e57ef6973865dbd7f",
}

# Filled after the deterministic transform is checked.  Keeping this value
# explicit makes later builder/manifest joins pin the actual P341 Image.
P341_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "7ede2bc496fdffcf98140106caa2c42ee957536b04b45b1778071128bc95144a",
}

IKCONFIG_ST = predecessor.IKCONFIG_ST
IKCONFIG_ED = predecessor.IKCONFIG_ED
IKCONFIG_OFFSET = predecessor.IKCONFIG_OFFSET
IKCONFIG_END_OFFSET = predecessor.IKCONFIG_END_OFFSET
IKCONFIG_COMPRESSED_SIZE = predecessor.IKCONFIG_COMPRESSED_SIZE
GZIP_HEADER = predecessor.GZIP_HEADER
RUN_CONFIG_KEY = predecessor.RUN_CONFIG_KEY
UNSAT_CONFIG_KEY = predecessor.UNSAT_CONFIG_KEY
P341_UNSAT_TAG_HEX = predecessor.P339_UNSAT_TAG_HEX
IMAGE_SECTION_LAYOUT = predecessor.IMAGE_SECTION_LAYOUT
LZ4 = predecessor.LZ4
LZ4_IDENTITY = predecessor.LZ4_IDENTITY
MAGISKBOOT = predecessor.MAGISKBOOT
MAGISKBOOT_IDENTITY = predecessor.MAGISKBOOT_IDENTITY
AUTH_KEY_SCHEMA = predecessor.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
AUTH_KEY_MODE = predecessor.AUTH_KEY_MODE


class ArtifactIdentityError(ValueError):
    """An Image, init, AP, or rollback identity is not exact."""


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


def stable_bytes(
    path: Path,
    label: str,
    maximum: int = 128 * 1024 * 1024,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
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
        or len(payload) > maximum
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise ArtifactIdentityError(f"{label} identity differs")
    return payload


if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
    raise ArtifactIdentityError("P3.40 artifact helper source identity differs")
if predecessor.P340_RUN_ID_HEX != P340_PREDECESSOR_RUN_ID_HEX:
    raise ArtifactIdentityError("P3.40 artifact helper binding differs")

_INNER = predecessor._INNER


def _gzip_config(image: bytes, label: str) -> tuple[int, int, bytes, bytes]:
    try:
        return _INNER._gzip_config(image, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _config_values(config: bytes, label: str) -> dict[str, str]:
    try:
        return _INNER._config_values(config, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _section_receipts(image: bytes, label: str) -> dict[str, dict[str, Any]]:
    try:
        return _INNER._section_receipts(image, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _recompress_config(config: bytes) -> bytes:
    try:
        value = _INNER._recompress_config(config)
    except Exception as exc:
        raise ArtifactIdentityError("IKCONFIG recompression failed") from exc
    if value[: len(GZIP_HEADER)] != GZIP_HEADER:
        raise ArtifactIdentityError("IKCONFIG gzip header differs")
    return value


def _stale_counts(payload: bytes) -> dict[str, int]:
    ids = {
        "b9cc424d0d184f5accbce94a844e817d",
        "c320f1e0a90b5e6d7c8a9b0c1d2e3f40",
        "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        "c322f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        "c327f1e0a90b5e6d7c8a9b0c1d2e3f3b",
        "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b",
        "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b",
        "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b",
        "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b",
        "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b",
        "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b",
        "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b",
        "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b",
        "c336f1e0a90b5e6d7c8a9b0c1d2e3f4b",
        "c337f1e0a90b5e6d7c8a9b0c1d2e3f3b",
        "c338f1e0a90b5e6d7c8a9b0c1d2e3f2b",
        "c339f1e0a90b5e6d7c8a9b0c1d2e3f1b",
        P340_PREDECESSOR_RUN_ID_HEX,
    }
    return {value: payload.count(value.encode("ascii")) for value in sorted(ids)}


def validate_image(image: bytes, *, expected_run_id: bytes = P341_RUN_ID) -> dict[str, Any]:
    if type(expected_run_id) is not bytes or expected_run_id != P341_RUN_ID:
        raise ArtifactIdentityError("P3.41 Image run ID differs")
    compressed_start, end, compressed, config = _gzip_config(image, "P341 Image")
    values = _config_values(config, "P341 Image")
    run_match = re.fullmatch(r'"([0-9a-f]{32})"', values[RUN_CONFIG_KEY])
    unsat_match = re.fullmatch(r'"([0-9a-f]{32})"', values[UNSAT_CONFIG_KEY])
    if run_match is None or unsat_match is None or run_match.group(1) != P341_RUN_ID_HEX:
        raise ArtifactIdentityError("P341 Image IKCONFIG run ID differs")
    if values[UNSAT_CONFIG_KEY] != f'"{P341_UNSAT_TAG_HEX}"':
        raise ArtifactIdentityError("P341 Image IKCONFIG UNSAT tag differs")
    outside = image[:compressed_start] + image[end:]
    raw_counts = _stale_counts(outside)
    raw_counts[P341_RUN_ID_HEX] = outside.count(P341_RUN_ID_HEX.encode("ascii"))
    if raw_counts[P341_RUN_ID_HEX] != 1 or any(
        count != 0 for key, count in raw_counts.items() if key != P341_RUN_ID_HEX
    ):
        raise ArtifactIdentityError("P341 Image raw run-ID occurrences are not exact")
    raw_offset = image.find(P341_RUN_ID_HEX.encode("ascii"))
    if raw_offset < 0 or compressed_start <= raw_offset < end:
        raise ArtifactIdentityError("P341 Image raw run-ID is inside IKCONFIG")
    sections = _section_receipts(image, "P341 Image")
    return {
        "identity": identity(image),
        "run_id_hex": P341_RUN_ID_HEX,
        "ikconfig": {
            "start_offset": compressed_start - len(IKCONFIG_ST),
            "end_offset": end,
            "compressed": identity(compressed),
            "decompressed": identity(config),
            "compression": "gzip",
            "gzip_header_hex": compressed[: len(GZIP_HEADER)].hex(),
            "run_id_hex": run_match.group(1),
            "unsat_tag_hex": unsat_match.group(1),
            "config_values": {
                RUN_CONFIG_KEY: values[RUN_CONFIG_KEY],
                UNSAT_CONFIG_KEY: values[UNSAT_CONFIG_KEY],
            },
            "marker_counts": {"IKCFG_ST": 1, "IKCFG_ED": 1},
        },
        "raw_run_id": {"offset": raw_offset, "counts_outside_ikconfig": raw_counts},
        "sections": sections,
        "layout_preserved": True,
    }


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Replace only P340's run ID and its exact same-size IKCONFIG stream."""
    if identity(original) != P340_IMAGE_IDENTITY:
        raise ArtifactIdentityError("P3.40 source Image identity differs")
    compressed_start, end, compressed, config = _gzip_config(original, "P3.40 source Image")
    values = _config_values(config, "P3.40 source Image")
    old_line = f'{RUN_CONFIG_KEY}="{P340_PREDECESSOR_RUN_ID_HEX}"'.encode("ascii")
    new_line = f'{RUN_CONFIG_KEY}="{P341_RUN_ID_HEX}"'.encode("ascii")
    if config.count(old_line) != 1 or config.count(new_line):
        raise ArtifactIdentityError("P3.40 source IKCONFIG run-ID line is not exact")
    if values[UNSAT_CONFIG_KEY] != f'"{P341_UNSAT_TAG_HEX}"':
        raise ArtifactIdentityError("P3.40 source UNSAT tag differs")
    old_raw = P340_PREDECESSOR_RUN_ID_HEX.encode("ascii")
    new_raw = P341_RUN_ID_HEX.encode("ascii")
    outside = original[:compressed_start] + original[end:]
    if outside.count(old_raw) != 1 or outside.count(new_raw):
        raise ArtifactIdentityError("P3.40 source raw run-ID occurrence is not unique")
    raw_offset = original.find(old_raw)
    if raw_offset < 0 or compressed_start <= raw_offset < end:
        raise ArtifactIdentityError("P3.40 source raw run-ID is inside IKCONFIG")
    transformed_config = config.replace(old_line, new_line, 1)
    transformed_compressed = _recompress_config(transformed_config)
    if (
        len(transformed_compressed) != len(compressed)
        or zlib.decompress(transformed_compressed, 31) != transformed_config
    ):
        raise ArtifactIdentityError("P3.41 IKCONFIG gzip transform is not same-length exact")
    transformed = original[:compressed_start] + transformed_compressed + original[end:]
    transformed = transformed[:raw_offset] + new_raw + transformed[raw_offset + len(old_raw) :]
    if len(transformed) != len(original):
        raise ArtifactIdentityError("P3.41 Image size changed during transform")
    checked = validate_image(transformed)
    return transformed, {
        "method": "identity_only_post_link_v1",
        "source": {"run_id_hex": P340_PREDECESSOR_RUN_ID_HEX, **identity(original)},
        "target": {"run_id_hex": P341_RUN_ID_HEX, **identity(transformed)},
        "raw_rodata": {
            "offset": raw_offset,
            "size": len(old_raw),
            "old_ascii": P340_PREDECESSOR_RUN_ID_HEX,
            "new_ascii": P341_RUN_ID_HEX,
            "old_count_outside_ikconfig": 1,
            "new_count_outside_ikconfig": 1,
        },
        "ikconfig": {
            "start_offset": compressed_start - len(IKCONFIG_ST),
            "end_offset": end,
            "compressed_size": len(compressed),
            "old_compressed": identity(compressed),
            "new_compressed": identity(transformed_compressed),
            "decompressed_old": identity(config),
            "decompressed_new": identity(transformed_config),
            "gzip_header_hex": GZIP_HEADER.hex(),
            "gzip_level": 9,
            "gzip_wbits": 31,
            "gzip_mem_level": 8,
            "gzip_strategy": "Z_DEFAULT_STRATEGY",
            "os_byte": GZIP_HEADER[-1],
            "old_line_count": 1,
            "new_line_count": 1,
        },
        "preserved": {
            "image_size": True,
            "ikconfig_offsets": True,
            "ikconfig_markers": True,
            "section_layout_and_sha256": True,
            "prel32_export_and_crc_regions": True,
            "outside_declared_spans": True,
            "ab_reproduction": True,
        },
        "validated": checked["identity"] == identity(transformed),
    }


def _validate_init(init: bytes, expected_run_id: bytes = P341_RUN_ID) -> dict[str, Any]:
    if type(expected_run_id) is not bytes or expected_run_id != P341_RUN_ID:
        raise ArtifactIdentityError("P3.41 init run ID differs")
    counts = _stale_counts(init)
    counts[P341_RUN_ID_HEX] = init.count(P341_RUN_ID)
    if counts[P341_RUN_ID_HEX] != 1 or any(
        count != 0 for key, count in counts.items() if key != P341_RUN_ID_HEX
    ):
        raise ArtifactIdentityError("P341 /init run-ID occurrences are not exact")
    return {"identity": identity(init), "run_id_hex": P341_RUN_ID_HEX, "counts": counts}


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P341_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P341 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P341_RUN_ID:
        raise ArtifactIdentityError("P3.41 AP run ID differs")
    payload = stable_bytes(ap_path, label, 128 * 1024 * 1024, nlink=1)
    ap_identity = identity(payload)
    if expected_ap is not None and ap_identity != dict(expected_ap):
        raise ArtifactIdentityError(f"{label} AP identity differs")
    try:
        frame, ap_structure = _INNER._parse_ap(payload, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc
    with tempfile.TemporaryDirectory(prefix="p341-ap-identity-") as temporary:
        work = Path(temporary)
        frame_path = work / "boot.img.lz4"
        boot_path = work / "boot.img"
        frame_path.write_bytes(frame)
        _INNER._run([str(LZ4), "-d", "-f", "-q", str(frame_path), str(boot_path)], work, f"{label} LZ4 decode")
        _INNER._run([str(MAGISKBOOT), "unpack", "-h", str(boot_path)], work, f"{label} boot unpack")
        boot = stable_bytes(boot_path, f"{label} boot", 128 * 1024 * 1024)
        image = stable_bytes(work / "kernel", f"{label} Image", 64 * 1024 * 1024)
        if expected_image is not None and image != expected_image:
            raise ArtifactIdentityError(f"{label} packaged Image differs")
        image_result = validate_image(image, expected_run_id=P341_RUN_ID)
        ramdisk = work / "ramdisk.cpio"
        init_path = work / "init"
        child_path = work / "child"
        _INNER._run([str(MAGISKBOOT), "cpio", str(ramdisk), f"extract init {init_path}"], work, f"{label} init extract")
        _INNER._run([str(MAGISKBOOT), "cpio", str(ramdisk), f"extract s22-e1-child {child_path}"], work, f"{label} child extract")
        init = stable_bytes(init_path, f"{label} /init", 2 * 1024 * 1024)
        child = stable_bytes(child_path, f"{label} child", 2 * 1024 * 1024)
    if expected_init is not None and init != expected_init:
        raise ArtifactIdentityError(f"{label} packaged /init differs")
    if expected_child is not None and child != expected_child:
        raise ArtifactIdentityError(f"{label} packaged child differs")
    init_result = _validate_init(init, P341_RUN_ID)
    if image_result["run_id_hex"] != init_result["run_id_hex"]:
        raise ArtifactIdentityError(f"{label} Image/init run-ID join differs")
    return {
        "ap": ap_identity,
        "ap_structure": ap_structure,
        "boot_img_lz4": identity(frame),
        "boot_img": identity(boot),
        "image": image_result,
        "init": init_result,
        "child": identity(child),
        "run_id_hex": P341_RUN_ID_HEX,
        "joined": True,
        "boot_only": True,
    }


STALE_AP_IDENTITIES = tuple(
    [dict(value) for value in predecessor.STALE_AP_IDENTITIES]
    + [dict(P340_AP_IDENTITY)]
)


def validate_rollback_ap(
    ap_path: Path,
    expected: Mapping[str, Any],
    *,
    label: str = "P341 exact rollback AP",
) -> dict[str, Any]:
    if any(dict(expected) == value for value in STALE_AP_IDENTITIES):
        raise ArtifactIdentityError("consumed predecessor candidate AP is not rollback")
    try:
        return _INNER.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_p341_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p341_artifact_identity_v1",
        "run_id_hex": P341_RUN_ID_HEX,
        "predecessor_run_id_rejected": P340_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P340_AP_IDENTITY),
        "boot_only": True,
        "ab_must_match": True,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key_size": AUTH_KEY_SIZE,
        "auth_key_path_published": False,
        "host_first_open": True,
        "host_open_before_banner": True,
        "device_banner_after_open": True,
        "stage_zero_after_banner": True,
        "open_parsed_after_stage_zero": True,
        "no_unsolicited_device_tx": True,
        "silent_no_peer_no_proof": True,
        "consumed_partial_open_no_replay": True,
    }


def __getattr__(name: str) -> Any:
    return getattr(predecessor, name)


__all__ = sorted(
    {
        "AUTH_KEY_MODE", "AUTH_KEY_SCHEMA", "AUTH_KEY_SIZE", "ArtifactIdentityError",
        "GZIP_HEADER", "IMAGE_SECTION_LAYOUT", "IKCONFIG_COMPRESSED_SIZE",
        "IKCONFIG_ED", "IKCONFIG_END_OFFSET", "IKCONFIG_OFFSET", "IKCONFIG_ST",
        "LZ4", "LZ4_IDENTITY", "MAGISKBOOT", "MAGISKBOOT_IDENTITY", "P340_AP_IDENTITY",
        "P340_IMAGE", "P340_IMAGE_IDENTITY", "P340_PREDECESSOR_RUN_ID",
        "P340_PREDECESSOR_RUN_ID_HEX", "P341_IMAGE_IDENTITY", "P341_RUN_ID",
        "P341_RUN_ID_HEX", "P341_UNSAT_TAG_HEX", "RUN_CONFIG_KEY", "SOURCE",
        "SOURCE_IDENTITY", "STALE_AP_IDENTITIES", "UNSAT_CONFIG_KEY", "identity",
        "inspect_ap", "stable_bytes", "transform_image", "validate_image",
        "validate_p341_identity", "validate_rollback_ap",
    }
)
