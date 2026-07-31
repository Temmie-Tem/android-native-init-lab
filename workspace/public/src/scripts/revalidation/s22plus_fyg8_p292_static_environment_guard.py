#!/usr/bin/env python3
"""Prove the complete P2.92 static-check tool environment before an attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p292_frozen_qualification_guard as frozen
import s22plus_fyg8_p292_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p292_static_environment_guard_v1"
VERDICT = "PASS_P292_STATIC_ENVIRONMENT_CLOSURE_HOST_ONLY"
EXPECTED_USERSPACE_TOOL_NAMES = (
    "aarch64-linux-gnu-gcc",
    "aarch64-linux-gnu-strip",
    "aarch64-linux-gnu-readelf",
    "aarch64-linux-gnu-nm",
    "file",
    "qemu-aarch64",
)
EXPECTED_TOOL_NAMES = (
    *EXPECTED_USERSPACE_TOOL_NAMES,
    "aarch64-linux-gnu-objdump",
    "cc",
)
PINNED_TOOL_NAMES = frozenset(
    {
        "aarch64-linux-gnu-gcc",
        "aarch64-linux-gnu-strip",
        "aarch64-linux-gnu-readelf",
        "aarch64-linux-gnu-nm",
        "aarch64-linux-gnu-objdump",
        "qemu-aarch64",
    }
)
DEFAULT_TOOL_BIN = Path(
    "workspace/private/tools/p286-cross-debian13/usr/bin"
)
DEFAULT_LIBRARY_DIR = Path(
    "workspace/private/tools/p286-cross-debian13/usr/lib/x86_64-linux-gnu"
)
DEFAULT_POSTBUILD = Path(
    "workspace/private/outputs/s22plus_fyg8_p292_full_lto_029c8b17/"
    "full-lto-postbuild-audit-v2.json"
)
DEFAULT_STATIC_BASELINE = Path(
    "workspace/private/outputs/s22plus_fyg8_p292_full_lto_029c8b17/"
    "static-check-result-v1.json"
)
POSTBUILD_RECEIPT = {
    "size": 48688,
    "sha256": "963d327e0585e8affc5ae69b6e9439b9ab705d28ec4108392c16651c24cfc705",
}
STATIC_BASELINE_RECEIPT = {
    "size": 54840,
    "sha256": "b1ff4bdf8b8390273989dd1ff52ee367fe0a1d8b616a109a65372b03238d034c",
}
MAX_JSON_SIZE = 16 * 1024 * 1024
MAX_TOOL_SIZE = 128 * 1024 * 1024
SYSTEM_PATH = (Path("/usr/local/bin"), Path("/usr/bin"), Path("/bin"), Path("/usr/games"))


class EnvironmentGuardError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def stable_read(path: Path, label: str, limit: int) -> bytes:
    resolved = path.resolve(strict=True)
    before = resolved.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size <= 0 or before.st_size > limit:
        raise EnvironmentGuardError(f"{label} is not a bounded regular file")
    descriptor = os.open(resolved, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise EnvironmentGuardError(f"{label} changed while opening")
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise EnvironmentGuardError(f"{label} ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise EnvironmentGuardError(f"{label} grew while reading")
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ):
            raise EnvironmentGuardError(f"{label} changed while reading")
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def load_exact_json(
    path: Path, label: str, expected_receipt: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = stable_read(path, label, MAX_JSON_SIZE)
    actual = receipt(payload)
    if actual != expected_receipt:
        raise EnvironmentGuardError(f"{label} receipt differs")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EnvironmentGuardError(f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise EnvironmentGuardError(f"{label} is not an object")
    return value, actual


def resolved_environment(root: Path, tool_bin: Path, library_dir: Path) -> dict[str, str]:
    tool_bin = (root / tool_bin).resolve(strict=True)
    library_dir = (root / library_dir).resolve(strict=True)
    if not tool_bin.is_dir() or not library_dir.is_dir():
        raise EnvironmentGuardError("pinned static tool directory is unavailable")
    path = os.pathsep.join(str(value) for value in (tool_bin, *SYSTEM_PATH))
    return {"PATH": path, "LD_LIBRARY_PATH": str(library_dir)}


def resolve_tools(
    tool_bin: Path,
    environment: dict[str, str],
    *,
    tool_names: tuple[str, ...] = EXPECTED_TOOL_NAMES,
) -> dict[str, dict[str, Any]]:
    tool_bin = tool_bin.resolve(strict=True)
    rows: dict[str, dict[str, Any]] = {}
    for name in tool_names:
        selected = shutil.which(name, path=environment["PATH"])
        if selected is None:
            raise EnvironmentGuardError(f"required static basename is missing: {name}")
        logical = Path(selected)
        resolved = logical.resolve(strict=True)
        if name in PINNED_TOOL_NAMES:
            try:
                resolved.relative_to(tool_bin)
            except ValueError as exc:
                raise EnvironmentGuardError(
                    f"pinned static basename escaped its tool directory: {name}"
                ) from exc
        data = stable_read(resolved, f"resolved static tool {name}", MAX_TOOL_SIZE)
        rows[name] = {
            "logical_path": str(logical),
            "resolved_path": str(resolved),
            **receipt(data),
        }
    return rows


def require_baseline_receipts(
    rows: dict[str, dict[str, Any]],
    postbuild: dict[str, Any],
    static_baseline: dict[str, Any],
) -> dict[str, Any]:
    try:
        staged = postbuild["linked_audit"]["staged_input_receipts"]
        host_compiler = postbuild["linked_audit"]["postbuild_audit"][
            "host_native_exhaustive"
        ]["compiler"]
        qemu = static_baseline["tools"]["qemu_aarch64"]
    except (KeyError, TypeError) as exc:
        raise EnvironmentGuardError("static tool baseline shape differs") from exc
    expected = {
        "aarch64-linux-gnu-nm": staged.get("nm"),
        "aarch64-linux-gnu-objdump": staged.get("objdump"),
        "cc": host_compiler,
        "qemu-aarch64": qemu,
    }
    for name, identity in expected.items():
        if not isinstance(identity, dict) or set(identity) != {"size", "sha256"}:
            raise EnvironmentGuardError(f"static tool baseline is malformed: {name}")
        actual = {key: rows[name][key] for key in ("size", "sha256")}
        if actual != identity:
            raise EnvironmentGuardError(f"static tool differs from baseline: {name}")
    return {name: expected[name] for name in sorted(expected)}


def run_checked(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    label: str,
    expected_returncode: int = 0,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != expected_returncode:
        detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
        raise EnvironmentGuardError(
            f"{label} failed rc={completed.returncode}: {detail[-1000:]}"
        )
    return completed


def execute_smoke(
    root: Path,
    rows: dict[str, dict[str, Any]],
    environment: dict[str, str],
) -> dict[str, Any]:
    if tuple(userspace.base.TOOL_NAMES) != EXPECTED_USERSPACE_TOOL_NAMES:
        raise EnvironmentGuardError("nested userspace tool inventory changed")
    sanitized = os.environ.copy()
    sanitized.update(environment)
    for key in userspace.base.COMPILER_ENVIRONMENT_KEYS:
        sanitized.pop(key, None)
    sanitized["PATH"] = environment["PATH"]
    sanitized.update({"LANG": "C", "LC_ALL": "C", "SOURCE_DATE_EPOCH": "0"})
    for name, row in sorted(rows.items()):
        run_checked(
            [row["logical_path"], "--version"],
            cwd=root,
            environment=sanitized,
            label=f"version probe {name}",
        )
    source_text = """\
__attribute__((noreturn)) void _start(void) {
    register long status __asm__("x0") = 0;
    register long syscall_number __asm__("x8") = 93;
    __asm__ volatile("svc 0" : : "r"(status), "r"(syscall_number) : "memory");
    __builtin_unreachable();
}
"""
    with tempfile.TemporaryDirectory(prefix="s22-p292-static-env-") as temporary:
        directory = Path(temporary)
        source = directory / "smoke.c"
        source.write_text(source_text, encoding="ascii")
        outputs = []
        for index in range(2):
            output = directory / f"smoke-{index}"
            run_checked(
                [
                    rows["aarch64-linux-gnu-gcc"]["logical_path"],
                    *userspace.base.COMPILE_FLAGS,
                    str(source),
                    "-o",
                    str(output),
                ],
                cwd=root,
                environment=sanitized,
                label=f"AArch64 environment smoke compile {index}",
            )
            outputs.append(output)
        file_output = run_checked(
            [rows["file"]["logical_path"], "-b", str(outputs[0])],
            cwd=root,
            environment=sanitized,
            label="AArch64 environment smoke file",
        ).stdout.decode("utf-8", "replace")
        readelf = run_checked(
            [rows["aarch64-linux-gnu-readelf"]["logical_path"], "-W", "-h", "-l", str(outputs[0])],
            cwd=root,
            environment=sanitized,
            label="AArch64 environment smoke readelf",
        ).stdout.decode("utf-8", "replace")
        undefined = run_checked(
            [rows["aarch64-linux-gnu-nm"]["logical_path"], "-u", str(outputs[0])],
            cwd=root,
            environment=sanitized,
            label="AArch64 environment smoke nm",
        ).stdout
        objdump = run_checked(
            [rows["aarch64-linux-gnu-objdump"]["logical_path"], "-h", str(outputs[0])],
            cwd=root,
            environment=sanitized,
            label="AArch64 environment smoke objdump",
        ).stdout
        if (
            "ELF 64-bit LSB executable, ARM aarch64" not in file_output
            or "statically linked" not in file_output
            or "Machine:                           AArch64" not in readelf
            or "INTERP" in readelf
            or "DYNAMIC" in readelf
            or undefined.strip()
            or not objdump.strip()
        ):
            raise EnvironmentGuardError("AArch64 environment smoke ELF differs")
        for output in outputs:
            run_checked(
                [rows["aarch64-linux-gnu-strip"]["logical_path"], "-s", str(output)],
                cwd=root,
                environment=sanitized,
                label=f"AArch64 environment smoke strip {output.name}",
            )
        first = outputs[0].read_bytes()
        second = outputs[1].read_bytes()
        if first != second:
            raise EnvironmentGuardError("AArch64 environment smoke is not reproducible")
        executed = run_checked(
            [rows["qemu-aarch64"]["logical_path"], str(outputs[0])],
            cwd=root,
            environment=sanitized,
            label="AArch64 environment smoke execution",
        )
        if executed.stdout or executed.stderr:
            raise EnvironmentGuardError("AArch64 environment smoke emitted output")
        return {
            **receipt(first),
            "two_build_byte_identical": True,
            "static_aarch64": True,
            "qemu_exit": 0,
            "verified": True,
        }


def check(
    root: Path,
    *,
    tool_bin: Path = DEFAULT_TOOL_BIN,
    library_dir: Path = DEFAULT_LIBRARY_DIR,
    postbuild_path: Path = DEFAULT_POSTBUILD,
    static_baseline_path: Path = DEFAULT_STATIC_BASELINE,
    smoke_runner: Callable[
        [Path, dict[str, dict[str, Any]], dict[str, str]], dict[str, Any]
    ] = execute_smoke,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    frozen_result = frozen.check(root, frozen.DEFAULT_QUALIFICATION)
    if frozen_result.get("verdict") != frozen.VERDICT:
        raise EnvironmentGuardError("frozen qualification guard did not pass")
    postbuild, postbuild_receipt = load_exact_json(
        root / postbuild_path,
        "P2.92 final postbuild audit",
        POSTBUILD_RECEIPT,
    )
    static_baseline, static_receipt = load_exact_json(
        root / static_baseline_path,
        "P2.92 passing static baseline",
        STATIC_BASELINE_RECEIPT,
    )
    environment = resolved_environment(root, tool_bin, library_dir)
    absolute_tool_bin = (root / tool_bin).resolve(strict=True)
    rows = resolve_tools(absolute_tool_bin, environment)
    baselines = require_baseline_receipts(rows, postbuild, static_baseline)
    smoke = smoke_runner(root, rows, environment)
    if smoke.get("verified") is not True:
        raise EnvironmentGuardError("static environment smoke did not pass")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "frozen_qualification_guard": {
            "verdict": frozen_result["verdict"],
            "implementation_count": frozen_result["implementation_count"],
            "unique_implementation_count": frozen_result[
                "unique_implementation_count"
            ],
            "changed_count": frozen_result["changed_count"],
            "verified": True,
        },
        "baselines": {
            "postbuild": postbuild_receipt,
            "static": static_receipt,
            "tool_receipts": baselines,
            "verified": True,
        },
        "environment": environment,
        "tools": rows,
        "smoke": smoke,
        "verified": True,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "static_attempt_started": False,
            "promotion_started": False,
            "manifest_created": False,
            "d0_authorized": False,
            "f1_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = check(repo_root() if args.repo_root is None else args.repo_root)
    except (EnvironmentGuardError, frozen.GuardError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
