#!/usr/bin/env python3
"""V2217 exact-slide resymbolization and ROPP decode audit.

This host-only analyzer consumes the V2216 codeword-matched slide and applies it
to V2216 perf-register samples. It keeps three layers separate:

* exact static symbol+offset for live ctx_pc/ctx_lr;
* callsite classification for live ctx_lr return addresses;
* conservative saved-FP LR ROPP decode attempts.
"""

from __future__ import annotations

import argparse
import bisect
import json
import struct
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_KERNEL_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_STOCK_DIR = PRIVATE_KERNEL_RUNS / "v2197-stock-kallsyms"
DEFAULT_SYSTEM_MAP = DEFAULT_STOCK_DIR / "System.map"
DEFAULT_KERNEL_RAW = DEFAULT_STOCK_DIR / "kernel.raw"
DEFAULT_STOCK_META = DEFAULT_STOCK_DIR / "stock-kallsyms.json"
DEFAULT_V2216_SUMMARY = PRIVATE_KERNEL_RUNS / "v2216-perf-regs-codeword-sample-ring-5s-20260612-053331/summary.json"
DEFAULT_OUT_DIR = PRIVATE_KERNEL_RUNS / "v2217-exact-slide-resymbolization-audit"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2217_EXACT_SLIDE_RESYMBOLIZATION_AUDIT_2026-06-12.md"

TEXT_SYMBOL_KINDS = {"T", "t", "W", "w"}
KERNEL_TEXT_MIN = 0xFFFFFF8008000000
KERNEL_TEXT_MAX = 0xFFFFFF800C000000
MAX_EXAMPLES = 16


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


def build_callsite_map(
    raw: bytes,
    synthetic_base: int,
    symbols: list[Symbol],
    symbol_addresses: list[int],
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
        nearest = nearest_symbol(symbols, symbol_addresses, target)
        target_symbol = None if nearest is None else str(nearest["symbol"])
        kind = "springboard" if target_symbol and target_symbol.startswith("jopp_springboard_blr_") else "direct"
        return_static = call_static + 4
        callsites.setdefault(return_static, []).append(Callsite(return_static, call_static, kind, target, target_symbol))
    return callsites


def extract_exact_slide(summary: dict[str, Any]) -> int:
    codeword = ((summary.get("analysis") or {}).get("codeword") or {})
    best = codeword.get("best") or {}
    if not codeword.get("accepted_exact_codeword_slide"):
        raise ValueError("V2216 summary does not mark exact codeword slide accepted")
    return parse_int(best["slide"])


def decode_insn_kind(insn: int | None) -> str:
    if insn is None:
        return "out-of-range"
    if (insn & 0xFC000000) == 0x94000000:
        return "bl"
    if (insn & 0x7C000000) == 0x14000000:
        return "b"
    if (insn & 0xFFFFFC1F) == 0xD63F0000:
        return f"blr_x{(insn >> 5) & 0x1f}"
    if (insn & 0xFFFFFC1F) == 0xD61F0000:
        return f"br_x{(insn >> 5) & 0x1f}"
    if insn == 0xD65F03C0:
        return "ret"
    if insn == 0xCA1103D0:
        return "ropp_eor_x16_x30_x17"
    if insn == 0x00BE7BAD:
        return "jopp_magic"
    return "other"


def resymbolize_live_regs(
    samples: list[dict[str, Any]],
    slide: int,
    ranges: list[FunctionRange],
    starts: list[int],
    callsites: dict[int, list[Callsite]],
    raw: bytes,
    synthetic_base: int,
) -> dict[str, Any]:
    rows = []
    pc_symbols: Counter[str] = Counter()
    lr_symbols: Counter[str] = Counter()
    pc_resolved = 0
    lr_resolved = 0
    lr_callsite = 0
    lr_user = 0
    for index, sample in enumerate(samples):
        ctx_pc = parse_int(sample.get("ctx_pc", 0))
        ctx_lr = parse_int(sample.get("ctx_lr", 0))
        pc_static = ctx_pc - slide
        lr_static = ctx_lr - slide
        pc_func = function_lookup(ranges, starts, pc_static)
        lr_func = function_lookup(ranges, starts, lr_static)
        lr_matches = callsites.get(lr_static, [])
        if pc_func is not None:
            pc_resolved += 1
            pc_symbols[pc_func.name] += 1
        if lr_func is not None:
            lr_resolved += 1
            lr_symbols[lr_func.name] += 1
        if lr_matches:
            lr_callsite += 1
        if ctx_lr and not (KERNEL_TEXT_MIN <= ctx_lr < KERNEL_TEXT_MAX):
            lr_user += 1
        if len(rows) < MAX_EXAMPLES:
            pc_insn_static = read_u32(raw, synthetic_base, pc_static)
            lr_prev_insn_static = read_u32(raw, synthetic_base, lr_static - 4)
            rows.append({
                "index": index,
                "pid": sample.get("pid"),
                "comm": sample.get("comm"),
                "ctx_pc": hex64(ctx_pc),
                "ctx_pc_static": hex64(pc_static),
                "ctx_pc_symbol": None if pc_func is None else pc_func.name,
                "ctx_pc_offset": None if pc_func is None else pc_static - pc_func.start,
                "ctx_pc_insn_live": f"0x{parse_int(sample.get('ctx_pc_insn', 0)):08x}",
                "ctx_pc_insn_static": None if pc_insn_static is None else f"0x{pc_insn_static:08x}",
                "ctx_lr": hex64(ctx_lr),
                "ctx_lr_static": hex64(lr_static),
                "ctx_lr_symbol": None if lr_func is None else lr_func.name,
                "ctx_lr_offset": None if lr_func is None else lr_static - lr_func.start,
                "ctx_lr_callsite": bool(lr_matches),
                "ctx_lr_callsite_kind": sorted({match.kind for match in lr_matches}),
                "ctx_lr_prev_insn_live": f"0x{parse_int(sample.get('ctx_lr_prev_insn', 0)):08x}",
                "ctx_lr_prev_insn_static": None if lr_prev_insn_static is None else f"0x{lr_prev_insn_static:08x}",
                "ctx_lr_prev_insn_kind": decode_insn_kind(lr_prev_insn_static),
            })
    return {
        "sample_count": len(samples),
        "pc_resolved": pc_resolved,
        "lr_resolved": lr_resolved,
        "lr_callsite": lr_callsite,
        "lr_user_or_nontext": lr_user,
        "pc_top_symbols": pc_symbols.most_common(24),
        "lr_top_symbols": lr_symbols.most_common(24),
        "preview": rows,
    }


def ropp_decode_attempt(
    samples: list[dict[str, Any]],
    slide: int,
    callsites: dict[int, list[Callsite]],
    raw: bytes,
    synthetic_base: int,
    ranges: list[FunctionRange],
    starts: list[int],
) -> dict[str, Any]:
    runtime_call_returns: dict[int, list[Callsite]] = {
        static + slide: matches
        for static, matches in callsites.items()
    }
    runtime_return_set = set(runtime_call_returns)
    tested = 0
    no_match = 0
    unique = 0
    ambiguous = 0
    same_function_context_unique = 0
    candidate_counts: list[int] = []
    reduced_counts: list[int] = []
    rows = []
    for index, sample in enumerate(samples):
        enc1 = parse_int(sample.get("fp_slot_raw_lr", 0))
        enc2 = parse_int(sample.get("fp2_slot_raw_lr", 0))
        if not enc1 or not enc2:
            continue
        tested += 1
        pair_delta = enc1 ^ enc2
        candidates = []
        for ret1 in runtime_return_set:
            ret2 = ret1 ^ pair_delta
            if ret2 not in runtime_return_set:
                continue
            candidates.append((ret1, ret2, enc1 ^ ret1))
        candidate_counts.append(len(candidates))
        if not candidates:
            no_match += 1
        elif len(candidates) == 1:
            unique += 1
        else:
            ambiguous += 1

        ctx_pc = parse_int(sample.get("ctx_pc", 0))
        ctx_pc_func = function_lookup(ranges, starts, ctx_pc - slide)
        reduced = []
        if ctx_pc_func is not None:
            for ret1, ret2, key in candidates:
                func1 = function_lookup(ranges, starts, ret1 - slide)
                func2 = function_lookup(ranges, starts, ret2 - slide)
                if (func1 and func1.name == ctx_pc_func.name) or (func2 and func2.name == ctx_pc_func.name):
                    reduced.append((ret1, ret2, key))
        reduced_counts.append(len(reduced))
        if len(reduced) == 1:
            same_function_context_unique += 1
        if len(rows) < MAX_EXAMPLES:
            example_candidates = reduced[:4] if reduced else candidates[:4]
            rows.append({
                "index": index,
                "pid": sample.get("pid"),
                "comm": sample.get("comm"),
                "ctx_pc_function": None if ctx_pc_func is None else ctx_pc_func.name,
                "encoded_1": hex64(enc1),
                "encoded_2": hex64(enc2),
                "candidate_count": len(candidates),
                "same_function_reduced_count": len(reduced),
                "examples": [
                    {
                        "key": hex64(key),
                        "decoded_1": hex64(ret1),
                        "decoded_2": hex64(ret2),
                        "decoded_1_static": hex64(ret1 - slide),
                        "decoded_2_static": hex64(ret2 - slide),
                        "decoded_1_symbol": None if function_lookup(ranges, starts, ret1 - slide) is None else function_lookup(ranges, starts, ret1 - slide).name,
                        "decoded_2_symbol": None if function_lookup(ranges, starts, ret2 - slide) is None else function_lookup(ranges, starts, ret2 - slide).name,
                    }
                    for ret1, ret2, key in example_candidates
                ],
            })
    return {
        "tested_samples": tested,
        "unique_samples": unique,
        "ambiguous_samples": ambiguous,
        "no_match_samples": no_match,
        "same_function_context_unique_samples": same_function_context_unique,
        "candidate_count_min": min(candidate_counts) if candidate_counts else None,
        "candidate_count_median": sorted(candidate_counts)[len(candidate_counts) // 2] if candidate_counts else None,
        "candidate_count_max": max(candidate_counts) if candidate_counts else None,
        "reduced_count_min": min(reduced_counts) if reduced_counts else None,
        "reduced_count_median": sorted(reduced_counts)[len(reduced_counts) // 2] if reduced_counts else None,
        "reduced_count_max": max(reduced_counts) if reduced_counts else None,
        "accepted_exact_unwind": unique > 0 and ambiguous == 0 and no_match == 0,
        "reason": "saved FP LR decode still needs extra key/stack constraints"
        if ambiguous or no_match else
        "saved FP LR decode produced unique candidates",
        "preview": rows,
    }


def render_report(result: dict[str, Any]) -> str:
    live = result["live_resymbolization"]
    ropp = result["ropp_decode"]
    lines = [
        "# Native Init V2217 Exact Slide Resymbolization Audit",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Exact slide: `{result['exact_slide_hex']}`",
        f"- Live PC resolved: `{live['pc_resolved']}` / `{live['sample_count']}`",
        f"- Live LR resolved: `{live['lr_resolved']}` / `{live['sample_count']}`",
        f"- Live LR callsite: `{live['lr_callsite']}` / `{live['sample_count']}`",
        f"- ROPP exact unwind accepted: `{str(ropp['accepted_exact_unwind']).lower()}`",
        "",
        "## Live Register Resymbolization",
        "",
        "| Source | Top Symbols |",
        "| --- | --- |",
        f"| `ctx_pc` | {', '.join(f'{name}:{count}' for name, count in live['pc_top_symbols'][:12])} |",
        f"| `ctx_lr` | {', '.join(f'{name}:{count}' for name, count in live['lr_top_symbols'][:12])} |",
        "",
        "| Index | PID | Comm | PC Symbol | PC Offset | LR Symbol | LR Offset | LR Callsite | LR Prev Insn |",
        "| ---: | ---: | --- | --- | ---: | --- | ---: | --- | --- |",
    ]
    for row in live["preview"][:12]:
        lines.append(
            f"| {row['index']} | {row.get('pid')} | `{row.get('comm')}` | "
            f"`{row.get('ctx_pc_symbol')}` | `{row.get('ctx_pc_offset')}` | "
            f"`{row.get('ctx_lr_symbol')}` | `{row.get('ctx_lr_offset')}` | "
            f"`{str(row.get('ctx_lr_callsite')).lower()}` | `{row.get('ctx_lr_prev_insn_kind')}` |"
        )
    lines.extend([
        "",
        "## ROPP Decode Attempt",
        "",
        f"- Tested samples: `{ropp['tested_samples']}`",
        f"- Unique samples: `{ropp['unique_samples']}`",
        f"- Ambiguous samples: `{ropp['ambiguous_samples']}`",
        f"- No-match samples: `{ropp['no_match_samples']}`",
        f"- Same-function reduced unique samples: `{ropp['same_function_context_unique_samples']}`",
        f"- Candidate min/median/max: `{ropp['candidate_count_min']}` / `{ropp['candidate_count_median']}` / `{ropp['candidate_count_max']}`",
        f"- Reduced min/median/max: `{ropp['reduced_count_min']}` / `{ropp['reduced_count_median']}` / `{ropp['reduced_count_max']}`",
        f"- Reason: {ropp['reason']}",
        "",
        "| Index | PID | Comm | Context Function | Candidates | Reduced | Encoded LR1 | Encoded LR2 |",
        "| ---: | ---: | --- | --- | ---: | ---: | --- | --- |",
    ])
    for row in ropp["preview"][:12]:
        lines.append(
            f"| {row['index']} | {row.get('pid')} | `{row.get('comm')}` | "
            f"`{row.get('ctx_pc_function')}` | {row['candidate_count']} | "
            f"{row['same_function_reduced_count']} | `{row['encoded_1']}` | `{row['encoded_2']}` |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- V2217 uses the V2216 codeword-matched slide, not V2215's rank-only slide.",
        "- Live `ctx_pc`/`ctx_lr` are now exact symbol+offset observations for this boot.",
        "- Saved FP-chain LR decoding remains unresolved when only pair-XOR and dense callsite constraints are used.",
        "- The next useful constraint is a real ROPP key source, stacktrace decoder behavior, or a narrower same-function live probe.",
        "",
        "## Evidence",
        "",
        f"- V2216 summary: `{result['inputs']['v2216_summary']}`",
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
    parser.add_argument("--v2216-summary", type=Path, default=DEFAULT_V2216_SUMMARY)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--kernel-raw", type=Path, default=DEFAULT_KERNEL_RAW)
    parser.add_argument("--stock-meta", type=Path, default=DEFAULT_STOCK_META)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = json.loads(args.v2216_summary.read_text())
    samples = summary["probe"]["samples"]
    slide = extract_exact_slide(summary)
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

    live = resymbolize_live_regs(samples, slide, ranges, starts, callsites, raw, synthetic_base)
    ropp = ropp_decode_attempt(samples, slide, callsites, raw, synthetic_base, ranges, starts)
    decision = (
        "v2217-live-resymbolized-ropp-still-ambiguous"
        if not ropp["accepted_exact_unwind"] else
        "v2217-live-resymbolized-ropp-decoded"
    )
    result = {
        "decision": decision,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "out_dir": rel(out_dir),
        "exact_slide": slide,
        "exact_slide_hex": hex_signed(slide),
        "inputs": {
            "v2216_summary": rel(args.v2216_summary),
            "system_map": rel(args.system_map),
            "kernel_raw": rel(args.kernel_raw),
            "stock_meta": rel(args.stock_meta),
        },
        "live_resymbolization": live,
        "ropp_decode": ropp,
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
        "decision": decision,
        "exact_slide": hex_signed(slide),
        "pc_resolved": live["pc_resolved"],
        "lr_resolved": live["lr_resolved"],
        "lr_callsite": live["lr_callsite"],
        "ropp_accepted": ropp["accepted_exact_unwind"],
        "out_dir": rel(out_dir),
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
