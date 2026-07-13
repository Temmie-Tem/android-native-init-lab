#!/usr/bin/env python3
"""Validate an unsparsed Android super image and extract selected partitions.

This host-only helper implements the AOSP liblp v10 metadata layout needed by
the FYG8 oracle audit. It accepts only a direct regular-file input, validates
both geometry blocks and the primary/backup slot-0 metadata checksums, and
creates only explicitly selected partition image files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_lp_extract_v1"
LP_METADATA_GEOMETRY_MAGIC = 0x616C4467
LP_METADATA_HEADER_MAGIC = 0x414C5030
LP_PARTITION_RESERVED_BYTES = 4096
LP_METADATA_GEOMETRY_SIZE = 4096
LP_SECTOR_SIZE = 512
LP_TARGET_TYPE_LINEAR = 0
LP_TARGET_TYPE_ZERO = 1
GEOMETRY_STRUCT_SIZE = 52
HEADER_V1_0_SIZE = 128
HEADER_V1_2_SIZE = 256
NAME_RE = re.compile(r"[A-Za-z0-9_]+")
COPY_CHUNK_SIZE = 4 * 1024 * 1024


class LpError(ValueError):
    pass


@dataclass(frozen=True)
class Geometry:
    metadata_max_size: int
    metadata_slot_count: int
    logical_block_size: int
    sha256: str


@dataclass(frozen=True)
class Extent:
    num_sectors: int
    target_type: int
    target_data: int
    target_source: int


@dataclass(frozen=True)
class Partition:
    name: str
    attributes: int
    first_extent_index: int
    num_extents: int
    group_index: int


@dataclass(frozen=True)
class BlockDevice:
    first_logical_sector: int
    alignment: int
    alignment_offset: int
    size: int
    partition_name: str
    flags: int


@dataclass(frozen=True)
class Metadata:
    major_version: int
    minor_version: int
    header_size: int
    tables_size: int
    slot_sha256: str
    partitions: tuple[Partition, ...]
    extents: tuple[Extent, ...]
    block_devices: tuple[BlockDevice, ...]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def direct_regular_file(path: Path) -> Path:
    if path.is_symlink():
        raise LpError(f"symlink input refused: {path}")
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise LpError(f"input missing: {path}") from exc
    if not stat.S_ISREG(mode):
        raise LpError(f"input is not a regular file: {path}")
    return path.resolve()


def pread_exact(fd: int, size: int, offset: int) -> bytes:
    if size < 0 or offset < 0:
        raise LpError("negative read range")
    data = os.pread(fd, size, offset)
    if len(data) != size:
        raise LpError(f"short read at {offset}: {len(data)} != {size}")
    return data


def checked_name(raw: bytes, kind: str) -> str:
    head, separator, tail = raw.partition(b"\0")
    if separator and any(tail):
        raise LpError(f"{kind} name has nonzero bytes after NUL")
    try:
        name = head.decode("ascii")
    except UnicodeDecodeError as exc:
        raise LpError(f"{kind} name is not ASCII") from exc
    if not name or NAME_RE.fullmatch(name) is None:
        raise LpError(f"invalid {kind} name: {name!r}")
    return name


def parse_geometry(block: bytes) -> Geometry:
    if len(block) != LP_METADATA_GEOMETRY_SIZE:
        raise LpError("geometry block size mismatch")
    magic, struct_size = struct.unpack_from("<II", block, 0)
    if magic != LP_METADATA_GEOMETRY_MAGIC:
        raise LpError(f"geometry magic mismatch: 0x{magic:08x}")
    if struct_size != GEOMETRY_STRUCT_SIZE:
        raise LpError(f"unsupported geometry struct size: {struct_size}")
    stored_checksum = block[8:40]
    checked = bytearray(block[:struct_size])
    checked[8:40] = b"\0" * 32
    if hashlib.sha256(checked).digest() != stored_checksum:
        raise LpError("geometry checksum mismatch")
    metadata_max_size, slot_count, logical_block_size = struct.unpack_from("<III", block, 40)
    if metadata_max_size == 0 or metadata_max_size % LP_SECTOR_SIZE:
        raise LpError("invalid metadata_max_size")
    if not 1 <= slot_count <= 4:
        raise LpError(f"invalid metadata_slot_count: {slot_count}")
    if logical_block_size == 0 or logical_block_size % LP_SECTOR_SIZE:
        raise LpError("invalid logical_block_size")
    return Geometry(
        metadata_max_size=metadata_max_size,
        metadata_slot_count=slot_count,
        logical_block_size=logical_block_size,
        sha256=sha256_bytes(block),
    )


def descriptor(header: bytes, offset: int) -> tuple[int, int, int]:
    return struct.unpack_from("<III", header, offset)


def table_entries(tables: bytes, desc: tuple[int, int, int], minimum_size: int, name: str) -> list[bytes]:
    offset, count, entry_size = desc
    if entry_size < minimum_size:
        raise LpError(f"{name} entry size too small: {entry_size}")
    size = count * entry_size
    if offset > len(tables) or size > len(tables) - offset:
        raise LpError(f"{name} table range outside metadata")
    return [tables[offset + index * entry_size:offset + (index + 1) * entry_size] for index in range(count)]


def parse_metadata_slot(slot: bytes) -> Metadata:
    if len(slot) < HEADER_V1_0_SIZE:
        raise LpError("metadata slot too small")
    magic, major, minor, header_size = struct.unpack_from("<IHHI", slot, 0)
    if magic != LP_METADATA_HEADER_MAGIC:
        raise LpError(f"metadata magic mismatch: 0x{magic:08x}")
    if major != 10 or minor not in (0, 1, 2):
        raise LpError(f"unsupported metadata version: {major}.{minor}")
    if header_size not in (HEADER_V1_0_SIZE, HEADER_V1_2_SIZE):
        raise LpError(f"unsupported metadata header size: {header_size}")
    tables_size = struct.unpack_from("<I", slot, 44)[0]
    if header_size + tables_size > len(slot):
        raise LpError("metadata header and tables exceed slot")

    header = bytearray(slot[:header_size])
    stored_header_checksum = bytes(header[12:44])
    header[12:44] = b"\0" * 32
    if hashlib.sha256(header).digest() != stored_header_checksum:
        raise LpError("metadata header checksum mismatch")
    tables = slot[header_size:header_size + tables_size]
    if hashlib.sha256(tables).digest() != slot[48:80]:
        raise LpError("metadata tables checksum mismatch")

    descriptions = {
        "partitions": descriptor(slot, 80),
        "extents": descriptor(slot, 92),
        "groups": descriptor(slot, 104),
        "block_devices": descriptor(slot, 116),
    }
    ranges = sorted(
        (offset, offset + count * entry_size, name)
        for name, (offset, count, entry_size) in descriptions.items()
    )
    cursor = 0
    for start, end, name in ranges:
        if start != cursor or end < start or end > tables_size:
            raise LpError(f"non-contiguous or invalid {name} table range")
        cursor = end
    if cursor != tables_size:
        raise LpError("metadata tables do not cover tables_size")

    partition_rows = table_entries(tables, descriptions["partitions"], 52, "partition")
    extent_rows = table_entries(tables, descriptions["extents"], 24, "extent")
    table_entries(tables, descriptions["groups"], 48, "group")
    block_rows = table_entries(tables, descriptions["block_devices"], 64, "block device")

    partitions = tuple(
        Partition(checked_name(row[:36], "partition"), *struct.unpack_from("<IIII", row, 36))
        for row in partition_rows
    )
    if len({partition.name for partition in partitions}) != len(partitions):
        raise LpError("duplicate partition name")
    extents = tuple(Extent(*struct.unpack_from("<QIQI", row, 0)) for row in extent_rows)
    block_devices = tuple(
        BlockDevice(
            *struct.unpack_from("<QIIQ", row, 0),
            checked_name(row[24:60], "block device"),
            struct.unpack_from("<I", row, 60)[0],
        )
        for row in block_rows
    )
    if not block_devices:
        raise LpError("metadata has no block device")

    for partition in partitions:
        if partition.num_extents == 0:
            raise LpError(f"partition has no extents: {partition.name}")
        end = partition.first_extent_index + partition.num_extents
        if end > len(extents):
            raise LpError(f"partition extent range is invalid: {partition.name}")
    for extent in extents:
        if extent.num_sectors == 0:
            raise LpError("zero-length extent")
        if extent.target_type not in (LP_TARGET_TYPE_LINEAR, LP_TARGET_TYPE_ZERO):
            raise LpError(f"unsupported extent target type: {extent.target_type}")
        if extent.target_type == LP_TARGET_TYPE_LINEAR:
            if extent.target_source >= len(block_devices):
                raise LpError("extent target_source is outside block-device table")
            block = block_devices[extent.target_source]
            if extent.target_data + extent.num_sectors > block.size // LP_SECTOR_SIZE:
                raise LpError("linear extent exceeds block device")
        elif extent.target_data != 0 or extent.target_source != 0:
            raise LpError("zero extent has nonzero target fields")

    return Metadata(
        major_version=major,
        minor_version=minor,
        header_size=header_size,
        tables_size=tables_size,
        slot_sha256=sha256_bytes(slot),
        partitions=partitions,
        extents=extents,
        block_devices=block_devices,
    )


def read_validated_metadata(path: Path) -> tuple[Path, Geometry, Metadata]:
    resolved = direct_regular_file(path)
    fd = os.open(resolved, os.O_RDONLY | os.O_CLOEXEC)
    try:
        primary_geometry = pread_exact(fd, LP_METADATA_GEOMETRY_SIZE, LP_PARTITION_RESERVED_BYTES)
        backup_geometry = pread_exact(
            fd, LP_METADATA_GEOMETRY_SIZE, LP_PARTITION_RESERVED_BYTES + LP_METADATA_GEOMETRY_SIZE
        )
        if primary_geometry != backup_geometry:
            raise LpError("primary and backup geometry blocks differ")
        geometry = parse_geometry(primary_geometry)
        metadata_base = LP_PARTITION_RESERVED_BYTES + 2 * LP_METADATA_GEOMETRY_SIZE
        primary = pread_exact(fd, geometry.metadata_max_size, metadata_base)
        backup_offset = metadata_base + geometry.metadata_max_size * geometry.metadata_slot_count
        backup = pread_exact(fd, geometry.metadata_max_size, backup_offset)
        if primary != backup:
            raise LpError("primary and backup slot-0 metadata differ")
        metadata = parse_metadata_slot(primary)
        actual_size = os.fstat(fd).st_size
        if metadata.block_devices[0].size != actual_size:
            raise LpError(
                f"super size mismatch: {actual_size} != {metadata.block_devices[0].size}"
            )
        return resolved, geometry, metadata
    finally:
        os.close(fd)


def partition_extents(metadata: Metadata, partition: Partition) -> tuple[Extent, ...]:
    start = partition.first_extent_index
    return metadata.extents[start:start + partition.num_extents]


def update_zeros(digest: Any, length: int) -> None:
    zeros = b"\0" * min(COPY_CHUNK_SIZE, length)
    remaining = length
    while remaining:
        chunk = zeros[:min(len(zeros), remaining)]
        digest.update(chunk)
        remaining -= len(chunk)


def extract_partition(
    source: Path,
    geometry: Geometry,
    metadata: Metadata,
    partition: Partition,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise LpError(f"output directory is not a direct directory: {output_dir}")
    output = output_dir / f"{partition.name}.img"
    if output.exists() or output.is_symlink():
        raise LpError(f"output already exists: {output}")

    digest = hashlib.sha256()
    logical_size = 0
    source_fd = os.open(source, os.O_RDONLY | os.O_CLOEXEC)
    try:
        with output.open("xb", buffering=0) as target:
            try:
                for extent in partition_extents(metadata, partition):
                    length = extent.num_sectors * LP_SECTOR_SIZE
                    logical_size += length
                    if extent.target_type == LP_TARGET_TYPE_ZERO:
                        update_zeros(digest, length)
                        target.seek(length, os.SEEK_CUR)
                        continue
                    source_offset = extent.target_data * LP_SECTOR_SIZE
                    remaining = length
                    while remaining:
                        amount = min(COPY_CHUNK_SIZE, remaining)
                        data = pread_exact(source_fd, amount, source_offset)
                        digest.update(data)
                        if any(data):
                            target.write(data)
                        else:
                            target.seek(amount, os.SEEK_CUR)
                        source_offset += amount
                        remaining -= amount
                target.truncate(logical_size)
                target.flush()
                os.fsync(target.fileno())
            except Exception:
                output.unlink(missing_ok=True)
                raise
    finally:
        os.close(source_fd)
    return {
        "name": partition.name,
        "path": str(output),
        "size": logical_size,
        "sha256": digest.hexdigest(),
        "extent_count": partition.num_extents,
    }


def inspect(path: Path) -> tuple[Path, Geometry, Metadata, dict[str, Any]]:
    resolved, geometry, metadata = read_validated_metadata(path)
    partitions = []
    for partition in metadata.partitions:
        extents = partition_extents(metadata, partition)
        partitions.append(
            {
                "name": partition.name,
                "attributes": partition.attributes,
                "group_index": partition.group_index,
                "extent_count": len(extents),
                "size": sum(extent.num_sectors * LP_SECTOR_SIZE for extent in extents),
                "extents": [
                    {
                        "num_sectors": extent.num_sectors,
                        "target_type": extent.target_type,
                        "target_data": extent.target_data,
                        "target_source": extent.target_source,
                    }
                    for extent in extents
                ],
            }
        )
    report = {
        "schema": SCHEMA,
        "verdict": "PASS_FYG8_LP_METADATA_VALIDATED_HOST_ONLY",
        "input": {"path": str(resolved), "size": resolved.stat().st_size},
        "geometry": {
            "metadata_max_size": geometry.metadata_max_size,
            "metadata_slot_count": geometry.metadata_slot_count,
            "logical_block_size": geometry.logical_block_size,
            "primary_backup_identical": True,
            "sha256": geometry.sha256,
        },
        "metadata": {
            "major_version": metadata.major_version,
            "minor_version": metadata.minor_version,
            "header_size": metadata.header_size,
            "tables_size": metadata.tables_size,
            "primary_backup_slot0_identical": True,
            "slot0_sha256": metadata.slot_sha256,
            "block_devices": [
                {
                    "partition_name": block.partition_name,
                    "first_logical_sector": block.first_logical_sector,
                    "alignment": block.alignment,
                    "alignment_offset": block.alignment_offset,
                    "size": block.size,
                    "flags": block.flags,
                }
                for block in metadata.block_devices
            ],
            "partitions": partitions,
        },
        "safety": {
            "host_only": True,
            "input_regular_file_only": True,
            "device_contact": False,
            "block_device_access": False,
            "flash": False,
            "live_authorized": False,
        },
    }
    return resolved, geometry, metadata, report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("super_image", type=Path)
    parser.add_argument("--partition", action="append", default=[])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def write_new(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="ascii") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        source, geometry, metadata, report = inspect(args.super_image)
        requested = args.partition
        if bool(requested) != bool(args.output_dir):
            raise LpError("--partition and --output-dir must be supplied together")
        known = {partition.name: partition for partition in metadata.partitions}
        if len(requested) != len(set(requested)):
            raise LpError("duplicate --partition request")
        missing = sorted(set(requested) - set(known))
        if missing:
            raise LpError(f"unknown partition(s): {missing}")
        extracted = []
        if requested:
            if args.output_dir.is_symlink():
                raise LpError(f"symlink output directory refused: {args.output_dir}")
            output_dir = args.output_dir
            for name in requested:
                extracted.append(extract_partition(source, geometry, metadata, known[name], output_dir))
        report["extracted"] = extracted
        encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.out is not None:
            write_new(args.out.resolve(), encoded)
        print(encoded, end="")
        return 0
    except (LpError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
