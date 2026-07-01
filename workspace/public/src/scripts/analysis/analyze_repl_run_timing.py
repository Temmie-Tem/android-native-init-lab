#!/usr/bin/env python3
"""Aggregate REPL live-call-proof run timings to find average phase times + the bottleneck.

Host-only. Reads the private `timeline.json` evidence emitted by the device-touching
V-iterations (per the GOAL.md 2026-07-01 timing rule) and reports per-phase mean / median /
min / max / p95 across runs, plus which phase dominates (the bottleneck) and the flash-vs-work
split that sizes a batching win. NO device action.

Canonical schema:
  {"events": [{"name": "...", "timestamp_utc": "..."}, ...]}

The timeline document must have no top-level ad-hoc objects such as "phases",
"commands", "steps", or "timeline".  This keeps cross-run aggregation stable.

Usage:
  python3 workspace/public/src/scripts/analysis/analyze_repl_run_timing.py \
    [--runs-dir workspace/private/runs/kernel] [--batch-size 10] \
    [--resident-batches 10] [--warm-reboot-sec 15] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_RUNS = REPO_ROOT / "workspace/private/runs/kernel"

REQUIRED_EVENT_NAMES = (
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "live_session_start",
    "live_session_end",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
)

# Canonical phases: (label, start-name, end-name).
PHASES = [
    ("candidate flash", "candidate_flash_start", "candidate_flash_done"),
    ("candidate boot/health", "candidate_flash_done", "candidate_boot_ready"),
    ("live session (work)", "live_session_start", "live_session_end"),
    ("rollback flash", "rollback_flash_start", "rollback_flash_done"),
    ("rollback boot/health", "rollback_flash_done", "rollback_boot_ready"),
]


def parse_ts(s: str) -> dt.datetime | None:
    if not isinstance(s, str):
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        return None
    return parsed


def validate_events_schema(doc) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["timeline document must be an object"]
    if set(doc) != {"events"}:
        found = ", ".join(sorted(str(k) for k in doc)) or "<empty>"
        errors.append(f"timeline top-level keys must be exactly events; found {found}")
    events = doc.get("events")
    if not isinstance(events, list):
        errors.append("events must be a list")
        return errors
    seen: set[str] = set()
    for index, ev in enumerate(events):
        if not isinstance(ev, dict):
            errors.append(f"events[{index}] must be an object")
            continue
        if set(ev) != {"name", "timestamp_utc"}:
            found = ", ".join(sorted(str(k) for k in ev)) or "<empty>"
            errors.append(f"events[{index}] keys must be exactly name,timestamp_utc; found {found}")
            continue
        name = ev.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"events[{index}].name must be a non-empty string")
            continue
        seen.add(name)
        if parse_ts(ev.get("timestamp_utc")) is None:
            errors.append(f"events[{index}].timestamp_utc must be UTC ISO8601")
    missing = [name for name in REQUIRED_EVENT_NAMES if name not in seen]
    if missing:
        errors.append("missing required events: " + ", ".join(missing))
    return errors


def extract_names(doc) -> dict[str, dt.datetime]:
    """Return {event_name: earliest UTC timestamp} from the canonical events schema."""
    out: dict[str, dt.datetime] = {}
    if validate_events_schema(doc):
        return out

    events = doc["events"]
    def put(name: str, ts: dt.datetime | None) -> None:
        if ts is None or not name:
            return
        # Keep the first occurrence for retry-style events.
        if name not in out or ts < out[name]:
            out[name] = ts

    for ev in events:
        put(ev["name"], parse_ts(ev["timestamp_utc"]))
    return out


def phase_elapsed(names: dict[str, dt.datetime], start: str, end: str):
    s = names.get(start)
    e = names.get(end)
    if s is not None and e is not None and (e - s).total_seconds() >= 0:
        return (e - s).total_seconds()
    return None


def fmt(x: float) -> str:
    return f"{x:6.1f}s"


def phase_stats(per_phase: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    def stats(v: list[float]) -> dict[str, float]:
        if not v:
            return {}
        sv = sorted(v)
        p95 = sv[min(len(sv) - 1, int(round(0.95 * (len(sv) - 1))))]
        return {
            "n": len(v),
            "mean": statistics.mean(v),
            "median": statistics.median(v),
            "min": min(v),
            "max": max(v),
            "p95": p95,
        }

    return {label: stats(v) for label, v in per_phase.items()}


def mean_phase(summary: dict[str, dict[str, float]], label: str) -> float | None:
    value = summary.get(label, {}).get("mean")
    return float(value) if value is not None else None


def resident_session_projection(
    summary: dict[str, dict[str, float]],
    *,
    batch_size: int,
    resident_batches: int,
    warm_reboot_sec: float,
) -> dict[str, float | int | str]:
    """Project the RESIDENT-SESSION MODE timing win from canonical run means.

    The current canonical timeline is one bounded work unit bracketed by a candidate flash
    and a rollback flash.  Resident mode keeps one v1-repl flash for many bounded batches,
    warm-rebooting v1-repl between batches and rolling back once at the end.
    """
    required = {
        "candidate_flash_sec": mean_phase(summary, "candidate flash"),
        "candidate_boot_health_sec": mean_phase(summary, "candidate boot/health"),
        "work_batch_sec": mean_phase(summary, "live session (work)"),
        "rollback_flash_sec": mean_phase(summary, "rollback flash"),
        "rollback_boot_health_sec": mean_phase(summary, "rollback boot/health"),
    }
    if any(value is None for value in required.values()):
        missing = [key for key, value in required.items() if value is None]
        return {"ok": 0, "reason": "missing phase means: " + ", ".join(missing)}

    candidate_flash = float(required["candidate_flash_sec"])
    candidate_boot = float(required["candidate_boot_health_sec"])
    work_batch = float(required["work_batch_sec"])
    rollback_flash = float(required["rollback_flash_sec"])
    rollback_boot = float(required["rollback_boot_health_sec"])
    old_batch_sec = candidate_flash + candidate_boot + work_batch + rollback_flash + rollback_boot
    old_in_boot_per_target = old_batch_sec / batch_size
    resident_total = (
        candidate_flash
        + candidate_boot
        + resident_batches * (warm_reboot_sec + work_batch)
        + rollback_flash
        + rollback_boot
    )
    resident_target_count = resident_batches * batch_size
    resident_per_target = resident_total / resident_target_count
    return {
        "ok": 1,
        "batch_size": batch_size,
        "resident_batches": resident_batches,
        "warm_reboot_sec": warm_reboot_sec,
        "old_flashes": 2 * resident_batches,
        "resident_flashes": 2,
        "old_batch_sec": old_batch_sec,
        "old_in_boot_per_target_sec": old_in_boot_per_target,
        "resident_session_total_sec": resident_total,
        "resident_per_target_sec": resident_per_target,
        "speedup_vs_unbatched_unit": old_batch_sec / resident_per_target,
        "speedup_vs_per_unit_in_boot_batch": old_in_boot_per_target / resident_per_target,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    ap.add_argument("--batch-size", type=int, default=10,
                    help="targets per bounded batch for projection; RESIDENT-SESSION guidance is 10-30")
    ap.add_argument("--resident-batches", type=int, default=10,
                    help="bounded batches per resident v1-repl session")
    ap.add_argument("--warm-reboot-sec", type=float, default=15.0,
                    help="estimated v1-repl warm reboot cost between resident batches")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()
    if args.batch_size <= 0:
        ap.error("--batch-size must be positive")
    if args.resident_batches <= 0:
        ap.error("--resident-batches must be positive")
    if args.warm_reboot_sec < 0:
        ap.error("--warm-reboot-sec must be non-negative")

    tls = sorted(args.runs_dir.glob("*/timeline.json"))
    per_phase: dict[str, list[float]] = {label: [] for label, _, _ in PHASES}
    runs_used = 0
    invalid: list[dict[str, object]] = []
    for tl in tls:
        try:
            doc = json.loads(tl.read_text())
        except (json.JSONDecodeError, OSError):
            invalid.append({"path": str(tl), "errors": ["timeline is not readable JSON"]})
            continue
        errors = validate_events_schema(doc)
        if errors:
            invalid.append({"path": str(tl), "errors": errors})
            continue
        names = extract_names(doc)
        if not names:
            continue
        runs_used += 1
        for label, start, end in PHASES:
            d = phase_elapsed(names, start, end)
            if d is not None:
                per_phase[label].append(d)

    summary = phase_stats(per_phase)
    resident = resident_session_projection(
        summary,
        batch_size=args.batch_size,
        resident_batches=args.resident_batches,
        warm_reboot_sec=args.warm_reboot_sec,
    )

    if args.json:
        print(json.dumps({"runs_dir": str(args.runs_dir), "timelines_found": len(tls),
                          "runs_used": runs_used, "invalid_timelines": invalid,
                          "required_events": list(REQUIRED_EVENT_NAMES),
                          "phases": summary,
                          "resident_session_projection": resident}, indent=2))
        return 0

    print(f"REPL run timing - {runs_used}/{len(tls)} canonical events timelines parsed from {args.runs_dir}")
    if invalid:
        print(f"Skipped {len(invalid)} non-canonical timeline(s); run with --json for details.")
    print()
    print(f"{'phase':24} {'n':>3} {'mean':>7} {'median':>7} {'min':>7} {'max':>7} {'p95':>7}")
    print("-" * 68)
    flash_total = 0.0
    work = 0.0
    for label, _, _ in PHASES:
        s = summary[label]
        if not s:
            print(f"{label:24} {'--':>3} {'(no data)':>7}")
            continue
        print(f"{label:24} {s['n']:>3} {fmt(s['mean'])} {fmt(s['median'])} "
              f"{fmt(s['min'])} {fmt(s['max'])} {fmt(s['p95'])}")
        if "flash" in label:
            flash_total += s["mean"]
        if "work" in label:
            work = s["mean"]

    # bottleneck + batching-win sizing
    means = {label: summary[label]["mean"] for label, _, _ in PHASES if summary[label]}
    if means:
        bott = max(means, key=means.get)
        print(f"\nBOTTLENECK: '{bott}' (mean {fmt(means[bott]).strip()}) dominates the iteration.")
    if flash_total and work:
        per_target_now = flash_total + work
        for n in (5, 10):
            batched = (flash_total + n * work) / n
            print(f"  flash overhead ~{flash_total:.0f}s vs work ~{work:.0f}s → "
                  f"batch {n}/boot ≈ {batched:.0f}s/target "
                  f"({per_target_now / batched:.1f}x vs {per_target_now:.0f}s now)")
    if resident.get("ok"):
        print("\nRESIDENT-SESSION projection "
              f"(batch_size={resident['batch_size']}, batches={resident['resident_batches']}, "
              f"warm_reboot={resident['warm_reboot_sec']:.1f}s):")
        print(f"  flashes: {resident['old_flashes']} -> {resident['resident_flashes']}")
        print(f"  old in-boot batch: {resident['old_in_boot_per_target_sec']:.1f}s/target")
        print(f"  resident session:  {resident['resident_per_target_sec']:.1f}s/target "
              f"over {resident['resident_session_total_sec']:.1f}s total")
        print(f"  speedup: {resident['speedup_vs_unbatched_unit']:.1f}x vs per-unit flash, "
              f"{resident['speedup_vs_per_unit_in_boot_batch']:.1f}x vs per-unit in-boot batch")
    else:
        print(f"\nRESIDENT-SESSION projection unavailable: {resident.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
