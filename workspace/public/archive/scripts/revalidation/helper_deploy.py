#!/usr/bin/env python3
"""Host helper for A90 native-init helper inventory/deploy checks.

This v98 tool intentionally avoids downloads and destructive device changes.
It talks to the existing serial bridge through a90ctl, discovers the runtime
root, prints candidate manifest lines, and verifies the device-side helper
inventory command.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"

DEFAULT_HELPERS = (
    ("a90_cpustress", REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_cpustress", "ramdisk-mirror"),
    ("a90sleep", REPO_ROOT / "stage3" / "linux_init" / "a90_sleep", "test-helper"),
    ("a90_usbnet", REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_usbnet", "net-helper"),
    ("a90_tcpctl", REPO_ROOT / "external_tools" / "userland" / "bin" / "a90_tcpctl-aarch64-static", "tcp-control"),
    ("a90_rshell", REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_rshell", "remote-shell"),
    (
        "a90_android_execns_probe",
        REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe",
        "android-exec-namespace-probe",
    ),
    ("busybox", REPO_ROOT / "external_tools" / "userland" / "bin" / "busybox-aarch64-static", "userland"),
    ("toybox", REPO_ROOT / "stage3" / "linux_init" / "toybox", "userland"),
)


def run_a90ctl(args: list[str], timeout: int = 10) -> str:
    command = [sys.executable, str(A90CTL), "--timeout", str(timeout), *args]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout.strip() or f"a90ctl failed rc={result.returncode}")
    return result.stdout


def parse_runtime_root(text: str) -> str:
    match = re.search(r"runtime: backend=\S+ root=(\S+) ", text)
    if not match:
        raise SystemExit("could not parse runtime root from device output")
    return match.group(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_line(root: str, name: str, local_path: Path, role: str) -> str:
    if not local_path.exists():
        return f"# missing-local {name} {local_path}"
    mode = local_path.stat().st_mode & 0o777
    size = local_path.stat().st_size
    digest = sha256_file(local_path)
    return f"{name} {root}/bin/{name} {role} no {digest} {mode:04o} {size}"


def cmd_status(_: argparse.Namespace) -> int:
    print(run_a90ctl(["runtime"]).rstrip())
    print(run_a90ctl(["helpers"]).rstrip())
    return 0


def cmd_manifest(_: argparse.Namespace) -> int:
    runtime = run_a90ctl(["runtime"])
    root = parse_runtime_root(runtime)
    print("# name path role required sha256 mode size")
    for name, local_path, role in DEFAULT_HELPERS:
        print(manifest_line(root, name, local_path, role))
    return 0


def cmd_verify(_: argparse.Namespace) -> int:
    print(run_a90ctl(["helpers", "verify"]).rstrip())
    return 0


def cmd_push(args: argparse.Namespace) -> int:
    local_path = Path(args.local_path)
    if not local_path.exists():
        raise SystemExit(f"local helper not found: {local_path}")
    runtime = run_a90ctl(["runtime"])
    root = parse_runtime_root(runtime)
    target = f"{root}/bin/{args.name}"
    print("operator action required:")
    print(f"  copy {local_path} to device:{target}")
    print("  then update manifest with:")
    print(manifest_line(root, args.name, local_path, args.role))
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    runtime = run_a90ctl(["runtime"])
    root = parse_runtime_root(runtime)
    print("operator action required:")
    print(f"  remove or rename device:{root}/bin/{args.name}")
    print("  remove matching line from helpers.manifest or set required=no")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show runtime and device helper inventory")
    status.set_defaults(func=cmd_status)

    manifest = subparsers.add_parser("manifest", help="print manifest lines for known local helpers")
    manifest.set_defaults(func=cmd_manifest)

    verify = subparsers.add_parser("verify", help="run device-side helper verification")
    verify.set_defaults(func=cmd_verify)

    push = subparsers.add_parser("push", help="print safe deploy instructions for one helper")
    push.add_argument("local_path")
    push.add_argument("name")
    push.add_argument("--role", default="manual")
    push.set_defaults(func=cmd_push)

    rollback = subparsers.add_parser("rollback", help="print rollback instructions for one helper")
    rollback.add_argument("name")
    rollback.set_defaults(func=cmd_rollback)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
