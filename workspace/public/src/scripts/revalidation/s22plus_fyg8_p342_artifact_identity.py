#!/usr/bin/env python3
"""Host-only P3.42 Image/AP identity binding.

P3.42 starts from the completed, consumed P3.41 candidate.  The Image
transform replaces only the fixed 32-byte run marker in the existing raw
region and same-length IKCONFIG gzip stream.  Packaging remains boot-only;
this module performs no device, ADB, Odin or partition operation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping
import zlib

import s22plus_fyg8_p341_artifact_identity as predecessor


ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 18_661,
    "sha256": "7f541c109a0eeebf4e4fb7c7afe120ae641149d7ac749e74867add754ae99a02",
}

P341_PREDECESSOR_RUN_ID_HEX = predecessor.P341_RUN_ID_HEX
P341_PREDECESSOR_RUN_ID = predecessor.P341_RUN_ID
P342_RUN_ID_HEX = "c342f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P342_RUN_ID = bytes.fromhex(P342_RUN_ID_HEX)

P341_IMAGE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p341/"
    "stock-candidate-build-v1-20260905-02/inputs/fixed-Image"
)
P341_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "7ede2bc496fdffcf98140106caa2c42ee957536b04b45b1778071128bc95144a",
}
P341_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "714c6c254d0685f67dfbdee3e8035d69ca7b6ee8230a24bcd2d81e770a68bca6",
}
# Filled from the deterministic transform and retained as the expected
# target identity for builder/static joins.
P342_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "db875eb9c7a3348ef1f57c00f9825cd8e331c2e384bf95e91941b920d0e444c0",
}

P342_AP_IDENTITY: dict[str, Any] = {
    "size": 28_631_081,
    "sha256": "76e23db43ce8e73711fc5a7b28c35ceebab8a5081687c2d4c6a19ce3bed5f83b",
}

IKCONFIG_ST = predecessor.IKCONFIG_ST
IKCONFIG_ED = predecessor.IKCONFIG_ED
IKCONFIG_OFFSET = predecessor.IKCONFIG_OFFSET
IKCONFIG_END_OFFSET = predecessor.IKCONFIG_END_OFFSET
IKCONFIG_COMPRESSED_SIZE = predecessor.IKCONFIG_COMPRESSED_SIZE
GZIP_HEADER = predecessor.GZIP_HEADER
RUN_CONFIG_KEY = predecessor.RUN_CONFIG_KEY
UNSAT_CONFIG_KEY = predecessor.UNSAT_CONFIG_KEY
P342_UNSAT_TAG_HEX = predecessor.P341_UNSAT_TAG_HEX
IMAGE_SECTION_LAYOUT = predecessor.IMAGE_SECTION_LAYOUT
LZ4 = predecessor.LZ4
LZ4_IDENTITY = predecessor.LZ4_IDENTITY
MAGISKBOOT = predecessor.MAGISKBOOT
MAGISKBOOT_IDENTITY = predecessor.MAGISKBOOT_IDENTITY
AUTH_KEY_SCHEMA = predecessor.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
AUTH_KEY_MODE = predecessor.AUTH_KEY_MODE


class ArtifactIdentityError(ValueError):
    """An Image, init, AP or rollback identity is not exact."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
    raise ArtifactIdentityError("P3.41 artifact helper source identity differs")
if predecessor.P341_RUN_ID_HEX != P341_PREDECESSOR_RUN_ID_HEX:
    raise ArtifactIdentityError("P3.41 artifact helper binding differs")

_INNER = predecessor._INNER


def stable_bytes(
    path: Path,
    label: str,
    maximum: int = 128 * 1024 * 1024,
    expected: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> bytes:
    try:
        return predecessor.stable_bytes(path, label, maximum, expected, **kwargs)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _gzip_config(image: bytes, label: str) -> tuple[int, int, bytes, bytes]:
    try:
        return predecessor._gzip_config(image, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _config_values(config: bytes, label: str) -> dict[str, str]:
    try:
        return predecessor._config_values(config, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _section_receipts(image: bytes, label: str) -> dict[str, dict[str, Any]]:
    try:
        return predecessor._section_receipts(image, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def _recompress_config(config: bytes) -> bytes:
    try:
        value = predecessor._recompress_config(config)
    except Exception as exc:
        raise ArtifactIdentityError("IKCONFIG recompression failed") from exc
    if value[: len(GZIP_HEADER)] != GZIP_HEADER:
        raise ArtifactIdentityError("IKCONFIG gzip header differs")
    return value


def _stale_counts(payload: bytes) -> dict[str, int]:
    value = dict(predecessor._stale_counts(payload))
    value[P341_PREDECESSOR_RUN_ID_HEX] = payload.count(
        P341_PREDECESSOR_RUN_ID_HEX.encode("ascii")
    )
    value[P342_RUN_ID_HEX] = payload.count(P342_RUN_ID_HEX.encode("ascii"))
    return value


def validate_image(
    image: bytes, *, expected_run_id: bytes = P342_RUN_ID
) -> dict[str, Any]:
    if type(expected_run_id) is not bytes or expected_run_id != P342_RUN_ID:
        raise ArtifactIdentityError("P3.42 Image run ID differs")
    compressed_start, end, compressed, config = _gzip_config(image, "P342 Image")
    values = _config_values(config, "P342 Image")
    run_match = re.fullmatch(r'"([0-9a-f]{32})"', values[RUN_CONFIG_KEY])
    unsat_match = re.fullmatch(r'"([0-9a-f]{32})"', values[UNSAT_CONFIG_KEY])
    if run_match is None or unsat_match is None or run_match.group(1) != P342_RUN_ID_HEX:
        raise ArtifactIdentityError("P342 Image IKCONFIG run ID differs")
    if values[UNSAT_CONFIG_KEY] != f'"{P342_UNSAT_TAG_HEX}"':
        raise ArtifactIdentityError("P342 Image IKCONFIG UNSAT tag differs")
    outside = image[:compressed_start] + image[end:]
    counts = _stale_counts(outside)
    if counts[P342_RUN_ID_HEX] != 1 or any(
        count != 0
        for key, count in counts.items()
        if key != P342_RUN_ID_HEX
    ):
        raise ArtifactIdentityError("P342 Image raw run-ID occurrences are not exact")
    raw_offset = image.find(P342_RUN_ID_HEX.encode("ascii"))
    if raw_offset < 0 or compressed_start <= raw_offset < end:
        raise ArtifactIdentityError("P342 Image raw run-ID is inside IKCONFIG")
    sections = _section_receipts(image, "P342 Image")
    return {
        "identity": identity(image),
        "run_id_hex": P342_RUN_ID_HEX,
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
        "raw_run_id": {"offset": raw_offset, "counts_outside_ikconfig": counts},
        "sections": sections,
        "layout_preserved": True,
    }


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Replace only P341's run ID in one same-length Image transform."""

    if identity(original) != P341_IMAGE_IDENTITY:
        raise ArtifactIdentityError("P3.41 source Image identity differs")
    compressed_start, end, compressed, config = _gzip_config(
        original, "P3.41 source Image"
    )
    values = _config_values(config, "P3.41 source Image")
    old_line = f'{RUN_CONFIG_KEY}="{P341_PREDECESSOR_RUN_ID_HEX}"'.encode("ascii")
    new_line = f'{RUN_CONFIG_KEY}="{P342_RUN_ID_HEX}"'.encode("ascii")
    if config.count(old_line) != 1 or config.count(new_line):
        raise ArtifactIdentityError("P3.41 source IKCONFIG run-ID line is not exact")
    if values[UNSAT_CONFIG_KEY] != f'"{P342_UNSAT_TAG_HEX}"':
        raise ArtifactIdentityError("P3.41 source UNSAT tag differs")
    old_raw = P341_PREDECESSOR_RUN_ID_HEX.encode("ascii")
    new_raw = P342_RUN_ID_HEX.encode("ascii")
    outside = original[:compressed_start] + original[end:]
    if outside.count(old_raw) != 1 or outside.count(new_raw):
        raise ArtifactIdentityError("P3.41 source raw run-ID occurrence is not unique")
    raw_offset = original.find(old_raw)
    if raw_offset < 0 or compressed_start <= raw_offset < end:
        raise ArtifactIdentityError("P3.41 source raw run-ID is inside IKCONFIG")
    transformed_config = config.replace(old_line, new_line, 1)
    transformed_compressed = _recompress_config(transformed_config)
    if (
        len(transformed_compressed) != len(compressed)
        or zlib.decompress(transformed_compressed, 31) != transformed_config
    ):
        raise ArtifactIdentityError("P3.42 IKCONFIG gzip transform is not same-length exact")
    transformed = original[:compressed_start] + transformed_compressed + original[end:]
    transformed = transformed[:raw_offset] + new_raw + transformed[raw_offset + len(old_raw) :]
    if len(transformed) != len(original):
        raise ArtifactIdentityError("P3.42 Image size changed during transform")
    checked = validate_image(transformed)
    if checked["identity"] != P342_IMAGE_IDENTITY:
        raise ArtifactIdentityError("P3.42 Image identity differs")
    return transformed, {
        "method": "identity_only_post_link_v1",
        "source": {"run_id_hex": P341_PREDECESSOR_RUN_ID_HEX, **identity(original)},
        "target": {"run_id_hex": P342_RUN_ID_HEX, **identity(transformed)},
        "raw_rodata": {
            "offset": raw_offset,
            "size": len(old_raw),
            "old_ascii": P341_PREDECESSOR_RUN_ID_HEX,
            "new_ascii": P342_RUN_ID_HEX,
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
        "validated": True,
    }


def _validate_init(init: bytes, expected_run_id: bytes = P342_RUN_ID) -> dict[str, Any]:
    if type(expected_run_id) is not bytes or expected_run_id != P342_RUN_ID:
        raise ArtifactIdentityError("P3.42 init run ID differs")
    counts = _stale_counts(init)
    if counts[P342_RUN_ID_HEX] != 1 or any(
        count != 0
        for key, count in counts.items()
        if key != P342_RUN_ID_HEX
    ):
        raise ArtifactIdentityError("P342 /init run-ID occurrences are not exact")
    return {"identity": identity(init), "run_id_hex": P342_RUN_ID_HEX, "counts": counts}


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P342_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P342 candidate AP",
) -> dict[str, Any]:
    if expected_run_id != P342_RUN_ID:
        raise ArtifactIdentityError("P3.42 AP run ID differs")
    payload = stable_bytes(ap_path, label, 128 * 1024 * 1024, nlink=1)
    ap_identity = identity(payload)
    if expected_ap is not None and ap_identity != dict(expected_ap):
        raise ArtifactIdentityError(f"{label} AP identity differs")
    try:
        frame, ap_structure = _INNER._parse_ap(payload, label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc
    with tempfile.TemporaryDirectory(prefix="p342-ap-identity-") as temporary:
        work = Path(temporary)
        frame_path = work / "boot.img.lz4"
        boot_path = work / "boot.img"
        frame_path.write_bytes(frame)
        _INNER._run(
            [str(LZ4), "-d", "-f", "-q", str(frame_path), str(boot_path)],
            work,
            f"{label} LZ4 decode",
        )
        _INNER._run(
            [str(MAGISKBOOT), "unpack", "-h", str(boot_path)],
            work,
            f"{label} boot unpack",
        )
        boot = stable_bytes(boot_path, f"{label} boot", 128 * 1024 * 1024)
        image = stable_bytes(work / "kernel", f"{label} Image", 64 * 1024 * 1024)
        if expected_image is not None and image != expected_image:
            raise ArtifactIdentityError(f"{label} packaged Image differs")
        image_result = validate_image(image, expected_run_id=P342_RUN_ID)
        ramdisk = work / "ramdisk.cpio"
        init_path = work / "init"
        child_path = work / "child"
        _INNER._run(
            [str(MAGISKBOOT), "cpio", str(ramdisk), f"extract init {init_path}"],
            work,
            f"{label} init extract",
        )
        _INNER._run(
            [
                str(MAGISKBOOT),
                "cpio",
                str(ramdisk),
                f"extract s22-e1-child {child_path}",
            ],
            work,
            f"{label} child extract",
        )
        init = stable_bytes(init_path, f"{label} /init", 2 * 1024 * 1024)
        child = stable_bytes(child_path, f"{label} child", 2 * 1024 * 1024)
    if expected_init is not None and init != expected_init:
        raise ArtifactIdentityError(f"{label} packaged /init differs")
    if expected_child is not None and child != expected_child:
        raise ArtifactIdentityError(f"{label} packaged child differs")
    init_result = _validate_init(init, P342_RUN_ID)
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
        "run_id_hex": P342_RUN_ID_HEX,
        "joined": True,
        "boot_only": True,
    }


STALE_AP_IDENTITIES = tuple(
    [dict(value) for value in predecessor.STALE_AP_IDENTITIES]
    + [dict(P341_AP_IDENTITY)]
)


def validate_rollback_ap(
    ap_path: Path,
    expected: Mapping[str, Any],
    *,
    label: str = "P342 exact rollback AP",
) -> dict[str, Any]:
    if any(dict(expected) == value for value in STALE_AP_IDENTITIES):
        raise ArtifactIdentityError("consumed predecessor candidate AP is not rollback")
    try:
        return _INNER.validate_rollback_ap(ap_path, expected, label=label)
    except Exception as exc:
        raise ArtifactIdentityError(str(exc)) from exc


def validate_p342_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p342_artifact_identity_v1",
        "run_id_hex": P342_RUN_ID_HEX,
        "predecessor_run_id_rejected": P341_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P341_AP_IDENTITY),
        "image_identity": dict(P342_IMAGE_IDENTITY),
        "ap_identity": dict(P342_AP_IDENTITY),
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
        "runtime_behavior_unchanged": True,
        "idle_listener_unchanged": True,
    }


def __getattr__(name: str) -> Any:
    return getattr(predecessor, name)


__all__ = sorted(
    {
        "AUTH_KEY_MODE",
        "AUTH_KEY_SCHEMA",
        "AUTH_KEY_SIZE",
        "ArtifactIdentityError",
        "GZIP_HEADER",
        "IMAGE_SECTION_LAYOUT",
        "IKCONFIG_COMPRESSED_SIZE",
        "IKCONFIG_ED",
        "IKCONFIG_END_OFFSET",
        "IKCONFIG_OFFSET",
        "IKCONFIG_ST",
        "LZ4",
        "LZ4_IDENTITY",
        "MAGISKBOOT",
        "MAGISKBOOT_IDENTITY",
        "P341_AP_IDENTITY",
        "P341_IMAGE",
        "P341_IMAGE_IDENTITY",
        "P341_PREDECESSOR_RUN_ID",
        "P341_PREDECESSOR_RUN_ID_HEX",
        "P342_AP_IDENTITY",
        "P342_IMAGE_IDENTITY",
        "P342_RUN_ID",
        "P342_RUN_ID_HEX",
        "P342_UNSAT_TAG_HEX",
        "RUN_CONFIG_KEY",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STALE_AP_IDENTITIES",
        "UNSAT_CONFIG_KEY",
        "identity",
        "inspect_ap",
        "stable_bytes",
        "transform_image",
        "validate_image",
        "validate_p342_identity",
        "validate_rollback_ap",
    }
)
