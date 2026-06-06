#!/usr/bin/env python3
"""Run bounded SD storage write/read/hash integrity checks over A90 NCM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import socket
import stat
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90harness.path_safety import (  # noqa: E402
    normalize_device_path,
    require_path_under,
    require_run_child,
    require_safe_component,
    require_safe_raw_arg,
)
from tcpctl_host import (  # noqa: E402
    BridgeRunThread,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_DEVICE_IP,
    DEFAULT_TOYBOX,
    bridge_command,
    device_command,
)


DEFAULT_TEST_ROOT = "/mnt/sdext/a90/test-io"
DEFAULT_TRANSFER_PORT = 18084
DEFAULT_SIZES = "4096,65536,1048576"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass
class FileResult:
    name: str
    size: int
    sha256: str
    device_path: str
    transfer_ok: bool
    sha_ok: bool
    rename_ok: bool
    fsync_ok: bool
    unlink_ok: bool


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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def deterministic_bytes(size: int, seed: str) -> bytes:
    output = bytearray()
    counter = 0
    seed_bytes = seed.encode("utf-8")
    while len(output) < size:
        digest = hashlib.sha256(seed_bytes + counter.to_bytes(8, "big")).digest()
        output.extend(digest)
        counter += 1
    return bytes(output[:size])


def parse_sizes(text: str) -> list[int]:
    sizes: list[int] = []
    for item in text.split(","):
        value = item.strip()
        if not value:
            continue
        multiplier = 1
        suffix = value[-1].lower()
        if suffix == "k":
            multiplier = 1024
            value = value[:-1]
        elif suffix == "m":
            multiplier = 1024 * 1024
            value = value[:-1]
        size = int(value, 10) * multiplier
        if size <= 0:
            raise ValueError(f"invalid size: {item}")
        sizes.append(size)
    if not sizes:
        raise ValueError("at least one size is required")
    return sizes


def validate_device_test_root(path: str) -> str:
    normalized = require_path_under(path, "/mnt/sdext/a90", "test root")
    basename = posixpath.basename(normalized)
    if not basename.startswith("test-"):
        raise RuntimeError(f"refusing test root outside /mnt/sdext/a90/test-*: {path}")
    return normalized


def validate_device_path(path: str, root: str) -> str:
    return require_path_under(path, root, "device path")


def raw_command(*args: str) -> str:
    return " ".join(require_safe_raw_arg(arg, "raw command argument") for arg in args)


def validate_common_args(args: argparse.Namespace) -> None:
    args.test_root = validate_device_test_root(args.test_root)
    args.run_id = require_safe_component(args.run_id, "run id")
    args.toybox = require_safe_raw_arg(normalize_device_path(args.toybox, "toybox path"), "toybox path")
    if not 1 <= args.transfer_port <= 65535:
        raise RuntimeError(f"invalid transfer port: {args.transfer_port}")


def run_device(args: argparse.Namespace,
               command: str,
               *,
               timeout: float | None = None,
               allow_error: bool = False) -> str:
    return device_command(args, command, timeout=timeout, allow_error=allow_error)


def mkdir_chain(args: argparse.Namespace, path: str) -> None:
    path = validate_device_path(path, args.test_root)
    parts = [part for part in path.split("/") if part]
    current = ""
    for part in parts:
        current += "/" + part
        if current in {"/mnt", "/mnt/sdext", "/mnt/sdext/a90"}:
            continue
        run_device(args, raw_command("mkdir", current), timeout=args.bridge_timeout, allow_error=True)


def transfer_file(args: argparse.Namespace, local_path: Path, device_path: str) -> str:
    tmp_path = f"{device_path}.tmp.{os.getpid()}.{int(time.time())}"
    device_path = validate_device_path(device_path, args.test_root)
    tmp_path = validate_device_path(tmp_path, args.test_root)
    receive_command = raw_command(
        "run",
        args.toybox,
        "netcat",
        "-l",
        "-p",
        str(args.transfer_port),
        args.toybox,
        "dd",
        f"of={tmp_path}",
        "bs=4096",
    )
    cleanup_command = raw_command("run", args.toybox, "rm", "-f", tmp_path)

    run_device(args, cleanup_command, timeout=args.bridge_timeout, allow_error=True)
    runner = BridgeRunThread(args, receive_command, echo=args.verbose)
    runner.start()
    time.sleep(args.transfer_delay)
    try:
        with socket.create_connection((args.device_ip, args.transfer_port), timeout=args.connect_timeout) as sock:
            with local_path.open("rb") as file_obj:
                for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                    sock.sendall(chunk)
            sock.shutdown(socket.SHUT_WR)
        runner.join(args.transfer_timeout)
        if runner.is_alive():
            raise RuntimeError(f"device transfer did not finish for {device_path}")
        if runner.error is not None:
            raise RuntimeError(f"bridge transfer failed: {runner.error}")
        text = runner.text()
        if "[done] run" not in text:
            raise RuntimeError(f"device transfer did not report done:\n{text}")
        run_device(args, raw_command("run", args.toybox, "mv", "-f", tmp_path, device_path), timeout=args.bridge_timeout)
        return text
    except Exception:
        run_device(args, cleanup_command, timeout=args.bridge_timeout, allow_error=True)
        raise


def device_sha256(args: argparse.Namespace, path: str) -> str:
    path = validate_device_path(path, args.test_root)
    text = run_device(args, raw_command("run", args.toybox, "sha256sum", path), timeout=args.bridge_timeout)
    for word in text.split():
        if len(word) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in word):
            return word.lower()
    raise RuntimeError(f"could not parse sha256sum for {path}:\n{text}")


def run_one_file(args: argparse.Namespace,
                 local_dir: Path,
                 index: int,
                 size: int) -> FileResult:
    name = f"file-{index:02d}-{size}.bin"
    local_path = local_dir / name
    device_path = validate_device_path(posixpath.join(args.test_root, args.run_id, name), args.test_root)
    renamed_path = device_path + ".renamed"
    renamed_path = validate_device_path(renamed_path, args.test_root)
    data = deterministic_bytes(size, f"{args.run_id}:{index}:{size}")
    digest = sha256_bytes(data)
    write_private_bytes(local_path, data)

    transfer_file(args, local_path, device_path)
    first_hash = device_sha256(args, device_path)
    sha_ok = first_hash == digest
    run_device(args, raw_command("run", args.toybox, "mv", "-f", device_path, renamed_path), timeout=args.bridge_timeout)
    run_device(args, raw_command("run", args.toybox, "mv", "-f", renamed_path, device_path), timeout=args.bridge_timeout)
    second_hash = device_sha256(args, device_path)
    rename_ok = second_hash == digest
    run_device(args, "sync", timeout=args.bridge_timeout)
    fsync_ok = device_sha256(args, device_path) == digest

    unlink_probe = device_path + ".unlink-probe"
    unlink_probe = validate_device_path(unlink_probe, args.test_root)
    transfer_file(args, local_path, unlink_probe)
    run_device(args, raw_command("run", args.toybox, "rm", "-f", unlink_probe), timeout=args.bridge_timeout)
    stat_text = run_device(args, raw_command("stat", unlink_probe), timeout=args.bridge_timeout, allow_error=True)
    unlink_ok = "No such file" in stat_text or "[err]" in stat_text or "ENOENT" in stat_text

    return FileResult(
        name=name,
        size=size,
        sha256=digest,
        device_path=device_path,
        transfer_ok=True,
        sha_ok=sha_ok,
        rename_ok=rename_ok,
        fsync_ok=fsync_ok,
        unlink_ok=unlink_ok,
    )


def command_run(args: argparse.Namespace) -> int:
    validate_common_args(args)
    sizes = parse_sizes(args.sizes)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    host_dir = Path(args.host_dir) / args.run_id
    local_dir = host_dir / "files"
    ensure_private_dir(local_dir)

    device_run_root = require_run_child(args.test_root, args.run_id)
    validate_device_path(posixpath.join(device_run_root, "probe"), args.test_root)
    mkdir_chain(args, device_run_root)

    results: list[FileResult] = []
    started = time.monotonic()
    for index, size in enumerate(sizes, start=1):
        results.append(run_one_file(args, local_dir, index, size))
    elapsed = time.monotonic() - started
    pass_ok = all(
        item.transfer_ok and item.sha_ok and item.rename_ok and item.fsync_ok and item.unlink_ok
        for item in results
    )
    payload: dict[str, Any] = {
        "pass": pass_ok,
        "run_id": args.run_id,
        "test_root": args.test_root,
        "device_run_root": device_run_root,
        "duration_sec": elapsed,
        "sizes": sizes,
        "results": [asdict(item) for item in results],
    }
    lines = [
        "# A90 Storage I/O Test Report\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- run_id: `{args.run_id}`\n",
        f"- test_root: `{args.test_root}`\n",
        f"- duration_sec: `{elapsed:.3f}`\n",
        "\n## Files\n\n",
        "| File | Size | SHA | Transfer | Read Hash | Rename | Sync/Rehash | Unlink |\n",
        "|---|---:|---|---|---|---|---|---|\n",
    ]
    for item in results:
        lines.append(
            f"| `{item.name}` | `{item.size}` | `{item.sha256}` | "
            f"`{item.transfer_ok}` | `{item.sha_ok}` | `{item.rename_ok}` | "
            f"`{item.fsync_ok}` | `{item.unlink_ok}` |\n"
        )
    write_private_text(out_json, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_private_text(out_md, "".join(lines))
    print(f"{'PASS' if pass_ok else 'FAIL'} files={len(results)} duration={elapsed:.3f}s root={device_run_root}")
    print(out_md)
    print(out_json)
    return 0 if pass_ok else 1


def command_clean(args: argparse.Namespace) -> int:
    validate_common_args(args)
    target = require_run_child(args.test_root, args.run_id)
    validate_device_path(posixpath.join(target.rstrip("/"), "probe"), args.test_root)
    text = run_device(args, raw_command("run", args.toybox, "rm", "-rf", target), timeout=args.bridge_timeout, allow_error=True)
    print(text, end="" if text.endswith("\n") else "\n")
    print(f"cleaned {target}")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--test-root", default=DEFAULT_TEST_ROOT)
    parser.add_argument("--run-id", default=f"v161-{int(time.time())}")
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--device-protocol", choices=("auto", "cmdv1", "raw"), default="auto")
    parser.add_argument("--busy-retries", type=int, default=3)
    parser.add_argument("--busy-retry-sleep", type=float, default=3.0)
    parser.add_argument("--menu-hide-sleep", type=float, default=3.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--transfer-port", type=int, default=DEFAULT_TRANSFER_PORT)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--verbose", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run bounded write/read/hash test")
    run_parser.add_argument("--sizes", default=DEFAULT_SIZES)
    run_parser.add_argument("--host-dir", default="tmp/soak/storage-iotest")
    run_parser.add_argument("--out-md", default="tmp/soak/storage-iotest-report.md")
    run_parser.add_argument("--out-json", default="tmp/soak/storage-iotest-report.json")
    run_parser.set_defaults(func=command_run)

    clean_parser = subparsers.add_parser("clean", help="remove one test run directory")
    clean_parser.set_defaults(func=command_clean)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
