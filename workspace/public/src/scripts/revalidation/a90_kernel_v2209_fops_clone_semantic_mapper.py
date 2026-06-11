#!/usr/bin/env python3
"""Build a semantic map for stock fops clone/landing RELA addends.

V2208 proved that V2206 live /dev/null and /dev/zero fops pointers are explained
by stock RELA addends under the 0x80000 runtime slide.  This host-only follow-up
derives the semantic names for those clone/landing addends from source
initializers, slot-accurate stock RELA entries, and rebuilt-ELF label checks.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_KERNEL_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_STOCK_DIR = PRIVATE_KERNEL_RUNS / "v2197-stock-kallsyms"
DEFAULT_SYSTEM_MAP = DEFAULT_STOCK_DIR / "System.map"
DEFAULT_KERNEL_RAW = DEFAULT_STOCK_DIR / "kernel.raw"
DEFAULT_STOCK_META = DEFAULT_STOCK_DIR / "stock-kallsyms.json"
DEFAULT_V2206_SUMMARY = PRIVATE_KERNEL_RUNS / "v2206-fops-member-anchor-20260612-015121/summary.json"
DEFAULT_V2208_RESULT = PRIVATE_KERNEL_RUNS / "v2208-rela-fops-discriminator/result.json"
DEFAULT_REBUILT_VMLINUX = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/vmlinux"
DEFAULT_REBUILT_SYSTEM_MAP = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/System.map"
DEFAULT_SOURCE_MEM_C = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/mem.c"
DEFAULT_SOURCE_FS_H = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/include/linux/fs.h"
DEFAULT_AUTOCONF = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/include/generated/autoconf.h"
DEFAULT_OUT_DIR = PRIVATE_KERNEL_RUNS / "v2209-fops-clone-semantic-mapper"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2209_FOPS_CLONE_SEMANTIC_MAPPER_2026-06-12.md"

KERNEL_VA_MIN = 0xFFFFFF8000000000
KERNEL_VA_MAX = 0xFFFFFF80FFFFFFFF
RELA_INFO_RELATIVE = 0x403
JOPP_MAGIC = 0x00BE7BAD
ROPP_EOR_X16_X30_X17 = 0xCA1103D0
U64_MASK = (1 << 64) - 1
FOPS_OBJECTS = {"null_fops": "fd0_fop", "zero_fops": "fd1_fop"}
FOPS_FIELD_TO_V2206 = {
    ("null_fops", "llseek"): "fd0_llseek",
    ("null_fops", "read"): "fd0_read",
    ("null_fops", "write"): "fd0_write",
    ("null_fops", "read_iter"): "fd0_read_iter",
    ("null_fops", "write_iter"): "fd0_write_iter",
    ("null_fops", "splice_write"): "fd0_splice_write",
    ("zero_fops", "llseek"): "fd1_llseek",
    ("zero_fops", "write"): "fd1_write",
    ("zero_fops", "read_iter"): "fd1_read_iter",
    ("zero_fops", "write_iter"): "fd1_write_iter",
    ("zero_fops", "mmap"): "fd1_mmap",
    ("zero_fops", "get_unmapped_area"): "fd1_get_unmapped_area",
}


@dataclass(frozen=True)
class Symbol:
    address: int
    kind: str
    name: str


@dataclass(frozen=True)
class RelaEntry:
    location: int
    r_offset: int
    r_info: int
    r_addend: int


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return int(text, 16) if text.lower().startswith("0x") else int(text, 10)


def hex64(value: int) -> str:
    return f"0x{value & U64_MASK:016x}"


def hex_signed(value: int) -> str:
    if value < 0:
        return f"-0x{-value:x}"
    return f"0x{value:x}"


def parse_system_map(path: Path) -> list[Symbol]:
    symbols: list[Symbol] = []
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            address = int(parts[0], 16)
        except ValueError:
            continue
        symbols.append(Symbol(address, parts[1], parts[2]))
    symbols.sort(key=lambda item: item.address)
    return symbols


def build_symbol_index(symbols: list[Symbol]) -> dict[str, int]:
    index: dict[str, int] = {}
    for symbol in symbols:
        index.setdefault(symbol.name, symbol.address)
    return index


def nearest_symbol(symbols: list[Symbol], addresses: list[int], address: int) -> dict[str, Any] | None:
    index = bisect.bisect_right(addresses, address) - 1
    if index < 0:
        return None
    symbol = symbols[index]
    return {
        "symbol": symbol.name,
        "kind": symbol.kind,
        "symbol_address": hex64(symbol.address),
        "offset": address - symbol.address,
        "offset_hex": hex_signed(address - symbol.address),
    }


def load_kernel_raw(path: Path) -> bytes:
    payload = path.read_bytes()
    if payload.startswith(b"UNCOMPRESSED_IMG"):
        if len(payload) < 20:
            raise ValueError("UNCOMPRESSED_IMG wrapper is too short")
        image_size = struct.unpack_from("<I", payload, 16)[0]
        raw = payload[20:20 + image_size]
        if len(raw) != image_size:
            raise ValueError(f"wrapper declares {image_size} bytes but only {len(raw)} are available")
        return raw
    return payload


def load_synthetic_base(path: Path) -> int:
    metadata = json.loads(path.read_text())
    return parse_int(metadata["synthetic_base"])


def looks_like_kernel_va(value: int) -> bool:
    return KERNEL_VA_MIN <= value <= KERNEL_VA_MAX


def is_stock_rela_record(raw: bytes, offset: int) -> bool:
    if offset < 0 or offset + 24 > len(raw):
        return False
    r_offset, r_info, r_addend = struct.unpack_from("<QQQ", raw, offset)
    if r_info != RELA_INFO_RELATIVE:
        return False
    if not looks_like_kernel_va(r_offset):
        return False
    return r_addend == 0 or looks_like_kernel_va(r_addend)


def discover_stock_rela(raw: bytes, synthetic_base: int) -> dict[str, Any]:
    best_start: int | None = None
    best_count = 0
    for residue in range(0, 24, 4):
        current_start: int | None = None
        current_count = 0
        for offset in range(residue, len(raw) - 23, 24):
            if is_stock_rela_record(raw, offset):
                if current_start is None:
                    current_start = offset
                current_count += 1
            else:
                if current_count > best_count:
                    best_start = current_start
                    best_count = current_count
                current_start = None
                current_count = 0
        if current_count > best_count:
            best_start = current_start
            best_count = current_count
    if best_start is None or best_count == 0:
        raise RuntimeError("stock RELA run was not found")
    entries: list[RelaEntry] = []
    for offset in range(best_start, best_start + best_count * 24, 24):
        r_offset, r_info, r_addend = struct.unpack_from("<QQQ", raw, offset)
        entries.append(RelaEntry(synthetic_base + offset, r_offset, r_info, r_addend))
    return {
        "start_offset": best_start,
        "start_vma": synthetic_base + best_start,
        "end_vma": synthetic_base + best_start + (best_count - 1) * 24,
        "count": best_count,
        "entries": entries,
    }


def parse_config_symbols(path: Path) -> set[str]:
    symbols: set[str] = set()
    for match in re.finditer(r"^#define\s+(CONFIG_[A-Za-z0-9_]+)\b", path.read_text(errors="replace"), re.M):
        symbols.add(match.group(1))
    return symbols


def strip_inactive_config_blocks(text: str, config_symbols: set[str]) -> str:
    output: list[str] = []
    active_stack: list[tuple[bool, bool]] = []
    active = True
    for line in text.splitlines():
        ifdef_match = re.match(r"\s*#ifdef\s+(CONFIG_[A-Za-z0-9_]+)", line)
        ifndef_match = re.match(r"\s*#ifndef\s+(CONFIG_[A-Za-z0-9_]+)", line)
        else_match = re.match(r"\s*#else\b", line)
        endif_match = re.match(r"\s*#endif\b", line)
        if ifdef_match:
            active_stack.append((active, ifdef_match.group(1) in config_symbols))
            active = active and active_stack[-1][1]
            continue
        if ifndef_match:
            active_stack.append((active, ifndef_match.group(1) not in config_symbols))
            active = active and active_stack[-1][1]
            continue
        if else_match:
            if not active_stack:
                continue
            parent_active, branch_active = active_stack[-1]
            active_stack[-1] = (parent_active, not branch_active)
            active = parent_active and not branch_active
            continue
        if endif_match:
            if active_stack:
                parent_active, _branch_active = active_stack.pop()
                active = parent_active
            continue
        if active:
            output.append(line)
    return "\n".join(output) + "\n"


def parse_file_operations_offsets(path: Path, config_symbols: set[str]) -> dict[str, int]:
    text = strip_inactive_config_blocks(path.read_text(errors="replace"), config_symbols)
    match = re.search(r"struct\s+file_operations\s*\{(?P<body>.*?)^\}\s*[^;]*;", text, re.S | re.M)
    if not match:
        raise RuntimeError("struct file_operations body not found")
    offsets: dict[str, int] = {}
    pointer_index = 0
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        simple_pointer = re.match(r".*\*\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;", line)
        callback_pointer = re.match(r".*\(\s*\*\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\)", line)
        name = None
        if callback_pointer:
            name = callback_pointer.group("name")
        elif simple_pointer:
            name = simple_pointer.group("name")
        if name:
            offsets[name] = pointer_index * 8
            pointer_index += 1
    return offsets


def parse_macros(text: str) -> dict[str, str]:
    macros: dict[str, str] = {}
    for match in re.finditer(r"^#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", text, re.M):
        macros[match.group(1)] = match.group(2)
    return macros


def resolve_alias(name: str, macros: dict[str, str]) -> str:
    seen: set[str] = set()
    current = name
    while current in macros and current not in seen:
        seen.add(current)
        current = macros[current]
    return current


def parse_fops_initializers(path: Path, names: set[str], config_symbols: set[str]) -> dict[str, dict[str, dict[str, Any]]]:
    text = strip_inactive_config_blocks(path.read_text(errors="replace"), config_symbols)
    macros = parse_macros(text)
    initializers: dict[str, dict[str, dict[str, Any]]] = {}
    for name in names:
        pattern = rf"static\s+const\s+struct\s+file_operations(?:\s+__maybe_unused)?\s+{re.escape(name)}\s*=\s*\{{(?P<body>.*?)^\}};"
        match = re.search(pattern, text, re.S | re.M)
        if not match:
            raise RuntimeError(f"{name} initializer not found")
        rows: dict[str, dict[str, Any]] = {}
        body_start = match.start("body")
        for field_match in re.finditer(r"\.(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<target>[A-Za-z_][A-Za-z0-9_]*)\s*,", match.group("body")):
            source_target = field_match.group("target")
            target = resolve_alias(source_target, macros)
            rows[field_match.group("field")] = {
                "source_target": source_target,
                "resolved_target": target,
                "line": text[:body_start + field_match.start()].count("\n") + 1,
            }
        initializers[name] = rows
    return initializers


def parse_elf_rela_dyn(vmlinux: Path) -> list[RelaEntry]:
    section = subprocess.run(
        ["aarch64-linux-gnu-readelf", "-SW", str(vmlinux)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    match = re.search(
        r"\]\s+\.rela\.dyn\s+RELA\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)",
        section,
    )
    if not match:
        raise RuntimeError(".rela.dyn section not found in rebuilt ELF")
    section_addr = int(match.group(1), 16)
    section_offset = int(match.group(2), 16)
    section_size = int(match.group(3), 16)
    entry_size = int(match.group(4), 16)
    if entry_size != 24:
        raise RuntimeError(f"unexpected .rela.dyn entry size: {entry_size}")
    payload = vmlinux.read_bytes()
    entries: list[RelaEntry] = []
    for index in range(section_size // entry_size):
        offset = section_offset + index * entry_size
        r_offset, r_info, signed_addend = struct.unpack_from("<QQq", payload, offset)
        entries.append(RelaEntry(section_addr + index * entry_size, r_offset, r_info, signed_addend & U64_MASK))
    return entries


def read_u32(raw: bytes, synthetic_base: int, address: int) -> int | None:
    offset = address - synthetic_base
    if offset < 0 or offset + 4 > len(raw):
        return None
    return struct.unpack_from("<I", raw, offset)[0]


def landing_profile(raw: bytes, synthetic_base: int, address: int) -> dict[str, Any]:
    magic_offsets: list[int] = []
    ropp_offsets: list[int] = []
    for delta in range(-0x40, 0x41, 4):
        value = read_u32(raw, synthetic_base, address + delta)
        if value == JOPP_MAGIC:
            magic_offsets.append(delta)
        if value == ROPP_EOR_X16_X30_X17:
            ropp_offsets.append(delta)
    return {
        "jopp_magic_relative_offsets": magic_offsets,
        "ropp_eor_relative_offsets": ropp_offsets,
    }


def live_value(summary: dict[str, Any], field: str) -> int | None:
    value = summary["probe"]["summary"].get(field)
    if value in (None, 0, "0", "0x0"):
        return None
    return parse_int(value)


def object_bases_from_v2208(v2208: dict[str, Any]) -> dict[str, int]:
    bases: dict[str, int] = {}
    for row in v2208["object_rows"]:
        expected = row["expected_symbol"]
        if expected in FOPS_OBJECTS:
            bases[expected] = parse_int(row["static_addend"])
    missing = sorted(set(FOPS_OBJECTS) - set(bases))
    if missing:
        raise RuntimeError(f"missing clone object bases from V2208: {', '.join(missing)}")
    return bases


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    stock_symbols = parse_system_map(args.system_map)
    stock_addresses = [symbol.address for symbol in stock_symbols]
    stock_index = build_symbol_index(stock_symbols)
    rebuilt_symbols = parse_system_map(args.rebuilt_system_map)
    rebuilt_index = build_symbol_index(rebuilt_symbols)
    raw = load_kernel_raw(args.kernel_raw)
    synthetic_base = load_synthetic_base(args.stock_meta)
    v2206 = json.loads(args.v2206_summary.read_text())
    v2208 = json.loads(args.v2208_result.read_text())
    slide = parse_int(v2208["slide"]["best"])
    config_symbols = parse_config_symbols(args.autoconf)
    rela_run = discover_stock_rela(raw, synthetic_base)
    stock_by_offset = {entry.r_offset: entry for entry in rela_run["entries"] if entry.r_info == RELA_INFO_RELATIVE}
    rebuilt_entries = parse_elf_rela_dyn(args.rebuilt_vmlinux)
    rebuilt_by_offset = {entry.r_offset: entry for entry in rebuilt_entries if entry.r_info == RELA_INFO_RELATIVE}
    fops_offsets = parse_file_operations_offsets(args.source_fs_h, config_symbols)
    initializers = parse_fops_initializers(args.source_mem_c, set(FOPS_OBJECTS), config_symbols)
    clone_bases = object_bases_from_v2208(v2208)

    rows: list[dict[str, Any]] = []
    runtime_semantic_map: dict[str, list[dict[str, Any]]] = {}
    addend_semantic_map: dict[str, list[dict[str, Any]]] = {}
    for object_name, fields in sorted(initializers.items()):
        clone_base = clone_bases[object_name]
        rebuilt_base = rebuilt_index.get(object_name)
        original_base = stock_index.get(object_name)
        for field, source in sorted(fields.items(), key=lambda item: fops_offsets[item[0]]):
            if field not in fops_offsets:
                raise RuntimeError(f"missing file_operations offset for {field}")
            offset = fops_offsets[field]
            slot = clone_base + offset
            stock_entry = stock_by_offset.get(slot)
            stock_addend = None if stock_entry is None else stock_entry.r_addend
            expected_symbol = source["resolved_target"]
            stock_expected = stock_index.get(expected_symbol)
            rebuilt_expected = rebuilt_index.get(expected_symbol)
            rebuilt_entry = None if rebuilt_base is None else rebuilt_by_offset.get(rebuilt_base + offset)
            v2206_field = FOPS_FIELD_TO_V2206.get((object_name, field))
            observed_runtime = None if v2206_field is None else live_value(v2206, v2206_field)
            predicted_runtime = None if stock_addend is None else stock_addend + slide
            runtime_key = None if predicted_runtime is None else hex64(predicted_runtime)
            addend_key = None if stock_addend is None else hex64(stock_addend)
            semantic = {
                "object": object_name,
                "field": field,
                "source_target": source["source_target"],
                "semantic_target": expected_symbol,
            }
            if runtime_key is not None:
                runtime_semantic_map.setdefault(runtime_key, []).append(semantic)
            if addend_key is not None:
                addend_semantic_map.setdefault(addend_key, []).append(semantic)
            rows.append({
                "object": object_name,
                "field": field,
                "field_offset": offset,
                "field_offset_hex": hex(offset),
                "source_line": source["line"],
                "source_target": source["source_target"],
                "semantic_target": expected_symbol,
                "clone_base": hex64(clone_base),
                "clone_slot": hex64(slot),
                "stock_rela_location": None if stock_entry is None else hex64(stock_entry.location),
                "stock_addend": None if stock_addend is None else hex64(stock_addend),
                "runtime_pointer": None if predicted_runtime is None else hex64(predicted_runtime),
                "observed_v2206_field": v2206_field,
                "observed_v2206_runtime": None if observed_runtime is None else hex64(observed_runtime),
                "observed_matches_predicted": observed_runtime is None or observed_runtime == predicted_runtime,
                "stock_expected_label": None if stock_expected is None else hex64(stock_expected),
                "delta_from_stock_label": None if stock_addend is None or stock_expected is None else stock_addend - stock_expected,
                "delta_from_stock_label_hex": None if stock_addend is None or stock_expected is None else hex_signed(stock_addend - stock_expected),
                "nearest_stock_symbol": None if stock_addend is None else nearest_symbol(stock_symbols, stock_addresses, stock_addend),
                "rebuilt_slot": None if rebuilt_base is None else hex64(rebuilt_base + offset),
                "rebuilt_rela_addend": None if rebuilt_entry is None else hex64(rebuilt_entry.r_addend),
                "rebuilt_expected_label": None if rebuilt_expected is None else hex64(rebuilt_expected),
                "rebuilt_matches_expected_label": bool(rebuilt_entry and rebuilt_expected is not None and rebuilt_entry.r_addend == rebuilt_expected),
                "landing_profile": None if stock_addend is None else landing_profile(raw, synthetic_base, stock_addend),
                "object_label_delta": None if original_base is None else clone_base - original_base,
                "object_label_delta_hex": None if original_base is None else hex_signed(clone_base - original_base),
            })

    stock_slot_ok = all(row["stock_rela_location"] for row in rows)
    rebuilt_label_ok = all(row["rebuilt_matches_expected_label"] for row in rows)
    live_ok = all(row["observed_matches_predicted"] for row in rows)
    decision = (
        "v2209-fops-clone-semantic-map-built"
        if stock_slot_ok and rebuilt_label_ok and live_ok
        else "v2209-fops-clone-semantic-map-needs-review"
    )
    reason = (
        "Source fops initializer fields, slot-accurate stock RELA entries, rebuilt label checks, and V2206 live values all agree."
        if decision == "v2209-fops-clone-semantic-map-built"
        else "At least one source/stock/rebuilt/live consistency check failed; review row details."
    )

    return {
        "decision": decision,
        "reason": reason,
        "inputs": {
            "system_map": rel(args.system_map),
            "kernel_raw": rel(args.kernel_raw),
            "stock_meta": rel(args.stock_meta),
            "v2206_summary": rel(args.v2206_summary),
            "v2208_result": rel(args.v2208_result),
            "rebuilt_vmlinux": rel(args.rebuilt_vmlinux),
            "rebuilt_system_map": rel(args.rebuilt_system_map),
            "source_mem_c": rel(args.source_mem_c),
            "source_fs_h": rel(args.source_fs_h),
            "autoconf": rel(args.autoconf),
        },
        "kernel": {
            "synthetic_base": hex64(synthetic_base),
            "raw_size": len(raw),
            "stock_symbol_count": len(stock_symbols),
        },
        "rela_run": {
            "start_vma": hex64(rela_run["start_vma"]),
            "end_vma": hex64(rela_run["end_vma"]),
            "count": rela_run["count"],
        },
        "slide": {
            "runtime_rela_slide": slide,
            "runtime_rela_slide_hex": hex_signed(slide),
            "source": rel(args.v2208_result),
        },
        "checks": {
            "stock_slot_rela_present": stock_slot_ok,
            "rebuilt_label_matches_source": rebuilt_label_ok,
            "v2206_live_values_match_predicted_runtime": live_ok,
            "row_count": len(rows),
        },
        "clone_bases": {name: hex64(address) for name, address in clone_bases.items()},
        "file_operations_offsets": fops_offsets,
        "config": {
            "CONFIG_MMU": "CONFIG_MMU" in config_symbols,
            "symbol_count": len(config_symbols),
        },
        "semantic_rows": rows,
        "runtime_semantic_map": runtime_semantic_map,
        "addend_semantic_map": addend_semantic_map,
        "safety": {
            "host_only": True,
            "live_device_access": False,
            "probe_write_user_executed": False,
            "cgroup_attach": False,
            "wifi_action": False,
            "flash_reboot": False,
        },
    }


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def semantic_targets_for_runtime(runtime_map: dict[str, list[dict[str, Any]]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for runtime, semantics in sorted(runtime_map.items()):
        labels = sorted({item["semantic_target"] for item in semantics})
        uses = ", ".join(f"{item['object']}.{item['field']}" for item in semantics)
        rows.append([f"`{runtime}`", ", ".join(f"`{label}`" for label in labels), uses])
    return rows


def render_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Native Init V2209 Fops Clone Semantic Mapper",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Reason: {result['reason']}",
        f"- Runtime RELA slide: `{result['slide']['runtime_rela_slide_hex']}`",
        f"- Semantic rows: `{result['checks']['row_count']}`",
        f"- Stock slot RELA present: `{str(result['checks']['stock_slot_rela_present']).lower()}`",
        f"- Rebuilt labels match source: `{str(result['checks']['rebuilt_label_matches_source']).lower()}`",
        f"- V2206 live values match predicted runtime: `{str(result['checks']['v2206_live_values_match_predicted_runtime']).lower()}`",
        "",
        "## Interpretation",
        "",
        "- V2209 converts V2208's clone/landing addends into semantic fops targets by using the source initializer field, not nearest System.map symbol names.",
        "- The stock RELA slot is matched by `clone_base + struct file_operations.<field offset>`, so shared targets such as `null_lseek` and `write_null` no longer collapse onto the first addend-only row.",
        "- The rebuilt ELF validates the source semantics: the same fops field slots point at the expected labeled functions before stock RKP_CFP/JOPP clone/landing transformation.",
        "- Nearest stock symbols around the clone addends remain misleading and must not be used as semantic names for these targets.",
        "",
        "## Runtime Semantic Map",
        "",
    ]
    lines.append(render_table(["Runtime pointer", "Semantic target", "Uses"], semantic_targets_for_runtime(result["runtime_semantic_map"])))
    lines.extend([
        "",
        "## Slot-Accurate Rows",
        "",
    ])
    row_lines: list[list[str]] = []
    for row in result["semantic_rows"]:
        nearest = row["nearest_stock_symbol"] or {}
        row_lines.append([
            f"`{row['object']}.{row['field']}`",
            f"`{row['field_offset_hex']}`",
            f"`{row['semantic_target']}`",
            f"`{row['clone_slot']}`",
            f"`{row['stock_addend']}`",
            f"`{row['runtime_pointer']}`",
            f"`{row['delta_from_stock_label_hex']}`",
            f"`{nearest.get('symbol', '-')}`{nearest.get('offset_hex', '')}",
            str(row["rebuilt_matches_expected_label"]).lower(),
            str(row["observed_matches_predicted"]).lower(),
        ])
    lines.append(render_table([
        "Field",
        "Offset",
        "Semantic",
        "Clone slot",
        "Stock addend",
        "Runtime",
        "Delta from stock label",
        "Nearest stock symbol",
        "Rebuilt OK",
        "Live OK",
    ], row_lines))
    lines.extend([
        "",
        "## Clone Bases",
        "",
    ])
    for name, address in sorted(result["clone_bases"].items()):
        lines.append(f"- `{name}` clone base: `{address}`")
    lines.extend([
        "",
        "## Next",
        "",
        "- Use this semantic map as the naming layer for V2206 fops pointers instead of direct nearest-symbol lookup.",
        "- Generalize the same method to other RELA-backed callback tables: source initializer slot → stock RELA addend → runtime pointer via `0x80000` → semantic name.",
        "- For stack/timer symbolization, keep raw IP/frame decoding separate; this fops map solves clone semantic naming for RELA-populated callback tables, not ROPP stack decoding.",
        "",
        "## Safety",
        "",
    ])
    for key, value in result["safety"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend([
        "",
        "## Evidence",
        "",
        f"- Private result: `{rel(DEFAULT_OUT_DIR / 'result.json')}`",
        f"- V2208 result: `{result['inputs']['v2208_result']}`",
        f"- Stock raw: `{result['inputs']['kernel_raw']}`",
        f"- Source `mem.c`: `{result['inputs']['source_mem_c']}`",
        f"- Source `fs.h`: `{result['inputs']['source_fs_h']}`",
        f"- Rebuilt ELF: `{result['inputs']['rebuilt_vmlinux']}`",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--kernel-raw", type=Path, default=DEFAULT_KERNEL_RAW)
    parser.add_argument("--stock-meta", type=Path, default=DEFAULT_STOCK_META)
    parser.add_argument("--v2206-summary", type=Path, default=DEFAULT_V2206_SUMMARY)
    parser.add_argument("--v2208-result", type=Path, default=DEFAULT_V2208_RESULT)
    parser.add_argument("--rebuilt-vmlinux", type=Path, default=DEFAULT_REBUILT_VMLINUX)
    parser.add_argument("--rebuilt-system-map", type=Path, default=DEFAULT_REBUILT_SYSTEM_MAP)
    parser.add_argument("--source-mem-c", type=Path, default=DEFAULT_SOURCE_MEM_C)
    parser.add_argument("--source-fs-h", type=Path, default=DEFAULT_SOURCE_FS_H)
    parser.add_argument("--autoconf", type=Path, default=DEFAULT_AUTOCONF)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.out_dir.joinpath("result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_markdown(result))
    print(json.dumps({
        "decision": result["decision"],
        "report": rel(args.report),
        "result": rel(args.out_dir / "result.json"),
        "runtime_rela_slide": result["slide"]["runtime_rela_slide_hex"],
        "rows": result["checks"]["row_count"],
        "stock_slot_rela_present": result["checks"]["stock_slot_rela_present"],
        "rebuilt_labels_match_source": result["checks"]["rebuilt_label_matches_source"],
        "live_values_match": result["checks"]["v2206_live_values_match_predicted_runtime"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
