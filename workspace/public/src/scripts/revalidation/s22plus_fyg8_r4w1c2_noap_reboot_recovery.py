#!/usr/bin/env python3
"""One-shot no-AP reboot recovery for the consumed R4W1-C2 parse failure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import re
import selectors
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import s22plus_fyg8_r4w1c2_measured_live_gate as measured
import s22plus_fyg8_r4w1c_connected_gate as connected
import s22plus_odin_transition_core as odin_core
import s22plus_boot_only_live_core as core


TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c2_noap_reboot_recovery.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1c2_noap_reboot_recovery.py")
POLICY_DRAFT_RELATIVE = Path(
    "docs/operations/S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_EXCEPTION_DRAFT_2026-07-21.md"
)
POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1"
POLICY_END = "END_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1"
POLICY_STATE = "S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_STATE=ACTIVE"
OLD_POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_V1"
OLD_POLICY_END = "END_S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_V1"
OLD_POLICY_ACTIVE = "S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_STATE=ACTIVE"
OLD_POLICY_RETIRED = "S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_STATE=RETIRED"
EXPECTED_POLICY_TEMPLATE_SHA256 = (
    "bf90b0c5ceeb7178491319cf4dae1e958e30a90c17e0c8badf30189cb13aecdf"
)
LIVE_ACK = "S22PLUS-FYG8-R4W1C2-NOAP-REBOOT-RECOVERY-LIVE"
PASS_VERDICT = "PASS_R4W1C2_NOAP_REBOOT_RECOVERY_EXACT_MAGISK_ANDROID"
FAIL_VERDICT = "FAIL_R4W1C2_NOAP_REBOOT_RECOVERY_REQUIRED"

INCIDENT_RUN = Path(
    "workspace/private/runs/s22plus-r4w1c2-measured-live-20260720T164444Z"
)
RECOVERY_RUN_ROOT = Path("workspace/private/runs")
RECOVERY_STATE = Path(
    "workspace/private/state/"
    "s22plus_fyg8_r4w1c2_noap_reboot_recovery_consumed.json"
)

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PARSE_FAILURE_STDOUT = b"Reboot into normal mode\nFail parse /proc/self/fd/7\n"
PARSE_FAILURE_SHA256 = hashlib.sha256(PARSE_FAILURE_STDOUT).hexdigest()
ODIN_SUCCESS_LINES = (
    "Reboot into normal mode",
    "Setup Connection",
    "initializeConnection",
    "Receive PIT Info",
    "success getpit",
    "Upload Binaries",
    "Close Connection",
)
MAX_ODIN_OUTPUT = 1024 * 1024
ODIN_CLEANUP_GRACE_SEC = 2.0
FINAL_PUBLISH_ATTEMPTS = 2
ODIN_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
PHYSICAL_CONTINUITY_BASIS = (
    "operator-attested-original-r4w1c2-handset;same-cable-hub-host-port;"
    "screen-normal-samsung-download-at-live-ack;download-serial-absent;"
    "not-host-intrinsically-verifiable"
)
UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z"
)

PINNED_FILES: dict[str, tuple[Path, int, str]] = {
    "consumed": (
        measured.CONSUMED_STATE,
        2680,
        "64d15cb2fab8dc7ea5ca0b569832cc15c32c7623e05cfbe6a60924cbf02ec477",
    ),
    "live_result": (
        INCIDENT_RUN / "result-live.json",
        108695,
        "74aa8f0a03b033299b2af5a6c97d9cba819ce671b04666549be3da45b38d9728",
    ),
    "recovery_result": (
        INCIDENT_RUN / "result-recovery-attempt-01.json",
        190297,
        "aabf8323dd4d78451c3378f968a2bb1900625a6705cba2122cb261b9aaab5456",
    ),
    "stock_intent": (
        INCIDENT_RUN / measured.STOCK_CLEANUP_INTENT_NAME,
        1290,
        "50d48adc1ad9710628d5282978ca8f984e2d1478192ccec2b75185628363f23c",
    ),
    "candidate_log": (
        INCIDENT_RUN / "odin-candidate.json",
        462,
        "84523c1d488f51c936a1d62fa832b0640e30f92d8544cb5c41e1dc70cfbc4757",
    ),
    "magisk_log": (
        INCIDENT_RUN / "odin-magisk-attempt-01.json",
        468,
        "12eef1ec931c2052196ca64d5930a23fc25cbfceb19530565b36eefadeadcc1d",
    ),
    "stock_log": (
        INCIDENT_RUN / "odin-stock-attempt-01.json",
        466,
        "175794cbe076165a41e171e6c5af8defb4c36158e651926af1871c44f810585d",
    ),
    "transaction": (
        INCIDENT_RUN / "transaction.jsonl",
        6971,
        "2811364fada46d840e8787f8947491688df1f3065d6be75e670b0a923561e97b",
    ),
    "recovery_timeline": (
        INCIDENT_RUN / "recovery-attempt-01-timeline.json",
        536,
        "48226674518c975f3d9d866834222e6f4217593cffb25b0e6700d6308c7df239",
    ),
}

DEPENDENCY_FILES: dict[str, tuple[Path, int, str]] = {
    "measured_helper": (
        measured.SCRIPT_RELATIVE,
        111396,
        "22cba55a924e9c56e5d245114357921ebefc73460a673e40e22c7ecf2e145172",
    ),
    "connected_helper": (
        connected.SCRIPT_RELATIVE,
        54734,
        "fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9",
    ),
    "odin_core": (
        connected.ODIN_CORE_RELATIVE,
        58423,
        "c9abb179158bb45039574465e743f1f5bee18f993cbddd2f0b40e9048d1ca6b3",
    ),
    "live_core": (
        connected.LIVE_CORE_RELATIVE,
        12524,
        "9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725",
    ),
    "usbfs_identity": (
        measured.USBFS_IDENTITY_RELATIVE,
        18998,
        "2d1310e129670e89862826bcacc3886820c60f2691f342720927e8e13bddfe10",
    ),
    "transport": (
        connected.TRANSPORT_RELATIVE,
        35401,
        "f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4",
    ),
    "m3_observable": (
        Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_m3_observable_live_gate.py"
        ),
        24686,
        "1f093d78a110925440c98741399d8828201cce38265a5c941ac2f71b6c104305",
    ),
}

ABSOLUTE_DEPENDENCIES: dict[str, tuple[Path, int, str]] = {
    "birth_time_stat": (
        measured.STAT_BINARY,
        11352352,
        "48893b0fb21436b54619db80486e83ef39dfccaf1aefe83dfa00c02d6146e8c0",
    ),
    "odin": (
        connected.DEFAULT_ODIN,
        connected.EXPECTED_ODIN_SIZE,
        connected.EXPECTED_ODIN_SHA256,
    ),
}

FAILED_LOGS = {
    "candidate_log": ("r4w1c-candidate", connected.EXPECTED_CANDIDATE_AP_SHA256),
    "magisk_log": (
        "r4w1c-magisk-rollback",
        connected.EXPECTED_MAGISK_AP_SHA256,
    ),
    "stock_log": ("r4w1c-stock-cleanup", connected.EXPECTED_STOCK_AP_SHA256),
}


class RecoveryError(RuntimeError):
    pass


class BoundedOdinError(RecoveryError):
    def __init__(
        self,
        message: str,
        stdout: bytes,
        stderr: bytes,
        *,
        timed_out: bool = False,
        output_overflow: bool = False,
        runner_error: bool = False,
        kill_sent: bool = False,
        reaped: bool = False,
        cleanup_error: str | None = None,
    ):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.output_overflow = output_overflow
        self.runner_error = runner_error
        self.kill_sent = kill_sent
        self.reaped = reaped
        self.cleanup_error = cleanup_error


def recovery_guard_path(root: Path) -> Path:
    state_path = root / RECOVERY_STATE
    return root / f".{state_path.name}.guard"


def close_noexcept(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except Exception:
        pass


def emit_summary(value: dict[str, str]) -> None:
    try:
        print(json.dumps(value, indent=2))
    except Exception:
        pass


def close_object_noexcept(value: Any) -> None:
    try:
        value.close()
    except Exception:
        pass


def recovery_consumed(root: Path) -> bool:
    paths = (root / RECOVERY_STATE, recovery_guard_path(root))
    return any(path.exists() or path.is_symlink() for path in paths)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_bytes(path: Path, *, maximum: int = 4 * 1024 * 1024) -> bytes:
    try:
        return core.read_stable_file(path, maximum=maximum)
    except (OSError, core.LiveCoreError) as exc:
        raise RecoveryError(f"pinned file is unavailable: {path}") from exc


def require_direct_directory(path: Path) -> os.stat_result:
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise RecoveryError(f"direct directory is unavailable: {path}") from exc
    if not stat.S_ISDIR(metadata.st_mode) or path.is_symlink():
        raise RecoveryError(f"path is not a direct directory: {path}")
    return metadata


def require_direct_directory_chain(root: Path, path: Path) -> None:
    direct_root = Path(os.path.abspath(root))
    direct_path = Path(os.path.abspath(path))
    try:
        relative = direct_path.relative_to(direct_root)
    except ValueError as exc:
        raise RecoveryError(f"path escapes repository root: {path}") from exc
    require_direct_directory(direct_root)
    current = direct_root
    for part in relative.parts:
        current /= part
        require_direct_directory(current)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def open_bound_directory(root: Path, path: Path) -> int:
    require_direct_directory_chain(root, path)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RecoveryError(f"cannot hold direct directory: {path}") from exc
    try:
        revalidate_bound_directory(descriptor, path)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def revalidate_bound_directory(descriptor: int, path: Path) -> os.stat_result:
    try:
        held = os.fstat(descriptor)
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise RecoveryError(f"bound directory is unavailable: {path}") from exc
    if (
        not stat.S_ISDIR(held.st_mode)
        or not stat.S_ISDIR(current.st_mode)
        or path.is_symlink()
        or (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino)
    ):
        raise RecoveryError(f"bound directory identity changed: {path}")
    return held


def _validate_leaf_name(name: str) -> None:
    if not name or name in {".", ".."} or "/" in name or "\x00" in name:
        raise RecoveryError(f"invalid descriptor-bound evidence name: {name!r}")


def read_bytes_at(directory_fd: int, name: str, *, maximum: int) -> bytes:
    _validate_leaf_name(name)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise RecoveryError(f"descriptor-bound evidence is unavailable: {name}") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 0
            or before.st_size > maximum
        ):
            raise RecoveryError(f"descriptor-bound evidence is not private: {name}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise RecoveryError(f"descriptor-bound evidence exceeds bound: {name}")
        after = os.fstat(descriptor)
        if (
            (before.st_dev, before.st_ino, before.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
            or after.st_nlink != 1
            or total != before.st_size
        ):
            raise RecoveryError(f"descriptor-bound evidence changed while read: {name}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def leaf_exists_at(directory_fd: int, name: str) -> bool:
    _validate_leaf_name(name)
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise RecoveryError(f"cannot inspect descriptor-bound evidence: {name}") from exc
    return True


def exact_record_at(
    directory_fd: int,
    name: str,
    payload: bytes,
    *,
    display_path: Path,
) -> dict[str, Any]:
    actual = read_bytes_at(directory_fd, name, maximum=max(len(payload), 1))
    if actual != payload:
        raise RecoveryError(f"descriptor-bound evidence content changed: {display_path}")
    return {
        "path": str(display_path),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def existing_record_at(
    directory_fd: int,
    name: str,
    *,
    display_path: Path,
    maximum: int = 4 * 1024 * 1024,
) -> dict[str, Any]:
    payload = read_bytes_at(directory_fd, name, maximum=maximum)
    return {
        "path": str(display_path),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def durable_create_bytes_at(
    directory_fd: int,
    name: str,
    payload: bytes,
    *,
    display_path: Path,
) -> dict[str, Any]:
    _validate_leaf_name(name)
    temporary = f".{name}.tmp-{os.getpid()}-{time.time_ns()}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    temporary_exists = False
    try:
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
        temporary_exists = True
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RecoveryError(f"temporary evidence is not private: {display_path}")
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise RecoveryError(f"evidence write stalled: {display_path}")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        try:
            os.link(
                temporary,
                name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise RecoveryError(f"evidence already exists: {display_path}") from exc
        os.unlink(temporary, dir_fd=directory_fd)
        temporary_exists = False
        os.fsync(directory_fd)
        return exact_record_at(
            directory_fd, name, payload, display_path=display_path
        )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_exists:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except FileNotFoundError:
                pass


def durable_create_bytes_at_idempotent(
    directory_fd: int,
    name: str,
    payload: bytes,
    *,
    display_path: Path,
    attempts: int = FINAL_PUBLISH_ATTEMPTS,
) -> dict[str, Any]:
    if attempts < 1:
        raise RecoveryError("descriptor-bound publication attempts are invalid")
    last_error: BaseException | None = None
    for attempt in range(attempts):
        try:
            return durable_create_bytes_at(
                directory_fd, name, payload, display_path=display_path
            )
        except (OSError, RecoveryError) as exc:
            last_error = exc
            try:
                return exact_record_at(
                    directory_fd, name, payload, display_path=display_path
                )
            except RecoveryError:
                if attempt + 1 >= attempts:
                    raise exc
    assert last_error is not None
    raise last_error


def json_record_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RecoveryError("evidence JSON is not finite and serializable") from exc


def durable_create_json_at_idempotent(
    directory_fd: int,
    name: str,
    value: Any,
    *,
    display_path: Path,
) -> dict[str, Any]:
    return durable_create_bytes_at_idempotent(
        directory_fd,
        name,
        json_record_bytes(value),
        display_path=display_path,
    )


def parse_json_at(directory_fd: int, name: str, label: str) -> dict[str, Any]:
    return parse_json(read_bytes_at(directory_fd, name, maximum=4 * 1024 * 1024), label)


def revalidate_bound_file_path(
    directory_fd: int,
    directory_path: Path,
    name: str,
    payload: bytes,
) -> None:
    held_directory = revalidate_bound_directory(directory_fd, directory_path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        by_name = os.open(name, flags, dir_fd=directory_fd)
        by_path = os.open(directory_path / name, flags)
    except OSError as exc:
        raise RecoveryError(f"bound evidence path is unavailable: {directory_path / name}") from exc
    try:
        name_stat = os.fstat(by_name)
        path_stat = os.fstat(by_path)
        if (
            not stat.S_ISREG(name_stat.st_mode)
            or name_stat.st_nlink != 1
            or (name_stat.st_dev, name_stat.st_ino)
            != (path_stat.st_dev, path_stat.st_ino)
            or name_stat.st_dev != held_directory.st_dev
        ):
            raise RecoveryError(f"bound evidence path identity changed: {directory_path / name}")
    finally:
        os.close(by_name)
        os.close(by_path)
    exact_record_at(
        directory_fd, name, payload, display_path=directory_path / name
    )


def allocate_recovery_run_dir(root: Path) -> Path:
    base = Path(os.path.abspath(root / RECOVERY_RUN_ROOT))
    require_direct_directory_chain(root, base)
    run_dir = base / (
        "s22plus-r4w1c2-noap-reboot-recovery-"
        + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    if run_dir.parent != base:
        raise RecoveryError("recovery run directory is not a direct run-root child")
    try:
        run_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise RecoveryError(f"recovery run directory already exists: {run_dir}") from exc
    fsync_directory(base)
    require_direct_directory(run_dir)
    return run_dir


def pinned_file(root: Path, key: str) -> tuple[Path, bytes]:
    relative, size, digest = PINNED_FILES[key]
    path = root / relative
    if path.is_symlink() or not path.is_file() or path.resolve() != path.absolute():
        raise RecoveryError(f"pinned incident file is missing or indirect: {relative}")
    payload = stable_bytes(path, maximum=max(size + 1, 4 * 1024 * 1024))
    if len(payload) != size or sha256_bytes(payload) != digest:
        raise RecoveryError(f"pinned incident file identity changed: {relative}")
    return path, payload


def parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryError(f"{label} is not a JSON object")
    return value


def helper_identity(root: Path) -> dict[str, Any]:
    path = root / SCRIPT_RELATIVE
    return {"path": str(SCRIPT_RELATIVE), **core.hash_stable_file(path)}


def test_identity(root: Path) -> dict[str, Any]:
    path = root / TEST_RELATIVE
    return {"path": str(TEST_RELATIVE), **core.hash_stable_file(path)}


def exact_file_identity(path: Path, *, size: int, digest: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.resolve() != path.absolute():
        raise RecoveryError(f"runtime dependency is missing or indirect: {path}")
    payload = stable_bytes(path, maximum=size + 1)
    if len(payload) != size or sha256_bytes(payload) != digest:
        raise RecoveryError(f"runtime dependency identity changed: {path}")
    return {"path": str(path), "size": size, "sha256": digest}


def dependency_identities(root: Path) -> dict[str, dict[str, Any]]:
    identities: dict[str, dict[str, Any]] = {}
    for name, (relative, size, digest) in DEPENDENCY_FILES.items():
        identities[name] = exact_file_identity(
            root / relative, size=size, digest=digest
        )
        identities[name]["path"] = str(relative)
    for name, (path, size, digest) in ABSOLUTE_DEPENDENCIES.items():
        identities[name] = exact_file_identity(path, size=size, digest=digest)
    validate_runtime_dependency_graph(root)
    return identities


def validate_runtime_dependency_graph(root: Path) -> None:
    source_root = SCRIPT_RELATIVE.parent
    expected = {relative for relative, _size, _digest in DEPENDENCY_FILES.values()}
    discovered: set[Path] = set()
    pending = [SCRIPT_RELATIVE]
    visited: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        visited.add(relative)
        payload = stable_bytes(root / relative, maximum=2 * 1024 * 1024)
        try:
            tree = ast.parse(payload, filename=str(relative))
        except SyntaxError as exc:
            raise RecoveryError(f"runtime dependency is not valid Python: {relative}") from exc
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".", 1)[0])
        for module_name in modules:
            candidate = source_root / f"{module_name}.py"
            if (root / candidate).is_file():
                discovered.add(candidate)
                pending.append(candidate)
    if discovered != expected:
        missing = sorted(str(path) for path in discovered - expected)
        surplus = sorted(str(path) for path in expected - discovered)
        raise RecoveryError(
            f"runtime dependency graph changed: unpinned={missing}, unused={surplus}"
        )


def policy_draft_identity(root: Path) -> tuple[dict[str, Any], bytes]:
    path = root / POLICY_DRAFT_RELATIVE
    payload = stable_bytes(path, maximum=256 * 1024)
    if not payload.endswith(b"\n"):
        raise RecoveryError("no-AP recovery policy draft lacks its exact newline")
    return (
        {
            "path": str(POLICY_DRAFT_RELATIVE),
            "size": len(payload),
            "sha256": sha256_bytes(payload),
        },
        payload,
    )


def canonical_policy_template(
    payload: bytes,
    *,
    helper: dict[str, Any],
    test: dict[str, Any],
) -> bytes:
    canonical = payload
    replacements = (
        (str(helper["size"]).encode("ascii"), b"<HELPER_SIZE>"),
        (str(helper["sha256"]).encode("ascii"), b"<HELPER_SHA256>"),
        (str(test["size"]).encode("ascii"), b"<TEST_SIZE>"),
        (str(test["sha256"]).encode("ascii"), b"<TEST_SHA256>"),
    )
    for exact, placeholder in replacements:
        if canonical.count(exact) != 1:
            raise RecoveryError("policy draft dynamic identity is not unique and exact")
        canonical = canonical.replace(exact, placeholder)
    return canonical


def extract_policy(text: str) -> str | None:
    start = text.find(POLICY_BEGIN)
    end = text.find(POLICY_END)
    if start < 0 and end < 0:
        return None
    if start < 0 or end < start or text.find(POLICY_BEGIN, start + 1) >= 0:
        raise RecoveryError("no-AP recovery policy markers are malformed")
    end += len(POLICY_END)
    if text.find(POLICY_END, end) >= 0:
        raise RecoveryError("duplicate no-AP recovery policy marker")
    return text[start:end]


def require_old_policy_retired(text: str) -> None:
    start = text.find(OLD_POLICY_BEGIN)
    end = text.find(OLD_POLICY_END)
    if (
        start < 0
        or end < start
        or text.find(OLD_POLICY_BEGIN, start + 1) >= 0
    ):
        raise RecoveryError("consumed R4W1-C2 measured policy markers are malformed")
    end += len(OLD_POLICY_END)
    if text.find(OLD_POLICY_END, end) >= 0:
        raise RecoveryError("consumed R4W1-C2 measured policy marker is duplicated")
    old_clause = text[start:end]
    if (
        OLD_POLICY_ACTIVE in old_clause
        or old_clause.count(OLD_POLICY_RETIRED) != 1
        or text.count(OLD_POLICY_ACTIVE) != 0
        or text.count(OLD_POLICY_RETIRED) != 1
    ):
        raise RecoveryError("consumed R4W1-C2 measured policy is not exactly retired")


def policy_status(root: Path) -> dict[str, Any]:
    text = stable_bytes(root / "AGENTS.md", maximum=2 * 1024 * 1024).decode("utf-8")
    clause = extract_policy(text)
    if clause is None:
        return {"active": False, "clause": None, "sha256": None}
    helper = helper_identity(root)
    test = test_identity(root)
    dependencies = dependency_identities(root)
    draft, draft_payload = policy_draft_identity(root)
    if clause.encode("utf-8") + b"\n" != draft_payload:
        raise RecoveryError("active no-AP recovery policy is not the exact reviewed draft")
    require_old_policy_retired(text)
    template_sha256 = sha256_bytes(
        canonical_policy_template(draft_payload, helper=helper, test=test)
    )
    if template_sha256 != EXPECTED_POLICY_TEMPLATE_SHA256:
        raise RecoveryError("no-AP recovery policy template identity changed")
    required = (
        POLICY_STATE,
        LIVE_ACK,
        helper["sha256"],
        test["sha256"],
        PINNED_FILES["consumed"][2],
        PINNED_FILES["stock_intent"][2],
        PARSE_FAILURE_SHA256,
        connected.EXPECTED_ODIN_SHA256,
        *(identity["sha256"] for identity in dependencies.values()),
    )
    if any(value not in clause for value in required):
        raise RecoveryError("active no-AP recovery policy does not bind exact inputs")
    return {
        "active": True,
        "clause": clause,
        "sha256": sha256_bytes(clause.encode("utf-8")),
        "draft": draft,
        "template_sha256": template_sha256,
        "dependencies": dependencies,
    }


def validate_failed_log(value: dict[str, Any], *, label: str, ap_sha256: str) -> None:
    expected = {
        "label": label,
        "returncode": 1,
        "stdout_bytes": len(PARSE_FAILURE_STDOUT),
        "stderr_bytes": 0,
        "stdout_sha256": PARSE_FAILURE_SHA256,
        "stderr_sha256": EMPTY_SHA256,
        "odin_sha256": connected.EXPECTED_ODIN_SHA256,
        "ap_sha256": ap_sha256,
        "sealed_inputs": True,
    }
    if value != expected:
        raise RecoveryError(f"{label} is not the exact sealed-path parse failure")


def validate_incident(root: Path) -> dict[str, Any]:
    opened: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    payloads: dict[str, bytes] = {}
    for key, (relative, size, digest) in PINNED_FILES.items():
        path, payload = pinned_file(root, key)
        payloads[key] = payload
        bindings[key] = {"path": str(relative), "size": size, "sha256": digest}
        if path.suffix == ".json":
            opened[key] = parse_json(payload, key)

    consumed = opened["consumed"]
    if (
        consumed.get("schema") != "s22plus_fyg8_r4w1c2_measured_consumed_v1"
        or consumed.get("target") != TARGET
        or consumed.get("run_dir") != str(INCIDENT_RUN)
        or consumed.get("usb_binding")
        != {
            "topology": "2-1.3",
            "serial_sha256": measured.android_serial_sha256("RFCT519XWGK"),
            "download_serial_state": measured.DOWNLOAD_USB_SERIAL_STATE,
        }
        or consumed.get("android_serial") != "RFCT519XWGK"
    ):
        raise RecoveryError("consumed incident binding is not exact")

    live_result = opened["live_result"]
    recovery_result = opened["recovery_result"]
    if (
        live_result.get("verdict")
        != "FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        or live_result.get("candidate_transfer_ok") is not False
        or live_result.get("candidate_transfer_error")
        != "r4w1c-candidate Odin flash failed rc=1"
        or recovery_result.get("verdict")
        != "FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        or recovery_result.get("error")
        != "r4w1c-stock-cleanup Odin flash failed rc=1"
        or recovery_result.get("rollback_ok") is not False
        or recovery_result.get("final_android") is not None
    ):
        raise RecoveryError("incident result contract does not describe failed rollback")

    for key, (label, ap_sha256) in FAILED_LOGS.items():
        validate_failed_log(opened[key], label=label, ap_sha256=ap_sha256)

    intent = opened["stock_intent"]
    if (
        intent.get("schema") != "s22plus_fyg8_r4w1c_stock_cleanup_intent_v1"
        or intent.get("target") != "stock"
        or intent.get("magisk_failure") != "definite-nonzero"
        or intent.get("stock_ap_sha256") != connected.EXPECTED_STOCK_AP_SHA256
        or intent.get("usb_binding", {}).get("topology") != "2-1.3"
        or intent.get("usb_binding", {}).get("serial_state") != "absent"
        or intent.get("ticket", {}).get("device_identity")
        != intent.get("usb_binding", {}).get("device_identity")
    ):
        raise RecoveryError("stock cleanup intent binding is not exact")

    transaction = payloads["transaction"]
    if b'"phase":"rollback_transfer_finished"' in transaction:
        raise RecoveryError("incident unexpectedly contains a completed rollback transfer")
    if PARSE_FAILURE_SHA256 != "7f6162459d49213e9d36485eaa1e7748492b484f4538db45ef50ab4d9f31adb4":
        raise RecoveryError("parse-failure preimage is not exact")

    return {
        "target": TARGET,
        "run_dir": str(INCIDENT_RUN),
        "android_serial": consumed["android_serial"],
        "usb_binding": consumed["usb_binding"],
        "parse_failure_stdout": {
            "bytes": len(PARSE_FAILURE_STDOUT),
            "sha256": PARSE_FAILURE_SHA256,
            "text": PARSE_FAILURE_STDOUT.decode("ascii").splitlines(),
            "meaning": "AP parse stopped before Setup Connection",
        },
        "files": bindings,
        "no_completed_transfer_receipt": True,
    }


def offline_check(root: Path) -> dict[str, Any]:
    incident = validate_incident(root)
    dependencies = dependency_identities(root)
    helper = helper_identity(root)
    test = test_identity(root)
    draft, draft_payload = policy_draft_identity(root)
    template_sha256 = sha256_bytes(
        canonical_policy_template(draft_payload, helper=helper, test=test)
    )
    if template_sha256 != EXPECTED_POLICY_TEMPLATE_SHA256:
        raise RecoveryError("no-AP recovery policy template identity changed")
    draft["template_sha256"] = template_sha256
    policy = policy_status(root)
    return {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_offline_v1",
        "verdict": "PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY",
        "target": TARGET,
        "helper": helper,
        "test": test,
        "policy_draft": draft,
        "dependencies": dependencies,
        "incident": incident,
        "policy": {key: value for key, value in policy.items() if key != "clause"},
        "recovery_consumed": recovery_consumed(root),
        "device_contact": False,
        "device_writes": False,
        "reboot": False,
        "odin_transfer": False,
        "flash": False,
    }


def exact_timeline(
    started: str,
    reboot_start: str,
    reboot_done: str,
    ready: str,
    ended: str | None = None,
) -> list[dict[str, str]]:
    ended = ready if ended is None else ended
    return [
        {"name": "live_session_start", "timestamp_utc": started},
        {"name": "candidate_flash_start", "timestamp_utc": started},
        {"name": "candidate_flash_done", "timestamp_utc": started},
        {"name": "candidate_boot_ready", "timestamp_utc": started},
        {"name": "rollback_flash_start", "timestamp_utc": reboot_start},
        {"name": "rollback_flash_done", "timestamp_utc": reboot_done},
        {"name": "rollback_boot_ready", "timestamp_utc": ready},
        {"name": "live_session_end", "timestamp_utc": ended},
    ]


def validate_reboot_stdout(stdout: bytes, stderr: bytes, device: str) -> list[str]:
    if stderr:
        raise RecoveryError("no-AP Odin reboot produced stderr")
    try:
        text = stdout.decode("utf-8")
    except UnicodeError as exc:
        raise RecoveryError("no-AP Odin reboot stdout is not UTF-8") from exc
    lines = text.splitlines()
    if (
        not stdout
        or len(stdout) > MAX_ODIN_OUTPUT
        or device not in lines
        or any(required not in lines for required in ODIN_SUCCESS_LINES)
        or any("fail" in line.lower() for line in lines)
    ):
        raise RecoveryError("no-AP Odin reboot output lacks the exact success shape")
    positions = [lines.index(value) for value in ODIN_SUCCESS_LINES]
    if positions != sorted(positions):
        raise RecoveryError("no-AP Odin reboot success lines are out of order")
    return lines


def bounded_kill_reap(
    process: subprocess.Popen[bytes], deadline: float
) -> tuple[bool, bool, str | None]:
    kill_sent = False
    cleanup_error: str | None = None
    running = True
    try:
        running = process.poll() is None
    except Exception as exc:
        cleanup_error = f"poll before kill failed: {exc}"
    try:
        if running:
            process.kill()
            kill_sent = True
    except Exception as exc:
        detail = f"kill failed: {exc}"
        cleanup_error = detail if cleanup_error is None else f"{cleanup_error}; {detail}"
    remaining = max(0.0, deadline - time.monotonic())
    try:
        running = process.poll() is None
        if running and remaining > 0:
            process.wait(timeout=remaining)
    except Exception as exc:
        detail = f"bounded reap failed: {exc}"
        cleanup_error = detail if cleanup_error is None else f"{cleanup_error}; {detail}"
    try:
        reaped = process.poll() is not None
    except Exception as exc:
        reaped = False
        detail = f"poll after reap failed: {exc}"
        cleanup_error = detail if cleanup_error is None else f"{cleanup_error}; {detail}"
    if not reaped and cleanup_error is None:
        cleanup_error = "child was not reaped within the total timeout"
    return kill_sent, reaped, cleanup_error


def bounded_odin_runner(
    command: list[str],
    *,
    stdout: int,
    stderr: int,
    stdin: int,
    pass_fds: tuple[int, ...],
    env: dict[str, str],
    timeout: float,
    check: bool,
) -> subprocess.CompletedProcess[bytes]:
    if (
        stdout != subprocess.PIPE
        or stderr != subprocess.PIPE
        or stdin != subprocess.DEVNULL
        or env != ODIN_ENV
        or check
    ):
        raise RecoveryError("bounded Odin runner contract is invalid")
    if not math.isfinite(timeout) or timeout <= 0:
        raise RecoveryError("bounded Odin timeout is invalid")
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    streams: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    total = 0
    deadline = time.monotonic() + timeout
    cleanup_grace = min(ODIN_CLEANUP_GRACE_SEC, timeout / 2.0)
    work_deadline = deadline - cleanup_grace
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            pass_fds=pass_fds,
            env=dict(env),
        )
        selector = selectors.DefaultSelector()
        assert process.stdout is not None
        assert process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = work_deadline - time.monotonic()
            if remaining <= 0:
                raise BoundedOdinError(
                    "no-AP Odin reboot timed out",
                    b"".join(streams["stdout"]),
                    b"".join(streams["stderr"]),
                    timed_out=True,
                )
            events = selector.select(remaining)
            if not events:
                raise BoundedOdinError(
                    "no-AP Odin reboot timed out",
                    b"".join(streams["stdout"]),
                    b"".join(streams["stderr"]),
                    timed_out=True,
                )
            for key, _mask in events:
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remaining_capacity = MAX_ODIN_OUTPUT - total
                if len(chunk) > remaining_capacity:
                    streams[str(key.data)].append(chunk[:remaining_capacity])
                    raise BoundedOdinError(
                        "no-AP Odin reboot output exceeded its bound",
                        b"".join(streams["stdout"]),
                        b"".join(streams["stderr"]),
                        output_overflow=True,
                    )
                total += len(chunk)
                streams[str(key.data)].append(chunk)
        remaining = work_deadline - time.monotonic()
        if remaining <= 0:
            raise BoundedOdinError(
                "no-AP Odin reboot timed out",
                b"".join(streams["stdout"]),
                b"".join(streams["stderr"]),
                timed_out=True,
            )
        returncode = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(
            command,
            returncode,
            stdout=b"".join(streams["stdout"]),
            stderr=b"".join(streams["stderr"]),
        )
    except BoundedOdinError as exc:
        if process is not None:
            exc.kill_sent, exc.reaped, exc.cleanup_error = bounded_kill_reap(
                process, deadline
            )
        raise
    except subprocess.TimeoutExpired as exc:
        kill_sent = False
        reaped = False
        cleanup_error = None
        if process is not None:
            kill_sent, reaped, cleanup_error = bounded_kill_reap(process, deadline)
        raise BoundedOdinError(
            "no-AP Odin reboot timed out",
            b"".join(streams["stdout"]),
            b"".join(streams["stderr"]),
            timed_out=True,
            kill_sent=kill_sent,
            reaped=reaped,
            cleanup_error=cleanup_error,
        ) from exc
    except OSError as exc:
        if process is None:
            raise
        kill_sent, reaped, cleanup_error = bounded_kill_reap(process, deadline)
        raise BoundedOdinError(
            "no-AP Odin reboot runner failed after process start",
            b"".join(streams["stdout"]),
            b"".join(streams["stderr"]),
            runner_error=True,
            kill_sent=kill_sent,
            reaped=reaped,
            cleanup_error=cleanup_error,
        ) from exc
    except BaseException as exc:
        if process is None:
            raise
        kill_sent, reaped, cleanup_error = bounded_kill_reap(process, deadline)
        raise BoundedOdinError(
            "no-AP Odin runner failed after process start: "
            f"{type(exc).__name__}: {exc}",
            b"".join(streams["stdout"]),
            b"".join(streams["stderr"]),
            runner_error=True,
            kill_sent=kill_sent,
            reaped=reaped,
            cleanup_error=cleanup_error,
        ) from exc
    finally:
        if selector is not None:
            close_object_noexcept(selector)
        if process is not None:
            if process.stdout is not None:
                close_object_noexcept(process.stdout)
            if process.stderr is not None:
                close_object_noexcept(process.stderr)


def sealed_enumeration_runner(
    odin_fd: int,
    external_odin: Path,
    *,
    output_dir_fd: int,
    output_dir: Path,
    outcomes: list[dict[str, Any]],
) -> Callable[[list[str], float], subprocess.CompletedProcess[bytes]]:
    expected = [str(external_odin), "-l"]
    invocation = 0

    def persist(
        index: int,
        *,
        stdout: bytes,
        stderr: bytes,
        returned: bool,
        returncode: int | None,
        timed_out: bool,
        output_overflow: bool,
        runner_error: str | None,
        kill_sent: bool,
        reaped: bool,
        cleanup_error: str | None,
    ) -> None:
        prefix = f"odin-enumeration-{index:06d}"
        stdout_path = output_dir / f"{prefix}.stdout"
        stderr_path = output_dir / f"{prefix}.stderr"
        outcome_path = output_dir / f"{prefix}-outcome.json"
        stdout_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stdout_path.name, stdout, display_path=stdout_path
        )
        stderr_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stderr_path.name, stderr, display_path=stderr_path
        )
        value = {
            "schema": "s22plus_fyg8_r4w1c2_noap_enumeration_outcome_v1",
            "created_at_utc": core.utc_now(),
            "invocation": index,
            "command_shape": ["<sealed-odin-fd>", "-l"],
            "attempted": True,
            "returned": returned,
            "returncode": returncode,
            "timed_out": timed_out,
            "output_overflow": output_overflow,
            "runner_error": runner_error,
            "kill_sent": kill_sent,
            "reaped": reaped,
            "cleanup_error": cleanup_error,
            "stdout": stdout_record,
            "stderr": stderr_record,
        }
        outcome_record = durable_create_json_at_idempotent(
            output_dir_fd,
            outcome_path.name,
            value,
            display_path=outcome_path,
        )
        outcomes.append({**value, "outcome": outcome_record})

    def run(argv: list[str], timeout: float) -> subprocess.CompletedProcess[bytes]:
        nonlocal invocation
        if argv != expected:
            raise RecoveryError("sealed Odin enumeration command shape changed")
        index = invocation
        invocation += 1
        try:
            completed = bounded_odin_runner(
                [f"/proc/self/fd/{odin_fd}", "-l"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                pass_fds=(odin_fd,),
                env=dict(ODIN_ENV),
                timeout=timeout,
                check=False,
            )
        except BoundedOdinError as exc:
            bounded_stdout, bounded_stderr, overflow = cap_output_pair(
                exc.stdout or b"", exc.stderr or b""
            )
            persist(
                index,
                stdout=bounded_stdout,
                stderr=bounded_stderr,
                returned=False,
                returncode=None,
                timed_out=exc.timed_out,
                output_overflow=exc.output_overflow or overflow,
                runner_error=str(exc) if exc.runner_error else None,
                kill_sent=exc.kill_sent,
                reaped=exc.reaped,
                cleanup_error=exc.cleanup_error,
            )
            raise
        except Exception as exc:
            persist(
                index,
                stdout=b"",
                stderr=b"",
                returned=False,
                returncode=None,
                timed_out=False,
                output_overflow=False,
                runner_error=f"{type(exc).__name__}: {exc}",
                kill_sent=False,
                reaped=False,
                cleanup_error=None,
            )
            raise
        bounded_stdout, bounded_stderr, overflow = cap_output_pair(
            completed.stdout or b"", completed.stderr or b""
        )
        persist(
            index,
            stdout=bounded_stdout,
            stderr=bounded_stderr,
            returned=True,
            returncode=completed.returncode,
            timed_out=False,
            output_overflow=overflow,
            runner_error=None,
            kill_sent=False,
            reaped=True,
            cleanup_error=None,
        )
        if overflow:
            raise RecoveryError("sealed Odin enumeration output exceeded its bound")
        return subprocess.CompletedProcess(
            completed.args,
            completed.returncode,
            stdout=bounded_stdout,
            stderr=bounded_stderr,
        )

    return run


def wait_for_endpoint_hardened(
    odin: Path,
    run_dir: Path,
    *,
    timeout_sec: float,
    sequence: int,
    lease: Any,
    expected_usb_binding: dict[str, str],
    runner: Callable[[list[str], float], subprocess.CompletedProcess[bytes]],
) -> tuple[odin_core.EndpointTicket, int]:
    started = time.monotonic()
    stable = measured.wait_for_stable_download_node(
        expected_usb_binding, timeout_sec
    )
    remaining = timeout_sec - (time.monotonic() - started)
    if remaining <= 0:
        raise RecoveryError("Download endpoint stabilization exhausted the wait deadline")
    result = odin_core.wait_for_single_live_endpoint(
        odin,
        run_dir,
        timeout_sec=remaining,
        sequence_start=sequence,
        poll_sec=1.0,
        lease=lease,
        runner=runner,
        endpoint_observer_factory=odin_core.measured_usbfs_observer,
    )
    if result.ticket is None or result.timed_out:
        raise RecoveryError("one normal Download endpoint did not appear in time")
    stable_node = stable["node"]
    if (
        result.ticket.device != stable["device"]
        or result.ticket.device_identity
        != str(stable_node.get("immutable_identity", ""))
    ):
        raise RecoveryError(
            "ticketed Odin endpoint differs from the stabilized endpoint"
        )
    measured.require_ticket_usb_binding(result.ticket, expected_usb_binding)
    return result.ticket, result.next_sequence


def revalidate_ticket_hardened(
    odin: Path,
    run_dir: Path,
    ticket: odin_core.EndpointTicket,
    *,
    sequence: int,
    lease: Any,
    runner: Callable[[list[str], float], subprocess.CompletedProcess[bytes]],
) -> tuple[str, int, dict[str, Any]]:
    record = odin_core.revalidate_endpoint_ticket(
        odin,
        run_dir,
        ticket,
        sequence=sequence,
        timeout_sec=15.0,
        lease=lease,
        runner=runner,
        endpoint_observer_factory=odin_core.measured_usbfs_observer,
    )
    return ticket.device, sequence + 1, record


def run_noap_odin(
    odin_fd: int,
    device: str,
    *,
    output_dir_fd: int,
    stdout_path: Path,
    stderr_path: Path,
    outcome_path: Path,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = bounded_odin_runner,
) -> tuple[subprocess.CompletedProcess[bytes], list[str], list[str]]:
    command = [f"/proc/self/fd/{odin_fd}", "--reboot", "-d", device]
    forbidden = {"-a", "-b", "-c", "-s", "-u", "-e", "-V", "--redownload"}
    if any(argument in forbidden for argument in command):
        raise RecoveryError("no-AP reboot command contains a transfer option")
    try:
        completed = runner(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=(odin_fd,),
            env=dict(ODIN_ENV),
            timeout=60,
            check=False,
        )
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
    except (subprocess.TimeoutExpired, BoundedOdinError) as exc:
        stdout, stderr, overflow = cap_output_pair(
            exc.stdout or b"", exc.stderr or b""
        )
        stdout_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stdout_path.name, stdout, display_path=stdout_path
        )
        stderr_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stderr_path.name, stderr, display_path=stderr_path
        )
        durable_create_json_at_idempotent(
            output_dir_fd,
            outcome_path.name,
            {
                "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
                "created_at_utc": core.utc_now(),
                "attempted": True,
                "returned": False,
                "timed_out": bool(getattr(exc, "timed_out", True)),
                "output_overflow": bool(
                    getattr(exc, "output_overflow", False) or overflow
                ),
                "runner_error": (
                    str(exc) if getattr(exc, "runner_error", False) else None
                ),
                "kill_sent": bool(getattr(exc, "kill_sent", False)),
                "reaped": bool(getattr(exc, "reaped", False)),
                "cleanup_error": getattr(exc, "cleanup_error", None),
                "returncode": None,
                "stdout": stdout_record,
                "stderr": stderr_record,
            },
            display_path=outcome_path,
        )
        raise RecoveryError(str(exc)) from exc
    except Exception as exc:
        stdout_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stdout_path.name, b"", display_path=stdout_path
        )
        stderr_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stderr_path.name, b"", display_path=stderr_path
        )
        durable_create_json_at_idempotent(
            output_dir_fd,
            outcome_path.name,
            {
                "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
                "created_at_utc": core.utc_now(),
                "attempted": True,
                "returned": False,
                "timed_out": False,
                "output_overflow": False,
                "returncode": None,
                "runner_error": str(exc),
                "kill_sent": False,
                "reaped": False,
                "cleanup_error": None,
                "stdout": stdout_record,
                "stderr": stderr_record,
            },
            display_path=outcome_path,
        )
        raise RecoveryError("no-AP Odin reboot runner failed before a return") from exc
    stdout, stderr, overflow = cap_output_pair(stdout, stderr)
    if overflow:
        stdout_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stdout_path.name, stdout, display_path=stdout_path
        )
        stderr_record = durable_create_bytes_at_idempotent(
            output_dir_fd, stderr_path.name, stderr, display_path=stderr_path
        )
        durable_create_json_at_idempotent(
            output_dir_fd,
            outcome_path.name,
            {
                "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
                "created_at_utc": core.utc_now(),
                "attempted": True,
                "returned": True,
                "timed_out": False,
                "output_overflow": True,
                "returncode": completed.returncode,
                "kill_sent": False,
                "reaped": True,
                "cleanup_error": None,
                "stdout": stdout_record,
                "stderr": stderr_record,
            },
            display_path=outcome_path,
        )
        raise RecoveryError("no-AP Odin reboot output exceeded its bound")
    stdout_record = durable_create_bytes_at_idempotent(
        output_dir_fd, stdout_path.name, stdout, display_path=stdout_path
    )
    stderr_record = durable_create_bytes_at_idempotent(
        output_dir_fd, stderr_path.name, stderr, display_path=stderr_path
    )
    durable_create_json_at_idempotent(
        output_dir_fd,
        outcome_path.name,
        {
            "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
            "created_at_utc": core.utc_now(),
            "attempted": True,
            "returned": True,
            "timed_out": False,
            "output_overflow": False,
            "returncode": completed.returncode,
            "kill_sent": False,
            "reaped": True,
            "cleanup_error": None,
            "stdout": stdout_record,
            "stderr": stderr_record,
        },
        display_path=outcome_path,
    )
    if completed.returncode != 0:
        raise RecoveryError(f"no-AP Odin reboot failed rc={completed.returncode}")
    lines = validate_reboot_stdout(stdout, stderr, device)
    return completed, command, lines


def cap_output_pair(stdout: bytes, stderr: bytes) -> tuple[bytes, bytes, bool]:
    bounded_stdout = stdout[:MAX_ODIN_OUTPUT]
    bounded_stderr = stderr[: MAX_ODIN_OUTPUT - len(bounded_stdout)]
    overflow = len(stdout) + len(stderr) > MAX_ODIN_OUTPUT
    return bounded_stdout, bounded_stderr, overflow


def create_recovery_state(
    root: Path,
    *,
    run_dir_fd: int,
    state_dir_fd: int,
    guard_dir_fd: int,
    policy: dict[str, Any],
    incident: dict[str, Any],
    run_dir: Path,
    helper: dict[str, Any],
    test: dict[str, Any],
    dependencies: dict[str, dict[str, Any]],
    policy_draft: dict[str, Any],
) -> dict[str, Any]:
    path = root / RECOVERY_STATE
    guard_path = recovery_guard_path(root)
    revalidate_bound_directory(run_dir_fd, run_dir)
    expected_run_root = Path(os.path.abspath(root / RECOVERY_RUN_ROOT))
    if Path(os.path.abspath(run_dir)).parent != expected_run_root:
        raise RecoveryError(
            "recovery state run directory is outside the direct run root"
        )
    revalidate_bound_directory(state_dir_fd, path.parent)
    revalidate_bound_directory(guard_dir_fd, guard_path.parent)
    for directory_fd, name in (
        (state_dir_fd, path.name),
        (guard_dir_fd, guard_path.name),
    ):
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise RecoveryError("no-AP reboot recovery was already consumed")
    run_metadata = os.fstat(run_dir_fd)
    record = {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_consumed_v1",
        "created_at_utc": core.utc_now(),
        "target": TARGET,
        "ack": LIVE_ACK,
        "operator_attestation_ack": LIVE_ACK,
        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
        "helper_sha256": helper["sha256"],
        "test_sha256": test["sha256"],
        "policy_clause_sha256": policy["sha256"],
        "policy_draft": policy_draft,
        "runtime_dependencies": dependencies,
        "incident_consumed_sha256": incident["files"]["consumed"]["sha256"],
        "stock_intent_sha256": incident["files"]["stock_intent"]["sha256"],
        "run_dir": str(run_dir.relative_to(root)),
        "run_directory_identity": {
            "st_dev": run_metadata.st_dev,
            "st_ino": run_metadata.st_ino,
        },
        "guard_path": str(guard_path.relative_to(root)),
        "expected_usb_binding": incident["usb_binding"],
        "consumption_timing": "before any device or USB observation",
        "action": "odin4 --reboot only; no AP and no partition payload",
    }
    payload = json_record_bytes(record)
    durable_create_bytes_at_idempotent(
        guard_dir_fd,
        guard_path.name,
        payload,
        display_path=guard_path,
    )
    durable_create_bytes_at_idempotent(
        state_dir_fd,
        path.name,
        payload,
        display_path=path,
    )
    revalidate_bound_file_path(
        guard_dir_fd, guard_path.parent, guard_path.name, payload
    )
    revalidate_bound_file_path(state_dir_fd, path.parent, path.name, payload)
    revalidate_bound_directory(run_dir_fd, run_dir)
    return record


def live_run(root: Path, args: argparse.Namespace) -> int:
    offline = offline_check(root)
    policy = policy_status(root)
    if not policy["active"] or args.ack != LIVE_ACK:
        raise RecoveryError("no-AP reboot recovery policy or acknowledgement is inactive")
    if offline["recovery_consumed"]:
        raise RecoveryError("no-AP reboot recovery one-shot is already consumed")

    started = core.utc_now()
    run_dir = allocate_recovery_run_dir(root)
    run_dir_fd = open_bound_directory(root, run_dir)
    state_dir = root / RECOVERY_STATE.parent
    guard_dir = recovery_guard_path(root).parent
    try:
        state_dir_fd = open_bound_directory(root, state_dir)
    except BaseException:
        close_noexcept(run_dir_fd)
        raise
    try:
        guard_dir_fd = open_bound_directory(root, guard_dir)
    except BaseException:
        close_noexcept(state_dir_fd)
        close_noexcept(run_dir_fd)
        raise
    try:
        outcome = live_run_bound(
            root,
            args,
            offline=offline,
            policy=policy,
            started=started,
            run_dir=run_dir,
            run_dir_fd=run_dir_fd,
            state_dir_fd=state_dir_fd,
            guard_dir_fd=guard_dir_fd,
        )
    finally:
        close_noexcept(guard_dir_fd)
        close_noexcept(state_dir_fd)
        close_noexcept(run_dir_fd)
    return outcome


def live_run_bound(
    root: Path,
    args: argparse.Namespace,
    *,
    offline: dict[str, Any],
    policy: dict[str, Any],
    started: str,
    run_dir: Path,
    run_dir_fd: int,
    state_dir_fd: int,
    guard_dir_fd: int,
) -> int:
    result_path = run_dir / "result.json"
    timeline_path = run_dir / "timeline.json"
    stdout_path = run_dir / "odin-reboot.stdout"
    stderr_path = run_dir / "odin-reboot.stderr"
    attempt_path = run_dir / "odin-reboot-attempt.json"
    outcome_path = run_dir / "odin-reboot-outcome.json"
    enumeration_outcomes: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_live_v1",
        "target": TARGET,
        "mode": "no-ap-reboot-only",
        "verdict": "INCOMPLETE",
        "incident": offline["incident"],
        "device_writes": False,
        "partition_write": False,
        "odin_transfer": False,
        "flash": False,
        "reboot": None,
        "no_odin_endpoint": None,
        "reboot_attempted": False,
        "reboot_command_returned": False,
        "odin_enumerations": enumeration_outcomes,
        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
    }

    odin = (root / args.odin).resolve() if not args.odin.is_absolute() else args.odin
    reboot_start: str | None = None
    reboot_done: str | None = None
    ready: str | None = None
    timeline_attempted: list[dict[str, str]] | None = None
    try:
        if odin != connected.DEFAULT_ODIN:
            raise RecoveryError("no-AP recovery requires the exact default Odin path")
        if offline_check(root) != offline:
            raise RecoveryError("host evidence changed before recovery consumption")
        state = create_recovery_state(
            root,
            run_dir_fd=run_dir_fd,
            state_dir_fd=state_dir_fd,
            guard_dir_fd=guard_dir_fd,
            policy=policy,
            incident=offline["incident"],
            run_dir=run_dir,
            helper=offline["helper"],
            test=offline["test"],
            dependencies=offline["dependencies"],
            policy_draft=offline["policy_draft"],
        )
        result["recovery_state"] = state
        state_path = root / RECOVERY_STATE
        guard_path = recovery_guard_path(root)
        state_payload = json_record_bytes(state)
        revalidate_bound_file_path(
            state_dir_fd, state_path.parent, state_path.name, state_payload
        )
        revalidate_bound_file_path(
            guard_dir_fd, guard_path.parent, guard_path.name, state_payload
        )
        revalidate_bound_directory(run_dir_fd, run_dir)
        with measured.pinned_odin_session(odin) as (odin_fd, external_odin):
            enumeration_runner = sealed_enumeration_runner(
                odin_fd,
                external_odin,
                output_dir_fd=run_dir_fd,
                output_dir=run_dir,
                outcomes=enumeration_outcomes,
            )
            with odin_core.transaction_session(run_dir) as lease:
                ticket, sequence = wait_for_endpoint_hardened(
                    external_odin,
                    run_dir,
                    timeout_sec=args.endpoint_wait_sec,
                    sequence=0,
                    lease=lease,
                    expected_usb_binding=dict(offline["incident"]["usb_binding"]),
                    runner=enumeration_runner,
                )
                usb = measured.require_ticket_usb_binding(
                    ticket, dict(offline["incident"]["usb_binding"])
                )
                device, sequence, revalidation = revalidate_ticket_hardened(
                    external_odin,
                    run_dir,
                    ticket,
                    sequence=sequence,
                    lease=lease,
                    runner=enumeration_runner,
                )
                if measured.require_ticket_usb_binding(
                    ticket, dict(offline["incident"]["usb_binding"])
                ) != usb:
                    raise RecoveryError("Download USB binding changed before reboot")
                reboot_start = core.utc_now()
                command_shape = ["<sealed-odin-fd>", "--reboot", "-d", device]
                attempt_value = {
                    "schema": "s22plus_fyg8_r4w1c2_noap_reboot_attempt_v1",
                    "created_at_utc": reboot_start,
                    "attempted": True,
                    "operator_attestation_ack": LIVE_ACK,
                    "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
                    "command_shape": command_shape,
                    "ticket": measured._ticket_payload(ticket),
                    "usb_binding": usb,
                    "device_writes": False,
                    "partition_write": False,
                    "odin_transfer": False,
                    "flash": False,
                }
                durable_create_json_at_idempotent(
                    run_dir_fd,
                    attempt_path.name,
                    attempt_value,
                    display_path=attempt_path,
                )
                revalidate_bound_file_path(
                    state_dir_fd, state_path.parent, state_path.name, state_payload
                )
                revalidate_bound_file_path(
                    guard_dir_fd, guard_path.parent, guard_path.name, state_payload
                )
                revalidate_bound_file_path(
                    run_dir_fd,
                    run_dir,
                    attempt_path.name,
                    json_record_bytes(attempt_value),
                )
                result["reboot_attempted"] = True
                completed, command, lines = run_noap_odin(
                    odin_fd,
                    device,
                    output_dir_fd=run_dir_fd,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    outcome_path=outcome_path,
                )
                reboot_done = core.utc_now()
                result["reboot_command_returned"] = True
                serial, android = measured.wait_magisk_android(
                    args.android_wait_sec,
                    expected_serial=str(offline["incident"]["android_serial"]),
                    expected_usb_binding=dict(offline["incident"]["usb_binding"]),
                )
                ready = core.utc_now()
                result.update(
                    {
                        "reboot": True,
                        "android_serial": serial,
                        "final_android": android,
                    }
                )
                absence = odin_core.wait_for_no_live_endpoint(
                    external_odin,
                    run_dir,
                    timeout_sec=args.odin_absence_wait_sec,
                    sequence_start=sequence,
                    poll_sec=0.1,
                    lease=lease,
                    runner=enumeration_runner,
                    endpoint_observer_factory=odin_core.measured_usbfs_observer,
                )
                if not absence.absent or absence.timed_out:
                    result["no_odin_endpoint"] = False
                    raise RecoveryError("exact Android return retained an Odin endpoint")
                result["no_odin_endpoint"] = True
                timeline = exact_timeline(started, reboot_start, reboot_done, ready)
                result.update(
                    {
                        "verdict": PASS_VERDICT,
                        "device_writes": False,
                        "partition_write": False,
                        "odin_transfer": False,
                        "flash": False,
                        "reboot": True,
                        "ticket": measured._ticket_payload(ticket),
                        "usb_binding": usb,
                        "endpoint_revalidation": revalidation,
                        "command_shape": command_shape,
                        "command_argument_count": len(command),
                        "ap_argument_present": False,
                        "odin": {
                            "returncode": completed.returncode,
                            "attempt": existing_record_at(
                                run_dir_fd,
                                attempt_path.name,
                                display_path=attempt_path.relative_to(root),
                            ),
                            "outcome": existing_record_at(
                                run_dir_fd,
                                outcome_path.name,
                                display_path=outcome_path.relative_to(root),
                            ),
                            "stdout": existing_record_at(
                                run_dir_fd,
                                stdout_path.name,
                                display_path=stdout_path.relative_to(root),
                                maximum=MAX_ODIN_OUTPUT,
                            ),
                            "stderr": existing_record_at(
                                run_dir_fd,
                                stderr_path.name,
                                display_path=stderr_path.relative_to(root),
                                maximum=MAX_ODIN_OUTPUT,
                            ),
                            "lines": lines,
                        },
                        "android_serial": serial,
                        "final_android": android,
                        "no_odin_endpoint": True,
                        "timeline_phase_semantics": {
                            "candidate_flash_start": "zero-action recovery placeholder",
                            "candidate_flash_done": "zero-action recovery placeholder",
                            "candidate_boot_ready": "zero-action recovery placeholder",
                            "rollback_flash_start": "no-AP reboot command start; no flash",
                            "rollback_flash_done": "no-AP reboot command return; no flash",
                        },
                    }
                )
        # Both child/session contexts must close before any canonical PASS exists.
        revalidate_bound_file_path(
            state_dir_fd, state_path.parent, state_path.name, state_payload
        )
        revalidate_bound_file_path(
            guard_dir_fd, guard_path.parent, guard_path.name, state_payload
        )
        revalidate_bound_file_path(
            run_dir_fd,
            run_dir,
            attempt_path.name,
            json_record_bytes(attempt_value),
        )
        revalidate_bound_directory(run_dir_fd, run_dir)
        timeline_attempted = timeline
        timeline_value = {"events": timeline}
        durable_create_json_at_idempotent(
            run_dir_fd,
            timeline_path.name,
            timeline_value,
            display_path=timeline_path,
        )
        result["timeline"] = {
            "path": str(timeline_path.relative_to(root)),
            "events": timeline,
        }
        # Result is the final load-bearing write. Nothing fallible follows it.
        revalidate_bound_file_path(
            state_dir_fd, state_path.parent, state_path.name, state_payload
        )
        revalidate_bound_file_path(
            guard_dir_fd, guard_path.parent, guard_path.name, state_payload
        )
        revalidate_bound_file_path(
            run_dir_fd,
            run_dir,
            timeline_path.name,
            json_record_bytes(timeline_value),
        )
        durable_create_json_at_idempotent(
            run_dir_fd,
            result_path.name,
            result,
            display_path=result_path,
        )
        emit_summary({"run_dir": str(run_dir), "verdict": PASS_VERDICT})
        return 0
    except Exception as exc:
        ended = core.utc_now()
        attempt: dict[str, Any] | None = None
        outcome: dict[str, Any] | None = None
        if leaf_exists_at(run_dir_fd, attempt_path.name):
            attempt = parse_json_at(run_dir_fd, attempt_path.name, "reboot attempt")
        if leaf_exists_at(run_dir_fd, outcome_path.name):
            outcome = parse_json_at(run_dir_fd, outcome_path.name, "reboot outcome")
        if attempt is not None:
            reboot_start = str(attempt.get("created_at_utc") or reboot_start or ended)
            result["reboot_attempted"] = attempt.get("attempted") is True
        if outcome is not None:
            reboot_done = str(outcome.get("created_at_utc") or reboot_done or ended)
            result["reboot_command_returned"] = outcome.get("returned") is True
        failure_timeline = exact_timeline(
            started,
            reboot_start or ended,
            reboot_done or ended,
            ready or ended,
            ended,
        )
        result["verdict"] = FAIL_VERDICT
        result["error"] = str(exc)
        result["recovery_consumed"] = leaf_exists_at(
            state_dir_fd, RECOVERY_STATE.name
        ) or leaf_exists_at(guard_dir_fd, recovery_guard_path(root).name)
        result["reboot"] = True if ready is not None else None
        result["odin_attempt"] = attempt
        result["odin_outcome"] = outcome
        result["timeline_phase_semantics"] = {
            "candidate_flash_start": "zero-action recovery placeholder",
            "candidate_flash_done": "zero-action recovery placeholder",
            "candidate_boot_ready": "zero-action recovery placeholder",
            "rollback_flash_start": (
                "no-AP reboot attempted; no flash"
                if result["reboot_attempted"]
                else "no reboot attempt; no flash"
            ),
            "rollback_flash_done": (
                "no-AP reboot command returned; no flash"
                if result["reboot_command_returned"]
                else "no command return observed; no flash"
            ),
            "rollback_boot_ready": (
                "exact Android ready"
                if ready is not None
                else "exact Android readiness not proven"
            ),
        }
        if leaf_exists_at(run_dir_fd, timeline_path.name):
            if timeline_attempted is None:
                raise RecoveryError("unexpected timeline appeared before publication")
            timeline = timeline_attempted
        else:
            timeline = failure_timeline
            timeline_attempted = timeline
        timeline_publication_error: str | None = None
        try:
            durable_create_json_at_idempotent(
                run_dir_fd,
                timeline_path.name,
                {"events": timeline},
                display_path=timeline_path,
            )
        except (OSError, RecoveryError) as publication_exc:
            timeline_publication_error = str(publication_exc)
            result["timeline_publication_error"] = timeline_publication_error
        result["timeline"] = {
            "path": str(timeline_path.relative_to(root)),
            "events": timeline,
        }
        durable_create_json_at_idempotent(
            run_dir_fd,
            result_path.name,
            result,
            display_path=result_path,
        )
        if timeline_publication_error is not None:
            raise RecoveryError(
                "failure result recorded but canonical timeline publication failed: "
                + timeline_publication_error
            )
        emit_summary({"run_dir": str(run_dir), "verdict": FAIL_VERDICT})
        return 20


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--live", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--odin", type=Path, default=connected.DEFAULT_ODIN)
    parser.add_argument("--endpoint-wait-sec", type=float, default=120.0)
    parser.add_argument("--android-wait-sec", type=float, default=300.0)
    parser.add_argument("--odin-absence-wait-sec", type=float, default=15.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        if args.offline_check:
            print(json.dumps(offline_check(root), indent=2, sort_keys=True))
            return 0
        return live_run(root, args)
    except (RecoveryError, measured.GateError, connected.GateError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
