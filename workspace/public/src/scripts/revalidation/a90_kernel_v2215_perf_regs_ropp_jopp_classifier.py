#!/usr/bin/env python3
"""Classify V2214 perf-reg samples with stock map plus ROPP/JOPP constraints.

This is host-only analysis. It consumes the V2214 live perf-register sample
ring, the V2197 stock kallsyms map/raw image, and no live device state.

The goals are intentionally bounded:

* P0: find the best text slide for live ctx_pc/ctx_lr addresses.
* P1: separate direct no-slide range-lookup artifacts from resolved text.
* P2: attempt a conservative ROPP saved-LR decode using callsite constraints.
"""

from __future__ import annotations

import argparse
import bisect
import json
import statistics
import struct
import time
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
DEFAULT_V2214_SUMMARY = PRIVATE_KERNEL_RUNS / "v2214-perf-regs-frame-sample-ring-5s-symbols-20260612-050706/summary.json"
DEFAULT_OUT_DIR = PRIVATE_KERNEL_RUNS / "v2215-perf-regs-ropp-jopp-classifier"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2215_PERF_REGS_ROPP_JOPP_CLASSIFIER_2026-06-12.md"

TEXT_SYMBOL_KINDS = {"T", "t", "W", "w"}
JOPP_MAGIC = 0x00BE7BAD
ROPP_EOR_X16_X30_X17 = 0xCA1103D0
DEFAULT_SLIDE_MIN = -0x400000
DEFAULT_SLIDE_MAX = 0x400000
MAX_ROPP_PAIR_CANDIDATES_STORED = 8


@dataclass(frozen=True)
class Symbol:
    address: int
    kind: str
    name: str


@dataclass(frozen=True)
class FunctionRange:
    start: int
    end: int
    name: str
    kind: str


@dataclass(frozen=True)
class Callsite:
    return_static: int
    call_static: int
    kind: str
    target_static: int
    target_symbol: str | None


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
    return f"-0x{-value:x}" if value < 0 else f"0x{value:x}"


def parse_system_map(path: Path) -> list[Symbol]:
    symbols: list[Symbol] = []
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) != 3:
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
    next_address = symbols[index + 1].address if index + 1 < len(symbols) else None
    return {
        "symbol": symbol.name,
        "kind": symbol.kind,
        "symbol_address": hex64(symbol.address),
        "offset": address - symbol.address,
        "offset_hex": hex_signed(address - symbol.address),
        "next_delta": None if next_address is None else next_address - address,
    }


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


def read_u32(raw: bytes, synthetic_base: int, address: int) -> int | None:
    offset = address - synthetic_base
    if offset < 0 or offset + 4 > len(raw):
        return None
    return struct.unpack_from("<I", raw, offset)[0]


def is_bl(insn: int | None) -> bool:
    return insn is not None and (insn & 0xFC000000) == 0x94000000


def decode_bl_target(insn: int, pc: int) -> int:
    imm26 = insn & 0x03FFFFFF
    if imm26 & 0x02000000:
        imm26 -= 0x04000000
    return pc + (imm26 << 2)


def build_function_ranges(symbols: list[Symbol], text_start: int, text_end: int) -> list[FunctionRange]:
    ranges: list[FunctionRange] = []
    for index, symbol in enumerate(symbols):
        if symbol.kind not in TEXT_SYMBOL_KINDS:
            continue
        if not (text_start <= symbol.address < text_end):
            continue
        end = text_end
        for next_symbol in symbols[index + 1:]:
            if next_symbol.address > symbol.address:
                end = min(next_symbol.address, text_end)
                break
        if end > symbol.address:
            ranges.append(FunctionRange(symbol.address, end, symbol.name, symbol.kind))
    ranges.sort(key=lambda item: item.start)
    return ranges


def function_lookup(ranges: list[FunctionRange], starts: list[int], address: int) -> FunctionRange | None:
    index = bisect.bisect_right(starts, address) - 1
    if index < 0:
        return None
    item = ranges[index]
    if item.start <= address < item.end:
        return item
    return None


def union_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for lo, hi in intervals[1:]:
        prev_lo, prev_hi = merged[-1]
        if lo <= prev_hi + 1:
            merged[-1] = (prev_lo, max(prev_hi, hi))
        else:
            merged.append((lo, hi))
    return merged


def top_slide_intervals(
    addresses: list[int],
    ranges: list[FunctionRange],
    slide_min: int,
    slide_max: int,
    limit: int,
) -> list[dict[str, Any]]:
    events: list[tuple[int, int]] = []
    for runtime in sorted(set(addresses)):
        intervals: list[tuple[int, int]] = []
        for item in ranges:
            lo = runtime - (item.end - 1)
            hi = runtime - item.start
            if hi < slide_min or lo > slide_max:
                continue
            lo = max(lo, slide_min)
            hi = min(hi, slide_max)
            if lo <= hi:
                intervals.append((lo, hi))
        for lo, hi in union_intervals(intervals):
            events.append((lo, 1))
            events.append((hi + 1, -1))
    events.sort()
    rows: list[tuple[int, int, int]] = []
    current = 0
    previous: int | None = None
    for point, delta in events:
        if previous is not None and point > previous and current > 0:
            rows.append((current, previous, point - 1))
        current += delta
        previous = point
    rows.sort(key=lambda row: (row[0], -(row[2] - row[1])), reverse=True)
    return [
        {"coverage_unique": count, "slide_min": lo, "slide_max": hi, "width": hi - lo + 1}
        for count, lo, hi in rows[:limit]
    ]


def build_callsite_map(
    raw: bytes,
    synthetic_base: int,
    symbols: list[Symbol],
    addresses: list[int],
    symbol_index: dict[str, int],
) -> dict[int, list[Callsite]]:
    text_start = symbol_index.get("_stext", symbol_index.get("_text", synthetic_base))
    text_end = symbol_index.get("_etext", synthetic_base + len(raw))
    callsites: dict[int, list[Callsite]] = {}
    for offset in range(max(0, text_start - synthetic_base), min(len(raw) - 4, text_end - synthetic_base), 4):
        call_static = synthetic_base + offset
        insn = struct.unpack_from("<I", raw, offset)[0]
        if not is_bl(insn):
            continue
        target = decode_bl_target(insn, call_static)
        nearest = nearest_symbol(symbols, addresses, target)
        target_symbol = None if nearest is None else str(nearest["symbol"])
        kind = "springboard" if target_symbol and target_symbol.startswith("jopp_springboard_blr_") else "direct"
        return_static = call_static + 4
        callsites.setdefault(return_static, []).append(Callsite(return_static, call_static, kind, target, target_symbol))
    return callsites


def candidate_slides_from_intervals(intervals: list[dict[str, Any]]) -> list[int]:
    candidates: set[int] = set()
    for row in intervals:
        lo = int(row["slide_min"])
        hi = int(row["slide_max"])
        for point in {lo, hi, (lo + hi) // 2}:
            aligned = point & ~0x3
            for delta in range(-8, 12, 4):
                value = aligned + delta
                if lo <= value <= hi:
                    candidates.add(value)
    return sorted(candidates)


def score_slide(
    slide: int,
    pc_values: list[int],
    lr_values: list[int],
    ranges: list[FunctionRange],
    starts: list[int],
    callsites: dict[int, list[Callsite]],
) -> dict[str, Any]:
    pc_func = 0
    lr_func = 0
    lr_call = 0
    lr_direct = 0
    lr_springboard = 0
    names: Counter[str] = Counter()
    for value in pc_values:
        item = function_lookup(ranges, starts, value - slide)
        if item is not None:
            pc_func += 1
            names[item.name] += 1
    for value in lr_values:
        static = value - slide
        item = function_lookup(ranges, starts, static)
        if item is not None:
            lr_func += 1
            names[item.name] += 1
        matches = callsites.get(static, [])
        if matches:
            lr_call += 1
            if any(match.kind == "direct" for match in matches):
                lr_direct += 1
            if any(match.kind == "springboard" for match in matches):
                lr_springboard += 1
    return {
        "slide": slide,
        "slide_hex": hex_signed(slide),
        "pc_func": pc_func,
        "lr_func": lr_func,
        "lr_callsite": lr_call,
        "lr_direct_callsite": lr_direct,
        "lr_springboard_callsite": lr_springboard,
        "weighted_score": pc_func + lr_func + (2 * lr_call),
        "top_symbols": names.most_common(12),
    }


def classify_no_slide(
    values: list[int],
    symbols: list[Symbol],
    symbol_addresses: list[int],
    text_start: int,
    text_end: int,
) -> dict[str, Any]:
    rows = []
    categories: Counter[str] = Counter()
    names: Counter[str] = Counter()
    for value in values:
        if text_start <= value < text_end:
            category = "core_text_no_slide"
        elif value >= text_end:
            category = "post_etext_no_slide"
        else:
            category = "pre_text_no_slide"
        categories[category] += 1
        nearest = nearest_symbol(symbols, symbol_addresses, value)
        if nearest:
            names[str(nearest["symbol"])] += 1
        rows.append({
            "runtime": hex64(value),
            "category": category,
            "nearest": nearest,
        })
    return {
        "categories": dict(categories),
        "top_nearest_symbols": names.most_common(16),
        "preview": rows[:24],
    }


def classify_under_slide(
    values: list[int],
    slide: int,
    ranges: list[FunctionRange],
    starts: list[int],
    callsites: dict[int, list[Callsite]],
    limit: int = 24,
) -> dict[str, Any]:
    rows = []
    categories: Counter[str] = Counter()
    names: Counter[str] = Counter()
    for value in values:
        static = value - slide
        item = function_lookup(ranges, starts, static)
        callsite_matches = callsites.get(static, [])
        if item is None:
            category = "unresolved_after_slide"
        elif callsite_matches:
            category = "function_and_callsite"
        else:
            category = "function_range"
        categories[category] += 1
        if item:
            names[item.name] += 1
        rows.append({
            "runtime": hex64(value),
            "static": hex64(static),
            "category": category,
            "symbol": None if item is None else item.name,
            "offset": None if item is None else static - item.start,
            "callsite_kind": sorted({match.kind for match in callsite_matches}),
        })
    return {
        "categories": dict(categories),
        "top_symbols": names.most_common(16),
        "preview": rows[:limit],
    }


def ropp_decode_audit(
    samples: list[dict[str, Any]],
    slide: int,
    callsites: dict[int, list[Callsite]],
) -> dict[str, Any]:
    runtime_returns: dict[int, list[Callsite]] = {
        static + slide: matches
        for static, matches in callsites.items()
    }
    runtime_return_set = set(runtime_returns)
    rows = []
    candidate_counts: list[int] = []
    tested = 0
    unique = 0
    ambiguous = 0
    no_match = 0
    for index, sample in enumerate(samples):
        first = parse_int(sample.get("fp_slot_raw_lr", 0))
        second = parse_int(sample.get("fp2_slot_raw_lr", 0))
        if not first or not second:
            continue
        tested += 1
        pair_delta = first ^ second
        examples = []
        count = 0
        for ret1 in runtime_return_set:
            ret2 = ret1 ^ pair_delta
            if ret2 not in runtime_return_set:
                continue
            count += 1
            if len(examples) < MAX_ROPP_PAIR_CANDIDATES_STORED:
                key = first ^ ret1
                examples.append({
                    "key": hex64(key),
                    "decoded_1": hex64(ret1),
                    "decoded_2": hex64(ret2),
                    "static_1": hex64(ret1 - slide),
                    "static_2": hex64(ret2 - slide),
                    "kind_1": sorted({match.kind for match in runtime_returns[ret1]}),
                    "kind_2": sorted({match.kind for match in runtime_returns[ret2]}),
                })
        candidate_counts.append(count)
        if count == 0:
            no_match += 1
        elif count == 1:
            unique += 1
        else:
            ambiguous += 1
        rows.append({
            "sample_index": index,
            "pid": sample.get("pid"),
            "comm": sample.get("comm"),
            "encoded_1": hex64(first),
            "encoded_2": hex64(second),
            "candidate_count": count,
            "examples": examples,
        })
    return {
        "tested_samples": tested,
        "unique_samples": unique,
        "ambiguous_samples": ambiguous,
        "no_match_samples": no_match,
        "candidate_count_min": min(candidate_counts) if candidate_counts else None,
        "candidate_count_median": statistics.median(candidate_counts) if candidate_counts else None,
        "candidate_count_max": max(candidate_counts) if candidate_counts else None,
        "accepted_exact_unwind": unique > 0 and ambiguous == 0 and no_match == 0,
        "reason": (
            "unique candidate for every tested frame pair"
            if unique > 0 and ambiguous == 0 and no_match == 0 else
            "ROPP pair decode remains ambiguous or unmatched under callsite constraints"
        ),
        "preview": rows[:16],
    }


def render_report(result: dict[str, Any]) -> str:
    p0 = result["p0_slide"]
    p1 = result["p1_generated_text"]
    p2 = result["p2_ropp_decode"]
    lines = [
        "# Native Init V2215 Perf Regs ROPP/JOPP Classifier",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Host-only: `{str(result['safety']['host_only']).lower()}`",
        f"- Best slide: `{p0['best']['slide_hex']}`",
        f"- P0 exact slide accepted: `{str(p0['exact_slide_accepted']).lower()}`",
        f"- Best weighted score: `{p0['best']['weighted_score']}`",
        f"- P2 exact unwind accepted: `{str(p2['accepted_exact_unwind']).lower()}`",
        "",
        "## P0 Slide Classifier",
        "",
        f"- Runtime samples: PC `{p0['pc_count']}`, LR `{p0['lr_count']}`",
        f"- Text range: `{p0['text_start']}` -> `{p0['text_end']}`",
        f"- Best PC function hits: `{p0['best']['pc_func']}` / `{p0['pc_count']}`",
        f"- Best LR function hits: `{p0['best']['lr_func']}` / `{p0['lr_count']}`",
        f"- Best LR callsite hits: `{p0['best']['lr_callsite']}` / `{p0['lr_count']}`",
        f"- Exact-slide threshold: `{p0['exact_threshold']}` LR callsite hits",
        f"- Exact-slide reason: {p0['exact_reason']}",
        "",
        "| Rank | Slide | Score | PC Func | LR Func | LR Callsite | Direct | Springboard | Top Symbols |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for rank, row in enumerate(p0["top_candidates"][:12], 1):
        symbols = ", ".join(f"{name}:{count}" for name, count in row["top_symbols"][:5])
        lines.append(
            f"| {rank} | `{row['slide_hex']}` | {row['weighted_score']} | {row['pc_func']} | "
            f"{row['lr_func']} | {row['lr_callsite']} | {row['lr_direct_callsite']} | "
            f"{row['lr_springboard_callsite']} | {symbols} |"
        )
    lines.extend([
        "",
        "## P1 Generated/Late-Text Discriminator",
        "",
        f"- No-slide PC categories: `{p1['pc_no_slide']['categories']}`",
        f"- No-slide LR categories: `{p1['lr_no_slide']['categories']}`",
        f"- No-slide PC nearest symbols: `{p1['pc_no_slide']['top_nearest_symbols'][:6]}`",
        f"- No-slide LR nearest symbols: `{p1['lr_no_slide']['top_nearest_symbols'][:6]}`",
        f"- Under best slide PC categories: `{p1['pc_under_slide']['categories']}`",
        f"- Under best slide LR categories: `{p1['lr_under_slide']['categories']}`",
        "",
        "- Direct `_end_hyperdrive`/post-`_etext` range hits are classified as no-slide artifacts unless the best-slide view still lands there.",
        "- This keeps direct range lookup separate from exact callgraph naming.",
        "",
        "## P2 ROPP Saved-LR Decode Audit",
        "",
        f"- Tested samples: `{p2['tested_samples']}`",
        f"- Unique decode samples: `{p2['unique_samples']}`",
        f"- Ambiguous decode samples: `{p2['ambiguous_samples']}`",
        f"- No-match samples: `{p2['no_match_samples']}`",
        f"- Candidate count min/median/max: `{p2['candidate_count_min']}` / `{p2['candidate_count_median']}` / `{p2['candidate_count_max']}`",
        f"- Reason: {p2['reason']}",
        "",
        "| Sample | PID | Comm | Candidates | Encoded LR1 | Encoded LR2 |",
        "| ---: | ---: | --- | ---: | --- | --- |",
    ])
    for row in p2["preview"][:12]:
        lines.append(
            f"| {row['sample_index']} | {row.get('pid')} | `{row.get('comm')}` | "
            f"{row['candidate_count']} | `{row['encoded_1']}` | `{row['encoded_2']}` |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- P0 moves V2214 away from no-slide direct range lookup and into explicit slide scoring.",
        "- P0 ranks a best candidate but does not promote it to exact because LR-callsite support is below threshold.",
        "- P1 shows whether `_end_hyperdrive` labels are real generated-text hits or artifacts of missing slide correction.",
        "- P2 keeps saved FP-chain LR decode conservative; ambiguous callsite-pair solutions are not promoted to exact unwind.",
        "",
        "## Evidence",
        "",
        f"- V2214 summary: `{result['inputs']['v2214_summary']}`",
        f"- System.map: `{result['inputs']['system_map']}`",
        f"- Kernel raw: `{result['inputs']['kernel_raw']}`",
        f"- Private result: `{result['out_dir']}/result.json`",
        "",
        "## Safety",
        "",
    ])
    for key, value in result["safety"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2214-summary", type=Path, default=DEFAULT_V2214_SUMMARY)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--kernel-raw", type=Path, default=DEFAULT_KERNEL_RAW)
    parser.add_argument("--stock-meta", type=Path, default=DEFAULT_STOCK_META)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--top-intervals", type=int, default=64)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = json.loads(args.v2214_summary.read_text())
    samples = summary["probe"]["samples"]
    pc_values = [parse_int(sample["ctx_pc"]) for sample in samples]
    lr_values = [parse_int(sample["ctx_lr"]) for sample in samples]

    symbols = parse_system_map(args.system_map)
    symbol_addresses = [symbol.address for symbol in symbols]
    symbol_index = build_symbol_index(symbols)
    synthetic_base = load_synthetic_base(args.stock_meta)
    raw = load_kernel_raw(args.kernel_raw)
    text_start = symbol_index["_stext"]
    text_end = symbol_index["_etext"]
    ranges = build_function_ranges(symbols, text_start, text_end)
    starts = [item.start for item in ranges]
    callsites = build_callsite_map(raw, synthetic_base, symbols, symbol_addresses, symbol_index)

    interval_rows = top_slide_intervals(
        pc_values + lr_values,
        ranges,
        DEFAULT_SLIDE_MIN,
        DEFAULT_SLIDE_MAX,
        args.top_intervals,
    )
    candidate_slides = candidate_slides_from_intervals(interval_rows)
    scored = [
        score_slide(slide, pc_values, lr_values, ranges, starts, callsites)
        for slide in candidate_slides
    ]
    scored.sort(key=lambda row: (row["weighted_score"], row["lr_callsite"], row["pc_func"], row["lr_func"]), reverse=True)
    if not scored:
        raise RuntimeError("no candidate slides produced")
    best = scored[0]
    best_slide = int(best["slide"])
    exact_threshold = max(1, len(lr_values) // 2)
    exact_slide_accepted = (
        best["pc_func"] == len(pc_values)
        and best["lr_func"] == len(lr_values)
        and best["lr_callsite"] >= exact_threshold
    )
    exact_reason = (
        "all PC/LR samples are in function ranges and LR-callsite support meets threshold"
        if exact_slide_accepted else
        "candidate is useful for ranking, but LR-callsite support is below exact-slide threshold"
    )

    result = {
        "decision": "v2215-slide-ranked-ropp-ambiguous"
        if not exact_slide_accepted else
        "v2215-slide-exact-ropp-ambiguous",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "out_dir": rel(out_dir),
        "inputs": {
            "v2214_summary": rel(args.v2214_summary),
            "system_map": rel(args.system_map),
            "kernel_raw": rel(args.kernel_raw),
            "stock_meta": rel(args.stock_meta),
        },
        "p0_slide": {
            "pc_count": len(pc_values),
            "lr_count": len(lr_values),
            "text_start": hex64(text_start),
            "text_end": hex64(text_end),
            "function_range_count": len(ranges),
            "callsite_count": len(callsites),
            "interval_candidates": interval_rows,
            "exact_threshold": exact_threshold,
            "exact_slide_accepted": exact_slide_accepted,
            "exact_reason": exact_reason,
            "best": best,
            "top_candidates": scored[:24],
        },
        "p1_generated_text": {
            "pc_no_slide": classify_no_slide(pc_values, symbols, symbol_addresses, text_start, text_end),
            "lr_no_slide": classify_no_slide(lr_values, symbols, symbol_addresses, text_start, text_end),
            "pc_under_slide": classify_under_slide(pc_values, best_slide, ranges, starts, callsites),
            "lr_under_slide": classify_under_slide(lr_values, best_slide, ranges, starts, callsites),
        },
        "p2_ropp_decode": ropp_decode_audit(samples, best_slide, callsites),
        "safety": {
            "host_only": True,
            "live_device_access": False,
            "probe_write_user_executed": False,
            "cgroup_attach": False,
            "wifi_action": False,
            "flash_reboot": False,
            "partition_or_firmware_write": False,
        },
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    REPORT_PATH.write_text(render_report(result))
    print(json.dumps({
        "decision": result["decision"],
        "best_slide": result["p0_slide"]["best"]["slide_hex"],
        "best_score": result["p0_slide"]["best"]["weighted_score"],
        "p2_accepted": result["p2_ropp_decode"]["accepted_exact_unwind"],
        "out_dir": rel(out_dir),
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
