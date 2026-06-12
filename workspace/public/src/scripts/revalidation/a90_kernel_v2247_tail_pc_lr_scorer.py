#!/usr/bin/env python3
"""V2247 post-FWREADY tail PC/LR scorer.

Map a per-boot exact-slide perf regs/codeword capture onto the V2246
post-FWREADY firmware_class/qcacld-HDD target whitelist. This is a host-only
analysis layer; it does not attach BPF or talk to the device.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from a90_kernel_v2241_user_uprobe_offset_base_map import PRIVATE_RUNS, rel

DEFAULT_SAMPLE_SUMMARY = (
    PRIVATE_RUNS
    / "v2216-perf-regs-codeword-sample-ring-5s-20260612-053331/summary.json"
)
DEFAULT_TARGET_SUMMARY = (
    PRIVATE_RUNS
    / "v2246-post-fwready-tail-symbol-source-map-20260612-115530/summary.json"
)

def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if text == "":
        return None
    return int(text, 0)


def load_exact_slide(sample_summary: dict[str, Any]) -> dict[str, Any]:
    codeword = ((sample_summary.get("analysis") or {}).get("codeword") or {})
    best = codeword.get("best") or {}
    slide = parse_int(best.get("slide"))
    accepted = bool(codeword.get("accepted_exact_codeword_slide"))
    return {
        "available": slide is not None,
        "accepted_exact_codeword_slide": accepted,
        "slide": slide,
        "slide_hex": best.get("slide_hex"),
        "pc_match": best.get("pc_match"),
        "pc_readable": best.get("pc_readable"),
        "lr_prev_match": best.get("lr_prev_match"),
        "lr_prev_readable": best.get("lr_prev_readable"),
        "lr_match": best.get("lr_match"),
        "lr_readable": best.get("lr_readable"),
        "weighted_score": best.get("weighted_score"),
    }


def load_targets(target_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in target_summary.get("rows") or []:
        address = parse_int(row.get("stock_address_hex"))
        size = parse_int(row.get("stack_reported_size_hex"))
        if address is None or size is None:
            continue
        rows.append({
            "symbol": row["symbol"],
            "start": address,
            "end": address + size,
            "start_hex": f"0x{address:016x}",
            "end_hex": f"0x{address + size:016x}",
            "size": size,
            "size_hex": f"0x{size:x}",
            "source": row.get("source") or {},
        })
    rows.sort(key=lambda item: item["start"])
    return rows


def target_for_static(static_addr: int, targets: list[dict[str, Any]]) -> dict[str, Any] | None:
    for target in targets:
        if target["start"] <= static_addr < target["end"]:
            return target
    return None


def sample_addresses(sample: dict[str, Any]) -> dict[str, int]:
    addresses: dict[str, int] = {}
    ctx_pc = parse_int(sample.get("ctx_pc"))
    ctx_lr = parse_int(sample.get("ctx_lr"))
    if ctx_pc:
        addresses["ctx_pc"] = ctx_pc
    if ctx_lr:
        addresses["ctx_lr"] = ctx_lr
        addresses["ctx_lr_minus4"] = ctx_lr - 4
    return addresses


def score_samples(
    sample_summary: dict[str, Any],
    targets: list[dict[str, Any]],
    slide: int,
) -> dict[str, Any]:
    samples = (sample_summary.get("probe") or {}).get("samples") or []
    hits: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    symbol_counts: Counter[str] = Counter()
    comm_counts: Counter[str] = Counter()
    for index, sample in enumerate(samples):
        comm = str(sample.get("comm") or "")
        for source, runtime_addr in sample_addresses(sample).items():
            static_addr = runtime_addr - slide
            target = target_for_static(static_addr, targets)
            if target is None:
                continue
            offset = static_addr - target["start"]
            source_counts[source] += 1
            symbol_counts[target["symbol"]] += 1
            if comm:
                comm_counts[comm] += 1
            hits.append({
                "sample_index": index,
                "source": source,
                "symbol": target["symbol"],
                "symbol_offset": offset,
                "symbol_offset_hex": f"0x{offset:x}",
                "comm": comm,
                "pid": sample.get("pid"),
            })
    return {
        "sample_count": len(samples),
        "hit_count": len(hits),
        "source_hit_counts": dict(sorted(source_counts.items())),
        "symbol_hit_counts": dict(sorted(symbol_counts.items())),
        "comm_hit_counts": dict(comm_counts.most_common(16)),
        "hits": hits,
    }


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    sample_summary = read_json(args.sample_summary)
    target_summary = read_json(args.target_summary)
    exact_slide = load_exact_slide(sample_summary)
    targets = load_targets(target_summary)
    if exact_slide["slide"] is None:
        scoring = {
            "sample_count": len((sample_summary.get("probe") or {}).get("samples") or []),
            "hit_count": 0,
            "source_hit_counts": {},
            "symbol_hit_counts": {},
            "comm_hit_counts": {},
            "hits": [],
        }
    else:
        scoring = score_samples(sample_summary, targets, int(exact_slide["slide"]))
    target_path = out_dir / "tail_pc_lr_score.json"
    target_path.write_text(json.dumps({
        "warning": "Private per-sample metadata. Public report contains aggregate counts only.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "exact_slide": exact_slide,
        "targets": targets,
        "scoring": scoring,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision = "v2247-tail-pc-lr-scorer-pass"
    if not exact_slide["accepted_exact_codeword_slide"]:
        decision = "v2247-tail-pc-lr-scorer-no-exact-slide"
    elif not targets:
        decision = "v2247-tail-pc-lr-scorer-no-targets"
    return {
        "label": args.label,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "decision": decision,
        "pass": decision.endswith("-pass"),
        "out_dir": rel(out_dir),
        "safety": {
            "host_only": True,
            "device_io": False,
            "bpf_attach": False,
            "tracefs_control_write": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
            "private_raw_log_copied_to_public": False,
        },
        "inputs": {
            "sample_summary": rel(args.sample_summary),
            "target_summary": rel(args.target_summary),
        },
        "exact_slide": exact_slide,
        "target_count": len(targets),
        "target_symbols": [target["symbol"] for target in targets],
        "scoring": {
            "sample_count": scoring["sample_count"],
            "hit_count": scoring["hit_count"],
            "source_hit_counts": scoring["source_hit_counts"],
            "symbol_hit_counts": scoring["symbol_hit_counts"],
            "comm_hit_counts": scoring["comm_hit_counts"],
        },
        "private_score": {
            "path": rel(target_path),
            "contains_raw_runtime_addresses": False,
            "contains_per_sample_symbol_hits": True,
        },
        "interpretation": {
            "result": "The scorer can map per-boot exact-slide perf PC/LR samples onto the V2246 post-FWREADY target whitelist.",
            "negative_control_note": "The default V2216 generic CPU-clock capture is not a post-FWREADY tail capture; zero hits there is expected and useful as a false-positive check.",
            "next_live_target": "Run a tail-window live capture and feed its summary to this scorer; nonzero hits in _request_firmware/request_firmware/qdf/cfg/hdd symbols would prove code-path identity for the post-FWREADY tail.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2247-tail-pc-lr-scorer")
    parser.add_argument("--sample-summary", type=Path, default=DEFAULT_SAMPLE_SUMMARY)
    parser.add_argument("--target-summary", type=Path, default=DEFAULT_TARGET_SUMMARY)
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args, out_dir)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": summary["decision"],
        "pass": summary["pass"],
        "out_dir": summary["out_dir"],
        "summary": rel(summary_path),
        "target_count": summary["target_count"],
        "sample_count": summary["scoring"]["sample_count"],
        "hit_count": summary["scoring"]["hit_count"],
        "source_hit_counts": summary["scoring"]["source_hit_counts"],
        "symbol_hit_counts": summary["scoring"]["symbol_hit_counts"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
