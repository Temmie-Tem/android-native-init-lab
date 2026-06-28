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
from dataclasses import dataclass, field, replace
from pathlib import Path


DEFAULT_TEXT_ADDRESS = 0xFFFFFF8008080000
ANDROID_BOOT_MAGIC = b"ANDROID!"
ANDROID_BOOT_HEADER_SIZE = 0x1000
UNCOMPRESSED_IMG_MAGIC = b"UNCOMPRESSED_IMG"
UNCOMPRESSED_IMG_HEADER_SIZE = 20
MAX_TOKEN_PADDING = 512
MAX_TOKEN_BYTES = 4096

U32_RKP_MAGIC = 0x00BE7BAD
U32_EOR_PROLOGUE = 0xCA1103D0
U32_FORCE_NO_NAP_STORE_FIRST = 0xD10103FF
PRINTK_REQUIRED_BODY_WORDS = {
    0xA9080BE1,  # stp x1, x2, [sp, #128]
    0xA90913E3,  # stp x3, x4, [sp, #144]
    0xA90A1BE5,  # stp x5, x6, [sp, #160]
    0xF9005BE7,  # str x7, [sp, #176]
    0xAD0007E0,  # stp q0, q1, [sp]
    0xAD010FE2,  # stp q2, q3, [sp, #32]
    0xAD0217E4,  # stp q4, q5, [sp, #64]
    0xAD031FE6,  # stp q6, q7, [sp, #96]
    0xD10123A1,  # sub x1, x29, #0x48 (va_list)
}
PRINTK_VA_HELPER_REQUIRED_BODY_WORDS = {
    0x12800001,  # mov w1, #-1
    0x2A1F03E0,  # mov w0, wzr
    0xAA1F03E2,  # mov x2, xzr
    0xAA1F03E3,  # mov x3, xzr
    0xAA1303E4,  # mov x4, x19 (fmt)
    0x9100A3E5,  # add x5, sp, #0x28 (copied va_list)
}


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
    decoded_addresses: list[int] | None = None
    decoded_address_sources: list[str] | None = None
    semantic_overrides: dict[str, int] = field(default_factory=dict)
    semantic_override_sources: dict[str, str] = field(default_factory=dict)


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
    kernel_blob = payload
    kernel_offset = 0
    if payload.startswith(ANDROID_BOOT_MAGIC):
        if len(payload) < ANDROID_BOOT_HEADER_SIZE:
            raise ValueError("Android boot image is too short")
        (
            kernel_size,
            _kernel_addr,
            _ramdisk_size,
            _ramdisk_addr,
            _second_size,
            _second_addr,
            _tags_addr,
            page_size,
            _dt_size,
            _unused,
        ) = struct.unpack_from("<10I", payload, 8)
        if page_size <= 0 or page_size > 0x10000 or page_size & (page_size - 1):
            raise ValueError(f"unexpected Android boot page size: 0x{page_size:x}")
        kernel_offset = page_size
        if kernel_offset + kernel_size > len(payload):
            raise ValueError(
                f"boot image declares kernel size {kernel_size} at 0x{kernel_offset:x}, "
                f"but only {len(payload)} bytes are available"
            )
        kernel_blob = payload[kernel_offset:kernel_offset + kernel_size]

    raw = kernel_blob
    raw_offset = kernel_offset
    if kernel_blob.startswith(UNCOMPRESSED_IMG_MAGIC):
        if len(kernel_blob) < UNCOMPRESSED_IMG_HEADER_SIZE:
            raise ValueError("UNCOMPRESSED_IMG wrapper is too short")
        image_size = struct.unpack_from("<I", kernel_blob, 16)[0]
        raw_offset = kernel_offset + UNCOMPRESSED_IMG_HEADER_SIZE
        raw = kernel_blob[UNCOMPRESSED_IMG_HEADER_SIZE:UNCOMPRESSED_IMG_HEADER_SIZE + image_size]
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


def s32_from_u32(value: int) -> int:
    return value - 0x100000000 if value & 0x80000000 else value


def decode_base_relative_address(raw_offset: int, relative_base: int, text_address: int) -> int:
    """Decode Samsung's 32-bit BASE_RELATIVE entries into Stage-C file vaddrs.

    For the A90 v2321 image the relative base is zero and positive entries are
    raw arm64 Image offsets.  Stage C treats raw Image offset zero as
    KERNEL_TEXT_VADDR, because the 20-byte UNCOMPRESSED_IMG wrapper is outside
    the loaded arm64 Image.  Negative entries are the ABSOLUTE_PERCPU encoding
    used by Linux kallsyms.
    """

    signed = s32_from_u32(raw_offset)
    if signed < 0:
        return relative_base - 1 - signed
    if relative_base == 0:
        return text_address + raw_offset
    return relative_base + raw_offset


def encode_bl_target(site_vaddr: int, word: int) -> int | None:
    if (word & 0xFC000000) != 0x94000000:
        return None
    imm26 = word & 0x03FFFFFF
    if imm26 & 0x02000000:
        imm26 -= 0x04000000
    return site_vaddr + imm26 * 4


def text_vaddr_to_raw_offset(vaddr: int, text_address: int, data_len: int) -> int | None:
    raw_offset = vaddr - text_address
    if 0 <= raw_offset < data_len:
        return raw_offset
    return None


def has_rkp_entry_at(data: bytes, raw_offset: int) -> bool:
    if raw_offset < 4 or raw_offset + 4 > len(data):
        return False
    if u32(data, raw_offset - 4) != U32_RKP_MAGIC:
        return False
    first = u32(data, raw_offset)
    second = u32(data, raw_offset + 4) if raw_offset + 8 <= len(data) else 0
    return first in {U32_EOR_PROLOGUE, U32_FORCE_NO_NAP_STORE_FIRST} or second == U32_EOR_PROLOGUE


def iter_qword_hits(data: bytes, value: int) -> list[int]:
    encoded = struct.pack("<Q", value)
    hits: list[int] = []
    start = 0
    while True:
        offset = data.find(encoded, start)
        if offset < 0:
            return hits
        if offset % 8 == 0:
            hits.append(offset)
        start = offset + 1


def locate_force_no_nap_handlers(data: bytes, text_address: int) -> tuple[int, int]:
    name_offset = data.find(b"force_no_nap\x00")
    if name_offset < 0:
        raise RuntimeError("force_no_nap string not found")
    name_vaddr = text_address + name_offset
    for ref_offset in iter_qword_hits(data, name_vaddr):
        executable_values: list[int] = []
        for cursor in range(ref_offset + 8, min(ref_offset + 0x80, len(data) - 8), 8):
            candidate = u64(data, cursor)
            raw_offset = text_vaddr_to_raw_offset(candidate, text_address, len(data))
            if raw_offset is not None and has_rkp_entry_at(data, raw_offset):
                executable_values.append(candidate)
        if len(executable_values) < 2:
            continue
        show_vaddr, store_vaddr = executable_values[0], executable_values[1]
        show_offset = text_vaddr_to_raw_offset(show_vaddr, text_address, len(data))
        store_offset = text_vaddr_to_raw_offset(store_vaddr, text_address, len(data))
        if show_offset is None or store_offset is None:
            continue
        if u32(data, show_offset) != U32_EOR_PROLOGUE:
            continue
        if u32(data, store_offset) != U32_FORCE_NO_NAP_STORE_FIRST:
            continue
        if u32(data, store_offset + 4) != U32_EOR_PROLOGUE:
            continue
        return show_vaddr, store_vaddr
    raise RuntimeError("force_no_nap show/store pointers not found")


def function_entry_after_magic(data: bytes, magic_offset: int) -> int | None:
    if magic_offset < 0 or magic_offset + 12 > len(data) or u32(data, magic_offset) != U32_RKP_MAGIC:
        return None
    if u32(data, magic_offset + 4) == U32_EOR_PROLOGUE:
        return magic_offset + 4
    if u32(data, magic_offset + 8) == U32_EOR_PROLOGUE:
        return magic_offset + 4
    return None


def find_next_magic(data: bytes, entry_offset: int, max_len: int = 0x400) -> int | None:
    end = min(entry_offset + max_len, len(data) - 4)
    for offset in range(entry_offset + 4, end, 4):
        if u32(data, offset) == U32_RKP_MAGIC:
            return offset
    return None


def function_body_words(data: bytes, entry_offset: int, max_len: int = 0x400) -> set[int]:
    next_magic = find_next_magic(data, entry_offset, max_len)
    if next_magic is None:
        return set()
    return {u32(data, offset) for offset in range(entry_offset, next_magic, 4)}


def direct_bl_targets(data: bytes,
                      entry_offset: int,
                      text_address: int,
                      max_len: int = 0x400) -> list[tuple[int, int]]:
    next_magic = find_next_magic(data, entry_offset, max_len)
    if next_magic is None:
        return []
    targets: list[tuple[int, int]] = []
    for offset in range(entry_offset, next_magic, 4):
        target = encode_bl_target(text_address + offset, u32(data, offset))
        if target is None:
            continue
        target_offset = text_vaddr_to_raw_offset(target, text_address, len(data))
        if target_offset is not None:
            targets.append((offset, target_offset))
    return targets


def iter_word_offsets(data: bytes, word: int) -> list[int]:
    encoded = struct.pack("<I", word)
    hits: list[int] = []
    start = 0
    while True:
        offset = data.find(encoded, start)
        if offset < 0:
            return hits
        if offset % 4 == 0:
            hits.append(offset)
        start = offset + 1


def locate_printk_variadic_wrapper(data: bytes, text_address: int) -> int:
    hits: list[int] = []
    for magic_offset in iter_word_offsets(data, U32_RKP_MAGIC):
        entry_offset = function_entry_after_magic(data, magic_offset)
        if entry_offset is None:
            continue
        if not PRINTK_REQUIRED_BODY_WORDS.issubset(function_body_words(data, entry_offset)):
            continue
        for _call_offset, helper_offset in direct_bl_targets(data, entry_offset, text_address):
            helper_entry = function_entry_after_magic(data, helper_offset - 4)
            if helper_entry != helper_offset:
                continue
            helper_words = function_body_words(data, helper_entry)
            if not PRINTK_VA_HELPER_REQUIRED_BODY_WORDS.issubset(helper_words):
                continue
            hits.append(entry_offset)
    if len(hits) != 1:
        raise RuntimeError(f"expected one plain printk variadic-wrapper hit, found {len(hits)}")
    return text_address + hits[0]


def build_semantic_overrides(data: bytes, text_address: int) -> tuple[dict[str, int], dict[str, str]]:
    overrides: dict[str, int] = {}
    sources: dict[str, str] = {}
    show_vaddr, store_vaddr = locate_force_no_nap_handlers(data, text_address)
    overrides["kgsl_pwrctrl_force_no_nap_show"] = show_vaddr
    overrides["kgsl_pwrctrl_force_no_nap_store"] = store_vaddr
    sources["kgsl_pwrctrl_force_no_nap_show"] = "force_no_nap device-attribute function pointer"
    sources["kgsl_pwrctrl_force_no_nap_store"] = "force_no_nap device-attribute function pointer"
    printk_vaddr = locate_printk_variadic_wrapper(data, text_address)
    overrides["printk"] = printk_vaddr
    sources["printk"] = "plain printk variadic-wrapper signature"
    return overrides, sources


def apply_semantic_overrides(addresses: AddressTable,
                             names: NameTable,
                             overrides: dict[str, int],
                             sources: dict[str, str]) -> AddressTable:
    decoded = decoded_symbol_map(names, addresses)
    mismatches: list[str] = []
    for symbol_name, expected in sorted(overrides.items()):
        actual = decoded.get(symbol_name)
        if actual != expected:
            actual_text = "missing" if actual is None else f"0x{actual:x}"
            mismatches.append(
                f"{symbol_name}: decoded={actual_text} semantic={expected:#x} "
                f"source={sources.get(symbol_name, 'unknown')}"
            )
    if mismatches:
        raise RuntimeError("semantic cross-check failed: " + "; ".join(mismatches))
    return replace(addresses, semantic_overrides=overrides, semantic_override_sources=sources)


def decoded_symbol_map(names: NameTable, addresses: AddressTable) -> dict[str, int]:
    decoded_addresses = addresses.decoded_addresses
    result: dict[str, int] = {}
    for index, (name, low_offset) in enumerate(zip(names.names, addresses.low_offsets)):
        if not name or not name[1:]:
            continue
        absolute = (
            decoded_addresses[index]
            if decoded_addresses is not None
            else addresses.synthetic_base + low_offset
        )
        result[name[1:]] = absolute
    return result


def raw_offset_to_vaddr(raw_offset: int, text_address: int) -> int:
    return text_address + raw_offset


def iter_ropp_entry_offsets(data: bytes) -> list[int]:
    entries: set[int] = set()
    for magic_offset in iter_word_offsets(data, U32_RKP_MAGIC):
        entry_offset = function_entry_after_magic(data, magic_offset)
        if entry_offset is not None:
            entries.add(entry_offset)
    return sorted(entries)


def legacy_stage_c_local_raw_offset(low_offset: int, text_offset: int) -> int:
    """Translate the legacy local-symbol slot into raw Image coordinates.

    The old synthetic-base map was calibrated against `_text`; Stage C uses the
    loaded kernel blob convention, where the 20-byte UNCOMPRESSED_IMG wrapper is
    outside the raw arm64 Image.  This value is only used as a local ROPP-run
    anchor; BASE_RELATIVE globals still decode directly from raw Image offsets.
    """

    return low_offset - text_offset - UNCOMPRESSED_IMG_HEADER_SIZE


def has_word_within(data: bytes, raw_offset: int, word: int, byte_count: int) -> bool:
    if raw_offset < 0:
        return False
    end = min(raw_offset + byte_count, len(data) - 4)
    for offset in range(raw_offset, end + 1, 4):
        if u32(data, offset) == word:
            return True
    return False


def symbol_index(names: NameTable, encoded_name: str) -> int:
    try:
        return names.names.index(encoded_name)
    except ValueError as exc:
        raise RuntimeError(f"required kallsyms name not found: {encoded_name}") from exc


def is_kgsl_pwrctrl_local_run_symbol(name: str) -> bool:
    if not name or name[0] != "t":
        return False
    symbol = name[1:]
    return (
        symbol.startswith("kgsl_pwrctrl_")
        or symbol in {
            "__force_on_store",
            "kgsl_get_bw",
            "kgsl_popp_show",
            "kgsl_popp_store",
        }
    )


def apply_kgsl_ropp_local_run_decode(data: bytes,
                                     names: NameTable,
                                     low_offsets: list[int],
                                     text_offset: int,
                                     text_address: int,
                                     decoded_addresses: list[int],
                                     decoded_sources: list[str]) -> None:
    if "tkgsl_pwrctrl_num_pwrlevels_show" not in names.names:
        return
    anchor_index = symbol_index(names, "tkgsl_pwrctrl_num_pwrlevels_show")
    anchor_raw = legacy_stage_c_local_raw_offset(low_offsets[anchor_index], text_offset)
    ropp_entries = iter_ropp_entry_offsets(data)
    try:
        anchor_entry_pos = ropp_entries.index(anchor_raw)
    except ValueError as exc:
        raise RuntimeError(
            "kgsl_pwrctrl local-run anchor does not land on an RKP/ROPP entry: "
            f"0x{anchor_raw:x}"
        ) from exc
    if not has_word_within(data, anchor_raw, 0x51000503, 0x80):
        raise RuntimeError("kgsl_pwrctrl local-run anchor lacks num_pwrlevels sub w3,w8,#1 marker")

    run_start = anchor_index
    while run_start > 0 and is_kgsl_pwrctrl_local_run_symbol(names.names[run_start - 1]):
        run_start -= 1
    run_end = anchor_index + 1
    while run_end < names.num_syms and is_kgsl_pwrctrl_local_run_symbol(names.names[run_end]):
        run_end += 1

    for index in range(run_start, run_end):
        entry_pos = anchor_entry_pos + (index - anchor_index)
        if entry_pos < 0 or entry_pos >= len(ropp_entries):
            raise RuntimeError(f"kgsl_pwrctrl local-run entry index out of range for {names.names[index]}")
        raw_offset = ropp_entries[entry_pos]
        decoded_addresses[index] = raw_offset_to_vaddr(raw_offset, text_address)
        decoded_sources[index] = "rkp-ropp-local-run"


def apply_printk_signature_decode(data: bytes,
                                  names: NameTable,
                                  text_address: int,
                                  decoded_addresses: list[int],
                                  decoded_sources: list[str]) -> None:
    if "Tprintk" not in names.names:
        return
    printk_index = symbol_index(names, "Tprintk")
    decoded_addresses[printk_index] = locate_printk_variadic_wrapper(data, text_address)
    decoded_sources[printk_index] = "plain-printk-variadic-wrapper-signature"


def apply_structural_decode_corrections(data: bytes,
                                        names: NameTable,
                                        low_offsets: list[int],
                                        text_offset: int,
                                        text_address: int,
                                        decoded_addresses: list[int],
                                        decoded_sources: list[str]) -> None:
    apply_kgsl_ropp_local_run_decode(
        data,
        names,
        low_offsets,
        text_offset,
        text_address,
        decoded_addresses,
        decoded_sources,
    )
    apply_printk_signature_decode(data, names, text_address, decoded_addresses, decoded_sources)


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
        parsed_length = parse_symbol_record_length(data, cursor, end)
        if parsed_length is None:
            if cursor < end and data[cursor] == 0 and allow_zero_padding and all(value == 0 for value in data[cursor:end]):
                return offsets, cursor
            return None
        length, header_len = parsed_length
        if length == 0:
            if allow_zero_padding and all(value == 0 for value in data[cursor:end]):
                return offsets, cursor
            return None
        if length > 0x3FFF:
            return None
        if cursor + header_len + length > end:
            return None
        offsets.append(cursor - start)
        cursor += header_len + length
    if cursor != end:
        return None
    return offsets, cursor


def parse_symbol_record_length(data: bytes, cursor: int, end: int) -> tuple[int, int] | None:
    if cursor >= end:
        return None
    first = data[cursor]
    if first & 0x80 == 0:
        return first, 1
    if cursor + 1 >= end:
        return None
    second = data[cursor + 1]
    if second & 0x80:
        return None
    return (first & 0x7F) | (second << 7), 2


def decode_names(data: bytes, start: int, record_offsets: list[int], tokens: list[bytes]) -> list[str]:
    decoded: list[str] = []
    for offset in record_offsets:
        cursor = start + offset
        parsed_length = parse_symbol_record_length(data, cursor, len(data))
        if parsed_length is None:
            raise RuntimeError(f"bad kallsyms name record length at 0x{cursor:x}")
        length, header_len = parsed_length
        record = data[cursor + header_len:cursor + header_len + length]
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
    decoded_addresses = [
        decode_base_relative_address(raw_offset, relative_base, text_address)
        for raw_offset in low_offsets
    ]
    decoded_sources = ["base-relative"] * len(decoded_addresses)
    apply_structural_decode_corrections(
        data,
        names,
        low_offsets,
        text_offset,
        text_address,
        decoded_addresses,
        decoded_sources,
    )
    return AddressTable(
        offsets_start,
        relative_base_pos,
        relative_base,
        low_offsets,
        text_address,
        text_offset,
        decoded_addresses,
        decoded_sources,
    )


def render_system_map(names: NameTable, addresses: AddressTable) -> str:
    rows: list[tuple[int, int, str]] = []
    decoded_addresses = addresses.decoded_addresses
    for index, (name, low_offset) in enumerate(zip(names.names, addresses.low_offsets)):
        if not name:
            continue
        kind = name[0]
        symbol_name = name[1:]
        if not symbol_name:
            continue
        absolute = (
            decoded_addresses[index]
            if decoded_addresses is not None
            else addresses.synthetic_base + low_offset
        )
        rows.append((absolute, index, f"{absolute:016x} {kind} {symbol_name}"))
    rows.sort(key=lambda row: (row[0], row[1]))
    return "\n".join(row for _absolute, _index, row in rows) + "\n"


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
    overrides, override_sources = build_semantic_overrides(image.raw, args.text_address)
    addresses = apply_semantic_overrides(addresses, names, overrides, override_sources)

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
        "address_decode": "base-relative raw Image offsets rendered as Stage-C file vaddrs",
        "file_text_address": f"0x{args.text_address:x}",
        "synthetic_base": f"0x{addresses.synthetic_base:x}",
        "text_offset": f"0x{addresses.text_offset:x}",
        "decode_sources": {
            source: (addresses.decoded_address_sources or []).count(source)
            for source in sorted(set(addresses.decoded_address_sources or []))
        },
        "semantic_cross_checks": {name: f"0x{value:x}" for name, value in sorted(overrides.items())},
        "semantic_cross_check_sources": override_sources,
        "out_map": str(args.out_map),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
