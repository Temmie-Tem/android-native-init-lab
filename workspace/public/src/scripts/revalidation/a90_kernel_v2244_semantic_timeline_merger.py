#!/usr/bin/env python3
"""V2244 semantic timeline merger.

Merge the V2239 helper-owned WLFW/QMI timeline contract with the V2243 public
semantic classifier. This keeps the boot-window evidence public-safe while
separating high-confidence call/entry evidence from marker-only semantic edges.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from a90_kernel_v2241_user_uprobe_offset_base_map import PRIVATE_RUNS, rel

DEFAULT_V2239_SUMMARY = PRIVATE_RUNS / "v2239-scalar-uprobe-timeline-20260612-105944/summary.json"
DEFAULT_V2239_TIMELINE = PRIVATE_RUNS / "v2239-scalar-uprobe-timeline-20260612-105944/timeline.json"
DEFAULT_V2243_SUMMARY = PRIVATE_RUNS / "v2243-user-uprobe-semantic-classifier-20260612-113113/summary.json"


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def semantic_by_event(v2243: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in v2243.get("key_events", []):
        rows[str(row["event"])] = row
    return rows


def evidence_strength(row: dict[str, Any] | None) -> str:
    if row is None:
        return "missing_semantics"
    if row.get("confidence") == "high":
        return "strong"
    if row.get("confidence") == "medium":
        return "marker"
    return "weak"


def merge_edge(edge: dict[str, Any], semantic: dict[str, Any] | None) -> dict[str, Any]:
    strength = evidence_strength(semantic)
    return {
        "event": edge.get("event"),
        "group": edge.get("group"),
        "surface": edge.get("surface"),
        "first_ts": edge.get("first_ts"),
        "hit_count": edge.get("hit_count"),
        "semantic_found": semantic is not None,
        "evidence_strength": strength,
        "event_role": semantic.get("event_role") if semantic else None,
        "instruction_class": semantic.get("instruction_class") if semantic else None,
        "alignment": semantic.get("alignment") if semantic else None,
        "confidence": semantic.get("confidence") if semantic else None,
        "object": semantic.get("object") if semantic else None,
    }


def summarize_run(run_id: str, run: dict[str, Any], semantics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    merged_edges = {
        event: merge_edge(edge, semantics.get(event))
        for event, edge in sorted((run.get("edges") or {}).items())
    }
    strengths = Counter(edge["evidence_strength"] for edge in merged_edges.values())
    missing_semantics = [event for event, edge in merged_edges.items() if not edge["semantic_found"]]
    low_or_weak = [event for event, edge in merged_edges.items() if edge["evidence_strength"] == "weak"]
    return {
        "run_id": run_id,
        "outcome": run.get("outcome"),
        "edge_count": len(merged_edges),
        "strong_edge_count": strengths.get("strong", 0),
        "marker_edge_count": strengths.get("marker", 0),
        "weak_edge_count": strengths.get("weak", 0),
        "missing_semantic_count": len(missing_semantics),
        "missing_semantics": missing_semantics,
        "weak_edges": low_or_weak,
        "deltas_sec": run.get("deltas_sec") or {},
        "edges": merged_edges,
    }


def compare_outcomes(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_outcome: dict[str, list[dict[str, Any]]] = {}
    for run in runs.values():
        by_outcome.setdefault(str(run.get("outcome")), []).append(run)
    edge_sets_by_outcome = {
        outcome: sorted(set.intersection(*(set(run["edges"]) for run in items))) if items else []
        for outcome, items in by_outcome.items()
    }
    all_edge_sets = {run_id: set(run["edges"]) for run_id, run in runs.items()}
    common_edges = sorted(set.intersection(*all_edge_sets.values())) if all_edge_sets else []
    union_edges = sorted(set.union(*all_edge_sets.values())) if all_edge_sets else []
    semantic_signatures = {
        run_id: {
            event: (
                edge["evidence_strength"],
                edge["event_role"],
                edge["alignment"],
                edge["confidence"],
            )
            for event, edge in run["edges"].items()
        }
        for run_id, run in runs.items()
    }
    first_signature = next(iter(semantic_signatures.values()), {})
    differing_semantic_edges = sorted({
        event
        for signature in semantic_signatures.values()
        for event, value in signature.items()
        if first_signature.get(event) != value
    })
    return {
        "outcomes": {outcome: [run["run_id"] for run in items] for outcome, items in sorted(by_outcome.items())},
        "common_edge_count": len(common_edges),
        "union_edge_count": len(union_edges),
        "common_edges": common_edges,
        "edge_sets_identical_across_runs": all(set(run["edges"]) == set(common_edges) for run in runs.values()),
        "edge_sets_by_outcome": edge_sets_by_outcome,
        "semantic_signatures_identical_across_runs": not differing_semantic_edges,
        "differing_semantic_edges": differing_semantic_edges,
    }


def sorted_counter(values) -> dict[str, int]:
    normalized = ("none" if value is None else str(value) for value in values)
    return dict(sorted(Counter(normalized).items()))


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    v2239_summary = read_json(args.v2239_summary)
    v2239_timeline = read_json(args.v2239_timeline)
    v2243_summary = read_json(args.v2243_summary)
    semantics = semantic_by_event(v2243_summary)
    runs = {
        run_id: summarize_run(run_id, run, semantics)
        for run_id, run in sorted(v2239_timeline.items())
    }
    comparison = compare_outcomes(runs)
    edge_rows = [edge for run in runs.values() for edge in run["edges"].values()]
    missing_semantic_edges = sorted({edge["event"] for edge in edge_rows if not edge["semantic_found"]})
    weak_edges = sorted({edge["event"] for edge in edge_rows if edge["evidence_strength"] == "weak"})
    low_confidence_key_edges = sorted({edge["event"] for edge in edge_rows if edge["confidence"] == "low"})
    merged_path = out_dir / "semantic_timeline.json"
    merged_path.write_text(json.dumps({
        "warning": "Public-safe metadata. Contains no raw bytes or raw disassembly.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runs": runs,
        "comparison": comparison,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision = "v2244-semantic-timeline-merge-pass"
    if missing_semantic_edges or weak_edges or low_confidence_key_edges:
        decision = "v2244-semantic-timeline-merge-review-needed"
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
            "v2239_summary": rel(args.v2239_summary),
            "v2239_timeline": rel(args.v2239_timeline),
            "v2243_summary": rel(args.v2243_summary),
        },
        "v2239_decision": v2239_summary.get("decision"),
        "v2243_decision": v2243_summary.get("decision"),
        "run_count": len(runs),
        "edge_observation_count": len(edge_rows),
        "semantic_coverage_count": sum(1 for edge in edge_rows if edge["semantic_found"]),
        "missing_semantic_edges": missing_semantic_edges,
        "weak_edges": weak_edges,
        "low_confidence_key_edges": low_confidence_key_edges,
        "strength_counts": sorted_counter(edge["evidence_strength"] for edge in edge_rows),
        "role_counts": sorted_counter(edge["event_role"] for edge in edge_rows),
        "alignment_counts": sorted_counter(edge["alignment"] for edge in edge_rows),
        "run_summaries": {
            run_id: {
                "outcome": run["outcome"],
                "edge_count": run["edge_count"],
                "strong_edge_count": run["strong_edge_count"],
                "marker_edge_count": run["marker_edge_count"],
                "weak_edge_count": run["weak_edge_count"],
                "missing_semantic_count": run["missing_semantic_count"],
            }
            for run_id, run in runs.items()
        },
        "comparison": comparison,
        "semantic_timeline": {
            "path": rel(merged_path),
            "raw_bytes_published": False,
            "raw_disassembly_published": False,
        },
        "interpretation": {
            "wl_fw_qmi_semantic_edges_differentiate_wlan0_success": bool(comparison["differing_semantic_edges"]),
            "result": "V2229/V2231/V2233 share the same semantic WLFW/QMI edge set; V2233 success remains downstream of this edge sequence.",
            "next_if_live_needed": "sample exact-slide kernel PC/LR around the post-FWREADY firmware-class or boot_wlan tail, not another WLFW/QMI order capture",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2244-semantic-timeline-merge")
    parser.add_argument("--v2239-summary", type=Path, default=DEFAULT_V2239_SUMMARY)
    parser.add_argument("--v2239-timeline", type=Path, default=DEFAULT_V2239_TIMELINE)
    parser.add_argument("--v2243-summary", type=Path, default=DEFAULT_V2243_SUMMARY)
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
        "run_count": summary["run_count"],
        "edge_observation_count": summary["edge_observation_count"],
        "semantic_coverage_count": summary["semantic_coverage_count"],
        "strength_counts": summary["strength_counts"],
        "edge_sets_identical_across_runs": summary["comparison"]["edge_sets_identical_across_runs"],
        "semantic_signatures_identical_across_runs": summary["comparison"]["semantic_signatures_identical_across_runs"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
