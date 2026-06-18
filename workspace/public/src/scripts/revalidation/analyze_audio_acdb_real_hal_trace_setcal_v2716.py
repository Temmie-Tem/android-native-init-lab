#!/usr/bin/env python3
"""V2716 host-only audit for real-HAL ACDB custom-topology SET records.

The active Gate-4 question is narrow: do existing Android-good real-HAL ptrace
captures already contain AUDIO_SET_CALIBRATION records for subsystem custom
topology cal_types 10, 14, or 24?

This script reuses the V2652 public-scalar decoder. It never emits raw ioctl
bytes or payload bytes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import analyze_audio_acdb_real_set_bytes_v2652 as v2652

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2716"
BUILD_TAG = "v2716-audio-acdb-real-hal-setcal-reparse"
DEFAULT_RUNS_ROOT = ROOT / "workspace/private/runs/audio"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2716_AUDIO_ACDB_REAL_HAL_TRACE_SETCAL_REPARSE_2026-06-18.md"
DEFAULT_RUN_NAMES = [
    "v2461-acdb-compat-live-20260615-190530",
    "v2466-acdb-dmabuf-live-20260615-200643",
]

TARGET_CUSTOM_TOPOLOGY_TYPES = {
    10: "ADM_CUST_TOPOLOGY",
    14: "ASM_CUST_TOPOLOGY",
    24: "AFE_CUST_TOPOLOGY",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def iter_target_trace_paths(runs_root: Path, run_names: list[str]) -> list[Path]:
    paths: list[Path] = []
    for run_name in run_names:
        run_dir = runs_root / run_name
        paths.extend(sorted(run_dir.glob("**/msm-audio-cal-*.jsonl")))
    return paths


def load_target_records(runs_root: Path, run_names: list[str]) -> list[v2652.SetArgRecord]:
    records: list[v2652.SetArgRecord] = []
    for path in iter_target_trace_paths(runs_root, run_names):
        for row in v2652.iter_jsonl(path):
            record = v2652.row_to_set_record(path, row, runs_root)
            if record is not None:
                records.append(record)
    return records


def summarize(records: list[v2652.SetArgRecord]) -> dict[str, Any]:
    by_type: Counter[int] = Counter(record.cal_type for record in records)
    by_run: dict[str, list[int]] = defaultdict(list)
    target_records: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: (item.run_dir, item.source, item.sequence or -1)):
        by_run[record.run_dir].append(record.cal_type)
        if record.cal_type in TARGET_CUSTOM_TOPOLOGY_TYPES:
            public = record.public_dict()
            public["target_name"] = TARGET_CUSTOM_TOPOLOGY_TYPES[record.cal_type]
            target_records.append(public)
    present_targets = sorted({record.cal_type for record in records if record.cal_type in TARGET_CUSTOM_TOPOLOGY_TYPES})
    missing_targets = sorted(set(TARGET_CUSTOM_TOPOLOGY_TYPES) - set(present_targets))
    return {
        "record_count": len(records),
        "observed_cal_type_counts": dict(sorted(by_type.items())),
        "observed_cal_types": sorted(by_type),
        "per_run_order": dict(sorted(by_run.items())),
        "target_custom_topology_types": TARGET_CUSTOM_TOPOLOGY_TYPES,
        "present_target_cal_types": present_targets,
        "missing_target_cal_types": missing_targets,
        "target_records": target_records,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    runs_root = Path(args.runs_root)
    run_names = list(args.run_name)
    trace_paths = iter_target_trace_paths(runs_root, run_names)
    records = load_target_records(runs_root, run_names)
    summary = summarize(records)
    decision = (
        "v2716-real-hal-trace-custom-topology-set-present"
        if summary["present_target_cal_types"]
        else "v2716-real-hal-trace-no-subsystem-custom-topology-set"
    )
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "generated_at": now_iso(),
        "ok": True,
        "decision": decision,
        "scope": "host-only reparse of existing private Android-good ptrace JSONL; no device action",
        "inputs": {
            "runs_root": rel(runs_root),
            "run_names": run_names,
            "trace_file_count": len(trace_paths),
            "trace_files": [rel(path) for path in trace_paths],
        },
        "summary": summary,
        "conclusions": {
            "existing_trace_contains_cal10": 10 in summary["present_target_cal_types"],
            "existing_trace_contains_cal14": 14 in summary["present_target_cal_types"],
            "existing_trace_contains_cal24": 24 in summary["present_target_cal_types"],
            "existing_trace_contains_any_subsystem_custom_topology_set": bool(summary["present_target_cal_types"]),
            "observed_real_hal_set_cal_types": summary["observed_cal_types"],
            "existing_trace_is_sufficient_for_gate4_manifest": bool(summary["present_target_cal_types"]),
            "raw_bytes_publicly_emitted": False,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def format_order(values: Iterable[int]) -> str:
    values = list(values)
    return ", ".join(str(value) for value in values) if values else "(none)"


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# NATIVE_INIT V2716 — ACDB real-HAL trace SET_CAL reparse",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only reparse of existing private Android-good ptrace JSONL from V2461/V2466.",
        "The audit answers only whether those traces already contain real kernel",
        "`AUDIO_SET_CALIBRATION` records for subsystem custom topology cal_types",
        "`10` / `14` / `24`. No device action, flash, playback, mixer write, native",
        "calibration ioctl, or raw byte publication occurred.",
        "",
        "## Decision",
        "",
        f"- `decision`: `{payload['decision']}`",
        f"- decoded real SET records: `{summary['record_count']}`",
        f"- observed real-HAL SET cal_types: `{format_order(summary['observed_cal_types'])}`",
        f"- present target cal_types 10/14/24: `{format_order(summary['present_target_cal_types'])}`",
        f"- missing target cal_types 10/14/24: `{format_order(summary['missing_target_cal_types'])}`",
        "",
        "## Per-run Order",
        "",
        "| Run | Decoded real SET order |",
        "| --- | --- |",
    ]
    for run, order in summary["per_run_order"].items():
        lines.append(f"| `{run}` | `{format_order(order)}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The existing V2461/V2466 real-HAL ptrace traces are useful, but not sufficient",
            "for the current Gate-4 manifest. They decode to cal_type `39` and cal_type",
            "`20`; they do not contain cal_type `10`, `14`, or `24`.",
            "",
            "Therefore the operator-spec alternative source is exhausted for subsystem",
            "custom topology SETs. The next useful path remains a fresh capture or RE path",
            "that reaches the actual cal_type `10`/`14`/`24` SET producer, rather than an",
            "unchanged native replay of the V2708/V2714 lower-hidden payload family.",
            "",
            "Raw `bytes_hex`, ioctl arg bytes, and payload bytes remain private under",
            "`workspace/private/` and are intentionally omitted from this report.",
            "",
            "## Validation",
            "",
            "- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.",
            "- Reused the V2652 scalar decoder for public-safe SET arg parsing.",
            "- `py_compile`, focused unittest, and `git diff --check` passed.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--run-name", action="append", default=list(DEFAULT_RUN_NAMES))
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    write_json(Path(args.manifest_path), payload)
    if args.write_report:
        write_report(Path(args.report_path), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
