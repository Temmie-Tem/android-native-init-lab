#!/usr/bin/env python3
"""Run a bounded deterministic filesystem exerciser under /mnt/sdext/a90/test-fsx."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import random
import re
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import run_cmdv1_command  # noqa: E402
from a90harness.path_safety import (  # noqa: E402
    normalize_device_path,
    require_path_under,
    require_run_child,
    require_safe_component,
    require_safe_raw_arg,
)
from tcpctl_host import DEFAULT_BRIDGE_HOST, DEFAULT_BRIDGE_PORT, DEFAULT_TOYBOX  # noqa: E402


DEFAULT_TEST_ROOT = "/mnt/sdext/a90/test-fsx"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
SIZE_CHOICES = (0, 1024, 2048, 4096, 8192, 16384, 32768)
STAT_SIZE_RE = re.compile(r"\bsize=([0-9]+)\b")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class OperationRecord:
    index: int
    op: str
    path: str
    aux_path: str | None
    size: int | None
    ok: bool
    detail: str


@dataclass
class FileState:
    path: str
    size: int


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--test-root", default=DEFAULT_TEST_ROOT)
    parser.add_argument("--run-id", default=f"v167-{int(time.time())}")
    parser.add_argument("--out-dir", default="tmp/soak/fs-exerciser")
    parser.add_argument("--ops", type=int, default=64)
    parser.add_argument("--seed", default="v167-fsx-seed")
    parser.add_argument("--max-files", type=int, default=8)
    parser.add_argument("--keep-device-files", action="store_true")
    return parser.parse_args()


def validate_test_root(path: str) -> str:
    normalized = normalize_device_path(path, "test root")
    if normalized != DEFAULT_TEST_ROOT:
        raise RuntimeError(f"refusing test root outside {DEFAULT_TEST_ROOT}: {path}")
    return normalized


def validate_device_path(path: str, root: str) -> str:
    return require_path_under(path, root, "device path")


def validate_common_args(args: argparse.Namespace) -> None:
    args.test_root = validate_test_root(args.test_root)
    args.run_id = require_safe_component(args.run_id, "run id")
    args.run_root = require_run_child(args.test_root, args.run_id)
    args.toybox = require_safe_raw_arg(normalize_device_path(args.toybox, "toybox path"), "toybox path")


def run_cmd(args: argparse.Namespace,
            command: list[str],
            *,
            allow_error: bool = False,
            retry_unsafe: bool = False,
            timeout: float | None = None) -> tuple[bool, str, int | None, str]:
    try:
        result = run_cmdv1_command(
            args.bridge_host,
            args.bridge_port,
            args.bridge_timeout if timeout is None else timeout,
            command,
            retry_unsafe=retry_unsafe,
        )
        ok = result.rc == 0 and result.status == "ok"
        if not ok and not allow_error:
            return False, result.text, result.rc, result.status
        return ok, result.text, result.rc, result.status
    except Exception as exc:  # noqa: BLE001
        if allow_error:
            return False, f"{type(exc).__name__}: {exc}", None, "exception"
        return False, f"{type(exc).__name__}: {exc}", None, "exception"


def mkdir_chain(args: argparse.Namespace, path: str) -> None:
    path = validate_device_path(path, args.test_root)
    parts = [part for part in path.split("/") if part]
    current = ""
    for part in parts:
        current += "/" + part
        if current in {"/mnt", "/mnt/sdext", "/mnt/sdext/a90"}:
            continue
        run_cmd(args, ["mkdir", current], allow_error=True)


def zero_sha256(size: int) -> str:
    digest = hashlib.sha256()
    chunk = b"\0" * 4096
    remaining = size
    while remaining > 0:
        take = min(remaining, len(chunk))
        digest.update(chunk[:take])
        remaining -= take
    return digest.hexdigest()


def parse_sha256(text: str) -> str | None:
    for word in text.split():
        if len(word) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in word):
            return word.lower()
    return None


def parse_stat_size(text: str) -> int | None:
    match = STAT_SIZE_RE.search(text)
    return int(match.group(1)) if match else None


def write_zero_file(args: argparse.Namespace, path: str, size: int) -> tuple[bool, str]:
    path = validate_device_path(path, args.run_root)
    if size == 0:
        ok, text, rc, status = run_cmd(
            args,
            ["run", args.toybox, "truncate", "-s", "0", path],
            retry_unsafe=True,
        )
        return ok, f"truncate rc={rc} status={status}\n{text}"
    if size % 1024 != 0:
        raise RuntimeError(f"size must be 1024-aligned: {size}")
    ok, text, rc, status = run_cmd(
        args,
        ["run", args.toybox, "dd", "if=/dev/zero", f"of={path}", "bs=1024", f"count={size // 1024}"],
        retry_unsafe=True,
        timeout=args.bridge_timeout,
    )
    return ok, f"dd rc={rc} status={status}\n{text}"


def verify_file(args: argparse.Namespace, path: str, expected_size: int) -> tuple[bool, str]:
    path = validate_device_path(path, args.run_root)
    ok, stat_text, rc, status = run_cmd(args, ["stat", path], allow_error=True)
    if not ok:
        return False, f"stat rc={rc} status={status}\n{stat_text}"
    actual_size = parse_stat_size(stat_text)
    if actual_size != expected_size:
        return False, f"size mismatch expected={expected_size} actual={actual_size}\n{stat_text}"
    ok, sha_text, rc, status = run_cmd(
        args,
        ["run", args.toybox, "sha256sum", path],
        retry_unsafe=True,
    )
    if not ok:
        return False, f"sha rc={rc} status={status}\n{sha_text}"
    actual_sha = parse_sha256(sha_text)
    expected_sha = zero_sha256(expected_size)
    if actual_sha != expected_sha:
        return False, f"sha mismatch expected={expected_sha} actual={actual_sha}\n{sha_text}"
    return True, f"size={actual_size} sha={actual_sha}"


def choose_file(rng: random.Random, files: dict[str, FileState]) -> FileState:
    return files[rng.choice(sorted(files))]


def record(index: int,
           op: str,
           path: str,
           aux_path: str | None,
           size: int | None,
           ok: bool,
           detail: str) -> OperationRecord:
    return OperationRecord(index, op, path, aux_path, size, ok, detail.replace("\r", "\\r").replace("\n", " | ")[:500])


def main() -> int:
    args = parse_args()
    validate_common_args(args)
    out_dir = Path(args.out_dir) / args.run_id
    ensure_private_dir(out_dir)
    rng = random.Random(args.seed)
    files: dict[str, FileState] = {}
    records: list[OperationRecord] = []
    created_counter = 0
    started = time.monotonic()

    mkdir_chain(args, args.run_root)

    for index in range(args.ops):
        op_choices = ["create", "write", "truncate", "rename", "unlink", "fsync", "verify"]
        if not files:
            op = "create"
        else:
            op = rng.choice(op_choices)
            if op == "create" and len(files) >= args.max_files:
                op = "write"

        if op == "create":
            created_counter += 1
            path = validate_device_path(posixpath.join(args.run_root, f"file-{created_counter:03d}.bin"), args.run_root)
            size = rng.choice(SIZE_CHOICES)
            ok, detail = write_zero_file(args, path, size)
            if ok:
                files[path] = FileState(path, size)
            records.append(record(index, op, path, None, size, ok, detail))
        elif op in {"write", "truncate"}:
            state = choose_file(rng, files)
            size = rng.choice(SIZE_CHOICES)
            ok, detail = write_zero_file(args, state.path, size)
            if ok:
                state.size = size
            records.append(record(index, op, state.path, None, size, ok, detail))
        elif op == "rename":
            state = choose_file(rng, files)
            new_path = validate_device_path(posixpath.join(args.run_root, f"renamed-{index:03d}.bin"), args.run_root)
            ok, text, rc, status = run_cmd(
                args,
                ["run", args.toybox, "mv", "-f", state.path, new_path],
                retry_unsafe=True,
            )
            if ok:
                del files[state.path]
                state.path = new_path
                files[new_path] = state
            records.append(record(index, op, state.path, new_path, state.size, ok, f"mv rc={rc} status={status}\n{text}"))
        elif op == "unlink":
            state = choose_file(rng, files)
            ok, text, rc, status = run_cmd(
                args,
                ["run", args.toybox, "rm", "-f", state.path],
                retry_unsafe=True,
            )
            if ok:
                del files[state.path]
            records.append(record(index, op, state.path, None, state.size, ok, f"rm rc={rc} status={status}\n{text}"))
        elif op == "fsync":
            state = choose_file(rng, files)
            ok, text, rc, status = run_cmd(
                args,
                ["run", args.toybox, "fsync", state.path],
                retry_unsafe=True,
                allow_error=True,
            )
            if not ok:
                ok, text, rc, status = run_cmd(args, ["sync"], retry_unsafe=True)
            records.append(record(index, op, state.path, None, state.size, ok, f"fsync/sync rc={rc} status={status}\n{text}"))
        else:
            state = choose_file(rng, files)
            ok, detail = verify_file(args, state.path, state.size)
            records.append(record(index, op, state.path, None, state.size, ok, detail))

    final_verify: list[OperationRecord] = []
    for state in sorted(files.values(), key=lambda item: item.path):
        ok, detail = verify_file(args, state.path, state.size)
        final_verify.append(record(args.ops + len(final_verify), "final-verify", state.path, None, state.size, ok, detail))
    records.extend(final_verify)

    ok, sync_text, sync_rc, sync_status = run_cmd(args, ["sync"], retry_unsafe=True)
    records.append(record(args.ops + len(final_verify), "sync", args.run_root, None, None, ok, f"sync rc={sync_rc} status={sync_status}\n{sync_text}"))

    cleanup_ok = True
    cleanup_text = ""
    if not args.keep_device_files:
        ok, cleanup_text, cleanup_rc, cleanup_status = run_cmd(
            args,
            ["run", args.toybox, "rm", "-rf", args.run_root],
            retry_unsafe=True,
            allow_error=True,
        )
        cleanup_ok = ok
        records.append(record(args.ops + len(final_verify) + 1, "cleanup", args.run_root, None, None, ok, f"rm rc={cleanup_rc} status={cleanup_status}\n{cleanup_text}"))
        ok, stat_text, stat_rc, stat_status = run_cmd(args, ["stat", args.run_root], allow_error=True)
        removed = not ok
        cleanup_ok = cleanup_ok and removed
        records.append(record(args.ops + len(final_verify) + 2, "cleanup-verify", args.run_root, None, None, removed, f"stat rc={stat_rc} status={stat_status}\n{stat_text}"))

    pass_ok = all(item.ok for item in records) and cleanup_ok
    elapsed = time.monotonic() - started
    op_counts: dict[str, int] = {}
    for item in records:
        op_counts[item.op] = op_counts.get(item.op, 0) + 1
    report: dict[str, Any] = {
        "pass": pass_ok,
        "run_id": args.run_id,
        "duration_sec": elapsed,
        "seed": args.seed,
        "ops_requested": args.ops,
        "test_root": args.test_root,
        "run_root": args.run_root,
        "operation_counts": op_counts,
        "remaining_files": [asdict(item) for item in sorted(files.values(), key=lambda file_state: file_state.path)],
        "cleanup_ok": cleanup_ok,
        "records": [asdict(item) for item in records],
    }
    lines = [
        "# A90 Filesystem Exerciser Mini Report\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- run_id: `{args.run_id}`\n",
        f"- duration_sec: `{elapsed:.3f}`\n",
        f"- seed: `{args.seed}`\n",
        f"- ops_requested: `{args.ops}`\n",
        f"- records: `{len(records)}`\n",
        f"- cleanup_ok: `{cleanup_ok}`\n",
        f"- remaining_files_before_cleanup: `{len(files)}`\n\n",
        "## Operation Counts\n\n",
    ]
    for name, count in sorted(op_counts.items()):
        lines.append(f"- `{name}`: `{count}`\n")
    lines.extend([
        "\n## Failed Records\n\n",
    ])
    failures = [item for item in records if not item.ok]
    if not failures:
        lines.append("- none\n")
    else:
        for item in failures:
            lines.append(f"- `{item.index}` `{item.op}` `{item.path}`: `{item.detail}`\n")
    write_private_text(out_dir / "fs-exerciser-report.json", json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "fs-exerciser-report.md", "".join(lines))
    print(f"{'PASS' if pass_ok else 'FAIL'} run_id={args.run_id} duration={elapsed:.3f}s")
    print(out_dir / "fs-exerciser-report.md")
    print(out_dir / "fs-exerciser-report.json")
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
