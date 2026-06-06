#!/usr/bin/env python3
"""Host helper for the A90 v100 custom TCP remote shell.

The remote shell is intentionally disabled by default and requires an explicit
`rshell start` plus token authentication over the USB NCM address.
"""

from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
DEFAULT_HOST = "192.168.7.2"
DEFAULT_PORT = 2326
TOKEN_RE = re.compile(r"rshell: token=([0-9a-fA-F]{16,128})")
END_RE = re.compile(r"^A90RSH1 END rc=(?P<rc>-?\d+)", re.MULTILINE)


def run_a90ctl(args: list[str], timeout: int = 20, allow_error: bool = False) -> str:
    command = [sys.executable, str(A90CTL), "--timeout", str(timeout), *args]
    if allow_error:
        command.insert(4, "--allow-error")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0 and not allow_error:
        raise SystemExit(result.stdout.strip() or f"a90ctl failed rc={result.returncode}")
    return result.stdout


def extract_token(text: str) -> str | None:
    matches = TOKEN_RE.findall(text)
    return matches[-1] if matches else None


def device_token(timeout: int = 10) -> str:
    text = run_a90ctl(["rshell", "token", "show"], timeout=timeout)
    token = extract_token(text)
    if not token:
        raise SystemExit(f"could not parse rshell token\n{text}")
    return token


def read_until(sock: socket.socket, marker: bytes, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    data = bytearray()
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(8192)
        except socket.timeout:
            continue
        if not chunk:
            break
        data.extend(chunk)
        if marker in data:
            break
    return data.decode("utf-8", errors="replace")


def rshell_exchange(host: str, port: int, token: str, command: str, timeout: float) -> tuple[int, str]:
    with socket.create_connection((host, port), timeout=min(timeout, 5.0)) as sock:
        sock.settimeout(0.25)
        banner = read_until(sock, b"\n", 3.0)
        if "A90RSH1 READY" not in banner:
            raise RuntimeError(f"unexpected banner: {banner!r}")
        sock.sendall(f"AUTH {token}\n".encode())
        auth = read_until(sock, b"\n", 3.0)
        if "OK auth" not in auth:
            raise RuntimeError(f"auth failed: {auth!r}")
        sock.sendall(f"EXEC {command}\n".encode())
        text = read_until(sock, b"A90RSH1 END ", timeout)
        text += read_until(sock, b"\n", 1.0)
        match = END_RE.search(text)
        if not match:
            raise RuntimeError(f"missing A90RSH1 END\n{text}")
        return int(match.group("rc")), text


def rshell_auth_attempt(host: str, port: int, token: str, timeout: float) -> str:
    with socket.create_connection((host, port), timeout=min(timeout, 5.0)) as sock:
        sock.settimeout(0.25)
        banner = read_until(sock, b"\n", 3.0)
        if "A90RSH1 READY" not in banner:
            raise RuntimeError(f"unexpected banner: {banner!r}")
        sock.sendall(f"AUTH {token}\n".encode())
        return read_until(sock, b"\n", timeout)






def hide_menu(args: argparse.Namespace) -> None:
    run_a90ctl(["hide"], timeout=min(args.bridge_timeout, 10), allow_error=True)


def wait_for_rshell_state(args: argparse.Namespace, running: bool, timeout: float | None = None) -> str:
    deadline = time.monotonic() + (timeout if timeout is not None else args.bridge_timeout)
    expected = "running=yes" if running else "running=no"
    last_text = ""
    while time.monotonic() < deadline:
        last_text = run_a90ctl(["rshell", "status"], timeout=min(args.bridge_timeout, 10), allow_error=True)
        if expected in last_text:
            return last_text
        time.sleep(1.0)
    raise SystemExit(f"rshell did not reach {expected} before timeout\n{last_text}")


def cmd_status(args: argparse.Namespace) -> int:
    hide_menu(args)
    print(run_a90ctl(["rshell", "status"], timeout=args.bridge_timeout).rstrip())
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    hide_menu(args)
    text = run_a90ctl(["rshell", "start"], timeout=args.bridge_timeout, allow_error=True)
    if text.strip():
        print(text.rstrip())
    print(wait_for_rshell_state(args, running=True).rstrip())
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    hide_menu(args)
    text = run_a90ctl(["rshell", "stop"], timeout=args.bridge_timeout, allow_error=True)
    if text.strip():
        print(text.rstrip())
    print(wait_for_rshell_state(args, running=False).rstrip())
    return 0


def cmd_token(args: argparse.Namespace) -> int:
    hide_menu(args)
    print(run_a90ctl(["rshell", "token", "show"], timeout=args.bridge_timeout).rstrip())
    return 0


def cmd_exec(args: argparse.Namespace) -> int:
    hide_menu(args)
    token = args.token or device_token(args.bridge_timeout)
    rc, text = rshell_exchange(args.host, args.port, token, args.command, args.timeout)
    print(text, end="" if text.endswith("\n") else "\n")
    return rc


def cmd_invalid_token(args: argparse.Namespace) -> int:
    hide_menu(args)
    token = args.token or device_token(args.bridge_timeout)
    bad_token = "0" * len(token)
    if bad_token == token:
        bad_token = "1" * len(token)
    text = rshell_auth_attempt(args.host, args.port, bad_token, args.timeout)
    print(text, end="" if text.endswith("\n") else "\n")
    if "ERR auth" not in text:
        raise SystemExit(f"invalid token was not rejected: {text!r}")
    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    hide_menu(args)
    start_text = run_a90ctl(["rshell", "start"], timeout=args.bridge_timeout, allow_error=True)
    if start_text.strip():
        print(start_text.rstrip())
    status_text = wait_for_rshell_state(args, running=True)
    print(status_text.rstrip())
    token = args.token or extract_token(start_text) or device_token(args.bridge_timeout)
    for command in ("echo A90_RSHELL_OK", "busybox uname -a", "busybox ls /proc | busybox head -5"):
        print(f"# EXEC {command}")
        rc, text = rshell_exchange(args.host, args.port, token, command, args.timeout)
        print(text, end="" if text.endswith("\n") else "\n")
        if rc != 0:
            return rc
    return 0


def cmd_harden(args: argparse.Namespace) -> int:
    hide_menu(args)
    start_text = run_a90ctl(["rshell", "start"], timeout=args.bridge_timeout, allow_error=True)
    if start_text.strip():
        print(start_text.rstrip())
    status_text = wait_for_rshell_state(args, running=True)
    print(status_text.rstrip())
    token = args.token or extract_token(start_text) or device_token(args.bridge_timeout)
    result_rc = 0

    try:
        bad_token = "0" * len(token)
        if bad_token == token:
            bad_token = "1" * len(token)
        print("# INVALID TOKEN")
        invalid_text = rshell_auth_attempt(args.host, args.port, bad_token, args.timeout)
        print(invalid_text, end="" if invalid_text.endswith("\n") else "\n")
        if "ERR auth" not in invalid_text:
            raise SystemExit(f"invalid token was not rejected: {invalid_text!r}")

        for command in ("echo A90_RSHELL_OK", "busybox uname -a", "busybox ls /proc | busybox head -5"):
            print(f"# EXEC {command}")
            rc, text = rshell_exchange(args.host, args.port, token, command, args.timeout)
            print(text, end="" if text.endswith("\n") else "\n")
            if rc != 0:
                result_rc = rc
                break
    finally:
        stop_text = run_a90ctl(["rshell", "stop"], timeout=args.bridge_timeout, allow_error=True)
        if stop_text.strip():
            print(stop_text.rstrip())
        print(wait_for_rshell_state(args, running=False).rstrip())
    return result_rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--bridge-timeout", type=int, default=25)
    parser.add_argument("--token")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    status = subparsers.add_parser("status")
    status.set_defaults(func=cmd_status)

    start = subparsers.add_parser("start")
    start.set_defaults(func=cmd_start)

    stop = subparsers.add_parser("stop")
    stop.set_defaults(func=cmd_stop)

    token = subparsers.add_parser("token")
    token.set_defaults(func=cmd_token)

    exec_parser = subparsers.add_parser("exec")
    exec_parser.add_argument("command")
    exec_parser.set_defaults(func=cmd_exec)

    invalid_token = subparsers.add_parser("invalid-token")
    invalid_token.set_defaults(func=cmd_invalid_token)

    smoke = subparsers.add_parser("smoke")
    smoke.set_defaults(func=cmd_smoke)

    harden = subparsers.add_parser("harden")
    harden.set_defaults(func=cmd_harden)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
