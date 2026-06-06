#!/usr/bin/env python3
"""Validate A90 native-init CPU, memory, thermal, and power stability."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import run_cmdv1_command  # noqa: E402
from tcpctl_host import DEFAULT_BRIDGE_HOST, DEFAULT_BRIDGE_PORT, DEFAULT_TOYBOX, host_ping  # noqa: E402


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
CONTROLLED_PROCESS_NAMES = {"a90_cpustress", "toybox", "a90sleep"}


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
    ok: bool
    output_file: str | None


@dataclass
class StatusSample:
    label: str
    command_duration_ms: int | None
    uptime_sec: float | None
    load_1m: float | None
    battery_percent: int | None
    battery_temp_c: float | None
    power_now_w: float | None
    power_avg_w: float | None
    cpu_temp_c: float | None
    cpu_usage_percent: int | None
    gpu_temp_c: float | None
    gpu_usage_percent: int | None
    mem_used_mb: int | None
    mem_total_mb: int | None
    longsoak_health: str | None


@dataclass
class MemoryCheck:
    size_bytes: int
    path: str
    expected_sha256: str
    device_sha256: str | None
    write_ok: bool
    hash_ok: bool
    cleanup_ok: bool


@dataclass
class ProcessSnapshot:
    pid_count: int
    zombie_count: int
    controlled_zombie_count: int
    pid1_fd_count: int | None


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


def add_check(checks: list[Check], name: str, ok: bool, detail: str) -> None:
    checks.append(Check(name=name, ok=ok, detail=detail))


def parse_size(text: str) -> int:
    value = text.strip()
    if not value:
        raise ValueError("empty size")
    suffix = value[-1].lower()
    multiplier = 1
    if suffix == "k":
        multiplier = 1024
        value = value[:-1]
    elif suffix == "m":
        multiplier = 1024 * 1024
        value = value[:-1]
    size = int(value, 10) * multiplier
    if size <= 0:
        raise ValueError(f"invalid size: {text}")
    return size


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--run-id", default=f"v163-{int(time.time())}")
    parser.add_argument("--out-dir", default="tmp/soak/cpu-mem-thermal")
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--stress-sec", type=int, default=3)
    parser.add_argument("--stress-workers", type=int, default=2)
    parser.add_argument("--mem-size", default="32M")
    parser.add_argument("--max-cpu-temp-c", type=float, default=85.0)
    parser.add_argument("--max-gpu-temp-c", type=float, default=85.0)
    parser.add_argument("--max-battery-temp-c", type=float, default=45.0)
    parser.add_argument("--max-status-duration-ms", type=int, default=2000)
    parser.add_argument("--host-ping", action="store_true", help="record host NCM ping checks as warnings only")
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ping-count", type=int, default=1)
    return parser.parse_args()


def run_cmd(args: argparse.Namespace,
            label: str,
            command: list[str],
            out_dir: Path,
            checks: list[Check],
            *,
            allow_error: bool = False,
            retry_unsafe: bool = False,
            timeout: float | None = None,
            attempts: int = 1) -> CommandRecord:
    output_file = out_dir / "commands" / f"{label}.txt"
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            result = run_cmdv1_command(
                args.bridge_host,
                args.bridge_port,
                args.bridge_timeout if timeout is None else timeout,
                command,
                retry_unsafe=retry_unsafe,
            )
            duration = time.monotonic() - started
            write_private_text(output_file, result.text)
            ok = result.rc == 0 and result.status == "ok"
            if not ok and not allow_error:
                add_check(checks, label, False, f"rc={result.rc} status={result.status}")
            return CommandRecord(label, command, result.rc, result.status, duration, ok, str(output_file))
        except Exception as exc:  # noqa: BLE001 - validator keeps failure evidence
            last_exc = exc
            if attempt < attempts:
                time.sleep(0.5)
                continue
            duration = time.monotonic() - started
            write_private_text(output_file, f"{type(exc).__name__}: {exc}\n")
            if not allow_error:
                add_check(checks, label, False, str(exc))
            return CommandRecord(label, command, None, "exception", duration, False, str(output_file))
    raise RuntimeError(f"unreachable command retry state: {last_exc}")


def read_status_sample(args: argparse.Namespace, label: str, out_dir: Path) -> tuple[StatusSample, CommandRecord]:
    checks: list[Check] = []
    record = run_cmd(args, f"status-{label}", ["status"], out_dir, checks, attempts=2)
    text = Path(record.output_file).read_text(encoding="utf-8", errors="replace") if record.output_file else ""
    sample = parse_status_text(label, text)
    sample.command_duration_ms = None
    match = re.search(r"A90P1 END .* duration_ms=([0-9]+)", text)
    if match:
        sample.command_duration_ms = int(match.group(1))
    return sample, record


def parse_status_text(label: str, text: str) -> StatusSample:
    sample = StatusSample(
        label=label,
        command_duration_ms=None,
        uptime_sec=None,
        load_1m=None,
        battery_percent=None,
        battery_temp_c=None,
        power_now_w=None,
        power_avg_w=None,
        cpu_temp_c=None,
        cpu_usage_percent=None,
        gpu_temp_c=None,
        gpu_usage_percent=None,
        mem_used_mb=None,
        mem_total_mb=None,
        longsoak_health=None,
    )
    if match := re.search(r"uptime:\s*([0-9.]+)s\s+load=([0-9.]+)", text):
        sample.uptime_sec = float(match.group(1))
        sample.load_1m = float(match.group(2))
    if match := re.search(r"battery:\s*([0-9]+)% .* temp=([0-9.]+)C", text):
        sample.battery_percent = int(match.group(1))
        sample.battery_temp_c = float(match.group(2))
    if match := re.search(r"power:\s*now=([0-9.]+)W\s+avg=([0-9.]+)W", text):
        sample.power_now_w = float(match.group(1))
        sample.power_avg_w = float(match.group(2))
    if match := re.search(r"thermal:\s*cpu=([0-9.]+)C\s+([0-9]+)%\s+gpu=([0-9.]+)C\s+([0-9]+)%", text):
        sample.cpu_temp_c = float(match.group(1))
        sample.cpu_usage_percent = int(match.group(2))
        sample.gpu_temp_c = float(match.group(3))
        sample.gpu_usage_percent = int(match.group(4))
    if match := re.search(r"memory:\s*([0-9]+)/([0-9]+)MB used", text):
        sample.mem_used_mb = int(match.group(1))
        sample.mem_total_mb = int(match.group(2))
    if match := re.search(r"longsoak:\s*health=([a-zA-Z0-9_-]+)", text):
        sample.longsoak_health = match.group(1)
    return sample


def zero_sha256(size: int) -> str:
    digest = hashlib.sha256()
    chunk = b"\0" * (1024 * 1024)
    remaining = size
    while remaining > 0:
        take = min(remaining, len(chunk))
        digest.update(chunk[:take])
        remaining -= take
    return digest.hexdigest()


def parse_sha256(text: str) -> str | None:
    for word in text.split():
        if len(word) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in word):
            return word.lower()
    return None


def run_memory_verify(args: argparse.Namespace,
                      out_dir: Path,
                      checks: list[Check]) -> MemoryCheck:
    size = parse_size(args.mem_size)
    path = f"/tmp/a90-{args.run_id}-mem.bin"
    expected = zero_sha256(size)
    block_size = 1024 * 1024
    count = max(1, size // block_size)
    write = run_cmd(
        args,
        "mem-dd",
        ["run", args.toybox, "dd", "if=/dev/zero", f"of={path}", f"bs={block_size}", f"count={count}"],
        out_dir,
        checks,
        timeout=max(args.bridge_timeout, 30.0),
    )
    sha = run_cmd(
        args,
        "mem-sha256",
        ["run", args.toybox, "sha256sum", path],
        out_dir,
        checks,
    )
    device_sha = None
    if sha.output_file:
        device_sha = parse_sha256(Path(sha.output_file).read_text(encoding="utf-8", errors="replace"))
    cleanup = run_cmd(
        args,
        "mem-cleanup",
        ["run", args.toybox, "rm", "-f", path],
        out_dir,
        checks,
        allow_error=True,
    )
    result = MemoryCheck(
        size_bytes=size,
        path=path,
        expected_sha256=expected,
        device_sha256=device_sha,
        write_ok=write.ok,
        hash_ok=device_sha == expected,
        cleanup_ok=cleanup.ok,
    )
    add_check(
        checks,
        "tmpfs memory verify",
        result.write_ok and result.hash_ok and result.cleanup_ok,
        f"size={size} hash_ok={result.hash_ok} cleanup={cleanup.status}/{cleanup.rc}",
    )
    return result


def process_snapshot(args: argparse.Namespace, out_dir: Path) -> ProcessSnapshot:
    result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm"],
    )
    write_private_text(out_dir / "process-ps.txt", result.text)
    pid_count = 0
    zombie_count = 0
    controlled_zombies = 0
    for line in result.text.splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3 or not parts[0].isdigit():
            continue
        pid_count += 1
        stat_text = parts[1]
        name = parts[2].strip()
        if name.startswith("[") and name.endswith("]"):
            name = name[1:-1]
        if stat_text.startswith("Z"):
            zombie_count += 1
            if name in CONTROLLED_PROCESS_NAMES or name.startswith("a90_"):
                controlled_zombies += 1
    fd_count = None
    try:
        fd_result = run_cmdv1_command(
            args.bridge_host,
            args.bridge_port,
            args.bridge_timeout,
            ["ls", "/proc/1/fd"],
        )
        fd_count = 0
        for line in fd_result.text.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[-1].isdigit() and parts[0][0] in {"-", "d", "l", "c", "b"}:
                fd_count += 1
    except Exception:
        fd_count = None
    return ProcessSnapshot(pid_count, zombie_count, controlled_zombies, fd_count)


def maybe_host_ping(args: argparse.Namespace, label: str, out_dir: Path) -> dict[str, Any]:
    if not args.host_ping:
        return {"label": label, "enabled": False, "ok": None, "error": ""}
    try:
        text = host_ping(args, args.ping_count)
        write_private_text(out_dir / f"host-ping-{label}.txt", text)
        return {"label": label, "enabled": True, "ok": "0% packet loss" in text, "error": ""}
    except Exception as exc:  # noqa: BLE001 - ping is warning-only in v163
        write_private_text(out_dir / f"host-ping-{label}.txt", f"{type(exc).__name__}: {exc}\n")
        return {"label": label, "enabled": True, "ok": False, "error": str(exc)}


def sample_extreme(samples: list[StatusSample], field: str) -> float | int | None:
    values = [getattr(sample, field) for sample in samples if getattr(sample, field) is not None]
    return max(values) if values else None


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir) / args.run_id
    ensure_private_dir(out_dir)
    checks: list[Check] = []
    started = time.monotonic()
    command_records: list[CommandRecord] = []
    samples: list[StatusSample] = []
    pings: list[dict[str, Any]] = []

    command_records.append(run_cmd(args, "initial-hide", ["hide"], out_dir, checks, allow_error=True))
    command_records.append(
        run_cmd(
            args,
            "longsoak-start",
            ["longsoak", "start", "15"],
            out_dir,
            checks,
            allow_error=True,
        )
    )
    memory = run_memory_verify(args, out_dir, checks)
    sample, record = read_status_sample(args, "baseline", out_dir)
    samples.append(sample)
    command_records.append(record)
    pings.append(maybe_host_ping(args, "baseline", out_dir))

    for index in range(1, args.cycles + 1):
        stress = run_cmd(
            args,
            f"cpustress-{index:02d}",
            ["run", "/bin/a90_cpustress", str(args.stress_sec), str(args.stress_workers)],
            out_dir,
            checks,
            timeout=max(args.bridge_timeout, args.stress_sec + 20.0),
        )
        command_records.append(stress)
        sample, record = read_status_sample(args, f"cycle-{index:02d}", out_dir)
        samples.append(sample)
        command_records.append(record)
        pings.append(maybe_host_ping(args, f"cycle-{index:02d}", out_dir))

    process = process_snapshot(args, out_dir)
    final_selftest = run_cmd(args, "final-selftest", ["selftest", "verbose"], out_dir, checks)
    final_longsoak = run_cmd(args, "final-longsoak", ["longsoak", "status", "verbose"], out_dir, checks)
    command_records.extend([final_selftest, final_longsoak])

    stress_records = [record for record in command_records if record.label.startswith("cpustress-")]
    status_records = [record for record in command_records if record.label.startswith("status-")]
    max_cpu = sample_extreme(samples, "cpu_temp_c")
    max_gpu = sample_extreme(samples, "gpu_temp_c")
    max_battery = sample_extreme(samples, "battery_temp_c")
    max_power = sample_extreme(samples, "power_now_w")
    max_mem = sample_extreme(samples, "mem_used_mb")
    max_status_ms = sample_extreme(samples, "command_duration_ms")

    add_check(checks, "cpustress cycles", all(record.ok for record in stress_records), f"ok={sum(1 for item in stress_records if item.ok)} total={len(stress_records)}")
    add_check(checks, "status samples", all(record.ok for record in status_records), f"ok={sum(1 for item in status_records if item.ok)} total={len(status_records)}")
    add_check(checks, "cpu temp threshold", max_cpu is not None and max_cpu <= args.max_cpu_temp_c, f"max={max_cpu} limit={args.max_cpu_temp_c}")
    add_check(checks, "gpu temp threshold", max_gpu is not None and max_gpu <= args.max_gpu_temp_c, f"max={max_gpu} limit={args.max_gpu_temp_c}")
    add_check(checks, "battery temp threshold", max_battery is not None and max_battery <= args.max_battery_temp_c, f"max={max_battery} limit={args.max_battery_temp_c}")
    add_check(checks, "status responsiveness", max_status_ms is not None and max_status_ms <= args.max_status_duration_ms, f"max={max_status_ms}ms limit={args.max_status_duration_ms}ms")
    add_check(checks, "longsoak health", all(sample.longsoak_health == "ok" for sample in samples if sample.longsoak_health), f"samples={len(samples)}")
    add_check(checks, "controlled zombies", process.controlled_zombie_count == 0, f"controlled={process.controlled_zombie_count} global={process.zombie_count}")
    add_check(checks, "final selftest", final_selftest.ok, f"rc={final_selftest.rc} status={final_selftest.status}")
    add_check(checks, "final longsoak", final_longsoak.ok, f"rc={final_longsoak.rc} status={final_longsoak.status}")

    elapsed = time.monotonic() - started
    pass_ok = all(item.ok for item in checks)
    report: dict[str, Any] = {
        "pass": pass_ok,
        "run_id": args.run_id,
        "duration_sec": elapsed,
        "args": {
            "cycles": args.cycles,
            "stress_sec": args.stress_sec,
            "stress_workers": args.stress_workers,
            "mem_size": args.mem_size,
            "max_cpu_temp_c": args.max_cpu_temp_c,
            "max_gpu_temp_c": args.max_gpu_temp_c,
            "max_battery_temp_c": args.max_battery_temp_c,
            "max_status_duration_ms": args.max_status_duration_ms,
        },
        "extremes": {
            "max_cpu_temp_c": max_cpu,
            "max_gpu_temp_c": max_gpu,
            "max_battery_temp_c": max_battery,
            "max_power_now_w": max_power,
            "max_mem_used_mb": max_mem,
            "max_status_duration_ms": max_status_ms,
        },
        "memory": asdict(memory),
        "process": asdict(process),
        "samples": [asdict(sample) for sample in samples],
        "host_ping": pings,
        "commands": [asdict(record) for record in command_records],
        "checks": [asdict(item) for item in checks],
    }
    lines = [
        "# A90 CPU/Memory/Thermal Stability Report\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- run_id: `{args.run_id}`\n",
        f"- duration_sec: `{elapsed:.3f}`\n",
        f"- cycles: `{args.cycles}`\n",
        f"- stress: `{args.stress_sec}s x {args.stress_workers} workers`\n",
        f"- memory_verify: `{memory.size_bytes} bytes hash_ok={memory.hash_ok}`\n",
        f"- max_cpu_temp_c: `{max_cpu}`\n",
        f"- max_gpu_temp_c: `{max_gpu}`\n",
        f"- max_battery_temp_c: `{max_battery}`\n",
        f"- max_power_now_w: `{max_power}`\n",
        f"- max_mem_used_mb: `{max_mem}`\n",
        f"- max_status_duration_ms: `{max_status_ms}`\n",
        f"- controlled_zombies: `{process.controlled_zombie_count}`\n\n",
        "## Checks\n\n",
        "| Check | Result | Detail |\n",
        "|---|---|---|\n",
    ]
    for item in checks:
        lines.append(f"| `{item.name}` | `{'PASS' if item.ok else 'FAIL'}` | `{item.detail}` |\n")
    write_private_text(out_dir / "cpu-mem-thermal-report.json", json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "cpu-mem-thermal-report.md", "".join(lines))
    print(f"{'PASS' if pass_ok else 'FAIL'} run_id={args.run_id} duration={elapsed:.3f}s")
    print(out_dir / "cpu-mem-thermal-report.md")
    print(out_dir / "cpu-mem-thermal-report.json")
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
