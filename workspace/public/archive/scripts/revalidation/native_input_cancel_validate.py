#!/usr/bin/env python3
"""Validate q-cancel handling for blocking native input commands."""

from __future__ import annotations

import argparse
import json
import re
import socket
import time
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.48 (v148)"
END_RE = re.compile(r"^A90P1 END (?P<fields>.+)$", re.MULTILINE)


@dataclass
class CancelCase:
    command: str
    start_marker: str


@dataclass
class CancelResult:
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    errors: list[str]
    text: str


DEFAULT_CASES = [
    CancelCase("waitkey 1", "waitkey: waiting"),
    CancelCase("waitgesture 1", "waitgesture: waiting"),
    CancelCase("inputmonitor 0", "inputmonitor: raw DOWN/UP/REPEAT"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=float, default=8.0, help="per-case timeout seconds")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", default="tmp/validation/native-input-cancel-v148.txt")
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--skip-inputmonitor", action="store_true", help="only validate waitkey/waitgesture")
    return parser.parse_args()


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in text.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        fields[key] = value
    return fields


def parse_end(text: str) -> dict[str, str] | None:
    matches = list(END_RE.finditer(text))
    if not matches:
        return None
    return parse_fields(matches[-1].group("fields"))


def bridge_exchange(host: str, port: int, line: str, timeout_sec: float) -> str:
    data = bytearray()
    deadline = time.monotonic() + timeout_sec
    with socket.create_connection((host, port), timeout=min(3.0, timeout_sec)) as sock:
        sock.settimeout(0.25)
        sock.sendall(("\n" + line + "\n").encode("utf-8"))
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(8192)
            except socket.timeout:
                continue
            if not chunk:
                break
            data.extend(chunk)
            if b"A90P1 END " in data:
                break
    return data.decode("utf-8", errors="replace")


def ensure_hidden(args: argparse.Namespace) -> None:
    text = bridge_exchange(args.host, args.port, "cmdv1 hide", args.timeout)
    end = parse_end(text)
    if end is None:
        raise RuntimeError(f"hide did not return A90P1 END\n{text}")
    if int(end.get("rc", "1"), 0) != 0:
        raise RuntimeError(f"hide failed rc={end.get('rc')}\n{text}")


def verify_version(args: argparse.Namespace) -> None:
    text = bridge_exchange(args.host, args.port, "cmdv1 version", args.timeout)
    end = parse_end(text)
    if end is None:
        raise RuntimeError(f"version did not return A90P1 END\n{text}")
    if args.expect_version not in text:
        raise RuntimeError(f"missing expected version {args.expect_version!r}\n{text}")
    if int(end.get("rc", "1"), 0) != 0 or end.get("status") != "ok":
        raise RuntimeError(f"version failed rc={end.get('rc')} status={end.get('status')}\n{text}")


def run_cancel_case(args: argparse.Namespace, case: CancelCase) -> CancelResult:
    started = time.monotonic()
    data = bytearray()
    sent_q = False
    errors: list[str] = []
    deadline = started + args.timeout

    ensure_hidden(args)
    with socket.create_connection((args.host, args.port), timeout=min(3.0, args.timeout)) as sock:
        sock.settimeout(0.25)
        sock.sendall(("\ncmdv1 " + case.command + "\n").encode("utf-8"))
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(8192)
            except socket.timeout:
                chunk = b""
            if chunk:
                data.extend(chunk)
            text = data.decode("utf-8", errors="replace")
            if not sent_q and case.start_marker in text:
                sock.sendall(b"q")
                sent_q = True
            if "A90P1 END " in text:
                break
    text = data.decode("utf-8", errors="replace")
    end = parse_end(text)
    rc: int | None = None
    status = "missing"
    if not sent_q:
        errors.append(f"start marker not observed: {case.start_marker}")
    if end is None:
        errors.append("missing A90P1 END")
    else:
        status = end.get("status", "missing")
        rc = int(end.get("rc", "1"), 0)
        if rc != -125:
            errors.append(f"expected rc=-125 cancel, got rc={rc}")
        if status != "error":
            errors.append(f"expected status=error for cancelled command, got {status}")
    if "cancelled by q" not in text:
        errors.append("missing cancelled-by-q output")
    return CancelResult(
        command=case.command,
        ok=not errors,
        rc=rc,
        status=status,
        duration_sec=time.monotonic() - started,
        errors=errors,
        text=text,
    )


def render_text(results: list[CancelResult]) -> str:
    lines: list[str] = []
    for result in results:
        verdict = "PASS" if result.ok else "FAIL"
        lines.append(f"## {verdict}: {result.command}")
        lines.append(f"rc={result.rc} status={result.status} duration={result.duration_sec:.3f}s")
        if result.errors:
            lines.append("errors:")
            lines.extend(f"- {error}" for error in result.errors)
        lines.append("```")
        lines.append(result.text.rstrip())
        lines.append("```")
        lines.append("")
    passed = sum(1 for result in results if result.ok)
    lines.insert(0, f"PASS cases={passed}/{len(results)}")
    lines.insert(1, "")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    cases = DEFAULT_CASES
    if args.skip_inputmonitor:
        cases = DEFAULT_CASES[:2]

    verify_version(args)
    results = [run_cancel_case(args, case) for case in cases]
    text = render_text(results)
    out_path = REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    if args.json_out:
        json_path = REPO_ROOT / args.json_out
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps([asdict(result) for result in results], indent=2))
    print(text)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
