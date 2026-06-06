#!/usr/bin/env python3
"""Failure and recovery tests for the A90B1 broker."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
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
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text  # noqa: E402


DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"


@dataclass
class TestCaseResult:
    name: str
    ok: bool
    detail: str
    duration_sec: float
    artifacts: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run A90B1 broker recovery/failure tests.")
    parser.add_argument("--run-dir", type=Path,
                        default=Path("tmp") / f"a90-v192-broker-recovery-{timestamp()}")
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=DEFAULT_TCP_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--include-live", action="store_true",
                        help="also run live ACM/NCM-path recovery checks")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--ready-timeout", type=float, default=5.0)
    return parser


def broker_script() -> Path:
    return SCRIPT_DIR / "a90_broker.py"


def start_broker(args: argparse.Namespace,
                 runtime_dir: Path,
                 *,
                 backend: str,
                 tcp_port: int | None = None,
                 no_auth: bool = False,
                 allow_no_auth: bool = False,
                 allow_exclusive: bool = False) -> subprocess.Popen[str]:
    ensure_private_dir(runtime_dir)
    command = [
        sys.executable,
        str(broker_script()),
        "serve",
        "--backend",
        backend,
        "--runtime-dir",
        str(runtime_dir),
        "--socket-name",
        DEFAULT_SOCKET_NAME,
        "--audit-name",
        DEFAULT_AUDIT_NAME,
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--device-ip",
        args.device_ip,
        "--tcp-port",
        str(args.tcp_port if tcp_port is None else tcp_port),
        "--tcp-timeout",
        str(args.tcp_timeout),
    ]
    if no_auth:
        command.append("--no-auth")
    if allow_no_auth:
        command.append("--allow-no-auth")
    if allow_exclusive:
        command.append("--allow-exclusive")
    return subprocess.Popen(
        command,
        cwd=REPO_ROOT,
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


def wait_for_socket(socket_path: Path, process: subprocess.Popen[str], timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"broker exited before ready rc={process.returncode}")
        if socket_path.exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(0.2)
                    client.connect(str(socket_path))
                return
            except OSError:
                pass
        time.sleep(0.05)
    raise RuntimeError(f"socket not ready: {socket_path}")


def request(argv: list[str], *, timeout_ms: int = 2000) -> dict[str, Any]:
    return {
        "proto": PROTO,
        "id": f"v192-{uuid.uuid4().hex[:12]}",
        "client_id": f"v192:{os.getpid()}",
        "op": "cmd",
        "argv": argv,
        "timeout_ms": timeout_ms,
    }


def call(socket_path: Path, argv: list[str], timeout_sec: float) -> dict[str, Any]:
    return connect_and_call(socket_path, request(argv, timeout_ms=int(timeout_sec * 1000)), timeout_sec + 3.0)


def collect_audit(store: EvidenceStore, runtime_dir: Path, label: str) -> dict[str, Any] | None:
    audit_path = runtime_dir / DEFAULT_AUDIT_NAME
    if not audit_path.exists():
        return None
    records, malformed = read_audit_jsonl(audit_path)
    summary = summarize_audit(records, malformed, audit_path)
    store.write_json(f"{label}-audit-summary.json", summary)
    store.write_text(f"{label}-audit-report.md", render_audit_markdown(summary))
    return summary


def tcp_port_open(host: str, port: int, timeout_sec: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def run_blocked_audit_test(args: argparse.Namespace, store: EvidenceStore) -> TestCaseResult:
    started = time.monotonic()
    runtime_dir = store.mkdir("blocked-audit-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    process = start_broker(args, runtime_dir, backend="fake")
    artifacts: list[str] = []
    try:
        wait_for_socket(socket_path, process, args.ready_timeout)
        response = call(socket_path, ["reboot"], args.timeout)
        store.write_json("blocked-audit-response.json", response)
        artifacts.append("blocked-audit-response.json")
        audit = collect_audit(store, runtime_dir, "blocked-audit")
        ok = (
            response.get("ok") is False and
            response.get("status") == "operator-required" and
            audit is not None and
            audit["integrity"]["ok"] is True and
            audit["status_counts"].get("operator-required") == 1
        )
        detail = f"status={response.get('status')} audit={audit['request_counts'] if audit else None}"
        return TestCaseResult("blocked command audit", ok, detail, time.monotonic() - started, artifacts)
    finally:
        stdout, stderr = stop_broker(process)
        if stdout:
            store.write_text("blocked-audit-stdout.txt", stdout)
        if stderr:
            store.write_text("blocked-audit-stderr.txt", stderr)


def run_restart_test(args: argparse.Namespace, store: EvidenceStore) -> TestCaseResult:
    started = time.monotonic()
    runtime_dir = store.mkdir("restart-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    artifacts: list[str] = []
    process = start_broker(args, runtime_dir, backend="fake")
    try:
        wait_for_socket(socket_path, process, args.ready_timeout)
        first = call(socket_path, ["status"], args.timeout)
        store.write_json("restart-first-response.json", first)
        artifacts.append("restart-first-response.json")
    finally:
        stop_broker(process)

    failed_while_down = False
    try:
        call(socket_path, ["status"], 1.0)
    except Exception:
        failed_while_down = True

    process = start_broker(args, runtime_dir, backend="fake")
    try:
        wait_for_socket(socket_path, process, args.ready_timeout)
        second = call(socket_path, ["status"], args.timeout)
        store.write_json("restart-second-response.json", second)
        artifacts.append("restart-second-response.json")
        audit = collect_audit(store, runtime_dir, "restart")
        ok = first.get("ok") is True and failed_while_down and second.get("ok") is True and audit is not None
        detail = f"first={first.get('status')} down_failed={failed_while_down} second={second.get('status')}"
        return TestCaseResult("broker restart stale socket recovery", ok, detail, time.monotonic() - started, artifacts)
    finally:
        stdout, stderr = stop_broker(process)
        if stdout:
            store.write_text("restart-stdout.txt", stdout)
        if stderr:
            store.write_text("restart-stderr.txt", stderr)


def run_stale_path_test(args: argparse.Namespace, store: EvidenceStore) -> TestCaseResult:
    started = time.monotonic()
    runtime_dir = store.mkdir("stale-path-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    write_private_text(socket_path, "not a socket\n")
    command = [
        sys.executable,
        str(broker_script()),
        "serve",
        "--backend",
        "fake",
        "--runtime-dir",
        str(runtime_dir),
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=5,
    )
    store.write_text("stale-path-output.txt", result.stdout)
    ok = result.returncode != 0 and "refusing to replace non-socket path" in result.stdout
    detail = f"rc={result.returncode}"
    return TestCaseResult("stale non-socket path refusal", ok, detail, time.monotonic() - started, ["stale-path-output.txt"])


def run_ncm_down_test(args: argparse.Namespace, store: EvidenceStore) -> TestCaseResult:
    started = time.monotonic()
    runtime_dir = store.mkdir("ncm-down-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    unused_port = 29999
    artifacts: list[str] = []
    precheck_open = tcp_port_open(args.device_ip, unused_port, min(args.tcp_timeout, 1.0))
    store.write_text(
        "ncm-down-port-precheck.txt",
        f"host={args.device_ip} port={unused_port} open={precheck_open}\n",
    )
    artifacts.append("ncm-down-port-precheck.txt")
    if precheck_open:
        return TestCaseResult(
            "ncm listener down transport-error",
            False,
            f"unsafe precheck: {args.device_ip}:{unused_port} is open; refused to send request",
            time.monotonic() - started,
            artifacts,
        )
    process = start_broker(
        args,
        runtime_dir,
        backend="ncm-tcpctl",
        tcp_port=unused_port,
        no_auth=True,
        allow_no_auth=True,
        allow_exclusive=True,
    )
    try:
        wait_for_socket(socket_path, process, args.ready_timeout)
        response = call(socket_path, ["run", "/cache/bin/toybox", "uptime"], args.timeout)
        store.write_json("ncm-down-response.json", response)
        artifacts.append("ncm-down-response.json")
        audit = collect_audit(store, runtime_dir, "ncm-down")
        ok = (
            response.get("ok") is False and
            response.get("status") == "transport-error" and
            audit is not None and
            audit["status_counts"].get("transport-error") == 1
        )
        detail = f"status={response.get('status')} error={response.get('error')}"
        return TestCaseResult("ncm listener down transport-error", ok, detail, time.monotonic() - started, artifacts)
    finally:
        stdout, stderr = stop_broker(process)
        if stdout:
            store.write_text("ncm-down-stdout.txt", stdout)
        if stderr:
            store.write_text("ncm-down-stderr.txt", stderr)


def run_acm_fallback_test(args: argparse.Namespace, store: EvidenceStore) -> TestCaseResult:
    started = time.monotonic()
    runtime_dir = store.mkdir("acm-fallback-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    process = start_broker(args, runtime_dir, backend="ncm-tcpctl", tcp_port=29999)
    artifacts: list[str] = []
    try:
        wait_for_socket(socket_path, process, args.ready_timeout)
        response = call(socket_path, ["version"], args.timeout)
        store.write_json("acm-fallback-response.json", response)
        artifacts.append("acm-fallback-response.json")
        audit = collect_audit(store, runtime_dir, "acm-fallback")
        text = str(response.get("text") or "")
        ok = (
            response.get("ok") is True and
            args.expect_version in text and
            response.get("backend") == "acm-cmdv1" and
            audit is not None and
            audit["backend_counts"].get("acm-cmdv1") == 1
        )
        detail = f"status={response.get('status')} backend={response.get('backend')}"
        return TestCaseResult("ncm backend acm fallback", ok, detail, time.monotonic() - started, artifacts)
    finally:
        stdout, stderr = stop_broker(process)
        if stdout:
            store.write_text("acm-fallback-stdout.txt", stdout)
        if stderr:
            store.write_text("acm-fallback-stderr.txt", stderr)


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# A90B1 Broker Recovery Tests\n\n",
        f"- result: `{'PASS' if summary['pass'] else 'FAIL'}`\n",
        f"- include_live: `{summary['include_live']}`\n",
        f"- tests: `{summary['test_count']}`\n",
        f"- failed: `{summary['failed_count']}`\n",
        f"- run_dir: `{summary['run_dir']}`\n\n",
        "## Results\n\n",
    ]
    for item in summary["results"]:
        lines.append(
            f"- {'PASS' if item['ok'] else 'FAIL'} `{item['name']}`: "
            f"{item['detail']} duration={item['duration_sec']:.3f}s\n"
        )
    return "".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    store = EvidenceStore(args.run_dir)
    started = time.monotonic()
    results = [
        run_blocked_audit_test(args, store),
        run_restart_test(args, store),
        run_stale_path_test(args, store),
    ]
    if args.include_live:
        results.extend([
            run_ncm_down_test(args, store),
            run_acm_fallback_test(args, store),
        ])
    failed = [item for item in results if not item.ok]
    summary = {
        "schema": "a90-broker-recovery-tests-v192",
        "pass": not failed,
        "include_live": args.include_live,
        "run_dir": str(store.run_dir),
        "duration_sec": round(time.monotonic() - started, 6),
        "test_count": len(results),
        "failed_count": len(failed),
        "results": [item.to_dict() for item in results],
    }
    store.write_json("broker-recovery-summary.json", summary)
    store.write_text("broker-recovery-report.md", render_report(summary))
    print(
        f"{'PASS' if summary['pass'] else 'FAIL'} tests={summary['test_count']} "
        f"failed={summary['failed_count']} include_live={args.include_live} out={store.run_dir}"
    )
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
