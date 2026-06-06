#!/usr/bin/env python3
"""Classify fault/debug facilities for A90 native init without enabling them."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600

MANDATORY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("kernelinv-full", ["kernelinv", "full"], 45.0),
    ("tracefs-full", ["tracefs", "full"], 30.0),
    ("pstore-full", ["pstore", "full"], 30.0),
    ("watchdoginv-status", ["watchdoginv", "status"], 20.0),
    ("diag-paths", ["diag", "paths"], 20.0),
    ("cat-proc-filesystems", ["cat", "/proc/filesystems"], 20.0),
    ("cat-proc-cmdline", ["cat", "/proc/cmdline"], 20.0),
)

OPTIONAL_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("ls-sys-kernel", ["ls", "/sys/kernel"], 20.0),
    ("stat-sys-kernel-debug", ["stat", "/sys/kernel/debug"], 20.0),
    ("ls-sys-kernel-debug", ["ls", "/sys/kernel/debug"], 20.0),
    ("stat-sys-kernel-tracing", ["stat", "/sys/kernel/tracing"], 20.0),
    ("ls-sys-kernel-tracing", ["ls", "/sys/kernel/tracing"], 20.0),
    ("stat-debug-tracing", ["stat", "/sys/kernel/debug/tracing"], 20.0),
    ("ls-debug-usb", ["ls", "/sys/kernel/debug/usb"], 20.0),
    ("stat-usbmon", ["stat", "/sys/kernel/debug/usb/usbmon"], 20.0),
    ("stat-fail-page-alloc", ["stat", "/sys/kernel/debug/fail_page_alloc"], 20.0),
    ("stat-fail-futex", ["stat", "/sys/kernel/debug/fail_futex"], 20.0),
    ("stat-fail-make-request", ["stat", "/sys/kernel/debug/fail_make_request"], 20.0),
    ("stat-provoke-crash", ["stat", "/sys/kernel/debug/provoke-crash"], 20.0),
)


@dataclass
class CommandCapture:
    name: str
    command: str
    mandatory: bool
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
        raise RuntimeError(f"refusing non-directory output path: {path}")
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


def collect_host_metadata() -> dict[str, Any]:
    metadata: dict[str, Any] = {"repo": str(REPO_ROOT)}
    rc, text = run_host_command(["git", "rev-parse", "--short", "HEAD"], timeout=5)
    metadata["git_head"] = text.strip() if rc == 0 else "unknown"
    rc, text = run_host_command(["git", "status", "--short"], timeout=5)
    metadata["git_dirty"] = bool(rc == 0 and text.strip())
    metadata["git_status_short"] = text.splitlines() if rc == 0 and text.strip() else []
    return metadata


def safe_filename(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in name)


def run_capture(args: argparse.Namespace,
                bundle_dir: Path,
                name: str,
                command: list[str],
                timeout: float,
                mandatory: bool) -> CommandCapture:
    out_file = bundle_dir / f"cmd-{safe_filename(name)}.txt"
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
        capture = CommandCapture(
            name,
            " ".join(command),
            mandatory,
            ok,
            result.rc,
            result.status,
            duration,
            str(out_file),
            "",
        )
    except Exception as exc:  # noqa: BLE001 - feasibility collector preserves failure evidence
        duration = time.monotonic() - started
        text = str(exc) + "\n"
        capture = CommandCapture(
            name,
            " ".join(command),
            mandatory,
            False,
            None,
            "missing",
            duration,
            str(out_file),
            str(exc),
        )
    write_private_text(out_file, text)
    return capture


def read_capture_text(captures: list[CommandCapture], name: str) -> str:
    capture = next((item for item in captures if item.name == name), None)
    if capture is None:
        return ""
    try:
        return Path(capture.file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def command_ok(captures: list[CommandCapture], name: str) -> bool:
    capture = next((item for item in captures if item.name == name), None)
    return bool(capture and capture.ok)


def classify(captures: list[CommandCapture]) -> list[dict[str, str]]:
    filesystems = read_capture_text(captures, "cat-proc-filesystems")
    kernelinv = read_capture_text(captures, "kernelinv-full")
    tracefs = read_capture_text(captures, "tracefs-full")
    pstore = read_capture_text(captures, "pstore-full")

    debugfs_available = "debugfs" in filesystems or "debugfs=yes" in kernelinv
    tracefs_available = "tracefs" in filesystems or "tracefs=fs=yes" in tracefs or "tracefs=yes" in kernelinv
    pstore_available = "pstore" in filesystems or "pstore=fs=yes" in pstore or "pstore=yes" in kernelinv

    facilities: list[dict[str, str]] = []
    facilities.append({
        "name": "debugfs",
        "status": "read-only-only" if debugfs_available else "unavailable",
        "reason": (
            "debugfs filesystem is listed, but it is not mounted; no mount was performed"
            if debugfs_available else
            "debugfs was not confirmed through current read-only inventory"
        ),
        "recovery_precondition": "explicit debugfs mount plan, ACM rescue verified, and no writes by default",
    })
    facilities.append({
        "name": "tracefs-active-mode",
        "status": "read-only-only" if tracefs_available else "unavailable",
        "reason": (
            "tracefs filesystem is available but not mounted; active tracing writes remain blocked by default"
            if tracefs_available else
            "tracefs availability was not confirmed"
        ),
        "recovery_precondition": "separate opt-in trace plan with bounded duration, buffer size, disable path, and baseline comparison",
    })
    facilities.append({
        "name": "usbmon",
        "status": "unavailable" if not command_ok(captures, "stat-usbmon") else "read-only-only",
        "reason": "usbmon debugfs path is not currently available because debugfs is not mounted",
        "recovery_precondition": "explicit debugfs/usbmon read-only capture plan and host-side packet privacy review",
    })
    facilities.append({
        "name": "fault-injection",
        "status": "blocked",
        "reason": "fault injection requires kernel/debugfs writes and can destabilize storage, scheduler, or memory paths",
        "recovery_precondition": "physical recovery path, pstore preservation plan, bounded target, and explicit operator approval",
    })
    facilities.append({
        "name": "lkdtm-crash-trigger",
        "status": "blocked",
        "reason": "crash triggers intentionally panic/reboot the device and are not stability smoke tests",
        "recovery_precondition": "known-good boot image, TWRP access, pstore/ramoops preservation plan, and manual approval",
    })
    facilities.append({
        "name": "pstore-reboot-preservation",
        "status": "opt-in-safe-candidate" if pstore_available else "unavailable",
        "reason": (
            "pstore support is visible, but reboot preservation must be a separate explicit test"
            if pstore_available else
            "pstore support was not confirmed"
        ),
        "recovery_precondition": "explicit reboot plan, pre/post evidence bundle, and no crash trigger by default",
    })
    facilities.append({
        "name": "watchdog-debug",
        "status": "blocked",
        "reason": "watchdog device open can arm reboot behavior; current policy is read-only-no-open",
        "recovery_precondition": "do not open watchdog until a dedicated watchdog safety plan exists",
    })
    facilities.append({
        "name": "raw-block-or-modem-debug",
        "status": "blocked",
        "reason": "raw block, modem, EFS, bootloader, and security partitions remain outside the native-init safety envelope",
        "recovery_precondition": "not applicable for current Wi-Fi/network baseline work",
    })
    return facilities


def default_bundle_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "soak" / "fault-debug-feasibility" / f"v169-fault-debug-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout-scale", type=float, default=1.0, help="multiply per-command timeouts")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--bundle-dir", type=Path, default=default_bundle_dir(), help="private evidence output directory")
    return parser.parse_args()


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# A90 v169 Fault/Debug Feasibility\n\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- expect_version: `{manifest['expect_version']}`\n",
        f"- version_matches: `{manifest['version_matches']}`\n",
        f"- policy: `{manifest['policy']}`\n",
        f"- mutation_performed: `{manifest['mutation_performed']}`\n",
        f"- failed mandatory commands: `{manifest['failed_mandatory_count']}`\n",
        f"- failed optional commands: `{manifest['failed_optional_count']}`\n\n",
        "## Facility Classification\n\n",
    ]
    for item in manifest["facilities"]:
        lines.append(
            f"- `{item['name']}`: `{item['status']}` — {item['reason']} "
            f"Recovery precondition: {item['recovery_precondition']}\n"
        )
    lines.append("\n## Command Captures\n\n")
    for capture in manifest["commands"]:
        label = "OK" if capture["ok"] else "FAIL"
        required = "mandatory" if capture["mandatory"] else "optional"
        lines.append(
            f"- {label} `{capture['command']}` ({required}) rc={capture['rc']} "
            f"status={capture['status']} duration={capture['duration_sec']:.3f}s "
            f"file=`{capture['file']}`\n"
        )
    return "".join(lines)


def main() -> int:
    args = parse_args()
    bundle_dir = args.bundle_dir if args.bundle_dir.is_absolute() else REPO_ROOT / args.bundle_dir
    ensure_private_dir(bundle_dir.parent)
    ensure_private_dir(bundle_dir)

    captures: list[CommandCapture] = []
    for name, command, timeout in MANDATORY_COMMANDS:
        captures.append(run_capture(args, bundle_dir, name, command, timeout * args.timeout_scale, True))
    for name, command, timeout in OPTIONAL_COMMANDS:
        captures.append(run_capture(args, bundle_dir, name, command, timeout * args.timeout_scale, False))

    version_text = read_capture_text(captures, "version")
    version_matches = args.expect_version in version_text
    failed_mandatory = [item for item in captures if item.mandatory and not item.ok]
    failed_optional = [item for item in captures if not item.mandatory and not item.ok]
    facilities = classify(captures)
    mutation_performed = False
    statuses = {item["status"] for item in facilities}
    pass_ok = (
        version_matches
        and not failed_mandatory
        and "blocked" in statuses
        and ("read-only-only" in statuses or "opt-in-safe-candidate" in statuses or "unavailable" in statuses)
        and not mutation_performed
    )

    manifest: dict[str, Any] = {
        "label": "v169 Fault/Debug Feasibility",
        "created_host_ts": time.time(),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": collect_host_metadata(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": pass_ok,
        "policy": "read-only; no debugfs/tracefs mount; no fault injection; no active tracing; no LKDTM/crash; no watchdog open",
        "mutation_performed": mutation_performed,
        "failed_mandatory_count": len(failed_mandatory),
        "failed_optional_count": len(failed_optional),
        "facilities": facilities,
        "commands": [asdict(capture) for capture in captures],
    }
    write_private_text(
        bundle_dir / "fault-debug-feasibility-report.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    write_private_text(bundle_dir / "fault-debug-feasibility-report.md", render_markdown(manifest))

    print(
        f"{'PASS' if pass_ok else 'FAIL'} bundle={bundle_dir} "
        f"failed_mandatory={len(failed_mandatory)} failed_optional={len(failed_optional)}"
    )
    return 0 if pass_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
