#!/usr/bin/env python3
"""Broker-backed mixed-soak gate for A90 native-init host validation."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from a90_broker import (  # noqa: E402
    DEFAULT_AUDIT_NAME,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_SOCKET_NAME,
    read_audit_jsonl,
    render_audit_markdown,
    summarize_audit,
)
from a90harness.evidence import EvidenceStore, ensure_private_dir  # noqa: E402


DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run native_test_supervisor mixed-soak through an A90B1 broker and verify broker audit.",
    )
    parser.add_argument("--run-dir", type=Path,
                        default=Path("tmp") / f"a90-v190-broker-mixed-{timestamp()}")
    parser.add_argument("--runtime-dir", type=Path,
                        help="broker runtime directory; defaults to <run-dir>/broker-runtime")
    parser.add_argument("--socket-name", default=DEFAULT_SOCKET_NAME)
    parser.add_argument("--audit-name", default=DEFAULT_AUDIT_NAME)
    parser.add_argument("--backend", choices=("acm-cmdv1",), default="acm-cmdv1")
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--ready-timeout", type=float, default=5.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--duration-sec", type=float, default=60.0)
    parser.add_argument("--observer-interval", type=float, default=10.0)
    parser.add_argument("--profile", choices=("idle", "smoke", "balanced"), default="smoke")
    parser.add_argument("--workload-profile", choices=("smoke", "quick"), default="smoke")
    parser.add_argument("--workload", action="append", default=[],
                        help="mixed-soak workload; repeatable. Default keeps the smoke fully broker-owned.")
    parser.add_argument("--seed", type=int, default=190)
    parser.add_argument("--allow-ncm", action="store_true")
    parser.add_argument("--allow-usb-rebind", action="store_true")
    parser.add_argument("--allow-destructive", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--stop-on-failure", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="run supervisor mixed-soak dry-run only; still writes a v190 bundle")
    parser.add_argument("--min-audit-results", type=int, default=8)
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.ready_timeout <= 0:
        raise SystemExit("--ready-timeout must be positive")
    if args.duration_sec <= 0:
        raise SystemExit("--duration-sec must be positive")
    if args.observer_interval <= 0:
        raise SystemExit("--observer-interval must be positive")
    if args.min_audit_results < 0:
        raise SystemExit("--min-audit-results must be non-negative")


def broker_script() -> Path:
    return SCRIPT_DIR / "a90_broker.py"


def supervisor_script() -> Path:
    return SCRIPT_DIR / "native_test_supervisor.py"


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
        "--allow-exclusive",
    ]
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


def wait_for_broker(socket_path: Path, process: subprocess.Popen[str] | None, timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"broker exited before ready rc={process.returncode}")
        if socket_path.exists():
            return
        time.sleep(0.05)
    raise RuntimeError(f"broker socket was not ready within {timeout_sec:.1f}s: {socket_path}")


def supervisor_command(args: argparse.Namespace,
                       runtime_dir: Path,
                       supervisor_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(supervisor_script()),
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        args.expect_version,
        "--device-backend",
        "broker",
        "--broker-runtime-dir",
        str(runtime_dir),
        "--broker-socket-name",
        args.socket_name,
        "--broker-client-id",
        f"v190-supervisor:{os.getpid()}",
        "mixed-soak",
        "--run-dir",
        str(supervisor_dir),
        "--duration-sec",
        str(args.duration_sec),
        "--observer-interval",
        str(args.observer_interval),
        "--profile",
        args.profile,
        "--workload-profile",
        args.workload_profile,
        "--seed",
        str(args.seed),
    ]
    workloads = args.workload or ["cpu-memory-profiles"]
    for workload in workloads:
        command.extend(["--workload", workload])
    if args.dry_run:
        command.append("--dry-run")
    if args.allow_ncm:
        command.append("--allow-ncm")
    if args.allow_usb_rebind:
        command.append("--allow-usb-rebind")
    if args.allow_destructive:
        command.append("--allow-destructive")
    if args.assume_yes:
        command.append("--assume-yes")
    if args.stop_on_failure:
        command.append("--stop-on-failure")
    return command


def run_supervisor(args: argparse.Namespace,
                   runtime_dir: Path,
                   supervisor_dir: Path) -> subprocess.CompletedProcess[str]:
    command = supervisor_command(args, runtime_dir, supervisor_dir)
    timeout = max(args.duration_sec + 300.0, args.timeout * 20.0)
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(manifest: dict[str, Any], args: argparse.Namespace) -> list[str]:
    failures: list[str] = []
    if manifest.get("pass") is not True:
        failures.append("supervisor manifest pass is not true")
    device_client = manifest.get("device_client", {})
    if not args.dry_run and device_client.get("backend") != "broker":
        failures.append(f"device_client backend is not broker: {device_client}")
    if args.expect_version not in json.dumps(manifest, ensure_ascii=False):
        failures.append("expected version not present in manifest")
    mixed = manifest.get("mixed_soak", {})
    if not args.dry_run:
        if mixed.get("fail_count") != 0:
            failures.append(f"mixed fail_count={mixed.get('fail_count')}")
        observer = mixed.get("observer") or {}
        if observer.get("ok") is not True:
            failures.append(f"observer not ok: {observer}")
        if int(mixed.get("workload_count") or 0) <= 0:
            failures.append("no workload events recorded")
    return failures


def validate_audit(audit_summary: dict[str, Any], args: argparse.Namespace) -> list[str]:
    if args.dry_run:
        return []
    failures: list[str] = []
    if audit_summary["integrity"]["ok"] is not True:
        failures.append(f"audit integrity failed: {audit_summary['integrity']}")
    counts = audit_summary["request_counts"]
    if int(counts.get("results") or 0) < args.min_audit_results:
        failures.append(f"audit results below threshold: {counts}")
    if int(counts.get("accepted") or 0) != int(counts.get("dispatched") or -1):
        failures.append(f"audit accepted/dispatched mismatch: {counts}")
    if int(counts.get("dispatched") or 0) != int(counts.get("results") or -1):
        failures.append(f"audit dispatched/results mismatch: {counts}")
    if audit_summary["backend_counts"].get(args.backend) != counts.get("results"):
        failures.append(f"audit backend count mismatch: {audit_summary['backend_counts']}")
    bad_status = {
        key: value
        for key, value in audit_summary["status_counts"].items()
        if key not in {"ok", "operator-required"}
    }
    if bad_status:
        failures.append(f"unexpected audit statuses: {bad_status}")
    return failures


def render_report(summary: dict[str, Any],
                  manifest: dict[str, Any] | None,
                  audit_summary: dict[str, Any] | None) -> str:
    lines = [
        "# A90B1 Broker Mixed-Soak Gate\n\n",
        f"- result: `{'PASS' if summary['pass'] else 'FAIL'}`\n",
        f"- backend: `{summary['backend']}`\n",
        f"- duration_sec: `{summary['duration_sec']}`\n",
        f"- workload: `{summary['workload']}`\n",
        f"- supervisor_rc: `{summary['supervisor_rc']}`\n",
        f"- run_dir: `{summary['run_dir']}`\n",
        f"- supervisor_dir: `{summary['supervisor_dir']}`\n",
        f"- broker_runtime_dir: `{summary['broker_runtime_dir']}`\n",
        f"- failures: `{len(summary['failures'])}`\n\n",
    ]
    if manifest:
        mixed = manifest.get("mixed_soak", {})
        lines.extend([
            "## Mixed Soak\n\n",
            f"- pass: `{manifest.get('pass')}`\n",
            f"- workload_count: `{mixed.get('workload_count')}`\n",
            f"- pass_count: `{mixed.get('pass_count')}`\n",
            f"- skip_count: `{mixed.get('skip_count')}`\n",
            f"- blocked_count: `{mixed.get('blocked_count')}`\n",
            f"- fail_count: `{mixed.get('fail_count')}`\n",
            f"- observer: `{mixed.get('observer')}`\n\n",
        ])
    if audit_summary:
        lines.extend([
            "## Broker Audit\n\n",
            f"- integrity_ok: `{audit_summary['integrity']['ok']}`\n",
            f"- accepted: `{audit_summary['request_counts']['accepted']}`\n",
            f"- dispatched: `{audit_summary['request_counts']['dispatched']}`\n",
            f"- results: `{audit_summary['request_counts']['results']}`\n",
            f"- non_ok_results: `{audit_summary['request_counts']['non_ok_results']}`\n",
            f"- status_counts: `{audit_summary['status_counts']}`\n",
            f"- class_counts: `{audit_summary['class_counts']}`\n\n",
        ])
    if summary["failures"]:
        lines.append("## Failures\n\n")
        for failure in summary["failures"]:
            lines.append(f"- {failure}\n")
    return "".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)

    store = EvidenceStore(args.run_dir)
    runtime_dir = args.runtime_dir or store.mkdir("broker-runtime")
    supervisor_dir = store.mkdir("supervisor")
    socket_path = runtime_dir / args.socket_name
    audit_path = runtime_dir / args.audit_name
    broker_process: subprocess.Popen[str] | None = None
    started = time.monotonic()
    manifest: dict[str, Any] | None = None
    audit_summary: dict[str, Any] | None = None
    supervisor_rc: int | None = None
    failures: list[str] = []
    try:
        if not args.dry_run:
            broker_process = start_broker(args, runtime_dir)
            wait_for_broker(socket_path, broker_process, args.ready_timeout)

        supervisor_result = run_supervisor(args, runtime_dir, supervisor_dir)
        supervisor_rc = supervisor_result.returncode
        store.write_text("supervisor-output.txt", supervisor_result.stdout)
        if supervisor_result.returncode != 0:
            failures.append(f"supervisor exited rc={supervisor_result.returncode}")

        manifest_path = supervisor_dir / "manifest.json"
        if manifest_path.exists():
            manifest = load_json(manifest_path)
            failures.extend(validate_manifest(manifest, args))
        else:
            failures.append(f"missing supervisor manifest: {manifest_path}")

        if audit_path.exists():
            records, malformed = read_audit_jsonl(audit_path)
            audit_summary = summarize_audit(records, malformed, audit_path)
            store.write_json("broker-audit-summary.json", audit_summary)
            store.write_text("broker-audit-report.md", render_audit_markdown(audit_summary))
            failures.extend(validate_audit(audit_summary, args))
        elif not args.dry_run:
            failures.append(f"missing broker audit: {audit_path}")

        summary = {
            "schema": "a90-broker-mixed-soak-gate-v190",
            "pass": not failures,
            "backend": args.backend,
            "duration_sec": round(time.monotonic() - started, 6),
            "workload": args.workload or ["cpu-memory-profiles"],
            "profile": args.profile,
            "workload_profile": args.workload_profile,
            "seed": args.seed,
            "supervisor_rc": supervisor_rc,
            "run_dir": str(store.run_dir),
            "supervisor_dir": str(supervisor_dir),
            "broker_runtime_dir": str(runtime_dir),
            "socket": str(socket_path),
            "audit": str(audit_path),
            "dry_run": args.dry_run,
            "failures": failures,
        }
        store.write_json("broker-mixed-soak-summary.json", summary)
        store.write_text("broker-mixed-soak-report.md", render_report(summary, manifest, audit_summary))
        print(
            f"{'PASS' if summary['pass'] else 'FAIL'} backend={args.backend} "
            f"workloads={','.join(args.workload or ['cpu-memory-profiles'])} supervisor_rc={supervisor_rc} "
            f"failures={len(failures)} out={store.run_dir}"
        )
        return 0 if summary["pass"] else 1
    finally:
        broker_stdout, broker_stderr = stop_broker(broker_process)
        if broker_stdout:
            store.write_text("broker-stdout.txt", broker_stdout)
        if broker_stderr:
            store.write_text("broker-stderr.txt", broker_stderr)


if __name__ == "__main__":
    raise SystemExit(main())
