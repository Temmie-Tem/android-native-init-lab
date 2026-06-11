#!/usr/bin/env python3
"""Inventory RELA-backed file_operations semantic mappings.

V2209 proved a slot-accurate semantic mapping for /dev/null and /dev/zero fops.
This host-only pass generalizes the same method across parsable
static const struct file_operations initializers:

  source initializer field -> struct file_operations offset -> stock RELA slot
  -> runtime pointer via V2208 0x80000 slide -> semantic source target.

Only rows with unambiguous clone-base and rebuilt-ELF label validation are
promoted as high-confidence.  Full inventory stays under workspace/private.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import struct
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SOURCE_ROOT = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source"
PRIVATE_KERNEL_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_STOCK_DIR = PRIVATE_KERNEL_RUNS / "v2197-stock-kallsyms"
DEFAULT_SYSTEM_MAP = DEFAULT_STOCK_DIR / "System.map"
DEFAULT_KERNEL_RAW = DEFAULT_STOCK_DIR / "kernel.raw"
DEFAULT_STOCK_META = DEFAULT_STOCK_DIR / "stock-kallsyms.json"
DEFAULT_V2208_RESULT = PRIVATE_KERNEL_RUNS / "v2208-rela-fops-discriminator/result.json"
DEFAULT_V2209_RESULT = PRIVATE_KERNEL_RUNS / "v2209-fops-clone-semantic-mapper/result.json"
DEFAULT_REBUILT_VMLINUX = SOURCE_ROOT / "out/vmlinux"
DEFAULT_REBUILT_SYSTEM_MAP = SOURCE_ROOT / "out/System.map"
DEFAULT_SOURCE_FS_H = SOURCE_ROOT / "include/linux/fs.h"
DEFAULT_AUTOCONF = SOURCE_ROOT / "out/include/generated/autoconf.h"
DEFAULT_OUT_DIR = PRIVATE_KERNEL_RUNS / "v2210-generic-fops-rela-inventory"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2210_GENERIC_FOPS_RELA_INVENTORY_2026-06-12.md"

KERNEL_VA_MIN = 0xFFFFFF8000000000
KERNEL_VA_MAX = 0xFFFFFF80FFFFFFFF
RELA_INFO_RELATIVE = 0x403
SEARCH_WINDOW_BEFORE = 0x8000
SEARCH_WINDOW_AFTER = 0x20000
U64_MASK = (1 << 64) - 1


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


@dataclass(frozen=True)
class FopsInitializer:
    name: str
    path: Path
    line: int
    fields: dict[str, str]


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


def parse_config_symbols(path: Path) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(r"^#define\s+(CONFIG_[A-Za-z0-9_]+)\b", path.read_text(errors="replace"), re.M)
    }


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


def parse_fops_initializers(source_root: Path, config_symbols: set[str]) -> list[FopsInitializer]:
    initializers: list[FopsInitializer] = []
    pattern = re.compile(
        r"static\s+(?:const\s+)?struct\s+file_operations\s+"
        r"(?:[A-Za-z_][A-Za-z0-9_]*\s+)*"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{(?P<body>.*?)^\};",
        re.S | re.M,
    )
    for path in sorted(source_root.rglob("*")):
        if path.suffix not in {".c", ".h"}:
            continue
        if "/out/" in str(path):
            continue
        text = strip_inactive_config_blocks(path.read_text(errors="replace"), config_symbols)
        macros = parse_macros(text)
        for match in pattern.finditer(text):
            body = match.group("body")
            fields: dict[str, str] = {}
            for field_match in re.finditer(
                r"\.(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<target>[A-Za-z_][A-Za-z0-9_]*)\s*,",
                body,
            ):
                fields[field_match.group("field")] = resolve_alias(field_match.group("target"), macros)
            if not fields:
                continue
            initializers.append(FopsInitializer(
                name=match.group("name"),
                path=path,
                line=text[:match.start()].count("\n") + 1,
                fields=fields,
            ))
    return initializers


def load_kernel_raw(path: Path) -> bytes:
    payload = path.read_bytes()
    if payload.startswith(b"UNCOMPRESSED_IMG"):
        image_size = struct.unpack_from("<I", payload, 16)[0]
        raw = payload[20:20 + image_size]
        if len(raw) != image_size:
            raise ValueError("truncated UNCOMPRESSED_IMG wrapper")
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
    if best_start is None:
        raise RuntimeError("stock RELA run not found")
    entries: list[RelaEntry] = []
    for offset in range(best_start, best_start + best_count * 24, 24):
        r_offset, r_info, r_addend = struct.unpack_from("<QQQ", raw, offset)
        entries.append(RelaEntry(synthetic_base + offset, r_offset, r_info, r_addend))
    return {
        "start_vma": synthetic_base + best_start,
        "end_vma": synthetic_base + best_start + (best_count - 1) * 24,
        "count": best_count,
        "entries": entries,
    }


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
    payload = vmlinux.read_bytes()
    entries: list[RelaEntry] = []
    for index in range(section_size // entry_size):
        offset = section_offset + index * entry_size
        r_offset, r_info, signed_addend = struct.unpack_from("<QQq", payload, offset)
        entries.append(RelaEntry(section_addr + index * entry_size, r_offset, r_info, signed_addend & U64_MASK))
    return entries


def find_clone_base(
    original_address: int,
    field_offsets: list[int],
    stock_offsets: list[int],
    addend_ref_counts: Counter[int],
) -> dict[str, Any]:
    lower = original_address - SEARCH_WINDOW_BEFORE
    upper = original_address + SEARCH_WINDOW_AFTER
    candidates: Counter[int] = Counter()
    for offset in field_offsets:
        start = bisect.bisect_left(stock_offsets, lower + offset)
        end = bisect.bisect_right(stock_offsets, upper + offset)
        for r_offset in stock_offsets[start:end]:
            base = r_offset - offset
            if lower <= base <= upper:
                candidates[base] += 1
    ranked = sorted(
        candidates.items(),
        key=lambda item: (-item[1], -addend_ref_counts[item[0]], abs(item[0] - original_address), item[0]),
    )
    if not ranked:
        return {"clone_base": None, "best_count": 0, "base_ref_count": 0, "unique_best": False, "top_candidates": []}
    best_count = ranked[0][1]
    best_ref_count = addend_ref_counts[ranked[0][0]]
    unique_best = sum(1 for base, count in ranked if count == best_count and addend_ref_counts[base] == best_ref_count) == 1
    return {
        "clone_base": ranked[0][0],
        "best_count": best_count,
        "base_ref_count": best_ref_count,
        "unique_best": unique_best,
        "top_candidates": [
            {
                "base": hex64(base),
                "delta": hex_signed(base - original_address),
                "score": count,
                "base_ref_count": addend_ref_counts[base],
            }
            for base, count in ranked[:5]
        ],
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    config_symbols = parse_config_symbols(args.autoconf)
    fops_offsets = parse_file_operations_offsets(args.source_fs_h, config_symbols)
    initializers = parse_fops_initializers(args.source_root, config_symbols)
    stock_symbols = parse_system_map(args.system_map)
    stock_index = build_symbol_index(stock_symbols)
    rebuilt_symbols = parse_system_map(args.rebuilt_system_map)
    rebuilt_index = build_symbol_index(rebuilt_symbols)
    raw = load_kernel_raw(args.kernel_raw)
    synthetic_base = load_synthetic_base(args.stock_meta)
    stock_rela = discover_stock_rela(raw, synthetic_base)
    stock_by_offset = {entry.r_offset: entry for entry in stock_rela["entries"] if entry.r_info == RELA_INFO_RELATIVE}
    stock_offsets = sorted(stock_by_offset)
    addend_ref_counts = Counter(entry.r_addend for entry in stock_rela["entries"] if entry.r_info == RELA_INFO_RELATIVE)
    rebuilt_entries = parse_elf_rela_dyn(args.rebuilt_vmlinux)
    rebuilt_by_offset = {entry.r_offset: entry for entry in rebuilt_entries if entry.r_info == RELA_INFO_RELATIVE}
    v2208 = json.loads(args.v2208_result.read_text())
    v2209 = json.loads(args.v2209_result.read_text())
    slide = parse_int(v2208["slide"]["best"])

    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    high_confidence_rows = 0
    for initializer in initializers:
        semantic_rows: list[dict[str, Any]] = []
        stock_address = stock_index.get(initializer.name)
        rebuilt_address = rebuilt_index.get(initializer.name)
        source_fields = {
            field: target
            for field, target in initializer.fields.items()
            if field in fops_offsets and target in rebuilt_index
        }
        if stock_address is None or rebuilt_address is None:
            status = "missing_symbol"
            clone = {"clone_base": None, "best_count": 0, "base_ref_count": 0, "unique_best": False, "top_candidates": []}
        elif len(source_fields) < 2:
            status = "too_few_labelled_fields"
            clone = {"clone_base": None, "best_count": 0, "base_ref_count": 0, "unique_best": False, "top_candidates": []}
        else:
            offsets = [fops_offsets[field] for field in source_fields]
            clone = find_clone_base(stock_address, offsets, stock_offsets, addend_ref_counts)
            clone_base = clone["clone_base"]
            stock_hits = 0
            rebuilt_hits = 0
            if clone_base is not None:
                for field, target in sorted(source_fields.items(), key=lambda item: fops_offsets[item[0]]):
                    field_offset = fops_offsets[field]
                    stock_entry = stock_by_offset.get(clone_base + field_offset)
                    rebuilt_entry = rebuilt_by_offset.get(rebuilt_address + field_offset)
                    rebuilt_target = rebuilt_index[target]
                    if stock_entry is not None:
                        stock_hits += 1
                    if rebuilt_entry is not None and rebuilt_entry.r_addend == rebuilt_target:
                        rebuilt_hits += 1
                    semantic_rows.append({
                        "field": field,
                        "target": target,
                        "field_offset": field_offset,
                        "stock_slot": None if stock_entry is None else hex64(stock_entry.r_offset),
                        "stock_addend": None if stock_entry is None else hex64(stock_entry.r_addend),
                        "runtime_pointer": None if stock_entry is None else hex64(stock_entry.r_addend + slide),
                        "rebuilt_matches_label": rebuilt_entry is not None and rebuilt_entry.r_addend == rebuilt_target,
                    })
            else:
                stock_hits = 0
                rebuilt_hits = 0
                semantic_rows = []
            if (
                clone_base is not None
                and clone["unique_best"]
                and clone["base_ref_count"] > 0
                and stock_hits == len(source_fields)
                and rebuilt_hits == len(source_fields)
            ):
                status = "high_confidence"
                high_confidence_rows += len(semantic_rows)
            elif clone_base is not None and stock_hits > 0:
                status = "partial_stock_rela"
            else:
                status = "no_stock_clone_base"
        status_counts[status] += 1
        row = {
            "name": initializer.name,
            "source_path": rel(initializer.path),
            "source_line": initializer.line,
            "status": status,
            "stock_label": None if stock_address is None else hex64(stock_address),
            "rebuilt_label": None if rebuilt_address is None else hex64(rebuilt_address),
            "labelled_field_count": len(source_fields),
            "clone_base": None if clone["clone_base"] is None else hex64(clone["clone_base"]),
            "clone_delta": None if clone["clone_base"] is None or stock_address is None else hex_signed(clone["clone_base"] - stock_address),
            "clone_score": clone["best_count"],
            "clone_base_ref_count": clone["base_ref_count"],
            "unique_best": clone["unique_best"],
            "top_candidates": clone["top_candidates"],
            "semantic_rows": semantic_rows if "semantic_rows" in locals() and initializer.name else [],
        }
        rows.append(row)

    high_confidence = [row for row in rows if row["status"] == "high_confidence"]
    high_confidence.sort(key=lambda row: (-row["labelled_field_count"], row["source_path"], row["name"]))
    delta_counts = Counter(row["clone_delta"] for row in high_confidence if row["clone_delta"])
    decision = "v2210-generic-fops-rela-inventory-built" if high_confidence else "v2210-generic-fops-rela-inventory-empty"
    return {
        "decision": decision,
        "reason": f"Built high-confidence semantic inventory for {len(high_confidence)} RELA-backed fops objects.",
        "inputs": {
            "source_root": rel(args.source_root),
            "system_map": rel(args.system_map),
            "kernel_raw": rel(args.kernel_raw),
            "stock_meta": rel(args.stock_meta),
            "v2208_result": rel(args.v2208_result),
            "v2209_result": rel(args.v2209_result),
            "rebuilt_vmlinux": rel(args.rebuilt_vmlinux),
            "rebuilt_system_map": rel(args.rebuilt_system_map),
            "source_fs_h": rel(args.source_fs_h),
            "autoconf": rel(args.autoconf),
        },
        "slide": {
            "runtime_rela_slide": slide,
            "runtime_rela_slide_hex": hex_signed(slide),
        },
        "stock_rela": {
            "start_vma": hex64(stock_rela["start_vma"]),
            "end_vma": hex64(stock_rela["end_vma"]),
            "count": stock_rela["count"],
        },
        "counts": {
            "parsed_fops_initializers": len(initializers),
            "high_confidence_objects": len(high_confidence),
            "high_confidence_semantic_rows": high_confidence_rows,
            "status_counts": dict(status_counts),
            "clone_delta_counts": dict(delta_counts.most_common(12)),
        },
        "v2209_anchor": {
            "decision": v2209.get("decision"),
            "checks": v2209.get("checks"),
        },
        "high_confidence_examples": high_confidence[:40],
        "inventory_rows": rows,
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


def render_markdown(result: dict[str, Any]) -> str:
    counts = result["counts"]
    lines: list[str] = [
        "# Native Init V2210 Generic Fops RELA Inventory",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Reason: {result['reason']}",
        f"- Runtime RELA slide: `{result['slide']['runtime_rela_slide_hex']}`",
        f"- Parsed fops initializers: `{counts['parsed_fops_initializers']}`",
        f"- High-confidence objects: `{counts['high_confidence_objects']}`",
        f"- High-confidence semantic rows: `{counts['high_confidence_semantic_rows']}`",
        "",
        "## Interpretation",
        "",
        "- V2210 generalizes V2209 from the `/dev/null`/`/dev/zero` proof pair to every parsable `static const struct file_operations` initializer with enough label evidence.",
        "- Promotion is intentionally strict: a fops object is high-confidence only when the source initializer fields, stock clone-base RELA slots, and rebuilt-ELF field labels all agree.",
        "- The full private inventory keeps partial and failed candidates for later parser work; the report only promotes high-confidence rows.",
        "- This is still a RELA-backed callback-table naming layer. It does not decode ROPP-protected call stacks.",
        "",
        "## Status Counts",
        "",
    ]
    status_rows = [[f"`{key}`", value] for key, value in sorted(counts["status_counts"].items())]
    lines.append(render_table(["Status", "Objects"], status_rows))
    lines.extend([
        "",
        "## Clone Delta Counts",
        "",
    ])
    delta_rows = [[f"`{key}`", value] for key, value in counts["clone_delta_counts"].items()]
    lines.append(render_table(["Clone delta", "High-confidence objects"], delta_rows))
    lines.extend([
        "",
        "## High-Confidence Examples",
        "",
    ])
    example_rows: list[list[Any]] = []
    for row in result["high_confidence_examples"][:20]:
        sample_targets = ", ".join(
            f"{semantic['field']}→{semantic['target']}"
            for semantic in row["semantic_rows"][:4]
        )
        example_rows.append([
            f"`{row['name']}`",
            f"`{row['clone_delta']}`",
            row["labelled_field_count"],
            row["source_path"],
            sample_targets,
        ])
    lines.append(render_table(["Fops", "Clone delta", "Fields", "Source", "Sample semantics"], example_rows))
    lines.extend([
        "",
        "## Anchors",
        "",
        f"- V2209 anchor decision: `{result['v2209_anchor']['decision']}`",
        f"- Stock RELA run: `{result['stock_rela']['start_vma']}` → `{result['stock_rela']['end_vma']}` (`{result['stock_rela']['count']}` entries)",
        "",
        "## Next",
        "",
        "- Use the private `inventory_rows` as a semantic lookup source for RELA-backed callback tables.",
        "- Improve source parsing for macro-generated or non-static fops only if a needed object is missing from high-confidence inventory.",
        "- Keep ROPP stack decoding as a separate V2211 path; V2210 supplies semantic names for table callbacks, not stack return-address recovery.",
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
        f"- V2209 result: `{result['inputs']['v2209_result']}`",
        f"- V2208 result: `{result['inputs']['v2208_result']}`",
        f"- Stock raw: `{result['inputs']['kernel_raw']}`",
        f"- Source root: `{result['inputs']['source_root']}`",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--kernel-raw", type=Path, default=DEFAULT_KERNEL_RAW)
    parser.add_argument("--stock-meta", type=Path, default=DEFAULT_STOCK_META)
    parser.add_argument("--v2208-result", type=Path, default=DEFAULT_V2208_RESULT)
    parser.add_argument("--v2209-result", type=Path, default=DEFAULT_V2209_RESULT)
    parser.add_argument("--rebuilt-vmlinux", type=Path, default=DEFAULT_REBUILT_VMLINUX)
    parser.add_argument("--rebuilt-system-map", type=Path, default=DEFAULT_REBUILT_SYSTEM_MAP)
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
        "parsed_fops": result["counts"]["parsed_fops_initializers"],
        "high_confidence_objects": result["counts"]["high_confidence_objects"],
        "high_confidence_semantic_rows": result["counts"]["high_confidence_semantic_rows"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
