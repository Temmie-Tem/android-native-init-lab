#!/usr/bin/env python3
"""Collect A90 native-init Wi-Fi inventory evidence without enabling Wi-Fi."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"

ADB_READ_ONLY_COMMANDS = [
    "getprop | grep -Ei 'wifi|wlan|qca|cnss' || true",
    "ip link",
    "ls -l /sys/class/net /sys/class/rfkill 2>/dev/null || true",
    "cat /proc/modules 2>/dev/null | grep -Ei 'wlan|wifi|qca|qcacld|cnss|wcnss|ath' || true",
    "find /vendor /odm /product /system -maxdepth 4 "
    "\\( -iname '*wifi*' -o -iname '*wlan*' -o -iname '*qca*' "
    "-o -iname '*cnss*' -o -iname '*wcnss*' \\) 2>/dev/null || true",
    "cmd wifi status 2>/dev/null || true",
]

FORBIDDEN_TOKENS = (
    "svc wifi enable",
    "svc wifi disable",
    "cmd wifi set-wifi-enabled",
    "ip link set wlan0 up",
    "insmod",
    "rmmod",
    "modprobe",
    "> /sys/class/rfkill",
)


def run_command(command: list[str],
                timeout: int,
                cwd: Path = REPO_ROOT) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def run_a90ctl(args: argparse.Namespace, device_args: list[str], timeout: int | None = None) -> tuple[int, str]:
    effective_timeout = timeout if timeout is not None else args.timeout
    command = [
        sys.executable,
        str(A90CTL),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(effective_timeout),
        "--allow-error",
        *device_args,
    ]
    return run_command(command, timeout=effective_timeout + 5)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_section(lines: list[str], title: str, body: str) -> None:
    lines.append(f"[{title}]")
    lines.append(body.rstrip() if body.strip() else "(empty)")
    lines.append("")


def collect_host_metadata(args: argparse.Namespace) -> str:
    lines: list[str] = []
    lines.append(f"repo={REPO_ROOT}")
    rc, text = run_command(["git", "rev-parse", "--short", "HEAD"], timeout=5)
    lines.append(f"git_head={text.strip() if rc == 0 else 'unknown'}")
    rc, text = run_command(["git", "status", "--short"], timeout=5)
    lines.append(f"git_dirty={'yes' if rc == 0 and text.strip() else 'no' if rc == 0 else 'unknown'}")
    if rc == 0 and text.strip():
        lines.append("git_status_short:")
        lines.extend(f"  {line}" for line in text.splitlines())
    if args.boot_image:
        image = Path(args.boot_image)
        if not image.is_absolute():
            image = REPO_ROOT / image
        if image.exists():
            lines.append(f"boot_image={image}")
            lines.append(f"boot_image_sha256={sha256_file(image)}")
        else:
            lines.append(f"boot_image_missing={image}")
    return "\n".join(lines)


def ensure_safe_adb_commands(commands: list[str]) -> None:
    joined = "\n".join(commands)
    for token in FORBIDDEN_TOKENS:
        if token in joined:
            raise RuntimeError(f"unsafe adb inventory command token found: {token}")


def collect_adb_read_only(args: argparse.Namespace, label: str) -> str:
    lines: list[str] = []
    ensure_safe_adb_commands(ADB_READ_ONLY_COMMANDS)
    lines.append(f"label={label}")
    lines.append("policy=read-only; no svc wifi enable; no rfkill write; no module load")
    lines.append("commands:")
    for command in ADB_READ_ONLY_COMMANDS:
        lines.append(f"  adb shell {command}")
    lines.append("")
    for command in ADB_READ_ONLY_COMMANDS:
        rc, text = run_command([args.adb, "shell", command], timeout=args.adb_timeout)
        lines.append(f"$ adb shell {command}")
        lines.append(text.rstrip())
        lines.append(f"rc={rc}")
        lines.append("")
    return "\n".join(lines).rstrip()


def default_output_path() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "wifiinv" / f"a90-wifiinv-{stamp}.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=int, default=30, help="a90ctl command timeout")
    parser.add_argument("--out", type=Path, default=default_output_path(), help="host-side output path")
    parser.add_argument("--boot-image", help="optional boot image path to hash")
    parser.add_argument("--native-only", action="store_true", help="skip optional adb baselines")
    parser.add_argument("--android-adb", action="store_true", help="append Android read-only adb baseline")
    parser.add_argument("--twrp-adb", action="store_true", help="append TWRP read-only adb baseline")
    parser.add_argument("--adb", default="adb", help="adb executable")
    parser.add_argument("--adb-timeout", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lines: list[str] = []
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()

    if args.native_only and (args.android_adb or args.twrp_adb):
        raise SystemExit("--native-only cannot be combined with --android-adb or --twrp-adb")

    lines.append("A90 HOST WIFI INVENTORY")
    lines.append(f"generated={stamp}")
    lines.append("policy=read-only native-first")
    lines.append("")
    append_section(lines, "host", collect_host_metadata(args))

    rc, text = run_a90ctl(args, ["wifiinv", "full"], timeout=max(args.timeout, 45))
    append_section(lines, "native wifiinv full", text + f"\nrc={rc}")

    rc, text = run_a90ctl(args, ["wifiinv", "refresh"], timeout=args.timeout)
    append_section(lines, "native wifiinv refresh", text + f"\nrc={rc}")

    rc, text = run_a90ctl(args, ["wififeas", "refresh"], timeout=args.timeout)
    append_section(lines, "native wififeas refresh", text + f"\nrc={rc}")

    rc, text = run_a90ctl(args, ["diag"], timeout=args.timeout)
    append_section(lines, "native diag summary", text + f"\nrc={rc}")

    if not args.native_only and args.android_adb:
        append_section(lines, "android adb read-only baseline", collect_adb_read_only(args, "android"))
    if not args.native_only and args.twrp_adb:
        append_section(lines, "twrp adb read-only baseline", collect_adb_read_only(args, "twrp"))

    output = args.out
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
