#!/usr/bin/env python3
"""Prepare A90VSTR1 video streams from host-rendered grayscale frames.

This is the bridge from real host-pre-rendered demo assets (for example Bad
Apple frames rendered by ffmpeg into PGM files) into the device-proven
`video stream` format. It intentionally has no image-library dependency and
does not download or embed copyrighted media.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import BinaryIO

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
DEFAULT_OUT_DIR = REPO_ROOT / "workspace/private/demo-assets/video/v2902-frame-source/build"
MAGIC = b"A90VSTR1"
PIXEL_FORMAT_GRAY8 = 2
PIXEL_FORMAT_MONO1 = 3
PGM_TOKEN_RE = re.compile(rb"(?:#[^\n\r]*(?:\r?\n|$))|(\S+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def next_pgm_token(data: bytes, position: int) -> tuple[str, int]:
    match = PGM_TOKEN_RE.search(data, position)
    while match and match.group(1) is None:
        match = PGM_TOKEN_RE.search(data, match.end())
    if not match:
        raise ValueError("truncated PGM header")
    return match.group(1).decode("ascii"), match.end()


def read_pgm_p5(path: Path, expected_width: int, expected_height: int) -> bytes:
    data = path.read_bytes()
    token, position = next_pgm_token(data, 0)
    if token != "P5":
        raise ValueError(f"{path}: expected binary PGM P5, got {token!r}")
    width_s, position = next_pgm_token(data, position)
    height_s, position = next_pgm_token(data, position)
    maxval_s, position = next_pgm_token(data, position)
    width = int(width_s)
    height = int(height_s)
    maxval = int(maxval_s)
    if width != expected_width or height != expected_height:
        raise ValueError(f"{path}: geometry {width}x{height}, expected {expected_width}x{expected_height}")
    if maxval <= 0 or maxval > 255:
        raise ValueError(f"{path}: unsupported maxval {maxval}; expected 1..255")
    if position >= len(data) or data[position:position + 1] not in (b" ", b"\t", b"\r", b"\n"):
        raise ValueError(f"{path}: missing PGM raster separator")
    if data[position:position + 2] == b"\r\n":
        position += 2
    else:
        position += 1
    raster = data[position:]
    expected_bytes = expected_width * expected_height
    if len(raster) != expected_bytes:
        raise ValueError(f"{path}: raster bytes {len(raster)}, expected {expected_bytes}")
    if maxval == 255:
        return raster
    return bytes((value * 255) // maxval for value in raster)


def read_raw_gray8(path: Path, expected_width: int, expected_height: int) -> bytes:
    data = path.read_bytes()
    expected_bytes = expected_width * expected_height
    if len(data) != expected_bytes:
        raise ValueError(f"{path}: raw gray8 bytes {len(data)}, expected {expected_bytes}")
    return data


def mono1_payload(gray: bytes, width: int, height: int, stride: int, threshold: int) -> bytes:
    visible_row_bytes = (width + 7) // 8
    if stride < visible_row_bytes:
        raise ValueError("stride must be >= ceil(width / 8) for mono1")
    payload = bytearray(stride * height)
    for y in range(height):
        source_base = y * width
        target_base = y * stride
        for x in range(width):
            if gray[source_base + x] >= threshold:
                payload[target_base + (x // 8)] |= 1 << (7 - (x % 8))
    return bytes(payload)


def gray8_payload(gray: bytes, width: int, height: int, stride: int) -> bytes:
    if stride < width:
        raise ValueError("stride must be >= width for gray8")
    if stride == width:
        return gray
    payload = bytearray(stride * height)
    for y in range(height):
        payload[y * stride:y * stride + width] = gray[y * width:y * width + width]
    return bytes(payload)


def sorted_frame_paths(input_dir: Path, glob_pattern: str, max_frames: int | None = None) -> list[Path]:
    paths = sorted(path for path in input_dir.glob(glob_pattern) if path.is_file())
    if not paths:
        raise ValueError(f"no input frames matched {input_dir}/{glob_pattern}")
    if max_frames is not None:
        paths = paths[:max_frames]
    return paths


def write_record(handle: BinaryIO, frame_index: int, payload: bytes, fps_num: int, fps_den: int) -> None:
    pts_ns = (frame_index * fps_den * 1_000_000_000) // fps_num
    handle.write(struct.pack("<IIQ", frame_index, len(payload), pts_ns))
    handle.write(payload)


def write_stream_from_frames(
    *,
    input_dir: Path,
    out_dir: Path,
    glob_pattern: str,
    width: int,
    height: int,
    stride: int,
    fps_num: int,
    fps_den: int,
    input_format: str,
    output_format: str,
    threshold: int,
    max_frames: int | None = None,
    asset_id: str = "v2902-host-rendered-frames",
) -> dict[str, object]:
    if not input_dir.is_absolute():
        input_dir = REPO_ROOT / input_dir
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    frame_paths = sorted_frame_paths(input_dir, glob_pattern, max_frames)
    out_dir.mkdir(parents=True, exist_ok=True)
    stream_path = out_dir / "frames.a90vstr"
    if output_format == "mono1":
        pixel_format = PIXEL_FORMAT_MONO1
        visible_row_bytes = (width + 7) // 8
    elif output_format == "gray8":
        pixel_format = PIXEL_FORMAT_GRAY8
        visible_row_bytes = width
    else:
        raise ValueError(f"unsupported output format: {output_format}")
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
            len(frame_paths),
            frame_bytes,
            b"\x00" * 32,
        ))
        for frame_index, frame_path in enumerate(frame_paths):
            if input_format == "pgm":
                gray = read_pgm_p5(frame_path, width, height)
            else:
                gray = read_raw_gray8(frame_path, width, height)
            if output_format == "mono1":
                payload = mono1_payload(gray, width, height, stride, threshold)
            else:
                payload = gray8_payload(gray, width, height, stride)
            write_record(handle, frame_index, payload, fps_num, fps_den)
    digest = sha256(stream_path)
    manifest = {
        "version": 1,
        "asset_id": asset_id,
        "source": {
            "type": "host-rendered-frame-sequence",
            "input_format": input_format,
            "input_glob": glob_pattern,
            "frame_count": len(frame_paths),
            "first_frame": frame_paths[0].name,
            "last_frame": frame_paths[-1].name,
        },
        "video": {
            "path": "frames.a90vstr",
            "format": output_format,
            "width": width,
            "height": height,
            "stride": stride,
            "frame_bytes": frame_bytes,
            "visible_row_bytes": visible_row_bytes,
            "fps_num": fps_num,
            "fps_den": fps_den,
            "frame_count": len(frame_paths),
            "sha256": digest,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "SHA256SUMS.txt").write_text(f"{digest}  frames.a90vstr\n", encoding="utf-8")
    return {
        "manifest": rel(out_dir / "manifest.json"),
        "stream": rel(stream_path),
        "sha256": digest,
        "frame_bytes": frame_bytes,
        "stream_bytes": stream_path.stat().st_size,
        "frame_count": len(frame_paths),
        "output_format": output_format,
        "input_format": input_format,
        "first_frame": frame_paths[0].name,
        "last_frame": frame_paths[-1].name,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--glob", default="*.pgm")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=2400)
    parser.add_argument("--stride", type=int)
    parser.add_argument("--fps-num", type=int, default=30)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--input-format", choices=("pgm", "raw-gray8"), default="pgm")
    parser.add_argument("--output-format", choices=("mono1", "gray8"), default="mono1")
    parser.add_argument("--threshold", type=int, default=128)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--asset-id", default="v2902-host-rendered-frames")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stride = args.stride
    if stride is None:
        stride = (args.width + 7) // 8 if args.output_format == "mono1" else args.width
    result = write_stream_from_frames(
        input_dir=args.input_dir,
        out_dir=args.out_dir,
        glob_pattern=args.glob,
        width=args.width,
        height=args.height,
        stride=stride,
        fps_num=args.fps_num,
        fps_den=args.fps_den,
        input_format=args.input_format,
        output_format=args.output_format,
        threshold=args.threshold,
        max_frames=args.max_frames,
        asset_id=args.asset_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
