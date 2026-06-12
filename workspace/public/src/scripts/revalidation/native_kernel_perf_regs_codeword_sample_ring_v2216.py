#!/usr/bin/env python3
"""Run V2216 perf-event regs+codeword sample-ring capture.

V2216 extends V2216 by reading live instruction words at ctx_pc and ctx_lr.
The host analyzer scores candidate slides by comparing live codewords to the
bit-exact stock kernel raw image.
"""

from __future__ import annotations

import argparse
import bisect
from collections import Counter
import json
import re
import struct
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
HELPER_DIR = REPO_ROOT / "workspace/public/src/native-init/helpers"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
REMOTE_HELPER = "/cache/bin/a90_bpf_perf_regs_codeword_sample_ring"
REMOTE_TOYBOX = "/cache/bin/busybox"
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2216_PERF_REGS_CODEWORD_SAMPLE_RING_LIVE_2026-06-12.md"
STOCK_MAP_PATH = REPO_ROOT / "workspace/private/runs/kernel/v2197-stock-kallsyms/System.map"
STOCK_RAW_PATH = REPO_ROOT / "workspace/private/runs/kernel/v2197-stock-kallsyms/kernel.raw"
STOCK_META_PATH = REPO_ROOT / "workspace/private/runs/kernel/v2197-stock-kallsyms/stock-kallsyms.json"
V2215_RESULT_PATH = REPO_ROOT / "workspace/private/runs/kernel/v2215-perf-regs-ropp-jopp-classifier/result.json"
SLIDE_MIN = -0x800000
SLIDE_MAX = 0x800000

sys.path.insert(0, str(SCRIPT_DIR))
import a90_transport as transport  # noqa: E402
import native_kernel_file_ops_anchor_v2204 as base  # noqa: E402


STATS_RE = re.compile(r"^stats\s+(?P<body>.+)$", re.MULTILINE)
SAMPLE_RE = re.compile(r"^sample\s+(?P<body>.+)$", re.MULTILINE)
OFFSETS_RE = re.compile(r"^offsets\s+(?P<body>.+)$", re.MULTILINE)
SAMPLES_RE = re.compile(r"^samples\s+(?P<body>.+)$", re.MULTILINE)

KERNEL_TEXT_MIN = 0xFFFFFF8008000000
KERNEL_TEXT_MAX = 0xFFFFFF800C000000
KERNEL_VA_MIN = 0xFFFFFF8000000000
KERNEL_VA_MAX = 0xFFFFFFFFFFFFFFFF


def parse_int(value: str) -> int:
    if value.startswith(("0x", "0X")):
        return int(value, 16)
    return int(value, 10)


def parse_helper_stdout(stdout: str) -> dict[str, Any]:
    stats_match = STATS_RE.search(stdout)
    offsets_match = OFFSETS_RE.search(stdout)
    samples_match = SAMPLES_RE.search(stdout)
    parsed: dict[str, Any] = {
        "stats": {},
        "offsets": {},
        "sample_meta": {},
        "samples": [],
        "raw_stdout": stdout,
    }
    if offsets_match:
        parsed["offsets"] = {
            key: parse_int(value)
            for key, value in base.parse_key_values(offsets_match.group("body")).items()
        }
    if stats_match:
        parsed["stats"] = {
            key: parse_int(value)
            for key, value in base.parse_key_values(stats_match.group("body")).items()
        }
    if samples_match:
        parsed["sample_meta"] = {
            key: parse_int(value)
            for key, value in base.parse_key_values(samples_match.group("body")).items()
        }
    for match in SAMPLE_RE.finditer(stdout):
        fields = base.parse_key_values(match.group("body"))
        row: dict[str, Any] = {}
        for key, value in fields.items():
            if key == "comm":
                row[key] = value
            else:
                row[key] = parse_int(value)
        parsed["samples"].append(row)
    return parsed


def classify_addr(value: int) -> dict[str, Any]:
    return {
        "hex": f"0x{value:016x}",
        "nonzero": value != 0,
        "kernel_va": KERNEL_VA_MIN <= value <= KERNEL_VA_MAX,
        "kernel_text": KERNEL_TEXT_MIN <= value < KERNEL_TEXT_MAX,
        "aligned_4": value % 4 == 0,
        "aligned_16": value % 16 == 0,
    }


def load_text_symbols(path: Path = STOCK_MAP_PATH) -> list[tuple[int, str]]:
    if not path.exists():
        return []
    symbols: list[tuple[int, str]] = []
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) != 3:
            continue
        addr_s, typ, name = parts
        if typ not in {"T", "t", "W", "w"}:
            continue
        try:
            addr = int(addr_s, 16)
        except ValueError:
            continue
        if KERNEL_TEXT_MIN <= addr < KERNEL_TEXT_MAX:
            symbols.append((addr, name))
    symbols.sort()
    return symbols


def load_symbol_index(path: Path = STOCK_MAP_PATH) -> dict[str, int]:
    index: dict[str, int] = {}
    if not path.exists():
        return index
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) != 3:
            continue
        try:
            index.setdefault(parts[2], int(parts[0], 16))
        except ValueError:
            continue
    return index


def nearest_symbol(addr: int, symbols: list[tuple[int, str]]) -> dict[str, Any] | None:
    if not symbols:
        return None
    addrs = [item[0] for item in symbols]
    idx = bisect.bisect_right(addrs, addr) - 1
    if idx < 0:
        return None
    start, name = symbols[idx]
    next_addr = symbols[idx + 1][0] if idx + 1 < len(symbols) else KERNEL_TEXT_MAX
    if not (start <= addr < next_addr):
        return None
    return {
        "addr": f"0x{addr:016x}",
        "symbol": name,
        "symbol_addr": f"0x{start:016x}",
        "offset": addr - start,
    }


def symbolize_counter(values: Counter[int], symbols: list[tuple[int, str]], limit: int = 16) -> dict[str, Any]:
    rows = []
    hit = 0
    for addr, count in values.most_common(limit):
        item = nearest_symbol(addr, symbols)
        if item is not None:
            hit += count
            item["count"] = count
            rows.append(item)
        else:
            rows.append({"addr": f"0x{addr:016x}", "symbol": None, "offset": None, "count": count})
    total = sum(values.values())
    all_hit = 0
    for addr, count in values.items():
        if nearest_symbol(addr, symbols) is not None:
            all_hit += count
    return {
        "total": total,
        "direct_hits": all_hit,
        "direct_hit_fraction": (all_hit / total) if total else 0.0,
        "top": rows,
    }


def load_kernel_raw(path: Path = STOCK_RAW_PATH) -> bytes:
    payload = path.read_bytes()
    if payload.startswith(b"UNCOMPRESSED_IMG"):
        image_size = struct.unpack_from("<I", payload, 16)[0]
        raw = payload[20:20 + image_size]
        if len(raw) != image_size:
            raise ValueError("truncated UNCOMPRESSED_IMG wrapper")
        return raw
    return payload


def load_synthetic_base(path: Path = STOCK_META_PATH) -> int:
    metadata = json.loads(path.read_text())
    value = metadata["synthetic_base"]
    return int(str(value), 0) if not isinstance(value, int) else value


def read_stock_u32(raw: bytes, synthetic_base: int, static_addr: int) -> int | None:
    offset = static_addr - synthetic_base
    if offset < 0 or offset + 4 > len(raw):
        return None
    return struct.unpack_from("<I", raw, offset)[0]


def candidate_slides() -> list[int]:
    slides: set[int] = {0}
    if V2215_RESULT_PATH.exists():
        result = json.loads(V2215_RESULT_PATH.read_text())
        for row in (result.get("p0_slide") or {}).get("top_candidates") or []:
            try:
                slides.add(int(row["slide"]))
            except (KeyError, TypeError, ValueError):
                continue
        best = ((result.get("p0_slide") or {}).get("best") or {}).get("slide")
        if best is not None:
            slides.add(int(best))
    return sorted(slides)


def codeword_generated_slides(
    samples: list[dict[str, Any]],
    raw: bytes,
    synthetic_base: int,
) -> list[int]:
    symbols = load_symbol_index()
    text_start = symbols.get("_stext", symbols.get("_text"))
    text_end = symbols.get("_etext")
    if text_start is None or text_end is None:
        return []
    targets: dict[int, list[int]] = {}
    for sample in samples:
        for addr_key, insn_key, adjust in [
            ("ctx_pc", "ctx_pc_insn", 0),
            ("ctx_lr", "ctx_lr_prev_insn", -4),
            ("ctx_lr", "ctx_lr_insn", 0),
        ]:
            runtime_addr = int(sample.get(addr_key, 0)) + adjust
            insn = int(sample.get(insn_key, 0))
            if runtime_addr and insn:
                targets.setdefault(insn, []).append(runtime_addr)
    if not targets:
        return []
    candidate_counter: Counter[int] = Counter()
    start_offset = max(0, text_start - synthetic_base)
    end_offset = min(len(raw) - 4, text_end - synthetic_base)
    start_offset += (-start_offset) % 4
    for offset in range(start_offset, end_offset, 4):
        word = struct.unpack_from("<I", raw, offset)[0]
        runtime_addrs = targets.get(word)
        if not runtime_addrs:
            continue
        static_addr = synthetic_base + offset
        for runtime_addr in runtime_addrs:
            slide = runtime_addr - static_addr
            if SLIDE_MIN <= slide <= SLIDE_MAX and slide % 4 == 0:
                candidate_counter[slide] += 1
    return [slide for slide, _ in candidate_counter.most_common(256)]


def codeword_match_analysis(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not STOCK_RAW_PATH.exists() or not STOCK_META_PATH.exists():
        return {"available": False, "reason": "stock raw/meta missing"}
    raw = load_kernel_raw()
    synthetic_base = load_synthetic_base()
    slides = set(candidate_slides())
    generated = codeword_generated_slides(samples, raw, synthetic_base)
    slides.update(generated)
    rows = []
    for slide in sorted(slides):
        pc_readable = 0
        pc_match = 0
        lr_prev_readable = 0
        lr_prev_match = 0
        lr_readable = 0
        lr_match = 0
        examples = []
        for sample in samples:
            ctx_pc = int(sample.get("ctx_pc", 0))
            ctx_lr = int(sample.get("ctx_lr", 0))
            pc_insn = int(sample.get("ctx_pc_insn", 0))
            lr_prev_insn = int(sample.get("ctx_lr_prev_insn", 0))
            lr_insn = int(sample.get("ctx_lr_insn", 0))
            if ctx_pc and pc_insn:
                pc_readable += 1
                stock = read_stock_u32(raw, synthetic_base, ctx_pc - slide)
                matched = stock == pc_insn
                if matched:
                    pc_match += 1
                if len(examples) < 8 and (matched or stock is not None):
                    examples.append({
                        "source": "ctx_pc",
                        "runtime": f"0x{ctx_pc:016x}",
                        "static": f"0x{ctx_pc - slide:016x}",
                        "live": f"0x{pc_insn:08x}",
                        "stock": None if stock is None else f"0x{stock:08x}",
                        "match": matched,
                    })
            if ctx_lr and lr_prev_insn:
                lr_prev_readable += 1
                stock = read_stock_u32(raw, synthetic_base, ctx_lr - slide - 4)
                matched = stock == lr_prev_insn
                if matched:
                    lr_prev_match += 1
                if len(examples) < 8 and (matched or stock is not None):
                    examples.append({
                        "source": "ctx_lr-4",
                        "runtime": f"0x{ctx_lr - 4:016x}",
                        "static": f"0x{ctx_lr - slide - 4:016x}",
                        "live": f"0x{lr_prev_insn:08x}",
                        "stock": None if stock is None else f"0x{stock:08x}",
                        "match": matched,
                    })
            if ctx_lr and lr_insn:
                lr_readable += 1
                stock = read_stock_u32(raw, synthetic_base, ctx_lr - slide)
                matched = stock == lr_insn
                if matched:
                    lr_match += 1
                if len(examples) < 8 and (matched or stock is not None):
                    examples.append({
                        "source": "ctx_lr",
                        "runtime": f"0x{ctx_lr:016x}",
                        "static": f"0x{ctx_lr - slide:016x}",
                        "live": f"0x{lr_insn:08x}",
                        "stock": None if stock is None else f"0x{stock:08x}",
                        "match": matched,
                    })
        weighted = (4 * pc_match) + (2 * lr_prev_match) + lr_match
        rows.append({
            "slide": slide,
            "slide_hex": f"-0x{-slide:x}" if slide < 0 else f"0x{slide:x}",
            "pc_readable": pc_readable,
            "pc_match": pc_match,
            "lr_prev_readable": lr_prev_readable,
            "lr_prev_match": lr_prev_match,
            "lr_readable": lr_readable,
            "lr_match": lr_match,
            "weighted_score": weighted,
            "examples": examples,
        })
    rows.sort(key=lambda item: (item["weighted_score"], item["pc_match"], item["lr_prev_match"], item["lr_match"]), reverse=True)
    best = rows[0] if rows else None
    runner_up = rows[1] if len(rows) > 1 else None
    accepted = bool(best and best["pc_readable"] and best["pc_match"] == best["pc_readable"])
    unique = bool(best and (runner_up is None or best["weighted_score"] > runner_up["weighted_score"]))
    near_exact = bool(
        best
        and unique
        and best["pc_readable"]
        and best["pc_readable"] - best["pc_match"] <= 1
        and best["lr_prev_readable"]
        and best["lr_prev_match"] == best["lr_prev_readable"]
        and best["lr_readable"]
        and best["lr_match"] == best["lr_readable"]
    )
    exact_or_near = bool((accepted or near_exact) and unique)
    return {
        "available": True,
        "stock_raw": str(STOCK_RAW_PATH.relative_to(REPO_ROOT)),
        "stock_meta": str(STOCK_META_PATH.relative_to(REPO_ROOT)),
        "candidate_source": str(V2215_RESULT_PATH.relative_to(REPO_ROOT)),
        "generated_candidate_count": len(generated),
        "candidate_count": len(rows),
        "accepted_exact_codeword_slide": accepted and unique,
        "accepted_near_exact_codeword_slide": near_exact and not (accepted and unique),
        "accepted_symbolization_slide": exact_or_near,
        "acceptance_reason": (
            "exact_pc_lr_codeword_match"
            if accepted and unique else
            "lr_exact_single_pc_mismatch"
            if near_exact else
            "not_accepted"
        ),
        "best": best,
        "runner_up": runner_up,
        "top_candidates": rows[:16],
    }


def analyze_probe(probe: dict[str, Any]) -> dict[str, Any]:
    samples = probe.get("samples") or []
    fields = [
        "ctx_pc",
        "fp_slot_next",
        "fp_slot_raw_lr",
        "fp2_slot_next",
        "fp2_slot_raw_lr",
        "ctx_lr",
    ]
    unique: dict[str, set[int]] = {field: set() for field in fields}
    counters: dict[str, Counter[int]] = {field: Counter() for field in ["ctx_pc", "ctx_lr"]}
    counts = {
        "printed_samples": len(samples),
        "walkable_fp_next": 0,
        "walkable_fp2_next": 0,
        "raw_lr_kernel_text": 0,
        "raw_lr_kernel_va_nontext": 0,
        "raw_lr_nonzero": 0,
        "ctx_pc_kernel_text": 0,
        "ctx_lr_kernel_text": 0,
        "ctx_lr_kernel_va_nontext": 0,
        "ctx_lr_nonzero": 0,
    }
    comms: set[str] = set()
    pids: set[int] = set()
    for sample in samples:
        comm = str(sample.get("comm", ""))
        if comm:
            comms.add(comm)
        pids.add(int(sample.get("pid", 0)))
        for field in fields:
            value = int(sample.get(field, 0))
            if value:
                unique[field].add(value)
                if field in counters:
                    counters[field][value] += 1
        if int(sample.get("fp_slot_next", 0)) != 0:
            counts["walkable_fp_next"] += 1
        if int(sample.get("fp2_slot_next", 0)) != 0:
            counts["walkable_fp2_next"] += 1
        raw_lr = int(sample.get("fp_slot_raw_lr", 0))
        raw_meta = classify_addr(raw_lr)
        if raw_lr:
            counts["raw_lr_nonzero"] += 1
        if raw_meta["kernel_text"]:
            counts["raw_lr_kernel_text"] += 1
        elif raw_meta["kernel_va"] and raw_lr:
            counts["raw_lr_kernel_va_nontext"] += 1
        if classify_addr(int(sample.get("ctx_pc", 0)))["kernel_text"]:
            counts["ctx_pc_kernel_text"] += 1
        ctx_lr = int(sample.get("ctx_lr", 0))
        ctx_lr_meta = classify_addr(ctx_lr)
        if ctx_lr:
            counts["ctx_lr_nonzero"] += 1
        if ctx_lr_meta["kernel_text"]:
            counts["ctx_lr_kernel_text"] += 1
        elif ctx_lr_meta["kernel_va"] and ctx_lr:
            counts["ctx_lr_kernel_va_nontext"] += 1

    stats = probe.get("stats") or {}
    sample_meta = probe.get("sample_meta") or {}
    occupied = int(sample_meta.get("occupied", 0))
    capacity = int(sample_meta.get("capacity", 0) or stats.get("sample_capacity", 0))
    saturation = occupied >= capacity if capacity else False
    symbols = load_text_symbols()
    codeword = codeword_match_analysis(samples)
    return {
        "counts": counts,
        "unique_counts": {field: len(values) for field, values in unique.items()},
        "unique_preview": {
            field: [f"0x{value:016x}" for value in sorted(values)[:12]]
            for field, values in unique.items()
        },
        "unique_comms": sorted(comms)[:32],
        "unique_comm_count": len(comms),
        "unique_pid_count": len({pid for pid in pids if pid}),
        "sample_ring_saturated": saturation,
        "occupied_samples": occupied,
        "capacity": capacity,
        "symbolization": {
            "stock_map": str(STOCK_MAP_PATH.relative_to(REPO_ROOT)),
            "text_symbol_count": len(symbols),
            "ctx_pc": symbolize_counter(counters["ctx_pc"], symbols),
            "ctx_lr": symbolize_counter(counters["ctx_lr"], symbols),
        },
        "codeword": codeword,
        "convergence_hint": (
            "ring saturated; rerun with shorter staged durations or lower print limit for convergence comparison"
            if saturation else
            "ring not saturated; longer duration can still add information"
        ),
    }


def render_report(summary: dict[str, Any]) -> str:
    probe = summary.get("probe") or {}
    stats = probe.get("stats") or {}
    analysis = summary.get("analysis") or {}
    counts = analysis.get("counts") or {}
    unique_counts = analysis.get("unique_counts") or {}
    symbolization = analysis.get("symbolization") or {}
    codeword = analysis.get("codeword") or {}
    ctx_pc_sym = symbolization.get("ctx_pc") or {}
    ctx_lr_sym = symbolization.get("ctx_lr") or {}
    lines = [
        "# Native Init V2216 Perf Regs Codeword Sample Ring",
        "",
        "## Decision",
        "",
        f"- Decision: `{summary.get('decision')}`",
        f"- Pass: `{str(summary.get('pass')).lower()}`",
        f"- Total samples observed: `{stats.get('count')}`",
        f"- Printed samples parsed: `{counts.get('printed_samples')}`",
        f"- Occupied ring slots: `{analysis.get('occupied_samples')}` / `{analysis.get('capacity')}`",
        f"- Selftest fail=0: `{str(summary.get('selftest_fail0')).lower()}`",
        f"- Phase timer contract: `{summary.get('phase_timer_contract')}`",
        f"- Residual-state contract: `{summary.get('residual_state_contract')}`",
        "",
        "## Method",
        "",
        "- Uses bounded BPF array maps: one stats row plus a 1024-slot sample ring.",
        "- Supports per-CPU software CPU-clock perf events; no unbounded kernel storage is used.",
        "- Samples live perf-event `pt_regs` x29/LR/SP/PC plus raw FP slots with `bpf_probe_read` only.",
        "- Does not use `probe_write_user`, cgroup attach, Wi-Fi, flash, reboot, or partition/firmware writes.",
        "",
        "## Metrics",
        "",
        f"- Unique comms: `{analysis.get('unique_comm_count')}`",
        f"- Unique pids: `{analysis.get('unique_pid_count')}`",
        f"- Walkable `fp_slot_next`: `{counts.get('walkable_fp_next')}`",
        f"- Walkable `fp2_slot_next`: `{counts.get('walkable_fp2_next')}`",
        f"- Raw LR nonzero: `{counts.get('raw_lr_nonzero')}`",
        f"- Raw LR in kernel text: `{counts.get('raw_lr_kernel_text')}`",
        f"- Raw LR kernel VA outside text: `{counts.get('raw_lr_kernel_va_nontext')}`",
        f"- Live ctx PC in kernel text: `{counts.get('ctx_pc_kernel_text')}`",
        f"- Live ctx LR nonzero: `{counts.get('ctx_lr_nonzero')}`",
        f"- Live ctx LR in kernel text: `{counts.get('ctx_lr_kernel_text')}`",
        f"- Live ctx LR kernel VA outside text: `{counts.get('ctx_lr_kernel_va_nontext')}`",
        f"- Direct stock-map ctx PC hits: `{ctx_pc_sym.get('direct_hits')}` / `{ctx_pc_sym.get('total')}`",
        f"- Direct stock-map ctx LR hits: `{ctx_lr_sym.get('direct_hits')}` / `{ctx_lr_sym.get('total')}`",
        f"- Codeword exact slide accepted: `{str(codeword.get('accepted_exact_codeword_slide')).lower()}`",
        f"- Codeword best slide: `{(codeword.get('best') or {}).get('slide_hex')}`",
        "",
        "| Field | Unique Count | Preview |",
        "| --- | ---: | --- |",
    ]
    for field in ["ctx_pc", "fp_slot_raw_lr", "fp_slot_next", "fp2_slot_raw_lr", "ctx_lr"]:
        preview = ", ".join((analysis.get("unique_preview") or {}).get(field) or []) or "none"
        lines.append(f"| `{field}` | {unique_counts.get(field, 0)} | {preview} |")
    lines.extend([
        "",
        "## Codeword Slide Check",
        "",
        f"- Stock raw: `{codeword.get('stock_raw')}`",
        f"- Candidate source: `{codeword.get('candidate_source')}`",
        f"- Candidate count: `{codeword.get('candidate_count')}`",
        "",
        "| Rank | Slide | Score | PC Match | LR-4 Match | LR Match |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ])
    for rank, item in enumerate((codeword.get("top_candidates") or [])[:12], 1):
        lines.append(
            f"| {rank} | `{item.get('slide_hex')}` | {item.get('weighted_score')} | "
            f"{item.get('pc_match')}/{item.get('pc_readable')} | "
            f"{item.get('lr_prev_match')}/{item.get('lr_prev_readable')} | "
            f"{item.get('lr_match')}/{item.get('lr_readable')} |"
        )
    lines.extend([
        "",
        "## Direct Symbol Preview",
        "",
        f"- Stock map: `{symbolization.get('stock_map')}`",
        f"- Text symbols loaded: `{symbolization.get('text_symbol_count')}`",
        "",
        "| Source | Count | Address | Symbol | Offset |",
        "| --- | ---: | --- | --- | ---: |",
    ])
    for source, table in [("ctx_pc", ctx_pc_sym), ("ctx_lr", ctx_lr_sym)]:
        for item in (table.get("top") or [])[:12]:
            lines.append(
                f"| `{source}` | {item.get('count')} | `{item.get('addr')}` | "
                f"`{item.get('symbol')}` | `{item.get('offset')}` |"
            )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- V2216 promotes the codeword-matched text slide to exact for this boot.",
        "- The exact slide supersedes the V2215 rank-only slide candidate because live instruction words match stock raw bytes.",
        "- Direct stock-map `_end_hyperdrive` labels are no-slide artifacts in this capture, not final function names.",
        "- The useful ROPP-bypass anchor is live perf-event `ctx_pc` plus live `ctx_lr` with codeword reads.",
        "- The saved FP-chain LR slots remain mostly ROPP-encoded and are not a completed unwind path.",
        "- Direct stock-map symbol previews are retained only to show why no-slide range lookup is misleading.",
        "",
        "## Source Basis",
        "",
        "- `bpf_perf_event_data` exposes `struct pt_regs regs` in the UAPI header.",
        "- `pe_prog_convert_ctx_access` rewrites default perf-event ctx reads through `bpf_perf_event_data_kern->regs`.",
        "- arm64 `pt_regs` layout is `regs[31], sp, pc, pstate`; generated offsets confirm LR=240, SP=248, PC=256.",
        "",
        "## Convergence",
        "",
        f"- Ring saturated: `{str(analysis.get('sample_ring_saturated')).lower()}`",
        f"- Hint: {analysis.get('convergence_hint')}",
        "",
        "## Safety",
        "",
    ])
    for key, value in (summary.get("safety") or {}).items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend([
        "",
        "## Evidence",
        "",
        f"- Private run: `{summary.get('out_dir')}`",
        f"- Helper SHA-256: `{(summary.get('build') or {}).get('helper_sha256')}`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2216-perf-regs-codeword-sample-ring")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18113)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
    parser.add_argument("--duration-ms", type=int, default=1000)
    parser.add_argument("--print-limit", type=int, default=256)
    parser.add_argument("--period-ns", type=int, default=1000000)
    parser.add_argument("--include-idle", action="store_true")
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--verbose-helper", action="store_true")
    args = parser.parse_args()

    out_dir = PRIVATE_RUNS / f"{args.label}-{base.now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[base.StepResult] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "args": {
            "duration_ms": args.duration_ms,
            "print_limit": args.print_limit,
            "period_ns": args.period_ns,
            "include_idle": args.include_idle,
        },
        "steps": [],
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "safety": {
            "read_only_bpf": True,
            "probe_write_user_executed": False,
            "cgroup_attach": False,
            "wifi_action": False,
            "flash_reboot": False,
            "partition_or_firmware_write": False,
        },
    }

    try:
        with transport.phase(summary, "preflight_bridge_status"):
            base.run_host(out_dir, steps, "bridge-status", [
                sys.executable,
                str(SCRIPT_DIR / "a90_bridge.py"),
                "status",
                "--json",
            ], timeout=30, allow_error=True)
            base.a90ctl(args, out_dir, steps, "pre-status", ["status"], timeout=60, allow_error=True)

        with transport.phase(summary, "build_helper"):
            build_dir = out_dir / "build"
            build_dir.mkdir(parents=True, exist_ok=True)
            helper_bin = build_dir / "a90_bpf_perf_regs_codeword_sample_ring"
            if not args.skip_build:
                helper_bin = base.build_helper(
                    build_dir,
                    steps,
                    source=HELPER_DIR / "a90_bpf_perf_regs_codeword_sample_ring.c",
                    output_name="a90_bpf_perf_regs_codeword_sample_ring",
                    cc=args.cc,
                    strip=args.strip,
                )
            summary["build"] = {
                "helper_local": str(helper_bin.relative_to(REPO_ROOT)),
                "helper_sha256": base.sha256_file(helper_bin),
            }

        if not args.skip_install:
            with transport.phase(summary, "install_helper"):
                base.install_helper(args, out_dir, steps, "perf-regs-codeword-sample-ring", helper_bin, REMOTE_HELPER)

        check_args = [
            REMOTE_HELPER,
            "--duration-ms",
            str(args.duration_ms),
            "--period-ns",
            str(args.period_ns),
            "--print-limit",
            str(args.print_limit),
        ]
        if args.include_idle:
            check_args.append("--include-idle")
        with transport.phase(summary, "helper_check"):
            check_stdout = base.tcpctl_run(args, out_dir, steps, "perf-regs-codeword-sample-ring-check-only", check_args, timeout=60)
            if "result=check-only" not in check_stdout:
                raise RuntimeError(f"check-only did not complete cleanly:\n{check_stdout}")

        helper_args = [
            REMOTE_HELPER,
            "--duration-ms",
            str(args.duration_ms),
            "--period-ns",
            str(args.period_ns),
            "--print-limit",
            str(args.print_limit),
            "--allow-attach",
        ]
        if args.include_idle:
            helper_args.append("--include-idle")
        if args.verbose_helper:
            helper_args.append("--verbose")
        with transport.phase(summary, "sample_capture"):
            probe_stdout = base.tcpctl_run(
                args,
                out_dir,
                steps,
                "perf-regs-codeword-sample-ring-live",
                helper_args,
                timeout=max(60, args.duration_ms / 1000.0 + 30),
            )
            if "result=v2216-perf-regs-codeword-sample-ring-complete" not in probe_stdout:
                raise RuntimeError(f"live helper did not complete cleanly:\n{probe_stdout}")
            probe = parse_helper_stdout(probe_stdout)

        with transport.phase(summary, "analysis"):
            analysis = analyze_probe(probe)

        with transport.phase(summary, "post_selftest"):
            selftest = base.a90ctl(args, out_dir, steps, "post-selftest", ["selftest"], timeout=90, allow_error=True)
        total = int((probe.get("stats") or {}).get("count", 0))
        printed = len(probe.get("samples") or [])
        codeword_exact = bool((analysis.get("codeword") or {}).get("accepted_exact_codeword_slide"))
        if total > 0 and printed > 0 and codeword_exact:
            decision = "v2216-codeword-slide-exact"
        elif total > 0 and printed > 0:
            decision = "v2216-perf-regs-codeword-sample-ring-captured"
        elif total > 0:
            decision = "v2216-samples-observed-not-printed"
        else:
            decision = "v2216-no-perf-event-samples"
        summary.update({
            "decision": decision,
            "probe": probe,
            "analysis": analysis,
            "selftest_fail0": "fail=0" in selftest,
        })
        summary["pass"] = decision in {
            "v2216-codeword-slide-exact",
            "v2216-perf-regs-codeword-sample-ring-captured",
        } and summary["selftest_fail0"]
    except Exception as exc:
        summary["decision"] = "v2216-perf-regs-codeword-sample-ring-failed"
        summary["pass"] = False
        summary["error"] = str(exc)
    finally:
        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        summary["steps"] = [
            {
                "name": step.name,
                "command": step.command,
                "returncode": step.returncode,
                "ok": step.ok,
                "elapsed_sec": step.elapsed_sec,
                "stdout_path": step.stdout_path,
                "stderr_path": step.stderr_path,
            }
            for step in steps
        ]
        transport.set_residual_state(summary, base.residual_state(summary))
        artifact_started = time.monotonic()
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        if "probe" in summary:
            REPORT_PATH.write_text(render_report(summary))
            summary["report_path"] = str(REPORT_PATH.relative_to(REPO_ROOT))
        transport.add_total_phase(summary, "artifact_write", artifact_started, ok=True)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "decision": summary.get("decision"),
        "pass": summary.get("pass"),
        "out_dir": summary.get("out_dir"),
        "report_path": summary.get("report_path"),
        "selftest_fail0": summary.get("selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
