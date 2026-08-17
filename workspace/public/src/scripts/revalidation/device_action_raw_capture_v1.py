#!/usr/bin/env python3
"""Durable raw-first capture boundary for connected device observers.

This module owns subprocess stream acquisition only.  It deliberately returns
an immutable handle rather than stdout/stderr bytes so a parser cannot run
before both streams and their capture receipt are file-fsynced and published.
It grants no device, command, target, tier, retry, or live authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import selectors
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "device_action_raw_capture_v1"
MAX_STREAM_BYTES = 128 * 1024 * 1024
NAME_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}")
FILE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}")
HEX64_RE = re.compile(r"[0-9a-f]{64}")


class RawCaptureError(RuntimeError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RawCaptureError(f"duplicate raw-capture key: {key}")
        value[key] = item
    return value


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _direct_directory(path: Path, *, create: bool = False) -> Path:
    direct = path.absolute()
    if create and not direct.exists() and not direct.is_symlink():
        parent = _direct_directory(direct.parent)
        try:
            os.mkdir(direct, 0o700)
        except FileExistsError:
            pass
        _fsync_dir(parent)
    try:
        entry = os.lstat(direct)
    except OSError as exc:
        raise RawCaptureError(f"capture directory is unavailable: {direct}") from exc
    if (
        stat.S_ISLNK(entry.st_mode)
        or not stat.S_ISDIR(entry.st_mode)
        or direct.resolve(strict=True) != direct
    ):
        raise RawCaptureError(f"capture directory is indirect: {direct}")
    return direct


def prepare_capture_dir(parent: Path, name: str = "raw-captures") -> Path:
    if NAME_RE.fullmatch(name) is None:
        raise RawCaptureError("capture directory name is invalid")
    return _direct_directory(_direct_directory(parent) / name, create=True)


def _identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _open_stream(path: Path) -> int:
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_CLOEXEC
        | getattr(os, "O_NOFOLLOW", 0),
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
            or metadata.st_size != 0
        ):
            raise RawCaptureError(f"new raw stream identity differs: {path.name}")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        try:
            written = os.write(descriptor, payload[offset:])
        except InterruptedError:
            continue
        if written <= 0:
            raise RawCaptureError("raw stream write made no progress")
        offset += written


def _stable_bytes(path: Path, maximum: int) -> tuple[bytes, os.stat_result]:
    if maximum < 0 or maximum > MAX_STREAM_BYTES:
        raise RawCaptureError("raw stream read bound is invalid")
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_nlink != 1
        ):
            raise RawCaptureError(f"raw stream metadata differs: {path.name}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise RawCaptureError(f"raw stream exceeds read bound: {path.name}")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    if _identity(before) != _identity(after) or _identity(after) != _identity(current):
        raise RawCaptureError(f"raw stream changed while reading: {path.name}")
    return b"".join(chunks), after


def _stream_receipt(path: Path, maximum: int) -> dict[str, Any]:
    payload, metadata = _stable_bytes(path, maximum)
    return {
        "name": path.name,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "mode": "0400",
        "nlink": metadata.st_nlink,
    }


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise RawCaptureError("raw capture receipt is not canonical JSON") from exc


def _durable_create(path: Path, payload: bytes) -> None:
    descriptor = _open_stream(path)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
        ):
            raise RawCaptureError(f"raw capture receipt identity differs: {path.name}")
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)


@dataclass(frozen=True)
class RawCaptureHandle:
    receipt_path: Path
    name: str
    returncode: int | None
    timed_out: bool
    output_exceeded: bool
    producer_error_type: str | None
    stdout: Mapping[str, Any]
    stderr: Mapping[str, Any]

    @property
    def stdout_path(self) -> Path:
        return self.receipt_path.parent / str(self.stdout["name"])

    @property
    def stderr_path(self) -> Path:
        return self.receipt_path.parent / str(self.stderr["name"])


def _strict_stream(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "mode",
        "name",
        "nlink",
        "sha256",
        "size",
    }:
        raise RawCaptureError("raw stream receipt shape differs")
    if (
        not isinstance(value["name"], str)
        or FILE_RE.fullmatch(value["name"]) is None
        or value["mode"] != "0400"
        or type(value["nlink"]) is not int
        or value["nlink"] != 1
        or type(value["size"]) is not int
        or not 0 <= value["size"] <= MAX_STREAM_BYTES
        or not isinstance(value["sha256"], str)
        or HEX64_RE.fullmatch(value["sha256"]) is None
    ):
        raise RawCaptureError("raw stream receipt value differs")
    return value


def load_handle(receipt_path: Path) -> RawCaptureHandle:
    direct = receipt_path.absolute()
    payload, _metadata = _stable_bytes(direct, 64 * 1024)
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RawCaptureError("raw capture receipt cannot be decoded") from exc
    required = {
        "argv0_name",
        "elapsed_msec",
        "name",
        "output_exceeded",
        "producer_error_type",
        "returncode",
        "schema",
        "stderr",
        "stdout",
        "timed_out",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise RawCaptureError("raw capture receipt shape differs")
    name = value["name"]
    if (
        value["schema"] != SCHEMA
        or not isinstance(name, str)
        or NAME_RE.fullmatch(name) is None
        or not isinstance(value["argv0_name"], str)
        or not value["argv0_name"]
        or len(value["argv0_name"]) > 255
        or type(value["elapsed_msec"]) is not int
        or value["elapsed_msec"] < 0
        or type(value["timed_out"]) is not bool
        or type(value["output_exceeded"]) is not bool
        or (
            value["returncode"] is not None
            and type(value["returncode"]) is not int
        )
        or (
            value["producer_error_type"] is not None
            and (
                not isinstance(value["producer_error_type"], str)
                or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", value["producer_error_type"])
                is None
            )
        )
    ):
        raise RawCaptureError("raw capture receipt value differs")
    expected_receipt_name = f"{name}.capture.json"
    if direct.name != expected_receipt_name:
        raise RawCaptureError("raw capture receipt pathname differs")
    stdout = _strict_stream(value["stdout"])
    stderr = _strict_stream(value["stderr"])
    if stdout["name"] == stderr["name"] or receipt_path.name in {
        stdout["name"],
        stderr["name"],
    }:
        raise RawCaptureError("raw capture filenames collide")
    handle = RawCaptureHandle(
        receipt_path=direct,
        name=name,
        returncode=value["returncode"],
        timed_out=value["timed_out"],
        output_exceeded=value["output_exceeded"],
        producer_error_type=value["producer_error_type"],
        stdout=stdout,
        stderr=stderr,
    )
    for path, expected in (
        (handle.stdout_path, stdout),
        (handle.stderr_path, stderr),
    ):
        current = _stream_receipt(path, int(expected["size"]))
        if current != expected:
            raise RawCaptureError(f"raw stream differs from receipt: {path.name}")
    return handle


class RawCaptureWriter:
    """One no-clobber two-stream producer; finalize before any parsing."""

    def __init__(
        self,
        capture_dir: Path,
        name: str,
        *,
        stdout_maximum: int,
        stderr_maximum: int,
        argv0_name: str = "direct-source",
        stdout_name: str | None = None,
        stderr_name: str | None = None,
    ) -> None:
        if (
            not isinstance(name, str)
            or NAME_RE.fullmatch(name) is None
            or type(stdout_maximum) is not int
            or not 0 <= stdout_maximum <= MAX_STREAM_BYTES
            or type(stderr_maximum) is not int
            or not 0 <= stderr_maximum <= MAX_STREAM_BYTES
            or stdout_maximum + stderr_maximum <= 0
            or not isinstance(argv0_name, str)
            or not argv0_name
            or len(argv0_name) > 255
        ):
            raise RawCaptureError("raw capture writer bounds are invalid")
        self.capture_dir = _direct_directory(capture_dir)
        self.name = name
        stdout_name = stdout_name or f"{name}.stdout.bin"
        stderr_name = stderr_name or f"{name}.stderr.bin"
        if (
            not isinstance(stdout_name, str)
            or not isinstance(stderr_name, str)
            or FILE_RE.fullmatch(stdout_name) is None
            or FILE_RE.fullmatch(stderr_name) is None
            or stdout_name == stderr_name
            or f"{name}.capture.json" in {stdout_name, stderr_name}
        ):
            raise RawCaptureError("raw capture stream filename is invalid")
        self.stdout_path = self.capture_dir / stdout_name
        self.stderr_path = self.capture_dir / stderr_name
        self.receipt_path = self.capture_dir / f"{name}.capture.json"
        if self.receipt_path.exists() or self.receipt_path.is_symlink():
            raise RawCaptureError("raw capture receipt already exists")
        self.stdout_fd = _open_stream(self.stdout_path)
        try:
            self.stderr_fd = _open_stream(self.stderr_path)
        except BaseException:
            os.close(self.stdout_fd)
            raise
        self.stdout_maximum = stdout_maximum
        self.stderr_maximum = stderr_maximum
        self.argv0_name = argv0_name
        self.stdout_size = 0
        self.stderr_size = 0
        self.started = time.monotonic()
        self.finished = False

    def write_stdout(self, payload: bytes) -> None:
        if self.finished:
            raise RawCaptureError("raw capture writer is already finalized")
        if self.stdout_size + len(payload) > self.stdout_maximum:
            raise RawCaptureError("raw stdout exceeds its acquisition bound")
        _write_all(self.stdout_fd, payload)
        self.stdout_size += len(payload)

    def write_stderr(self, payload: bytes) -> None:
        if self.finished:
            raise RawCaptureError("raw capture writer is already finalized")
        if self.stderr_size + len(payload) > self.stderr_maximum:
            raise RawCaptureError("raw stderr exceeds its acquisition bound")
        _write_all(self.stderr_fd, payload)
        self.stderr_size += len(payload)

    def stream_fds(self) -> tuple[int, int]:
        if self.finished:
            raise RawCaptureError("raw capture writer is already finalized")
        return self.stdout_fd, self.stderr_fd

    def current_sizes(self) -> tuple[int, int]:
        if self.finished:
            raise RawCaptureError("raw capture writer is already finalized")
        return os.fstat(self.stdout_fd).st_size, os.fstat(self.stderr_fd).st_size

    def finalize(
        self,
        *,
        returncode: int | None,
        timed_out: bool = False,
        output_exceeded: bool = False,
        producer_error_type: str | None = None,
    ) -> RawCaptureHandle:
        if self.finished:
            raise RawCaptureError("raw capture writer was finalized twice")
        if (
            returncode is not None
            and type(returncode) is not int
            or type(timed_out) is not bool
            or type(output_exceeded) is not bool
            or (
                producer_error_type is not None
                and (
                    not isinstance(producer_error_type, str)
                    or re.fullmatch(
                        r"[A-Za-z_][A-Za-z0-9_]{0,127}", producer_error_type
                    )
                    is None
                )
            )
        ):
            raise RawCaptureError("raw capture outcome is invalid")
        self.finished = True
        try:
            for descriptor, expected in (
                (self.stdout_fd, self.stdout_size),
                (self.stderr_fd, self.stderr_size),
            ):
                os.fchmod(descriptor, 0o400)
                os.fsync(descriptor)
                metadata = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or stat.S_IMODE(metadata.st_mode) != 0o400
                    or metadata.st_nlink != 1
                    or metadata.st_size != expected
                ):
                    raise RawCaptureError("raw stream final identity differs")
        finally:
            os.close(self.stdout_fd)
            os.close(self.stderr_fd)
        _fsync_dir(self.capture_dir)
        stdout = _stream_receipt(self.stdout_path, self.stdout_maximum)
        stderr = _stream_receipt(self.stderr_path, self.stderr_maximum)
        value = {
            "argv0_name": self.argv0_name,
            "elapsed_msec": max(0, round((time.monotonic() - self.started) * 1000)),
            "name": self.name,
            "output_exceeded": output_exceeded,
            "producer_error_type": producer_error_type,
            "returncode": returncode,
            "schema": SCHEMA,
            "stderr": stderr,
            "stdout": stdout,
            "timed_out": timed_out,
        }
        _durable_create(self.receipt_path, _canonical(value))
        return load_handle(self.receipt_path)


def _terminate(process: subprocess.Popen[Any]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def acquire_command(
    argv: Sequence[str],
    capture_dir: Path,
    name: str,
    *,
    timeout: float,
    stdout_maximum: int,
    stderr_maximum: int,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    executable: str | None = None,
    pass_fds: Sequence[int] = (),
    start_new_session: bool = False,
    stdout_name: str | None = None,
    stderr_name: str | None = None,
) -> RawCaptureHandle:
    """Run one command and publish both raw streams before returning a handle."""

    if (
        isinstance(argv, (str, bytes))
        or not argv
        or any(not isinstance(value, str) or not value for value in argv)
        or isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or not 0.1 <= timeout <= 7200
    ):
        raise RawCaptureError("raw command invocation is invalid")
    writer = RawCaptureWriter(
        capture_dir,
        name,
        stdout_maximum=stdout_maximum,
        stderr_maximum=stderr_maximum,
        argv0_name=Path(argv[0]).name,
        stdout_name=stdout_name,
        stderr_name=stderr_name,
    )
    process: subprocess.Popen[Any] | None = None
    selector: selectors.BaseSelector | None = None
    timed_out = False
    exceeded = False
    producer_error_type: str | None = None
    returncode: int | None = None
    interruption: BaseException | None = None
    try:
        try:
            process = subprocess.Popen(
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                cwd=cwd,
                env=None if env is None else dict(env),
                executable=executable,
                pass_fds=tuple(pass_fds),
                start_new_session=start_new_session,
            )
        except OSError as exc:
            producer_error_type = type(exc).__name__
        if process is not None:
            deadline = time.monotonic() + timeout
            selector = selectors.DefaultSelector()
            assert process.stdout is not None
            assert process.stderr is not None
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    _terminate(process)
                    break
                events = selector.select(min(0.1, remaining))
                if not events:
                    if process.poll() is not None:
                        # Drain both pipes to EOF after child exit.
                        continue
                    continue
                for key, _mask in events:
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    current = (
                        writer.stdout_size
                        if key.data == "stdout"
                        else writer.stderr_size
                    )
                    maximum = (
                        stdout_maximum
                        if key.data == "stdout"
                        else stderr_maximum
                    )
                    allowed = max(0, maximum - current)
                    if allowed:
                        if key.data == "stdout":
                            writer.write_stdout(chunk[:allowed])
                        else:
                            writer.write_stderr(chunk[:allowed])
                    if len(chunk) > allowed:
                        exceeded = True
                        _terminate(process)
                        break
                if exceeded:
                    break
            if process.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    _terminate(process)
                else:
                    try:
                        process.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:
                        timed_out = True
                        _terminate(process)
            returncode = process.returncode
    except BaseException as exc:
        if process is not None and process.poll() is None:
            _terminate(process)
            returncode = process.returncode
        producer_error_type = type(exc).__name__
        if not isinstance(exc, Exception):
            interruption = exc
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
    handle = writer.finalize(
        returncode=returncode,
        timed_out=timed_out,
        output_exceeded=exceeded,
        producer_error_type=producer_error_type,
    )
    if interruption is not None:
        raise interruption
    return handle


def publish_captured_bytes(
    capture_dir: Path,
    name: str,
    *,
    stdout: bytes,
    stderr: bytes = b"",
    returncode: int = 0,
    argv0_name: str = "fixture-source",
    stdout_name: str | None = None,
    stderr_name: str | None = None,
) -> RawCaptureHandle:
    """Publish already-acquired bounded bytes before handing them to a parser."""

    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        raise RawCaptureError("captured byte fixture has an invalid type")
    writer = RawCaptureWriter(
        capture_dir,
        name,
        stdout_maximum=len(stdout),
        stderr_maximum=max(1, len(stderr)),
        argv0_name=argv0_name,
        stdout_name=stdout_name,
        stderr_name=stderr_name,
    )
    writer.write_stdout(stdout)
    writer.write_stderr(stderr)
    return writer.finalize(returncode=returncode)


def read_stdout(handle: RawCaptureHandle, *, maximum: int) -> bytes:
    if not isinstance(handle, RawCaptureHandle):
        raise RawCaptureError("raw parser input is not a capture handle")
    current = load_handle(handle.receipt_path)
    if current != handle:
        raise RawCaptureError("raw capture handle changed before parse")
    payload, _metadata = _stable_bytes(handle.stdout_path, maximum)
    return payload


def read_stderr(handle: RawCaptureHandle, *, maximum: int) -> bytes:
    if not isinstance(handle, RawCaptureHandle):
        raise RawCaptureError("raw parser input is not a capture handle")
    current = load_handle(handle.receipt_path)
    if current != handle:
        raise RawCaptureError("raw capture handle changed before parse")
    payload, _metadata = _stable_bytes(handle.stderr_path, maximum)
    return payload


def require_success(handle: RawCaptureHandle) -> RawCaptureHandle:
    if not isinstance(handle, RawCaptureHandle):
        raise RawCaptureError("success input is not a capture handle")
    current = load_handle(handle.receipt_path)
    if current != handle:
        raise RawCaptureError("raw capture handle changed before success check")
    if handle.producer_error_type is not None:
        raise RawCaptureError(
            f"raw producer failed: {handle.producer_error_type}"
        )
    if handle.timed_out:
        raise RawCaptureError("raw producer timed out")
    if handle.output_exceeded:
        raise RawCaptureError("raw producer exceeded its output bound")
    if handle.returncode != 0:
        raise RawCaptureError(f"raw producer returned rc={handle.returncode}")
    if int(handle.stderr["size"]) != 0:
        raise RawCaptureError("raw producer emitted stderr")
    return handle


def decode_success_stdout(
    handle: RawCaptureHandle,
    *,
    maximum: int,
    encoding: str = "utf-8",
    strip: bool = True,
) -> str:
    require_success(handle)
    payload = read_stdout(handle, maximum=maximum)
    try:
        value = payload.decode(encoding, "strict")
    except (LookupError, UnicodeError) as exc:
        raise RawCaptureError(f"raw stdout is not strict {encoding}") from exc
    return value.strip() if strip else value

