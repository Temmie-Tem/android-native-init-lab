#!/usr/bin/env python3
"""Fail closed if a frozen P2.92 qualification implementation changed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any


SCHEMA = "s22plus_fyg8_p292_frozen_qualification_guard_v1"
VERDICT = "PASS_P292_FROZEN_QUALIFICATION_IMPLEMENTATION_UNCHANGED_H0"
QUALIFICATION_SCHEMA = "s22plus_fyg8_p292_pre_lto_qualification_v1"
QUALIFICATION_VERDICT = "PASS_P292_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
EXPECTED_IMPLEMENTATION_COUNT = 51
EXPECTED_UNIQUE_IMPLEMENTATION_COUNT = 50
EXPECTED_IMPLEMENTATION_ALIASES = {
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p292_linked_audit.py": frozenset(
        {"linked_audit", "p292_linked_audit"}
    ),
}
FROZEN_QUALIFICATION_RECEIPT = {
    "size": 94438,
    "sha256": "425d18956e67285ebb580a220486166cf076eca55d75c3b57a3bfb2af5478f8e",
}
DEFAULT_QUALIFICATION = Path(
    "workspace/private/outputs/s22plus_fyg8_p292_pre_lto/qualification.json"
)
MAX_QUALIFICATION_SIZE = 16 * 1024 * 1024
MAX_IMPLEMENTATION_SIZE = 64 * 1024 * 1024


class GuardError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _relative_path(value: Any, label: str) -> Path:
    if not isinstance(value, str):
        raise GuardError(f"{label} path is not text")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or "." in pure.parts
        or ".." in pure.parts
        or pure.as_posix() != value
    ):
        raise GuardError(f"{label} path is not canonical repository-relative")
    return Path(*pure.parts)


def _stable_read(path: Path, label: str, limit: int) -> bytes:
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise GuardError(f"{label} is missing, indirect, or not regular")
    if before.st_size <= 0 or before.st_size > limit:
        raise GuardError(f"{label} size is outside the bound")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise GuardError(f"{label} changed while opening")
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise GuardError(f"{label} ended before its recorded size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise GuardError(f"{label} grew while reading")
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
            raise GuardError(f"{label} changed while reading")
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _identity(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"path", "size", "sha256"}:
        raise GuardError(f"{label} identity shape differs")
    relative = _relative_path(value["path"], label)
    size = value["size"]
    digest = value["sha256"]
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or not 0 < size <= MAX_IMPLEMENTATION_SIZE
        or not isinstance(digest, str)
        or len(digest) != 64
    ):
        raise GuardError(f"{label} identity is malformed")
    try:
        bytes.fromhex(digest)
    except ValueError as exc:
        raise GuardError(f"{label} digest is not hexadecimal") from exc
    return {"path": relative, "size": size, "sha256": digest}


def check(root: Path, qualification_path: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    qualification_path = (
        qualification_path
        if qualification_path.is_absolute()
        else root / qualification_path
    )
    payload = _stable_read(
        qualification_path,
        "P2.92 frozen qualification",
        MAX_QUALIFICATION_SIZE,
    )
    qualification_receipt = _receipt(payload)
    if qualification_receipt != FROZEN_QUALIFICATION_RECEIPT:
        raise GuardError("P2.92 frozen qualification receipt differs")
    try:
        qualification = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GuardError("P2.92 frozen qualification is not canonical JSON") from exc
    if (
        not isinstance(qualification, dict)
        or qualification.get("schema") != QUALIFICATION_SCHEMA
        or qualification.get("verdict") != QUALIFICATION_VERDICT
        or qualification.get("build_allowed") is not True
    ):
        raise GuardError("P2.92 frozen qualification identity is not accepted")
    implementation_block = qualification.get("gate_implementation")
    if (
        not isinstance(implementation_block, dict)
        or implementation_block.get("verified") is not True
    ):
        raise GuardError("P2.92 frozen implementation inventory differs")
    implementations = {
        name: value
        for name, value in implementation_block.items()
        if name != "verified"
    }
    if len(implementations) != EXPECTED_IMPLEMENTATION_COUNT:
        raise GuardError("P2.92 frozen implementation inventory differs")
    path_identities: dict[Path, dict[str, Any]] = {}
    path_names: dict[Path, set[str]] = {}
    rows: dict[str, Any] = {}
    for name, value in sorted(implementations.items()):
        if not isinstance(name, str) or not name:
            raise GuardError("P2.92 frozen implementation name is invalid")
        expected = _identity(value, f"P2.92 frozen implementation {name}")
        relative = expected["path"]
        prior = path_identities.get(relative)
        if prior is not None and prior != expected:
            raise GuardError("P2.92 frozen implementation alias identity differs")
        path_identities[relative] = expected
        path_names.setdefault(relative, set()).add(name)
        actual = _receipt(
            _stable_read(
                root / relative,
                f"P2.92 current implementation {name}",
                MAX_IMPLEMENTATION_SIZE,
            )
        )
        if actual != {key: expected[key] for key in ("size", "sha256")}:
            raise GuardError(f"P2.92 frozen implementation changed: {name}")
        rows[name] = {
            "path": relative.as_posix(),
            **actual,
            "byte_identical": True,
        }
    aliases = {
        path.as_posix(): frozenset(names)
        for path, names in path_names.items()
        if len(names) > 1
    }
    if (
        len(path_identities) != EXPECTED_UNIQUE_IMPLEMENTATION_COUNT
        or aliases != EXPECTED_IMPLEMENTATION_ALIASES
    ):
        raise GuardError("P2.92 frozen implementation alias inventory differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "qualification": qualification_receipt,
        "implementation_count": len(rows),
        "unique_implementation_count": len(path_identities),
        "implementation_aliases": {
            path: sorted(names) for path, names in sorted(aliases.items())
        },
        "implementations": rows,
        "changed_count": 0,
        "verified": True,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "manifest_created": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root())
    parser.add_argument(
        "--qualification", type=Path, default=DEFAULT_QUALIFICATION
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = check(args.repo_root, args.qualification)
    except (GuardError, OSError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
