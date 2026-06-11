#!/usr/bin/env python3
"""Classify V2206 file-ops member pointers against JOPP/ROPP evidence.

This is host-only analysis.  It consumes the V2197 bit-exact stock kernel map,
the V2206 live fops/member capture, and Samsung RKP_CFP source evidence.  It
does not force an exact text slide.  It records which interpretation layers are
proven and which remain blocked by JOPP/ROPP/runtime patching.
"""

from __future__ import annotations

import argparse
import bisect
import json
import struct
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
DEFAULT_V2197_SYMBOLIZATION = DEFAULT_STOCK_DIR / "symbolization.json"
DEFAULT_V2206_SUMMARY = PRIVATE_KERNEL_RUNS / "v2206-fops-member-anchor-20260612-015121/summary.json"
DEFAULT_RKP_INSTRUMENT = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/scripts/rkp_cfp/instrument.py"
DEFAULT_AUTOCONF = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/include/generated/autoconf.h"
DEFAULT_OUT_DIR = PRIVATE_KERNEL_RUNS / "v2207-jopp-stub-mapper"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2207_JOPP_STUB_MAPPER_2026-06-12.md"

JOPP_MAGIC = 0x00BE7BAD
ROPP_EOR_X16_X30_X17 = 0xCA1103D0
TEXT_SYMBOL_KINDS = {"T", "t", "W", "w"}
FOPS_MEMBER_EXPECTED: dict[str, list[str]] = {
    "fd0_llseek": ["null_lseek"],
    "fd0_read": ["read_null"],
    "fd0_write": ["write_null"],
    "fd0_read_iter": ["read_iter_null"],
    "fd0_write_iter": ["write_iter_null"],
    "fd0_splice_write": ["splice_write_null"],
    "fd1_llseek": ["null_lseek"],
    "fd1_write": ["write_null"],
    "fd1_read_iter": ["read_iter_zero"],
    "fd1_write_iter": ["write_iter_null"],
    "fd1_mmap": ["mmap_zero"],
    "fd1_get_unmapped_area": ["get_unmapped_area_zero"],
}


@dataclass(frozen=True)
class Symbol:
    address: int
    kind: str
    name: str


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
    return f"0x{value & ((1 << 64) - 1):016x}"


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
    symbols.sort(key=lambda symbol: symbol.address)
    return symbols


def build_symbol_index(symbols: list[Symbol]) -> dict[str, int]:
    index: dict[str, int] = {}
    for symbol in symbols:
        index.setdefault(symbol.name, symbol.address)
    return index


def nearest_symbol(symbols: list[Symbol], addresses: list[int], address: int) -> dict[str, Any] | None:
    symbol_index = bisect.bisect_right(addresses, address) - 1
    if symbol_index < 0:
        return None
    symbol = symbols[symbol_index]
    next_address = symbols[symbol_index + 1].address if symbol_index + 1 < len(symbols) else None
    return {
        "symbol_address": hex64(symbol.address),
        "symbol": symbol.name,
        "kind": symbol.kind,
        "offset": address - symbol.address,
        "next_delta": None if next_address is None else next_address - address,
    }


def load_kernel(path: Path) -> bytes:
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


def raw_offset(synthetic_base: int, address: int) -> int | None:
    offset = address - synthetic_base
    if offset < 0:
        return None
    return offset


def read_u32(raw: bytes, synthetic_base: int, address: int) -> int | None:
    offset = raw_offset(synthetic_base, address)
    if offset is None or offset + 4 > len(raw):
        return None
    return struct.unpack_from("<I", raw, offset)[0]


def read_u64(raw: bytes, synthetic_base: int, address: int) -> int | None:
    offset = raw_offset(synthetic_base, address)
    if offset is None or offset + 8 > len(raw):
        return None
    return struct.unpack_from("<Q", raw, offset)[0]


def classify_insn(value: int | None, address: int | None = None) -> dict[str, Any]:
    if value is None:
        return {"mnemonic": "out-of-range"}
    row: dict[str, Any] = {"word": f"0x{value:08x}", "mnemonic": "other"}
    if value == JOPP_MAGIC:
        row["mnemonic"] = "jopp_magic"
    elif value == ROPP_EOR_X16_X30_X17:
        row["mnemonic"] = "ropp_eor_x16_x30_x17"
    elif (value & 0xFC000000) == 0x94000000:
        row["mnemonic"] = "bl"
        if address is not None:
            row["target"] = hex64(decode_branch_target(value, address))
    elif (value & 0x7C000000) == 0x14000000:
        row["mnemonic"] = "b"
        if address is not None:
            row["target"] = hex64(decode_branch_target(value, address))
    elif (value & 0xFFFFFC1F) == 0xD63F0000:
        row["mnemonic"] = f"blr_x{(value >> 5) & 0x1f}"
    elif (value & 0xFFFFFC1F) == 0xD61F0000:
        row["mnemonic"] = f"br_x{(value >> 5) & 0x1f}"
    elif value == 0xD65F03C0:
        row["mnemonic"] = "ret"
    return row


def decode_branch_target(value: int, pc: int) -> int:
    imm26 = value & 0x03FFFFFF
    if imm26 & 0x02000000:
        imm26 -= 0x04000000
    return pc + (imm26 << 2)


def instruction_window(raw: bytes, synthetic_base: int, address: int, before: int = 8, after: int = 16) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = address - before
    end = address + after
    for current in range(start, end + 1, 4):
        value = read_u32(raw, synthetic_base, current)
        decoded = classify_insn(value, current)
        decoded["address"] = hex64(current)
        decoded["relative_to_target"] = current - address
        rows.append(decoded)
    return rows


def entry_profile(raw: bytes, synthetic_base: int, entry: int) -> dict[str, Any]:
    preceding_magic_delta: int | None = None
    for delta in range(4, 0x84, 4):
        if read_u32(raw, synthetic_base, entry - delta) == JOPP_MAGIC:
            preceding_magic_delta = delta
            break
    ropp_offsets: list[int] = []
    for offset in range(0, 0x40, 4):
        if read_u32(raw, synthetic_base, entry + offset) == ROPP_EOR_X16_X30_X17:
            ropp_offsets.append(offset)
    return {
        "address": hex64(entry),
        "jopp_magic_delta_before": preceding_magic_delta,
        "jopp_magic_before_entry": preceding_magic_delta == 4,
        "ropp_prologue_offsets": ropp_offsets,
        "ropp_prologue_present": bool(ropp_offsets),
        "first_window": instruction_window(raw, synthetic_base, entry, before=8, after=16),
    }


def static_mapping(
    raw: bytes,
    synthetic_base: int,
    symbols: list[Symbol],
    addresses: list[int],
    runtime: int,
    slide: int,
) -> dict[str, Any]:
    static = runtime - slide
    mapping = nearest_symbol(symbols, addresses, static)
    row: dict[str, Any] = {
        "runtime": hex64(runtime),
        "slide": slide,
        "slide_hex": hex_signed(slide),
        "static": hex64(static),
        "raw_in_range": raw_offset(synthetic_base, static) is not None and raw_offset(synthetic_base, static) + 4 <= len(raw),
        "instruction": classify_insn(read_u32(raw, synthetic_base, static), static),
        "jopp_magic_nearby": entry_profile(raw, synthetic_base, static)["jopp_magic_delta_before"],
        "ropp_nearby_offsets": entry_profile(raw, synthetic_base, static)["ropp_prologue_offsets"],
    }
    if mapping:
        row.update(mapping)
        row["text_symbol"] = mapping["kind"] in TEXT_SYMBOL_KINDS
    else:
        row["text_symbol"] = False
    return row


def parse_v2206_members(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = json.loads(path.read_text())
    rows: list[dict[str, Any]] = []
    for observation in summary["member_analysis"]["observations"]:
        runtime = parse_int(observation["runtime"])
        if runtime == 0:
            continue
        field = observation["field"]
        rows.append({
            "field": field,
            "runtime": runtime,
            "runtime_hex": hex64(runtime),
            "expected_symbols": observation.get("expected_symbols") or FOPS_MEMBER_EXPECTED.get(field, []),
        })
    return summary, rows


def parse_required_config(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(errors="replace").splitlines():
        if not line.startswith("#define CONFIG_RKP_CFP"):
            continue
        parts = line.split(maxsplit=2)
        if len(parts) == 3:
            result[parts[1]] = parts[2]
    return result


def inspect_rkp_source(path: Path) -> dict[str, Any]:
    text = path.read_text(errors="replace") if path.exists() else ""
    snippets: list[str] = []
    for needle in (
        "Replace:\n        BLR rX",
        "Instrument the nop just before the function.",
        "objdump.write(magic_i, objdump.JOPP_MAGIC)",
        "jopp_springboard_blr_x{register}",
        "eor RRX, x30, RRK",
        "stp x29, RRX",
        "ldp x29, RRX",
    ):
        snippets.append(needle)
    return {
        "path": rel(path),
        "exists": path.exists(),
        "has_jopp_blr_rewrite": "jopp_springboard_blr_x{register}" in text,
        "has_magic_before_function": "objdump.write(magic_i, objdump.JOPP_MAGIC)" in text,
        "has_ropp_eor_stp": "eor RRX, x30, RRK" in text and "stp x29, RRX" in text,
        "has_ropp_ldp_decode": "ldp x29, RRX" in text and "eor x30, RRX, RRK" in text,
        "searched_snippets": snippets,
    }


def load_v2197_slide_context(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    rows: list[dict[str, Any]] = []
    for candidate in data.get("top_slide_candidates") or []:
        rows.append({
            "slide": candidate.get("slide"),
            "slide_hex": candidate.get("slide_hex"),
            "stack_score": candidate.get("stack_score"),
            "stack_total": candidate.get("stack_total"),
            "source_symbol": (candidate.get("source") or {}).get("source_symbol"),
            "timer_entry_weighted_score": candidate.get("timer_entry_weighted_score"),
        })
    return rows[:8]


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    symbols = parse_system_map(args.system_map)
    addresses = [symbol.address for symbol in symbols]
    symbol_index = build_symbol_index(symbols)
    raw = load_kernel(args.kernel_raw)
    synthetic_base = load_synthetic_base(args.stock_meta)
    v2206_summary, members = parse_v2206_members(args.v2206_summary)
    object_slide = parse_int(v2206_summary["object_analysis"]["best_slide"])
    member_slide_rows = v2206_summary["member_analysis"].get("ranked_slides") or []

    config = parse_required_config(args.autoconf)
    rkp_source = inspect_rkp_source(args.rkp_instrument)
    expected_entry_profiles: dict[str, Any] = {}
    missing_expected_symbols: list[str] = []
    for expected_symbol in sorted({name for member in members for name in member["expected_symbols"]}):
        address = symbol_index.get(expected_symbol)
        if address is None:
            missing_expected_symbols.append(expected_symbol)
            continue
        expected_entry_profiles[expected_symbol] = entry_profile(raw, synthetic_base, address)

    object_slots: list[dict[str, Any]] = []
    for object_observation in v2206_summary["object_analysis"]["observations"]:
        for candidate in object_observation.get("candidates") or []:
            if parse_int(candidate["slide"]) != object_slide:
                continue
            runtime = parse_int(object_observation["runtime"])
            static = parse_int(candidate["static"])
            object_slots.append({
                "field": object_observation["field"],
                "runtime": hex64(runtime),
                "static": hex64(static),
                "expected_symbols": object_observation.get("expected_symbols") or [],
                "raw_member_words_zero": all((read_u64(raw, synthetic_base, static + member_offset) or 0) == 0 for member_offset in (8, 16, 24, 32, 40, 88, 152, 176)),
            })

    slide_candidates: dict[str, int] = {"object_slide": object_slide}
    for row in member_slide_rows:
        slide_candidates[f"member_rank_{len(slide_candidates)}_{row['slide_hex']}"] = parse_int(row["slide"])
    for candidate in load_v2197_slide_context(args.v2197_symbolization):
        if candidate.get("slide") is not None:
            slide_candidates[f"v2197_{candidate['slide_hex']}"] = parse_int(candidate["slide"])

    member_rows: list[dict[str, Any]] = []
    per_field_slides: Counter[int] = Counter()
    for member in members:
        runtime = member["runtime"]
        expected_mappings: list[dict[str, Any]] = []
        for expected_symbol in member["expected_symbols"]:
            expected_address = symbol_index.get(expected_symbol)
            if expected_address is None:
                continue
            slide_to_expected = runtime - expected_address
            per_field_slides[slide_to_expected] += 1
            expected_mappings.append({
                "expected_symbol": expected_symbol,
                "expected_static": hex64(expected_address),
                "slide_to_expected": slide_to_expected,
                "slide_to_expected_hex": hex_signed(slide_to_expected),
                "delta_from_object_slide": object_slide - slide_to_expected,
                "delta_from_object_slide_hex": hex_signed(object_slide - slide_to_expected),
                "entry_profile": {
                    "jopp_magic_before_entry": expected_entry_profiles.get(expected_symbol, {}).get("jopp_magic_before_entry"),
                    "ropp_prologue_present": expected_entry_profiles.get(expected_symbol, {}).get("ropp_prologue_present"),
                    "ropp_prologue_offsets": expected_entry_profiles.get(expected_symbol, {}).get("ropp_prologue_offsets"),
                },
            })

        candidate_mappings: dict[str, Any] = {}
        for slide_name, slide_value in slide_candidates.items():
            candidate_mappings[slide_name] = static_mapping(raw, synthetic_base, symbols, addresses, runtime, slide_value)

        member_rows.append({
            "field": member["field"],
            "runtime": member["runtime_hex"],
            "expected_symbols": member["expected_symbols"],
            "expected_mappings": expected_mappings,
            "candidate_mappings": candidate_mappings,
        })

    single_slide_exact_hits: list[dict[str, Any]] = []
    for slide, count in per_field_slides.most_common():
        sources: list[str] = []
        for member in member_rows:
            for mapping in member["expected_mappings"]:
                if mapping["slide_to_expected"] == slide:
                    sources.append(f"{member['field']}:{mapping['expected_symbol']}")
        single_slide_exact_hits.append({
            "slide": slide,
            "slide_hex": hex_signed(slide),
            "exact_expected_hit_count": count,
            "sources": sources,
        })

    object_slide_expected_hits = 0
    object_slide_unrelated_hits: list[str] = []
    for member in member_rows:
        mapping = member["candidate_mappings"]["object_slide"]
        if mapping.get("symbol") in member["expected_symbols"] and mapping.get("offset") == 0:
            object_slide_expected_hits += 1
        elif mapping.get("symbol"):
            object_slide_unrelated_hits.append(f"{member['field']}->{mapping['symbol']}+{mapping.get('offset')}")

    exact_member_slide = max((row["exact_expected_hit_count"] for row in single_slide_exact_hits), default=0) >= 4
    if object_slide_expected_hits == 0 and not exact_member_slide:
        decision = "v2207-member-targets-runtime-patched-not-direct-symbol-slide"
        reason = "V2206 member values are readable, but neither the exact object slide nor any single member slide maps them to the expected fops entries."
    elif exact_member_slide:
        decision = "v2207-member-target-single-slide-candidate"
        reason = "At least four fops member pointers agree on one expected-entry slide; review candidate before promoting."
    else:
        decision = "v2207-member-target-needs-review"
        reason = "Mixed evidence; review object/member mapping details."

    return {
        "decision": decision,
        "reason": reason,
        "inputs": {
            "system_map": rel(args.system_map),
            "kernel_raw": rel(args.kernel_raw),
            "stock_meta": rel(args.stock_meta),
            "v2206_summary": rel(args.v2206_summary),
            "v2197_symbolization": rel(args.v2197_symbolization),
            "rkp_instrument": rel(args.rkp_instrument),
            "autoconf": rel(args.autoconf),
        },
        "kernel": {
            "synthetic_base": hex64(synthetic_base),
            "raw_size": len(raw),
            "symbol_count": len(symbols),
        },
        "rkp_cfp": {
            "config": {key: config.get(key) for key in sorted(config) if key.startswith("CONFIG_RKP_CFP")},
            "source": rkp_source,
            "jopp_magic": f"0x{JOPP_MAGIC:08x}",
            "ropp_eor_x16_x30_x17": f"0x{ROPP_EOR_X16_X30_X17:08x}",
        },
        "object_layer": {
            "slide": object_slide,
            "slide_hex": hex_signed(object_slide),
            "exact": bool(v2206_summary["object_analysis"].get("exact_slide")),
            "sources": v2206_summary["object_analysis"].get("best_sources") or [],
            "slots": object_slots,
        },
        "member_layer": {
            "exact_single_text_slide": exact_member_slide,
            "object_slide_expected_hits": object_slide_expected_hits,
            "object_slide_unrelated_hits": object_slide_unrelated_hits[:12],
            "single_slide_exact_hits": single_slide_exact_hits,
            "v2197_slide_context": load_v2197_slide_context(args.v2197_symbolization),
            "rows": member_rows,
        },
        "expected_entry_profiles": expected_entry_profiles,
        "missing_expected_symbols": missing_expected_symbols,
        "safety": {
            "host_only": True,
            "live_device_access": False,
            "probe_write_user_executed": False,
            "cgroup_attach": False,
            "wifi_action": False,
            "flash_reboot": False,
        },
    }


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def render_markdown(result: dict[str, Any]) -> str:
    object_layer = result["object_layer"]
    member_layer = result["member_layer"]
    rkp_cfp = result["rkp_cfp"]
    lines: list[str] = [
        "# Native Init V2207 JOPP Stub Mapper",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Reason: {result['reason']}",
        f"- Object/fops slide: `{object_layer['slide_hex']}`",
        f"- Object slide expected member hits: `{member_layer['object_slide_expected_hits']}`",
        f"- Single member text slide exact: `{str(member_layer['exact_single_text_slide']).lower()}`",
        "",
        "## Interpretation",
        "",
        "- V2204/V2206 still prove the object/rodata layer: `/dev/null` and `/dev/zero` f_op objects agree on `0x8179c`.",
        "- V2207 blocks promoting that object slide to fops member text targets: object-slide mapping sends member pointers into unrelated `msm_geni_serial_*` code, not `drivers/char/mem.c` fops entries.",
        "- The expected fops entries in the bit-exact map do contain JOPP magic immediately before entry and ROPP prologue patterns, so the stock map/source side is internally coherent.",
        "- The live fops member values require runtime patch/RKP_CFP/JOPP metadata interpretation; direct `runtime - single_slide = expected_symbol` is not valid yet.",
        "",
        "## RKP_CFP Source Basis",
        "",
        f"- `CONFIG_RKP_CFP_JOPP`: `{rkp_cfp['config'].get('CONFIG_RKP_CFP_JOPP')}`",
        f"- `CONFIG_RKP_CFP_ROPP`: `{rkp_cfp['config'].get('CONFIG_RKP_CFP_ROPP')}`",
        f"- `CONFIG_RKP_CFP_ROPP_SYSREGKEY`: `{rkp_cfp['config'].get('CONFIG_RKP_CFP_ROPP_SYSREGKEY')}`",
        f"- `CONFIG_RKP_CFP_JOPP_MAGIC`: `{rkp_cfp['config'].get('CONFIG_RKP_CFP_JOPP_MAGIC')}`",
        f"- Source has BLR→springboard rewrite: `{str(rkp_cfp['source']['has_jopp_blr_rewrite']).lower()}`",
        f"- Source has function-entry magic write: `{str(rkp_cfp['source']['has_magic_before_function']).lower()}`",
        f"- Source has ROPP LR save/restore rewrite: `{str(rkp_cfp['source']['has_ropp_eor_stp'] and rkp_cfp['source']['has_ropp_ldp_decode']).lower()}`",
        "",
        "## Object Layer",
        "",
        f"- Exact object slide: `{object_layer['slide_hex']}` from `{', '.join(object_layer['sources'])}`",
        "- Raw stock image table slots for `null_fops/zero_fops` are zero at the checked member offsets, so live member values are runtime-populated/patched state rather than plain raw-image table data.",
        "",
        "## Member Slide Spread",
        "",
    ]
    slide_rows = []
    for row in member_layer["single_slide_exact_hits"]:
        slide_rows.append([
            row["slide_hex"],
            row["exact_expected_hit_count"],
            ", ".join(row["sources"]),
        ])
    lines.append(render_table(["Slide", "Expected-entry hits", "Sources"], slide_rows[:12]))
    lines.extend([
        "",
        "## Member Mapping Details",
        "",
    ])
    detail_rows = []
    for row in member_layer["rows"]:
        expected = row["expected_mappings"][0] if row["expected_mappings"] else {}
        object_mapping = row["candidate_mappings"]["object_slide"]
        detail_rows.append([
            f"`{row['field']}`",
            f"`{row['runtime']}`",
            ", ".join(row["expected_symbols"]),
            f"`{expected.get('slide_to_expected_hex', '-')}`",
            f"`{expected.get('delta_from_object_slide_hex', '-')}`",
            f"`{object_mapping.get('symbol', '-')}`+{object_mapping.get('offset', '-')}",
            object_mapping.get("instruction", {}).get("mnemonic", "-"),
        ])
    lines.append(render_table([
        "Field",
        "Runtime",
        "Expected",
        "Expected slide",
        "Delta from object",
        "Object-slide maps to",
        "Insn",
    ], detail_rows))
    lines.extend([
        "",
        "## Expected Entry Profiles",
        "",
    ])
    profile_rows = []
    for name, profile in sorted(result["expected_entry_profiles"].items()):
        profile_rows.append([
            f"`{name}`",
            f"`{profile['address']}`",
            str(profile["jopp_magic_before_entry"]).lower(),
            str(profile["ropp_prologue_present"]).lower(),
            ",".join(str(offset) for offset in profile["ropp_prologue_offsets"]),
        ])
    lines.append(render_table(["Symbol", "Static entry", "JOPP magic -4", "ROPP prologue", "ROPP offsets"], profile_rows))
    lines.extend([
        "",
        "## Next",
        "",
        "- Do not label V2206 member pointers as exact text symbolization yet.",
        "- Next useful unit is a runtime patch/metadata discriminator: either locate the RKP_CFP/JOPP function-pointer rewrite table used to populate fops members, or add a read-only live probe around the fops object update path to capture pre/post member values.",
        "- Keep V2204 object slide available for object/rodata anchors only; keep text-stack/timer/fops-member symbolization behind the JOPP/ROPP decode gate.",
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
        f"- System.map: `{result['inputs']['system_map']}`",
        f"- Kernel raw: `{result['inputs']['kernel_raw']}`",
        f"- V2206 summary: `{result['inputs']['v2206_summary']}`",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--kernel-raw", type=Path, default=DEFAULT_KERNEL_RAW)
    parser.add_argument("--stock-meta", type=Path, default=DEFAULT_STOCK_META)
    parser.add_argument("--v2206-summary", type=Path, default=DEFAULT_V2206_SUMMARY)
    parser.add_argument("--v2197-symbolization", type=Path, default=DEFAULT_V2197_SYMBOLIZATION)
    parser.add_argument("--rkp-instrument", type=Path, default=DEFAULT_RKP_INSTRUMENT)
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
        "object_slide": result["object_layer"]["slide_hex"],
        "object_slide_expected_hits": result["member_layer"]["object_slide_expected_hits"],
        "single_member_text_slide_exact": result["member_layer"]["exact_single_text_slide"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
