#!/usr/bin/env python3
"""Stream one LZ4 frame from stdin to a file, for images too big to hold in RAM.

`s22plus_boot_verify.decompress_lz4_stream_python` decodes a whole frame in
memory, which is right for a 100 MB boot image and impossible for the 8.87 GB
`super.img.lz4`: that would need the compressed frame and the ~12 GB result
resident at once on a host with 15 GB total.

This reuses that module's block decoder and its header parsing rules rather than
reimplementing them, and only changes where the bytes go.  Samsung's frames use
independent blocks -- `_decompress_lz4_layout` rejects dependent-block frames and
the FYG8 boot image decoded through it -- so a block can be decoded and written
without carrying a dictionary forward.

The content checksum is not verified here, because that would require the whole
output in memory, which is the thing being avoided.  What is checked instead is
the header checksum, every block checksum when present, the declared content
size when present, and the decoded byte count.  Nothing here touches a device.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any, BinaryIO

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA = "s22plus_fyg8_super_stream_extract_v1"
BLOCK_MAX_BY_CODE = {4: 65536, 5: 262144, 6: 1048576, 7: 4194304}


def load_boot_verify():
    spec = importlib.util.spec_from_file_location(
        "s22plus_boot_verify_streamed", SCRIPT_DIR / "s22plus_boot_verify.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StreamExtractError(RuntimeError):
    pass


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    data = stream.read(count)
    if len(data) != count:
        raise StreamExtractError(f"short read: wanted {count}, got {len(data)}")
    return data


def stream_frame(stream: BinaryIO, out: BinaryIO, bv: Any) -> dict[str, Any]:
    if _read_exact(stream, 4) != bv.LZ4_FRAME_MAGIC:
        raise StreamExtractError("LZ4 frame magic missing")
    flg, bd = _read_exact(stream, 2)
    descriptor = bytes((flg, bd))
    if (flg >> 6) != 1 or flg & 0x02:
        raise StreamExtractError(f"invalid LZ4 FLG: 0x{flg:02x}")
    if flg & 0x01:
        raise StreamExtractError("LZ4 dictionary frames are not accepted")
    if not flg & 0x20:
        raise StreamExtractError("dependent-block LZ4 frames are not accepted")
    block_max = BLOCK_MAX_BY_CODE.get((bd >> 4) & 7)
    if block_max is None or bd & 0x8F:
        raise StreamExtractError(f"invalid LZ4 BD: 0x{bd:02x}")
    content_size = None
    if flg & 0x08:
        raw = _read_exact(stream, 8)
        descriptor += raw
        content_size = struct.unpack("<Q", raw)[0]
    if _read_exact(stream, 1)[0] != (bv.xxh32(descriptor) >> 8) & 0xFF:
        raise StreamExtractError("LZ4 header checksum mismatch")

    digest = hashlib.sha256()
    written = 0
    blocks = 0
    while True:
        encoded = struct.unpack("<I", _read_exact(stream, 4))[0]
        if encoded == 0:
            break
        size = encoded & 0x7FFFFFFF
        if not size or size > block_max:
            raise StreamExtractError("invalid LZ4 block size")
        block = _read_exact(stream, size)
        if flg & 0x10:
            checksum = struct.unpack("<I", _read_exact(stream, 4))[0]
            if checksum != bv.xxh32(block):
                raise StreamExtractError("LZ4 block checksum mismatch")
        decoded = (
            block
            if encoded & 0x80000000
            else bv._decompress_lz4_block(block, block_max)
        )
        if len(decoded) > block_max:
            raise StreamExtractError("LZ4 block exceeds its declared maximum")
        out.write(decoded)
        digest.update(decoded)
        written += len(decoded)
        blocks += 1
        if blocks % 512 == 0:
            print(
                f"  {blocks:>7} blocks  {written / 1e9:6.2f} GB", file=sys.stderr
            )
    if flg & 0x04:
        _read_exact(stream, 4)  # content checksum, not verified while streaming
    if content_size is not None and written != content_size:
        raise StreamExtractError(
            f"decoded size mismatch: {written} != {content_size}"
        )
    return {
        "schema": SCHEMA,
        "blocks": blocks,
        "block_max": block_max,
        "declared_content_size": content_size,
        "bytes_written": written,
        "sha256": digest.hexdigest(),
        "content_checksum_present": bool(flg & 0x04),
        "content_checksum_verified": False,
        "block_checksums_verified": bool(flg & 0x10),
        "device_contact": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    bv = load_boot_verify()
    with open(args.out, "wb") as handle:
        value = stream_frame(sys.stdin.buffer, handle, bv)
    value["out"] = str(args.out)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
