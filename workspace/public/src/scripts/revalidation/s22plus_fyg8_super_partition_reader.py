#!/usr/bin/env python3
"""Read Android super-partition metadata and extract one logical partition.

Gate 0 for this campaign is the normal-boot second-stage module list,
`vendor_dlkm/lib/modules/modules.load`, which lives inside `super.img` and has
never been recovered.  `lpunpack` is not installed on this host, so the metadata
is parsed directly from the image.

Formats handled:

  - Android sparse images (magic 0xed26ff3a), unsparsed on the fly
  - LP metadata (`liblp`): geometry at 4096, metadata slots from 12288

Nothing here touches a device.  It reads a file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any, BinaryIO

SCHEMA = "s22plus_fyg8_super_partition_reader_v1"

SPARSE_MAGIC = 0xED26FF3A
LP_GEOMETRY_MAGIC = 0x616C4467
LP_HEADER_MAGIC = 0x414C5030
LP_PARTITION_RESERVED_BYTES = 4096
LP_METADATA_GEOMETRY_SIZE = 4096
SECTOR_SIZE = 512


class SuperReadError(RuntimeError):
    pass


class SparseReader:
    """Random access over an Android sparse image without materialising it.

    The raw super partition is larger than the sparse file and the host has
    limited free space, so the chunk table is indexed once -- headers only, no
    payload -- and reads are served by seeking into the covering chunk.
    """

    RAW, FILL, DONT_CARE, CRC32 = 0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4

    def __init__(self, handle: BinaryIO) -> None:
        self.handle = handle
        handle.seek(0)
        header = handle.read(28)
        (magic, _major, _minor, file_hdr_sz, chunk_hdr_sz, self.block_size,
         self.total_blocks, total_chunks, _checksum) = struct.unpack(
            "<IHHHHIIII", header
        )
        if magic != SPARSE_MAGIC:
            raise SuperReadError("sparse magic missing")
        handle.seek(file_hdr_sz)
        self.chunks: list[tuple[int, int, int, int, bytes]] = []
        block = 0
        for _ in range(total_chunks):
            chunk_header = handle.read(chunk_hdr_sz)
            chunk_type, _reserved, chunk_blocks, total_size = struct.unpack_from(
                "<HHII", chunk_header, 0
            )
            payload_at = handle.tell()
            payload_size = total_size - chunk_hdr_sz
            fill = b""
            if chunk_type == self.FILL:
                fill = handle.read(4)
            else:
                handle.seek(payload_at + payload_size)
            self.chunks.append(
                (block, chunk_blocks, chunk_type, payload_at, fill)
            )
            block += chunk_blocks
        self.size = self.total_blocks * self.block_size
        self.position = 0

    def seek(self, offset: int) -> None:
        self.position = offset

    def read(self, length: int) -> bytes:
        out = bytearray()
        while length > 0:
            block = self.position // self.block_size
            inside = self.position % self.block_size
            chunk = self._chunk_for(block)
            if chunk is None:
                break
            start_block, blocks, chunk_type, payload_at, fill = chunk
            available = (start_block + blocks) * self.block_size - self.position
            take = min(length, available)
            if chunk_type == self.RAW:
                self.handle.seek(
                    payload_at + (block - start_block) * self.block_size + inside
                )
                out += self.handle.read(take)
            elif chunk_type == self.FILL:
                pattern = fill * (take // 4 + 2)
                out += pattern[inside % 4 : inside % 4 + take]
            else:
                out += b"\x00" * take
            self.position += take
            length -= take
        return bytes(out)

    def _chunk_for(self, block: int):
        low, high = 0, len(self.chunks) - 1
        while low <= high:
            mid = (low + high) // 2
            start, blocks, *_ = self.chunks[mid]
            if block < start:
                high = mid - 1
            elif block >= start + blocks:
                low = mid + 1
            else:
                return self.chunks[mid]
        return None


def is_sparse(handle: BinaryIO) -> bool:
    handle.seek(0)
    head = handle.read(4)
    handle.seek(0)
    return len(head) == 4 and struct.unpack("<I", head)[0] == SPARSE_MAGIC


def read_geometry(handle: BinaryIO) -> dict[str, Any]:
    handle.seek(LP_PARTITION_RESERVED_BYTES)
    raw = handle.read(LP_METADATA_GEOMETRY_SIZE)
    magic, struct_size = struct.unpack_from("<II", raw, 0)
    if magic != LP_GEOMETRY_MAGIC:
        raise SuperReadError(f"LP geometry magic missing: 0x{magic:08x}")
    checksum = raw[8:40]
    metadata_max_size, slot_count, logical_block_size = struct.unpack_from(
        "<III", raw, 40
    )
    # The checksum covers the geometry with its own checksum field zeroed.
    blanked = raw[:8] + b"\x00" * 32 + raw[40:struct_size]
    if hashlib.sha256(blanked).digest() != checksum:
        raise SuperReadError("LP geometry checksum mismatch")
    return {
        "struct_size": struct_size,
        "metadata_max_size": metadata_max_size,
        "metadata_slot_count": slot_count,
        "logical_block_size": logical_block_size,
    }


def read_metadata(handle: BinaryIO, geometry: dict[str, Any], slot: int = 0) -> dict[str, Any]:
    base = LP_PARTITION_RESERVED_BYTES + LP_METADATA_GEOMETRY_SIZE * 2
    offset = base + slot * geometry["metadata_max_size"]
    handle.seek(offset)
    header = handle.read(256)
    magic, major, minor, header_size = struct.unpack_from("<IHHI", header, 0)
    if magic != LP_HEADER_MAGIC:
        raise SuperReadError(f"LP header magic missing: 0x{magic:08x}")
    tables_size = struct.unpack_from("<I", header, 44)[0]
    tables_checksum = header[48:80]
    descriptors = []
    position = 80
    for _ in range(4):
        descriptors.append(struct.unpack_from("<III", header, position))
        position += 12
    handle.seek(offset + header_size)
    tables = handle.read(tables_size)
    if hashlib.sha256(tables).digest() != tables_checksum:
        raise SuperReadError("LP tables checksum mismatch")

    (p_off, p_num, p_size) = descriptors[0]
    (e_off, e_num, e_size) = descriptors[1]
    # Entry sizes are read from the descriptors rather than assumed, but the
    # unpack formats below are fixed, so a mismatch must stop rather than slide.
    if p_size != 52 or e_size != struct.calcsize("<QIQI"):
        raise SuperReadError(
            f"unexpected LP entry sizes: partition={p_size} extent={e_size}"
        )
    partitions = []
    for index in range(p_num):
        raw = tables[p_off + index * p_size : p_off + (index + 1) * p_size]
        name = raw[:36].split(b"\x00", 1)[0].decode("utf-8", "replace")
        attributes, first_extent, num_extents, group = struct.unpack_from(
            "<IIII", raw, 36
        )
        partitions.append(
            {
                "name": name,
                "attributes": attributes,
                "first_extent_index": first_extent,
                "num_extents": num_extents,
                "group_index": group,
            }
        )
    extents = []
    for index in range(e_num):
        raw = tables[e_off + index * e_size : e_off + (index + 1) * e_size]
        num_sectors, target_type, target_data, target_source = struct.unpack_from(
            "<QIQI", raw, 0
        )
        extents.append(
            {
                "num_sectors": num_sectors,
                "target_type": target_type,
                "target_data": target_data,
                "target_source": target_source,
            }
        )
    return {
        "major_version": major,
        "minor_version": minor,
        "header_size": header_size,
        "partitions": partitions,
        "extents": extents,
    }


def partition_extents(metadata: dict[str, Any], name: str) -> list[dict[str, Any]]:
    for partition in metadata["partitions"]:
        if partition["name"] == name:
            start = partition["first_extent_index"]
            return metadata["extents"][start : start + partition["num_extents"]]
    raise SuperReadError(f"logical partition not found: {name}")


def extract(handle: BinaryIO, extents: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    written = 0
    with open(out, "wb") as sink:
        for extent in extents:
            if extent["target_type"] != 0:
                # ZERO extents contribute holes rather than image bytes.
                payload = b"\x00" * (extent["num_sectors"] * SECTOR_SIZE)
                sink.write(payload)
                digest.update(payload)
                written += len(payload)
                continue
            handle.seek(extent["target_data"] * SECTOR_SIZE)
            remaining = extent["num_sectors"] * SECTOR_SIZE
            while remaining:
                chunk = handle.read(min(remaining, 8 * 1024 * 1024))
                if not chunk:
                    raise SuperReadError("truncated extent read")
                sink.write(chunk)
                digest.update(chunk)
                written += len(chunk)
                remaining -= len(chunk)
    return {"bytes": written, "sha256": digest.hexdigest(), "out": str(out)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--extract", help="logical partition name to write out")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    with open(args.image, "rb") as handle:
        source: Any = handle
        sparse = is_sparse(handle)
        if sparse:
            source = SparseReader(handle)
        geometry = read_geometry(source)
        metadata = read_metadata(source, geometry)
        value: dict[str, Any] = {
            "schema": SCHEMA,
            "image": str(args.image),
            "sparse": sparse,
            "geometry": geometry,
            "metadata_version": f"{metadata['major_version']}.{metadata['minor_version']}",
            "partitions": [
                {
                    "name": partition["name"],
                    "extents": partition["num_extents"],
                    "size": sum(
                        extent["num_sectors"] * SECTOR_SIZE
                        for extent in partition_extents(metadata, partition["name"])
                    ),
                }
                for partition in metadata["partitions"]
            ],
            "device_contact": False,
        }
        if args.extract:
            if args.out is None:
                raise SuperReadError("--extract requires --out")
            value["extracted"] = extract(
                source, partition_extents(metadata, args.extract), args.out
            )
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
