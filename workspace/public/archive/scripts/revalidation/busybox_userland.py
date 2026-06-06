#!/usr/bin/env python3
"""Host helper for v99 BusyBox/toybox userland evaluation."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
DEFAULT_BUSYBOX = REPO_ROOT / "external_tools" / "userland" / "bin" / "busybox-aarch64-static"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def run_a90ctl(args: list[str], timeout: int = 30) -> str:
    result = run([sys.executable, str(A90CTL), "--timeout", str(timeout), *args], timeout=timeout + 5)
    if result.returncode != 0:
        raise SystemExit(result.stdout.strip() or f"a90ctl failed rc={result.returncode}")
    return result.stdout


def cmd_local_info(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"busybox: missing local artifact {path}")
        return 1
    print(f"path: {path}")
    print(f"size: {path.stat().st_size}")
    print(f"sha256: {sha256_file(path)}")
    for command in (["file", str(path)], ["aarch64-linux-gnu-readelf", "-d", str(path)]):
        result = run(command)
        print(result.stdout.rstrip())
        if result.returncode != 0:
            return result.returncode
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    print(run_a90ctl(["runtime"]).rstrip())
    print(run_a90ctl(["helpers"]).rstrip())
    print(run_a90ctl(["userland"]).rstrip())
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"# missing-local busybox {path}")
        return 1
    runtime = run_a90ctl(["runtime"])
    root = "-"
    for token in runtime.split():
        if token.startswith("root="):
            root = token.removeprefix("root=")
            break
    mode = path.stat().st_mode & 0o777
    print("# name path role required sha256 mode size")
    print(f"busybox {root}/bin/busybox userland no {sha256_file(path)} {mode:04o} {path.stat().st_size}")
    return 0


def cmd_verify(_: argparse.Namespace) -> int:
    print(run_a90ctl(["helpers", "verify", "busybox"]).rstrip())
    print(run_a90ctl(["userland", "verbose"]).rstrip())
    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    target = args.target
    print(run_a90ctl(["userland", "test", target], timeout=args.timeout).rstrip())
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    rc = 0
    for target in ("busybox", "toybox"):
        try:
            print(run_a90ctl(["userland", "test", target], timeout=args.timeout).rstrip())
        except SystemExit as exc:
            rc = 1
            print(exc)
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--busybox", default=str(DEFAULT_BUSYBOX), help="local static BusyBox path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    local_info = subparsers.add_parser("local-info", help="inspect local BusyBox artifact")
    local_info.set_defaults(func=lambda args: cmd_local_info(argparse.Namespace(path=args.busybox)))

    status = subparsers.add_parser("status", help="show device runtime/helper/userland status")
    status.set_defaults(func=cmd_status)

    manifest = subparsers.add_parser("manifest", help="print BusyBox manifest line")
    manifest.set_defaults(func=lambda args: cmd_manifest(argparse.Namespace(path=args.busybox)))

    verify = subparsers.add_parser("verify", help="verify device busybox inventory")
    verify.set_defaults(func=cmd_verify)

    smoke = subparsers.add_parser("smoke", help="run device-side userland smoke")
    smoke.add_argument("target", nargs="?", default="busybox", choices=("busybox", "toybox", "all"))
    smoke.add_argument("--timeout", type=int, default=90)
    smoke.set_defaults(func=cmd_smoke)

    compare = subparsers.add_parser("compare-toybox", help="run BusyBox and toybox smoke tests")
    compare.add_argument("--timeout", type=int, default=120)
    compare.set_defaults(func=cmd_compare)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
