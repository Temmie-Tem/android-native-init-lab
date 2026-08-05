#!/usr/bin/env python3
"""Parse and compare low-overhead A90 automatic-handoff benchmark markers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


MARKER = "A90BENCH "
SCHEMA = "a90-boot-benchmark-v1"
RESULT_SCHEMA = "a90-boot-benchmark-result-v2"
COMPARISON_SCHEMA = "a90-boot-benchmark-comparison-v2"
STAGE_RE = re.compile(r"^[a-z0-9_]+$")
FIELDS = (
    "schema",
    "stage",
    "boottime_ms",
    "clock_ok",
    "telemetry_sampled",
    "sample_duration_ms",
    "prior_emit_duration_ms",
    "cpu_temp_c",
    "gpu_temp_c",
    "battery_temp_c",
    "cpu_usage_pct",
    "gpu_usage_pct",
    "memory_mb",
    "load1",
    "cpu0_khz",
    "cpu4_khz",
    "cpu7_khz",
    "gpu_hz",
    "battery_current_ua",
    "battery_voltage_uv",
    "power_now_raw",
    "power_avg_raw",
    "calculated_power_uw",
    "mmc_read_sectors",
    "mmc_write_sectors",
)
OPTIONAL_INTEGER_FIELDS = frozenset(
    {
        "cpu0_khz",
        "cpu4_khz",
        "cpu7_khz",
        "gpu_hz",
        "battery_current_ua",
        "battery_voltage_uv",
        "power_now_raw",
        "power_avg_raw",
        "calculated_power_uw",
        "mmc_read_sectors",
        "mmc_write_sectors",
    }
)
COMPLETE_STAGES = (
    "native_cache_stage_ready",
    "native_runtime_ready",
    "native_services_ready",
    "auto_handoff_dispatched",
    "handoff_begin",
    "source_sha_initial_done",
    "display_release_done",
    "source_sha_post_display_done",
    "work_copy_done",
    "loop_attached",
    "root_mounted",
    "distro_init_verified",
    "display_marker_ready",
    "mount_moves_done",
    "switch_root_exec",
)
PHASES = {
    "native_runtime_ms": ("native_cache_stage_ready", "native_runtime_ready"),
    "native_services_ms": ("native_runtime_ready", "native_services_ready"),
    "handoff_total_ms": ("auto_handoff_dispatched", "switch_root_exec"),
    "source_sha_initial_ms": ("handoff_begin", "source_sha_initial_done"),
    "display_release_ms": ("source_sha_initial_done", "display_release_done"),
    "source_sha_post_display_ms": (
        "display_release_done",
        "source_sha_post_display_done",
    ),
    "work_copy_ms": ("source_sha_post_display_done", "work_copy_done"),
    "loop_attach_ms": ("work_copy_done", "loop_attached"),
    "root_mount_ms": ("loop_attached", "root_mounted"),
    "distro_init_check_ms": ("root_mounted", "distro_init_verified"),
    "display_marker_ms": ("distro_init_verified", "display_marker_ready"),
    "mount_moves_ms": ("display_marker_ready", "mount_moves_done"),
    "switch_root_exec_prep_ms": ("mount_moves_done", "switch_root_exec"),
}


class BenchmarkError(RuntimeError):
    """Raised for malformed or incomparable benchmark evidence."""


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)


def load_texts(path: Path) -> list[str]:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BenchmarkError(f"cannot read benchmark input {path}: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return [body]
    texts = list(_walk_strings(parsed))
    return texts if texts else [body]


def marker_lines(texts: Iterable[str]) -> Iterable[str]:
    for text in texts:
        for line in text.replace("\r", "\n").splitlines():
            marker_at = line.find(MARKER)
            if marker_at >= 0:
                yield line[marker_at + len(MARKER) :].strip()


def _parse_optional_integer(field: str, value: str) -> int | None:
    if value == "na":
        return None
    try:
        return int(value, 10)
    except ValueError as exc:
        raise BenchmarkError(f"{field} is not an integer or na: {value!r}") from exc


def parse_marker(line: str) -> dict[str, Any]:
    tokens = line.split()
    keys: list[str] = []
    raw: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise BenchmarkError(f"marker token is not key=value: {token!r}")
        key, value = token.split("=", 1)
        if not key or not value or key in raw:
            raise BenchmarkError(f"marker has an invalid or duplicate field: {key!r}")
        keys.append(key)
        raw[key] = value
    if tuple(keys) != FIELDS:
        raise BenchmarkError(
            f"marker fields changed: got={tuple(keys)!r} expected={FIELDS!r}"
        )
    if raw["schema"] != SCHEMA:
        raise BenchmarkError(f"unexpected marker schema: {raw['schema']!r}")
    if STAGE_RE.fullmatch(raw["stage"]) is None:
        raise BenchmarkError(f"invalid stage: {raw['stage']!r}")
    try:
        boottime_ms = int(raw["boottime_ms"], 10)
    except ValueError as exc:
        raise BenchmarkError("boottime_ms is not an integer") from exc
    if boottime_ms < 0:
        raise BenchmarkError("boottime_ms is negative")
    try:
        clock_ok = int(raw["clock_ok"], 10)
        telemetry_sampled = int(raw["telemetry_sampled"], 10)
        sample_duration_ms = int(raw["sample_duration_ms"], 10)
        prior_emit_duration_ms = int(raw["prior_emit_duration_ms"], 10)
    except ValueError as exc:
        raise BenchmarkError("telemetry sampling fields are not integers") from exc
    if clock_ok != 1:
        raise BenchmarkError("CLOCK_BOOTTIME sampling was not exact")
    if (
        telemetry_sampled not in {0, 1}
        or sample_duration_ms < 0
        or prior_emit_duration_ms < 0
    ):
        raise BenchmarkError("telemetry sampling fields are out of range")

    record: dict[str, Any] = dict(raw)
    record["boottime_ms"] = boottime_ms
    record["clock_ok"] = clock_ok
    record["telemetry_sampled"] = telemetry_sampled
    record["sample_duration_ms"] = sample_duration_ms
    record["prior_emit_duration_ms"] = prior_emit_duration_ms
    for field in OPTIONAL_INTEGER_FIELDS:
        record[field] = _parse_optional_integer(field, raw[field])
    return record


def _result_from_records(
    records: list[dict[str, Any]],
    *,
    require_complete: bool,
) -> dict[str, Any]:
    if not records:
        raise BenchmarkError("benchmark boot segment is empty")
    by_stage = {record["stage"]: record for record in records}
    missing = [stage for stage in COMPLETE_STAGES if stage not in by_stage]
    if require_complete and missing:
        raise BenchmarkError(f"complete handoff markers missing: {missing!r}")
    if not missing:
        stage_indexes = {
            record["stage"]: index for index, record in enumerate(records)
        }
        complete_indexes = [stage_indexes[stage] for stage in COMPLETE_STAGES]
        if complete_indexes != sorted(complete_indexes):
            raise BenchmarkError("complete handoff stages are out of order")

    first_ms = records[0]["boottime_ms"]
    prior_ms = first_ms
    for record in records:
        record["since_first_ms"] = record["boottime_ms"] - first_ms
        record["since_previous_ms"] = record["boottime_ms"] - prior_ms
        prior_ms = record["boottime_ms"]

    phase_durations: dict[str, int | None] = {}
    record_indexes = {
        record["stage"]: index for index, record in enumerate(records)
    }
    for name, (start, end) in PHASES.items():
        if start in by_stage and end in by_stage:
            start_index = record_indexes[start]
            if start_index + 1 >= len(records):
                raise BenchmarkError(f"cannot recover emitter overhead for {start}")
            start_overhead_ms = records[start_index + 1][
                "prior_emit_duration_ms"
            ]
            phase_durations[name] = max(
                0,
                by_stage[end]["boottime_ms"]
                - by_stage[start]["boottime_ms"]
                - start_overhead_ms,
            )
        else:
            phase_durations[name] = None

    return {
        "schema": RESULT_SCHEMA,
        "status": "complete" if not missing else "partial",
        "missing_complete_stages": missing,
        "phase_durations_ms": phase_durations,
        "records": records,
    }


def parse_runs(texts: Iterable[str]) -> list[dict[str, Any]]:
    """Split an accumulated native log into monotonic, unique-stage boot segments."""

    segments: list[list[dict[str, Any]]] = []
    records: list[dict[str, Any]] = []
    by_stage: dict[str, dict[str, Any]] = {}
    previous_ms = -1
    for line in marker_lines(texts):
        record = parse_marker(line)
        stage = record["stage"]
        if stage in by_stage:
            if by_stage[stage] == record:
                continue
            segments.append(records)
            records = []
            by_stage = {}
            previous_ms = -1
        elif record["boottime_ms"] < previous_ms:
            segments.append(records)
            records = []
            by_stage = {}
            previous_ms = -1
        previous_ms = record["boottime_ms"]
        records.append(record)
        by_stage[stage] = record
    if records:
        segments.append(records)
    if not segments:
        raise BenchmarkError("no A90BENCH markers found")
    return [
        _result_from_records(segment, require_complete=False)
        for segment in segments
    ]


def parse_run(texts: Iterable[str], *, require_complete: bool = False) -> dict[str, Any]:
    segments = parse_runs(texts)
    handoff = [
        (index, value)
        for index, value in enumerate(segments)
        if {"auto_handoff_dispatched", "switch_root_exec"}.issubset(
            {record["stage"] for record in value["records"]}
        )
    ]
    if len(handoff) == 1:
        selected_index, selected = handoff[0]
    elif len(segments) == 1:
        selected_index, selected = 0, segments[0]
    elif not handoff:
        raise BenchmarkError("accumulated log has no unique handoff boot segment")
    else:
        raise BenchmarkError("accumulated log has multiple handoff boot segments")
    selected["boot_segments_total"] = len(segments)
    selected["selected_segment_index"] = selected_index
    if require_complete and selected["missing_complete_stages"]:
        raise BenchmarkError(
            "complete handoff markers missing: "
            f"{selected['missing_complete_stages']!r}"
        )
    return selected


def compare_runs(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    if baseline.get("schema") != RESULT_SCHEMA or candidate.get("schema") != RESULT_SCHEMA:
        raise BenchmarkError("comparison inputs are not parsed benchmark results")
    baseline_phases = baseline["phase_durations_ms"]
    candidate_phases = candidate["phase_durations_ms"]
    phases: dict[str, dict[str, int | None]] = {}
    for name in PHASES:
        before = baseline_phases[name]
        after = candidate_phases[name]
        phases[name] = {
            "baseline_ms": before,
            "candidate_ms": after,
            "delta_ms": None if before is None or after is None else after - before,
        }
    return {
        "schema": COMPARISON_SCHEMA,
        "baseline_status": baseline["status"],
        "candidate_status": candidate["status"],
        "phase_comparison": phases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="raw console/log text or JSON receipt")
    parser.add_argument(
        "--compare",
        type=Path,
        help="second input to compare against the baseline input",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="reject inputs missing any complete switch_root stage",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        baseline = parse_run(
            load_texts(args.input), require_complete=args.require_complete
        )
        if args.compare is None:
            result = baseline
        else:
            candidate = parse_run(
                load_texts(args.compare), require_complete=args.require_complete
            )
            result = compare_runs(baseline, candidate)
    except BenchmarkError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
