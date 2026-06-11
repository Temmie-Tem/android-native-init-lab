#!/usr/bin/env python3
"""Extract a stock A90 kernel System.map from embedded kallsyms.

The Samsung boot kernel can be stored either as a raw arm64 Image or inside an
UNCOMPRESSED_IMG wrapper.  This tool unwraps that input, locates the in-image
kallsyms token/name/marker/address tables, validates the layout, and emits a
System.map-like file suitable for later runtime slide matching.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TEXT_ADDRESS = 0xFFFFFF8008080000
MAX_TOKEN_PADDING = 512
MAX_TOKEN_BYTES = 4096


@dataclass(frozen=True)
class KernelImage:
    source_path: Path
    wrapper_sha256: str
    raw_sha256: str
    raw: bytes
    raw_offset: int
    wrapper_size: int


@dataclass(frozen=True)
class TokenTable:
    table_start: int
    table_end: int
    index_start: int
    token_index: list[int]
    tokens: list[bytes]


@dataclass(frozen=True)
class NameTable:
    names_start: int
    names_end: int
    marker_start: int
    marker_count: int
    num_syms_pos: int
    num_syms: int
    names: list[str]
    record_offsets: list[int]


@dataclass(frozen=True)
class AddressTable:
    offsets_start: int
    relative_base_pos: int
    relative_base: int
    low_offsets: list[int]
    synthetic_base: int
    text_offset: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def unwrap_kernel(path: Path) -> KernelImage:
    payload = path.read_bytes()
    raw = payload
    raw_offset = 0
    if payload.startswith(b"UNCOMPRESSED_IMG"):
        if len(payload) < 20:
            raise ValueError("UNCOMPRESSED_IMG wrapper is too short")
        image_size = struct.unpack_from("<I", payload, 16)[0]
        raw_offset = 20
        raw = payload[raw_offset:raw_offset + image_size]
        if len(raw) != image_size:
            raise ValueError(f"wrapper declares {image_size} bytes but only {len(raw)} are available")
    else:
        image_size = len(raw)
    return KernelImage(
        source_path=path,
        wrapper_sha256=sha256_bytes(payload),
        raw_sha256=sha256_bytes(raw),
        raw=raw,
        raw_offset=raw_offset,
        wrapper_size=len(payload),
    )


def printable_token(segment: bytes) -> bool:
    return all(0x09 <= value <= 0x7E for value in segment)


def parse_token_run(data: bytes, start: int) -> tuple[int, list[int], list[bytes]] | None:
    cursor = start
    cumulative: list[int] = []
    tokens: list[bytes] = []
    for _ in range(256):
        cumulative.append(cursor - start)
        end = data.find(b"\x00", cursor, min(cursor + 64, len(data)))
        if end < 0:
            return None
        token = data[cursor:end]
        if len(token) > 48 or not printable_token(token):
            return None
        tokens.append(token)
        cursor = end + 1
    nonempty = sum(1 for token in tokens if token)
    if nonempty < 128 or cumulative[-1] < 128 or cursor - start > MAX_TOKEN_BYTES:
        return None
    return cursor, cumulative, tokens


def token_table_at(data: bytes, start: int) -> TokenTable | None:
    parsed = parse_token_run(data, start)
    if parsed is None:
        return None
    table_end, cumulative, tokens = parsed
    for padding in range(MAX_TOKEN_PADDING + 1):
        index_start = table_end + padding
        if index_start + 512 > len(data):
            break
        values = [u16(data, index_start + 2 * index) for index in range(256)]
        if values == cumulative:
            return TokenTable(start, table_end, index_start, values, tokens)
    return None


def find_token_table(data: bytes, hints: list[int]) -> TokenTable:
    for hint in hints:
        if hint < 0 or hint >= len(data):
            continue
        table = token_table_at(data, hint)
        if table is not None:
            return table
    start = len(data) // 3
    while start < len(data) - 2048:
        table = token_table_at(data, start)
        if table is not None:
            return table
        start += 1
    raise RuntimeError("kallsyms token table not found")


def marker_candidate(data: bytes, start: int, token_table_start: int) -> list[int] | None:
    count = (token_table_start - start) // 8
    if count < 32:
        return None
    values = [u64(data, start + 8 * index) for index in range(count)]
    if values[0] != 0:
        return None
    if len(values) < 2 or not (512 <= values[1] <= 10000):
        return None
    if not all(values[index] < values[index + 1] for index in range(len(values) - 1)):
        return None
    if values[-1] < 1024 * 1024:
        return None
    return values


def find_marker_table(data: bytes, token_table_start: int, hints: list[int]) -> tuple[int, list[int]]:
    for hint in hints:
        if hint < 0 or hint >= token_table_start:
            continue
        values = marker_candidate(data, hint, token_table_start)
        if values is not None:
            return hint, values
    best: tuple[int, list[int]] | None = None
    search_start = max(0, token_table_start - 0x40000)
    for start in range(search_start & ~7, token_table_start - 16, 8):
        values = marker_candidate(data, start, token_table_start)
        if values is None:
            continue
        best = (start, values)
    if best is None:
        raise RuntimeError("kallsyms marker table not found")
    return best


def parse_record_offsets(data: bytes,
                         start: int,
                         end: int,
                         *,
                         allow_zero_padding: bool = False) -> tuple[list[int], int] | None:
    cursor = start
    offsets: list[int] = []
    while cursor < end:
        length = data[cursor]
        if length == 0:
            if allow_zero_padding and all(value == 0 for value in data[cursor:end]):
                return offsets, cursor
            return None
        if length > 128:
            return None
        if cursor + 1 + length > end:
            return None
        offsets.append(cursor - start)
        cursor += 1 + length
    if cursor != end:
        return None
    return offsets, cursor


def decode_names(data: bytes, start: int, record_offsets: list[int], tokens: list[bytes]) -> list[str]:
    decoded: list[str] = []
    for offset in record_offsets:
        cursor = start + offset
        length = data[cursor]
        record = data[cursor + 1:cursor + 1 + length]
        symbol = b"".join(tokens[value] for value in record)
        decoded.append(symbol.decode("latin1"))
    return decoded


def validate_names_candidate(data: bytes,
                             token_table: TokenTable,
                             marker_start: int,
                             markers: list[int],
                             start: int,
                             min_count: int,
                             max_count: int) -> NameTable | None:
    first = parse_record_offsets(data, start, start + markers[1])
    if first is None or len(first[0]) != 256:
        return None
    parsed = parse_record_offsets(data, start, marker_start, allow_zero_padding=True)
    if parsed is None:
        return None
    record_offsets, names_end = parsed
    count = len(record_offsets)
    if not (min_count <= count <= max_count):
        return None
    if any(record_offsets[index * 256] != markers[index] for index in range(len(markers))):
        return None
    names = decode_names(data, start, record_offsets, token_table.tokens)
    required = {
        "T_text",
        "T_stext",
        "ttrace_event_raw_event_sched_switch",
        "tperf_trace_sched_switch",
        "Ttrace_call_bpf",
        "Tbpf_get_stackid",
        "t__schedule",
        "tmdm_subsys_powerup",
    }
    if not required.issubset(set(names)):
        return None
    num_pos = find_num_syms_position(data, start, count)
    return NameTable(
        names_start=start,
        names_end=names_end,
        marker_start=marker_start,
        marker_count=len(markers),
        num_syms_pos=num_pos,
        num_syms=count,
        names=names,
        record_offsets=record_offsets,
    )


def find_names(data: bytes,
               token_table: TokenTable,
               marker_start: int,
               markers: list[int],
               hints: list[int]) -> NameTable:
    min_count = (len(markers) - 1) * 256 + 1
    max_count = len(markers) * 256
    for hint in hints:
        if hint < 0 or hint >= marker_start:
            continue
        candidate = validate_names_candidate(data, token_table, marker_start, markers, hint, min_count, max_count)
        if candidate is not None:
            return candidate
    last_marker = markers[-1]
    low = max(0, marker_start - last_marker - 0x40000)
    high = min(marker_start, marker_start - last_marker + 0x40000)

    for start in range((low + 7) & ~7, high, 8):
        candidate = validate_names_candidate(data, token_table, marker_start, markers, start, min_count, max_count)
        if candidate is not None:
            return candidate
    raise RuntimeError("kallsyms names table not found")


def find_num_syms_position(data: bytes, names_start: int, count: int) -> int:
    encoded = struct.pack("<Q", count)
    window_start = max(0, names_start - 0x400)
    position = data.rfind(encoded, window_start, names_start)
    if position < 0:
        raise RuntimeError(f"kallsyms_num_syms={count} not found before names")
    return position


def find_address_table(data: bytes, names: NameTable, text_address: int) -> AddressTable:
    relative_base_pos = names.num_syms_pos - 8
    relative_base = u64(data, relative_base_pos) if relative_base_pos >= 0 else 0
    offsets_start = relative_base_pos - 4 * names.num_syms
    if offsets_start < 0:
        raise RuntimeError("kallsyms_offsets would start before image")
    low_offsets = [u32(data, offsets_start + 4 * index) for index in range(names.num_syms)]
    if sum(low_offsets[index] >= low_offsets[index - 1] for index in range(1, min(4096, len(low_offsets)))) < 4000:
        raise RuntimeError("kallsyms_offsets are not monotonically increasing")
    text_index = names.names.index("T_text")
    text_offset = low_offsets[text_index]
    synthetic_base = text_address - text_offset
    return AddressTable(offsets_start, relative_base_pos, relative_base, low_offsets, synthetic_base, text_offset)


def render_system_map(names: NameTable, addresses: AddressTable) -> str:
    rows: list[str] = []
    for name, low_offset in zip(names.names, addresses.low_offsets):
        if not name:
            continue
        kind = name[0]
        symbol_name = name[1:]
        if not symbol_name:
            continue
        absolute = addresses.synthetic_base + low_offset
        rows.append(f"{absolute:016x} {kind} {symbol_name}")
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--out-map", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--text-address", type=lambda value: int(value, 0), default=DEFAULT_TEXT_ADDRESS)
    parser.add_argument(
        "--token-table-hint",
        type=lambda value: int(value, 0),
        action="append",
        default=[0x2103100],
        help="raw Image file offset to try before full token-table scan; can be repeated",
    )
    parser.add_argument(
        "--marker-start-hint",
        type=lambda value: int(value, 0),
        action="append",
        default=[0x2101F00],
        help="raw Image file offset to try before marker-table scan; can be repeated",
    )
    parser.add_argument(
        "--names-start-hint",
        type=lambda value: int(value, 0),
        action="append",
        default=[0x1F10700],
        help="raw Image file offset to try before names-table scan; can be repeated",
    )
    args = parser.parse_args()

    image = unwrap_kernel(args.kernel)
    token_table = find_token_table(image.raw, args.token_table_hint)
    marker_start, markers = find_marker_table(image.raw, token_table.table_start, args.marker_start_hint)
    names = find_names(image.raw, token_table, marker_start, markers, args.names_start_hint)
    addresses = find_address_table(image.raw, names, args.text_address)

    args.out_map.parent.mkdir(parents=True, exist_ok=True)
    args.out_map.write_text(render_system_map(names, addresses))
    summary = {
        "decision": "stock-kallsyms-extract-pass",
        "source_path": str(image.source_path),
        "wrapper_sha256": image.wrapper_sha256,
        "wrapper_size": image.wrapper_size,
        "raw_sha256": image.raw_sha256,
        "raw_offset": image.raw_offset,
        "raw_size": len(image.raw),
        "token_table_start": f"0x{token_table.table_start:x}",
        "token_table_end": f"0x{token_table.table_end:x}",
        "token_index_start": f"0x{token_table.index_start:x}",
        "marker_start": f"0x{names.marker_start:x}",
        "marker_count": names.marker_count,
        "names_start": f"0x{names.names_start:x}",
        "names_end": f"0x{names.names_end:x}",
        "num_syms_pos": f"0x{names.num_syms_pos:x}",
        "num_syms": names.num_syms,
        "offsets_start": f"0x{addresses.offsets_start:x}",
        "relative_base_pos": f"0x{addresses.relative_base_pos:x}",
        "relative_base_raw": f"0x{addresses.relative_base:x}",
        "synthetic_text_address": f"0x{args.text_address:x}",
        "synthetic_base": f"0x{addresses.synthetic_base:x}",
        "text_offset": f"0x{addresses.text_offset:x}",
        "out_map": str(args.out_map),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
