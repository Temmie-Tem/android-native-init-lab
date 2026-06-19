#!/usr/bin/env python3
"""Prepare a private A90VSTR1 synthetic raw-stride video stream.

The output is intentionally written under workspace/private by default. The
stream format matches the V2873 manifest contract and the V2874 native-init
`video stream --manifest ... --video-only` reader.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
DEFAULT_OUT_DIR = REPO_ROOT / "workspace/private/demo-assets/video/v2874-synthetic/build"
MAGIC = b"A90VSTR1"
PIXEL_FORMAT_XBGR8888_RAW_STRIDE = 1
PIXEL_FORMAT_GRAY8 = 2
PIXEL_FORMAT_MONO1 = 3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_for(pattern: str, x: int, y: int, frame: int, width: int, height: int) -> int:
    if pattern == "checker":
        tile = max(width // 12, 32)
        return 0xD8E8FF if ((x // tile) + (y // tile) + frame) % 2 == 0 else 0x101820
    if pattern == "pulse":
        level = (frame * 255) // max(1, 29)
        inverse = 255 - min(level, 255)
        return ((level & 0xFF) << 16) | ((inverse & 0xFF) << 8) | 0x40
    colors = [0xFFFFFF, 0xFFFF00, 0x00FFFF, 0x00FF00, 0xFF00FF, 0xFF0000, 0x0000FF, 0x202020]
    bar_width = max(1, width // len(colors))
    return colors[((x // bar_width) + frame) % len(colors)]


def gray_for(color: int) -> int:
    red = color & 0xFF
    green = (color >> 8) & 0xFF
    blue = (color >> 16) & 0xFF
    return ((red * 77) + (green * 150) + (blue * 29)) >> 8


def write_frame(handle, pattern: str, frame: int, width: int, height: int, stride: int, frame_bytes: int, fps_num: int, fps_den: int, stream_format: str) -> None:
    payload = bytearray(frame_bytes)
    if stream_format == "mono1":
        visible_row_bytes = (width + 7) // 8
        for y in range(height):
            row_base = y * stride
            for x in range(width):
                if gray_for(pixel_for(pattern, x, y, frame, width, height)) >= 128:
                    payload[row_base + (x // 8)] |= 1 << (7 - (x % 8))
            if stride > visible_row_bytes:
                payload[row_base + visible_row_bytes:row_base + stride] = b"\x00" * (stride - visible_row_bytes)
    elif stream_format == "gray8":
        visible_row_bytes = width
        for y in range(height):
            row_base = y * stride
            for x in range(width):
                payload[row_base + x] = gray_for(pixel_for(pattern, x, y, frame, width, height))
            if stride > visible_row_bytes:
                payload[row_base + visible_row_bytes:row_base + stride] = b"\x00" * (stride - visible_row_bytes)
    else:
        visible_row_bytes = width * 4
        for y in range(height):
            row_base = y * stride
            for x in range(width):
                color = pixel_for(pattern, x, y, frame, width, height)
                offset = row_base + x * 4
                payload[offset:offset + 4] = struct.pack("<I", color)
            if stride > visible_row_bytes:
                payload[row_base + visible_row_bytes:row_base + stride] = b"\x00" * (stride - visible_row_bytes)
    pts_ns = (frame * fps_den * 1_000_000_000) // fps_num
    handle.write(struct.pack("<IIQ", frame, frame_bytes, pts_ns))
    handle.write(payload)


def write_stream(out_dir: Path, width: int, height: int, stride: int, fps_num: int, fps_den: int, frames: int, pattern: str, stream_format: str) -> dict[str, object]:
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stream_path = out_dir / "frames.a90vstr"
    if stream_format == "mono1":
        pixel_format = PIXEL_FORMAT_MONO1
        format_name = "mono1"
        visible_row_bytes = (width + 7) // 8
        if stride < visible_row_bytes:
            raise ValueError("stride must be >= ceil(width / 8) for mono1")
    elif stream_format == "gray8":
        pixel_format = PIXEL_FORMAT_GRAY8
        format_name = "gray8"
        visible_row_bytes = width
        if stride < visible_row_bytes:
            raise ValueError("stride must be >= width for gray8")
    else:
        pixel_format = PIXEL_FORMAT_XBGR8888_RAW_STRIDE
        format_name = "xbgr8888-raw-stride"
        visible_row_bytes = width * 4
        if stride < visible_row_bytes:
            raise ValueError("stride must be >= width * 4")
    frame_bytes = stride * height
    with stream_path.open("wb") as handle:
        handle.write(MAGIC)
        handle.write(struct.pack(
            "<IIIIIIIII32s",
            1,
            width,
            height,
            stride,
            pixel_format,
            fps_num,
            fps_den,
            frames,
            frame_bytes,
            b"\x00" * 32,
        ))
        for frame in range(frames):
            write_frame(handle, pattern, frame, width, height, stride, frame_bytes, fps_num, fps_den, stream_format)
    digest = sha256(stream_path)
    manifest = {
        "version": 1,
        "asset_id": f"v2874-synthetic-{stream_format}-{pattern}-{frames}f",
        "video": {
            "path": "frames.a90vstr",
            "format": format_name,
            "width": width,
            "height": height,
            "stride": stride,
            "frame_bytes": frame_bytes,
            "visible_row_bytes": visible_row_bytes,
            "fps_num": fps_num,
            "fps_den": fps_den,
            "frame_count": frames,
            "sha256": digest,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "SHA256SUMS.txt").write_text(f"{digest}  frames.a90vstr\n", encoding="utf-8")
    return {
        "manifest": str((out_dir / "manifest.json").relative_to(REPO_ROOT)),
        "stream": str(stream_path.relative_to(REPO_ROOT)),
        "sha256": digest,
        "frame_bytes": frame_bytes,
        "stream_bytes": stream_path.stat().st_size,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=2400)
    parser.add_argument("--stride", type=int, default=4352)
    parser.add_argument("--fps-num", type=int, default=30)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--pattern", choices=("bars", "checker", "pulse"), default="bars")
    parser.add_argument("--format", choices=("raw", "gray8", "mono1"), default="raw")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = write_stream(
        args.out_dir,
        args.width,
        args.height,
        args.stride,
        args.fps_num,
        args.fps_den,
        args.frames,
        args.pattern,
        args.format,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
