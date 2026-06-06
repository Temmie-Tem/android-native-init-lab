#!/usr/bin/env python3
"""Start tcpctl, run NCM broker smoke, and stop tcpctl as one lifecycle check."""

from __future__ import annotations

import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from a90_broker import DEFAULT_DEVICE_IP, DEFAULT_TCP_PORT, DEFAULT_TCP_TIMEOUT, redact_text  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from tcpctl_host import (  # noqa: E402
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_DEVICE_BINARY,
    DEFAULT_TCPCTL_TOKEN_PATH,
    DEFAULT_TOKEN_COMMAND,
    DEFAULT_TOYBOX,
    get_tcpctl_token,
)


READY_MARKER = "tcpctl: listening"


@dataclass
class LifecycleResult:
    name: str
    ok: bool
    detail: str
    artifacts: list[str]


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage an NCM tcpctl listener around an A90B1 ncm-tcpctl broker smoke.",
    )
    parser.add_argument("--run-dir", type=Path,
                        default=Path("tmp") / f"a90-v194-ncm-lifecycle-{timestamp()}")
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=DEFAULT_TCP_TIMEOUT)
    parser.add_argument("--device-binary", default="/cache/bin/a90_tcpctl")
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--idle-timeout", type=int, default=120)
    parser.add_argument("--max-clients", type=int, default=0,
                        help="tcpctl max_clients; default 0 keeps listener alive for lifecycle tests")
    parser.add_argument("--token")
    parser.add_argument("--token-command", default=DEFAULT_TOKEN_COMMAND)
    parser.add_argument("--token-path", default=DEFAULT_TCPCTL_TOKEN_PATH)
    parser.add_argument("--bridge-timeout", type=float, default=30.0)
    parser.add_argument("--device-protocol", choices=("auto", "cmdv1", "raw"), default="auto")
    parser.add_argument("--busy-retries", type=int, default=3)
    parser.add_argument("--busy-retry-sleep", type=float, default=3.0)
    parser.add_argument("--menu-hide-sleep", type=float, default=3.0)
    parser.add_argument("--clients", type=int, default=2)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--ready-timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default="")
    parser.add_argument("--leave-running", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="write planned lifecycle commands without touching device state")
    return parser


def tcpctl_script() -> Path:
    return SCRIPT_DIR / "tcpctl_host.py"


def smoke_script() -> Path:
    return SCRIPT_DIR / "a90_broker_concurrent_smoke.py"


def redacted_command(command: list[str]) -> list[str]:
    return [redact_text(part) for part in command]


class LineReader(threading.Thread):
    def __init__(self, stream: Any) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.lines: list[str] = []
        self.ready = threading.Event()
        self.done = threading.Event()
        self.errors: "queue.Queue[BaseException]" = queue.Queue()

    def run(self) -> None:
        try:
            for line in self.stream:
                self.lines.append(line)
                if READY_MARKER in line:
                    self.ready.set()
        except BaseException as exc:  # noqa: BLE001 - reader should not kill owner
            self.errors.put(exc)
        finally:
            self.done.set()

    def text(self) -> str:
        return "".join(self.lines)


def base_tcpctl_args(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(tcpctl_script()),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--device-ip",
        args.device_ip,
        "--tcp-port",
        str(args.tcp_port),
        "--device-binary",
        args.device_binary,
        "--toybox",
        args.toybox,
        "--idle-timeout",
        str(args.idle_timeout),
        "--max-clients",
        str(args.max_clients),
        "--tcp-timeout",
        str(args.tcp_timeout),
        "--token-command",
        args.token_command,
        "--token-path",
        args.token_path,
        "--bridge-timeout",
        str(args.bridge_timeout),
    ]
    if args.token:
        command.extend(["--token", args.token])
    return command


def start_command(args: argparse.Namespace) -> list[str]:
    return [*base_tcpctl_args(args), "start"]


def stop_command(args: argparse.Namespace) -> list[str]:
    return [*base_tcpctl_args(args), "stop"]


def smoke_command(args: argparse.Namespace, smoke_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(smoke_script()),
        "--backend",
        "ncm-tcpctl",
        "--run-dir",
        str(smoke_dir),
        "--device-ip",
        args.device_ip,
        "--tcp-port",
        str(args.tcp_port),
        "--tcp-timeout",
        str(args.tcp_timeout),
        "--allow-exclusive",
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--clients",
        str(args.clients),
        "--rounds",
        str(args.rounds),
        "--command",
        f"run {args.toybox} uptime",
        "--command",
        f"run {args.toybox} uname -a",
    ]
    if args.token:
        command.extend(["--token", args.token])
    if args.expect_version:
        command.extend(["--expect-version", args.expect_version])
    return command


def stop_process(process: subprocess.Popen[str] | None) -> tuple[str, str]:
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
        return "", "tcpctl start output collection timed out\n"


def run_lifecycle(args: argparse.Namespace, store: EvidenceStore) -> list[LifecycleResult]:
    smoke_dir = store.mkdir("broker-ncm-smoke")
    results: list[LifecycleResult] = []
    if not args.dry_run and not args.token:
        try:
            args.token = get_tcpctl_token(args)
            store.write_text("tcpctl-token-source.txt", "source=bridge token command\n")
            results.append(LifecycleResult("tcpctl token captured", True, "source=bridge token command", ["tcpctl-token-source.txt"]))
        except Exception as exc:  # noqa: BLE001 - lifecycle should report setup failure
            store.write_text("tcpctl-token-error.txt", redact_text(f"{type(exc).__name__}: {exc}\n"))
            return [
                LifecycleResult(
                    "tcpctl token captured",
                    False,
                    redact_text(f"{type(exc).__name__}: {exc}"),
                    ["tcpctl-token-error.txt"],
                )
            ]
    elif args.token:
        store.write_text("tcpctl-token-source.txt", "source=cli token\n")
        results.append(LifecycleResult("tcpctl token captured", True, "source=cli token", ["tcpctl-token-source.txt"]))

    planned = {
        "start": redacted_command(start_command(args)),
        "smoke": redacted_command(smoke_command(args, smoke_dir)),
        "stop": redacted_command(stop_command(args)),
    }
    store.write_json("planned-commands.json", planned)
    if args.dry_run:
        return [
            LifecycleResult("dry-run command plan", True, "device state not touched", ["planned-commands.json"]),
            LifecycleResult("max-clients unlimited", args.max_clients == 0, f"max_clients={args.max_clients}", []),
        ]

    start_proc: subprocess.Popen[str] | None = None
    reader: LineReader | None = None
    try:
        start_proc = subprocess.Popen(
            start_command(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        assert start_proc.stdout is not None
        reader = LineReader(start_proc.stdout)
        reader.start()
        if not reader.ready.wait(args.ready_timeout):
            text = reader.text()
            store.write_text("tcpctl-start-output.txt", redact_text(text))
            results.append(LifecycleResult("tcpctl listener ready", False, "ready marker timeout", ["tcpctl-start-output.txt"]))
            return results
        start_text = reader.text()
        store.write_text("tcpctl-start-output.txt", redact_text(start_text))
        auth_required = "auth=required" in start_text and "auth=none" not in start_text
        results.append(LifecycleResult("tcpctl listener ready", True, READY_MARKER, ["tcpctl-start-output.txt"]))
        results.append(LifecycleResult("tcpctl auth required", auth_required, "auth=required marker", ["tcpctl-start-output.txt"]))

        smoke = subprocess.run(
            smoke_command(args, smoke_dir),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=max(60.0, args.clients * args.rounds * args.tcp_timeout + 60.0),
        )
        store.write_text("broker-ncm-smoke-output.txt", redact_text(smoke.stdout))
        results.append(
            LifecycleResult(
                "ncm broker smoke",
                smoke.returncode == 0,
                f"rc={smoke.returncode}",
                ["broker-ncm-smoke-output.txt", "broker-ncm-smoke"],
            )
        )
    finally:
        if not args.leave_running:
            stop = subprocess.run(
                stop_command(args),
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=15.0,
            )
            store.write_text("tcpctl-stop-output.txt", redact_text(stop.stdout))
            results.append(LifecycleResult("tcpctl stop", stop.returncode == 0, f"rc={stop.returncode}", ["tcpctl-stop-output.txt"]))
        stdout, stderr = stop_process(start_proc)
        if stdout:
            store.write_text("tcpctl-start-remaining-stdout.txt", redact_text(stdout))
        if stderr:
            store.write_text("tcpctl-start-remaining-stderr.txt", redact_text(stderr))
        if reader is not None:
            reader.join(timeout=1.0)
    return results


def render_report(results: list[LifecycleResult], pass_ok: bool, run_dir: Path) -> str:
    lines = [
        "# v194 NCM/tcpctl Broker Lifecycle Check\n\n",
        f"- result: `{'PASS' if pass_ok else 'FAIL'}`\n",
        f"- run_dir: `{run_dir}`\n\n",
        "## Checks\n\n",
    ]
    for result in results:
        lines.append(f"- {'PASS' if result.ok else 'FAIL'} `{result.name}`: {result.detail}\n")
    return "".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    store = EvidenceStore(args.run_dir)
    results = run_lifecycle(args, store)
    pass_ok = all(result.ok for result in results)
    payload: dict[str, Any] = {
        "pass": pass_ok,
        "run_dir": str(args.run_dir),
        "dry_run": args.dry_run,
        "results": [asdict(result) for result in results],
    }
    store.write_json("broker-ncm-lifecycle-summary.json", payload)
    store.write_text("broker-ncm-lifecycle-report.md", render_report(results, pass_ok, args.run_dir))
    print(f"{'PASS' if pass_ok else 'FAIL'} run_dir={args.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
