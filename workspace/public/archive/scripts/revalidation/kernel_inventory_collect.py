#!/usr/bin/env python3
"""Collect read-only A90 kernel capability inventory evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import stat
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.54 (v154)"
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


def write_private_text(path: Path, text: str) -> None:
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
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            fd = -1
            file.write(text)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def run_host_command(command: list[str], timeout: int = 10) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_capture(args: argparse.Namespace, command: list[str]) -> CommandCapture:
    started = time.monotonic()
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            args.timeout,
            command,
            retry_unsafe=False,
        )
        duration = time.monotonic() - started
        ok = result.rc == 0 and result.status == "ok"
        return CommandCapture(" ".join(command), ok, result.rc, result.status, duration, result.text, "")
    except Exception as exc:  # noqa: BLE001 - collector preserves failure evidence
        duration = time.monotonic() - started
        return CommandCapture(" ".join(command), False, None, "missing", duration, "", str(exc))


def collect_host_metadata(args: argparse.Namespace) -> list[str]:
    lines: list[str] = []

    lines.append(f"repo={REPO_ROOT}")
    rc, text = run_host_command(["git", "rev-parse", "--short", "HEAD"], timeout=5)
    lines.append(f"git_head={text.strip() if rc == 0 else 'unknown'}")
    rc, text = run_host_command(["git", "status", "--short"], timeout=5)
    lines.append(f"git_dirty={'yes' if rc == 0 and text.strip() else 'no' if rc == 0 else 'unknown'}")
    if rc == 0 and text.strip():
        lines.append("git_status_short:")
        lines.extend(f"  {line}" for line in text.splitlines())
    if args.boot_image:
        boot_image = Path(args.boot_image)
        if not boot_image.is_absolute():
            boot_image = REPO_ROOT / boot_image
        if boot_image.exists():
            lines.append(f"boot_image={boot_image}")
            lines.append(f"boot_image_sha256={sha256_file(boot_image)}")
        else:
            lines.append(f"boot_image_missing={boot_image}")
    return lines


def default_output_path() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "kernelinv" / f"a90-kernelinv-{stamp}.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=float, default=20.0, help="per-command timeout")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", type=Path, default=default_output_path(), help="private output text path")
    parser.add_argument("--boot-image", help="optional boot image path to hash")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    captures = [
        run_capture(args, ["version"]),
        run_capture(args, ["kernelinv"]),
        run_capture(args, ["kernelinv", "full"]),
        run_capture(args, ["kernelinv", "paths"]),
        run_capture(args, ["status"]),
        run_capture(args, ["bootstatus"]),
    ]
    version_capture = captures[0]
    version_matches = args.expect_version in version_capture.text
    failed = [capture for capture in captures if not capture.ok]
    pass_ok = version_matches and not failed

    lines: list[str] = []
    lines.append("A90 HOST KERNEL INVENTORY")
    lines.append(f"generated={dt.datetime.now(dt.timezone.utc).isoformat()}")
    lines.append("policy=read-only; no pstore mount; no watchdog open; no tracing enable")
    lines.append(f"expect_version={args.expect_version}")
    lines.append(f"version_matches={version_matches}")
    lines.append(f"result={'PASS' if pass_ok else 'FAIL'}")
    lines.append("")
    lines.append("[host]")
    lines.extend(collect_host_metadata(args))
    lines.append("")
    for capture in captures:
        lines.append(f"[cmd {capture.command}]")
        lines.append(f"ok={capture.ok} rc={capture.rc} status={capture.status} duration={capture.duration_sec:.3f}s")
        if capture.error:
            lines.append(f"error={capture.error}")
        if capture.text:
            lines.append(capture.text.rstrip())
        lines.append("")
    lines.append("[manifest]")
    lines.append(str([asdict(capture) for capture in captures]))
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
