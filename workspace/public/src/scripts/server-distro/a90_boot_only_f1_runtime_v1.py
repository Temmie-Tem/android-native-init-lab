#!/usr/bin/env python3
"""Generate and reverify the A90 boot-only F1 host runtime closure.

This module is host-only.  It never contacts a device.  The generated receipt
binds the fixed isolated Python and ADB executables, Python's complete isolated
``sys.path`` trees, and the resolved ELF dependency files used by those trees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from a90_boot_only_f1_contract_v1 import (
    CAPABILITY,
    RUNTIME_QUALIFICATION_SCHEMA,
    ContractError,
    canonical_json,
    load_canonical,
    publish_exclusive,
    require_sha,
    sha256_bytes,
    validate_runtime_qualification,
)


PYTHON_EXECUTABLE = Path("/usr/bin/python3.14")
ADB_EXECUTABLE = Path("/usr/lib/android-sdk/platform-tools/adb")
LDD_EXECUTABLE = Path("/usr/bin/ldd")
MAX_COMMAND_BYTES = 64 * 1024
MAX_TREE_FILES = 100_000
MAX_TREE_BYTES = 4 << 30
COMMAND_ENV = {
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "PYTHONHASHSEED": "0",
}
PYTHON_RECEIPT_PROGRAM = r"""
import json
import sys
import sysconfig
print(json.dumps({
    "cacheTag": sys.implementation.cache_tag,
    "implementation": sys.implementation.name,
    "isolated": sys.flags.isolated,
    "noUserSite": sys.flags.no_user_site,
    "platstdlib": sysconfig.get_path("platstdlib"),
    "safePath": sys.flags.safe_path,
    "stdlib": sysconfig.get_path("stdlib"),
    "sysPath": sys.path,
    "version": sys.version,
}, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")))
""".strip()


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
    )


def _require_system_metadata(metadata: os.stat_result, path: Path) -> None:
    if (
        metadata.st_uid != 0
        or metadata.st_gid != 0
        or (not stat.S_ISLNK(metadata.st_mode) and metadata.st_mode & 0o022)
    ):
        raise ContractError(f"runtime object is not root-owned immutable: {path}")


def _require_system_ancestors(path: Path) -> None:
    current = path.parent
    while True:
        metadata = current.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or current.is_symlink()
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or metadata.st_mode & 0o022
        ):
            raise ContractError(f"runtime ancestor is not root-owned immutable: {current}")
        if current == Path("/"):
            return
        current = current.parent


def _run_exact(argv: list[str]) -> bytes:
    completed = subprocess.run(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=COMMAND_ENV,
        shell=False,
        close_fds=True,
        timeout=15,
        check=False,
    )
    if (
        completed.returncode != 0
        or completed.stderr
        or not completed.stdout
        or len(completed.stdout) > MAX_COMMAND_BYTES
    ):
        raise ContractError(f"runtime command failed: {argv[0]}")
    return completed.stdout


def _same_file_read(path: Path, maximum: int = 1 << 30) -> tuple[os.stat_result, bytes]:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        named = path.lstat()
        _require_system_ancestors(path)
        _require_system_metadata(before, path)
        _require_system_metadata(named, path)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(named.st_mode)
            or before.st_nlink < 1
            or before.st_size < 0
            or before.st_size > maximum
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise ContractError(f"runtime file identity mismatch: {path}")
        chunks = bytearray()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(descriptor, min(1 << 20, before.st_size - offset), offset)
            if not chunk:
                raise ContractError(f"runtime file ended early: {path}")
            chunks.extend(chunk)
            offset += len(chunk)
        if os.pread(descriptor, 1, before.st_size):
            raise ContractError(f"runtime file grew during read: {path}")
        after = os.fstat(descriptor)
        if _identity(after) != _identity(before):
            raise ContractError(f"runtime file drifted during read: {path}")
        return before, bytes(chunks)
    finally:
        os.close(descriptor)


def _file_receipt(path: Path) -> dict[str, Any]:
    metadata, raw = _same_file_read(path)
    return {
        "path": str(path),
        "size": metadata.st_size,
        "sha256": sha256_bytes(raw),
    }


def _entry_record(
    root: Path, path: Path
) -> tuple[dict[str, Any], int, bool, Path | None]:
    relative = str(path.relative_to(root))
    metadata = path.lstat()
    _require_system_metadata(metadata, path)
    common = {
        "path": relative,
        "mode": stat.S_IMODE(metadata.st_mode),
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "nlink": metadata.st_nlink,
    }
    if stat.S_ISDIR(metadata.st_mode):
        return ({**common, "kind": "directory"}, 0, False, None)
    if stat.S_ISLNK(metadata.st_mode):
        target = os.readlink(path)
        if _identity(path.lstat()) != _identity(metadata):
            raise ContractError(f"runtime symlink drifted during read: {path}")
        resolved = path.resolve(strict=True)
        if not resolved.is_file() or resolved.is_symlink():
            raise ContractError(f"runtime symlink target is not one regular file: {path}")
        return (
            {**common, "kind": "symlink", "target": target, "resolved": str(resolved)},
            0,
            False,
            resolved,
        )
    if stat.S_ISREG(metadata.st_mode):
        opened, raw = _same_file_read(path, MAX_TREE_BYTES)
        if (
            opened.st_mode,
            opened.st_uid,
            opened.st_gid,
            opened.st_nlink,
            opened.st_size,
        ) != (
            metadata.st_mode,
            metadata.st_uid,
            metadata.st_gid,
            metadata.st_nlink,
            metadata.st_size,
        ):
            raise ContractError(f"runtime tree file drifted: {path}")
        return (
            {
                **common,
                "kind": "regular",
                "size": metadata.st_size,
                "sha256": sha256_bytes(raw),
            },
            metadata.st_size,
            raw.startswith(b"\x7fELF"),
            None,
        )
    raise ContractError(f"runtime tree contains a special node: {path}")


def _tree_receipt(path: Path) -> tuple[dict[str, Any], list[Path], list[Path]]:
    if not path.exists():
        if path.is_symlink():
            raise ContractError(f"runtime root is a dangling symlink: {path}")
        _require_system_ancestors(path)
        empty = sha256_bytes(canonical_json({"path": str(path), "state": "ABSENT"}))
        return ({
            "path": str(path),
            "state": "ABSENT",
            "fileCount": 0,
            "totalBytes": 0,
            "treeSha256": empty,
        }, [], [])
    root_metadata = path.lstat()
    _require_system_ancestors(path)
    _require_system_metadata(root_metadata, path)
    if stat.S_ISREG(root_metadata.st_mode):
        opened, raw = _same_file_read(path, MAX_TREE_BYTES)
        record = {
            "path": str(path),
            "kind": "regular",
            "mode": stat.S_IMODE(opened.st_mode),
            "uid": opened.st_uid,
            "gid": opened.st_gid,
            "nlink": opened.st_nlink,
            "size": opened.st_size,
            "sha256": sha256_bytes(raw),
        }
        return ({
            "path": str(path),
            "state": "PRESENT_REGULAR",
            "fileCount": 1,
            "totalBytes": opened.st_size,
            "treeSha256": sha256_bytes(canonical_json(record)),
        }, [path] if raw.startswith(b"\x7fELF") else [], [])
    if not stat.S_ISDIR(root_metadata.st_mode) or path.is_symlink():
        raise ContractError(f"runtime root is not a direct directory: {path}")
    entries: list[dict[str, Any]] = []
    elf_files: list[Path] = []
    external_files: set[Path] = set()
    file_count = 0
    total_bytes = 0
    pending = [path]
    while pending:
        directory = pending.pop()
        before = directory.lstat()
        _require_system_metadata(before, directory)
        if not stat.S_ISDIR(before.st_mode) or directory.is_symlink():
            raise ContractError(f"runtime directory identity changed: {directory}")
        children = sorted(directory.iterdir(), key=lambda child: child.name)
        if _identity(directory.lstat()) != _identity(before):
            raise ContractError(f"runtime directory drifted during scan: {directory}")
        for child in children:
            record, size, is_elf, external = _entry_record(path, child)
            entries.append(record)
            if record["kind"] == "directory":
                pending.append(child)
            elif record["kind"] == "regular":
                file_count += 1
                total_bytes += size
                if is_elf:
                    elf_files.append(child)
            elif external is not None:
                external_files.add(external)
            if file_count > MAX_TREE_FILES or total_bytes > MAX_TREE_BYTES:
                raise ContractError(f"runtime tree exceeds its bound: {path}")
    entries.sort(key=lambda entry: entry["path"])
    root_record = {
        "path": str(path),
        "mode": stat.S_IMODE(root_metadata.st_mode),
        "uid": root_metadata.st_uid,
        "gid": root_metadata.st_gid,
        "nlink": root_metadata.st_nlink,
        "entries": entries,
    }
    return ({
        "path": str(path),
        "state": "PRESENT_DIRECTORY",
        "fileCount": file_count,
        "totalBytes": total_bytes,
        "treeSha256": sha256_bytes(canonical_json(root_record)),
    }, sorted(elf_files), sorted(external_files, key=str))


def _python_receipt() -> dict[str, Any]:
    raw = _run_exact([str(PYTHON_EXECUTABLE), "-I", "-c", PYTHON_RECEIPT_PROGRAM])
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise ContractError("Python version receipt framing mismatch")
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("Python version receipt is not JSON") from exc
    expected_keys = {
        "cacheTag", "implementation", "isolated", "noUserSite", "platstdlib",
        "safePath", "stdlib", "sysPath", "version",
    }
    if (
        type(value) is not dict
        or set(value) != expected_keys
        or value["implementation"] != "cpython"
        or value["isolated"] != 1
        or value["noUserSite"] != 1
        or value["safePath"] is not True
        or type(value["sysPath"]) is not list
        or not value["sysPath"]
        or any(type(item) is not str or not Path(item).is_absolute() for item in value["sysPath"])
        or len(value["sysPath"]) != len(set(value["sysPath"]))
    ):
        raise ContractError("Python isolated version receipt mismatch")
    return value


def _adb_receipt() -> dict[str, Any]:
    raw = _run_exact([str(ADB_EXECUTABLE), "version"])
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ContractError("ADB version receipt is not ASCII") from exc
    if (
        len(lines) != 4
        or lines[0] != "Android Debug Bridge version 1.0.41"
        or not lines[1].startswith("Version ")
        or lines[2] != f"Installed as {ADB_EXECUTABLE}"
        or not lines[3].startswith("Running on Linux ")
    ):
        raise ContractError("ADB version receipt mismatch")
    return {"lines": lines}


def _ldd_dependencies(objects: Iterable[Path]) -> list[Path]:
    dependencies: set[Path] = set()
    for obj in sorted(set(objects), key=str):
        raw = _run_exact([str(LDD_EXECUTABLE), str(obj)])
        for line in raw.decode("ascii").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("linux-vdso.so"):
                continue
            if stripped == "statically linked":
                continue
            if "not found" in stripped:
                raise ContractError(f"unresolved dynamic dependency for {obj}")
            if "=>" in stripped:
                candidate = stripped.split("=>", 1)[1].strip().split(" ", 1)[0]
            elif stripped.startswith("/"):
                candidate = stripped.split(" ", 1)[0]
            else:
                raise ContractError(f"unparsed ldd output for {obj}: {stripped}")
            resolved = Path(candidate).resolve(strict=True)
            if not resolved.is_absolute() or resolved.is_symlink():
                raise ContractError(f"dynamic dependency is not canonical: {candidate}")
            dependencies.add(resolved)
    return sorted(dependencies, key=str)


def _member(
    executable: Path,
    version_receipt: dict[str, Any],
    roots: list[dict[str, Any]],
    external_files: list[dict[str, Any]],
    libraries: list[dict[str, Any]],
) -> dict[str, Any]:
    executable_receipt = _file_receipt(executable)
    version_sha = sha256_bytes(canonical_json(version_receipt))
    closure = {
        "versionReceiptSha256": version_sha,
        "runtimeRoots": roots,
        "externalFiles": external_files,
        "dynamicLibraries": libraries,
    }
    return {
        **executable_receipt,
        "versionReceipt": version_receipt,
        "versionReceiptSha256": version_sha,
        "runtimeRoots": roots,
        "externalFiles": external_files,
        "dynamicLibraries": libraries,
        "runtimeClosureSha256": sha256_bytes(canonical_json(closure)),
    }


def build_runtime_qualification(owner_closure_sha256: str) -> dict[str, Any]:
    require_sha(owner_closure_sha256, "owner closure SHA256")
    python_receipt = _python_receipt()
    roots: list[dict[str, Any]] = []
    python_elfs: list[Path] = []
    python_external: set[Path] = set()
    for text in python_receipt["sysPath"]:
        receipt, elfs, external = _tree_receipt(Path(text))
        roots.append(receipt)
        python_elfs.extend(elfs)
        python_external.update(external)
    roots.sort(key=lambda item: item["path"])
    python_libraries = [
        _file_receipt(path)
        for path in _ldd_dependencies([PYTHON_EXECUTABLE, *python_elfs])
    ]
    adb_libraries = [
        _file_receipt(path) for path in _ldd_dependencies([ADB_EXECUTABLE])
    ]
    value = {
        "schema": RUNTIME_QUALIFICATION_SCHEMA,
        "capability": CAPABILITY,
        "ownerClosureSha256": owner_closure_sha256,
        "python": _member(
            PYTHON_EXECUTABLE,
            python_receipt,
            roots,
            [_file_receipt(path) for path in sorted(python_external, key=str)],
            python_libraries,
        ),
        "adb": _member(ADB_EXECUTABLE, _adb_receipt(), [], [], adb_libraries),
    }
    return validate_runtime_qualification(value, owner_closure_sha256)


def verify_runtime_qualification_current(
    value: dict[str, Any], owner_closure_sha256: str
) -> dict[str, Any]:
    validated = validate_runtime_qualification(value, owner_closure_sha256)
    current = build_runtime_qualification(owner_closure_sha256)
    if canonical_json(validated) != canonical_json(current):
        raise ContractError("runtime qualification does not equal current host bytes")
    return validated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-closure-sha256", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    if (args.output is None) == (args.check is None):
        parser.error("select exactly one of --output or --check")
    if args.output is not None:
        value = build_runtime_qualification(args.owner_closure_sha256)
        publish_exclusive(args.output, value)
        return 0
    assert args.check is not None
    _, value = load_canonical(args.check, "runtime qualification")
    verify_runtime_qualification_current(value, args.owner_closure_sha256)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
