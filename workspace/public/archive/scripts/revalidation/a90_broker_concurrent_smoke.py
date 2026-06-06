#!/usr/bin/env python3
"""Concurrent smoke validator for the A90B1 host-local broker."""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from a90_broker import (  # noqa: E402
    DEFAULT_AUDIT_NAME,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_DEVICE_IP,
    DEFAULT_SOCKET_NAME,
    DEFAULT_TCP_PORT,
    DEFAULT_TCP_TIMEOUT,
    PROTO,
    connect_and_call,
    read_audit_jsonl,
    render_audit_markdown,
    summarize_audit,
)
from a90harness.evidence import EvidenceStore, ensure_private_dir  # noqa: E402


DEFAULT_COMMANDS = (
    ("version",),
    ("status",),
    ("bootstatus",),
    ("selftest", "verbose"),
)
DEFAULT_EXPECT_VERSION = ""
REBINDS_OR_DESTRUCTIVE = {"reboot", "recovery", "poweroff"}


@dataclass(frozen=True)
class WorkItem:
    request_id: str
    client_id: str
    argv: list[str]
    timeout_ms: int
    expect_blocked: bool


@dataclass
class CallResult:
    request_id: str
    client_id: str
    argv: list[str]
    ok: bool
    expected_ok: bool
    duration_sec: float
    response: dict[str, Any] | None
    error: str


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def parse_command(text: str) -> tuple[str, ...]:
    argv = tuple(shlex.split(text))
    if not argv:
        raise argparse.ArgumentTypeError("command must not be empty")
    return argv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run concurrent read-only clients through the A90B1 broker.",
    )
    parser.add_argument("--run-dir", type=Path,
                        default=Path("tmp") / f"a90-v189-broker-concurrent-{timestamp()}")
    parser.add_argument("--runtime-dir", type=Path,
                        help="broker runtime directory; defaults to <run-dir>/broker-runtime")
    parser.add_argument("--socket-name", default=DEFAULT_SOCKET_NAME)
    parser.add_argument("--audit-name", default=DEFAULT_AUDIT_NAME)
    parser.add_argument("--socket", type=Path,
                        help="existing broker socket path; implies --use-existing-broker")
    parser.add_argument("--use-existing-broker", action="store_true",
                        help="do not spawn a broker subprocess")
    parser.add_argument("--backend", choices=("acm-cmdv1", "fake", "ncm-tcpctl"), default="acm-cmdv1")
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=DEFAULT_TCP_TIMEOUT)
    parser.add_argument("--token")
    parser.add_argument("--no-auth", action="store_true")
    parser.add_argument(
        "--allow-no-auth",
        action="store_true",
        help="explicitly allow legacy unauthenticated ncm-tcpctl mode for negative tests",
    )
    parser.add_argument("--allow-operator", action="store_true",
                        help="allow operator-action commands through a spawned broker")
    parser.add_argument("--allow-exclusive", action="store_true",
                        help="allow exclusive commands through a spawned broker")
    parser.add_argument("--clients", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--ready-timeout", type=float, default=5.0)
    parser.add_argument("--command", action="append", type=parse_command,
                        help="command to include; may be repeated, shell-style quoted")
    parser.add_argument("--include-blocked", action="store_true",
                        help="also send one blocked reboot request per client")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION,
                        help="substring expected in version output; empty disables check")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.clients <= 0 or args.clients > 64:
        raise SystemExit("--clients must be 1..64")
    if args.rounds <= 0 or args.rounds > 1000:
        raise SystemExit("--rounds must be 1..1000")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.connect_timeout <= 0:
        raise SystemExit("--connect-timeout must be positive")
    if args.ready_timeout <= 0:
        raise SystemExit("--ready-timeout must be positive")


def broker_script() -> Path:
    return SCRIPT_DIR / "a90_broker.py"


def start_broker(args: argparse.Namespace, runtime_dir: Path) -> subprocess.Popen[str]:
    ensure_private_dir(runtime_dir)
    command = [
        sys.executable,
        str(broker_script()),
        "serve",
        "--backend",
        args.backend,
        "--runtime-dir",
        str(runtime_dir),
        "--socket-name",
        args.socket_name,
        "--audit-name",
        args.audit_name,
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--device-ip",
        args.device_ip,
        "--tcp-port",
        str(args.tcp_port),
        "--tcp-timeout",
        str(args.tcp_timeout),
    ]
    if args.token:
        command.extend(["--token", args.token])
    if args.no_auth:
        command.append("--no-auth")
    if args.allow_no_auth:
        command.append("--allow-no-auth")
    if args.allow_operator:
        command.append("--allow-operator")
    if args.allow_exclusive:
        command.append("--allow-exclusive")
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def stop_broker(process: subprocess.Popen[str] | None) -> tuple[str, str]:
    if process is None:
        return "", ""
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            return process.communicate(timeout=2.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        return process.communicate(timeout=2.0)
    except subprocess.TimeoutExpired:
        return "", "broker output collection timed out\n"


def wait_for_broker(socket_path: Path, process: subprocess.Popen[str] | None, timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"broker exited before ready rc={process.returncode}")
        if socket_path.exists():
            return
        time.sleep(0.05)
    raise RuntimeError(f"broker socket was not ready within {timeout_sec:.1f}s: {socket_path}")


def build_work_items(args: argparse.Namespace) -> list[WorkItem]:
    commands = [list(command) for command in (args.command or DEFAULT_COMMANDS)]
    timeout_ms = int(args.timeout * 1000)
    work: list[WorkItem] = []
    for round_index in range(args.rounds):
        for client_index in range(args.clients):
            argv = commands[(round_index + client_index) % len(commands)]
            work.append(
                WorkItem(
                    request_id=f"v189-c{client_index}-r{round_index}-{uuid.uuid4().hex[:8]}",
                    client_id=f"v189-client-{client_index}",
                    argv=list(argv),
                    timeout_ms=timeout_ms,
                    expect_blocked=False,
                )
            )
    if args.include_blocked:
        for client_index in range(args.clients):
            work.append(
                WorkItem(
                    request_id=f"v189-c{client_index}-blocked-{uuid.uuid4().hex[:8]}",
                    client_id=f"v189-client-{client_index}",
                    argv=["reboot"],
                    timeout_ms=timeout_ms,
                    expect_blocked=True,
                )
            )
    return work


def response_expected_ok(item: WorkItem,
                         response: dict[str, Any],
                         expect_version: str) -> tuple[bool, str]:
    if response.get("id") != item.request_id:
        return False, f"id mismatch: {response.get('id')!r} != {item.request_id!r}"
    if response.get("proto") != PROTO:
        return False, f"proto mismatch: {response.get('proto')!r}"
    command = item.argv[0]
    if item.expect_blocked or command in REBINDS_OR_DESTRUCTIVE:
        if response.get("ok") is False and response.get("status") == "operator-required":
            return True, ""
        return False, f"blocked command was not operator-required: {response}"
    if response.get("ok") is not True:
        return False, f"command failed: {response}"
    if response.get("status") != "ok" or response.get("rc") != 0:
        return False, f"unexpected rc/status: {response}"
    if command == "version" and expect_version:
        text = str(response.get("text") or "")
        if expect_version not in text:
            return False, f"version output missing {expect_version!r}"
    return True, ""


def call_one(socket_path: Path,
             item: WorkItem,
             connect_timeout: float,
             expect_version: str) -> CallResult:
    payload = {
        "proto": PROTO,
        "id": item.request_id,
        "client_id": item.client_id,
        "op": "cmd",
        "argv": item.argv,
        "timeout_ms": item.timeout_ms,
    }
    started = time.monotonic()
    try:
        response = connect_and_call(socket_path, payload, connect_timeout + (item.timeout_ms / 1000.0))
        duration = time.monotonic() - started
        expected_ok, error = response_expected_ok(item, response, expect_version)
        return CallResult(
            request_id=item.request_id,
            client_id=item.client_id,
            argv=item.argv,
            ok=expected_ok,
            expected_ok=expected_ok,
            duration_sec=duration,
            response=response,
            error=error,
        )
    except Exception as exc:  # noqa: BLE001 - smoke evidence should capture exact failure
        duration = time.monotonic() - started
        return CallResult(
            request_id=item.request_id,
            client_id=item.client_id,
            argv=item.argv,
            ok=False,
            expected_ok=False,
            duration_sec=duration,
            response=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def run_concurrent(socket_path: Path,
                   work: list[WorkItem],
                   args: argparse.Namespace) -> list[CallResult]:
    results: list[CallResult] = []
    with ThreadPoolExecutor(max_workers=args.clients) as executor:
        futures = [
            executor.submit(call_one, socket_path, item, args.connect_timeout, args.expect_version)
            for item in work
        ]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item.request_id)
    return results


def render_smoke_report(summary: dict[str, Any],
                        audit_summary: dict[str, Any] | None,
                        run_dir: Path,
                        runtime_dir: Path,
                        socket_path: Path,
                        audit_path: Path,
                        results: list[CallResult]) -> str:
    lines = [
        "# A90B1 Broker Concurrent Smoke\n\n",
        f"- result: `{'PASS' if summary['pass'] else 'FAIL'}`\n",
        f"- backend: `{summary['backend']}`\n",
        f"- clients: `{summary['clients']}`\n",
        f"- rounds: `{summary['rounds']}`\n",
        f"- requests: `{summary['requests']}`\n",
        f"- ok: `{summary['ok']}`\n",
        f"- failed: `{summary['failed']}`\n",
        f"- blocked_expected: `{summary['blocked_expected']}`\n",
        f"- run_dir: `{run_dir}`\n",
        f"- runtime_dir: `{runtime_dir}`\n",
        f"- socket: `{socket_path}`\n",
        f"- audit: `{audit_path}`\n\n",
        "## Command Counts\n\n",
    ]
    for command, count in summary["command_counts"].items():
        lines.append(f"- `{command}`: `{count}`\n")
    if audit_summary is not None:
        lines.extend([
            "\n## Audit Summary\n\n",
            f"- integrity_ok: `{audit_summary['integrity']['ok']}`\n",
            f"- accepted: `{audit_summary['request_counts']['accepted']}`\n",
            f"- dispatched: `{audit_summary['request_counts']['dispatched']}`\n",
            f"- results: `{audit_summary['request_counts']['results']}`\n",
            f"- non_ok_results: `{audit_summary['request_counts']['non_ok_results']}`\n",
            f"- duration_ms: `{audit_summary['duration_ms']}`\n",
        ])
    failures = [item for item in results if not item.ok]
    if failures:
        lines.append("\n## Failures\n\n")
        for item in failures[:32]:
            lines.append(
                f"- id=`{item.request_id}` argv=`{' '.join(item.argv)}` error=`{item.error}`\n"
            )
    return "".join(lines)


def summarize_results(args: argparse.Namespace,
                      work: list[WorkItem],
                      results: list[CallResult],
                      audit_summary: dict[str, Any] | None) -> dict[str, Any]:
    result_ids = [item.request_id for item in results]
    duplicate_result_ids = sorted({request_id for request_id in result_ids if result_ids.count(request_id) > 1})
    missing_result_ids = sorted(set(item.request_id for item in work) - set(result_ids))
    blocked_expected = sum(1 for item in work if item.expect_blocked)
    command_counts: dict[str, int] = {}
    for item in work:
        command_counts[item.argv[0]] = command_counts.get(item.argv[0], 0) + 1
    expected_audit_non_ok = blocked_expected
    audit_ok = True
    audit_reason = ""
    if audit_summary is not None:
        counts = audit_summary["request_counts"]
        audit_ok = (
            audit_summary["integrity"]["ok"] and
            counts["accepted"] == len(work) and
            counts["dispatched"] == len(work) and
            counts["results"] == len(work) and
            counts["non_ok_results"] == expected_audit_non_ok
        )
        if not audit_ok:
            audit_reason = (
                f"audit counts/integrity mismatch counts={counts} "
                f"integrity={audit_summary['integrity']}"
            )
    ok_count = sum(1 for item in results if item.ok)
    pass_ok = (
        ok_count == len(work) and
        not duplicate_result_ids and
        not missing_result_ids and
        audit_ok
    )
    return {
        "schema": "a90-broker-concurrent-smoke-v189",
        "pass": pass_ok,
        "backend": args.backend,
        "clients": args.clients,
        "rounds": args.rounds,
        "requests": len(work),
        "ok": ok_count,
        "failed": len(results) - ok_count + len(missing_result_ids),
        "blocked_expected": blocked_expected,
        "command_counts": dict(sorted(command_counts.items())),
        "duplicate_result_ids": duplicate_result_ids,
        "missing_result_ids": missing_result_ids,
        "audit_ok": audit_ok,
        "audit_reason": audit_reason,
        "expect_version": args.expect_version,
    }


def result_to_dict(result: CallResult) -> dict[str, Any]:
    return {
        "request_id": result.request_id,
        "client_id": result.client_id,
        "argv": result.argv,
        "ok": result.ok,
        "expected_ok": result.expected_ok,
        "duration_sec": round(result.duration_sec, 6),
        "response": result.response,
        "error": result.error,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)

    store = EvidenceStore(args.run_dir)
    runtime_dir = args.runtime_dir or store.mkdir("broker-runtime")
    if args.socket is not None:
        args.use_existing_broker = True
        socket_path = args.socket
    else:
        socket_path = runtime_dir / args.socket_name
    audit_path = runtime_dir / args.audit_name
    broker_process: subprocess.Popen[str] | None = None
    broker_stdout = ""
    broker_stderr = ""
    try:
        if not args.use_existing_broker:
            broker_process = start_broker(args, runtime_dir)
        wait_for_broker(socket_path, broker_process, args.ready_timeout)
        work = build_work_items(args)
        started = time.monotonic()
        results = run_concurrent(socket_path, work, args)
        duration_sec = time.monotonic() - started
        audit_summary: dict[str, Any] | None = None
        if audit_path.exists():
            records, malformed = read_audit_jsonl(audit_path)
            audit_summary = summarize_audit(records, malformed, audit_path)
            store.write_json("broker-audit-summary.json", audit_summary)
            store.write_text("broker-audit-report.md", render_audit_markdown(audit_summary))
        summary = summarize_results(args, work, results, audit_summary)
        summary["duration_sec"] = round(duration_sec, 6)
        store.write_json("concurrent-smoke-summary.json", summary)
        store.write_json("concurrent-smoke-responses.json", {"results": [result_to_dict(item) for item in results]})
        store.write_text(
            "concurrent-smoke-report.md",
            render_smoke_report(summary, audit_summary, store.run_dir, runtime_dir, socket_path, audit_path, results),
        )
        print(
            f"{'PASS' if summary['pass'] else 'FAIL'} "
            f"backend={args.backend} clients={args.clients} rounds={args.rounds} "
            f"requests={summary['requests']} failed={summary['failed']} "
            f"blocked_expected={summary['blocked_expected']} out={store.run_dir}"
        )
        if summary["audit_reason"]:
            print(summary["audit_reason"], file=sys.stderr)
        return 0 if summary["pass"] else 1
    finally:
        broker_stdout, broker_stderr = stop_broker(broker_process)
        if broker_stdout:
            store.write_text("broker-stdout.txt", broker_stdout)
        if broker_stderr:
            store.write_text("broker-stderr.txt", broker_stderr)


if __name__ == "__main__":
    raise SystemExit(main())
