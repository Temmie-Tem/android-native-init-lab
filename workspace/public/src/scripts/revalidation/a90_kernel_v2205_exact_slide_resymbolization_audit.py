#!/usr/bin/env python3
"""Audit V2195/V2202 symbolization under the V2204 exact fops slide.

V2204 proved a clean file_operations object slide from `/dev/null` and
`/dev/zero`.  This host-only audit applies that exact fops/object slide to older
raw stack and timer pointers, then records whether it can be promoted to a
universal text symbolization slide.

No device access is required.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_KERNEL_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_SYSTEM_MAP = PRIVATE_KERNEL_RUNS / "v2197-stock-kallsyms/System.map"
DEFAULT_V2195_STACK_REPORT = REPO_ROOT / "docs/reports/NATIVE_INIT_V2195_STACKMAP_DUMP_LIVE_2026-06-11.md"
DEFAULT_V2197_SYMBOLIZATION = PRIVATE_KERNEL_RUNS / "v2197-stock-kallsyms/symbolization.json"
DEFAULT_V2202_SUMMARY = PRIVATE_KERNEL_RUNS / "v2202-timer-object-histogram-20260612-010308/summary.json"
DEFAULT_V2203_RESULT = PRIVATE_KERNEL_RUNS / "v2203-timer-row-source-matcher/result.json"
DEFAULT_V2204_SUMMARY = PRIVATE_KERNEL_RUNS / "v2204-file-ops-anchor-20260612-012852/summary.json"
DEFAULT_OUT_DIR = PRIVATE_KERNEL_RUNS / "v2205-exact-slide-resymbolization-audit"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2205_EXACT_SLIDE_RESYMBOLIZATION_AUDIT_2026-06-12.md"

STACK_IP_RE = re.compile(r"stack_ip(?:\s+rank=\d+)?\s+index=(?P<index>\d+)\s+value=0x(?P<addr>[0-9a-fA-F]+)")
SCHEDULE_HINT_RE = re.compile(r"(sched|schedule|switch|perf_trace_sched|trace_event_raw_event_sched)", re.IGNORECASE)
TIMER_HINT_RE = re.compile(r"(timer|timeout|jiffies|work|rcu|hrtimer|watchdog)", re.IGNORECASE)


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


def signed_hex(value: int) -> str:
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


def nearest_symbol(symbols: list[Symbol], addresses: list[int], address: int) -> dict[str, Any] | None:
    index = bisect.bisect_right(addresses, address) - 1
    if index < 0:
        return None
    symbol = symbols[index]
    next_address = symbols[index + 1].address if index + 1 < len(symbols) else None
    return {
        "symbol": symbol.name,
        "kind": symbol.kind,
        "symbol_address": f"0x{symbol.address:016x}",
        "offset": address - symbol.address,
        "next_delta": None if next_address is None else next_address - address,
    }


def symbolize_runtime(runtime: int, slide: int, symbols: list[Symbol], addresses: list[int]) -> dict[str, Any]:
    static = runtime - slide
    mapping = nearest_symbol(symbols, addresses, static)
    row: dict[str, Any] = {
        "runtime": f"0x{runtime:016x}",
        "static": f"0x{static:016x}",
        "mapped": mapping is not None,
    }
    if mapping:
        row.update(mapping)
    return row


def parse_stack_ips(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in STACK_IP_RE.finditer(path.read_text(errors="replace")):
        rows.append({
            "index": int(match.group("index"), 10),
            "runtime": int(match.group("addr"), 16),
        })
    unique: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for row in rows:
        key = (row["index"], row["runtime"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def load_exact_slide(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    analysis = data.get("analysis") or {}
    slide = analysis.get("best_slide")
    if slide is None:
        raise ValueError(f"missing V2204 best_slide in {path}")
    return {
        "slide": int(slide),
        "slide_hex": analysis.get("best_slide_hex") or signed_hex(int(slide)),
        "sources": analysis.get("best_sources") or [],
        "summary": data,
    }


def map_v2195_stack(path: Path, slide: int, symbols: list[Symbol], addresses: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in parse_stack_ips(path):
        mapping = symbolize_runtime(item["runtime"], slide, symbols, addresses)
        mapping["index"] = item["index"]
        symbol = str(mapping.get("symbol") or "")
        mapping["schedule_hint"] = bool(SCHEDULE_HINT_RE.search(symbol))
        rows.append(mapping)
    return rows


def map_v2202_rows(path: Path, slide: int, symbols: list[Symbol], addresses: list[int]) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    rows: list[dict[str, Any]] = []
    for source in (data.get("histogram") or {}).get("rows") or []:
        function = int(str(source["function"]), 16)
        mapped_function = symbolize_runtime(function, slide, symbols, addresses)
        symbol = str(mapped_function.get("symbol") or "")
        mapped_stacks: list[dict[str, Any]] = []
        for stack in source.get("stack_ips") or []:
            runtime = int(str(stack["value"]), 16)
            mapped = symbolize_runtime(runtime, slide, symbols, addresses)
            mapped["index"] = stack.get("index")
            mapped_stacks.append(mapped)
        rows.append({
            "rank": source.get("rank"),
            "comm": source.get("comm"),
            "count": source.get("count"),
            "timeout_min": source.get("timeout_min"),
            "timeout_max": source.get("timeout_max"),
            "timeout_avg": source.get("timeout_avg"),
            "obj_data_delta": source.get("obj_data_delta"),
            "runtime_function": source.get("function"),
            "mapped_function": mapped_function,
            "timer_hint": bool(TIMER_HINT_RE.search(symbol)),
            "mapped_stack_ips": mapped_stacks,
        })
    return rows


def load_legacy_context(v2197_path: Path, v2203_path: Path, exact_slide: int) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if v2197_path.exists():
        data = json.loads(v2197_path.read_text())
        top = data.get("top_slide_candidates") or []
        context["v2197_top_slides"] = [
            {
                "slide_hex": item.get("slide_hex"),
                "slide": item.get("slide"),
                "source": item.get("source"),
                "stack_score": item.get("stack_score"),
                "stack_total": item.get("stack_total"),
            }
            for item in top[:5]
        ]
        if top and top[0].get("slide") is not None:
            context["exact_minus_v2197_top"] = exact_slide - int(top[0]["slide"])
            context["exact_minus_v2197_top_hex"] = signed_hex(context["exact_minus_v2197_top"])
    if v2203_path.exists():
        data = json.loads(v2203_path.read_text())
        context["v2203_decision"] = data.get("decision")
        context["v2203_reason"] = data.get("reason")
        top = data.get("top_candidates") or []
        context["v2203_top_candidate"] = top[0] if top else None
    return context


def classify_result(v2195_stack: list[dict[str, Any]], v2202_rows: list[dict[str, Any]]) -> tuple[str, str]:
    schedule_hints = sum(1 for row in v2195_stack if row.get("schedule_hint"))
    dominant = v2202_rows[0] if v2202_rows else {}
    dominant_symbol = (((dominant.get("mapped_function") or {}).get("symbol")) or "")
    dominant_timer_hint = bool(dominant.get("timer_hint"))
    if schedule_hints == 0 and not dominant_timer_hint:
        return (
            "v2205-fops-slide-not-universal-text-slide",
            "V2204 fops slide maps clean rodata anchors, but maps existing stack/timer text pointers to semantically implausible symbols.",
        )
    return (
        "v2205-fops-slide-text-audit-needs-review",
        f"V2204 fops slide produced {schedule_hints} schedule-like V2195 stack frames and dominant timer symbol {dominant_symbol!r}.",
    )


def render_markdown(result: dict[str, Any]) -> str:
    exact = result["v2204_exact_slide"]
    lines = [
        "# Native Init V2205 Exact-Slide Resymbolization Audit",
        "",
        "## Decision",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Reason: {result['reason']}",
        f"- V2204 fops/object slide: `{exact['slide_hex']}`",
        f"- V2204 sources: `{', '.join(exact['sources'])}`",
        "",
        "## Interpretation",
        "",
        "- V2204 remains valid as a clean object/rodata anchor: `/dev/null` and `/dev/zero` f_op pointers agree.",
        "- V2205 blocks promoting that value to a universal text-stack symbolization slide.",
        "- Existing raw text-like values still need a text-side anchor or CFP/JOPP/ROPP decode layer before assigning final function names.",
        "",
        "## V2195 Stack Under V2204 Slide",
        "",
        "| Index | Runtime IP | Static Address | Symbol | Offset | Schedule-like |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in result["v2195_stack_exact_slide"]:
        lines.append(
            f"| {row['index']} | `{row['runtime']}` | `{row['static']}` | "
            f"`{row.get('symbol', 'unmapped')}` | `{row.get('offset', '')}` | `{str(row.get('schedule_hint')).lower()}` |"
        )
    lines.extend([
        "",
        "## V2202 Timer Rows Under V2204 Slide",
        "",
        "| Rank | Comm | Count | Runtime Function | Static Symbol | Offset | Timer-like |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in result["v2202_timer_rows_exact_slide"][:12]:
        mapped = row["mapped_function"]
        lines.append(
            f"| {row['rank']} | `{row['comm']}` | {row['count']} | `{row['runtime_function']}` | "
            f"`{mapped.get('symbol', 'unmapped')}` | `{mapped.get('offset', '')}` | `{str(row.get('timer_hint')).lower()}` |"
        )
    legacy = result.get("legacy_context") or {}
    lines.extend([
        "",
        "## Legacy Context",
        "",
        f"- V2197 top text-candidate delta from V2204: `{legacy.get('exact_minus_v2197_top_hex')}`",
        f"- V2203 decision: `{legacy.get('v2203_decision')}`",
        f"- V2203 reason: {legacy.get('v2203_reason')}",
        "",
        "## Next",
        "",
        "- Build a text-side anchor, preferably by extending the file-ops path to read known fops member function pointers.",
        "- Treat fops object addresses and stack/timer text addresses as separate interpretation layers until that anchor converges.",
        "",
        "## Evidence",
        "",
    ])
    for key, value in result["inputs"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-map", type=Path, default=DEFAULT_SYSTEM_MAP)
    parser.add_argument("--v2195-stack-report", type=Path, default=DEFAULT_V2195_STACK_REPORT)
    parser.add_argument("--v2197-symbolization", type=Path, default=DEFAULT_V2197_SYMBOLIZATION)
    parser.add_argument("--v2202-summary", type=Path, default=DEFAULT_V2202_SUMMARY)
    parser.add_argument("--v2203-result", type=Path, default=DEFAULT_V2203_RESULT)
    parser.add_argument("--v2204-summary", type=Path, default=DEFAULT_V2204_SUMMARY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    symbols = parse_system_map(args.system_map)
    addresses = [symbol.address for symbol in symbols]
    exact = load_exact_slide(args.v2204_summary)
    slide = int(exact["slide"])
    v2195_stack = map_v2195_stack(args.v2195_stack_report, slide, symbols, addresses)
    v2202_rows = map_v2202_rows(args.v2202_summary, slide, symbols, addresses)
    legacy = load_legacy_context(args.v2197_symbolization, args.v2203_result, slide)
    decision, reason = classify_result(v2195_stack, v2202_rows)

    result = {
        "decision": decision,
        "reason": reason,
        "inputs": {
            "system_map": rel(args.system_map),
            "v2195_stack_report": rel(args.v2195_stack_report),
            "v2197_symbolization": rel(args.v2197_symbolization),
            "v2202_summary": rel(args.v2202_summary),
            "v2203_result": rel(args.v2203_result),
            "v2204_summary": rel(args.v2204_summary),
        },
        "v2204_exact_slide": {
            "slide": slide,
            "slide_hex": exact["slide_hex"],
            "sources": exact["sources"],
        },
        "v2195_stack_exact_slide": v2195_stack,
        "v2202_timer_rows_exact_slide": v2202_rows,
        "legacy_context": legacy,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.out_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_markdown(result))
    print(json.dumps({
        "decision": decision,
        "reason": reason,
        "slide": exact["slide_hex"],
        "v2195_schedule_hints": sum(1 for row in v2195_stack if row.get("schedule_hint")),
        "v2202_top_symbol": ((v2202_rows[0]["mapped_function"].get("symbol")) if v2202_rows else None),
        "out_json": rel(result_path),
        "report": rel(args.report),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
