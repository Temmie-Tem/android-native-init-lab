#!/usr/bin/env python3
"""Validate A90 native-init process, service, and TCP concurrency stability."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import run_cmdv1_command  # noqa: E402
from tcpctl_host import (  # noqa: E402
    BridgeRunThread,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_DEVICE_BINARY,
    DEFAULT_DEVICE_IP,
    DEFAULT_TCPCTL_TOKEN_PATH,
    DEFAULT_TCP_PORT,
    DEFAULT_TOKEN_COMMAND,
    DEFAULT_TOYBOX,
    best_effort_hide_menu,
    get_tcpctl_token,
    tcpctl_expect_ok,
    tcpctl_listen_command,
    wait_for_tcpctl,
)


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
CONTROLLED_PROCESS_NAMES = {"a90_tcpctl", "a90_cpustress", "toybox", "a90sleep"}


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
class ProcessEntry:
    pid: int
    name: str
    state: str


@dataclass
class ProcessSnapshot:
    label: str
    pid_count: int
    scanned_pids: int
    zombie_count: int
    controlled_zombie_count: int
    pid1_fd_count: int | None
    entries: list[ProcessEntry]


@dataclass
class TcpctlOp:
    worker: int
    loop: int
    command: str
    ok: bool
    duration_sec: float
    error: str


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT + 1)
    parser.add_argument("--device-binary", default=DEFAULT_DEVICE_BINARY)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--idle-timeout", type=int, default=120)
    parser.add_argument("--max-clients", type=int, default=32)
    parser.add_argument("--token", help="tcpctl auth token; defaults to reading it from native init")
    parser.add_argument("--token-command", default=DEFAULT_TOKEN_COMMAND)
    parser.add_argument("--token-path", default=DEFAULT_TCPCTL_TOKEN_PATH)
    parser.add_argument("--no-auth", action="store_true")
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--tcp-timeout", type=float, default=10.0)
    parser.add_argument("--device-protocol", choices=("auto", "cmdv1", "raw"), default="auto")
    parser.add_argument("--busy-retries", type=int, default=3)
    parser.add_argument("--busy-retry-sleep", type=float, default=3.0)
    parser.add_argument("--menu-hide-sleep", type=float, default=3.0)
    parser.add_argument("--run-id", default=f"v162-{int(time.time())}")
    parser.add_argument("--out-dir", default="tmp/soak/process-concurrency")
    parser.add_argument("--churn-loops", type=int, default=8)
    parser.add_argument("--client-workers", type=int, default=4)
    parser.add_argument("--client-loops", type=int, default=4)
    parser.add_argument("--cpustress-sec", type=int, default=3)
    parser.add_argument("--cpustress-workers", type=int, default=2)
    parser.add_argument("--longsoak-interval", type=int, default=15)
    parser.add_argument("--fd-growth-limit", type=int, default=8)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


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
        duration = time.monotonic() - started
        write_private_text(output_file, result.text)
        ok = result.rc == 0 and result.status == "ok"
        if not ok and not allow_error:
            add_check(checks, label, False, f"rc={result.rc} status={result.status}")
        return CommandRecord(
            label=label,
            command=command,
            rc=result.rc,
            status=result.status,
            duration_sec=duration,
            ok=ok,
            output_file=str(output_file),
        )
    except Exception as exc:  # noqa: BLE001 - validator keeps evidence
        duration = time.monotonic() - started
        write_private_text(output_file, f"{type(exc).__name__}: {exc}\n")
        if not allow_error:
            add_check(checks, label, False, str(exc))
        return CommandRecord(
            label=label,
            command=command,
            rc=None,
            status="exception",
            duration_sec=duration,
            ok=False,
            output_file=str(output_file),
        )


def fd_count(args: argparse.Namespace) -> int | None:
    try:
        result = run_cmdv1_command(
            args.bridge_host,
            args.bridge_port,
            args.bridge_timeout,
            ["ls", "/proc/1/fd"],
        )
    except Exception:
        return None
    if result.rc != 0:
        return None
    count = 0
    for line in result.text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1].isdigit() and parts[0][0] in {"-", "d", "l", "c", "b"}:
            count += 1
    return count


def process_snapshot(args: argparse.Namespace, label: str, out_dir: Path) -> ProcessSnapshot:
    result = run_cmdv1_command(
        args.bridge_host,
        args.bridge_port,
        args.bridge_timeout,
        ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm"],
        retry_unsafe=True,
    )
    write_private_text(out_dir / f"proc-{label}-ps.txt", result.text)
    entries: list[ProcessEntry] = []
    for line in result.text.splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3 or not parts[0].isdigit() or parts[0] == "PID":
            continue
        name = parts[2].strip()
        if name.startswith("[") and name.endswith("]"):
            name = name[1:-1]
        entries.append(ProcessEntry(pid=int(parts[0]), name=name, state=parts[1]))

    zombie_entries = [item for item in entries if item.state.startswith("Z")]
    controlled_zombies = [
        item for item in zombie_entries
        if item.name in CONTROLLED_PROCESS_NAMES or item.name.startswith("a90_")
    ]
    snapshot = ProcessSnapshot(
        label=label,
        pid_count=len(entries),
        scanned_pids=len(entries),
        zombie_count=len(zombie_entries),
        controlled_zombie_count=len(controlled_zombies),
        pid1_fd_count=fd_count(args),
        entries=zombie_entries + controlled_zombies,
    )
    write_private_text(
        out_dir / f"proc-{label}-summary.json",
        json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return snapshot


def run_churn(args: argparse.Namespace, out_dir: Path, checks: list[Check]) -> list[CommandRecord]:
    records: list[CommandRecord] = []
    commands = [
        ("toybox-true", ["run", args.toybox, "true"]),
        ("toybox-uptime", ["run", args.toybox, "uptime"]),
        ("stat-proc1", ["stat", "/proc/1/status"]),
        ("echo-ping", ["echo", "v162-concurrency-ping"]),
    ]
    for loop_index in range(args.churn_loops):
        for label, command in commands:
            records.append(
                run_cmd(
                    args,
                    f"churn-{loop_index:02d}-{label}",
                    command,
                    out_dir,
                    checks,
                    retry_unsafe=command[0] == "run",
                )
            )
    ok_count = sum(1 for item in records if item.ok)
    add_check(
        checks,
        "helper churn",
        ok_count == len(records),
        f"ok={ok_count} total={len(records)}",
    )
    return records


def run_busy_gate_probe(args: argparse.Namespace,
                        out_dir: Path,
                        checks: list[Check]) -> dict[str, Any]:
    policy = run_cmd(args, "policycheck-run", ["policycheck", "run"], out_dir, checks)
    screenmenu = run_cmd(args, "busy-screenmenu", ["screenmenu"], out_dir, checks)
    time.sleep(1.0)
    probe = run_cmd(
        args,
        "busy-run-while-menu",
        ["run", args.toybox, "true"],
        out_dir,
        checks,
        allow_error=True,
        retry_unsafe=True,
    )
    hide = run_cmd(args, "busy-hide", ["hide"], out_dir, checks, allow_error=True)
    blocked = probe.status == "busy" or probe.rc in {-16, -114}
    add_check(
        checks,
        "busy gate blocks run",
        blocked,
        f"screenmenu={screenmenu.status}/{screenmenu.rc} probe={probe.status}/{probe.rc} hide={hide.status}/{hide.rc}",
    )
    add_check(checks, "policycheck pass", policy.ok, f"rc={policy.rc} status={policy.status}")
    return {
        "policy": asdict(policy),
        "screenmenu": asdict(screenmenu),
        "probe": asdict(probe),
        "hide": asdict(hide),
        "blocked": blocked,
    }


def start_tcpctl(args: argparse.Namespace) -> BridgeRunThread:
    best_effort_hide_menu(args)
    if not args.no_auth:
        get_tcpctl_token(args)
    runner = BridgeRunThread(args, tcpctl_listen_command(args), echo=args.verbose)
    runner.start()
    wait_for_tcpctl(args, args.bridge_timeout)
    return runner


def tcpctl_worker(args: argparse.Namespace, worker: int, loops: int) -> list[TcpctlOp]:
    commands = [
        "ping",
        "status",
        f"run {args.toybox} uptime",
        f"run {args.toybox} true",
    ]
    ops: list[TcpctlOp] = []
    for loop_index in range(loops):
        command = commands[(worker + loop_index) % len(commands)]
        ops.append(tcpctl_one(args, worker, loop_index, command))
    return ops


def tcpctl_one(args: argparse.Namespace, worker: int, loop_index: int, command: str) -> TcpctlOp:
    started = time.monotonic()
    try:
        tcpctl_expect_ok(args, command)
        return TcpctlOp(
            worker=worker,
            loop=loop_index,
            command=command,
            ok=True,
            duration_sec=time.monotonic() - started,
            error="",
        )
    except Exception as exc:  # noqa: BLE001 - keep all failures in report
        return TcpctlOp(
            worker=worker,
            loop=loop_index,
            command=command,
            ok=False,
            duration_sec=time.monotonic() - started,
            error=str(exc),
        )


def run_tcpctl_parallel(args: argparse.Namespace,
                        out_dir: Path,
                        checks: list[Check]) -> dict[str, Any]:
    required_clients = args.client_workers * args.client_loops + 4
    if args.max_clients < required_clients:
        args.max_clients = required_clients
    runner = start_tcpctl(args)

    operations: list[TcpctlOp] = []
    with ThreadPoolExecutor(max_workers=args.client_workers + 2) as executor:
        futures = [
            executor.submit(tcpctl_worker, args, worker, args.client_loops)
            for worker in range(args.client_workers)
        ]
        futures.append(
            executor.submit(
                lambda: [
                    tcpctl_one(
                        args,
                        args.client_workers,
                        0,
                        f"run /bin/a90_cpustress {args.cpustress_sec} {args.cpustress_workers}",
                    )
                ]
            )
        )
        futures.append(
            executor.submit(
                lambda: [
                    tcpctl_one(
                        args,
                        args.client_workers + 1,
                        0,
                        "status",
                    )
                ]
            )
        )
        for future in as_completed(futures):
            operations.extend(future.result())

    shutdown_error = ""
    try:
        tcpctl_expect_ok(args, "shutdown")
    except Exception as exc:  # noqa: BLE001 - report shutdown failures
        shutdown_error = str(exc)
    runner.join(args.bridge_timeout)
    serial_text = runner.text()
    write_private_text(out_dir / "tcpctl-serial-run.txt", serial_text)

    ok_ops = sum(1 for item in operations if item.ok)
    total_ops = len(operations)
    cpustress_ops = [item for item in operations if "a90_cpustress" in item.command]
    serial_done = "[done] run" in serial_text
    cpustress_ok = bool(cpustress_ops) and all(item.ok for item in cpustress_ops)
    add_check(checks, "tcpctl parallel ops", ok_ops == total_ops, f"ok={ok_ops} total={total_ops}")
    add_check(checks, "tcpctl shutdown", not shutdown_error and serial_done, f"shutdown_error={shutdown_error!r} serial_done={serial_done}")
    add_check(
        checks,
        "concurrent cpustress",
        cpustress_ok,
        f"ok={sum(1 for item in cpustress_ops if item.ok)} total={len(cpustress_ops)}",
    )
    return {
        "operations": [asdict(item) for item in operations],
        "ok_ops": ok_ops,
        "total_ops": total_ops,
        "shutdown_error": shutdown_error,
        "serial_done": serial_done,
        "cpustress": [asdict(item) for item in cpustress_ops],
    }


def command_summary(records: list[CommandRecord]) -> list[dict[str, Any]]:
    return [asdict(item) for item in records]


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir) / args.run_id
    ensure_private_dir(out_dir)
    checks: list[Check] = []
    started = time.monotonic()

    before = process_snapshot(args, "before", out_dir)
    setup_records = [
        run_cmd(
            args,
            "initial-hide",
            ["hide"],
            out_dir,
            checks,
            allow_error=True,
        ),
        run_cmd(
            args,
            "longsoak-start",
            ["longsoak", "start", str(args.longsoak_interval)],
            out_dir,
            checks,
            allow_error=True,
            retry_unsafe=True,
        ),
        run_cmd(
            args,
            "autohud-start",
            ["autohud", "2"],
            out_dir,
            checks,
            allow_error=True,
            retry_unsafe=True,
        ),
        run_cmd(
            args,
            "post-autohud-hide",
            ["hide"],
            out_dir,
            checks,
            allow_error=True,
        ),
    ]
    add_check(
        checks,
        "background services requested",
        all(item.ok for item in setup_records),
        ", ".join(f"{item.label}={item.status}/{item.rc}" for item in setup_records),
    )
    churn_records = run_churn(args, out_dir, checks)
    tcpctl = run_tcpctl_parallel(args, out_dir, checks)
    busy_gate = run_busy_gate_probe(args, out_dir, checks)
    after = process_snapshot(args, "after", out_dir)

    fd_ok = (
        before.pid1_fd_count is None or
        after.pid1_fd_count is None or
        after.pid1_fd_count <= before.pid1_fd_count + args.fd_growth_limit
    )
    add_check(
        checks,
        "controlled zombies",
        after.controlled_zombie_count == 0,
        f"controlled_zombies={after.controlled_zombie_count} global_zombies={after.zombie_count}",
    )
    add_check(
        checks,
        "pid1 fd growth",
        fd_ok,
        f"before={before.pid1_fd_count} after={after.pid1_fd_count} limit={args.fd_growth_limit}",
    )
    status = run_cmd(args, "final-status", ["status"], out_dir, checks)
    selftest = run_cmd(args, "final-selftest", ["selftest", "verbose"], out_dir, checks)
    longsoak = run_cmd(args, "final-longsoak-status", ["longsoak", "status", "verbose"], out_dir, checks)
    post_records = [status, selftest, longsoak]

    elapsed = time.monotonic() - started
    pass_ok = all(item.ok for item in checks)
    report: dict[str, Any] = {
        "pass": pass_ok,
        "run_id": args.run_id,
        "duration_sec": elapsed,
        "args": {
            "churn_loops": args.churn_loops,
            "client_workers": args.client_workers,
            "client_loops": args.client_loops,
            "cpustress_sec": args.cpustress_sec,
            "cpustress_workers": args.cpustress_workers,
            "tcp_port": args.tcp_port,
            "max_clients": args.max_clients,
        },
        "checks": [asdict(item) for item in checks],
        "process": {
            "before": asdict(before),
            "after": asdict(after),
        },
        "setup": command_summary(setup_records),
        "churn": command_summary(churn_records),
        "tcpctl": tcpctl,
        "busy_gate": busy_gate,
        "post": command_summary(post_records),
    }
    lines = [
        "# A90 Process/Concurrency Stability Report\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- run_id: `{args.run_id}`\n",
        f"- duration_sec: `{elapsed:.3f}`\n",
        f"- churn: `{sum(1 for item in churn_records if item.ok)}/{len(churn_records)}`\n",
        f"- tcpctl_ops: `{tcpctl['ok_ops']}/{tcpctl['total_ops']}`\n",
        f"- before_pid_count: `{before.pid_count}`\n",
        f"- after_pid_count: `{after.pid_count}`\n",
        f"- before_pid1_fd_count: `{before.pid1_fd_count}`\n",
        f"- after_pid1_fd_count: `{after.pid1_fd_count}`\n",
        f"- after_zombies: `{after.zombie_count}`\n",
        f"- after_controlled_zombies: `{after.controlled_zombie_count}`\n\n",
        "## Checks\n\n",
        "| Check | Result | Detail |\n",
        "|---|---|---|\n",
    ]
    for item in checks:
        lines.append(f"| `{item.name}` | `{'PASS' if item.ok else 'FAIL'}` | `{item.detail}` |\n")
    write_private_text(out_dir / "process-concurrency-report.json", json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "process-concurrency-report.md", "".join(lines))
    print(f"{'PASS' if pass_ok else 'FAIL'} run_id={args.run_id} duration={elapsed:.3f}s")
    print(out_dir / "process-concurrency-report.md")
    print(out_dir / "process-concurrency-report.json")
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
