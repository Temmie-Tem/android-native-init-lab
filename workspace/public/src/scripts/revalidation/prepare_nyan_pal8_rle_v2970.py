#!/usr/bin/env python3
"""Prepare A90VSTR2 pal8-rle streams for the Nyan Cat video rung.

This is the first compact color stream encoder for native-init playback. It is
deliberately host-side only: source frames and generated streams stay under
workspace/private, while public tests use synthetic frames.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
from pathlib import Path
from typing import BinaryIO

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
DEFAULT_OUT_DIR = REPO_ROOT / "workspace/private/demo-assets/video/v2970-nyan-pal8-rle/build"
MAGIC = b"A90VSTR2"
VERSION = 2
MODE_PAL8_RAW = 1
MODE_PAL8_RLE = 2
PPM_TOKEN_RE = re.compile(rb"(?:#[^\n\r]*(?:\r?\n|$))|(\S+)")
HEADER_STRUCT = struct.Struct("<8sIIIIIIIII32s")
FRAME_RECORD_STRUCT = struct.Struct("<IIIQ")
MAX_PALETTE_COLORS = 256


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def next_ppm_token(data: bytes, position: int) -> tuple[str, int]:
    match = PPM_TOKEN_RE.search(data, position)
    while match and match.group(1) is None:
        match = PPM_TOKEN_RE.search(data, match.end())
    if not match:
        raise ValueError("truncated PPM header")
    return match.group(1).decode("ascii"), match.end()


def read_ppm_p6(path: Path, expected_width: int, expected_height: int) -> bytes:
    data = path.read_bytes()
    token, position = next_ppm_token(data, 0)
    if token != "P6":
        raise ValueError(f"{path}: expected binary PPM P6, got {token!r}")
    width_s, position = next_ppm_token(data, position)
    height_s, position = next_ppm_token(data, position)
    maxval_s, position = next_ppm_token(data, position)
    width = int(width_s)
    height = int(height_s)
    maxval = int(maxval_s)
    if width != expected_width or height != expected_height:
        raise ValueError(f"{path}: geometry {width}x{height}, expected {expected_width}x{expected_height}")
    if maxval <= 0 or maxval > 255:
        raise ValueError(f"{path}: unsupported maxval {maxval}; expected 1..255")
    if position >= len(data) or data[position:position + 1] not in (b" ", b"\t", b"\r", b"\n"):
        raise ValueError(f"{path}: missing PPM raster separator")
    if data[position:position + 2] == b"\r\n":
        position += 2
    else:
        position += 1
    raster = data[position:]
    expected_bytes = expected_width * expected_height * 3
    if len(raster) != expected_bytes:
        raise ValueError(f"{path}: raster bytes {len(raster)}, expected {expected_bytes}")
    if maxval == 255:
        return raster
    return bytes((value * 255) // maxval for value in raster)


def read_raw_rgb24(path: Path, expected_width: int, expected_height: int) -> bytes:
    data = path.read_bytes()
    expected_bytes = expected_width * expected_height * 3
    if len(data) != expected_bytes:
        raise ValueError(f"{path}: raw rgb24 bytes {len(data)}, expected {expected_bytes}")
    return data


def xbgr_from_rgb(red: int, green: int, blue: int) -> int:
    return ((blue & 0xFF) << 16) | ((green & 0xFF) << 8) | (red & 0xFF)


def rgb_from_xbgr(value: int) -> tuple[int, int, int]:
    return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF


def sorted_frame_paths(input_dir: Path, glob_pattern: str, max_frames: int | None = None) -> list[Path]:
    paths = sorted(path for path in input_dir.glob(glob_pattern) if path.is_file())
    if not paths:
        raise ValueError(f"no input frames matched {input_dir}/{glob_pattern}")
    if max_frames is not None:
        paths = paths[:max_frames]
    return paths


def read_frame(path: Path, input_format: str, width: int, height: int) -> bytes:
    if input_format == "ppm":
        return read_ppm_p6(path, width, height)
    if input_format == "raw-rgb24":
        return read_raw_rgb24(path, width, height)
    raise ValueError(f"unsupported input format: {input_format}")


def build_palette(frames_rgb: list[bytes]) -> tuple[list[int], dict[int, int]]:
    palette: list[int] = []
    palette_index: dict[int, int] = {}
    for frame_rgb in frames_rgb:
        if len(frame_rgb) % 3 != 0:
            raise ValueError("rgb frame length must be divisible by 3")
        for offset in range(0, len(frame_rgb), 3):
            color = xbgr_from_rgb(frame_rgb[offset], frame_rgb[offset + 1], frame_rgb[offset + 2])
            if color in palette_index:
                continue
            if len(palette) >= MAX_PALETTE_COLORS:
                raise ValueError("palette exceeds 256 colors; quantize source frames first")
            palette_index[color] = len(palette)
            palette.append(color)
    return palette, palette_index


def frame_to_indices(frame_rgb: bytes, palette_index: dict[int, int]) -> bytes:
    indices = bytearray(len(frame_rgb) // 3)
    target_index = 0
    for offset in range(0, len(frame_rgb), 3):
        color = xbgr_from_rgb(frame_rgb[offset], frame_rgb[offset + 1], frame_rgb[offset + 2])
        indices[target_index] = palette_index[color]
        target_index += 1
    return bytes(indices)


def encode_rle(indices: bytes, width: int, height: int) -> bytes:
    if len(indices) != width * height:
        raise ValueError("indexed frame size does not match geometry")
    payload = bytearray()
    for row_index in range(height):
        row_start = row_index * width
        column_index = 0
        while column_index < width:
            color_index = indices[row_start + column_index]
            run_length = 1
            while (column_index + run_length < width and
                   run_length < 255 and
                   indices[row_start + column_index + run_length] == color_index):
                run_length += 1
            payload.append(run_length)
            payload.append(color_index)
            column_index += run_length
    return bytes(payload)


def choose_frame_payload(indices: bytes, width: int, height: int) -> tuple[int, bytes]:
    rle = encode_rle(indices, width, height)
    if len(rle) < len(indices):
        return MODE_PAL8_RLE, rle
    return MODE_PAL8_RAW, indices


def write_header(handle: BinaryIO,
                 width: int,
                 height: int,
                 fps_num: int,
                 fps_den: int,
                 frame_count: int,
                 palette: list[int],
                 max_payload_bytes: int) -> None:
    handle.write(HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        width,
        height,
        fps_num,
        fps_den,
        frame_count,
        len(palette),
        max_payload_bytes,
        0,
        b"\x00" * 32,
    ))
    for color in palette:
        handle.write(struct.pack("<I", color))


def write_frame_record(handle: BinaryIO,
                       frame_index: int,
                       mode: int,
                       payload: bytes,
                       fps_num: int,
                       fps_den: int) -> None:
    pts_ns = (frame_index * fps_den * 1_000_000_000) // fps_num
    handle.write(FRAME_RECORD_STRUCT.pack(frame_index, mode, len(payload), pts_ns))
    handle.write(payload)


def write_stream_from_frames(
    *,
    input_dir: Path,
    out_dir: Path,
    glob_pattern: str,
    width: int,
    height: int,
    fps_num: int,
    fps_den: int,
    input_format: str,
    max_frames: int | None = None,
    asset_id: str = "v2970-nyan-pal8-rle",
) -> dict[str, object]:
    if not input_dir.is_absolute():
        input_dir = REPO_ROOT / input_dir
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    frame_paths = sorted_frame_paths(input_dir, glob_pattern, max_frames)
    frames_rgb = [read_frame(path, input_format, width, height) for path in frame_paths]
    palette, palette_index = build_palette(frames_rgb)
    encoded_frames: list[tuple[int, bytes]] = []
    raw_pal8_bytes = 0
    encoded_payload_bytes = 0
    mode_counts = {MODE_PAL8_RAW: 0, MODE_PAL8_RLE: 0}
    max_payload_bytes = 0
    for frame_rgb in frames_rgb:
        indices = frame_to_indices(frame_rgb, palette_index)
        mode, payload = choose_frame_payload(indices, width, height)
        encoded_frames.append((mode, payload))
        raw_pal8_bytes += len(indices)
        encoded_payload_bytes += len(payload)
        max_payload_bytes = max(max_payload_bytes, len(payload))
        mode_counts[mode] += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    stream_path = out_dir / "frames.a90vstr2"
    with stream_path.open("wb") as handle:
        write_header(handle, width, height, fps_num, fps_den, len(encoded_frames), palette, max_payload_bytes)
        for frame_index, (mode, payload) in enumerate(encoded_frames):
            write_frame_record(handle, frame_index, mode, payload, fps_num, fps_den)

    digest = sha256(stream_path)
    raw_xbgr_bytes = width * height * 4 * len(encoded_frames)
    compression_ratio_milli = (encoded_payload_bytes * 1000) // raw_pal8_bytes if raw_pal8_bytes else 0
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
            "path": "frames.a90vstr2",
            "format": "pal8-rle",
            "stream_version": VERSION,
            "width": width,
            "height": height,
            "fps_num": fps_num,
            "fps_den": fps_den,
            "frame_count": len(encoded_frames),
            "palette_count": len(palette),
            "max_payload_bytes": max_payload_bytes,
            "raw_xbgr_bytes": raw_xbgr_bytes,
            "raw_pal8_bytes": raw_pal8_bytes,
            "encoded_payload_bytes": encoded_payload_bytes,
            "compression_ratio_milli": compression_ratio_milli,
            "mode_counts": {
                "pal8-raw": mode_counts[MODE_PAL8_RAW],
                "pal8-rle": mode_counts[MODE_PAL8_RLE],
            },
            "sha256": digest,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "SHA256SUMS.txt").write_text(f"{digest}  frames.a90vstr2\n", encoding="utf-8")
    return {
        "manifest": rel(out_dir / "manifest.json"),
        "stream": rel(stream_path),
        "sha256": digest,
        "stream_bytes": stream_path.stat().st_size,
        "frame_count": len(encoded_frames),
        "palette_count": len(palette),
        "raw_xbgr_bytes": raw_xbgr_bytes,
        "raw_pal8_bytes": raw_pal8_bytes,
        "encoded_payload_bytes": encoded_payload_bytes,
        "compression_ratio_milli": compression_ratio_milli,
        "mode_counts": manifest["video"]["mode_counts"],
        "input_format": input_format,
        "first_frame": frame_paths[0].name,
        "last_frame": frame_paths[-1].name,
    }


def decode_rle_payload(payload: bytes, width: int, height: int) -> bytes:
    output = bytearray()
    source = io.BytesIO(payload)
    for row_index in range(height):
        row_pixels = 0
        while row_pixels < width:
            pair = source.read(2)
            if len(pair) != 2:
                raise ValueError(f"truncated RLE row {row_index}")
            run_length = pair[0]
            color_index = pair[1]
            if run_length == 0 or row_pixels + run_length > width:
                raise ValueError(f"invalid RLE run in row {row_index}")
            output.extend(bytes([color_index]) * run_length)
            row_pixels += run_length
    if source.read(1):
        raise ValueError("trailing RLE payload bytes")
    if len(output) != width * height:
        raise ValueError("decoded RLE size mismatch")
    return bytes(output)


def indices_to_rgb(indices: bytes, palette: list[int]) -> bytes:
    output = bytearray()
    for color_index in indices:
        if color_index >= len(palette):
            raise ValueError("palette index out of range")
        red, green, blue = rgb_from_xbgr(palette[color_index])
        output.extend((red, green, blue))
    return bytes(output)


def read_stream_for_test(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    source = io.BytesIO(data)
    header_data = source.read(HEADER_STRUCT.size)
    if len(header_data) != HEADER_STRUCT.size:
        raise ValueError("truncated A90VSTR2 header")
    magic, version, width, height, fps_num, fps_den, frame_count, palette_count, max_payload_bytes, flags, _reserved = (
        HEADER_STRUCT.unpack(header_data)
    )
    if magic != MAGIC or version != VERSION:
        raise ValueError("unsupported stream header")
    if palette_count > MAX_PALETTE_COLORS:
        raise ValueError("palette count exceeds 256")
    palette = [struct.unpack("<I", source.read(4))[0] for _palette_index in range(palette_count)]
    frames: list[bytes] = []
    modes: list[int] = []
    for expected_index in range(frame_count):
        record_data = source.read(FRAME_RECORD_STRUCT.size)
        if len(record_data) != FRAME_RECORD_STRUCT.size:
            raise ValueError("truncated frame record")
        frame_index, mode, payload_bytes, _pts_ns = FRAME_RECORD_STRUCT.unpack(record_data)
        if frame_index != expected_index or payload_bytes > max_payload_bytes:
            raise ValueError("invalid frame record")
        payload = source.read(payload_bytes)
        if len(payload) != payload_bytes:
            raise ValueError("truncated frame payload")
        if mode == MODE_PAL8_RAW:
            if len(payload) != width * height:
                raise ValueError("raw pal8 payload size mismatch")
            indices = payload
        elif mode == MODE_PAL8_RLE:
            indices = decode_rle_payload(payload, width, height)
        else:
            raise ValueError("unsupported frame mode")
        frames.append(indices_to_rgb(indices, palette))
        modes.append(mode)
    if source.read(1):
        raise ValueError("trailing stream bytes")
    return {
        "width": width,
        "height": height,
        "fps_num": fps_num,
        "fps_den": fps_den,
        "frame_count": frame_count,
        "palette": palette,
        "frames_rgb": frames,
        "modes": modes,
        "flags": flags,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--glob", default="*.ppm")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--fps-num", type=int, default=30)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--input-format", choices=("ppm", "raw-rgb24"), default="ppm")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--asset-id", default="v2970-nyan-pal8-rle")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = write_stream_from_frames(
        input_dir=args.input_dir,
        out_dir=args.out_dir,
        glob_pattern=args.glob,
        width=args.width,
        height=args.height,
        fps_num=args.fps_num,
        fps_den=args.fps_den,
        input_format=args.input_format,
        max_frames=args.max_frames,
        asset_id=args.asset_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
