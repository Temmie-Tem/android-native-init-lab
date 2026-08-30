#!/usr/bin/env python3
"""Verify the P3.21 boot/AP identity join, host-only.

P3.20 used a P3.19-configured kernel Image with a P3.20 ``/init``.  P3.21
keeps the reviewed kernel layout and changes only the identity-bearing string
and embedded IKCONFIG line through a deterministic, same-length post-link
transform.  This module is deliberately a narrow artifact boundary: it
unpacks the real AP, checks the kernel Image and ramdisk ``init`` bytes, and
rejects any mixed or stale run ID.  It does not contact a device or invoke
Odin.
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import tempfile
from typing import Any, Mapping
import zlib


ROOT = Path(__file__).resolve().parents[5]

P319_IMAGE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-55/inputs/fixed-Image"
)
P319_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8",
}
P319_RUN_ID_HEX = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID_HEX = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
# The final byte is chosen so the pinned gzip-9 stream remains exactly
# 40,695 bytes.  It is a run identity, not a decoder wildcard.
P321_RUN_ID_HEX = "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P319_RUN_ID = bytes.fromhex(P319_RUN_ID_HEX)
P320_RUN_ID = bytes.fromhex(P320_RUN_ID_HEX)
P321_RUN_ID = bytes.fromhex(P321_RUN_ID_HEX)

IKCONFIG_ST = b"IKCFG_ST"
IKCONFIG_ED = b"IKCFG_ED"
IKCONFIG_OFFSET = 25_375_264
IKCONFIG_END_OFFSET = 25_415_967
IKCONFIG_COMPRESSED_SIZE = IKCONFIG_END_OFFSET - IKCONFIG_OFFSET - len(IKCONFIG_ST)
GZIP_HEADER = bytes.fromhex("1f8b0800000000000203")
RUN_CONFIG_KEY = "CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX"
UNSAT_CONFIG_KEY = "CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX"
P319_UNSAT_TAG_HEX = "ecbfff41d2c5ed22383db45dedfb622d"

# These are the raw Image sections whose bytes must not move or change during
# an identity-only transform.  They also fence the module-provider/CRC ABI.
IMAGE_SECTION_LAYOUT: dict[str, dict[str, Any]] = {
    "__ksymtab": {
        "image_offset": 35_693_760,
        "size": 34_212,
        "entry_size": 12,
        "sha256": "a5ff1f5fb15683862f0dbf8d4132ba43a78250ecc5d51a0d718be2298878be3a",
    },
    "__ksymtab_gpl": {
        "image_offset": 35_727_972,
        "size": 52_452,
        "entry_size": 12,
        "sha256": "11de1b664019175d2b43b32211e62f007aab7dad201daefe58a3224021ac8b7d",
    },
    "__kcrctab": {
        "image_offset": 35_780_424,
        "size": 11_404,
        "entry_size": 4,
        "sha256": "551a646cdcc3d066b43e01187e448b83c6d712d3067a2e87354cc79cb3688543",
    },
    "__kcrctab_gpl": {
        "image_offset": 35_791_828,
        "size": 17_484,
        "entry_size": 4,
        "sha256": "018b0f33ceeee6e438a6c3c6054844c14124833f79acdeabb066e1a7664b1bcb",
    },
    "__ksymtab_strings": {
        "image_offset": 35_809_312,
        "size": 170_032,
        "entry_size": 1,
        "sha256": "4c0d4ae1f1a69aaef35b5adcb17e15aace1c68847b7a5a17069f157dbe81e854",
    },
}

MAGISKBOOT = ROOT / "workspace/private/tools/magisk-v30.7/magiskboot"
LZ4 = ROOT / (
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/lz4"
)
MAGISKBOOT_IDENTITY = {
    "size": 943_848,
    "sha256": "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e",
}
LZ4_IDENTITY = {
    "size": 218_696,
    "sha256": "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8",
}


class ArtifactIdentityError(ValueError):
    """An Image, init, AP, or rollback identity is not exact."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def stable_bytes(
    path: Path,
    label: str,
    maximum: int = 128 * 1024 * 1024,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    """Read one unchanged regular file without following an indirect path."""
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
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink < 1
        or before_id != inside_id
        or before_id != after_id
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
        or (expected is not None and identity(payload) != dict(expected))
    ):
        raise ArtifactIdentityError(f"{label} identity differs")
    return payload


def _gzip_config(image: bytes, label: str) -> tuple[int, int, bytes, bytes]:
    if type(image) is not bytes:
        raise ArtifactIdentityError(f"{label} is not bytes")
    starts = [match.start() for match in re.finditer(re.escape(IKCONFIG_ST), image)]
    ends = [match.start() for match in re.finditer(re.escape(IKCONFIG_ED), image)]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ArtifactIdentityError(f"{label} IKCONFIG markers are not unique")
    start = starts[0]
    end = ends[0]
    compressed_start = start + len(IKCONFIG_ST)
    compressed = image[compressed_start:end]
    if (
        start != IKCONFIG_OFFSET
        or end != IKCONFIG_END_OFFSET
        or len(compressed) != IKCONFIG_COMPRESSED_SIZE
        or compressed[: len(GZIP_HEADER)] != GZIP_HEADER
    ):
        raise ArtifactIdentityError(f"{label} IKCONFIG geometry differs")
    decompressor = zlib.decompressobj(16 + 15)
    try:
        config = decompressor.decompress(compressed, 2 * 1024 * 1024 + 1)
        config += decompressor.flush()
    except zlib.error as exc:
        raise ArtifactIdentityError(f"{label} IKCONFIG gzip is corrupt") from exc
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or not config.endswith(b"\n")
    ):
        raise ArtifactIdentityError(f"{label} IKCONFIG stream is not exact")
    try:
        config.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ArtifactIdentityError(f"{label} IKCONFIG is not ASCII") from exc
    return compressed_start, end, compressed, config


def _config_values(config: bytes, label: str) -> dict[str, str]:
    values: dict[str, str] = {}
    line_re = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
    unset_re = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
    for line in config.decode("ascii").splitlines():
        if not line or line.startswith("#") and not unset_re.fullmatch(line):
            continue
        match = line_re.fullmatch(line)
        unset = unset_re.fullmatch(line)
        if match is None and unset is None:
            raise ArtifactIdentityError(f"{label} IKCONFIG line is malformed")
        key = match.group(1) if match else unset.group(1)  # type: ignore[union-attr]
        if key in values:
            raise ArtifactIdentityError(f"{label} IKCONFIG key is duplicated")
        values[key] = match.group(2) if match else "unset"  # type: ignore[union-attr]
    required = {
        "CONFIG_MODVERSIONS",
        "CONFIG_MODULE_SIG",
        "CONFIG_MODULE_FORCE_LOAD",
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE",
        "CONFIG_S22PLUS_FYG8_E1_PROFILE",
        RUN_CONFIG_KEY,
        UNSAT_CONFIG_KEY,
    }
    if not required <= set(values):
        raise ArtifactIdentityError(f"{label} IKCONFIG required key is absent")
    if (
        values["CONFIG_MODVERSIONS"] != "y"
        or values["CONFIG_MODULE_SIG"] != "unset"
        or values["CONFIG_MODULE_FORCE_LOAD"] != "unset"
        or values.get("CONFIG_MODULE_REL_CRCS", "unset") != "unset"
        or values["CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE"] != "y"
        or values["CONFIG_S22PLUS_FYG8_E1_PROFILE"] != "3"
    ):
        raise ArtifactIdentityError(f"{label} IKCONFIG module lane differs")
    for key in (RUN_CONFIG_KEY, UNSAT_CONFIG_KEY):
        if re.fullmatch(r'"[0-9a-f]{32}"', values[key]) is None:
            raise ArtifactIdentityError(f"{label} IKCONFIG {key} is malformed")
    return values


def _section_receipts(image: bytes, label: str) -> dict[str, dict[str, Any]]:
    if len(image) != P319_IMAGE_IDENTITY["size"]:
        raise ArtifactIdentityError(f"{label} Image size differs")
    result: dict[str, dict[str, Any]] = {}
    for name, spec in IMAGE_SECTION_LAYOUT.items():
        offset = int(spec["image_offset"])
        size = int(spec["size"])
        entry_size = int(spec["entry_size"])
        if (
            offset < 0
            or size <= 0
            or entry_size <= 0
            or size % entry_size
            or offset + size > len(image)
        ):
            raise ArtifactIdentityError(f"{label} Image section geometry differs")
        section = image[offset : offset + size]
        actual = identity(section)
        if actual != {"size": size, "sha256": spec["sha256"]}:
            raise ArtifactIdentityError(f"{label} Image section bytes differ: {name}")
        result[name] = {
            "image_offset": offset,
            "size": size,
            "entry_size": entry_size,
            "sha256": actual["sha256"],
        }
    return result


def validate_image(image: bytes, *, expected_run_id: bytes = P321_RUN_ID) -> dict[str, Any]:
    """Validate one Image and expose its run ID for the AP join."""
    if type(expected_run_id) is not bytes or len(expected_run_id) != 16:
        raise ArtifactIdentityError("expected Image run ID is not 16 bytes")
    expected_hex = expected_run_id.hex()
    compressed_start, end, compressed, config = _gzip_config(image, "Image")
    values = _config_values(config, "Image")
    run_match = re.fullmatch(r'"([0-9a-f]{32})"', values[RUN_CONFIG_KEY])
    unsat_match = re.fullmatch(r'"([0-9a-f]{32})"', values[UNSAT_CONFIG_KEY])
    if run_match is None or unsat_match is None or run_match.group(1) != expected_hex:
        raise ArtifactIdentityError("Image IKCONFIG run ID differs")
    if values[UNSAT_CONFIG_KEY] != f'"{P319_UNSAT_TAG_HEX}"':
        raise ArtifactIdentityError("Image IKCONFIG UNSAT tag differs")
    outside = image[:compressed_start] + image[end:]
    raw_counts = {
        P319_RUN_ID_HEX: outside.count(P319_RUN_ID_HEX.encode("ascii")),
        P320_RUN_ID_HEX: outside.count(P320_RUN_ID_HEX.encode("ascii")),
        P321_RUN_ID_HEX: outside.count(P321_RUN_ID_HEX.encode("ascii")),
    }
    if raw_counts.get(expected_hex) != 1 or any(
        count != 0 for run, count in raw_counts.items() if run != expected_hex
    ):
        raise ArtifactIdentityError("Image raw run-ID occurrences are not exact")
    raw_offset = image.find(expected_hex.encode("ascii"))
    if raw_offset < 0 or compressed_start <= raw_offset < end:
        raise ArtifactIdentityError("Image raw run-ID location is inside IKCONFIG")
    sections = _section_receipts(image, "Image")
    return {
        "identity": identity(image),
        "run_id_hex": expected_hex,
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
        "raw_run_id": {
            "offset": raw_offset,
            "counts_outside_ikconfig": raw_counts,
        },
        "sections": sections,
        "layout_preserved": True,
    }


def _recompress_config(config: bytes) -> bytes:
    compressor = zlib.compressobj(
        level=9,
        method=zlib.DEFLATED,
        wbits=31,
        memLevel=8,
        strategy=zlib.Z_DEFAULT_STRATEGY,
    )
    return compressor.compress(config) + compressor.flush()


def transform_image(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Change only the old run-ID constant and its exact embedded IKCONFIG."""
    if identity(original) != P319_IMAGE_IDENTITY:
        raise ArtifactIdentityError("P319 source Image identity differs")
    compressed_start, end, compressed, config = _gzip_config(original, "P319 source Image")
    values = _config_values(config, "P319 source Image")
    old_line = f'{RUN_CONFIG_KEY}="{P319_RUN_ID_HEX}"'.encode("ascii")
    new_line = f'{RUN_CONFIG_KEY}="{P321_RUN_ID_HEX}"'.encode("ascii")
    if config.count(old_line) != 1 or config.count(new_line) != 0:
        raise ArtifactIdentityError("P319 source IKCONFIG run-ID line is not exact")
    if values[UNSAT_CONFIG_KEY] != f'"{P319_UNSAT_TAG_HEX}"':
        raise ArtifactIdentityError("P319 source UNSAT tag differs")
    old_raw = P319_RUN_ID_HEX.encode("ascii")
    new_raw = P321_RUN_ID_HEX.encode("ascii")
    outside = original[:compressed_start] + original[end:]
    if outside.count(old_raw) != 1 or outside.count(new_raw) != 0:
        raise ArtifactIdentityError("P319 source raw run-ID occurrence is not unique")
    raw_offset = original.find(old_raw)
    if raw_offset < 0 or compressed_start <= raw_offset < end:
        raise ArtifactIdentityError("P319 source raw run-ID is not outside IKCONFIG")
    transformed_config = config.replace(old_line, new_line, 1)
    transformed_compressed = _recompress_config(transformed_config)
    if (
        len(transformed_compressed) != len(compressed)
        or transformed_compressed[: len(GZIP_HEADER)] != GZIP_HEADER
        or zlib.decompress(transformed_compressed, 31) != transformed_config
    ):
        raise ArtifactIdentityError("P321 IKCONFIG gzip transform is not same-length exact")
    transformed = (
        original[:compressed_start]
        + transformed_compressed
        + original[end:]
    )
    transformed = (
        transformed[:raw_offset]
        + new_raw
        + transformed[raw_offset + len(old_raw) :]
    )
    if len(transformed) != len(original):
        raise ArtifactIdentityError("P321 Image size changed during transform")
    # The complete construction is intentionally explicit: all bytes outside
    # the gzip region and one fixed 32-byte rodata slot must be unchanged.
    expected = original[:compressed_start] + transformed_compressed + original[end:]
    expected = expected[:raw_offset] + new_raw + expected[raw_offset + len(old_raw) :]
    if transformed != expected:
        raise ArtifactIdentityError("P321 Image changed outside declared identity spans")
    checked = validate_image(transformed)
    if checked["identity"] != identity(transformed):
        raise ArtifactIdentityError("P321 Image receipt is unstable")
    second, second_meta = _transform_image_once(original)
    if second != transformed or second_meta != checked:
        raise ArtifactIdentityError("P321 Image transform is not deterministic")
    return transformed, {
        "method": "identity_only_post_link_v1",
        "source": {"run_id_hex": P319_RUN_ID_HEX, **P319_IMAGE_IDENTITY},
        "target": {"run_id_hex": P321_RUN_ID_HEX, **identity(transformed)},
        "raw_rodata": {
            "offset": raw_offset,
            "size": len(old_raw),
            "old_ascii": P319_RUN_ID_HEX,
            "new_ascii": P321_RUN_ID_HEX,
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
    }


def _transform_image_once(original: bytes) -> tuple[bytes, dict[str, Any]]:
    """Pure second pass used solely to prove transform A/B equality."""
    compressed_start, end, compressed, config = _gzip_config(original, "P319 source Image")
    old_line = f'{RUN_CONFIG_KEY}="{P319_RUN_ID_HEX}"'.encode("ascii")
    new_line = f'{RUN_CONFIG_KEY}="{P321_RUN_ID_HEX}"'.encode("ascii")
    old_raw = P319_RUN_ID_HEX.encode("ascii")
    new_raw = P321_RUN_ID_HEX.encode("ascii")
    transformed_config = config.replace(old_line, new_line, 1)
    transformed_compressed = _recompress_config(transformed_config)
    raw_offset = original.find(old_raw)
    transformed = original[:compressed_start] + transformed_compressed + original[end:]
    transformed = transformed[:raw_offset] + new_raw + transformed[raw_offset + len(old_raw) :]
    return transformed, validate_image(transformed)


def _parse_ap(
    payload: bytes,
    label: str,
    *,
    owner: tuple[int, int] = (0, 0),
) -> tuple[bytes, dict[str, Any]]:
    marker = b"  AP.tar\n"
    if type(payload) is not bytes or payload.count(marker) != 1:
        raise ArtifactIdentityError(f"{label} AP trailer is not unique")
    trailer_start = payload.rfind(marker)
    tar_start = trailer_start - 32
    if tar_start < 0 or trailer_start != len(payload) - len(marker):
        raise ArtifactIdentityError(f"{label} AP trailer geometry differs")
    try:
        recorded = payload[tar_start:trailer_start].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ArtifactIdentityError(f"{label} AP digest is not ASCII") from exc
    if re.fullmatch(r"[0-9a-f]{32}", recorded) is None:
        raise ArtifactIdentityError(f"{label} AP digest is malformed")
    tar_payload = payload[:tar_start]
    if hashlib.md5(tar_payload).hexdigest() != recorded:
        raise ArtifactIdentityError(f"{label} AP tar digest differs")
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_payload), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) != 1 or members[0].name != "boot.img.lz4":
                raise ArtifactIdentityError(f"{label} AP member set is not boot-only")
            member = members[0]
            if (
                not member.isfile()
                or member.issym()
                or member.islnk()
                or member.mode != 0o644
                or (member.uid, member.gid) != owner
            ):
                raise ArtifactIdentityError(f"{label} AP member metadata differs")
            stream = archive.extractfile(member)
            if stream is None:
                raise ArtifactIdentityError(f"{label} AP member is unreadable")
            frame = stream.read(member.size + 1)
    except (OSError, tarfile.TarError) as exc:
        raise ArtifactIdentityError(f"{label} AP tar cannot be audited") from exc
    if len(frame) != member.size:
        raise ArtifactIdentityError(f"{label} AP member size differs")
    return frame, {
        "member": {"name": member.name, **identity(frame)},
        "tar_prefix_size": len(tar_payload),
        "tar_md5": recorded,
        "trailer": recorded + "  AP.tar\\n",
    }


def _run(command: list[str], cwd: Path, label: str) -> None:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ArtifactIdentityError(f"{label} could not run") from exc
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
        raise ArtifactIdentityError(f"{label} failed: {detail[-1000:]}")


def _validate_init(init: bytes, expected_run_id: bytes) -> dict[str, Any]:
    expected = expected_run_id
    stale = {
        P319_RUN_ID_HEX: init.count(P319_RUN_ID),
        P320_RUN_ID_HEX: init.count(P320_RUN_ID),
        P321_RUN_ID_HEX: init.count(P321_RUN_ID),
    }
    if stale.get(expected_run_id.hex()) != 1 or any(
        value != 0 for key, value in stale.items() if key != expected_run_id.hex()
    ):
        raise ArtifactIdentityError("/init run-ID occurrences are not exact")
    raw_expected = init.count(expected)
    if raw_expected != 1:
        raise ArtifactIdentityError("/init run-ID occurrence is not unique")
    return {"identity": identity(init), "run_id_hex": expected_run_id.hex(), "counts": stale}


def inspect_ap(
    ap_path: Path,
    *,
    expected_run_id: bytes = P321_RUN_ID,
    expected_image: bytes | None = None,
    expected_init: bytes | None = None,
    expected_child: bytes | None = None,
    expected_ap: Mapping[str, Any] | None = None,
    label: str = "P321 candidate AP",
) -> dict[str, Any]:
    """Unpack a real AP and join Image/config, init, and AP identities."""
    # The unpacker is execution-critical.  Bind both tools at the same seam as
    # the AP before invoking either one; callers cannot substitute PATH tools.
    tool_identities()
    payload = stable_bytes(ap_path, label, 128 * 1024 * 1024, nlink=1)
    ap_identity = identity(payload)
    if expected_ap is not None and ap_identity != dict(expected_ap):
        raise ArtifactIdentityError(f"{label} AP identity differs")
    frame, ap_structure = _parse_ap(payload, label)
    with tempfile.TemporaryDirectory(prefix="p321-ap-identity-") as temporary:
        work = Path(temporary)
        frame_path = work / "boot.img.lz4"
        boot_path = work / "boot.img"
        frame_path.write_bytes(frame)
        _run(
            [str(LZ4), "-d", "-f", "-q", str(frame_path), str(boot_path)],
            work,
            f"{label} LZ4 decode",
        )
        _run([str(MAGISKBOOT), "unpack", "-h", str(boot_path)], work, f"{label} boot unpack")
        boot_identity = identity(stable_bytes(boot_path, f"{label} boot", 128 * 1024 * 1024))
        image = stable_bytes(work / "kernel", f"{label} Image", 64 * 1024 * 1024)
        if expected_image is not None and image != expected_image:
            raise ArtifactIdentityError(f"{label} packaged Image differs")
        image_result = validate_image(image, expected_run_id=expected_run_id)
        ramdisk = work / "ramdisk.cpio"
        init_path = work / "init"
        child_path = work / "child"
        _run(
            [str(MAGISKBOOT), "cpio", str(ramdisk), f"extract init {init_path}"],
            work,
            f"{label} init extract",
        )
        _run(
            [str(MAGISKBOOT), "cpio", str(ramdisk), f"extract s22-e1-child {child_path}"],
            work,
            f"{label} child extract",
        )
        init = stable_bytes(init_path, f"{label} /init", 2 * 1024 * 1024)
        child = stable_bytes(child_path, f"{label} child", 2 * 1024 * 1024)
    if expected_init is not None and init != expected_init:
        raise ArtifactIdentityError(f"{label} packaged /init differs")
    if expected_child is not None and child != expected_child:
        raise ArtifactIdentityError(f"{label} packaged child differs")
    init_result = _validate_init(init, expected_run_id)
    if image_result["run_id_hex"] != init_result["run_id_hex"]:
        raise ArtifactIdentityError(f"{label} Image/init run-ID join differs")
    return {
        "ap": ap_identity,
        "ap_structure": ap_structure,
        "boot_img_lz4": identity(frame),
        "boot_img": boot_identity,
        "image": image_result,
        "init": init_result,
        "child": identity(child),
        "run_id_hex": expected_run_id.hex(),
        "joined": True,
        "boot_only": True,
    }


def validate_rollback_ap(
    ap_path: Path,
    expected: Mapping[str, Any],
    *,
    label: str = "P321 exact rollback AP",
) -> dict[str, Any]:
    """Check rollback identity and boot-only member closure without opening it."""
    payload = stable_bytes(ap_path, label, 128 * 1024 * 1024, nlink=1)
    if identity(payload) != dict(expected):
        raise ArtifactIdentityError(f"{label} identity differs")
    _frame, structure = _parse_ap(payload, label, owner=(1000, 1000))
    return {"identity": identity(payload), "ap_structure": structure, "untouched": True}


def tool_identities() -> dict[str, dict[str, Any]]:
    stable_bytes(MAGISKBOOT, "P321 magiskboot", 4 * 1024 * 1024, MAGISKBOOT_IDENTITY)
    stable_bytes(LZ4, "P321 lz4", 4 * 1024 * 1024, LZ4_IDENTITY)
    return {"magiskboot": dict(MAGISKBOOT_IDENTITY), "lz4": dict(LZ4_IDENTITY)}


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
    "identity",
    "inspect_ap",
    "stable_bytes",
    "tool_identities",
    "transform_image",
    "validate_image",
    "validate_rollback_ap",
]
