#!/usr/bin/env python3
"""Bundle read-only kernel diagnostics evidence from A90 native init."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.55 (v155)"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600

DEVICE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 20.0),
    ("bootstatus", ["bootstatus"], 20.0),
    ("selftest-verbose", ["selftest", "verbose"], 20.0),
    ("kernelinv-summary", ["kernelinv"], 20.0),
    ("kernelinv-full", ["kernelinv", "full"], 30.0),
    ("kernelinv-paths", ["kernelinv", "paths"], 20.0),
    ("diag-full", ["diag", "full"], 45.0),
    ("diag-paths", ["diag", "paths"], 20.0),
    ("longsoak-status", ["longsoak", "status", "verbose"], 20.0),
    ("exposure-guard", ["exposure", "guard"], 20.0),
    ("wifiinv-refresh", ["wifiinv", "refresh"], 45.0),
    ("wififeas-refresh", ["wififeas", "refresh"], 45.0),
)


@dataclass
class CommandCapture:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


def nofollow_flag() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def cloexec_flag() -> int:
    return getattr(os, "O_CLOEXEC", 0)


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=PRIVATE_DIR_MODE, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory bundle path: {path}")
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
        with os.fdopen(fd, "wb") as file:
            fd = -1
            file.write(data)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def write_private_text(path: Path, text: str) -> None:
    write_private_bytes(path, text.encode("utf-8"))


def run_capture(args: argparse.Namespace,
                bundle_dir: Path,
                name: str,
                command: list[str],
                timeout: float) -> CommandCapture:
    out_file = bundle_dir / f"cmd-{name}.txt"
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
        text = result.text
        ok = result.rc == 0 and result.status == "ok"
        capture = CommandCapture(name, " ".join(command), ok, result.rc, result.status, duration, str(out_file), "")
    except Exception as exc:  # noqa: BLE001 - bundle keeps failure evidence
        duration = time.monotonic() - started
        text = str(exc) + "\n"
        capture = CommandCapture(name, " ".join(command), False, None, "missing", duration, str(out_file), str(exc))
    write_private_text(out_file, text)
    return capture


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout-scale", type=float, default=1.0, help="multiply per-command timeouts")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--bundle-dir", default="tmp/kerneldiag/a90-kerneldiag-v155-bundle")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir)
    ensure_private_dir(bundle_dir)
    captures: list[CommandCapture] = []

    for name, command, timeout in DEVICE_COMMANDS:
        captures.append(run_capture(args, bundle_dir, name, command, timeout * args.timeout_scale))

    version_capture = next((capture for capture in captures if capture.name == "version"), None)
    version_text = Path(version_capture.file).read_text(encoding="utf-8") if version_capture else ""
    version_matches = args.expect_version in version_text
    failed = [capture for capture in captures if not capture.ok]
    pass_ok = version_matches and not failed

    manifest: dict[str, Any] = {
        "bundle_dir": str(bundle_dir),
        "created_host_ts": time.time(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": pass_ok,
        "commands": [asdict(capture) for capture in captures],
        "failed_command_count": len(failed),
        "policy": "read-only; no pstore mount; no watchdog open; no tracing enable; no wifi enable",
    }
    write_private_text(
        bundle_dir / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )

    lines = [
        "# A90 Kernel Diagnostics Bundle\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- expect_version: `{args.expect_version}`\n",
        f"- version_matches: `{version_matches}`\n",
        f"- failed commands: `{len(failed)}`\n",
        "- policy: read-only; no pstore mount; no watchdog open; no tracing enable; no wifi enable\n\n",
        "## Command Captures\n\n",
    ]
    for capture in captures:
        lines.append(
            f"- {'OK' if capture.ok else 'FAIL'} `{capture.command}` rc={capture.rc} "
            f"status={capture.status} duration={capture.duration_sec:.3f}s file=`{capture.file}`\n"
        )
    write_private_text(bundle_dir / "README.md", "".join(lines))

    print(f"{'PASS' if pass_ok else 'FAIL'} bundle={bundle_dir} failed_commands={len(failed)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
