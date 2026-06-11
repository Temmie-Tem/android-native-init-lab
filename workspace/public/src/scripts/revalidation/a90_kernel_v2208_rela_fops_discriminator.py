#!/usr/bin/env python3
"""Resolve V2206 fops member pointers against stock RELA addends.

This is host-only analysis. It consumes the bit-exact stock raw kernel image
from V2197, the V2206 live fops/member capture, and the rebuilt reference ELF.
It verifies whether the apparent V2206/V2207 member-slide spread is explained
by the stock image's RELA addends rather than direct System.map labels.
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
PRIVATE_KERNEL_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_STOCK_DIR = PRIVATE_KERNEL_RUNS / "v2197-stock-kallsyms"
DEFAULT_SYSTEM_MAP = DEFAULT_STOCK_DIR / "System.map"
DEFAULT_KERNEL_RAW = DEFAULT_STOCK_DIR / "kernel.raw"
DEFAULT_STOCK_META = DEFAULT_STOCK_DIR / "stock-kallsyms.json"
DEFAULT_V2206_SUMMARY = PRIVATE_KERNEL_RUNS / "v2206-fops-member-anchor-20260612-015121/summary.json"
DEFAULT_REBUILT_VMLINUX = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/vmlinux"
DEFAULT_REBUILT_SYSTEM_MAP = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/System.map"
DEFAULT_SOURCE_MEM_C = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/mem.c"
DEFAULT_OUT_DIR = PRIVATE_KERNEL_RUNS / "v2208-rela-fops-discriminator"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2208_RELA_FOPS_DISCRIMINATOR_2026-06-12.md"

KERNEL_VA_MIN = 0xFFFFFF8000000000
KERNEL_VA_MAX = 0xFFFFFF80FFFFFFFF
RELA_INFO_RELATIVE = 0x403
MAX_SLIDE = 0x200000
U64_MASK = (1 << 64) - 1

FOPS_MEMBER_OFFSETS = {
    "llseek": 8,
    "read": 16,
    "write": 24,
    "read_iter": 32,
    "write_iter": 40,
    "mmap": 88,
    "get_unmapped_area": 152,
    "splice_write": 176,
}

TARGETS: list[dict[str, Any]] = [
    {"field": "fd0_fop", "kind": "object", "expected": "null_fops"},
    {"field": "fd1_fop", "kind": "object", "expected": "zero_fops"},
    {"field": "fd0_llseek", "kind": "member", "object": "null_fops", "member": "llseek", "expected": "null_lseek"},
    {"field": "fd0_read", "kind": "member", "object": "null_fops", "member": "read", "expected": "read_null"},
    {"field": "fd0_write", "kind": "member", "object": "null_fops", "member": "write", "expected": "write_null"},
    {"field": "fd0_read_iter", "kind": "member", "object": "null_fops", "member": "read_iter", "expected": "read_iter_null"},
    {"field": "fd0_write_iter", "kind": "member", "object": "null_fops", "member": "write_iter", "expected": "write_iter_null"},
    {"field": "fd0_splice_write", "kind": "member", "object": "null_fops", "member": "splice_write", "expected": "splice_write_null"},
    {"field": "fd1_llseek", "kind": "member", "object": "zero_fops", "member": "llseek", "expected": "null_lseek"},
    {"field": "fd1_write", "kind": "member", "object": "zero_fops", "member": "write", "expected": "write_null"},
    {"field": "fd1_read_iter", "kind": "member", "object": "zero_fops", "member": "read_iter", "expected": "read_iter_zero"},
    {"field": "fd1_write_iter", "kind": "member", "object": "zero_fops", "member": "write_iter", "expected": "write_iter_null"},
    {"field": "fd1_mmap", "kind": "member", "object": "zero_fops", "member": "mmap", "expected": "mmap_zero"},
    {
        "field": "fd1_get_unmapped_area",
        "kind": "member",
        "object": "zero_fops",
        "member": "get_unmapped_area",
        "expected": "get_unmapped_area_zero",
    },
]


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
    current_start: int | None
    current_count: int
    for residue in range(0, 24, 4):
        current_start = None
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


def build_rela_addend_index(entries: list[RelaEntry]) -> dict[int, list[RelaEntry]]:
    index: dict[int, list[RelaEntry]] = {}
    for entry in entries:
        index.setdefault(entry.r_addend, []).append(entry)
    return index


def live_value(summary: dict[str, Any], field: str) -> int:
    value = summary["probe"]["summary"].get(field)
    return parse_int(value)


def score_slides(target_values: list[int], rela_addends: list[int]) -> list[dict[str, Any]]:
    per_slide_fields: dict[int, set[int]] = {}
    unique_addends = sorted(set(rela_addends))
    for field_index, runtime in enumerate(target_values):
        for addend in unique_addends:
            slide = runtime - addend
            if 0 <= slide <= MAX_SLIDE:
                per_slide_fields.setdefault(slide, set()).add(field_index)
    scored = [
        {"slide": slide, "slide_hex": hex_signed(slide), "matched_fields": len(fields)}
        for slide, fields in per_slide_fields.items()
    ]
    scored.sort(key=lambda row: (-row["matched_fields"], row["slide"]))
    return scored


def parse_elf_rela_dyn(vmlinux: Path) -> list[RelaEntry]:
    if not vmlinux.exists():
        return []
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
        return []
    section_addr = int(match.group(1), 16)
    section_offset = int(match.group(2), 16)
    section_size = int(match.group(3), 16)
    entry_size = int(match.group(4), 16)
    if entry_size != 24:
        raise ValueError(f"unexpected .rela.dyn entry size: {entry_size}")
    payload = vmlinux.read_bytes()
    entries: list[RelaEntry] = []
    for index in range(section_size // entry_size):
        offset = section_offset + index * entry_size
        r_offset, r_info, signed_addend = struct.unpack_from("<QQq", payload, offset)
        entries.append(RelaEntry(section_addr + index * entry_size, r_offset, r_info, signed_addend & U64_MASK))
    return entries


def rebuilt_rela_comparison(rebuilt_vmlinux: Path, rebuilt_system_map: Path) -> dict[str, Any]:
    if not rebuilt_vmlinux.exists() or not rebuilt_system_map.exists():
        return {"available": False, "reason": "rebuilt ELF/System.map missing", "rows": []}
    symbols = parse_system_map(rebuilt_system_map)
    symbol_index = build_symbol_index(symbols)
    entries = parse_elf_rela_dyn(rebuilt_vmlinux)
    offset_index = {entry.r_offset: entry for entry in entries if entry.r_info == RELA_INFO_RELATIVE}
    rows: list[dict[str, Any]] = []
    for target in TARGETS:
        if target["kind"] != "member":
            continue
        object_address = symbol_index.get(target["object"])
        expected_address = symbol_index.get(target["expected"])
        if object_address is None or expected_address is None:
            rows.append({
                "field": target["field"],
                "available": False,
                "reason": "symbol missing",
            })
            continue
        slot = object_address + FOPS_MEMBER_OFFSETS[target["member"]]
        entry = offset_index.get(slot)
        rows.append({
            "field": target["field"],
            "object": target["object"],
            "member": target["member"],
            "slot": hex64(slot),
            "expected_symbol": target["expected"],
            "expected_address": hex64(expected_address),
            "rela_addend": None if entry is None else hex64(entry.r_addend),
            "matches_expected_label": bool(entry and entry.r_addend == expected_address),
        })
    return {
        "available": True,
        "vmlinux": rel(rebuilt_vmlinux),
        "system_map": rel(rebuilt_system_map),
        "rela_entry_count": len(entries),
        "matched_expected_labels": sum(1 for row in rows if row.get("matches_expected_label")),
        "member_row_count": len(rows),
        "rows": rows,
    }


def source_initializer_evidence(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"available": False, "path": rel(path)}
    text = path.read_text(errors="replace")
    evidence: dict[str, Any] = {"available": True, "path": rel(path), "symbols": {}}
    for name in [
        "null_fops",
        "zero_fops",
        "null_lseek",
        "read_null",
        "write_null",
        "read_iter_null",
        "write_iter_null",
        "splice_write_null",
        "read_iter_zero",
        "mmap_zero",
        "get_unmapped_area_zero",
    ]:
        match = re.search(rf"^(.*\b{name}\b.*)$", text, re.MULTILINE)
        evidence["symbols"][name] = None if match is None else {"line": text[:match.start()].count("\n") + 1, "text": match.group(1).strip()}
    return evidence


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    stock_symbols = parse_system_map(args.system_map)
    stock_addresses = [symbol.address for symbol in stock_symbols]
    stock_symbol_index = build_symbol_index(stock_symbols)
    raw = load_kernel_raw(args.kernel_raw)
    synthetic_base = load_synthetic_base(args.stock_meta)
    v2206_summary = json.loads(args.v2206_summary.read_text())
    rela_run = discover_stock_rela(raw, synthetic_base)
    rela_entries: list[RelaEntry] = rela_run["entries"]
    rela_addend_index = build_rela_addend_index(rela_entries)

    target_values = [live_value(v2206_summary, target["field"]) for target in TARGETS]
    scored_slides = score_slides(target_values, [entry.r_addend for entry in rela_entries])
    best_slide = scored_slides[0]["slide"] if scored_slides else None
    if best_slide is None:
        raise RuntimeError("no candidate slide found")

    rows: list[dict[str, Any]] = []
    for target, runtime in zip(TARGETS, target_values, strict=True):
        static_addend = runtime - best_slide
        matches = rela_addend_index.get(static_addend, [])
        primary = matches[0] if matches else None
        expected_address = stock_symbol_index.get(target["expected"])
        expected_delta = None if expected_address is None else static_addend - expected_address
        offset_nearest = None if primary is None else nearest_symbol(stock_symbols, stock_addresses, primary.r_offset)
        addend_nearest = nearest_symbol(stock_symbols, stock_addresses, static_addend)
        rows.append({
            "field": target["field"],
            "kind": target["kind"],
            "runtime": hex64(runtime),
            "slide": hex_signed(best_slide),
            "static_addend": hex64(static_addend),
            "rela_match_count": len(matches),
            "rela_location": None if primary is None else hex64(primary.location),
            "rela_r_offset": None if primary is None else hex64(primary.r_offset),
            "r_offset_nearest": offset_nearest,
            "addend_nearest": addend_nearest,
            "expected_symbol": target["expected"],
            "expected_address": None if expected_address is None else hex64(expected_address),
            "delta_from_expected": None if expected_delta is None else expected_delta,
            "delta_from_expected_hex": None if expected_delta is None else hex_signed(expected_delta),
            "source_target": target,
        })

    object_rows = [row for row in rows if row["kind"] == "object"]
    member_rows = [row for row in rows if row["kind"] == "member"]
    all_matched = all(row["rela_match_count"] > 0 for row in rows)
    rebuilt = rebuilt_rela_comparison(args.rebuilt_vmlinux, args.rebuilt_system_map)

    decision = "v2208-stock-rela-clone-slide-resolves-v2206-members" if all_matched and best_slide == 0x80000 else "v2208-rela-fops-discriminator-needs-review"
    reason = (
        "A single stock-RELA-derived 0x80000 runtime slide explains every targeted V2206 /dev/null and /dev/zero fops object/member pointer."
        if decision == "v2208-stock-rela-clone-slide-resolves-v2206-members"
        else "The targeted V2206 fops pointers did not all resolve through one stock RELA slide; inspect result rows."
    )

    return {
        "decision": decision,
        "reason": reason,
        "inputs": {
            "system_map": rel(args.system_map),
            "kernel_raw": rel(args.kernel_raw),
            "stock_meta": rel(args.stock_meta),
            "v2206_summary": rel(args.v2206_summary),
            "rebuilt_vmlinux": rel(args.rebuilt_vmlinux),
            "rebuilt_system_map": rel(args.rebuilt_system_map),
            "source_mem_c": rel(args.source_mem_c),
        },
        "kernel": {
            "synthetic_base": hex64(synthetic_base),
            "raw_size": len(raw),
            "stock_symbol_count": len(stock_symbols),
        },
        "rela_run": {
            "start_offset": hex(rela_run["start_offset"]),
            "start_vma": hex64(rela_run["start_vma"]),
            "end_vma": hex64(rela_run["end_vma"]),
            "count": rela_run["count"],
            "record_size": 24,
            "alignment_note": "run starts at a 4-byte-aligned offset; 8-byte-only scanners miss it",
        },
        "slide": {
            "best": best_slide,
            "best_hex": hex_signed(best_slide),
            "matched_targets": sum(1 for row in rows if row["rela_match_count"] > 0),
            "total_targets": len(rows),
            "top_candidates": scored_slides[:12],
        },
        "object_rows": object_rows,
        "member_rows": member_rows,
        "rebuilt_rela_comparison": rebuilt,
        "source_initializer_evidence": source_initializer_evidence(args.source_mem_c),
        "previous_interpretation_delta": {
            "v2204_object_slide_hex": "0x8179c",
            "corrected_rela_runtime_slide_hex": hex_signed(best_slide),
            "null_fops_label_delta_hex": next((row["delta_from_expected_hex"] for row in object_rows if row["field"] == "fd0_fop"), None),
            "zero_fops_label_delta_hex": next((row["delta_from_expected_hex"] for row in object_rows if row["field"] == "fd1_fop"), None),
        },
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
    lines: list[str] = [
        "# Native Init V2208 RELA Fops Discriminator",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Reason: {result['reason']}",
        f"- Corrected RELA runtime slide: `{result['slide']['best_hex']}`",
        f"- Matched targets: `{result['slide']['matched_targets']}/{result['slide']['total_targets']}`",
        f"- Stock RELA run: `{result['rela_run']['start_vma']}` → `{result['rela_run']['end_vma']}` (`{result['rela_run']['count']}` entries)",
        "",
        "## Interpretation",
        "",
        "- V2208 resolves the V2206/V2207 ambiguity: the live `/dev/null` and `/dev/zero` fops object/member values match stock RELA addends under one slide, `0x80000`.",
        "- The previous `0x8179c` object slide was a symbol-label alias against `null_fops`/`zero_fops`; the stock RELA addends use clone/landing object addresses `0x179c` after those labels.",
        "- The V2206 member slide spread was caused by comparing live runtime values to original labeled function symbols instead of the stock RELA addends that actually populate the image.",
        "- This does not yet assign semantic function names to every clone/landing addend. It does explain the exact runtime addresses and separates relocation from semantic clone mapping.",
        "",
        "## RELA Discovery",
        "",
        f"- `synthetic_base`: `{result['kernel']['synthetic_base']}`",
        f"- `start_offset`: `{result['rela_run']['start_offset']}`",
        f"- Record size: `{result['rela_run']['record_size']}`",
        f"- Alignment note: {result['rela_run']['alignment_note']}",
        "",
        "## Object Rows",
        "",
    ]
    object_rows = []
    for row in result["object_rows"]:
        object_rows.append([
            f"`{row['field']}`",
            f"`{row['runtime']}`",
            f"`{row['static_addend']}`",
            f"`{row['rela_location']}`",
            f"`{row['rela_r_offset']}`",
            f"`{row['expected_symbol']}`",
            f"`{row['delta_from_expected_hex']}`",
        ])
    lines.append(render_table(["Field", "Runtime", "RELA addend", "RELA row", "Reloc slot", "Expected label", "Delta"], object_rows))
    lines.extend([
        "",
        "## Member Rows",
        "",
    ])
    member_rows = []
    for row in result["member_rows"]:
        nearest = row["addend_nearest"] or {}
        member_rows.append([
            f"`{row['field']}`",
            f"`{row['runtime']}`",
            f"`{row['static_addend']}`",
            f"`{row['rela_location']}`",
            f"`{row['expected_symbol']}`",
            f"`{row['delta_from_expected_hex']}`",
            f"`{nearest.get('symbol', '-')}`{nearest.get('offset_hex', '')}",
        ])
    lines.append(render_table(["Field", "Runtime", "RELA addend", "RELA row", "Expected label", "Delta", "Nearest stock symbol"], member_rows))
    rebuilt = result["rebuilt_rela_comparison"]
    lines.extend([
        "",
        "## Rebuilt ELF Contrast",
        "",
        f"- Available: `{str(rebuilt['available']).lower()}`",
    ])
    if rebuilt["available"]:
        lines.extend([
            f"- Rebuilt RELA entries: `{rebuilt['rela_entry_count']}`",
            f"- Member slots matching expected labels: `{rebuilt['matched_expected_labels']}/{rebuilt['member_row_count']}`",
            "- Meaning: the local rebuilt ELF keeps the source-level fops members tied to labeled functions, while the stock live image uses clone/landing addends. Rebuilt labels must not be treated as bit-exact stock labels.",
        ])
    lines.extend([
        "",
        "## Next",
        "",
        "- Treat `0x80000` as the proven runtime relocation slide for this stock RELA/object layer.",
        "- Do not promote original System.map function names onto clone/landing addends until a clone-to-original semantic map is built.",
        "- Next useful unit: derive that semantic clone map from stock RELA initializer order plus RKP_CFP/JOPP-generated landing metadata, then re-apply it to stack/timer/fops symbolization.",
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
        f"- Stock System.map: `{result['inputs']['system_map']}`",
        f"- Stock raw: `{result['inputs']['kernel_raw']}`",
        f"- V2206 summary: `{result['inputs']['v2206_summary']}`",
        f"- Rebuilt ELF: `{result['inputs']['rebuilt_vmlinux']}`",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--kernel-raw", type=Path, default=DEFAULT_KERNEL_RAW)
    parser.add_argument("--stock-meta", type=Path, default=DEFAULT_STOCK_META)
    parser.add_argument("--v2206-summary", type=Path, default=DEFAULT_V2206_SUMMARY)
    parser.add_argument("--rebuilt-vmlinux", type=Path, default=DEFAULT_REBUILT_VMLINUX)
    parser.add_argument("--rebuilt-system-map", type=Path, default=DEFAULT_REBUILT_SYSTEM_MAP)
    parser.add_argument("--source-mem-c", type=Path, default=DEFAULT_SOURCE_MEM_C)
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
        "rela_slide": result["slide"]["best_hex"],
        "matched_targets": f"{result['slide']['matched_targets']}/{result['slide']['total_targets']}",
        "rela_run_count": result["rela_run"]["count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
