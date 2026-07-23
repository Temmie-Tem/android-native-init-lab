#!/usr/bin/env python3
"""Independent host-only parsers for inspecting constructed boot artifacts."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import stat
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


ANDROID_MAGIC = b"ANDROID!"
VENDOR_BOOT_MAGIC = b"VNDRBOOT"
CPIO_MAGICS = {b"070701", b"070702"}
AP_TRAILER_RE = re.compile(rb"([0-9a-f]{32})  AP\.tar\n")
LZ4_FRAME_MAGIC = b"\x04\x22\x4d\x18"
LZ4_LEGACY_MAGIC = b"\x02\x21\x4c\x18"
LZ4_LEGACY_BLOCK_MAX = 8 * 1024 * 1024
LZ4_LEGACY_COMPRESSED_BLOCK_MAX = (
    LZ4_LEGACY_BLOCK_MAX + LZ4_LEGACY_BLOCK_MAX // 255 + 16
)


class BootVerifyError(ValueError):
    pass


@dataclass(frozen=True)
class BootImageV4:
    header: dict[str, Any]
    kernel: bytes
    ramdisk: bytes
    signature: bytes
    opaque_tail: bytes


@dataclass(frozen=True)
class VendorRamdiskFragment:
    name: str
    ramdisk_type: int
    board_id: tuple[int, ...]
    data: bytes


@dataclass(frozen=True)
class VendorBootV4:
    header: dict[str, Any]
    cmdline: str
    fragments: tuple[VendorRamdiskFragment, ...]
    bootconfig: bytes


@dataclass(frozen=True)
class CpioEntry:
    encoded_name: str
    name: str
    inode: int
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    data: bytes

    @property
    def file_type(self) -> str:
        if stat.S_ISREG(self.mode):
            return "regular"
        if stat.S_ISDIR(self.mode):
            return "directory"
        if stat.S_ISLNK(self.mode):
            return "symlink"
        return "other"

    def summary(self) -> dict[str, Any]:
        return {
            "encoded_name": self.encoded_name,
            "name": self.name,
            "inode": self.inode,
            "mode": stat.S_IMODE(self.mode),
            "type": self.file_type,
            "uid": self.uid,
            "gid": self.gid,
            "nlink": self.nlink,
            "mtime": self.mtime,
            "size": len(self.data),
            "sha256": sha256_bytes(self.data),
        }


def align(value: int, boundary: int) -> int:
    if boundary <= 0 or boundary & (boundary - 1):
        raise BootVerifyError(f"invalid alignment: {boundary}")
    return (value + boundary - 1) // boundary * boundary


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rotl32(value: int, count: int) -> int:
    value &= 0xFFFFFFFF
    return ((value << count) | (value >> (32 - count))) & 0xFFFFFFFF


def xxh32(data: bytes, seed: int = 0) -> int:
    """Return the LZ4 frame checksum primitive without an external dependency."""
    prime1 = 0x9E3779B1
    prime2 = 0x85EBCA77
    prime3 = 0xC2B2AE3D
    prime4 = 0x27D4EB2F
    prime5 = 0x165667B1

    def round_acc(accumulator: int, lane: int) -> int:
        accumulator = (accumulator + lane * prime2) & 0xFFFFFFFF
        accumulator = _rotl32(accumulator, 13)
        return (accumulator * prime1) & 0xFFFFFFFF

    offset = 0
    length = len(data)
    if length >= 16:
        values = [
            (seed + prime1 + prime2) & 0xFFFFFFFF,
            (seed + prime2) & 0xFFFFFFFF,
            seed & 0xFFFFFFFF,
            (seed - prime1) & 0xFFFFFFFF,
        ]
        limit = length - 16
        while offset <= limit:
            for index in range(4):
                values[index] = round_acc(
                    values[index], struct.unpack_from("<I", data, offset)[0]
                )
                offset += 4
        result = (
            _rotl32(values[0], 1)
            + _rotl32(values[1], 7)
            + _rotl32(values[2], 12)
            + _rotl32(values[3], 18)
        ) & 0xFFFFFFFF
    else:
        result = (seed + prime5) & 0xFFFFFFFF

    result = (result + length) & 0xFFFFFFFF
    while offset + 4 <= length:
        result = (
            result + struct.unpack_from("<I", data, offset)[0] * prime3
        ) & 0xFFFFFFFF
        result = (_rotl32(result, 17) * prime4) & 0xFFFFFFFF
        offset += 4
    while offset < length:
        result = (result + data[offset] * prime5) & 0xFFFFFFFF
        result = (_rotl32(result, 11) * prime1) & 0xFFFFFFFF
        offset += 1
    result ^= result >> 15
    result = (result * prime2) & 0xFFFFFFFF
    result ^= result >> 13
    result = (result * prime3) & 0xFFFFFFFF
    result ^= result >> 16
    return result & 0xFFFFFFFF


def _identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_stable(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BootVerifyError(f"{label} missing or indirect: {path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise BootVerifyError(f"{label} is not a regular file: {path}")
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
        raise BootVerifyError(f"{label} path disappeared after read: {path}") from exc
    if not stat.S_ISREG(current.st_mode):
        raise BootVerifyError(f"{label} path is no longer regular: {path}")
    if _identity(before) != _identity(after) or _identity(after) != _identity(current):
        raise BootVerifyError(f"{label} changed during pinned read: {path}")
    data = b"".join(chunks)
    if len(data) != before.st_size:
        raise BootVerifyError(f"{label} short read: {len(data)} != {before.st_size}")
    digest = sha256_bytes(data)
    return {"size": len(data), "sha256": digest, "stable_direct_regular_file": True}, data


def read_pinned_stable(
    path: Path, expected_size: int, expected_sha256: str, label: str
) -> tuple[dict[str, Any], bytes]:
    receipt, data = read_stable(path, label)
    if receipt["size"] != expected_size:
        raise BootVerifyError(
            f"{label} size mismatch: {receipt['size']} != {expected_size}"
        )
    if receipt["sha256"] != expected_sha256:
        raise BootVerifyError(f"{label} SHA256 mismatch: {receipt['sha256']}")
    return receipt, data


def parse_arm64_header(image: bytes) -> dict[str, int | str]:
    if len(image) < 64:
        raise BootVerifyError("Image is too short for an ARM64 header")
    fields = struct.unpack_from("<IIQQQQQQII", image, 0)
    if fields[8] != 0x644D5241:
        raise BootVerifyError(f"ARM64 Image magic mismatch: 0x{fields[8]:08x}")
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


def parse_boot_v4(data: bytes) -> BootImageV4:
    if len(data) < 4096 or data[:8] != ANDROID_MAGIC:
        raise BootVerifyError("Android boot magic missing")
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", data, 8)
    header_version = struct.unpack_from("<I", data, 40)[0]
    signature_size = struct.unpack_from("<I", data, 1580)[0]
    if header_version != 4 or header_size != 1584:
        raise BootVerifyError(
            f"expected boot v4 header size 1584, got v{header_version}/{header_size}"
        )
    kernel_start = 4096
    kernel_end = kernel_start + kernel_size
    ramdisk_start = align(kernel_end, 4096)
    ramdisk_end = ramdisk_start + ramdisk_size
    signature_start = align(ramdisk_end, 4096)
    signature_end = signature_start + signature_size
    if signature_end > len(data):
        raise BootVerifyError("boot v4 sections exceed image size")
    cmdline_raw = data[44:1580].split(b"\0", 1)[0]
    try:
        cmdline = cmdline_raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise BootVerifyError("boot v4 cmdline is not ASCII") from exc
    return BootImageV4(
        header={
            "header_version": header_version,
            "header_size": header_size,
            "kernel_size": kernel_size,
            "ramdisk_size": ramdisk_size,
            "signature_size": signature_size,
            "os_version": os_version,
            "cmdline": cmdline,
            "kernel_start": kernel_start,
            "kernel_end": kernel_end,
            "ramdisk_start": ramdisk_start,
            "ramdisk_end": ramdisk_end,
            "signature_start": signature_start,
            "signature_end": signature_end,
        },
        kernel=data[kernel_start:kernel_end],
        ramdisk=data[ramdisk_start:ramdisk_end],
        signature=data[signature_start:signature_end],
        opaque_tail=data[signature_end:],
    )


def parse_vendor_boot_v4(data: bytes) -> VendorBootV4:
    if len(data) < 4096 or data[:8] != VENDOR_BOOT_MAGIC:
        raise BootVerifyError("vendor_boot magic missing")
    header_version, page_size, kernel_addr, ramdisk_addr, ramdisk_size = struct.unpack_from(
        "<5I", data, 8
    )
    if header_version != 4 or page_size != 4096:
        raise BootVerifyError(f"expected vendor_boot v4/page 4096, got {header_version}/{page_size}")
    cmdline_raw = data[28:2076].split(b"\0", 1)[0]
    try:
        cmdline = cmdline_raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise BootVerifyError("vendor_boot cmdline is not ASCII") from exc
    tags_addr = struct.unpack_from("<I", data, 2076)[0]
    product_raw = data[2080:2096].split(b"\0", 1)[0]
    try:
        product_name = product_raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise BootVerifyError("vendor_boot product name is not ASCII") from exc
    header_size, dtb_size = struct.unpack_from("<2I", data, 2096)
    dtb_addr = struct.unpack_from("<Q", data, 2104)[0]
    table_size, table_entries, entry_size, bootconfig_size = struct.unpack_from(
        "<4I", data, 2112
    )
    if header_size != 2128 or entry_size != 108 or table_size != table_entries * entry_size:
        raise BootVerifyError("vendor_boot v4 header/table geometry mismatch")
    ramdisk_start = page_size
    ramdisk_end = ramdisk_start + ramdisk_size
    dtb_start = ramdisk_start + align(ramdisk_size, page_size)
    dtb_end = dtb_start + dtb_size
    table_start = dtb_start + align(dtb_size, page_size)
    table_end = table_start + table_size
    bootconfig_start = table_start + align(table_size, page_size)
    bootconfig_end = bootconfig_start + bootconfig_size
    if bootconfig_end > len(data):
        raise BootVerifyError("vendor_boot sections exceed image size")
    ramdisks = data[ramdisk_start:ramdisk_end]
    fragments: list[VendorRamdiskFragment] = []
    seen_names: set[str] = set()
    fragment_ranges: list[tuple[int, int, str]] = []
    for index in range(table_entries):
        entry = data[table_start + index * entry_size : table_start + (index + 1) * entry_size]
        size, offset, ramdisk_type = struct.unpack_from("<3I", entry, 0)
        name_raw = entry[12:44].split(b"\0", 1)[0]
        try:
            name = name_raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise BootVerifyError(f"vendor ramdisk name {index} is not ASCII") from exc
        board_id = struct.unpack_from("<16I", entry, 44)
        if name and name in seen_names:
            raise BootVerifyError(f"duplicate vendor ramdisk name: {name!r}")
        if offset + size > len(ramdisks):
            raise BootVerifyError(f"vendor ramdisk fragment exceeds aggregate: {name}")
        fragment_ranges.append((offset, offset + size, name or f"fragment-{index}"))
        if name:
            seen_names.add(name)
        fragments.append(
            VendorRamdiskFragment(name, ramdisk_type, board_id, ramdisks[offset : offset + size])
        )
    ordered_ranges = sorted(fragment_ranges)
    for left, right in zip(ordered_ranges, ordered_ranges[1:]):
        if left[1] > right[0]:
            raise BootVerifyError(f"overlapping vendor ramdisk fragments: {left[2]}/{right[2]}")
    return VendorBootV4(
        header={
            "header_version": header_version,
            "page_size": page_size,
            "kernel_addr": kernel_addr,
            "ramdisk_addr": ramdisk_addr,
            "vendor_ramdisk_size": ramdisk_size,
            "tags_addr": tags_addr,
            "product_name": product_name,
            "header_size": header_size,
            "dtb_size": dtb_size,
            "dtb_addr": dtb_addr,
            "table_size": table_size,
            "table_entries": table_entries,
            "table_entry_size": entry_size,
            "bootconfig_size": bootconfig_size,
            "ramdisk_start": ramdisk_start,
            "ramdisk_end": ramdisk_end,
            "dtb_start": dtb_start,
            "dtb_end": dtb_end,
            "table_start": table_start,
            "table_end": table_end,
            "bootconfig_start": bootconfig_start,
            "bootconfig_end": bootconfig_end,
        },
        cmdline=cmdline,
        fragments=tuple(fragments),
        bootconfig=data[bootconfig_start:bootconfig_end],
    )


def parse_avb_footer(data: bytes) -> dict[str, Any]:
    if len(data) < 64:
        raise BootVerifyError("image is too short for an AVB footer")
    magic, major, minor, original_size, vbmeta_offset, vbmeta_size, reserved = struct.unpack(
        "!4s2I3Q28s", data[-64:]
    )
    if magic != b"AVBf" or any(reserved):
        raise BootVerifyError("invalid AVB footer")
    if vbmeta_offset + vbmeta_size > len(data) - 64:
        raise BootVerifyError("AVB vbmeta range exceeds image")
    vbmeta = data[vbmeta_offset : vbmeta_offset + vbmeta_size]
    if not vbmeta.startswith(b"AVB0"):
        raise BootVerifyError("AVB vbmeta magic missing")
    return {
        "version_major": major,
        "version_minor": minor,
        "original_image_size": original_size,
        "vbmeta_offset": vbmeta_offset,
        "vbmeta_size": vbmeta_size,
        "vbmeta_sha256": sha256_bytes(vbmeta),
    }


def parse_tar_octal(field: bytes, label: str) -> int:
    if field and field[0] & 0x80:
        raise BootVerifyError(f"GNU base-256 tar number forbidden: {label}")
    encoded = field.rstrip(b"\0 ").lstrip(b" ")
    if not encoded:
        return 0
    if any(byte not in b"01234567" for byte in encoded):
        raise BootVerifyError(f"invalid tar octal field: {label}")
    return int(encoded, 8)


def _tar_text(field: bytes, label: str) -> str:
    try:
        return field.split(b"\0", 1)[0].decode("ascii")
    except UnicodeDecodeError as exc:
        raise BootVerifyError(f"non-ASCII tar field: {label}") from exc


def parse_single_boot_tar(
    prefix: bytes, *, require_deterministic_metadata: bool = True
) -> tuple[dict[str, Any], bytes]:
    if len(prefix) % 512:
        raise BootVerifyError("AP tar prefix is not block aligned")
    members: list[dict[str, Any]] = []
    payloads: list[bytes] = []
    offset = 0
    while offset + 512 <= len(prefix):
        header = prefix[offset : offset + 512]
        if header == bytes(512):
            if offset + 1024 > len(prefix) or prefix[offset + 512 : offset + 1024] != bytes(512):
                raise BootVerifyError("AP tar lacks two terminal zero blocks")
            if any(prefix[offset:]):
                raise BootVerifyError("AP tar has data after terminal blocks")
            break
        checksum = parse_tar_octal(header[148:156], "checksum")
        calculated = sum(header[:148]) + 8 * ord(" ") + sum(header[156:])
        if checksum != calculated:
            raise BootVerifyError("tar header checksum mismatch")
        if header[257:263] != b"ustar\0" or header[263:265] != b"00":
            raise BootVerifyError("AP tar is not canonical USTAR")
        name = _tar_text(header[:100], "name")
        path_prefix = _tar_text(header[345:500], "prefix")
        if path_prefix:
            raise BootVerifyError("AP member USTAR prefix must be empty")
        if name != "boot.img.lz4" or name.startswith("/") or ".." in Path(name).parts:
            raise BootVerifyError(f"forbidden AP member: {name!r}")
        if header[156:157] not in (b"0", b"\0") or _tar_text(header[157:257], "linkname"):
            raise BootVerifyError("AP member must be a direct regular file")
        size = parse_tar_octal(header[124:136], "size")
        member = {
            "name": name,
            "size": size,
            "mode": parse_tar_octal(header[100:108], "mode"),
            "uid": parse_tar_octal(header[108:116], "uid"),
            "gid": parse_tar_octal(header[116:124], "gid"),
            "mtime": parse_tar_octal(header[136:148], "mtime"),
            "uname": _tar_text(header[265:297], "uname"),
            "gname": _tar_text(header[297:329], "gname"),
        }
        if require_deterministic_metadata:
            expected_metadata = {
                "mode": 0o644,
                "uid": 0,
                "gid": 0,
                "mtime": 0,
                "uname": "",
                "gname": "",
            }
            for key, expected in expected_metadata.items():
                if member[key] != expected:
                    raise BootVerifyError(
                        f"AP deterministic metadata mismatch: {key}"
                    )
        data_start = offset + 512
        data_end = data_start + size
        padded_end = align(data_end, 512)
        if padded_end > len(prefix) or any(prefix[data_end:padded_end]):
            raise BootVerifyError("AP member is truncated or has nonzero padding")
        members.append(member)
        payloads.append(prefix[data_start:data_end])
        offset = padded_end
    else:
        raise BootVerifyError("AP tar terminal blocks missing")
    if len(members) != 1:
        raise BootVerifyError(f"AP tar requires one member, got {len(members)}")
    return members[0], payloads[0]


def parse_ap_tar_md5(
    data: bytes, *, require_deterministic_metadata: bool = True
) -> tuple[dict[str, Any], bytes]:
    if len(data) < 41:
        raise BootVerifyError("AP is too short for MD5 trailer")
    prefix, trailer = data[:-41], data[-41:]
    match = AP_TRAILER_RE.fullmatch(trailer)
    if match is None:
        raise BootVerifyError("AP MD5 trailer is malformed")
    actual_md5 = hashlib.md5(prefix).hexdigest()
    if match.group(1).decode("ascii") != actual_md5:
        raise BootVerifyError("AP tar MD5 mismatch")
    member, frame = parse_single_boot_tar(
        prefix,
        require_deterministic_metadata=require_deterministic_metadata,
    )
    return {"tar_md5": actual_md5, "member": member}, frame


def _parse_lz4_frame_layout(
    frame: bytes,
) -> tuple[dict[str, Any], tuple[tuple[bool, bytes], ...], int | None]:
    if len(frame) < 11 or frame[:4] != LZ4_FRAME_MAGIC:
        raise BootVerifyError("LZ4 frame magic missing")
    position = 4
    descriptor_start = position
    flg, bd = frame[position], frame[position + 1]
    position += 2
    if (flg >> 6) != 1 or flg & 0x02:
        raise BootVerifyError(f"invalid LZ4 FLG: 0x{flg:02x}")
    if flg & 0x01:
        raise BootVerifyError("LZ4 dictionary frames are not accepted")
    block_max = {4: 65536, 5: 262144, 6: 1048576, 7: 4194304}.get((bd >> 4) & 7)
    if block_max is None or bd & 0x8F:
        raise BootVerifyError(f"invalid LZ4 BD: 0x{bd:02x}")
    content_size = None
    if flg & 0x08:
        if position + 8 > len(frame):
            raise BootVerifyError("truncated LZ4 content size")
        content_size = struct.unpack_from("<Q", frame, position)[0]
        position += 8
    if position >= len(frame):
        raise BootVerifyError("truncated LZ4 header")
    descriptor = frame[descriptor_start:position]
    if frame[position] != (xxh32(descriptor) >> 8) & 0xFF:
        raise BootVerifyError("LZ4 header checksum mismatch")
    position += 1
    blocks: list[tuple[bool, bytes]] = []
    while True:
        if position + 4 > len(frame):
            raise BootVerifyError("truncated LZ4 block size")
        encoded_size = struct.unpack_from("<I", frame, position)[0]
        position += 4
        if encoded_size == 0:
            break
        block_size = encoded_size & 0x7FFFFFFF
        if not block_size or block_size > block_max or position + block_size > len(frame):
            raise BootVerifyError("invalid or truncated LZ4 block")
        uncompressed = bool(encoded_size & 0x80000000)
        block = frame[position : position + block_size]
        position += block_size
        if flg & 0x10:
            if position + 4 > len(frame):
                raise BootVerifyError("truncated LZ4 block checksum")
            checksum = struct.unpack_from("<I", frame, position)[0]
            if checksum != xxh32(block):
                raise BootVerifyError("LZ4 block checksum mismatch")
            position += 4
        blocks.append((uncompressed, block))
    content_checksum = None
    if flg & 0x04:
        if position + 4 > len(frame):
            raise BootVerifyError("truncated LZ4 content checksum")
        content_checksum = struct.unpack_from("<I", frame, position)[0]
        position += 4
    if position != len(frame):
        raise BootVerifyError("trailing or concatenated LZ4 data")
    info = {
        "flg": flg,
        "bd": bd,
        "content_size": content_size,
        "block_count": len(blocks),
        "frame_size": len(frame),
        "header_checksum_valid": True,
        "block_checksums_valid": True,
        "content_checksum_present": content_checksum is not None,
        "single_frame_no_trailing_data": True,
    }
    return info, tuple(blocks), content_checksum


def parse_lz4_frame(frame: bytes) -> dict[str, Any]:
    info, blocks, content_checksum = _parse_lz4_frame_layout(frame)
    _decompress_lz4_layout(
        info,
        blocks,
        content_checksum,
        expected_size=info["content_size"],
        maximum=256 * 1024 * 1024,
    )
    return info


def _decompress_lz4_block(block: bytes, maximum: int) -> bytes:
    output = bytearray()
    position = 0
    sequence_count = 0
    final_literal_size: int | None = None
    last_match_start: int | None = None
    while position < len(block):
        sequence_count += 1
        token = block[position]
        position += 1
        literal_size = token >> 4
        if literal_size == 15:
            while True:
                if position >= len(block):
                    raise BootVerifyError("truncated LZ4 literal length")
                value = block[position]
                position += 1
                literal_size += value
                if value != 255:
                    break
        if position + literal_size > len(block):
            raise BootVerifyError("truncated LZ4 literals")
        if len(output) + literal_size > maximum:
            raise BootVerifyError("LZ4 block exceeds output bound")
        output.extend(block[position : position + literal_size])
        position += literal_size
        if position == len(block):
            final_literal_size = literal_size
            break
        if position + 2 > len(block):
            raise BootVerifyError("truncated LZ4 match offset")
        offset = int.from_bytes(block[position : position + 2], "little")
        position += 2
        if offset == 0 or offset > len(output):
            raise BootVerifyError("invalid LZ4 match offset")
        match_size = token & 0x0F
        if match_size == 15:
            while True:
                if position >= len(block):
                    raise BootVerifyError("truncated LZ4 match length")
                value = block[position]
                position += 1
                match_size += value
                if value != 255:
                    break
        match_size += 4
        if len(output) + match_size > maximum:
            raise BootVerifyError("LZ4 block exceeds output bound")
        last_match_start = len(output)
        for _ in range(match_size):
            output.append(output[-offset])
    if final_literal_size is None:
        raise BootVerifyError("LZ4 block ends with a match")
    if len(output) >= 5:
        if final_literal_size < 5:
            raise BootVerifyError("LZ4 block has fewer than 5 final literals")
    elif sequence_count != 1 or final_literal_size != len(output):
        raise BootVerifyError("invalid short LZ4 block termination")
    if last_match_start is not None and last_match_start > len(output) - 12:
        raise BootVerifyError("last LZ4 match starts too close to block end")
    return bytes(output)


def decompress_lz4_legacy_python(
    stream: bytes,
    *,
    expected_size: int | None = None,
    maximum: int = 256 * 1024 * 1024,
) -> bytes:
    """Decode one bounded legacy LZ4 stream without an external tool."""
    if maximum <= 0 or maximum > 1024 * 1024 * 1024:
        raise BootVerifyError("invalid LZ4 output bound")
    if not stream.startswith(LZ4_LEGACY_MAGIC):
        raise BootVerifyError("legacy LZ4 magic missing")
    position = len(LZ4_LEGACY_MAGIC)
    output = bytearray()
    block_count = 0
    while position < len(stream):
        if position + 4 > len(stream):
            raise BootVerifyError("truncated legacy LZ4 block size")
        block_size = struct.unpack_from("<I", stream, position)[0]
        position += 4
        if not block_size or block_size > LZ4_LEGACY_COMPRESSED_BLOCK_MAX:
            raise BootVerifyError("invalid legacy LZ4 block size")
        block_end = position + block_size
        if block_end > len(stream):
            raise BootVerifyError("truncated legacy LZ4 block")
        remaining = maximum - len(output)
        if remaining <= 0:
            raise BootVerifyError("legacy LZ4 stream exceeds output bound")
        decoded = _decompress_lz4_block(
            stream[position:block_end], min(LZ4_LEGACY_BLOCK_MAX, remaining)
        )
        output.extend(decoded)
        position = block_end
        block_count += 1
    if block_count == 0:
        raise BootVerifyError("legacy LZ4 stream has no blocks")
    if expected_size is not None and len(output) != expected_size:
        raise BootVerifyError(
            f"LZ4 decoded size mismatch: {len(output)} != {expected_size}"
        )
    return bytes(output)


def _decompress_lz4_layout(
    info: dict[str, Any],
    blocks: tuple[tuple[bool, bytes], ...],
    content_checksum: int | None,
    *,
    expected_size: int | None = None,
    maximum: int = 256 * 1024 * 1024,
) -> bytes:
    if maximum <= 0 or maximum > 1024 * 1024 * 1024:
        raise BootVerifyError("invalid LZ4 output bound")
    flg = info["flg"]
    if not flg & 0x20:
        raise BootVerifyError("dependent-block LZ4 frames are not accepted")
    block_max = {4: 65536, 5: 262144, 6: 1048576, 7: 4194304}[
        (info["bd"] >> 4) & 7
    ]
    content_size = info["content_size"]
    output = bytearray()
    for uncompressed, block in blocks:
        decoded = (
            block
            if uncompressed
            else _decompress_lz4_block(block, block_max)
        )
        if len(decoded) > block_max or len(output) + len(decoded) > maximum:
            raise BootVerifyError("LZ4 frame exceeds output bound")
        output.extend(decoded)
    if content_checksum is not None and content_checksum != xxh32(bytes(output)):
        raise BootVerifyError("LZ4 content checksum mismatch")
    required_size = expected_size if expected_size is not None else content_size
    if required_size is not None and len(output) != required_size:
        raise BootVerifyError(
            f"LZ4 decoded size mismatch: {len(output)} != {required_size}"
        )
    return bytes(output)


def decompress_lz4_frame_python(
    frame: bytes,
    *,
    expected_size: int | None = None,
    maximum: int = 256 * 1024 * 1024,
) -> bytes:
    """Decode one bounded independent-block LZ4 frame without an external tool."""
    info, blocks, content_checksum = _parse_lz4_frame_layout(frame)
    return _decompress_lz4_layout(
        info,
        blocks,
        content_checksum,
        expected_size=expected_size,
        maximum=maximum,
    )


def decompress_lz4_stream_python(
    stream: bytes,
    *,
    expected_size: int | None = None,
    maximum: int = 256 * 1024 * 1024,
) -> bytes:
    """Decode one bounded modern-frame or legacy LZ4 stream."""
    if stream.startswith(LZ4_FRAME_MAGIC):
        return decompress_lz4_frame_python(
            stream, expected_size=expected_size, maximum=maximum
        )
    if stream.startswith(LZ4_LEGACY_MAGIC):
        return decompress_lz4_legacy_python(
            stream, expected_size=expected_size, maximum=maximum
        )
    raise BootVerifyError("recognized LZ4 stream magic missing")


def decompress_lz4(tool: Path, frame: bytes, expected_size: int | None = None) -> bytes:
    result = subprocess.run(
        [str(tool), "-d", "-c"],
        input=frame,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise BootVerifyError(f"LZ4 decompression failed: {result.stderr.decode(errors='replace')}")
    if expected_size is not None and len(result.stdout) != expected_size:
        raise BootVerifyError(f"LZ4 decoded size mismatch: {len(result.stdout)} != {expected_size}")
    return result.stdout


def normalize_cpio_name(encoded_name: str) -> str:
    if not encoded_name or encoded_name.startswith("/") or "\\" in encoded_name:
        raise BootVerifyError(f"unsafe CPIO path: {encoded_name!r}")
    path = PurePosixPath(encoded_name)
    if any(part in ("", "..") for part in path.parts):
        raise BootVerifyError(f"unsafe CPIO path: {encoded_name!r}")
    parts = [part for part in path.parts if part != "."]
    normalized = "/".join(parts)
    if encoded_name not in (normalized, f"./{normalized}"):
        raise BootVerifyError(f"noncanonical CPIO path alias: {encoded_name!r}")
    return normalized or "."


def parse_newc(data: bytes) -> tuple[CpioEntry, ...]:
    entries: list[CpioEntry] = []
    names: set[str] = set()
    offset = 0
    trailer_end = None
    while True:
        if offset + 110 > len(data):
            raise BootVerifyError("truncated newc header")
        header = data[offset : offset + 110]
        if header[:6] not in CPIO_MAGICS:
            raise BootVerifyError(f"invalid newc magic at offset {offset}")
        try:
            fields = [int(header[6 + index * 8 : 14 + index * 8], 16) for index in range(13)]
        except ValueError as exc:
            raise BootVerifyError(f"invalid newc field at offset {offset}") from exc
        inode, mode, uid, gid, nlink, mtime, size = fields[:7]
        name_size = fields[11]
        if name_size < 1:
            raise BootVerifyError("newc name size is zero")
        name_start = offset + 110
        name_end = name_start + name_size
        if name_end > len(data) or data[name_end - 1] != 0:
            raise BootVerifyError("truncated or unterminated newc name")
        try:
            encoded_name = data[name_start : name_end - 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BootVerifyError("newc name is not UTF-8") from exc
        content_start = align(name_end, 4)
        if any(data[name_end:content_start]):
            raise BootVerifyError(f"nonzero newc name padding: {encoded_name}")
        content_end = content_start + size
        if content_end > len(data):
            raise BootVerifyError(f"truncated newc content: {encoded_name}")
        next_offset = align(content_end, 4)
        if any(data[content_end:next_offset]):
            raise BootVerifyError(f"nonzero newc content padding: {encoded_name}")
        if encoded_name == "TRAILER!!!":
            trailer_end = next_offset
            break
        normalized = normalize_cpio_name(encoded_name)
        if normalized in names:
            raise BootVerifyError(f"duplicate or aliased CPIO entry: {normalized}")
        names.add(normalized)
        entries.append(
            CpioEntry(
                encoded_name,
                normalized,
                inode,
                mode,
                uid,
                gid,
                nlink,
                mtime,
                data[content_start:content_end],
            )
        )
        offset = next_offset
    assert trailer_end is not None
    if any(data[trailer_end:]):
        raise BootVerifyError("nonzero data follows newc trailer")
    return tuple(entries)


def inspect_aarch64_static_init(elf: bytes) -> dict[str, Any]:
    if len(elf) < 64 or elf[:4] != b"\x7fELF":
        raise BootVerifyError("/init is not ELF")
    if elf[4:6] != b"\x02\x01":
        raise BootVerifyError("/init must be ELF64 little-endian")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", elf, 0)
    machine, entry, phoff, shoff = header[2], header[4], header[5], header[6]
    phentsize, phnum, shentsize, shnum = header[9], header[10], header[11], header[12]
    if machine != 183 or phentsize != 56:
        raise BootVerifyError("/init is not an AArch64 ELF with standard program headers")
    load_offset = None
    interpreter = False
    for index in range(phnum):
        offset = phoff + index * phentsize
        if offset + phentsize > len(elf):
            raise BootVerifyError("truncated /init program header")
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, _p_memsz, _p_align = struct.unpack_from(
            "<IIQQQQQQ", elf, offset
        )
        interpreter |= p_type == 3
        if p_type == 1 and p_flags & 1 and p_vaddr <= entry < p_vaddr + p_filesz:
            load_offset = p_offset + entry - p_vaddr
    if interpreter or load_offset is None:
        raise BootVerifyError("/init has an interpreter or unmapped entrypoint")
    if shentsize != 64:
        raise BootVerifyError("/init has nonstandard section headers")
    executable_ranges: list[tuple[int, int]] = []
    for index in range(shnum):
        offset = shoff + index * shentsize
        if offset + shentsize > len(elf):
            raise BootVerifyError("truncated /init section header")
        _name, _type, flags, _addr, section_offset, section_size, *_rest = struct.unpack_from(
            "<IIQQQQIIQQ", elf, offset
        )
        if flags & 0x4 and section_size:
            if section_offset + section_size > len(elf):
                raise BootVerifyError("/init executable section exceeds file")
            executable_ranges.append((section_offset, section_size))
    executable = b"".join(elf[offset : offset + size] for offset, size in executable_ranges)
    if len(executable) != 8 or load_offset + 8 > len(elf):
        raise BootVerifyError("/init executable footprint is not exactly two instructions")
    words = struct.unpack_from("<2I", elf, load_offset)
    if words != (0xD503205F, 0x17FFFFFF):
        raise BootVerifyError(f"/init entrypoint is not exact wfe; b: {[hex(word) for word in words]}")
    if any((word[0] & 0xFFE0001F) == 0xD4000001 for word in struct.iter_unpack("<I", executable)):
        raise BootVerifyError("/init executable section contains svc")
    return {
        "elf_class": 64,
        "machine": "AArch64",
        "entrypoint": entry,
        "interpreter": False,
        "executable_size": len(executable),
        "instruction_words": [f"0x{word:08x}" for word in words],
        "instructions": ["wfe", "b <entrypoint>"],
        "syscall_instruction": False,
        "verified": True,
    }


def run_avbtool(tool: Path, image: bytes) -> dict[str, Any]:
    if not hasattr(os, "memfd_create"):
        raise BootVerifyError("sealed memfd support is required")
    descriptor = os.memfd_create("s22plus-boot-verify", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(image)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written : written + 4 * 1024 * 1024])
            if count <= 0:
                raise BootVerifyError("short write to AVB memfd")
            written += count
        os.lseek(descriptor, 0, os.SEEK_SET)
        seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
        with tempfile.TemporaryDirectory(prefix="s22plus-boot-verify-") as temporary:
            image_path = Path(temporary) / "boot"
            image_path.symlink_to(f"/proc/self/fd/{descriptor}")
            result = subprocess.run(
                [str(tool), "verify_image", "--image", str(image_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=60,
                pass_fds=(descriptor,),
            )
    finally:
        os.close(descriptor)
    combined = result.stdout + result.stderr
    return {
        "returncode": result.returncode,
        "vbmeta_signature_verified": "Successfully verified footer and SHA256_RSA4096 vbmeta struct" in combined,
        "payload_hash_verified": "Successfully verified sha256 hash" in combined,
        "payload_hash_mismatch": "does not match digest in descriptor" in combined,
        "input_transport": "sealed-memfd",
    }
