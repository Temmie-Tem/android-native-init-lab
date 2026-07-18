#!/usr/bin/env python3
"""Target-independent host-only helpers for fixed-slice boot builders."""

from __future__ import annotations

import hashlib
import io
import os
import stat
import struct
import subprocess
import tarfile
from pathlib import Path
from typing import Any


INVALID_ODIN_DEVICE = "/dev/bus/usb/999/999"


class BootSliceError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_pinned_stable(
    path: Path, expected_size: int, expected_sha256: str, label: str
) -> tuple[dict[str, Any], bytes]:
    """Read one direct regular file while pinning descriptor and path identity."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BootSliceError(f"{label} missing or indirect: {path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise BootSliceError(f"{label} is not a regular file: {path}")
        if before.st_size != expected_size:
            raise BootSliceError(
                f"{label} size mismatch: {before.st_size} != {expected_size}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 4 * 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        current = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise BootSliceError(f"{label} path disappeared after read: {path}") from exc
    if not stat.S_ISREG(current.st_mode):
        raise BootSliceError(f"{label} path is no longer a regular file: {path}")
    if _identity(before) != _identity(after) or _identity(after) != _identity(current):
        raise BootSliceError(f"{label} changed during pinned read: {path}")
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise BootSliceError(f"{label} short read: {len(data)} != {expected_size}")
    actual_sha256 = sha256_bytes(data)
    if actual_sha256 != expected_sha256:
        raise BootSliceError(f"{label} SHA256 mismatch: {actual_sha256}")
    return {
        "size": len(data),
        "sha256": actual_sha256,
        "stable_direct_regular_file": True,
    }, data


def parse_arm64_header(image: bytes) -> dict[str, int | str]:
    if len(image) < 64:
        raise BootSliceError("Image is too short for an ARM64 header")
    fields = struct.unpack_from("<IIQQQQQQII", image, 0)
    if fields[8] != 0x644D5241:
        raise BootSliceError(f"ARM64 Image magic mismatch: 0x{fields[8]:08x}")
    return {
        "code0": fields[0],
        "code1": fields[1],
        "text_offset": fields[2],
        "image_size_field": fields[3],
        "flags": fields[4],
        "reserved2": fields[5],
        "reserved3": fields[6],
        "reserved4": fields[7],
        "magic": fields[8],
        "reserved5": fields[9],
        "header_hex": image[:64].hex(),
        "header_sha256": sha256_bytes(image[:64]),
    }


def replace_fixed_interval(
    carrier: bytes, replacement: bytes, start: int, end_exclusive: int
) -> bytes:
    if start < 0 or end_exclusive <= start or end_exclusive > len(carrier):
        raise BootSliceError(
            f"invalid replacement interval [{start},{end_exclusive}) for {len(carrier)} bytes"
        )
    required = end_exclusive - start
    if len(replacement) != required:
        raise BootSliceError(
            f"replacement size mismatch: {len(replacement)} != {required}"
        )
    return carrier[:start] + replacement + carrier[end_exclusive:]


def diff_outside_interval(
    carrier: bytes, candidate: bytes, start: int, end_exclusive: int
) -> dict[str, int | None]:
    if len(carrier) != len(candidate):
        raise BootSliceError(
            f"image size mismatch: {len(candidate)} != carrier {len(carrier)}"
        )
    if start < 0 or end_exclusive <= start or end_exclusive > len(carrier):
        raise BootSliceError("invalid comparison interval")
    first: int | None = None
    last: int | None = None
    changed = 0
    outside = 0
    for offset, (left, right) in enumerate(zip(carrier, candidate)):
        if left == right:
            continue
        first = offset if first is None else first
        last = offset
        changed += 1
        if offset < start or offset >= end_exclusive:
            outside += 1
    if outside:
        raise BootSliceError(f"candidate changed {outside} bytes outside replacement interval")
    return {
        "first_changed_offset": first,
        "last_changed_offset_inclusive": last,
        "changed_byte_count": changed,
        "outside_interval_changed_byte_count": outside,
    }


def write_deterministic_boot_ap(frame: bytes, output: Path) -> dict[str, Any]:
    """Create one canonical USTAR member followed by Samsung's MD5 trailer."""

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        with tarfile.open(fileobj=handle, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo("boot.img.lz4")
            info.size = len(frame)
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.mtime = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(frame))
    prefix = output.read_bytes()
    digest = hashlib.md5(prefix).hexdigest()
    with output.open("ab") as handle:
        handle.write(f"{digest}  AP.tar\n".encode("ascii"))
    return {
        "tar_prefix_size": len(prefix),
        "tar_md5": digest,
        "trailer": f"{digest}  AP.tar\\n",
        "members": ["boot.img.lz4"],
    }


def classify_marker_family(
    data: bytes, exact_marker: bytes, family_prefix: bytes
) -> dict[str, Any]:
    if not exact_marker or not family_prefix or family_prefix not in exact_marker:
        raise BootSliceError("invalid exact marker/family prefix contract")
    exact_count = data.count(exact_marker)
    records: list[bytes] = []
    partial_offsets: list[int] = []
    cursor = 0
    while True:
        start = data.find(family_prefix, cursor)
        if start < 0:
            break
        end = data.find(b"]]", start + len(family_prefix))
        if end < 0:
            partial_offsets.append(start)
            cursor = start + len(family_prefix)
            continue
        records.append(data[start : end + 2])
        cursor = end + 2
    exact_core = exact_marker.strip(b"\n")
    foreign = [record for record in records if record != exact_core]
    return {
        "exact_count": exact_count,
        "family_count": len(records) + len(partial_offsets),
        "complete_record_count": len(records),
        "foreign_count": len(foreign),
        "foreign_records_hex": [record.hex() for record in foreign],
        "partial_count": len(partial_offsets),
        "partial_offsets": partial_offsets,
        "valid_single_exact": (
            exact_count == 1
            and len(records) == 1
            and records[0] == exact_core
            and not partial_offsets
        ),
    }


def run_odin_invalid_device_gate(
    odin: Path, ap_path: Path, timeout: int = 30
) -> dict[str, Any]:
    result = subprocess.run(
        [str(odin), "-a", str(ap_path), "-d", INVALID_ODIN_DEVICE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    required = (
        "Check file :",
        INVALID_ODIN_DEVICE,
        "No such file or directory",
        "usb device Fail",
    )
    missing = [marker for marker in required if marker not in output]
    if result.returncode != 1 or missing:
        raise BootSliceError(
            f"unexpected Odin invalid-device gate rc={result.returncode} "
            f"missing={missing}: {output}"
        )
    return {
        "returncode": result.returncode,
        "invalid_device": INVALID_ODIN_DEVICE,
        "ap_recognized": True,
        "failed_before_device_open": True,
        "required_markers_present": True,
    }
