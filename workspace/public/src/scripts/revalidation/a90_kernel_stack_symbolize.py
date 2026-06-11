#!/usr/bin/env python3
"""Symbolize A90 BPF stackmap IPs against a candidate kernel System.map."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


STACK_IP_RE = re.compile(r"stack_ip\s+index=(?P<index>\d+)\s+value=0x(?P<addr>[0-9a-fA-F]+)")
TIMER_VALUE_RE = re.compile(r"value=(?P<addr>\d+)\s+count=(?P<count>\d+)")


DEFAULT_CANDIDATE_SYMBOLS = (
    "__schedule",
    "schedule",
    "finish_task_switch",
    "trace_call_bpf",
    "bpf_get_stackid",
    "perf_trace_sched_switch",
    "trace_event_raw_event_sched_switch",
)

TIMER_NAME_HINT_RE = re.compile(
    r"(timer|timeout|delayed_work|watchdog|hrtimer|tick|process_times|scheduler|work)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Symbol:
    address: int
    kind: str
    name: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_int(value: str) -> int:
    value = value.strip()
    if value.lower().startswith("0x"):
        return int(value, 16)
    return int(value, 10)


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
        kind = parts[1]
        name = parts[2]
        if address >= 0xFFFFFF8000000000 and kind.lower() in {"t", "w"}:
            symbols.append(Symbol(address, kind, name))
    symbols.sort(key=lambda symbol: symbol.address)
    return symbols


def nearest_symbol(symbols: list[Symbol], addresses: list[int], address: int) -> dict[str, object] | None:
    index = bisect.bisect_right(addresses, address) - 1
    if index < 0:
        return None
    symbol = symbols[index]
    next_address = symbols[index + 1].address if index + 1 < len(symbols) else None
    return {
        "address": f"0x{address:016x}",
        "symbol_address": f"0x{symbol.address:016x}",
        "symbol": symbol.name,
        "kind": symbol.kind,
        "offset": address - symbol.address,
        "next_delta": None if next_address is None else next_address - address,
        "inside_known_extent": next_address is None or address < next_address,
    }


def parse_stack_log(path: Path) -> list[int]:
    ips: list[int] = []
    for line in path.read_text(errors="replace").splitlines():
        match = STACK_IP_RE.search(line)
        if match:
            ips.append(int(match.group("addr"), 16))
    return ips


def parse_timer_log(path: Path) -> list[dict[str, int]]:
    values: list[dict[str, int]] = []
    for line in path.read_text(errors="replace").splitlines():
        match = TIMER_VALUE_RE.search(line)
        if match:
            values.append({
                "address": int(match.group("addr"), 10) & ((1 << 64) - 1),
                "count": int(match.group("count"), 10),
            })
    return values


def build_symbol_index(symbols: list[Symbol]) -> dict[str, int]:
    index: dict[str, int] = {}
    for symbol in symbols:
        index.setdefault(symbol.name, symbol.address)
    return index


def candidate_slides(stack_ips: list[int], symbol_index: dict[str, int], names: list[str]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for stack_ip in stack_ips:
        for name in names:
            symbol_address = symbol_index.get(name)
            if symbol_address is None:
                continue
            slide = stack_ip - symbol_address
            if -0x8000000 <= slide <= 0x8000000:
                candidates.append({
                    "slide": slide,
                    "source_ip": f"0x{stack_ip:016x}",
                    "source_symbol": name,
                    "source_symbol_address": f"0x{symbol_address:016x}",
                })
    unique: dict[int, dict[str, object]] = {}
    for candidate in candidates:
        unique.setdefault(int(candidate["slide"]), candidate)
    return list(unique.values())


def score_slide(symbols: list[Symbol],
                addresses: list[int],
                slide: int,
                stack_ips: list[int],
                timer_functions: list[dict[str, int]],
                source: dict[str, object] | None = None) -> dict[str, object]:
    stack_mappings = []
    timer_mappings = []
    stack_score = 0
    timer_score = 0
    timer_entry_score = 0
    timer_near_entry_score = 0
    timer_name_hint_score = 0
    for stack_ip in stack_ips:
        static_address = stack_ip - slide
        mapping = nearest_symbol(symbols, addresses, static_address)
        if mapping is None:
            stack_mappings.append({"runtime": f"0x{stack_ip:016x}", "static": f"0x{static_address:016x}", "mapped": False})
            continue
        mapping["runtime"] = f"0x{stack_ip:016x}"
        mapping["static"] = f"0x{static_address:016x}"
        stack_mappings.append(mapping)
        offset = int(mapping["offset"])
        next_delta = mapping["next_delta"]
        if 0 <= offset < 0x4000 and (next_delta is None or int(next_delta) >= 0):
            stack_score += 1
    for timer in timer_functions:
        runtime_address = int(timer["address"])
        static_address = runtime_address - slide
        mapping = nearest_symbol(symbols, addresses, static_address)
        if mapping is None:
            timer_mappings.append({
                "runtime": f"0x{runtime_address:016x}",
                "count": timer["count"],
                "static": f"0x{static_address:016x}",
                "mapped": False,
            })
            continue
        mapping["runtime"] = f"0x{runtime_address:016x}"
        mapping["count"] = timer["count"]
        mapping["static"] = f"0x{static_address:016x}"
        timer_mappings.append(mapping)
        offset = int(mapping["offset"])
        next_delta = mapping["next_delta"]
        if 0 <= offset < 0x4000 and (next_delta is None or int(next_delta) >= 0):
            timer_score += int(timer["count"])
        if offset == 0:
            timer_entry_score += int(timer["count"])
        if 0 <= offset < 0x100:
            timer_near_entry_score += int(timer["count"])
        if TIMER_NAME_HINT_RE.search(str(mapping["symbol"])):
            timer_name_hint_score += int(timer["count"])
    return {
        "slide": slide,
        "slide_hex": f"0x{slide:x}",
        "source": source or {},
        "stack_score": stack_score,
        "stack_total": len(stack_ips),
        "timer_weighted_score": timer_score,
        "timer_weight_total": sum(int(item["count"]) for item in timer_functions),
        "timer_entry_weighted_score": timer_entry_score,
        "timer_near_entry_weighted_score": timer_near_entry_score,
        "timer_name_hint_weighted_score": timer_name_hint_score,
        "stack_mappings": stack_mappings,
        "timer_mappings": timer_mappings,
    }


def render_markdown(result: dict[str, object]) -> str:
    lines = [
        "# A90 Kernel Stack Symbolization Result",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Exact symbolization: `{str(result['exact_symbolization']).lower()}`",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
    ]
    for key, value in result["inputs"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Kernel Hash Comparison", ""])
    comparison = result.get("kernel_hash_comparison") or {}
    for key, value in comparison.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Raw Stack IPs", ""])
    for item in result["raw_stack_ips"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Timer Function Anchors", ""])
    for item in result["timer_functions"]:
        lines.append(f"- `{item['address_hex']}` count={item['count']}")
    lines.extend(["", "## Top Slide Candidates", ""])
    for candidate in result["top_slide_candidates"]:
        lines.append(
            f"- slide `{candidate['slide_hex']}`: stack "
            f"{candidate['stack_score']}/{candidate['stack_total']}, timer "
            f"{candidate['timer_weighted_score']}/{candidate['timer_weight_total']}"
        )
        if candidate.get("source"):
            source = candidate["source"]
            lines.append(
                f"  - source: `{source.get('source_symbol', 'unknown')}` from "
                f"`{source.get('source_ip', 'unknown')}`"
            )
        lines.append(
            f"  - timer_entry: {candidate.get('timer_entry_weighted_score', 0)}/"
            f"{candidate['timer_weight_total']}, timer_near_entry: "
            f"{candidate.get('timer_near_entry_weighted_score', 0)}/"
            f"{candidate['timer_weight_total']}, timer_name_hint: "
            f"{candidate.get('timer_name_hint_weighted_score', 0)}/"
            f"{candidate['timer_weight_total']}"
        )
        for mapping in candidate["stack_mappings"][:6]:
            lines.append(
                f"  - `{mapping.get('runtime')}` -> `{mapping.get('symbol', 'unmapped')}`"
                f"+0x{int(mapping.get('offset', 0)):x}"
            )
    ambiguity = result.get("ambiguity") or {}
    if ambiguity:
        lines.extend(["", "## Ambiguity", ""])
        for key, value in ambiguity.items():
            lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-map", type=Path, required=True)
    parser.add_argument("--stack-log", type=Path, action="append", default=[])
    parser.add_argument("--timer-log", type=Path, action="append", default=[])
    parser.add_argument("--stack-ip", action="append", default=[])
    parser.add_argument("--timer-function", action="append", default=[], help="ADDR[:COUNT], decimal or hex")
    parser.add_argument("--candidate-symbol", action="append", default=[])
    parser.add_argument("--live-kernel", type=Path)
    parser.add_argument("--candidate-image", type=Path)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args()

    symbols = parse_system_map(args.system_map)
    addresses = [symbol.address for symbol in symbols]
    symbol_index = build_symbol_index(symbols)
    stack_ips = [parse_int(value) for value in args.stack_ip]
    for path in args.stack_log:
        stack_ips.extend(parse_stack_log(path))
    timer_functions = []
    for path in args.timer_log:
        timer_functions.extend(parse_timer_log(path))
    for value in args.timer_function:
        raw_address, _, raw_count = value.partition(":")
        timer_functions.append({"address": parse_int(raw_address), "count": int(raw_count or "1")})
    timer_functions = [
        {"address": item["address"], "address_hex": f"0x{item['address']:016x}", "count": item["count"]}
        for item in timer_functions
    ]
    candidate_names = list(DEFAULT_CANDIDATE_SYMBOLS)
    candidate_names.extend(args.candidate_symbol)
    candidates = candidate_slides(stack_ips, symbol_index, candidate_names)
    candidates.append({"slide": 0, "source_ip": "manual", "source_symbol": "identity", "source_symbol_address": "0x0"})
    scored = [
        score_slide(symbols, addresses, int(candidate["slide"]), stack_ips, timer_functions, candidate)
        for candidate in candidates
    ]
    scored.sort(
        key=lambda item: (
            int(item["stack_score"]),
            int(item["timer_entry_weighted_score"]),
            int(item["timer_near_entry_weighted_score"]),
            int(item["timer_weighted_score"]),
        ),
        reverse=True,
    )
    comparison = {}
    if args.live_kernel and args.candidate_image:
        comparison = {
            "live_kernel": str(args.live_kernel),
            "live_kernel_sha256": sha256(args.live_kernel),
            "candidate_image": str(args.candidate_image),
            "candidate_image_sha256": sha256(args.candidate_image),
        }
        comparison["hash_match"] = str(comparison["live_kernel_sha256"] == comparison["candidate_image_sha256"]).lower()
    exact = False
    reason = "candidate System.map is not proven to match the live boot kernel"
    full_stack_candidate_count = sum(1 for item in scored if item["stack_score"] == len(stack_ips))
    best = scored[0] if scored else None
    if comparison and comparison.get("hash_match") == "true":
        if best and best["stack_score"] == best["stack_total"]:
            exact = True
            reason = (
                "candidate kernel hash matches live boot kernel and all stack IPs map under one "
                "stack-context slide"
            )
        else:
            reason = "kernel hash matches but no single candidate slide maps all stack IPs"
    decision = "kernel-stack-symbolization-pass" if exact else "kernel-stack-symbolization-blocked-no-matching-symbol-map"
    result = {
        "decision": decision,
        "exact_symbolization": exact,
        "reason": reason,
        "inputs": {
            "system_map": str(args.system_map),
            "stack_logs": [str(path) for path in args.stack_log],
            "timer_logs": [str(path) for path in args.timer_log],
        },
        "kernel_hash_comparison": comparison,
        "symbol_count": len(symbols),
        "raw_stack_ips": [f"0x{value:016x}" for value in stack_ips],
        "timer_functions": timer_functions,
        "top_slide_candidates": scored[:10],
        "ambiguity": {
            "full_stack_candidate_count": full_stack_candidate_count,
            "best_timer_entry_weighted_score": 0 if best is None else best["timer_entry_weighted_score"],
            "best_timer_near_entry_weighted_score": 0 if best is None else best["timer_near_entry_weighted_score"],
            "best_timer_name_hint_weighted_score": 0 if best is None else best["timer_name_hint_weighted_score"],
            "timer_functions_are_slide_authority": (
                "true" if best and best["timer_entry_weighted_score"] == best["timer_weight_total"] else "false"
            ),
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_markdown(result))
    print(json.dumps({
        "decision": decision,
        "exact_symbolization": exact,
        "reason": reason,
        "out_json": str(args.out_json),
        "out_md": str(args.out_md) if args.out_md else None,
    }, indent=2, sort_keys=True))
    return 0 if exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
