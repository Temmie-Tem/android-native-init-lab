#!/usr/bin/env python3
"""Build a PASS/FAIL report from A90 NCM/tcpctl stability evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class TcpctlSummary:
    duration_sec: float | None
    cycles: int | None
    tcp_ping_pass: int | None
    status_pass: int | None
    run_pass: int | None
    host_ping_pass: int | None
    failures: int | None
    tcp_ping_pass_lines: int
    status_pass_lines: int
    run_pass_lines: int
    host_ping_pass_lines: int
    fail_lines: int


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
        with os.fdopen(fd, "w", encoding="utf-8") as file_obj:
            fd = -1
            file_obj.write(text)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tcpctl-soak", required=True, help="tcpctl_host.py soak transcript")
    parser.add_argument("--ncm-setup", help="optional ncm_host_setup.py setup transcript")
    parser.add_argument("--longsoak-report-json", help="optional native_long_soak_report.py JSON")
    parser.add_argument("--expect-version", help="expected native init version banner in bridge-version output")
    parser.add_argument("--expect-ready", default="a90_tcpctl v1 ready")
    parser.add_argument("--min-duration", type=float, default=0.0)
    parser.add_argument("--min-cycles", type=int, default=1)
    parser.add_argument("--out-md", default="tmp/soak/ncm-tcp-stability-report.md")
    parser.add_argument("--out-json", default="tmp/soak/ncm-tcp-stability-report.json")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_int(text: str, label: str) -> int | None:
    match = re.search(rf"^{re.escape(label)}:\s*(\d+)\s*$", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def extract_float(text: str, label: str, suffix: str = "") -> float | None:
    match = re.search(rf"^{re.escape(label)}:\s*([0-9]+(?:\.[0-9]+)?)\s*{re.escape(suffix)}\s*$", text, re.MULTILINE)
    return float(match.group(1)) if match else None


def parse_tcpctl_summary(text: str) -> TcpctlSummary:
    return TcpctlSummary(
        duration_sec=extract_float(text, "duration", "s"),
        cycles=extract_int(text, "cycles"),
        tcp_ping_pass=extract_int(text, "tcp ping pass"),
        status_pass=extract_int(text, "status pass"),
        run_pass=extract_int(text, "run pass"),
        host_ping_pass=extract_int(text, "host ping pass"),
        failures=extract_int(text, "failures"),
        tcp_ping_pass_lines=len(re.findall(r"^tcp ping: PASS$", text, re.MULTILINE)),
        status_pass_lines=len(re.findall(r"^status: PASS", text, re.MULTILINE)),
        run_pass_lines=len(re.findall(r"^run uptime: PASS$", text, re.MULTILINE)),
        host_ping_pass_lines=len(re.findall(r"^host ping x\d+: PASS$", text, re.MULTILINE)),
        fail_lines=len(re.findall(r": FAIL(?:\s|$)", text)),
    )


def tcpctl_auth_required(text: str) -> bool:
    return bool(re.search(r"\bauth=required\b", text))


def tcpctl_auth_none(text: str) -> bool:
    return bool(re.search(r"\bauth=none\b", text))


def tcpctl_authenticated_flow(text: str) -> bool:
    return "OK authenticated" in text


def add_check(checks: list[Check], name: str, ok: bool, detail: str) -> None:
    checks.append(Check(name, ok, detail))


def validate_tcpctl(args: argparse.Namespace, text: str, summary: TcpctlSummary, checks: list[Check]) -> None:
    add_check(checks, "tcpctl ready banner", args.expect_ready in text, args.expect_ready)
    add_check(checks, "summary present", "--- summary ---" in text, "tcpctl_host.py soak summary marker")
    add_check(checks, "shutdown marker", "--- shutdown ---" in text, "shutdown section present")
    add_check(checks, "serial run done", "[done] run" in text, "serial run reports [done] run")
    add_check(checks, "final ncm ping", "0% packet loss" in text, "final ping reports zero packet loss")
    add_check(checks, "tcpctl auth required", tcpctl_auth_required(text), "transcript contains auth=required")
    add_check(checks, "tcpctl authenticated flow", tcpctl_authenticated_flow(text), "transcript contains OK authenticated")
    add_check(checks, "tcpctl no no-auth marker", not tcpctl_auth_none(text), "transcript must not contain auth=none")
    if args.expect_version:
        add_check(checks, "expected native version", args.expect_version in text, args.expect_version)

    add_check(
        checks,
        "duration threshold",
        summary.duration_sec is not None and summary.duration_sec >= args.min_duration,
        f"duration={summary.duration_sec} min={args.min_duration}",
    )
    add_check(
        checks,
        "cycle threshold",
        summary.cycles is not None and summary.cycles >= args.min_cycles,
        f"cycles={summary.cycles} min={args.min_cycles}",
    )
    add_check(checks, "failure count zero", summary.failures == 0, f"failures={summary.failures}")
    add_check(checks, "no fail lines", summary.fail_lines == 0, f"fail_lines={summary.fail_lines}")

    if summary.cycles is not None:
        add_check(
            checks,
            "tcp ping count",
            summary.tcp_ping_pass == summary.cycles == summary.tcp_ping_pass_lines,
            f"summary={summary.tcp_ping_pass} lines={summary.tcp_ping_pass_lines} cycles={summary.cycles}",
        )
        add_check(
            checks,
            "host ping count",
            summary.host_ping_pass == summary.host_ping_pass_lines and summary.host_ping_pass_lines > 0,
            f"summary={summary.host_ping_pass} lines={summary.host_ping_pass_lines}",
        )
        add_check(
            checks,
            "status count",
            summary.status_pass == summary.status_pass_lines and summary.status_pass_lines > 0,
            f"summary={summary.status_pass} lines={summary.status_pass_lines}",
        )
        add_check(
            checks,
            "run count",
            summary.run_pass == summary.run_pass_lines and summary.run_pass_lines > 0,
            f"summary={summary.run_pass} lines={summary.run_pass_lines}",
        )


def validate_ncm_setup(path: Path | None, checks: list[Check]) -> dict[str, Any] | None:
    if path is None:
        add_check(checks, "ncm setup transcript", True, "not provided")
        return None

    text = read_text(path)
    saw_complete = "NCM setup complete" in text
    saw_ifname = "ncm.ifname: ncm0" in text
    saw_ifconfig = "ifconfig ncm0" in text and "rc=0" in text
    saw_zero_loss = "0% packet loss" in text
    setup_ok = saw_complete or (saw_ifname and saw_ifconfig and saw_zero_loss)

    add_check(
        checks,
        "ncm setup complete",
        setup_ok,
        "complete marker or ncm0+ifconfig+zero-loss ping",
    )
    add_check(checks, "ncm setup ping", saw_zero_loss, "setup ping reports zero packet loss")
    return {
        "path": str(path),
        "setup_complete": saw_complete,
        "ncm0_reported": saw_ifname,
        "ifconfig_ok": saw_ifconfig,
        "zero_packet_loss": saw_zero_loss,
    }


def validate_longsoak(path: Path | None, checks: list[Check]) -> dict[str, Any] | None:
    if path is None:
        add_check(checks, "longsoak trend report", True, "not provided")
        return None

    data = json.loads(read_text(path))
    add_check(checks, "longsoak pass", bool(data.get("pass")), str(path))
    add_check(checks, "longsoak host failures", int(data.get("host_failures", -1)) == 0, f"host_failures={data.get('host_failures')}")
    add_check(checks, "longsoak device samples", int(data.get("device_samples", 0)) > 0, f"device_samples={data.get('device_samples')}")
    add_check(checks, "longsoak sequence", bool(data.get("device_seq_contiguous")), f"seq={data.get('device_seq_contiguous')}")
    add_check(checks, "longsoak uptime monotonic", bool(data.get("device_uptime_monotonic")), f"uptime={data.get('device_uptime_monotonic')}")
    return data


def build_markdown(args: argparse.Namespace,
                   pass_ok: bool,
                   summary: TcpctlSummary,
                   checks: list[Check],
                   ncm_setup: dict[str, Any] | None,
                   longsoak: dict[str, Any] | None) -> str:
    lines = [
        "# A90 NCM/TCP Stability Report\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- tcpctl transcript: `{args.tcpctl_soak}`\n",
        f"- ncm setup transcript: `{args.ncm_setup or '-'}`\n",
        f"- longsoak report json: `{args.longsoak_report_json or '-'}`\n",
        f"- expect_version: `{args.expect_version or '-'}`\n",
        "\n## Tcpctl Summary\n\n",
        f"- duration_sec: `{summary.duration_sec}`\n",
        f"- cycles: `{summary.cycles}`\n",
        f"- tcp_ping_pass: `{summary.tcp_ping_pass}`\n",
        f"- status_pass: `{summary.status_pass}`\n",
        f"- run_pass: `{summary.run_pass}`\n",
        f"- host_ping_pass: `{summary.host_ping_pass}`\n",
        f"- failures: `{summary.failures}`\n",
        "\n## Checks\n\n",
    ]
    for check in checks:
        lines.append(f"- {'PASS' if check.ok else 'FAIL'} `{check.name}` — {check.detail}\n")
    if ncm_setup:
        lines.extend(["\n## NCM Setup\n\n", "```json\n", json.dumps(ncm_setup, ensure_ascii=False, indent=2, sort_keys=True), "\n```\n"])
    if longsoak:
        selected = {
            "pass": longsoak.get("pass"),
            "host_failures": longsoak.get("host_failures"),
            "device_samples": longsoak.get("device_samples"),
            "device_seq_contiguous": longsoak.get("device_seq_contiguous"),
            "device_uptime_monotonic": longsoak.get("device_uptime_monotonic"),
        }
        lines.extend(["\n## Longsoak\n\n", "```json\n", json.dumps(selected, ensure_ascii=False, indent=2, sort_keys=True), "\n```\n"])
    return "".join(lines)


def main() -> int:
    args = parse_args()
    tcpctl_path = Path(args.tcpctl_soak)
    ncm_path = Path(args.ncm_setup) if args.ncm_setup else None
    longsoak_path = Path(args.longsoak_report_json) if args.longsoak_report_json else None
    out_md = Path(args.out_md)
    out_json = Path(args.out_json)

    tcpctl_text = read_text(tcpctl_path)
    summary = parse_tcpctl_summary(tcpctl_text)
    checks: list[Check] = []
    validate_tcpctl(args, tcpctl_text, summary, checks)
    ncm_setup = validate_ncm_setup(ncm_path, checks)
    longsoak = validate_longsoak(longsoak_path, checks)
    pass_ok = all(check.ok for check in checks)

    payload = {
        "pass": pass_ok,
        "tcpctl_soak": str(tcpctl_path),
        "ncm_setup": str(ncm_path) if ncm_path else None,
        "longsoak_report_json": str(longsoak_path) if longsoak_path else None,
        "summary": asdict(summary),
        "checks": [asdict(check) for check in checks],
        "ncm_setup_summary": ncm_setup,
        "longsoak_summary": longsoak,
    }
    write_private_text(out_json, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_private_text(out_md, build_markdown(args, pass_ok, summary, checks, ncm_setup, longsoak))

    print(f"{'PASS' if pass_ok else 'FAIL'} tcpctl={tcpctl_path} cycles={summary.cycles} failures={summary.failures}")
    print(out_md)
    print(out_json)
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
