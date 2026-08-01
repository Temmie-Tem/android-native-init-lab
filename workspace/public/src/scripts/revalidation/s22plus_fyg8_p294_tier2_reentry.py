#!/usr/bin/env python3
"""Reconcile one exact post-qualification P2.94 Tier-2 observer change."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any, Callable, Iterator

import s22plus_fyg8_p282_pre_lto_qualification as evidence_verifier
import s22plus_fyg8_p286_pre_lto_qualification as frozen_verifier


SCHEMA = "s22plus_fyg8_p294_tier2_reentry_v1"
VERDICT = "PASS_P294_QUALIFICATION_BOUND_TIER2_REENTRY_HOST_ONLY"
QUALIFICATION_SCHEMA = "s22plus_fyg8_p294_pre_lto_qualification_v1"
QUALIFICATION_VERDICT = "PASS_P294_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
FROZEN_QUALIFICATION_RECEIPT = {
    "size": 97913,
    "sha256": "158cdeddb1d8bf1ffe1adb57106fa0e537a650d2bd1502d7ad0dd0e722b09a4d",
}
FROZEN_COMMIT = "9b0627851943504c68e1ba7b91f2d555f52f39c1"
OBSERVER_NAME = "observer"
OBSERVER_PATH = Path(
    "workspace/public/src/scripts/revalidation/"
    "device_action_cdc_acm_observer_v1.py"
)
FROZEN_OBSERVER_RECEIPT = {
    "size": 51304,
    "sha256": "a2536c44f8585cb41e58eab97c4bb97e4f957533139c847b49f55ef729f7586a",
}
CURRENT_OBSERVER_RECEIPT = {
    "size": 51402,
    "sha256": "6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9",
}
OBSERVER_TEST_PATH = Path("tests/test_device_action_cdc_acm_observer_v1.py")
FROZEN_OBSERVER_TEST_RECEIPT = {
    "size": 55001,
    "sha256": "18522aeedadfac5c25f0b4748b80e1557b6256238fd9df6636c67ac29a897038",
}
CURRENT_OBSERVER_TEST_RECEIPT = {
    "size": 55001,
    "sha256": "1087c8656c70ae4a4159e124f31af468d050c4a1ccece93b03227f29b8347213",
}
EXPECTED_IMPLEMENTATION_COUNT = 50
EXPECTED_UNIQUE_IMPLEMENTATION_COUNT = 49
EXPECTED_ALIASES = {
    Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p294_linked_audit.py"
    ): frozenset({"linked_audit", "p294_linked_audit"})
}
DEFAULT_QUALIFICATION = Path(
    "workspace/private/outputs/s22plus_fyg8_p294_pre_lto/qualification.json"
)
MAX_QUALIFICATION_SIZE = 16 * 1024 * 1024
MAX_IMPLEMENTATION_SIZE = 64 * 1024 * 1024


class ReentryError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_read(path: Path, label: str, limit: int) -> bytes:
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise ReentryError(f"{label} is missing, indirect, or not regular")
    if before.st_size <= 0 or before.st_size > limit:
        raise ReentryError(f"{label} size is outside the bound")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise ReentryError(f"{label} changed while opening")
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise ReentryError(f"{label} ended before its recorded size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise ReentryError(f"{label} grew while reading")
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
            raise ReentryError(f"{label} changed while reading")
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _relative_path(value: Any, label: str) -> Path:
    if not isinstance(value, str):
        raise ReentryError(f"{label} path is not text")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or "." in pure.parts
        or ".." in pure.parts
        or pure.as_posix() != value
    ):
        raise ReentryError(f"{label} path is not canonical repository-relative")
    return Path(*pure.parts)


def _identity(value: Any, label: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"path", "size", "sha256"}:
        raise ReentryError(f"{label} identity shape differs")
    path = _relative_path(value["path"], label)
    size = value["size"]
    digest = value["sha256"]
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or not 0 < size <= MAX_IMPLEMENTATION_SIZE
        or not isinstance(digest, str)
        or len(digest) != 64
    ):
        raise ReentryError(f"{label} identity is malformed")
    try:
        bytes.fromhex(digest)
    except ValueError as exc:
        raise ReentryError(f"{label} digest is not hexadecimal") from exc
    return path, {"size": size, "sha256": digest}


def _git_blob(root: Path, commit: str, path: Path) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0 or not completed.stdout:
        raise ReentryError("frozen observer Git blob is unavailable")
    return completed.stdout


def _expected_current_observer(frozen: bytes) -> bytes:
    old_limit = b"GUARD_MAX_SEC_LIMIT = 3600\n"
    new_limit = b"GUARD_MAX_SEC_LIMIT = 7200\n"
    old_tail = b"GUARD_UNCOMMANDED_EXIT = 4\nPKEXEC = \"/usr/bin/pkexec\"\n"
    new_tail = (
        b"GUARD_UNCOMMANDED_EXIT = 4\n"
        b"GUARD_RUNTIME_RULE_PATH = Path(\n"
        b"    \"/run/udev/rules.d/79-device-action-f1-cdc-acm-guard.rules\"\n"
        b")\n"
        b"PKEXEC = \"/usr/bin/pkexec\"\n"
    )
    if frozen.count(old_limit) != 1 or frozen.count(old_tail) != 1:
        raise ReentryError("frozen observer change anchors differ")
    return frozen.replace(old_limit, new_limit).replace(old_tail, new_tail)


def _expected_current_observer_test(frozen: bytes) -> bytes:
    old = b"for invalid in (359, 3601, 360.0, True):"
    new = b"for invalid in (359, 7201, 360.0, True):"
    if frozen.count(old) != 1:
        raise ReentryError("frozen observer test change anchor differs")
    return frozen.replace(old, new)


def _run_current_observer_test(root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", str(OBSERVER_TEST_PATH)],
        cwd=root,
        env={**os.environ, "PYTHONPYCACHEPREFIX": "/tmp/a90_pycache"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=180,
    )
    matches = re.findall(r"Ran ([0-9]+) tests?", completed.stdout)
    if completed.returncode != 0 or len(matches) != 1 or int(matches[0]) < 1:
        raise ReentryError("current observer focused test did not pass exactly")
    return {
        "command": [
            sys.executable,
            "-m",
            "unittest",
            "-v",
            str(OBSERVER_TEST_PATH),
        ],
        "test_count": int(matches[0]),
        "output_sha256": hashlib.sha256(
            completed.stdout.encode("utf-8")
        ).hexdigest(),
        "verified": True,
    }


def check(root: Path, qualification_path: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    qualification_path = (
        qualification_path
        if qualification_path.is_absolute()
        else root / qualification_path
    )
    qualification_payload = _stable_read(
        qualification_path,
        "P2.94 frozen qualification",
        MAX_QUALIFICATION_SIZE,
    )
    if _receipt(qualification_payload) != FROZEN_QUALIFICATION_RECEIPT:
        raise ReentryError("P2.94 frozen qualification receipt differs")
    try:
        qualification = json.loads(qualification_payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReentryError("P2.94 frozen qualification is not JSON") from exc
    if (
        not isinstance(qualification, dict)
        or qualification.get("schema") != QUALIFICATION_SCHEMA
        or qualification.get("verdict") != QUALIFICATION_VERDICT
        or qualification.get("build_allowed") is not True
    ):
        raise ReentryError("P2.94 frozen qualification identity differs")
    gate = qualification.get("gate_implementation")
    if not isinstance(gate, dict) or gate.get("verified") is not True:
        raise ReentryError("P2.94 frozen gate inventory differs")
    implementations = {name: value for name, value in gate.items() if name != "verified"}
    if len(implementations) != EXPECTED_IMPLEMENTATION_COUNT:
        raise ReentryError("P2.94 frozen gate count differs")

    rows: dict[str, Any] = {}
    path_names: dict[Path, set[str]] = {}
    frozen_observer = _git_blob(root, FROZEN_COMMIT, OBSERVER_PATH)
    if _receipt(frozen_observer) != FROZEN_OBSERVER_RECEIPT:
        raise ReentryError("P2.94 frozen observer Git receipt differs")
    current_observer = _stable_read(
        root / OBSERVER_PATH,
        "P2.94 current observer",
        MAX_IMPLEMENTATION_SIZE,
    )
    if (
        _receipt(current_observer) != CURRENT_OBSERVER_RECEIPT
        or current_observer != _expected_current_observer(frozen_observer)
    ):
        raise ReentryError("P2.94 current observer delta differs")
    frozen_observer_test = _git_blob(root, FROZEN_COMMIT, OBSERVER_TEST_PATH)
    if _receipt(frozen_observer_test) != FROZEN_OBSERVER_TEST_RECEIPT:
        raise ReentryError("P2.94 frozen observer test Git receipt differs")
    current_observer_test = _stable_read(
        root / OBSERVER_TEST_PATH,
        "P2.94 current observer test",
        MAX_IMPLEMENTATION_SIZE,
    )
    if (
        _receipt(current_observer_test) != CURRENT_OBSERVER_TEST_RECEIPT
        or current_observer_test
        != _expected_current_observer_test(frozen_observer_test)
    ):
        raise ReentryError("P2.94 current observer test delta differs")
    observer_test = _run_current_observer_test(root)

    for name, value in sorted(implementations.items()):
        if not isinstance(name, str) or not name:
            raise ReentryError("P2.94 frozen gate name is invalid")
        path, expected = _identity(value, f"P2.94 frozen gate {name}")
        path_names.setdefault(path, set()).add(name)
        if name == OBSERVER_NAME:
            if path != OBSERVER_PATH or expected != FROZEN_OBSERVER_RECEIPT:
                raise ReentryError("P2.94 frozen observer identity differs")
            rows[name] = {
                "path": path.as_posix(),
                "frozen": expected,
                "current": CURRENT_OBSERVER_RECEIPT,
                "exact_declared_delta": True,
            }
            continue
        actual = _receipt(
            _stable_read(
                root / path,
                f"P2.94 current frozen gate {name}",
                MAX_IMPLEMENTATION_SIZE,
            )
        )
        if actual != expected:
            raise ReentryError(f"P2.94 frozen gate changed: {name}")
        rows[name] = {
            "path": path.as_posix(),
            "frozen": expected,
            "current": actual,
            "byte_identical": True,
        }

    aliases = {
        path: frozenset(names)
        for path, names in path_names.items()
        if len(names) > 1
    }
    if (
        len(path_names) != EXPECTED_UNIQUE_IMPLEMENTATION_COUNT
        or aliases != EXPECTED_ALIASES
    ):
        raise ReentryError("P2.94 frozen gate alias inventory differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "qualification": FROZEN_QUALIFICATION_RECEIPT,
        "frozen_commit": FROZEN_COMMIT,
        "implementation_count": len(rows),
        "unique_implementation_count": len(path_names),
        "changed_names": [OBSERVER_NAME, "observer_test"],
        "changed_count": 2,
        "gate_changed_count": 1,
        "evidence_changed_count": 1,
        "unchanged_gate_count": len(rows) - 1,
        "observer_test": observer_test,
        "implementations": rows,
        "verified": True,
        "safety": {
            "host_only": True,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


@contextmanager
def _frozen_gate_context(gate: dict[str, Any]) -> Iterator[None]:
    previous = frozen_verifier._gate_implementation  # noqa: SLF001
    previous_material = evidence_verifier._repo_material  # noqa: SLF001

    def frozen_material(root: Path, path: Path, label: str) -> dict[str, Any]:
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            relative = None
        if relative == OBSERVER_TEST_PATH:
            return {
                "path": OBSERVER_TEST_PATH.as_posix(),
                **FROZEN_OBSERVER_TEST_RECEIPT,
            }
        return previous_material(root, path, label)

    frozen_verifier._gate_implementation = lambda: gate  # noqa: SLF001
    evidence_verifier._repo_material = frozen_material  # noqa: SLF001
    try:
        yield
    finally:
        frozen_verifier._gate_implementation = previous  # noqa: SLF001
        evidence_verifier._repo_material = previous_material  # noqa: SLF001


def verify_with_frozen_gate(
    verifier: Callable[..., dict[str, Any]],
    value: Any,
    exact_contract: dict[str, Any],
    *,
    intent_path: Path,
    patch_path: Path,
    root: Path | None = None,
) -> dict[str, Any]:
    repository = repo_root() if root is None else root.resolve()
    if not isinstance(value, dict):
        raise ReentryError("P2.94 qualification provenance is not an object")
    relative = _relative_path(
        value.get("qualification_repo_path"),
        "P2.94 qualification",
    )
    result = check(repository, repository / relative)
    qualification = json.loads(
        _stable_read(
            repository / relative,
            "P2.94 frozen qualification",
            MAX_QUALIFICATION_SIZE,
        ).decode("ascii")
    )
    with _frozen_gate_context(qualification["gate_implementation"]):
        verified = verifier(
            value,
            exact_contract,
            intent_path=intent_path,
            patch_path=patch_path,
            root=repository,
        )
    if result.get("verified") is not True or verified != value:
        raise ReentryError("P2.94 qualification re-entry result differs")
    return verified


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root())
    parser.add_argument("--qualification", type=Path, default=DEFAULT_QUALIFICATION)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = check(args.repo_root, args.qualification)
    except (OSError, ReentryError, subprocess.SubprocessError) as exc:
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
