#!/usr/bin/env python3
"""Collect A90 native-init scheduler/run-loop latency baseline samples."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import run_cmdv1_command  # noqa: E402
from tcpctl_host import DEFAULT_BRIDGE_HOST, DEFAULT_BRIDGE_PORT, DEFAULT_TOYBOX  # noqa: E402


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class CommandRecord:
    label: str
    command: list[str]
    rc: int | None
    status: str
    duration_sec: float
    duration_ms: int | None
    ok: bool
    output_file: str | None


@dataclass
class LatencySample:
    profile: str
    index: int
    duration_ms: int
    expected_ms: float
    excess_ms: float
    host_roundtrip_ms: float
    missed: bool


@dataclass
class LatencyStats:
    profile: str
    count: int
    min_ms: float | None
    max_ms: float | None
    avg_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    max_excess_ms: float | None
    missed_count: int


def nofollow_flag() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def cloexec_flag() -> int:
    return getattr(os, "O_CLOEXEC", 0)


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=PRIVATE_DIR_MODE, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory output path: {path}")
    path.chmod(PRIVATE_DIR_MODE)


def write_private_bytes(path: Path, data: bytes) -> None:
    ensure_private_dir(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | cloexec_flag() | nofollow_flag()
    fd = os.open(path, flags, PRIVATE_FILE_MODE)
    try:
        with os.fdopen(fd, "wb") as file_obj:
            fd = -1
            file_obj.write(data)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def write_private_text(path: Path, text: str) -> None:
    write_private_bytes(path, text.encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--run-id", default=f"v164-{int(time.time())}")
    parser.add_argument("--out-dir", default="tmp/soak/scheduler-latency")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--sleep-us", type=int, default=10_000)
    parser.add_argument("--deadline-ms", type=float, default=250.0)
    parser.add_argument("--stress-sec", type=int, default=2)
    parser.add_argument("--stress-workers", type=int, default=2)
    parser.add_argument("--io-mb", type=int, default=8)
    return parser.parse_args()


def add_check(checks: list[Check], name: str, ok: bool, detail: str) -> None:
    checks.append(Check(name=name, ok=ok, detail=detail))


def run_cmd(args: argparse.Namespace,
            label: str,
            command: list[str],
            out_dir: Path,
            checks: list[Check],
            *,
            allow_error: bool = False,
            retry_unsafe: bool = False,
            timeout: float | None = None) -> CommandRecord:
    started = time.monotonic()
    output_file = out_dir / "commands" / f"{label}.txt"
    try:
        result = run_cmdv1_command(
            args.bridge_host,
            args.bridge_port,
            args.bridge_timeout if timeout is None else timeout,
            command,
            retry_unsafe=retry_unsafe,
        )
        elapsed = time.monotonic() - started
        write_private_text(output_file, result.text)
        ok = result.rc == 0 and result.status == "ok"
        duration_ms = None
        if "duration_ms" in result.end:
            try:
                duration_ms = int(result.end["duration_ms"], 0)
            except ValueError:
                duration_ms = None
        if not ok and not allow_error:
            add_check(checks, label, False, f"rc={result.rc} status={result.status}")
        return CommandRecord(label, command, result.rc, result.status, elapsed, duration_ms, ok, str(output_file))
    except Exception as exc:  # noqa: BLE001 - evidence capture
        elapsed = time.monotonic() - started
        write_private_text(output_file, f"{type(exc).__name__}: {exc}\n")
        if not allow_error:
            add_check(checks, label, False, str(exc))
        return CommandRecord(label, command, None, "exception", elapsed, None, False, str(output_file))


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile_value * len(ordered)) - 1))
    return ordered[index]


def stats_for(profile: str, samples: list[LatencySample]) -> LatencyStats:
    values = [sample.duration_ms for sample in samples if sample.profile == profile]
    excess = [sample.excess_ms for sample in samples if sample.profile == profile]
    missed = [sample for sample in samples if sample.profile == profile and sample.missed]
    return LatencyStats(
        profile=profile,
        count=len(values),
        min_ms=min(values) if values else None,
        max_ms=max(values) if values else None,
        avg_ms=mean(values) if values else None,
        p95_ms=percentile([float(value) for value in values], 0.95),
        p99_ms=percentile([float(value) for value in values], 0.99),
        max_excess_ms=max(excess) if excess else None,
        missed_count=len(missed),
    )


def collect_profile(args: argparse.Namespace,
                    profile: str,
                    out_dir: Path,
                    checks: list[Check]) -> tuple[list[LatencySample], list[CommandRecord]]:
    expected_ms = args.sleep_us / 1000.0
    samples: list[LatencySample] = []
    records: list[CommandRecord] = []
    for index in range(args.samples):
        record = run_cmd(
            args,
            f"{profile}-{index:03d}",
            ["run", args.toybox, "usleep", str(args.sleep_us)],
            out_dir,
            checks,
            retry_unsafe=True,
            timeout=args.bridge_timeout,
        )
        records.append(record)
        if record.duration_ms is None:
            add_check(checks, f"{profile}-{index:03d}-duration", False, "missing duration_ms")
            continue
        host_roundtrip_ms = record.duration_sec * 1000.0
        excess_ms = max(0.0, record.duration_ms - expected_ms)
        samples.append(
            LatencySample(
                profile=profile,
                index=index,
                duration_ms=record.duration_ms,
                expected_ms=expected_ms,
                excess_ms=excess_ms,
                host_roundtrip_ms=host_roundtrip_ms,
                missed=record.duration_ms > args.deadline_ms,
            )
        )
    return samples, records


def run_tmpfs_io(args: argparse.Namespace, out_dir: Path, checks: list[Check]) -> list[CommandRecord]:
    path = f"/tmp/a90-{args.run_id}-latency-io.bin"
    block_size = 1024 * 1024
    records = [
        run_cmd(
            args,
            "io-dd",
            ["run", args.toybox, "dd", "if=/dev/zero", f"of={path}", f"bs={block_size}", f"count={args.io_mb}"],
            out_dir,
            checks,
            retry_unsafe=True,
            timeout=max(args.bridge_timeout, 30.0),
        ),
        run_cmd(
            args,
            "io-sync",
            ["sync"],
            out_dir,
            checks,
            retry_unsafe=True,
        ),
        run_cmd(
            args,
            "io-cleanup",
            ["run", args.toybox, "rm", "-f", path],
            out_dir,
            checks,
            allow_error=True,
            retry_unsafe=True,
        ),
    ]
    add_check(checks, "tmpfs io profile", all(record.ok for record in records), f"ok={sum(1 for item in records if item.ok)} total={len(records)}")
    return records


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir) / args.run_id
    ensure_private_dir(out_dir)
    checks: list[Check] = []
    records: list[CommandRecord] = []
    samples: list[LatencySample] = []
    started = time.monotonic()

    records.append(run_cmd(args, "initial-hide", ["hide"], out_dir, checks, allow_error=True))
    profile_samples, profile_records = collect_profile(args, "idle", out_dir, checks)
    samples.extend(profile_samples)
    records.extend(profile_records)

    records.append(
        run_cmd(
            args,
            "cpustress-primer",
            ["run", "/bin/a90_cpustress", str(args.stress_sec), str(args.stress_workers)],
            out_dir,
            checks,
            retry_unsafe=True,
            timeout=max(args.bridge_timeout, args.stress_sec + 20.0),
        )
    )
    profile_samples, profile_records = collect_profile(args, "post-cpustress", out_dir, checks)
    samples.extend(profile_samples)
    records.extend(profile_records)

    records.extend(run_tmpfs_io(args, out_dir, checks))
    profile_samples, profile_records = collect_profile(args, "post-tmpfs-io", out_dir, checks)
    samples.extend(profile_samples)
    records.extend(profile_records)

    records.append(run_cmd(args, "final-status", ["status"], out_dir, checks))
    records.append(run_cmd(args, "final-longsoak", ["longsoak", "status", "verbose"], out_dir, checks))

    profiles = ["idle", "post-cpustress", "post-tmpfs-io"]
    stats = [stats_for(profile, samples) for profile in profiles]
    for item in stats:
        add_check(checks, f"{item.profile} sample count", item.count == args.samples, f"count={item.count} expected={args.samples}")
        add_check(checks, f"{item.profile} missed deadlines", item.missed_count == 0, f"missed={item.missed_count} deadline={args.deadline_ms}ms")
    add_check(checks, "cpustress primer", any(record.label == "cpustress-primer" and record.ok for record in records), "post-cpustress profile prepared")
    add_check(checks, "final status", records[-2].ok, f"rc={records[-2].rc} status={records[-2].status}")
    add_check(checks, "final longsoak", records[-1].ok, f"rc={records[-1].rc} status={records[-1].status}")

    elapsed = time.monotonic() - started
    pass_ok = all(item.ok for item in checks)
    report: dict[str, Any] = {
        "pass": pass_ok,
        "run_id": args.run_id,
        "duration_sec": elapsed,
        "args": {
            "samples": args.samples,
            "sleep_us": args.sleep_us,
            "deadline_ms": args.deadline_ms,
            "stress_sec": args.stress_sec,
            "stress_workers": args.stress_workers,
            "io_mb": args.io_mb,
        },
        "limitations": [
            "This v164 baseline uses toybox usleep through PID1 run/cmdv1 as a scheduler/run-loop proxy.",
            "True clock_nanosleep cyclictest-style helper deployment is deferred until a binary deploy path is available without host sudo friction.",
        ],
        "stats": [asdict(item) for item in stats],
        "samples": [asdict(item) for item in samples],
        "commands": [asdict(item) for item in records],
        "checks": [asdict(item) for item in checks],
    }
    lines = [
        "# A90 Scheduler/Latency Baseline Report\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- run_id: `{args.run_id}`\n",
        f"- duration_sec: `{elapsed:.3f}`\n",
        f"- samples_per_profile: `{args.samples}`\n",
        f"- sleep_us: `{args.sleep_us}`\n",
        f"- deadline_ms: `{args.deadline_ms}`\n\n",
        "## Profile Stats\n\n",
        "| Profile | Count | Min ms | Avg ms | P95 ms | P99 ms | Max ms | Max Excess ms | Missed |\n",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n",
    ]
    for item in stats:
        lines.append(
            f"| `{item.profile}` | `{item.count}` | `{item.min_ms}` | `{item.avg_ms}` | "
            f"`{item.p95_ms}` | `{item.p99_ms}` | `{item.max_ms}` | "
            f"`{item.max_excess_ms}` | `{item.missed_count}` |\n"
        )
    lines.extend([
        "\n## Checks\n\n",
        "| Check | Result | Detail |\n",
        "|---|---|---|\n",
    ])
    for item in checks:
        lines.append(f"| `{item.name}` | `{'PASS' if item.ok else 'FAIL'}` | `{item.detail}` |\n")
    write_private_text(out_dir / "scheduler-latency-report.json", json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "scheduler-latency-report.md", "".join(lines))
    print(f"{'PASS' if pass_ok else 'FAIL'} run_id={args.run_id} duration={elapsed:.3f}s")
    print(out_dir / "scheduler-latency-report.md")
    print(out_dir / "scheduler-latency-report.json")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
