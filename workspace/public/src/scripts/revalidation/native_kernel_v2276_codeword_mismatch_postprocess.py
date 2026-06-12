#!/usr/bin/env python3
"""V2276 host-only postprocess for the V2275 codeword mismatch sites.

This does not touch the device. It reuses the V2275 private codeword/workqueue
logs and decides whether the V2216 slide can be accepted when PC mismatches are
known ARM64 UAO runtime-alternative patches and LR/LR-4 remain exact.
"""

from __future__ import annotations

import argparse
import bisect
import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_kernel_perf_regs_codeword_sample_ring_v2216 as codeword_v2216
import native_kernel_workqueue_codeword_handoff_v2275 as workqueue_v2275


REPO_ROOT = repo_root()
DEFAULT_RUN_DIR = REPO_ROOT / "workspace/private/runs/kernel/v2275-workqueue-codeword-live-20260612-172723"
CODEWORD_REL = Path("device/codeword_log.cmdv1.txt")
WORKQUEUE_REL = Path("device/workqueue_log.cmdv1.txt")
UAO_SOURCE = "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/arch/arm64/include/asm/alternative.h:222"

PAIR_POST_MASK = 0x7FC00000
STP_POST_VALUE = 0x28800000
LDP_POST_VALUE = 0x28C00000
SINGLE_POST_MASK = 0xFFE00C00
STR_POST_VALUE = 0xF8000400
LDR_POST_VALUE = 0xF8400400
UNPRIV_MASK = 0xFFE00C00
STTR_VALUE = 0xF8000800
LDTR_VALUE = 0xF8400800


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args()


def as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def hex64(value: int | None) -> str | None:
    return None if value is None else f"0x{value:016x}"


def hex32(value: int | None) -> str | None:
    return None if value is None else f"0x{value:08x}"


def is_pair_post(insn: int, value: int) -> bool:
    return (insn & PAIR_POST_MASK) == value


def is_single_post(insn: int, value: int) -> bool:
    return (insn & SINGLE_POST_MASK) == value


def is_unpriv(insn: int, value: int) -> bool:
    return (insn & UNPRIV_MASK) == value


def rt(insn: int) -> int:
    return insn & 0x1F


def rn(insn: int) -> int:
    return (insn >> 5) & 0x1F


def classify_uao_runtime_patch(stock: int | None, live: int) -> str | None:
    if stock is None:
        return None
    same_rt_rn = rt(stock) == rt(live) and rn(stock) == rn(live)
    if not same_rt_rn:
        return None
    if is_single_post(stock, STR_POST_VALUE) and is_unpriv(live, STTR_VALUE):
        return "uao_user_alternative_str_to_sttr"
    if is_single_post(stock, LDR_POST_VALUE) and is_unpriv(live, LDTR_VALUE):
        return "uao_user_alternative_ldr_to_ldtr"
    if is_pair_post(stock, STP_POST_VALUE) and is_unpriv(live, STTR_VALUE):
        return "uao_stp_first_lane_to_sttr"
    if is_pair_post(stock, LDP_POST_VALUE) and is_unpriv(live, LDTR_VALUE):
        return "uao_ldp_first_lane_to_ldtr"
    return None


def symbol_resolver(symbols: list[tuple[int, str]]):
    addrs = [addr for addr, _ in symbols]
    names = [name for _, name in symbols]

    def resolve(static_addr: int) -> dict[str, Any]:
        idx = bisect.bisect_right(addrs, static_addr) - 1
        if idx < 0:
            return {"symbol": None, "offset": None, "symbol_addr": None}
        next_addr = addrs[idx + 1] if idx + 1 < len(addrs) else None
        in_range = next_addr is None or static_addr < next_addr
        return {
            "symbol": names[idx] if in_range else None,
            "offset": static_addr - addrs[idx] if in_range else None,
            "symbol_addr": addrs[idx] if in_range else None,
        }

    return resolve


def mismatch_rows(probe: dict[str, Any], slide: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    raw = codeword_v2216.load_kernel_raw()
    base = codeword_v2216.load_synthetic_base()
    resolve = symbol_resolver(codeword_v2216.load_text_symbols())
    rows: list[dict[str, Any]] = []
    counts = {
        "pc_readable": 0,
        "pc_match": 0,
        "lr_prev_readable": 0,
        "lr_prev_match": 0,
        "lr_readable": 0,
        "lr_match": 0,
    }
    for sample_index, sample in enumerate(probe.get("samples") or []):
        pc = int(sample.get("ctx_pc", 0))
        pc_insn = int(sample.get("ctx_pc_insn", 0))
        lr = int(sample.get("ctx_lr", 0))
        lr_prev_insn = int(sample.get("ctx_lr_prev_insn", 0))
        lr_insn = int(sample.get("ctx_lr_insn", 0))

        pc_stock = None
        pc_static = None
        if pc and pc_insn:
            counts["pc_readable"] += 1
            pc_static = pc - slide
            pc_stock = codeword_v2216.read_stock_u32(raw, base, pc_static)
            if pc_stock == pc_insn:
                counts["pc_match"] += 1

        lr_static = lr - slide if lr else None
        lr_prev_stock = None
        if lr_static is not None and lr_prev_insn:
            counts["lr_prev_readable"] += 1
            lr_prev_stock = codeword_v2216.read_stock_u32(raw, base, lr_static - 4)
            if lr_prev_stock == lr_prev_insn:
                counts["lr_prev_match"] += 1
        lr_stock = None
        if lr_static is not None and lr_insn:
            counts["lr_readable"] += 1
            lr_stock = codeword_v2216.read_stock_u32(raw, base, lr_static)
            if lr_stock == lr_insn:
                counts["lr_match"] += 1

        if pc and pc_insn and pc_stock != pc_insn and pc_static is not None:
            pc_symbol = resolve(pc_static)
            lr_symbol = resolve(lr_static) if lr_static is not None else {"symbol": None, "offset": None}
            uao_class = classify_uao_runtime_patch(pc_stock, pc_insn)
            rows.append({
                "sample_index": sample_index,
                "seq": sample.get("seq"),
                "comm": sample.get("comm"),
                "pid": sample.get("pid"),
                "tgid": sample.get("tgid"),
                "runtime_pc": hex64(pc),
                "static_pc": hex64(pc_static),
                "pc_symbol": pc_symbol["symbol"],
                "pc_symbol_offset": pc_symbol["offset"],
                "live_pc_insn": hex32(pc_insn),
                "stock_pc_insn": hex32(pc_stock),
                "uao_patch_class": uao_class,
                "runtime_lr": hex64(lr) if lr else None,
                "static_lr": hex64(lr_static) if lr_static is not None else None,
                "lr_symbol": lr_symbol["symbol"],
                "lr_symbol_offset": lr_symbol["offset"],
                "lr_prev_live": hex32(lr_prev_insn) if lr_prev_insn else None,
                "lr_prev_stock": hex32(lr_prev_stock),
                "lr_prev_match": bool(lr_prev_stock == lr_prev_insn and lr_prev_insn),
                "lr_live": hex32(lr_insn) if lr_insn else None,
                "lr_stock": hex32(lr_stock),
                "lr_match": bool(lr_stock == lr_insn and lr_insn),
            })
    return rows, counts


def classify_workqueue_with_slide(run_dir: Path, slide: int) -> dict[str, Any]:
    text = (run_dir / WORKQUEUE_REL).read_text(encoding="utf-8", errors="replace")
    workqueue = workqueue_v2275.parse_workqueue_log(text)
    addrs, names, symbol_index = workqueue_v2275.load_symbol_map()
    target_static = {name: symbol_index[name] for name in workqueue_v2275.TARGET_SYMBOLS if name in symbol_index}
    symbol_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    target_hits: list[dict[str, Any]] = []
    for sample in workqueue.get("samples") or []:
        function = int(sample.get("function", 0))
        static_addr = function - slide
        resolved = workqueue_v2275.resolve_symbol(static_addr, addrs, names)
        symbol = resolved.get("symbol")
        kind = str(sample.get("kind") or "")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if symbol:
            symbol_counts[str(symbol)] = symbol_counts.get(str(symbol), 0) + 1
        if symbol in target_static:
            target_hits.append({
                "index": sample.get("index"),
                "kind": kind,
                "function": hex64(function),
                "static": resolved.get("static_hex"),
                "symbol": symbol,
                "offset": resolved.get("offset"),
                "pid": sample.get("pid"),
                "tgid": sample.get("tgid"),
            })
    total = int((workqueue.get("stats") or {}).get("total", 0))
    stored = int((workqueue.get("stats") or {}).get("stored", 0))
    if workqueue.get("result") != "v2273-workqueue-func-sample-ring-complete":
        classification = "workqueue-sampler-incomplete"
    elif total <= 0 or stored <= 0:
        classification = "workqueue-no-activity"
    elif target_hits:
        classification = "workqueue-target-hit"
    else:
        classification = "workqueue-no-target-hit"
    return {
        "classification": classification,
        "target_hit_count": len(target_hits),
        "target_hits": target_hits[:32],
        "stats": workqueue.get("stats"),
        "sample_count": len(workqueue.get("samples") or []),
        "kind_counts": kind_counts,
        "symbol_counts_top": sorted(symbol_counts.items(), key=lambda item: (-item[1], item[0]))[:24],
        "target_symbols": list(workqueue_v2275.TARGET_SYMBOLS),
    }


def analyze(run_dir: Path) -> dict[str, Any]:
    codeword_path = run_dir / CODEWORD_REL
    if not codeword_path.exists():
        raise FileNotFoundError(codeword_path)
    codeword_text = codeword_path.read_text(encoding="utf-8", errors="replace")
    probe = codeword_v2216.parse_helper_stdout(codeword_text)
    codeword_analysis = codeword_v2216.analyze_probe(probe)
    codeword = codeword_analysis.get("codeword") or {}
    best = codeword.get("best") or {}
    slide = as_int(best.get("slide"))
    mismatches, counts = mismatch_rows(probe, slide)
    all_mismatches_are_uao = bool(mismatches) and all(row.get("uao_patch_class") for row in mismatches)
    lr_exact = counts["lr_prev_readable"] > 0 and counts["lr_prev_match"] == counts["lr_prev_readable"] and counts["lr_readable"] > 0 and counts["lr_match"] == counts["lr_readable"]
    patch_aware_accepted = bool(all_mismatches_are_uao and lr_exact and counts["pc_readable"] - counts["pc_match"] == len(mismatches))
    workqueue = classify_workqueue_with_slide(run_dir, slide) if patch_aware_accepted else None
    decision = "v2276-codeword-uao-patch-aware-slide-accepted"
    if not patch_aware_accepted:
        decision = "v2276-codeword-mismatch-not-accepted"
    elif workqueue and workqueue.get("classification") == "workqueue-no-target-hit":
        decision = "v2276-codeword-uao-patch-aware-accepted-workqueue-no-target-hit"
    elif workqueue and workqueue.get("classification") == "workqueue-target-hit":
        decision = "v2276-codeword-uao-patch-aware-accepted-workqueue-target-hit"
    return {
        "cycle": "V2276",
        "decision": decision,
        "patch_aware_accepted": patch_aware_accepted,
        "run_dir": str(run_dir.relative_to(REPO_ROOT) if run_dir.is_relative_to(REPO_ROOT) else run_dir),
        "codeword": {
            "existing_accepted_symbolization_slide": codeword.get("accepted_symbolization_slide"),
            "existing_acceptance_reason": codeword.get("acceptance_reason"),
            "slide": slide,
            "slide_hex": best.get("slide_hex") or (f"0x{slide:x}" if slide >= 0 else f"-0x{-slide:x}"),
            "pc_match": f"{counts['pc_match']}/{counts['pc_readable']}",
            "lr_prev_match": f"{counts['lr_prev_match']}/{counts['lr_prev_readable']}",
            "lr_match": f"{counts['lr_match']}/{counts['lr_readable']}",
            "mismatch_count": len(mismatches),
            "mismatch_classes": sorted({str(row.get("uao_patch_class")) for row in mismatches}),
            "uao_source": UAO_SOURCE,
        },
        "mismatches": mismatches,
        "workqueue": workqueue,
        "next_action": (
            "Treat V2275 same-boot slide as accepted only under the bounded UAO-patch-aware rule; "
            "do not rerun the combined capture. Since workqueue target hits are zero, design the next T1 oracle around a call-stack/callsite observable rather than work->func alone."
            if patch_aware_accepted and workqueue and workqueue.get("target_hit_count") == 0 else
            "Do not use the V2275 workqueue classification until a narrower same-boot symbolization oracle is available."
        ),
    }


def main() -> int:
    args = parse_args()
    result = analyze(args.run_dir)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
