#!/usr/bin/env python3
"""Validate A90 native-init USB ACM/NCM software recovery cycles."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import (  # noqa: E402
    DEFAULT_HOST,
    DEFAULT_PORT,
    bridge_exchange,
    encode_cmdv1_line,
    run_cmdv1_command,
)


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class RecoveryStep:
    label: str
    command: list[str]
    raw_ok: bool
    raw_error: str
    raw_output_file: str
    recovered: bool
    recovery_sec: float | None
    verify_rc: int | None
    verify_status: str


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
        with os.fdopen(fd, "wb") as file_obj:
            fd = -1
            file_obj.write(data)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def write_private_text(path: Path, text: str) -> None:
    write_private_bytes(path, text.encode("utf-8"))


def add_check(checks: list[Check], name: str, ok: bool, detail: str) -> None:
    checks.append(Check(name=name, ok=ok, detail=detail))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--recovery-timeout", type=float, default=30.0)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--usbnet-helper", default="/cache/bin/a90_usbnet")
    parser.add_argument("--run-id", default=f"v165-{int(time.time())}")
    parser.add_argument("--out-dir", default="tmp/soak/usb-recovery")
    return parser.parse_args()


def send_raw_cmdv1(args: argparse.Namespace,
                   command: list[str],
                   label: str,
                   out_dir: Path) -> tuple[bool, str, str]:
    line = encode_cmdv1_line(command)
    output_file = out_dir / "commands" / f"{label}.txt"
    try:
        text = bridge_exchange(
            args.host,
            args.port,
            line,
            args.timeout,
            markers=(b"A90P1 END ", b"serial may reconnect", b"rebinding", b"[done]", b"[err]"),
            require_prompt_after_end=False,
        )
        write_private_text(output_file, text)
        return True, "", str(output_file)
    except Exception as exc:  # noqa: BLE001 - disconnect is expected for some USB commands
        write_private_text(output_file, f"{type(exc).__name__}: {exc}\n")
        return False, str(exc), str(output_file)


def wait_recovered(args: argparse.Namespace, out_dir: Path, label: str) -> tuple[bool, float | None, int | None, str]:
    deadline = time.monotonic() + args.recovery_timeout
    started = time.monotonic()
    last_error = ""
    while time.monotonic() < deadline:
        try:
            result = run_cmdv1_command(args.host, args.port, args.timeout, ["version"])
            write_private_text(out_dir / "commands" / f"{label}-version.txt", result.text)
            if result.rc == 0 and result.status == "ok":
                return True, time.monotonic() - started, result.rc, result.status
            last_error = f"rc={result.rc} status={result.status}"
        except Exception as exc:  # noqa: BLE001 - retry during USB recovery
            last_error = str(exc)
        time.sleep(args.poll_interval)
    write_private_text(out_dir / "commands" / f"{label}-recover-timeout.txt", last_error + "\n")
    return False, None, None, "timeout"


def run_step(args: argparse.Namespace,
             label: str,
             command: list[str],
             out_dir: Path) -> RecoveryStep:
    raw_ok, raw_error, output_file = send_raw_cmdv1(args, command, label, out_dir)
    recovered, recovery_sec, verify_rc, verify_status = wait_recovered(args, out_dir, label)
    return RecoveryStep(
        label=label,
        command=command,
        raw_ok=raw_ok,
        raw_error=raw_error,
        raw_output_file=output_file,
        recovered=recovered,
        recovery_sec=recovery_sec,
        verify_rc=verify_rc,
        verify_status=verify_status,
    )


def cmdv1_text(args: argparse.Namespace, out_dir: Path, label: str, command: list[str]) -> tuple[bool, str, int | None, str]:
    output_file = out_dir / "commands" / f"{label}.txt"
    try:
        result = run_cmdv1_command(args.host, args.port, args.timeout, command)
        write_private_text(output_file, result.text)
        return result.rc == 0 and result.status == "ok", result.text, result.rc, result.status
    except Exception as exc:  # noqa: BLE001
        write_private_text(output_file, f"{type(exc).__name__}: {exc}\n")
        return False, str(exc), None, "exception"


def recovery_times(steps: list[RecoveryStep]) -> list[float]:
    return [step.recovery_sec for step in steps if step.recovery_sec is not None]


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir) / args.run_id
    ensure_private_dir(out_dir)
    checks: list[Check] = []
    started = time.monotonic()

    baseline_ok, baseline_text, baseline_rc, baseline_status = cmdv1_text(args, out_dir, "baseline-status", ["status"])
    add_check(checks, "baseline status", baseline_ok, f"rc={baseline_rc} status={baseline_status}")

    steps: list[RecoveryStep] = []
    for index in range(1, args.cycles + 1):
        steps.append(run_step(args, f"usbacmreset-{index:02d}", ["usbacmreset"], out_dir))

    steps.append(run_step(args, "usbnet-ncm", ["run", args.usbnet_helper, "ncm"], out_dir))
    ncm_ok, ncm_text, ncm_rc, ncm_status = cmdv1_text(args, out_dir, "usbnet-status-ncm", ["run", args.usbnet_helper, "status"])
    ncm_present = "ncm.ifname: ncm0" in ncm_text
    add_check(checks, "ncm device function present", ncm_ok and ncm_present, f"rc={ncm_rc} status={ncm_status} present={ncm_present}")

    steps.append(run_step(args, "usbnet-off", ["run", args.usbnet_helper, "off"], out_dir))
    final_status_ok, final_status_text, final_status_rc, final_status = cmdv1_text(args, out_dir, "final-netservice-status", ["netservice", "status"])
    final_acm_only = "ncm0=absent" in final_status_text or "ncm0=missing" in final_status_text or "ncm0=stopped" in final_status_text
    final_version_ok, final_version_text, final_version_rc, final_version_status = cmdv1_text(args, out_dir, "final-version", ["version"])
    final_selftest_ok, _, final_selftest_rc, final_selftest_status = cmdv1_text(args, out_dir, "final-selftest", ["selftest", "verbose"])

    recovered_count = sum(1 for step in steps if step.recovered)
    times = recovery_times(steps)
    max_recovery = max(times) if times else None
    add_check(checks, "recovery steps", recovered_count == len(steps), f"recovered={recovered_count} total={len(steps)}")
    add_check(checks, "final acm-only", final_status_ok and final_acm_only, f"rc={final_status_rc} status={final_status} acm_only={final_acm_only}")
    add_check(checks, "final version", final_version_ok, f"rc={final_version_rc} status={final_version_status}")
    add_check(checks, "final selftest", final_selftest_ok, f"rc={final_selftest_rc} status={final_selftest_status}")

    elapsed = time.monotonic() - started
    pass_ok = all(item.ok for item in checks)
    report: dict[str, Any] = {
        "pass": pass_ok,
        "run_id": args.run_id,
        "duration_sec": elapsed,
        "cycles": args.cycles,
        "steps": [asdict(step) for step in steps],
        "recovered_count": recovered_count,
        "max_recovery_sec": max_recovery,
        "baseline_status_contains_version": "A90 Linux init" in baseline_text,
        "ncm_present_after_ncm_step": ncm_present,
        "final_acm_only": final_acm_only,
        "checks": [asdict(item) for item in checks],
    }
    lines = [
        "# A90 USB Recovery Report\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- run_id: `{args.run_id}`\n",
        f"- duration_sec: `{elapsed:.3f}`\n",
        f"- cycles: `{args.cycles}`\n",
        f"- recovered: `{recovered_count}/{len(steps)}`\n",
        f"- max_recovery_sec: `{max_recovery}`\n",
        f"- ncm_present_after_ncm_step: `{ncm_present}`\n",
        f"- final_acm_only: `{final_acm_only}`\n\n",
        "## Steps\n\n",
        "| Step | Command | Recovered | Recovery sec | Verify |\n",
        "|---|---|---|---:|---|\n",
    ]
    for step in steps:
        lines.append(
            f"| `{step.label}` | `{' '.join(step.command)}` | `{step.recovered}` | "
            f"`{step.recovery_sec}` | `{step.verify_status}/{step.verify_rc}` |\n"
        )
    lines.extend([
        "\n## Checks\n\n",
        "| Check | Result | Detail |\n",
        "|---|---|---|\n",
    ])
    for item in checks:
        lines.append(f"| `{item.name}` | `{'PASS' if item.ok else 'FAIL'}` | `{item.detail}` |\n")
    write_private_text(out_dir / "usb-recovery-report.json", json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "usb-recovery-report.md", "".join(lines))
    print(f"{'PASS' if pass_ok else 'FAIL'} run_id={args.run_id} duration={elapsed:.3f}s")
    print(out_dir / "usb-recovery-report.md")
    print(out_dir / "usb-recovery-report.json")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
