#!/usr/bin/env python3
"""Host-only v193 checks for A90B1 broker auth hardening."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from a90_broker import DEFAULT_AUDIT_NAME, DEFAULT_SOCKET_NAME, DEFAULT_TOKEN_PATH, NcmTcpctlBackend, connect_and_call  # noqa: E402
from a90harness.evidence import EvidenceStore, ensure_private_dir  # noqa: E402


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def broker_script() -> Path:
    return SCRIPT_DIR / "a90_broker.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run broker auth hardening checks.")
    parser.add_argument("--run-dir", type=Path,
                        default=Path("tmp") / f"a90-v193-broker-auth-{timestamp()}")
    parser.add_argument("--ready-timeout", type=float, default=5.0)
    return parser


def run_command(command: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def start_broker(runtime_dir: Path, *extra: str, backend: str = "ncm-tcpctl") -> subprocess.Popen[str]:
    ensure_private_dir(runtime_dir)
    command = [
        sys.executable,
        str(broker_script()),
        "serve",
        "--runtime-dir",
        str(runtime_dir),
        "--backend",
        backend,
        *extra,
    ]
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


def wait_for_socket(socket_path: Path, process: subprocess.Popen[str], timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"broker exited before socket ready rc={process.returncode}")
        if socket_path.exists():
            return
        time.sleep(0.05)
    raise RuntimeError(f"broker socket was not ready: {socket_path}")


def check_selftest(store: EvidenceStore) -> CheckResult:
    result = run_command([sys.executable, str(broker_script()), "selftest"], timeout=10.0)
    store.write_text("selftest-stdout.txt", result.stdout)
    store.write_text("selftest-stderr.txt", result.stderr)
    return CheckResult("broker selftest", result.returncode == 0, f"rc={result.returncode}")


def check_no_auth_requires_explicit_allow(store: EvidenceStore) -> CheckResult:
    runtime_dir = store.mkdir("no-auth-denied-runtime")
    result = run_command([
        sys.executable,
        str(broker_script()),
        "serve",
        "--backend",
        "ncm-tcpctl",
        "--runtime-dir",
        str(runtime_dir),
        "--no-auth",
    ])
    store.write_text("no-auth-denied-stdout.txt", result.stdout)
    store.write_text("no-auth-denied-stderr.txt", result.stderr)
    ok = result.returncode != 0 and "--allow-no-auth" in result.stderr
    return CheckResult("no-auth denied unless explicitly allowed", ok, f"rc={result.returncode}")


def check_bad_token_rejected(store: EvidenceStore) -> CheckResult:
    runtime_dir = store.mkdir("bad-token-runtime")
    result = run_command([
        sys.executable,
        str(broker_script()),
        "serve",
        "--backend",
        "ncm-tcpctl",
        "--runtime-dir",
        str(runtime_dir),
        "--token",
        "not-a-token",
    ])
    store.write_text("bad-token-stdout.txt", result.stdout)
    store.write_text("bad-token-stderr.txt", result.stderr)
    ok = result.returncode != 0 and "24+ char hex" in result.stderr and "Traceback" not in result.stderr
    return CheckResult("invalid token rejected cleanly", ok, f"rc={result.returncode}")


def check_allow_no_auth_metadata(store: EvidenceStore, ready_timeout: float) -> CheckResult:
    runtime_dir = store.mkdir("no-auth-allowed-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    process = start_broker(runtime_dir, "--no-auth", "--allow-no-auth")
    try:
        wait_for_socket(socket_path, process, ready_timeout)
        response = connect_and_call(
            socket_path,
            {
                "proto": "A90B1",
                "id": "v193-fallback-version",
                "client_id": "v193-auth-check",
                "op": "cmd",
                "argv": ["version"],
                "timeout_ms": 1000,
            },
            3.0,
        )
        metadata = (runtime_dir / "broker.json").read_text(encoding="utf-8")
        store.write_json("no-auth-allowed-response.json", response)
        store.write_text("no-auth-allowed-metadata.json", metadata)
        ok = (
            response.get("backend") in {"acm-cmdv1", "ncm-tcpctl"} and
            '"required": false' in metadata and
            '"token_source": "disabled"' in metadata
        )
        return CheckResult("explicit no-auth records disabled auth metadata", ok, f"backend={response.get('backend')}")
    finally:
        stdout, stderr = stop_broker(process)
        if stdout:
            store.write_text("no-auth-allowed-stdout.txt", stdout)
        if stderr:
            store.write_text("no-auth-allowed-stderr.txt", stderr)


def broker_call(socket_path: Path, argv: list[str], command_class: str | None = None) -> dict[str, Any]:
    safe_name = "-".join(part.replace("/", "_") for part in argv[:2])
    payload: dict[str, Any] = {
        "proto": "A90B1",
        "id": f"v193-policy-{os.getpid()}-{len(argv)}-{safe_name}",
        "client_id": "v193-auth-check",
        "op": "cmd",
        "argv": argv,
        "timeout_ms": 1000,
    }
    if command_class is not None:
        payload["class"] = command_class
    return connect_and_call(socket_path, payload, 3.0)


def check_default_policy_blocks_mutating(store: EvidenceStore, ready_timeout: float) -> CheckResult:
    runtime_dir = store.mkdir("default-policy-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    process = start_broker(runtime_dir, backend="fake")
    try:
        wait_for_socket(socket_path, process, ready_timeout)
        status = broker_call(socket_path, ["status"], "observe")
        run = broker_call(socket_path, ["run", "id"], "exclusive")
        menu = broker_call(socket_path, ["menu"], "operator-action")
        sensitive_cat = broker_call(socket_path, ["cat", DEFAULT_TOKEN_PATH], "operator-action")
        reboot = broker_call(socket_path, ["reboot"], "rebind-destructive")
        store.write_json("default-policy-responses.json", {
            "status": status,
            "run": run,
            "menu": menu,
            "sensitive_cat": sensitive_cat,
            "reboot": reboot,
        })
        ok = (
            status.get("ok") is True and
            run.get("ok") is False and run.get("status") == "exclusive-required" and
            menu.get("ok") is False and menu.get("status") == "operator-required" and
            sensitive_cat.get("ok") is False and sensitive_cat.get("status") == "sensitive-path-denied" and
            reboot.get("ok") is False and reboot.get("status") == "operator-required"
        )
        return CheckResult(
            "default broker policy blocks mutating commands",
            ok,
            f"run={run.get('status')} menu={menu.get('status')} sensitive_cat={sensitive_cat.get('status')} reboot={reboot.get('status')}",
        )
    finally:
        stdout, stderr = stop_broker(process)
        if stdout:
            store.write_text("default-policy-stdout.txt", stdout)
        if stderr:
            store.write_text("default-policy-stderr.txt", stderr)


def check_allow_policy_flags(store: EvidenceStore, ready_timeout: float) -> CheckResult:
    runtime_dir = store.mkdir("allow-policy-runtime")
    socket_path = runtime_dir / DEFAULT_SOCKET_NAME
    process = start_broker(runtime_dir, "--allow-exclusive", backend="fake")
    try:
        wait_for_socket(socket_path, process, ready_timeout)
        run = broker_call(socket_path, ["run", "id"], "exclusive")
        menu = broker_call(socket_path, ["menu"], "operator-action")
        sensitive_cat = broker_call(socket_path, ["cat", DEFAULT_TOKEN_PATH], "operator-action")
        store.write_json("allow-policy-responses.json", {"run": run, "menu": menu, "sensitive_cat": sensitive_cat})
        ok = (
            run.get("ok") is True and
            menu.get("ok") is True and
            sensitive_cat.get("ok") is False and
            sensitive_cat.get("status") == "sensitive-path-denied"
        )
        return CheckResult(
            "allow-exclusive permits exclusive and operator classes",
            ok,
            f"run={run.get('status')} menu={menu.get('status')} sensitive_cat={sensitive_cat.get('status')}",
        )
    finally:
        stdout, stderr = stop_broker(process)
        if stdout:
            store.write_text("allow-policy-stdout.txt", stdout)
        if stderr:
            store.write_text("allow-policy-stderr.txt", stderr)


def check_tcpctl_final_status_parser(_: EvidenceStore) -> CheckResult:
    cases = {
        "auth_then_err": ("a90_tcpctl v1 ready\nOK authenticated\n[exit 1]\nERR exit=1\n", "error"),
        "auth_then_ok": ("a90_tcpctl v1 ready\nOK authenticated\n[exit 0]\nOK\n", "ok"),
        "auth_required": ("a90_tcpctl v1 ready\nERR auth-required\n", "auth-failed"),
        "auth_failed": ("a90_tcpctl v1 ready\nERR auth-failed\n", "auth-failed"),
    }
    failures: list[str] = []
    for name, (text, expected) in cases.items():
        actual = NcmTcpctlBackend.tcpctl_status(text)
        if actual != expected:
            failures.append(f"{name}: expected {expected} got {actual}")
    return CheckResult(
        "tcpctl final status parser",
        not failures,
        "ok" if not failures else "; ".join(failures),
    )


def render_report(checks: list[CheckResult], pass_ok: bool, run_dir: Path) -> str:
    lines = [
        "# v193 Broker Auth Hardening Check\n\n",
        f"- result: `{'PASS' if pass_ok else 'FAIL'}`\n",
        f"- run_dir: `{run_dir}`\n\n",
        "## Checks\n\n",
    ]
    for check in checks:
        lines.append(f"- {'PASS' if check.ok else 'FAIL'} `{check.name}`: {check.detail}\n")
    return "".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    store = EvidenceStore(args.run_dir)
    checks = [
        check_selftest(store),
        check_no_auth_requires_explicit_allow(store),
        check_bad_token_rejected(store),
        check_allow_no_auth_metadata(store, args.ready_timeout),
        check_default_policy_blocks_mutating(store, args.ready_timeout),
        check_allow_policy_flags(store, args.ready_timeout),
        check_tcpctl_final_status_parser(store),
    ]
    pass_ok = all(check.ok for check in checks)
    summary: dict[str, Any] = {
        "pass": pass_ok,
        "run_dir": str(args.run_dir),
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("broker-auth-hardening-summary.json", summary)
    store.write_text("broker-auth-hardening-report.md", render_report(checks, pass_ok, args.run_dir))
    print(f"{'PASS' if pass_ok else 'FAIL'} run_dir={args.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
