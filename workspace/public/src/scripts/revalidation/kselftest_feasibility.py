#!/usr/bin/env python3
"""Classify safe kselftest/LTP subset candidates for A90 native init."""

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

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a90_transport as transport  # noqa: E402
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600

MANDATORY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("kernelinv-full", ["kernelinv", "full"], 45.0),
    ("userland-status", ["userland", "status"], 20.0),
    ("helpers-status", ["helpers", "status"], 20.0),
    ("tracefs-status", ["tracefs", "status"], 20.0),
    ("pstore-status", ["pstore", "status"], 20.0),
    ("watchdoginv-status", ["watchdoginv", "status"], 20.0),
    ("sensormap-summary", ["sensormap", "summary"], 20.0),
)

OPTIONAL_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("diag-summary", ["diag", "summary"], 45.0),
    ("cat-proc-version", ["cat", "/proc/version"], 20.0),
    ("cat-proc-cmdline", ["cat", "/proc/cmdline"], 20.0),
    ("cat-proc-filesystems", ["cat", "/proc/filesystems"], 20.0),
    ("cat-proc-self-status", ["cat", "/proc/self/status"], 20.0),
    ("cat-proc-meminfo", ["cat", "/proc/meminfo"], 20.0),
    ("cat-proc-uptime", ["cat", "/proc/uptime"], 20.0),
    ("ls-sys-class-thermal", ["ls", "/sys/class/thermal"], 20.0),
    ("ls-sys-class-power-supply", ["ls", "/sys/class/power_supply"], 20.0),
    ("toybox-applets", ["run", "/cache/bin/toybox"], 20.0),
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
    except Exception as exc:  # noqa: BLE001 - feasibility collector preserves evidence
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


def read_capture_text(capture: CommandCapture) -> str:
    try:
        return Path(capture.file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def has_text(captures: list[CommandCapture], name: str, needle: str) -> bool:
    capture = next((item for item in captures if item.name == name), None)
    return bool(capture and needle in read_capture_text(capture))


def classify(captures: list[CommandCapture]) -> dict[str, list[dict[str, str]]]:
    candidates: list[dict[str, str]] = [
        {
            "name": "timers-basic-userspace-helper",
            "status": "safe-candidate",
            "reason": "bounded static helper can measure sleep/jitter without kernel mutation; v164 already has PID1 run-loop proxy evidence",
        },
        {
            "name": "procfs-readers",
            "status": "safe-candidate",
            "reason": "procfs version/filesystems/self/status/meminfo/uptime reads completed through existing cat path",
        },
        {
            "name": "sysfs-thermal-power-readers",
            "status": "safe-candidate",
            "reason": "sensormap and status already read thermal/power_supply data without writes",
        },
        {
            "name": "filesystem-non-destructive-tempdir",
            "status": "safe-candidate",
            "reason": "v167 bounded fs exerciser under /mnt/sdext/a90/test-fsx passed and avoids raw block access",
        },
    ]
    conditional: list[dict[str, str]] = [
        {
            "name": "network-smoke-kselftest-subset",
            "status": "conditional",
            "reason": "safe only when operator-configured USB NCM is present; current ACM-only state leaves throughput work deferred",
        },
        {
            "name": "static-kselftest-helper-build",
            "status": "unknown",
            "reason": "requires per-test source/dependency audit before cross-compiling static ARM64 helper binaries",
        },
        {
            "name": "pstore-read-only-inventory",
            "status": "conditional",
            "reason": "pstore filesystem is available, but mount/reboot persistence tests require explicit separate plan",
        },
        {
            "name": "tracefs-read-only-inventory",
            "status": "conditional",
            "reason": "tracefs filesystem is available, but active tracing and mounts remain opt-in after baseline stability",
        },
        {
            "name": "cgroup-bpf-read-only-inventory",
            "status": "unknown",
            "reason": "filesystems are listed, but controllers/mounts/userspace dependency coverage needs a smaller follow-up helper",
        },
    ]
    blocked: list[dict[str, str]] = [
        {
            "name": "hotplug-module-tests",
            "status": "blocked",
            "reason": "module insertion/removal and hotplug mutation are outside current recovery envelope",
        },
        {
            "name": "fault-injection",
            "status": "blocked",
            "reason": "fault injection writes can destabilize PID1/kernel; v169 must classify read-only availability first",
        },
        {
            "name": "watchdog-tests",
            "status": "blocked",
            "reason": "opening /dev/watchdog can arm reboot behavior; policy is read-only-no-open",
        },
        {
            "name": "raw-device-mutation",
            "status": "blocked",
            "reason": "raw block, modem, bootloader, EFS, and Android partition mutation is explicitly forbidden",
        },
        {
            "name": "crash-reboot-lkdtm",
            "status": "blocked",
            "reason": "crash/reboot paths need explicit pstore/recovery preconditions and operator approval",
        },
        {
            "name": "active-ftrace-tracing",
            "status": "blocked-by-default",
            "reason": "tracefs active tracing writes are deferred until v169/future opt-in plan",
        },
    ]

    if not has_text(captures, "cat-proc-filesystems", "tracefs"):
        conditional.append({
            "name": "tracefs-dependent-tests",
            "status": "unknown",
            "reason": "tracefs was not confirmed through /proc/filesystems in this run",
        })
    if not has_text(captures, "userland-status", "toybox=ready"):
        conditional.append({
            "name": "toybox-backed-shell-probes",
            "status": "unknown",
            "reason": "toybox readiness was not confirmed by userland status",
        })
    return {
        "safe_candidates": candidates,
        "conditional_or_unknown": conditional,
        "blocked": blocked,
    }


def default_bundle_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "soak" / "kselftest-feasibility" / f"v168-kselftest-{stamp}"


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
        "# A90 v168 Kernel Selftest Feasibility\n\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- expect_version: `{manifest['expect_version']}`\n",
        f"- version_matches: `{manifest['version_matches']}`\n",
        f"- policy: `{manifest['policy']}`\n",
        f"- mutation_performed: `{manifest['mutation_performed']}`\n",
        f"- failed mandatory commands: `{manifest['failed_mandatory_count']}`\n",
        f"- failed optional commands: `{manifest['failed_optional_count']}`\n\n",
        "## Safe Candidates\n\n",
    ]
    for item in manifest["classification"]["safe_candidates"]:
        lines.append(f"- `{item['name']}`: {item['reason']}\n")
    lines.append("\n## Conditional Or Unknown\n\n")
    for item in manifest["classification"]["conditional_or_unknown"]:
        lines.append(f"- `{item['name']}` ({item['status']}): {item['reason']}\n")
    lines.append("\n## Blocked\n\n")
    for item in manifest["classification"]["blocked"]:
        lines.append(f"- `{item['name']}` ({item['status']}): {item['reason']}\n")
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
    started_monotonic = time.monotonic()
    args = parse_args()
    bundle_dir = args.bundle_dir if args.bundle_dir.is_absolute() else REPO_ROOT / args.bundle_dir
    ensure_private_dir(bundle_dir.parent)
    ensure_private_dir(bundle_dir)

    captures: list[CommandCapture] = []
    for name, command, timeout in MANDATORY_COMMANDS:
        captures.append(run_capture(args, bundle_dir, name, command, timeout * args.timeout_scale, True))
    for name, command, timeout in OPTIONAL_COMMANDS:
        captures.append(run_capture(args, bundle_dir, name, command, timeout * args.timeout_scale, False))

    version_capture = next((item for item in captures if item.name == "version"), None)
    version_text = read_capture_text(version_capture) if version_capture else ""
    version_matches = args.expect_version in version_text
    failed_mandatory = [item for item in captures if item.mandatory and not item.ok]
    failed_optional = [item for item in captures if not item.mandatory and not item.ok]
    classification = classify(captures)
    mutation_performed = False
    pass_ok = (
        version_matches
        and not failed_mandatory
        and bool(classification["safe_candidates"])
        and bool(classification["conditional_or_unknown"])
        and bool(classification["blocked"])
        and not mutation_performed
    )

    manifest: dict[str, Any] = {
        "label": "v168 Kernel Selftest Feasibility",
        "created_host_ts": time.time(),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": collect_host_metadata(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": pass_ok,
        "policy": "read-only; no full kselftest/LTP run; no mount; no watchdog open; no fault injection; no raw device mutation",
        "mutation_performed": mutation_performed,
        "failed_mandatory_count": len(failed_mandatory),
        "failed_optional_count": len(failed_optional),
        "classification": classification,
        "commands": [asdict(capture) for capture in captures],
    }
    transport.add_total_phase(
        manifest,
        "kselftest_feasibility_total",
        started_monotonic,
        ok=pass_ok,
    )
    transport.set_residual_state(manifest, {
        "mutation_performed": mutation_performed,
        "failed_mandatory_count": len(failed_mandatory),
        "failed_optional_count": len(failed_optional),
        "cleanup_required": False,
    })
    write_private_text(
        bundle_dir / "kselftest-feasibility-report.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    write_private_text(bundle_dir / "kselftest-feasibility-report.md", render_markdown(manifest))

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
