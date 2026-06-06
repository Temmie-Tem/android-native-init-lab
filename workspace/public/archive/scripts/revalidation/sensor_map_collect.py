#!/usr/bin/env python3
"""Collect read-only thermal and power sensor map evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.56 (v156)"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass
class CommandCapture:
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    text: str
    error: str


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=PRIVATE_DIR_MODE, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory output path: {path}")
    path.chmod(PRIVATE_DIR_MODE)


def write_private_text(path: Path, text: str) -> None:
    ensure_private_dir(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, PRIVATE_FILE_MODE)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            fd = -1
            file.write(text)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def run_capture(args: argparse.Namespace, command: list[str], timeout: float) -> CommandCapture:
    started = time.monotonic()
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            timeout,
            command,
            retry_unsafe=False,
        )
        duration = time.monotonic() - started
        return CommandCapture(" ".join(command), result.rc == 0 and result.status == "ok",
                              result.rc, result.status, duration, result.text, "")
    except Exception as exc:  # noqa: BLE001 - collector keeps failure evidence
        duration = time.monotonic() - started
        return CommandCapture(" ".join(command), False, None, "missing", duration, "", str(exc))


def default_output_path() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "sensormap" / f"a90-sensormap-{stamp}.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=float, default=45.0, help="per-command timeout")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", type=Path, default=default_output_path(), help="private output text path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    commands = (
        ["version"],
        ["sensormap"],
        ["sensormap", "thermal"],
        ["sensormap", "power"],
        ["sensormap", "paths"],
        ["status"],
        ["bootstatus"],
    )
    captures = [run_capture(args, command, args.timeout) for command in commands]
    version_matches = args.expect_version in captures[0].text
    failed = [capture for capture in captures if not capture.ok]
    pass_ok = version_matches and not failed

    lines = [
        "A90 HOST SENSOR MAP",
        f"generated={dt.datetime.now(dt.timezone.utc).isoformat()}",
        "policy=read-only; no cooling/charger/write operations",
        f"expect_version={args.expect_version}",
        f"version_matches={version_matches}",
        f"result={'PASS' if pass_ok else 'FAIL'}",
        "",
    ]
    for capture in captures:
        lines.append(f"[cmd {capture.command}]")
        lines.append(f"ok={capture.ok} rc={capture.rc} status={capture.status} duration={capture.duration_sec:.3f}s")
        if capture.error:
            lines.append(f"error={capture.error}")
        if capture.text:
            lines.append(capture.text.rstrip())
        lines.append("")
    write_private_text(output, "\n".join(lines).rstrip() + "\n")
    print(f"{'PASS' if pass_ok else 'FAIL'} out={output} failed_commands={len(failed)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
