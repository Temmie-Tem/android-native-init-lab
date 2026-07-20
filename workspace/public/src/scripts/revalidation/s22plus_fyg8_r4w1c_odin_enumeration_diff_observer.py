#!/usr/bin/env python3
"""Observe one Odin listing across exact S22+ Download-node snapshots.

The observer owns no boot artifact, transfer command, candidate execution, or
rollback surface. Its future attended mode may request normal Download, execute
exactly one bounded ``odin4 -l``, persist complete before/after host evidence,
and wait for the same Android target to return. This source is inert until an
exact independently reviewed policy clause is ACTIVE in ``AGENTS.md``.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import fcntl
import functools
import hashlib
import json
import math
import os
import re
import selectors
import shlex
import signal
import stat
import subprocess
import sys
import termios
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA = "s22plus_fyg8_r4w1c_odin_enumeration_diff_observer_v1"
CONSUMED_SCHEMA = "s22plus_fyg8_r4w1c_odin_enumeration_diff_consumed_v1"
RECOVERY_INTENT_SCHEMA = (
    "s22plus_fyg8_r4w1c_odin_enumeration_diff_recovery_intent_v1"
)
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.py"
)
TEST_RELATIVE = Path(
    "tests/test_s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.py"
)
POLICY_DRAFT = Path(
    "docs/operations/"
    "S22PLUS_FYG8_R4W1C_ODIN_ENUMERATION_DIFF_OBSERVER_EXCEPTION_DRAFT_2026-07-20.md"
)
POLICY_MARKER = "S22+ FYG8 R4W1-C Odin enumeration-diff observation gate"
ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1C_ENUM_DIFF_OBSERVER_POLICY_STATE=ACTIVE"
POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C_ENUM_DIFF_OBSERVER_POLICY_V1"
POLICY_END = "END_S22PLUS_FYG8_R4W1C_ENUM_DIFF_OBSERVER_POLICY_V1"
POLICY_HASH_PREFIX = "S22PLUS_FYG8_R4W1C_ENUM_DIFF_POLICY_CLAUSE_SHA256="
OBSERVE_ACK_TOKEN = "S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-OBSERVE"
DOWNLOAD_CONFIRM_TOKEN = (
    "S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-NORMAL-DOWNLOAD-CONFIRMED"
)
RECOVERY_ACK_TOKEN = (
    "S22PLUS-FYG8-R4W1C-ODIN-ENUMERATION-DIFF-RECOVER-CONSUMED-OBSERVER"
)

EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_BUILD = "S906NKSS7FYG8"
EXPECTED_ANDROID_USB_PRODUCT = "6860"
EXPECTED_DOWNLOAD_USB_PRODUCT = "685d"
EXPECTED_DOWNLOAD_PRODUCT_TEXT = "SAMSUNG USB"
EXPECTED_DOWNLOAD_MANUFACTURER = "Samsung"
EXPECTED_MAGISK_BOOT_SHA256 = (
    "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
)
EXPECTED_VENDOR_BOOT_SHA256 = (
    "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7"
)
EXPECTED_DTBO_SHA256 = (
    "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
)
EXPECTED_RECOVERY_SHA256 = (
    "93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4"
)
EXPECTED_ODIN_SIZE = 3_746_744
EXPECTED_ODIN_SHA256 = (
    "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
)

DEFAULT_ODIN = Path("/usr/bin/odin4")
RUN_ROOT = Path("workspace/private/runs")
CONSUMED_STATE = Path(
    "workspace/private/state/"
    "s22plus_fyg8_r4w1c_odin_enumeration_diff_observer_consumed.json"
)
AUTHORITY_LOCK = Path(
    "workspace/private/state/"
    ".s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.lock"
)
USB_SYSFS_ROOT = Path("/sys/bus/usb/devices")
USBFS_ROOT = Path("/dev/bus/usb")
STAT_BINARY = Path("/usr/bin/stat")
ODIN_DEVICE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])/dev/bus/usb/[0-9]{3}/[0-9]{3}(?![A-Za-z0-9_./-])"
)
TOPOLOGY_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
SERIAL_RE = re.compile(r"[A-Z0-9]{10,16}")
UTC_RE = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z")

MAX_COMMAND_OUTPUT = 64 * 1024
MAX_INVENTORY_ENTRIES = 4096
MAX_JSON_BYTES = 4 * 1024 * 1024
STABLE_SAMPLE_COUNT = 3
STABLE_POLL_SEC = 0.25
TIMELINE_NAMES = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
IMMUTABLE_NODE_FIELDS = (
    "path",
    "st_dev",
    "st_ino",
    "st_rdev",
    "st_nlink",
    "device_major",
    "device_minor",
    "birth_time_ns",
)


class ObserverError(RuntimeError):
    pass


class BoundedCommandError(ObserverError):
    def __init__(
        self,
        message: str,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
        timed_out: bool = False,
        output_truncated: bool = False,
        cleanup_error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.output_truncated = output_truncated
        self.cleanup_error = cleanup_error


class CommandInterruption(BaseException):
    def __init__(
        self,
        original: BaseException,
        *,
        stdout: bytes,
        stderr: bytes,
        cleanup_error: str | None = None,
    ) -> None:
        super().__init__(str(original))
        self.original = original
        self.stdout = stdout
        self.stderr = stderr
        self.cleanup_error = cleanup_error


@dataclass(eq=False)
class AuthorityLease:
    root: Path
    owner_pid: int
    owner_thread: int
    receipt: dict[str, str]
    pinned_files: dict[str, tuple[int, tuple[int, int, int], str]]
    lock_descriptor: int
    lock_identity: tuple[int, int]


@dataclass(eq=False)
class ConsumedStatePin:
    path: Path
    descriptor: int
    identity: tuple[int, int, int]
    sha256: str


_ACTIVE_AUTHORITY_LEASES: set[AuthorityLease] = set()
_ACTIVE_AUTHORITY_LEASES_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@contextlib.contextmanager
def termination_signals_deferred():
    signals = {signal.SIGINT, signal.SIGTERM, signal.SIGHUP}
    old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)


def defer_termination_signals(function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        with termination_signals_deferred():
            return function(*args, **kwargs)

    return wrapped


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise ObserverError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else (root / value).resolve()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_fd(descriptor: int) -> str:
    digest = hashlib.sha256()
    offset = 0
    while True:
        chunk = os.pread(descriptor, 1024 * 1024, offset)
        if not chunk:
            return digest.hexdigest()
        digest.update(chunk)
        offset += len(chunk)


def executable_fd_identity(descriptor: int) -> dict[str, Any]:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ObserverError("Odin4 descriptor is not one linked regular file")
    identity = {
        "path": str(DEFAULT_ODIN),
        "st_dev": metadata.st_dev,
        "st_ino": metadata.st_ino,
        "st_mode": stat.S_IMODE(metadata.st_mode),
        "st_uid": metadata.st_uid,
        "st_gid": metadata.st_gid,
        "size": metadata.st_size,
        "sha256": sha256_fd(descriptor),
    }
    if identity["size"] != EXPECTED_ODIN_SIZE or identity["sha256"] != EXPECTED_ODIN_SHA256:
        raise ObserverError("Odin4 descriptor identity mismatch")
    return identity


def require_path_matches_fd(path: Path, descriptor: int) -> None:
    path_metadata = os.stat(path, follow_symlinks=False)
    fd_metadata = os.fstat(descriptor)
    if not stat.S_ISREG(path_metadata.st_mode) or (
        path_metadata.st_dev,
        path_metadata.st_ino,
        path_metadata.st_size,
    ) != (fd_metadata.st_dev, fd_metadata.st_ino, fd_metadata.st_size):
        raise ObserverError("Odin4 pathname no longer names the verified descriptor")


@contextlib.contextmanager
def open_verified_odin(path: Path = DEFAULT_ODIN):
    if path != DEFAULT_ODIN or path.is_symlink():
        raise ObserverError("only exact direct /usr/bin/odin4 is permitted")
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        identity = executable_fd_identity(descriptor)
        require_path_matches_fd(path, descriptor)
        yield descriptor, identity
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require_direct_directory(path: Path) -> os.stat_result:
    metadata = os.stat(path, follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode) or path.is_symlink():
        raise ObserverError(f"evidence parent is not a direct directory: {path}")
    return metadata


def require_direct_directory_chain(root: Path, path: Path) -> None:
    root = Path(os.path.abspath(root))
    path = Path(os.path.abspath(path))
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ObserverError(f"path escapes repository root: {path}") from exc
    require_direct_directory(root)
    current = root
    for part in relative.parts:
        current /= part
        require_direct_directory(current)


def json_bytes(value: Any) -> bytes:
    payload = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    if len(payload) > MAX_JSON_BYTES:
        raise ObserverError("JSON evidence exceeds bound")
    return payload


def durable_create_bytes(path: Path, payload: bytes) -> dict[str, Any]:
    if len(payload) > MAX_JSON_BYTES:
        raise ObserverError("evidence payload exceeds bound")
    require_direct_directory(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o400)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ObserverError(f"evidence target is not a private regular file: {path}")
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise ObserverError(f"short evidence write: {path}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)
    return {"path": str(path), "size": len(payload), "sha256": sha256_bytes(payload)}


def durable_create_json(path: Path, value: Any) -> dict[str, Any]:
    return durable_create_bytes(path, json_bytes(value))


def read_direct_json(path: Path) -> dict[str, Any]:
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > MAX_JSON_BYTES
        ):
            raise ObserverError(f"JSON evidence shape is invalid: {path}")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        after = os.fstat(descriptor)
        if (
            len(payload) != before.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise ObserverError(f"JSON evidence changed while reading: {path}")
    finally:
        os.close(descriptor)
    value = json.loads(bytes(payload))
    if not isinstance(value, dict):
        raise ObserverError(f"JSON evidence root is not an object: {path}")
    return value


def durable_replace_json(path: Path, value: Any) -> None:
    payload = json_bytes(value)
    require_direct_directory(path.parent)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise ObserverError(f"short timeline write: {temporary}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def allocate_run_dir(root: Path, requested: Path | None = None) -> Path:
    base = Path(os.path.abspath(root / RUN_ROOT))
    require_direct_directory_chain(root, base)
    run_dir = (
        Path(os.path.abspath(root / requested))
        if requested is not None and not requested.is_absolute()
        else Path(os.path.abspath(requested))
        if requested is not None
        else base / f"s22plus-r4w1c-enum-diff-{utc_stamp()}"
    )
    if run_dir.parent != base:
        raise ObserverError("run directory must be one direct child of private run root")
    try:
        run_dir.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ObserverError(f"run directory already exists: {run_dir}") from exc
    _fsync_directory(run_dir.parent)
    require_direct_directory(run_dir)
    return run_dir


def append_timeline(path: Path, events: list[dict[str, str]], name: str) -> None:
    if name not in TIMELINE_NAMES:
        raise ObserverError(f"unknown timeline event: {name}")
    expected = TIMELINE_NAMES[len(events)] if len(events) < len(TIMELINE_NAMES) else None
    if name != expected:
        raise ObserverError(f"noncanonical timeline event: {name} != {expected}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    durable_replace_json(path, {"events": events})


def complete_timeline(path: Path, events: list[dict[str, str]]) -> None:
    while len(events) < len(TIMELINE_NAMES):
        append_timeline(path, events, TIMELINE_NAMES[len(events)])


def timeline_event_status(actual_names: list[str]) -> dict[str, str]:
    actual = set(actual_names)
    return {
        name: "reached" if name in actual else "not-reached-no-action-placeholder"
        for name in TIMELINE_NAMES
    }


def validate_actual_timeline_names(value: Any) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(name, str) for name in value)
        or value != list(TIMELINE_NAMES[: len(value)])
        or (value and value[-1] == "live_session_end")
    ):
        raise ObserverError("actual timeline event semantics are invalid")
    return value


def recovery_original_actual_events(
    run_dir: Path, timeline_events: list[dict[str, str]]
) -> list[str]:
    for name in ("result.json", "result-preclosure.json"):
        path = run_dir / name
        if not path.exists():
            continue
        record = read_direct_json(path)
        if name == "result.json" and record.get("verdict") == (
            "PASS_R4W1C_ENUM_DIFF_OBSERVER_EVIDENCE_CAPTURED"
        ):
            raise ObserverError("observer result already passed and needs no recovery")
        return validate_actual_timeline_names(record.get("actual_timeline_events"))
    if len(timeline_events) == len(TIMELINE_NAMES):
        raise ObserverError("completed timeline lacks durable actual-event semantics")
    return validate_actual_timeline_names(
        [str(event["name"]) for event in timeline_events]
    )


def preclosure_result(result: dict[str, Any], *, successful: bool) -> dict[str, Any]:
    pending = dict(result)
    pending["verdict"] = "PENDING_FINAL_AUTHORITY_VALIDATION"
    pending["outcome_class"] = "successful-evidence" if successful else "incomplete"
    return pending


def validate_timeline_prefix(value: dict[str, Any]) -> list[dict[str, str]]:
    if set(value) != {"events"} or not isinstance(value["events"], list):
        raise ObserverError("timeline schema is invalid")
    events = value["events"]
    if len(events) > len(TIMELINE_NAMES):
        raise ObserverError("timeline has too many events")
    for index, event in enumerate(events):
        if (
            not isinstance(event, dict)
            or set(event) != {"name", "timestamp_utc"}
            or event["name"] != TIMELINE_NAMES[index]
            or UTC_RE.fullmatch(str(event["timestamp_utc"])) is None
        ):
            raise ObserverError("timeline prefix is invalid")
    return events


def terminate_process_group(process: subprocess.Popen[bytes], timeout_sec: float = 2.0) -> None:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise ObserverError("process cleanup bound is invalid")
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        raise ObserverError("command process group did not terminate within bound") from exc


def run_bounded(
    argv: list[str],
    timeout_sec: float,
    *,
    maximum: int = MAX_COMMAND_OUTPUT,
    executable_fd: int | None = None,
) -> subprocess.CompletedProcess[bytes]:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0 or maximum <= 0:
        raise ObserverError("command bound is invalid")
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    chunks: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    total = 0
    deadline = time.monotonic() + timeout_sec
    def payloads() -> tuple[bytes, bytes]:
        return b"".join(chunks["stdout"]), b"".join(chunks["stderr"])

    def append_chunk(channel: str, chunk: bytes) -> None:
        nonlocal total
        available = maximum - total
        if len(chunk) > available:
            if available > 0:
                chunks[channel].append(chunk[:available])
                total += available
            stdout, stderr = payloads()
            raise BoundedCommandError(
                "command output exceeds bound",
                stdout=stdout,
                stderr=stderr,
                output_truncated=True,
            )
        chunks[channel].append(chunk)
        total += len(chunk)

    popen_options: dict[str, Any] = {}
    if executable_fd is not None:
        metadata = os.fstat(executable_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ObserverError("verified executable descriptor is not regular")
        popen_options = {
            "executable": f"/proc/self/fd/{executable_fd}",
            "pass_fds": (executable_fd,),
        }
    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
            **popen_options,
        )
        selector = selectors.DefaultSelector()
        assert process.stdout is not None and process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout_sec)
            ready = selector.select(remaining)
            if not ready:
                raise subprocess.TimeoutExpired(argv, timeout_sec)
            for key, _mask in ready:
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                append_chunk(str(key.data), chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, timeout_sec)
        returncode = process.wait(timeout=remaining)
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = payloads()
        cleanup_error = None
        if process is not None:
            try:
                terminate_process_group(process)
            except BaseException as cleanup_exc:
                cleanup_error = f"{type(cleanup_exc).__name__}: {cleanup_exc}"
        raise BoundedCommandError(
            f"command timed out after {timeout_sec} seconds",
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            output_truncated=total >= maximum,
            cleanup_error=cleanup_error,
        ) from exc
    except BoundedCommandError as exc:
        if process is not None:
            try:
                terminate_process_group(process)
            except BaseException as cleanup_exc:
                exc.cleanup_error = f"{type(cleanup_exc).__name__}: {cleanup_exc}"
        raise
    except BaseException as exc:
        stdout, stderr = payloads()
        cleanup_error = None
        if process is not None:
            try:
                terminate_process_group(process)
            except BaseException as cleanup_exc:
                cleanup_error = f"{type(cleanup_exc).__name__}: {cleanup_exc}"
        raise CommandInterruption(
            exc,
            stdout=stdout,
            stderr=stderr,
            cleanup_error=cleanup_error,
        ) from exc
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
    return subprocess.CompletedProcess(
        argv,
        returncode,
        stdout=payloads()[0],
        stderr=payloads()[1],
    )


def command_text(
    argv: list[str], timeout_sec: float, *, maximum: int = MAX_COMMAND_OUTPUT
) -> tuple[int, str, str]:
    result = run_bounded(argv, timeout_sec, maximum=maximum)
    return (
        result.returncode,
        result.stdout.decode("utf-8", "replace"),
        result.stderr.decode("utf-8", "replace"),
    )


def require_command_text(argv: list[str], timeout_sec: float) -> str:
    returncode, stdout, stderr = command_text(argv, timeout_sec)
    if returncode != 0 or stderr:
        raise ObserverError(f"command failed: {argv[0]}")
    return stdout.strip()


def adb_serial() -> str:
    output = require_command_text(["adb", "devices", "-l"], 10.0)
    serials: list[str] = []
    for line in output.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "device":
            serials.append(fields[0])
    if len(serials) != 1 or SERIAL_RE.fullmatch(serials[0]) is None:
        raise ObserverError(f"expected one exact Android device, found {len(serials)}")
    return serials[0]


def adb_shell(serial: str, command: str, *, root: bool = False, timeout: float = 30.0) -> str:
    argv = ["adb", "-s", serial, "shell"]
    if root:
        argv.extend(["su", "-c", shlex.quote(command)])
    else:
        argv.append(command)
    return require_command_text(argv, timeout)


def parse_sha256(value: str, label: str) -> str:
    fields = value.split()
    if not fields or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
        raise ObserverError(f"malformed SHA256: {label}")
    return fields[0]


def android_state() -> tuple[str, dict[str, str]]:
    serial = adb_serial()
    values = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "incremental": adb_shell(serial, "getprop ro.build.version.incremental"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "bootanim": adb_shell(serial, "getprop init.svc.bootanim"),
        "verified_boot_state": adb_shell(serial, "getprop ro.boot.verifiedbootstate"),
        "root": adb_shell(serial, "id", root=True),
        "boot_sha256": parse_sha256(
            adb_shell(serial, "sha256sum /dev/block/by-name/boot", root=True, timeout=90),
            "boot",
        ),
        "vendor_boot_sha256": parse_sha256(
            adb_shell(
                serial,
                "sha256sum /dev/block/by-name/vendor_boot",
                root=True,
                timeout=90,
            ),
            "vendor_boot",
        ),
        "dtbo_sha256": parse_sha256(
            adb_shell(serial, "sha256sum /dev/block/by-name/dtbo", root=True, timeout=60),
            "dtbo",
        ),
        "recovery_sha256": parse_sha256(
            adb_shell(
                serial,
                "sha256sum /dev/block/by-name/recovery",
                root=True,
                timeout=90,
            ),
            "recovery",
        ),
    }
    expected = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "bootloader": EXPECTED_BUILD,
        "incremental": EXPECTED_BUILD,
        "boot_completed": "1",
        "bootanim": "stopped",
        "verified_boot_state": "orange",
        "boot_sha256": EXPECTED_MAGISK_BOOT_SHA256,
        "vendor_boot_sha256": EXPECTED_VENDOR_BOOT_SHA256,
        "dtbo_sha256": EXPECTED_DTBO_SHA256,
        "recovery_sha256": EXPECTED_RECOVERY_SHA256,
    }
    for name, expected_value in expected.items():
        if values[name] != expected_value:
            raise ObserverError(f"Android identity mismatch: {name}")
    if "uid=0(root)" not in values["root"]:
        raise ObserverError("Magisk root is absent")
    values["root"] = "uid=0(root)"
    return serial, values


def read_sysfs_text(path: Path, *, allow_missing: bool = False) -> str | None:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    if len(payload) > 4096:
        raise ObserverError(f"sysfs value exceeds bound: {path}")
    return payload.decode("utf-8", "strict").strip()


def android_usb_binding(serial: str) -> dict[str, str]:
    devpath = require_command_text(["adb", "-s", serial, "get-devpath"], 10.0)
    remote_serial = require_command_text(["adb", "-s", serial, "get-serialno"], 10.0)
    if remote_serial != serial or not devpath.startswith("usb:"):
        raise ObserverError("Android ADB serial or devpath mismatch")
    topology = devpath.removeprefix("usb:")
    if TOPOLOGY_RE.fullmatch(topology) is None:
        raise ObserverError("Android USB topology is malformed")
    first = android_sysfs_identity(topology)
    second = android_sysfs_identity(topology)
    if first != second or first["serial"] != serial:
        raise ObserverError("Android USB sysfs identity mismatch")
    return {
        "topology": topology,
        "android_serial_sha256": sha256_bytes(serial.encode("ascii")),
        "download_serial_state": "absent",
    }


def android_sysfs_identity(topology: str) -> dict[str, str]:
    sysfs = USB_SYSFS_ROOT / topology
    identity = {
        "vendor": str(read_sysfs_text(sysfs / "idVendor")),
        "product": str(read_sysfs_text(sysfs / "idProduct")),
        "serial": str(read_sysfs_text(sysfs / "serial")),
        "busnum": str(read_sysfs_text(sysfs / "busnum")),
        "devnum": str(read_sysfs_text(sysfs / "devnum")),
        "devpath": str(read_sysfs_text(sysfs / "devpath")),
    }
    if (
        identity["vendor"] != "04e8"
        or identity["product"] != EXPECTED_ANDROID_USB_PRODUCT
        or identity["devpath"] != topology.split("-", 1)[1]
        or not identity["busnum"].isdigit()
        or not identity["devnum"].isdigit()
    ):
        raise ObserverError("Android USB sysfs descriptors mismatch")
    return identity


def download_sysfs_inventory_evidence(
    *, root: Path | None = None
) -> dict[str, Any]:
    root = USB_SYSFS_ROOT if root is None else root
    entries: dict[str, dict[str, str]] = {}
    races: list[str] = []
    errors: list[dict[str, str]] = []
    try:
        root_metadata = os.stat(root, follow_symlinks=False)
        if not stat.S_ISDIR(root_metadata.st_mode):
            return {
                "entries": entries,
                "races": races,
                "errors": [
                    {"path": str(root), "error": "Download sysfs root is not a directory"}
                ],
            }
        paths = sorted(root.iterdir())
    except FileNotFoundError:
        return {
            "entries": entries,
            "races": races,
            "errors": [{"path": str(root), "error": "Download sysfs root is absent"}],
        }
    except OSError as exc:
        return {
            "entries": entries,
            "races": races,
            "errors": [{"path": str(root), "error": f"{type(exc).__name__}: {exc}"}],
        }
    for path in paths:
        if TOPOLOGY_RE.fullmatch(path.name) is None:
            continue
        try:
            vendor = read_sysfs_text(path / "idVendor", allow_missing=True)
            product = read_sysfs_text(path / "idProduct", allow_missing=True)
            if vendor is None or product is None:
                races.append(path.name)
                continue
            if vendor != "04e8" or product != EXPECTED_DOWNLOAD_USB_PRODUCT:
                continue
            identity = download_sysfs_identity(path.name)
            if identity is None:
                races.append(path.name)
                continue
            entries[path.name] = identity
        except (ObserverError, OSError, UnicodeError) as exc:
            errors.append({"path": path.name, "error": f"{type(exc).__name__}: {exc}"})
        if len(entries) + len(races) + len(errors) > 16:
            errors.append({"path": str(root), "error": "Download inventory exceeds bound"})
            break
    return {"entries": entries, "races": races, "errors": errors}


def download_endpoint_inventory() -> list[dict[str, str]]:
    evidence = download_sysfs_inventory_evidence()
    if evidence["races"] or evidence["errors"]:
        raise ObserverError("Download endpoint inventory is incomplete")
    return [evidence["entries"][name] for name in sorted(evidence["entries"])]


def download_sysfs_identity(topology: str) -> dict[str, str] | None:
    if TOPOLOGY_RE.fullmatch(topology) is None:
        raise ObserverError("Download topology is malformed")
    path = USB_SYSFS_ROOT / topology
    vendor = read_sysfs_text(path / "idVendor", allow_missing=True)
    product = read_sysfs_text(path / "idProduct", allow_missing=True)
    if vendor is None or product is None:
        return None
    if vendor != "04e8":
        raise ObserverError("bound topology is no longer Samsung")
    if product != EXPECTED_DOWNLOAD_USB_PRODUCT:
        return None
    serial = read_sysfs_text(path / "serial", allow_missing=True)
    identity = {
        "topology": topology,
        "vendor": vendor,
        "product": product,
        "product_text": str(read_sysfs_text(path / "product")),
        "manufacturer": str(read_sysfs_text(path / "manufacturer")),
        "busnum": str(read_sysfs_text(path / "busnum")),
        "devnum": str(read_sysfs_text(path / "devnum")),
        "devpath": str(read_sysfs_text(path / "devpath")),
        "serial_state": "absent" if serial is None else "present",
        "serial_sha256": None if serial is None else sha256_bytes(serial.encode()),
    }
    if (
        identity["product_text"] != EXPECTED_DOWNLOAD_PRODUCT_TEXT
        or identity["manufacturer"] != EXPECTED_DOWNLOAD_MANUFACTURER
        or identity["devpath"] != topology.split("-", 1)[1]
        or identity["serial_state"] != "absent"
    ):
        raise ObserverError("Download sysfs descriptor mismatch")
    if not identity["busnum"].isdigit() or not identity["devnum"].isdigit():
        raise ObserverError("Download bus or device number is malformed")
    return identity


def usbfs_path(identity: dict[str, Any]) -> str:
    return f"/dev/bus/usb/{int(identity['busnum']):03d}/{int(identity['devnum']):03d}"


def parse_birth_time_ns(value: str) -> int | None:
    match = re.fullmatch(
        r"(20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})"
        r"\.([0-9]{1,9}) ([+-][0-9]{4})",
        value,
    )
    if match is None:
        return None
    base, fraction, offset = match.groups()
    instant = datetime.strptime(f"{base} {offset}", "%Y-%m-%d %H:%M:%S %z")
    return int(instant.timestamp()) * 1_000_000_000 + int(fraction.ljust(9, "0"))


def birth_time_ns(path: str) -> int | None:
    returncode, stdout, stderr = command_text(
        [str(STAT_BINARY), "--printf=%w", "--", path], 5.0, maximum=1024
    )
    if returncode != 0 or stderr:
        raise ObserverError(f"birth-time read failed for USB endpoint: {path}")
    value = stdout.strip()
    if value == "-":
        return None
    parsed = parse_birth_time_ns(value)
    if parsed is None:
        raise ObserverError(f"birth-time output is malformed for USB endpoint: {path}")
    return parsed


def node_stat_tuple(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_rdev,
        metadata.st_nlink,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_atime_ns,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def node_snapshot(
    path: str, *, birth_reader: Callable[[str], int | None] = birth_time_ns
) -> dict[str, Any]:
    before = os.stat(path, follow_symlinks=False)
    if not stat.S_ISCHR(before.st_mode) or before.st_nlink != 1:
        raise ObserverError(f"USB endpoint is not a character device: {path}")
    birth = birth_reader(path)
    metadata = os.stat(path, follow_symlinks=False)
    if node_stat_tuple(metadata) != node_stat_tuple(before):
        raise ObserverError(f"USB endpoint changed around birth-time read: {path}")
    return {
        "path": path,
        "st_dev": metadata.st_dev,
        "st_ino": metadata.st_ino,
        "st_rdev": metadata.st_rdev,
        "st_nlink": metadata.st_nlink,
        "st_mode": stat.S_IMODE(metadata.st_mode),
        "st_uid": metadata.st_uid,
        "st_gid": metadata.st_gid,
        "st_atime_ns": metadata.st_atime_ns,
        "st_mtime_ns": metadata.st_mtime_ns,
        "st_ctime_ns": metadata.st_ctime_ns,
        "birth_time_ns": birth,
        "device_major": os.major(metadata.st_rdev),
        "device_minor": os.minor(metadata.st_rdev),
    }


def require_usbfs_relation(node: dict[str, Any], identity: dict[str, Any]) -> None:
    expected_path = usbfs_path(identity)
    expected_minor = (int(identity["busnum"]) - 1) * 128 + int(identity["devnum"]) - 1
    if (
        node.get("path") != expected_path
        or node.get("device_major") != 189
        or node.get("device_minor") != expected_minor
    ):
        raise ObserverError("usbfs node does not match Download sysfs identity")


def usbfs_inventory_evidence(
    *,
    root: Path | None = None,
    snapshotter: Callable[[str], dict[str, Any]] = node_snapshot,
) -> dict[str, Any]:
    root = USBFS_ROOT if root is None else root
    inventory: dict[str, dict[str, Any]] = {}
    races: list[str] = []
    errors: list[dict[str, str]] = []
    if not root.is_dir():
        return {
            "entries": inventory,
            "races": races,
            "errors": [{"path": str(root), "error": "usbfs root is absent"}],
        }
    try:
        paths = sorted(root.glob("[0-9][0-9][0-9]/[0-9][0-9][0-9]"))
    except OSError as exc:
        return {
            "entries": inventory,
            "races": races,
            "errors": [{"path": str(root), "error": f"{type(exc).__name__}: {exc}"}],
        }
    for path in paths:
        encoded = str(USBFS_ROOT / path.relative_to(root))
        if ODIN_DEVICE_RE.fullmatch(encoded) is None:
            continue
        try:
            inventory[encoded] = snapshotter(encoded)
        except FileNotFoundError:
            races.append(encoded)
        except (ObserverError, OSError) as exc:
            errors.append({"path": encoded, "error": f"{type(exc).__name__}: {exc}"})
        if len(inventory) + len(races) + len(errors) > MAX_INVENTORY_ENTRIES:
            errors.append({"path": str(root), "error": "usbfs inventory exceeds bound"})
            break
    return {"entries": inventory, "races": races, "errors": errors}


def usbfs_inventory() -> dict[str, dict[str, Any]]:
    evidence = usbfs_inventory_evidence()
    if evidence["races"] or evidence["errors"]:
        raise ObserverError("usbfs inventory is incomplete")
    return evidence["entries"]


def sample_bound_download(topology: str) -> dict[str, Any] | None:
    first = download_sysfs_identity(topology)
    if first is None:
        return None
    path = usbfs_path(first)
    try:
        before = node_snapshot(path)
    except FileNotFoundError:
        return None
    require_usbfs_relation(before, first)
    second = download_sysfs_identity(topology)
    if second != first:
        raise ObserverError("Download sysfs identity changed while sampling")
    after = node_snapshot(path)
    require_usbfs_relation(after, second)
    if after != before:
        raise ObserverError("Download node changed while sampling")
    return {"sysfs": first, "node": before}


def wait_for_stable_download(
    topology: str,
    timeout_sec: float,
    *,
    sampler: Callable[[str], dict[str, Any] | None] = sample_bound_download,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    on_sample: Callable[[int, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise ObserverError("Download stabilization timeout is invalid")
    started = monotonic()
    deadline = started + timeout_sec
    samples: list[dict[str, Any]] = []
    last: dict[str, Any] | None = None
    consecutive = 0
    while monotonic() < deadline:
        # A signal delivered after sampling but before the durable callback would
        # otherwise create an unrecorded observation. Keep that pair atomic.
        with termination_signals_deferred():
            sample = sampler(topology)
            if sample is not None:
                samples.append(sample)
                if on_sample is not None:
                    on_sample(len(samples), sample)
        if sample is None:
            if last is not None:
                raise ObserverError("Download endpoint disappeared while stabilizing")
            consecutive = 0
        else:
            if len(samples) > 128:
                raise ObserverError("Download stabilization sample bound exceeded")
            if last is None:
                consecutive = 1
            else:
                old = last["node"]
                new = sample["node"]
                if any(new[field] != old[field] for field in IMMUTABLE_NODE_FIELDS):
                    raise ObserverError("Download immutable node identity changed")
                consecutive = consecutive + 1 if sample == last else 1
            last = sample
            if consecutive >= STABLE_SAMPLE_COUNT:
                return {
                    "topology": topology,
                    "samples": samples,
                    "stable_sample": sample,
                    "stable_count": consecutive,
                    "elapsed_sec": round(monotonic() - started, 6),
                }
        sleep(min(STABLE_POLL_SEC, max(0.0, deadline - monotonic())))
    raise ObserverError("Download endpoint did not stabilize in time")


def capture_bundle(topology: str) -> dict[str, Any]:
    first = download_sysfs_inventory_evidence()
    inventory = usbfs_inventory_evidence()
    second = download_sysfs_inventory_evidence()
    errors: list[str] = []
    for label, evidence in (
        ("download-sysfs-before", first),
        ("usbfs", inventory),
        ("download-sysfs-after", second),
    ):
        if evidence["races"]:
            errors.append(f"{label}-races:{','.join(evidence['races'])}")
        for error in evidence["errors"]:
            errors.append(f"{label}-error:{error['path']}:{error['error']}")
    first_entries = first["entries"]
    second_entries = second["entries"]
    if sorted(first_entries) != [topology] or sorted(second_entries) != [topology]:
        errors.append("download-endpoint-ambiguity-or-absence")
    first_bound = first_entries.get(topology)
    second_bound = second_entries.get(topology)
    if first_bound != second_bound:
        errors.append("download-sysfs-changed-around-usbfs-inventory")
    bound = first_bound or second_bound
    expected = usbfs_path(bound) if bound is not None else None
    node = inventory["entries"].get(expected) if expected is not None else None
    if node is None:
        errors.append("expected-download-node-absent")
    elif bound is not None:
        try:
            require_usbfs_relation(node, bound)
        except ObserverError as exc:
            errors.append(f"usbfs-relation:{exc}")
    return {
        "captured_at_utc": utc_now(),
        "download_sysfs_before": first,
        "usbfs": inventory,
        "download_sysfs_after": second,
        "expected_path": expected,
        "expected_node": node,
        "capture_errors": errors,
        "complete": not errors,
    }


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else str(key)
            output.update(flatten(value[key], child))
        return output
    return {prefix: value}


def field_diff(before: Any, after: Any) -> list[dict[str, Any]]:
    left = flatten(before)
    right = flatten(after)
    output: list[dict[str, Any]] = []
    for name in sorted(set(left) | set(right)):
        left_present = name in left
        right_present = name in right
        if left_present and right_present and left[name] == right[name]:
            continue
        output.append(
            {
                "field": name,
                "before": left[name] if left_present else {"state": "missing"},
                "after": right[name] if right_present else {"state": "missing"},
            }
        )
    return output


def stabilization_binding(
    stabilization: dict[str, Any] | None,
    before: dict[str, Any],
    topology: str,
) -> dict[str, Any]:
    unsafe_reasons: list[str] = []
    immutable_changes: list[str] = []
    metadata_changes: list[str] = []
    stable_sample: dict[str, Any] | None = None
    if not isinstance(stabilization, dict):
        unsafe_reasons.append("stabilization-baseline-missing")
    else:
        candidate = stabilization.get("stable_sample")
        samples = stabilization.get("samples")
        if (
            stabilization.get("topology") != topology
            or not isinstance(samples, list)
            or len(samples) < STABLE_SAMPLE_COUNT
            or not isinstance(candidate, dict)
            or samples[-1] != candidate
            or stabilization.get("stable_count", 0) < STABLE_SAMPLE_COUNT
        ):
            unsafe_reasons.append("stabilization-record-invalid")
        else:
            stable_sample = candidate
    stable_sysfs = stable_sample.get("sysfs") if stable_sample is not None else None
    stable_node = stable_sample.get("node") if stable_sample is not None else None
    before_sysfs = before.get("download_sysfs_before", {}).get("entries", {}).get(topology)
    before_sysfs_after = before.get("download_sysfs_after", {}).get("entries", {}).get(topology)
    before_node = before.get("expected_node")
    if stable_sample is not None:
        if stable_sysfs != before_sysfs or stable_sysfs != before_sysfs_after:
            unsafe_reasons.append("stabilization-sysfs-identity-changed")
        if not isinstance(stable_node, dict) or not isinstance(before_node, dict):
            unsafe_reasons.append("stabilization-node-missing")
        else:
            for name in sorted(set(stable_node) | set(before_node)):
                if stable_node.get(name) == before_node.get(name):
                    continue
                target = (
                    immutable_changes
                    if name in IMMUTABLE_NODE_FIELDS
                    else metadata_changes
                )
                target.append(name)
            if immutable_changes:
                unsafe_reasons.append("stabilization-immutable-node-fields-changed")
    return {
        "unsafe_reasons": unsafe_reasons,
        "immutable_changes": immutable_changes,
        "metadata_changes": metadata_changes,
        "stable_sample_to_before_diff": field_diff(stable_sample, {
            "sysfs": before_sysfs,
            "node": before_node,
        }),
    }


def classify_observation(
    before: dict[str, Any],
    after: dict[str, Any],
    odin: dict[str, Any],
    stabilization: dict[str, Any] | None,
    topology: str,
) -> dict[str, Any]:
    expected = str(before["expected_path"])
    before_node = before["expected_node"]
    after_node = after["usbfs"]["entries"].get(expected)
    paths = odin["reported_paths"]
    occurrences = odin["reported_path_occurrences"]
    immutable_changes: list[str] = []
    metadata_changes: list[str] = []
    if before_node is not None and after_node is not None:
        for name in sorted(set(before_node) | set(after_node)):
            if before_node.get(name) == after_node.get(name):
                continue
            target = immutable_changes if name in IMMUTABLE_NODE_FIELDS else metadata_changes
            target.append(name)
    unsafe_reasons: list[str] = []
    stable_binding = stabilization_binding(stabilization, before, topology)
    unsafe_reasons.extend(stable_binding["unsafe_reasons"])
    if before["capture_errors"]:
        unsafe_reasons.append("before-capture-incomplete")
    if after["capture_errors"]:
        unsafe_reasons.append("after-capture-incomplete")
    if odin["returncode"] != 0 or odin["timed_out"]:
        unsafe_reasons.append("odin-enumeration-failed")
    if odin.get("output_truncated"):
        unsafe_reasons.append("odin-output-truncated")
    if not odin.get("output_parse_valid", False):
        unsafe_reasons.append("odin-output-not-strict-listing")
    if odin.get("stderr_nonempty"):
        unsafe_reasons.append("odin-stderr-nonempty")
    if odin.get("executable_path_changed"):
        unsafe_reasons.append("odin-path-identity-changed")
    if paths != [expected] or occurrences != [expected]:
        unsafe_reasons.append("odin-output-not-one-expected-path")
    if after_node is None:
        unsafe_reasons.append("expected-node-absent-after")
    if (
        before["download_sysfs_after"] != after["download_sysfs_before"]
        or before["expected_path"] != after["expected_path"]
    ):
        unsafe_reasons.append("download-sysfs-inventory-changed")
    if immutable_changes:
        unsafe_reasons.append("immutable-node-fields-changed")
    before_inventory = before["usbfs"]["entries"]
    after_inventory = after["usbfs"]["entries"]
    inventory_added = sorted(set(after_inventory) - set(before_inventory))
    inventory_removed = sorted(set(before_inventory) - set(after_inventory))
    if inventory_added or inventory_removed:
        unsafe_reasons.append("usbfs-inventory-membership-changed")
    if unsafe_reasons:
        classification = "OBSERVED_UNSAFE_OR_INCOMPLETE_ENUMERATION_TRANSITION"
    elif not metadata_changes:
        classification = "OBSERVED_NO_NODE_MUTATION"
    elif metadata_changes == ["st_ctime_ns"]:
        classification = "OBSERVED_CTIME_ONLY_MUTATION"
    else:
        classification = "OBSERVED_METADATA_ONLY_MUTATION"
    return {
        "classification": classification,
        "acceptance_decision": False,
        "expected_path": expected,
        "immutable_changes": immutable_changes,
        "metadata_changes": metadata_changes,
        "inventory_added": inventory_added,
        "inventory_removed": inventory_removed,
        "unsafe_reasons": unsafe_reasons,
        "stabilization_binding": stable_binding,
        "expected_node_diff": field_diff(before_node, after_node),
        "complete_bundle_diff": field_diff(before, after),
    }


def failed_capture_bundle(topology: str, exc: BaseException) -> dict[str, Any]:
    empty = {"entries": {}, "races": [], "errors": []}
    return {
        "captured_at_utc": utc_now(),
        "download_sysfs_before": dict(empty),
        "usbfs": dict(empty),
        "download_sysfs_after": dict(empty),
        "expected_path": None,
        "expected_node": None,
        "capture_errors": [f"capture-exception:{type(exc).__name__}:{exc}"],
        "requested_topology": topology,
        "complete": False,
    }


def parse_odin_listing_output(stdout: bytes, stderr: bytes) -> dict[str, Any]:
    try:
        stdout_text = stdout.decode("utf-8", "strict")
        stderr_text = stderr.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        return {
            "valid": False,
            "error": f"non-UTF-8 Odin output: {exc}",
            "paths": [],
            "occurrences": [],
            "stderr_nonempty": bool(stderr),
        }
    # Accept only literal path lines, with at most one final LF. Do not normalize
    # whitespace: every raw output byte is part of the evidence contract.
    body = stdout_text[:-1] if stdout_text.endswith("\n") else stdout_text
    lines = body.split("\n") if body else []
    occurrences = [line for line in lines if ODIN_DEVICE_RE.fullmatch(line)]
    stdout_shape_valid = (
        bool(lines)
        and "\r" not in stdout_text
        and not stdout_text.endswith("\n\n")
        and all(lines)
        and len(occurrences) == len(lines)
    )
    valid = stdout_shape_valid and stderr == b""
    return {
        "valid": valid,
        "error": (
            None
            if valid
            else "Odin output is not an exact path-only stdout listing with byte-empty stderr"
        ),
        "paths": sorted(set(occurrences)),
        "occurrences": occurrences,
        "stderr_nonempty": stderr != b"",
    }


@defer_termination_signals
def observe_odin_listing(
    odin: Path,
    run_dir: Path,
    topology: str,
    *,
    stabilization: dict[str, Any],
    odin_fd: int | None = None,
    verified_odin: dict[str, Any] | None = None,
    capture: Callable[[str], dict[str, Any]] = capture_bundle,
    runner: Callable[[list[str], float], subprocess.CompletedProcess[bytes]] | None = None,
    on_attempt: Callable[[], None] | None = None,
) -> dict[str, Any]:
    before = capture(topology)
    before_receipt = durable_create_json(run_dir / "enumeration-before.json", before)
    if before["capture_errors"] or not before["complete"]:
        raise ObserverError("pre-enumeration evidence is incomplete")
    stable_binding = stabilization_binding(stabilization, before, topology)
    durable_create_json(
        run_dir / "enumeration-baseline-binding.json", stable_binding
    )
    if stable_binding["unsafe_reasons"]:
        raise ObserverError("Download identity changed after stabilization")
    timed_out = False
    output_truncated = False
    cleanup_error: str | None = None
    error: str | None = None
    argv = [str(odin), "-l"]
    intent_receipt = durable_create_json(
        run_dir / "odin-list-intent.json",
        {
            "schema": SCHEMA,
            "created_at_utc": utc_now(),
            "argv": argv,
            "timeout_sec": 10.0,
            "transfer_authorized": False,
        },
    )
    if on_attempt is not None:
        on_attempt()
    deferred_exception: BaseException | None = None
    try:
        if runner is None:
            if odin_fd is None or verified_odin is None:
                raise ObserverError("verified Odin descriptor is required")
            require_path_matches_fd(odin, odin_fd)
            if executable_fd_identity(odin_fd) != verified_odin:
                raise ObserverError("verified Odin descriptor changed before execution")
            process = run_bounded(argv, 10.0, executable_fd=odin_fd)
        else:
            process = runner(argv, 10.0)
        returncode = process.returncode
        stdout = bytes(process.stdout or b"")
        stderr = bytes(process.stderr or b"")
    except BoundedCommandError as exc:
        timed_out = exc.timed_out
        output_truncated = exc.output_truncated
        cleanup_error = exc.cleanup_error
        error = f"{type(exc).__name__}: {exc}"
        returncode = -1
        stdout = exc.stdout
        stderr = exc.stderr
    except (OSError, ObserverError, subprocess.SubprocessError) as exc:
        error = f"{type(exc).__name__}: {exc}"
        returncode = -1
        stdout = b""
        stderr = b""
    except CommandInterruption as exc:
        cleanup_error = exc.cleanup_error
        error = f"{type(exc.original).__name__}: {exc.original}"
        if cleanup_error is not None:
            error = f"{error}; process-cleanup={cleanup_error}"
        returncode = -1
        stdout = exc.stdout
        stderr = exc.stderr
        deferred_exception = exc.original
    except BaseException as exc:
        # Defer asynchronous/programmatic interruption until the mandatory
        # post-command evidence and command accounting are durably sealed.
        error = f"{type(exc).__name__}: {exc}"
        returncode = -1
        stdout = b""
        stderr = b""
        deferred_exception = exc
    try:
        after = capture(topology)
    except BaseException as exc:
        after = failed_capture_bundle(topology, exc)
        if deferred_exception is None:
            deferred_exception = exc
    closure_failures: list[tuple[str, BaseException]] = []
    after_receipt: dict[str, Any] | None = None
    try:
        after_receipt = durable_create_json(run_dir / "enumeration-after.json", after)
    except BaseException as exc:
        closure_failures.append(("enumeration-after.json", exc))
    command_outcome = {
        "schema": SCHEMA,
        "argv": argv,
        "returncode": returncode,
        "timed_out": timed_out,
        "output_truncated": output_truncated,
        "cleanup_error": cleanup_error,
        "error": error,
        "exception_type": (
            type(deferred_exception).__name__ if deferred_exception is not None else None
        ),
        "stdout_size": len(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_size": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
        "post_capture": after_receipt,
        "evidence_persist_errors": [
            {"path": path, "error": f"{type(exc).__name__}: {exc}"}
            for path, exc in closure_failures
        ],
        "transfer_authorized": False,
        "acceptance_decision": False,
    }
    command_outcome_receipt: dict[str, Any] | None = None
    stdout_receipt: dict[str, Any] | None = None
    stderr_receipt: dict[str, Any] | None = None
    for label, writer in (
        (
            "odin-list-command-outcome.json",
            lambda: durable_create_json(
                run_dir / "odin-list-command-outcome.json", command_outcome
            ),
        ),
        (
            "odin-list.stdout",
            lambda: durable_create_bytes(run_dir / "odin-list.stdout", stdout),
        ),
        (
            "odin-list.stderr",
            lambda: durable_create_bytes(run_dir / "odin-list.stderr", stderr),
        ),
    ):
        try:
            receipt = writer()
        except BaseException as exc:
            closure_failures.append((label, exc))
            continue
        if label == "odin-list-command-outcome.json":
            command_outcome_receipt = receipt
        elif label == "odin-list.stdout":
            stdout_receipt = receipt
        else:
            stderr_receipt = receipt
    if closure_failures:
        details = "; ".join(
            f"{path}={type(exc).__name__}: {exc}" for path, exc in closure_failures
        )
        raise ObserverError(f"post-Odin evidence closure failed: {details}") from (
            closure_failures[0][1]
        )
    parsed_output = parse_odin_listing_output(stdout, stderr)
    reported_occurrences = parsed_output["occurrences"]
    reported = parsed_output["paths"]
    if parsed_output["error"]:
        error = (
            f"{error}; {parsed_output['error']}"
            if error
            else str(parsed_output["error"])
        )
    executable_after: dict[str, Any] | None = None
    executable_path_changed = False
    if odin_fd is not None:
        try:
            executable_after = executable_fd_identity(odin_fd)
            require_path_matches_fd(odin, odin_fd)
            if executable_after != verified_odin:
                raise ObserverError("verified Odin descriptor changed after execution")
        except (ObserverError, OSError) as exc:
            executable_path_changed = True
            error = f"{error}; {type(exc).__name__}: {exc}" if error else f"{type(exc).__name__}: {exc}"
    odin_result = {
        "argv": argv,
        "returncode": returncode,
        "timed_out": timed_out,
        "output_truncated": output_truncated,
        "error": error,
        "reported_paths": reported,
        "reported_path_occurrences": reported_occurrences,
        "output_parse_valid": parsed_output["valid"],
        "stderr_nonempty": parsed_output["stderr_nonempty"],
        "stdout": stdout_receipt,
        "stderr": stderr_receipt,
        "command_outcome": command_outcome_receipt,
        "verified_executable_before": verified_odin,
        "verified_executable_after": executable_after,
        "executable_path_changed": executable_path_changed,
    }
    durable_create_json(run_dir / "odin-list-result.json", odin_result)
    classification = classify_observation(
        before, after, odin_result, stabilization, topology
    )
    classification_receipt = durable_create_json(
        run_dir / "enumeration-diff.json", classification
    )
    if deferred_exception is not None:
        raise deferred_exception
    return {
        "before": before_receipt,
        "after": after_receipt,
        "intent": intent_receipt,
        "odin": odin_result,
        "classification": classification,
        "classification_receipt": classification_receipt,
    }


def verify_odin(path: Path) -> dict[str, Any]:
    with open_verified_odin(path) as (_descriptor, identity):
        return identity


def rendered_policy_clause(root: Path) -> str:
    lines = [
        POLICY_BEGIN,
        ACTIVE_SENTINEL,
        POLICY_MARKER,
        f"helper_path={SCRIPT_RELATIVE}",
        f"helper_sha256={sha256_file(root / SCRIPT_RELATIVE)}",
        f"test_path={TEST_RELATIVE}",
        f"test_sha256={sha256_file(root / TEST_RELATIVE)}",
        f"draft_path={POLICY_DRAFT}",
        f"draft_sha256={sha256_file(root / POLICY_DRAFT)}",
        f"odin_path={DEFAULT_ODIN}",
        f"odin_size={EXPECTED_ODIN_SIZE}",
        f"odin_sha256={EXPECTED_ODIN_SHA256}",
        f"observe_ack={OBSERVE_ACK_TOKEN}",
        f"download_confirm={DOWNLOAD_CONFIRM_TOKEN}",
        f"recovery_ack={RECOVERY_ACK_TOKEN}",
        "authorization=one-exact-android-baseline+one-adb-reboot-download+one-bounded-odin4-list+physical-exit+exact-android-return",
        "target=one-attended-SM-S906N+g0q+S906NKSS7FYG8+same-cable-hub-port",
        "android_baseline=boot-complete+bootanim-stopped+orange+magisk-uid0+exact-known-boot+stock-vendor_boot+stock-dtbo+stock-recovery+exact-adb-serial+usb-topology+no-download-endpoint",
        "odin_executable=open-no-follow+exact-size-sha+held-fd+execute-through-fd+same-path-inode-before-after",
        "one_shot=exclusive-durable-consume-before-adb-reboot-download-attempt+immediate-open-no-follow-pin+path-inode-sha-check-across-all-subsequent-actions-and-final-result",
        "download_endpoint=only-bound-topology+04e8:685d+SAMSUNG-USB+Samsung+serial-absent+unambiguous",
        "stabilization=SIGINT+SIGTERM+SIGHUP-masked-from-each-sample-read-through-exclusive-create-fsync+failure-or-interruption-preserves-every-collected-sample+last-stable-sample-is-immutable-pre-odin-baseline",
        "pre_odin_binding=first-complete-pre-listing-bundle-must-match-stable-topology+full-sysfs+path+all-immutable-node-fields;replacement-or-device-number-change-stops-before-odin",
        "listing=exactly-one-bounded-10s-odin4-minus-l+bounded-output+no-other-subprocess-execution-surface",
        "post_odin_order=SIGINT+SIGTERM+SIGHUP-masked-through-closure+partial-output-and-original-interruption-preserved-even-if-process-cleanup-fails+on-return+failure+timeout+output-bound+interruption:first-capture-complete-after-bundle;independently-attempt-after-bundle+command-outcome-including-cleanup-error-and-after-persist-error+raw-stdout+raw-stderr-so-one-write-failure-cannot-skip-the-others;any-write-failure-is-non-PASS;then-rehash-parse-classify;unmask-or-reraise-only-after-closure",
        "evidence=bracketed-all-download-sysfs+complete-bounded-usbfs+exact-node-stat-fields+all-races-errors+raw-output+return-timeout-truncation+parsed-paths+per-field-diff+exclusive-create+fsync",
        "odin_output=raw-strict-utf8-path-only-stdout+at-most-one-final-LF+no-blank-or-whitespace-normalization+byte-empty-stderr+exactly-one-expected-path",
        "unsafe=topology-or-descriptor-or-device-number-or-immutable-change+inventory-change+ambiguity+disappearance+capture-error+command-failure+malformed-output",
        "android_return=same-exact-serial+topology+complete-pre-run-FYG8+Magisk+partition-identities",
        "recovery=only-exact-consumed-run+pinned-open-no-follow-state-fd+path-inode-sha-check-before-and-after-every-Android-return-polling-attempt+after-preclosure-fsync+immediately-before-final-result+separate-token+no-reboot-or-odin-or-transfer+exclusive-intent-before-contact+attempt-specific-evidence+interrupted-intent-counts+maximum-two-bounded-attempts",
        "authority=whole-observation-or-recovery-session+single-writer-nonblocking-lease+pinned-lock-fd-and-path-inode+pinned-policy-helper-test-draft+checks-before-and-after-initial-Android-baseline+authority-and-consumed-pin-checks-before-and-after-adb-reboot-download+around-every-stabilization-sample+confirmation+odin-observation+Android-return-polling-attempt+after-non-PASS-preclosure-fsync+immediately-before-final-result",
        "partition_writes=false",
        "odin_transfer=false",
        "acceptance_decision=false",
        "pass=only-PASS_R4W1C_ENUM_DIFF_OBSERVER_EVIDENCE_CAPTURED-after-evidence-closure-and-exact-android-return;never-authorizes-candidate-or-second-observer",
        "timeline=only-events-name-timestamp_utc+canonical-eight-ordered-slots+zero-flash-semantics+non-PASS-preclosure-preserves-actual-prefix-before-placeholder-completion+recovery-never-relabels-placeholders+recovery-activity-uses-separate-noncanonical-result-field+result-maps-each-slot-to-reached-or-not-reached-no-action-placeholder",
        "result_closure=exclusive-non-PASS-preclosure+post-fsync-authority-and-consumed-state-validation+final-PASS-result-created-only-after-validation",
        "policy_digest_semantics=embedded-policy-clause-sha256-is-sha256-of-normalized-clause-template-containing-literal-placeholder;authority-receipt-policy-clause-sha256-is-sha256-of-final-rendered-block",
        "forbidden=candidate-ap,odin-transfer,flash,partition-write,raw-dd,fastboot,module,panic,sysrq,rdx,sboot,ramdump,qdl,sahara,firehose,eud,uart,format,cleanup,a90,boot,recovery,vendor_boot,dtbo,vbmeta,bl,cp,csc,super,userdata,persist,efs,sec_efs,rpmb,keymaster,modem,bootloader,all-other-partitions",
        f"{POLICY_HASH_PREFIX}{{{{POLICY_CLAUSE_SHA256}}}}",
        POLICY_END,
    ]
    normalized = "\n".join(lines) + "\n"
    digest = sha256_bytes(normalized.encode("utf-8"))
    return normalized.replace("{{POLICY_CLAUSE_SHA256}}", digest)


def policy_clause_from_text(root: Path, text: str) -> str:
    begin = f"{POLICY_BEGIN}\n"
    end = f"{POLICY_END}\n"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ObserverError("enumeration-diff observer policy clause is not singular")
    block = text[text.index(begin) : text.index(end) + len(end)]
    if block != rendered_policy_clause(root):
        raise ObserverError("enumeration-diff observer policy clause mismatch")
    return block


def policy_clause(root: Path) -> str:
    return policy_clause_from_text(
        root, (root / "AGENTS.md").read_text(encoding="utf-8")
    )


def policy_active(root: Path) -> bool:
    try:
        policy_clause(root)
    except (ObserverError, OSError):
        return False
    return True


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if path.is_symlink() or not path.is_file():
        raise ObserverError("observer policy draft is missing")
    text = path.read_text(encoding="utf-8")
    required = (
        "DRAFT_INACTIVE",
        POLICY_MARKER,
        ACTIVE_SENTINEL,
        OBSERVE_ACK_TOKEN,
        DOWNLOAD_CONFIRM_TOKEN,
        RECOVERY_ACK_TOKEN,
        str(SCRIPT_RELATIVE),
        str(TEST_RELATIVE),
        "{{HELPER_SHA256}}",
        "{{TEST_SHA256}}",
        "{{POLICY_DRAFT_SHA256}}",
        "{{POLICY_CLAUSE_SHA256}}",
        EXPECTED_ODIN_SHA256,
        "odin4 -l",
        "no transfer",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise ObserverError(f"observer policy draft mismatch: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "active": policy_active(root),
    }


def authority_receipt(root: Path) -> dict[str, str]:
    block = policy_clause(root)
    return {
        "helper_sha256": sha256_file(root / SCRIPT_RELATIVE),
        "test_sha256": sha256_file(root / TEST_RELATIVE),
        "draft_sha256": sha256_file(root / POLICY_DRAFT),
        "policy_clause_sha256": sha256_bytes(block.encode("utf-8")),
    }


def require_authority_unchanged(root: Path, expected: dict[str, str]) -> None:
    if authority_receipt(root) != expected:
        raise ObserverError("observer authority changed during the live session")


def read_fd_bytes(descriptor: int, maximum: int = MAX_JSON_BYTES) -> bytes:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
        or metadata.st_size > maximum
    ):
        raise ObserverError("authority file shape is invalid")
    payload = bytearray()
    offset = 0
    while offset < metadata.st_size:
        chunk = os.pread(descriptor, min(1024 * 1024, metadata.st_size - offset), offset)
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    after = os.fstat(descriptor)
    if len(payload) != metadata.st_size or (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
    ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ObserverError("authority file changed while reading")
    return bytes(payload)


def authority_file_paths() -> tuple[Path, ...]:
    return (Path("AGENTS.md"), SCRIPT_RELATIVE, TEST_RELATIVE, POLICY_DRAFT)


@contextlib.contextmanager
def authority_session(root: Path):
    if not policy_active(root):
        raise ObserverError("observer policy is inactive")
    lock_path = root / AUTHORITY_LOCK
    require_direct_directory_chain(root, lock_path.parent)
    lock_fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    descriptors: list[int] = []
    lease: AuthorityLease | None = None
    lock_acquired = False
    try:
        lock_metadata = os.fstat(lock_fd)
        if not stat.S_ISREG(lock_metadata.st_mode) or lock_metadata.st_nlink != 1:
            raise ObserverError("observer authority lock is not a direct regular file")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_acquired = True
        except BlockingIOError as exc:
            raise ObserverError("observer already has an active authority session") from exc
        lock_metadata = os.fstat(lock_fd)
        lock_path_metadata = os.stat(lock_path, follow_symlinks=False)
        lock_identity = (lock_metadata.st_dev, lock_metadata.st_ino)
        if (
            lock_metadata.st_nlink != 1
            or lock_identity
            != (lock_path_metadata.st_dev, lock_path_metadata.st_ino)
        ):
            raise ObserverError("observer authority lock pathname changed")
        pinned: dict[str, tuple[int, tuple[int, int, int], str]] = {}
        payloads: dict[str, bytes] = {}
        for relative in authority_file_paths():
            path = root / relative
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            )
            descriptors.append(descriptor)
            payload = read_fd_bytes(descriptor)
            metadata = os.fstat(descriptor)
            path_metadata = os.stat(path, follow_symlinks=False)
            identity = (metadata.st_dev, metadata.st_ino, metadata.st_size)
            if identity != (
                path_metadata.st_dev,
                path_metadata.st_ino,
                path_metadata.st_size,
            ):
                raise ObserverError("authority pathname changed while pinning")
            pinned[str(relative)] = (descriptor, identity, sha256_bytes(payload))
            payloads[str(relative)] = payload
        block = policy_clause_from_text(
            root, payloads["AGENTS.md"].decode("utf-8", "strict")
        )
        receipt = {
            "helper_sha256": pinned[str(SCRIPT_RELATIVE)][2],
            "test_sha256": pinned[str(TEST_RELATIVE)][2],
            "draft_sha256": pinned[str(POLICY_DRAFT)][2],
            "policy_clause_sha256": sha256_bytes(block.encode("utf-8")),
        }
        if receipt != authority_receipt(root):
            raise ObserverError("authority receipt changed while acquiring lease")
        lease = AuthorityLease(
            root=root.resolve(),
            owner_pid=os.getpid(),
            owner_thread=threading.get_ident(),
            receipt=receipt,
            pinned_files=pinned,
            lock_descriptor=lock_fd,
            lock_identity=lock_identity,
        )
        with _ACTIVE_AUTHORITY_LEASES_LOCK:
            _ACTIVE_AUTHORITY_LEASES.add(lease)
        yield lease
    finally:
        if lease is not None:
            with _ACTIVE_AUTHORITY_LEASES_LOCK:
                _ACTIVE_AUTHORITY_LEASES.discard(lease)
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        try:
            if lock_acquired:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def require_authority_lease(root: Path, lease: AuthorityLease) -> None:
    with _ACTIVE_AUTHORITY_LEASES_LOCK:
        active = lease in _ACTIVE_AUTHORITY_LEASES
    if (
        not active
        or lease.owner_pid != os.getpid()
        or lease.owner_thread != threading.get_ident()
        or lease.root != root.resolve()
    ):
        raise ObserverError("active observer authority lease is required")
    lock_metadata = os.fstat(lease.lock_descriptor)
    lock_path_metadata = os.stat(root / AUTHORITY_LOCK, follow_symlinks=False)
    if (
        lock_metadata.st_nlink != 1
        or (lock_metadata.st_dev, lock_metadata.st_ino) != lease.lock_identity
        or lease.lock_identity
        != (lock_path_metadata.st_dev, lock_path_metadata.st_ino)
    ):
        raise ObserverError("observer authority lock pathname changed")
    for relative, (descriptor, identity, digest) in lease.pinned_files.items():
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(root / relative, follow_symlinks=False)
        current = (metadata.st_dev, metadata.st_ino, metadata.st_size)
        if (
            current != identity
            or current
            != (path_metadata.st_dev, path_metadata.st_ino, path_metadata.st_size)
            or sha256_fd(descriptor) != digest
        ):
            raise ObserverError("observer authority changed under active lease")
    require_authority_unchanged(root, lease.receipt)


def source_surface_audit(root: Path) -> dict[str, Any]:
    source = (root / SCRIPT_RELATIVE).read_text(encoding="utf-8")
    forbidden = (
        ".tar" + ".md5",
        "boot.img" + ".lz4",
        "flash_" + "exact",
        "flash_" + "ap",
        "candidate_" + "ap",
        "magisk_" + "ap",
        "stock_" + "ap",
        "--rollback-from-" + "download",
    )
    found = [item for item in forbidden if item in source]
    if found:
        raise ObserverError(f"observer source has a transfer surface: {found}")
    tree = ast.parse(source)
    forbidden_cli_literals = {
        "--" + "ap",
        "--" + "boot",
        "--" + "csc",
        "--" + "flash",
        "--" + "pit",
        "--" + "repartition",
    }
    literal_hits = sorted(
        {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in forbidden_cli_literals
        }
    )
    if literal_hits:
        raise ObserverError(f"observer source has transfer CLI literals: {literal_hits}")
    subprocess_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr in {"Popen", "run", "call", "check_call", "check_output"}
    ]
    if len(subprocess_calls) != 1 or subprocess_calls[0].func.attr != "Popen":
        raise ObserverError("observer subprocess surface is not one sealed Popen")
    os_execution_calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
        and (
            node.func.attr == "system"
            or node.func.attr.startswith("exec")
            or node.func.attr.startswith("spawn")
        )
    ]
    if os_execution_calls:
        raise ObserverError(f"observer has alternate execution surfaces: {os_execution_calls}")
    observer = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "observe_odin_listing"
        ),
        None,
    )
    if observer is None:
        raise ObserverError("Odin observer function is absent")
    argv_assignments = [
        node
        for node in ast.walk(observer)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "argv" for target in node.targets)
        and isinstance(node.value, ast.List)
        and len(node.value.elts) == 2
        and isinstance(node.value.elts[1], ast.Constant)
        and node.value.elts[1].value == "-l"
    ]
    listing_calls = [
        node
        for node in ast.walk(observer)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_bounded"
        and len(node.args) == 2
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "argv"
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == 10.0
        and any(keyword.arg == "executable_fd" for keyword in node.keywords)
    ]
    if len(argv_assignments) != 1 or len(listing_calls) != 1:
        raise ObserverError("observer does not have exactly one Odin listing callsite")
    return {
        "transfer_surface": False,
        "odin_listing_callsites": 1,
        "subprocess_execution_callsites": 1,
        "alternate_execution_callsites": 0,
        "allowed_device_mutation": "adb-reboot-download-only-when-policy-active",
    }


def offline_check(root: Path, args: argparse.Namespace) -> int:
    result = {
        "schema": SCHEMA,
        "mode": "offline-check",
        "target": TARGET,
        "source": {
            "path": str(SCRIPT_RELATIVE),
            "size": (root / SCRIPT_RELATIVE).stat().st_size,
            "sha256": sha256_file(root / SCRIPT_RELATIVE),
            "test_path": str(TEST_RELATIVE),
            "test_size": (root / TEST_RELATIVE).stat().st_size,
            "test_sha256": sha256_file(root / TEST_RELATIVE),
        },
        "policy": verify_policy_draft(root),
        "odin": verify_odin(DEFAULT_ODIN),
        "surface": source_surface_audit(root),
        "observer_consumed": (root / CONSUMED_STATE).exists(),
        "device_contact": False,
        "device_writes": False,
        "reboot": False,
        "download_transition": False,
        "odin_enumeration": False,
        "odin_transfer": False,
        "flash": False,
        "acceptance_decision": False,
        "verdict": "PASS_R4W1C_ENUM_DIFF_OBSERVER_SOURCE_OFFLINE_CHECK",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def fresh_confirmation(timeout_sec: float) -> str:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise ObserverError("confirmation timeout is invalid")
    descriptor = sys.stdin.fileno()
    if os.isatty(descriptor):
        termios.tcflush(descriptor, termios.TCIFLUSH)
    else:
        ready, _, _ = select_with_timeout(descriptor, 0.0)
        if ready:
            raise ObserverError("prebuffered Download confirmation is not fresh")
    deadline = time.monotonic() + timeout_sec
    payload = bytearray()
    while b"\n" not in payload:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ObserverError("Download confirmation timed out")
        ready, _, _ = select_with_timeout(descriptor, remaining)
        if not ready:
            raise ObserverError("Download confirmation timed out")
        chunk = os.read(descriptor, 256)
        if not chunk:
            raise ObserverError("Download confirmation input closed")
        payload.extend(chunk)
        if len(payload) > 256:
            raise ObserverError("Download confirmation is oversized")
    line, separator, trailing = bytes(payload).partition(b"\n")
    if separator != b"\n" or trailing:
        raise ObserverError("Download confirmation framing is invalid")
    return line.decode("ascii", "strict")


def select_with_timeout(descriptor: int, timeout_sec: float) -> tuple[list[int], list[int], list[int]]:
    import select

    return select.select([descriptor], [], [], timeout_sec)


def wait_for_android_return(
    expected_serial: str | None,
    expected_binding: dict[str, str],
    timeout_sec: float,
    *,
    expected_serial_sha256: str | None = None,
    continuity_check: Callable[[], None] | None = None,
) -> dict[str, Any]:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise ObserverError("Android return timeout is invalid")
    deadline = time.monotonic() + timeout_sec
    last_error = "Android did not appear"
    while time.monotonic() < deadline:
        if continuity_check is not None:
            continuity_check()
        try:
            serial, state = android_state()
            binding = android_usb_binding(serial)
            if expected_serial is not None and serial != expected_serial:
                raise ObserverError("returned Android serial mismatch")
            if expected_serial_sha256 is not None and sha256_bytes(serial.encode("ascii")) != expected_serial_sha256:
                raise ObserverError("returned Android serial digest mismatch")
            if binding != expected_binding:
                raise ObserverError("returned Android identity or topology mismatch")
            if download_endpoint_inventory():
                raise ObserverError("Download endpoint remains present after Android return")
            returned = {"serial": serial, "android": state, "usb_binding": binding}
        except (ObserverError, OSError, subprocess.SubprocessError) as exc:
            last_error = str(exc)
        else:
            if continuity_check is not None:
                continuity_check()
            return returned
        if continuity_check is not None:
            continuity_check()
        time.sleep(1.0)
    if continuity_check is not None:
        continuity_check()
    raise ObserverError(f"exact Android return timed out: {last_error}")


def consume_observer(
    root: Path,
    run_dir: Path,
    serial: str,
    binding: dict[str, str],
    odin: dict[str, Any],
    authority: dict[str, str],
) -> dict[str, Any]:
    path = root / CONSUMED_STATE
    require_direct_directory_chain(root, path.parent)
    record = {
        "schema": CONSUMED_SCHEMA,
        "consumed_at_utc": utc_now(),
        "target": TARGET,
        "authority": authority,
        "android_serial_sha256": sha256_bytes(serial.encode("ascii")),
        "usb_binding": binding,
        "odin": odin,
        "run_dir": str(run_dir.relative_to(root)),
        "transfer_authorized": False,
    }
    durable_create_json(path, record)
    return record


def _observe_live_with_lease(
    root: Path, args: argparse.Namespace, lease: AuthorityLease
) -> int:
    if (root / CONSUMED_STATE).exists():
        raise ObserverError("observer one-shot state is already consumed")
    authority = lease.receipt
    run_dir = allocate_run_dir(root, args.run_dir)
    timeline_path = run_dir / "timeline.json"
    events: list[dict[str, str]] = []
    append_timeline(timeline_path, events, "live_session_start")
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "observe-download-enumeration",
        "target": TARGET,
        "run_dir": str(run_dir),
        "transfer_surface": False,
        "device_contact": True,
        "device_writes": False,
        "reboot_request_attempted": False,
        "reboot_request_returned_cleanly": False,
        "reboot": False,
        "download_transition": False,
        "odin_enumeration": False,
        "odin_transfer": False,
        "flash": False,
        "acceptance_decision": False,
        "timeline_semantics": {
            "candidate_flash_start": "no-flash-download-request-start",
            "candidate_flash_done": "no-flash-download-node-stable",
            "candidate_boot_ready": "single-enumeration-evidence-closed",
            "rollback_flash_start": "no-flash-physical-android-return-wait-start",
            "rollback_flash_done": "no-flash-android-transport-returned",
            "rollback_boot_ready": "exact-android-return-verified",
        },
        "verdict": "INCOMPLETE",
    }
    download_request_attempted = False
    serial: str | None = None
    binding: dict[str, str] | None = None
    android_return: dict[str, Any] | None = None
    consumed_pin: ConsumedStatePin | None = None

    def require_live_continuity() -> None:
        require_authority_lease(root, lease)
        if consumed_pin is not None:
            require_consumed_state_pin(consumed_pin)

    try:
        with open_verified_odin(DEFAULT_ODIN) as (odin_fd, odin):
            require_live_continuity()
            try:
                serial, initial_android = android_state()
            finally:
                require_live_continuity()
            try:
                binding = android_usb_binding(serial)
            finally:
                require_live_continuity()
            if download_endpoint_inventory():
                raise ObserverError("Android baseline has a Download endpoint")
            baseline = {
                "serial_sha256": sha256_bytes(serial.encode("ascii")),
                "android": initial_android,
                "usb_binding": binding,
            }
            durable_create_json(run_dir / "android-before.json", baseline)
            require_live_continuity()
            consumed = consume_observer(
                root, run_dir, serial, binding, odin, authority
            )
            pinned_state, pinned_run_dir, consumed_pin = open_validated_consumed_observer(
                root, authority
            )
            if pinned_state != consumed or pinned_run_dir != run_dir:
                raise ObserverError("newly consumed observer state does not reopen exactly")
            require_live_continuity()
            result["consumed"] = consumed
            result["consumed_state_sha256"] = consumed_pin.sha256
            append_timeline(timeline_path, events, "candidate_flash_start")
            download_request_attempted = True
            result["reboot_request_attempted"] = True
            require_live_continuity()
            try:
                returncode, _stdout, stderr = command_text(
                    ["adb", "-s", serial, "reboot", "download"], 20.0
                )
            finally:
                require_live_continuity()
            if returncode != 0 or stderr:
                raise ObserverError("Android Download request result is ambiguous")
            result["reboot_request_returned_cleanly"] = True
            result["reboot"] = True
            def persist_stabilization_sample(
                index: int, sample: dict[str, Any]
            ) -> None:
                require_live_continuity()
                try:
                    durable_create_json(
                        run_dir / f"download-stabilization-sample-{index:04d}.json",
                        {
                            "schema": SCHEMA,
                            "sample_index": index,
                            "topology": binding["topology"],
                            "sample": sample,
                        },
                    )
                finally:
                    require_live_continuity()

            require_live_continuity()
            stabilization = wait_for_stable_download(
                binding["topology"],
                args.download_wait_sec,
                on_sample=persist_stabilization_sample,
            )
            require_live_continuity()
            result["download_transition"] = True
            durable_create_json(
                run_dir / "download-stabilization.json", stabilization
            )
            append_timeline(timeline_path, events, "candidate_flash_done")
            print(
                "Confirm the same attended handset is in normal Samsung Download. "
                f"Type {DOWNLOAD_CONFIRM_TOKEN}"
            )
            require_live_continuity()
            confirmation = fresh_confirmation(args.confirmation_wait_sec)
            require_live_continuity()
            if confirmation != DOWNLOAD_CONFIRM_TOKEN:
                raise ObserverError("normal Download confirmation mismatch")
            require_live_continuity()
            observation = observe_odin_listing(
                DEFAULT_ODIN,
                run_dir,
                binding["topology"],
                stabilization=stabilization,
                odin_fd=odin_fd,
                verified_odin=odin,
                on_attempt=lambda: result.__setitem__("odin_enumeration", True),
            )
            require_live_continuity()
            result["odin_enumeration"] = True
            result["observation"] = observation
            append_timeline(timeline_path, events, "candidate_boot_ready")
            if observation["classification"]["unsafe_reasons"]:
                raise ObserverError("enumeration observation is unsafe or incomplete")
            require_live_continuity()
            append_timeline(timeline_path, events, "rollback_flash_start")
            print(
                "Enumeration evidence is closed. Physically exit Download and return "
                "the same handset to exact Android."
            )
            android_return = wait_for_android_return(
                serial,
                binding,
                args.android_wait_sec,
                continuity_check=require_live_continuity,
            )
            append_timeline(timeline_path, events, "rollback_flash_done")
            durable_create_json(run_dir / "android-after.json", android_return)
            append_timeline(timeline_path, events, "rollback_boot_ready")
            require_live_continuity()
            result["android_return"] = android_return
            result["verdict"] = "PASS_R4W1C_ENUM_DIFF_OBSERVER_EVIDENCE_CAPTURED"
            result["acceptance_decision"] = False
            rc = 0
    except (ObserverError, OSError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
        result["download_request_attempted"] = download_request_attempted
        result["verdict"] = "FAIL_R4W1C_ENUM_DIFF_OBSERVER_INCOMPLETE"
        rc = 1
    finally:
        try:
            if (
                download_request_attempted
                and android_return is None
                and serial is not None
                and binding is not None
            ):
                print(
                    "Observer stopped after requesting Download. Physically exit Download "
                    "and return the same handset to exact Android."
                )
                try:
                    require_live_continuity()
                    recovered = wait_for_android_return(
                        serial,
                        binding,
                        args.android_wait_sec,
                        continuity_check=require_live_continuity,
                    )
                    require_live_continuity()
                    durable_create_json(
                        run_dir / "android-after-recovery.json", recovered
                    )
                    require_live_continuity()
                    result["failure_recovery_android"] = recovered
                except (ObserverError, OSError, subprocess.SubprocessError) as recovery_exc:
                    result["failure_recovery_error"] = str(recovery_exc)
            result["actual_timeline_events"] = [event["name"] for event in events]
            result["timeline_event_status"] = timeline_event_status(
                result["actual_timeline_events"] + ["live_session_end"]
            )
            result["timeline_placeholder_semantics"] = (
                "unreached canonical slots are no-action placeholders, not milestones"
            )
            require_live_continuity()
            preclosure_receipt = durable_create_json(
                run_dir / "result-preclosure.json",
                preclosure_result(result, successful=rc == 0),
            )
            require_live_continuity()
            complete_timeline(timeline_path, events)
            require_live_continuity()
            result["timeline"] = {"events": events, "path": str(timeline_path)}
            result["authority_final"] = lease.receipt
            result["preclosure"] = preclosure_receipt
            if consumed_pin is not None:
                result["consumed_state_final_sha256"] = consumed_pin.sha256
            require_live_continuity()
            durable_create_json(run_dir / "result.json", result)
        finally:
            if consumed_pin is not None:
                os.close(consumed_pin.descriptor)
    print(json.dumps({"run_dir": str(run_dir), "verdict": result["verdict"]}, indent=2))
    return rc


def observe_live(root: Path, args: argparse.Namespace) -> int:
    if args.ack != OBSERVE_ACK_TOKEN:
        raise ObserverError("observer acknowledgement mismatch")
    with authority_session(root) as lease:
        return _observe_live_with_lease(root, args, lease)


def require_consumed_state_pin(pin: ConsumedStatePin) -> None:
    metadata = os.fstat(pin.descriptor)
    path_metadata = os.stat(pin.path, follow_symlinks=False)
    current = (metadata.st_dev, metadata.st_ino, metadata.st_size)
    if (
        metadata.st_nlink != 1
        or current != pin.identity
        or current
        != (path_metadata.st_dev, path_metadata.st_ino, path_metadata.st_size)
        or sha256_fd(pin.descriptor) != pin.sha256
    ):
        raise ObserverError("consumed observer state changed under active session")


def open_validated_consumed_observer(
    root: Path, authority: dict[str, str]
) -> tuple[dict[str, Any], Path, ConsumedStatePin]:
    state_path = root / CONSUMED_STATE
    require_direct_directory_chain(root, state_path.parent)
    descriptor = os.open(
        state_path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        payload = read_fd_bytes(descriptor)
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(state_path, follow_symlinks=False)
        identity = (metadata.st_dev, metadata.st_ino, metadata.st_size)
        if identity != (
            path_metadata.st_dev,
            path_metadata.st_ino,
            path_metadata.st_size,
        ):
            raise ObserverError("consumed observer pathname changed while pinning")
        state = json.loads(payload)
        if not isinstance(state, dict) or (
            state.get("schema") != CONSUMED_SCHEMA
            or state.get("target") != TARGET
            or state.get("authority") != authority
            or state.get("transfer_authorized") is not False
            or not isinstance(state.get("android_serial_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", state["android_serial_sha256"]) is None
            or not isinstance(state.get("usb_binding"), dict)
            or state.get("odin", {}).get("sha256") != EXPECTED_ODIN_SHA256
            or not isinstance(state.get("run_dir"), str)
        ):
            raise ObserverError("consumed observer state is invalid")
        run_dir = Path(os.path.abspath(root / state["run_dir"]))
        run_root = Path(os.path.abspath(root / RUN_ROOT))
        if run_dir.parent != run_root:
            raise ObserverError("consumed observer run directory escapes private run root")
        require_direct_directory_chain(root, run_dir)
        pin = ConsumedStatePin(
            path=state_path,
            descriptor=descriptor,
            identity=identity,
            sha256=sha256_bytes(payload),
        )
        require_consumed_state_pin(pin)
        return state, run_dir, pin
    except BaseException:
        os.close(descriptor)
        raise


@contextlib.contextmanager
def validated_consumed_observer(root: Path, authority: dict[str, str]):
    state, run_dir, pin = open_validated_consumed_observer(root, authority)
    try:
        yield state, run_dir, pin
    finally:
        os.close(pin.descriptor)


def reserve_recovery_attempt(
    root: Path,
    run_dir: Path,
    state: dict[str, Any],
    authority: dict[str, str],
    consumed_pin: ConsumedStatePin,
) -> tuple[int, Path, Path]:
    require_consumed_state_pin(consumed_pin)
    state_sha256 = consumed_pin.sha256
    for attempt in (1, 2):
        intent_path = run_dir / f"recovery-attempt-{attempt:02d}-intent.json"
        result_path = run_dir / f"recovery-result-{attempt:02d}.json"
        evidence_path = run_dir / f"android-after-restarted-recovery-{attempt:02d}.json"
        if result_path.exists() and not intent_path.exists():
            raise ObserverError("recovery result exists without its durable intent")
        if intent_path.exists():
            intent = read_direct_json(intent_path)
            if (
                intent.get("schema") != RECOVERY_INTENT_SCHEMA
                or intent.get("attempt") != attempt
                or intent.get("authority") != authority
                or intent.get("consumed_state_sha256") != state_sha256
                or intent.get("run_dir") != str(run_dir.relative_to(root))
                or intent.get("device_writes") is not False
                or intent.get("reboot") is not False
                or intent.get("odin_enumeration") is not False
                or intent.get("odin_transfer") is not False
            ):
                raise ObserverError("recovery attempt intent is invalid")
            if result_path.exists():
                previous = read_direct_json(result_path)
                if previous.get("verdict") == "PASS_R4W1C_ENUM_DIFF_OBSERVER_RECOVERY_ONLY":
                    raise ObserverError("observer recovery already passed")
            continue
        intent = {
            "schema": RECOVERY_INTENT_SCHEMA,
            "created_at_utc": utc_now(),
            "target": TARGET,
            "attempt": attempt,
            "run_dir": str(run_dir.relative_to(root)),
            "authority": authority,
            "consumed_state_sha256": state_sha256,
            "android_serial_sha256": state["android_serial_sha256"],
            "device_contact_authorized": True,
            "device_writes": False,
            "reboot": False,
            "odin_enumeration": False,
            "odin_transfer": False,
            "flash": False,
        }
        try:
            durable_create_json(intent_path, intent)
        except FileExistsError:
            continue
        return attempt, result_path, evidence_path
    raise ObserverError("observer recovery failed or was interrupted twice; stop")


def _recover_consumed_observer_with_lease(
    root: Path, args: argparse.Namespace, lease: AuthorityLease
) -> int:
    authority = lease.receipt
    with validated_consumed_observer(root, authority) as (state, run_dir, consumed_pin):
        return _recover_consumed_observer_with_pin(
            root, args, lease, state, run_dir, consumed_pin
        )


def _recover_consumed_observer_with_pin(
    root: Path,
    args: argparse.Namespace,
    lease: AuthorityLease,
    state: dict[str, Any],
    run_dir: Path,
    consumed_pin: ConsumedStatePin,
) -> int:
    authority = lease.receipt
    timeline_path = run_dir / "timeline.json"
    events = validate_timeline_prefix(read_direct_json(timeline_path))
    original_actual_events = recovery_original_actual_events(run_dir, events)
    attempt, result_path, evidence_path = reserve_recovery_attempt(
        root, run_dir, state, authority, consumed_pin
    )
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "recover-consumed-observer",
        "target": TARGET,
        "run_dir": str(run_dir),
        "attempt": attempt,
        "device_contact": True,
        "device_writes": False,
        "reboot": False,
        "download_transition": False,
        "odin_enumeration": False,
        "odin_transfer": False,
        "flash": False,
        "acceptance_decision": False,
        "verdict": "INCOMPLETE",
    }
    rc = 1
    recovery_actual_events = ["recovery-wait-start"]

    def require_recovery_continuity() -> None:
        require_authority_lease(root, lease)
        require_consumed_state_pin(consumed_pin)

    try:
        print(
            "Physically exit Download and return the same handset to exact Android. "
            "This recovery mode performs no reboot or Odin command."
        )
        require_authority_lease(root, lease)
        require_consumed_state_pin(consumed_pin)
        returned = wait_for_android_return(
            None,
            state["usb_binding"],
            args.android_wait_sec,
            expected_serial_sha256=state["android_serial_sha256"],
            continuity_check=require_recovery_continuity,
        )
        require_authority_lease(root, lease)
        require_consumed_state_pin(consumed_pin)
        durable_create_json(evidence_path, returned)
        recovery_actual_events.extend(
            ["recovery-android-transport-returned", "recovery-exact-android-verified"]
        )
        result["android_return"] = returned
        result["verdict"] = "PASS_R4W1C_ENUM_DIFF_OBSERVER_RECOVERY_ONLY"
        rc = 0
    except (ObserverError, OSError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
        result["verdict"] = "FAIL_R4W1C_ENUM_DIFF_OBSERVER_RECOVERY_INCOMPLETE"
    finally:
        result["original_actual_timeline_events"] = original_actual_events
        result["recovery_activity_events"] = recovery_actual_events
        result["timeline_event_status"] = timeline_event_status(
            original_actual_events + ["live_session_end"]
        )
        result["timeline_placeholder_semantics"] = (
            "unreached canonical slots are no-action placeholders, not milestones"
        )
        require_consumed_state_pin(consumed_pin)
        require_authority_lease(root, lease)
        preclosure_receipt = durable_create_json(
            run_dir / f"recovery-result-{attempt:02d}-preclosure.json",
            preclosure_result(result, successful=rc == 0),
        )
        require_consumed_state_pin(consumed_pin)
        require_authority_lease(root, lease)
        complete_timeline(timeline_path, events)
        require_consumed_state_pin(consumed_pin)
        require_authority_lease(root, lease)
        result["timeline"] = {"events": events, "path": str(timeline_path)}
        result["authority_final"] = lease.receipt
        result["consumed_state_final_sha256"] = consumed_pin.sha256
        result["preclosure"] = preclosure_receipt
        require_consumed_state_pin(consumed_pin)
        require_authority_lease(root, lease)
        durable_create_json(result_path, result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": result["verdict"]}, indent=2))
    return rc


def recover_consumed_observer(root: Path, args: argparse.Namespace) -> int:
    if args.ack != RECOVERY_ACK_TOKEN:
        raise ObserverError("observer recovery acknowledgement mismatch")
    with authority_session(root) as lease:
        return _recover_consumed_observer_with_lease(root, args, lease)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--observe-download-enumeration", action="store_true")
    modes.add_argument("--recover-consumed-observer", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--download-wait-sec", type=float, default=120.0)
    parser.add_argument("--confirmation-wait-sec", type=float, default=120.0)
    parser.add_argument("--android-wait-sec", type=float, default=300.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()
    try:
        if args.offline_check:
            return offline_check(root, args)
        if args.recover_consumed_observer:
            return recover_consumed_observer(root, args)
        return observe_live(root, args)
    except (ObserverError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc), "verdict": "FAIL_CLOSED"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
