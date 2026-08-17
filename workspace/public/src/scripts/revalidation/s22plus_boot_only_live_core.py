#!/usr/bin/env python3
"""Mechanical safety primitives for new S22+ boot-only live gates.

This module deliberately owns no candidate pins, target geometry, policy text,
or proof verdict.  A target-specific helper must keep those trust decisions
local while reusing these filesystem, timeline, capture, and marker mechanics.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import device_action_raw_capture_v1 as raw_capture


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


class LiveCoreError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_stable_file(path: Path) -> dict[str, Any]:
    """Hash one direct regular file without loading it into memory."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise LiveCoreError(f"not a direct regular file: {path}")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = path.stat(follow_symlinks=False)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    identity_current = (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
    )
    if identity_before != identity_after or identity_after != identity_current:
        raise LiveCoreError(f"file identity changed during hash: {path}")
    if total != before.st_size:
        raise LiveCoreError(f"short file hash: {path}")
    return {"size": total, "sha256": digest.hexdigest()}


def durable_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def durable_create_json(path: Path, value: Any) -> None:
    """Create an un-overwritable durable state record without a TOCTOU gap."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    if path.exists() or path.is_symlink():
        raise LiveCoreError(f"state already exists: {path}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        _fsync_directory(path.parent)
    except FileExistsError as exc:
        raise LiveCoreError(f"state was created concurrently: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def append_event(path: Path, events: list[dict[str, str]], name: str) -> None:
    if name not in TIMELINE_NAMES:
        raise LiveCoreError(f"unknown timeline event: {name}")
    expected_index = len(events)
    if expected_index >= len(TIMELINE_NAMES) or TIMELINE_NAMES[expected_index] != name:
        raise LiveCoreError(f"out-of-order timeline event: {name}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    durable_write_json(path, {"events": events})


def append_remaining_events(path: Path, events: list[dict[str, str]]) -> None:
    for name in TIMELINE_NAMES[len(events) :]:
        append_event(path, events, name)


def timeline_complete(events: list[dict[str, str]]) -> bool:
    return [event.get("name") for event in events] == list(TIMELINE_NAMES) and all(
        set(event) == {"name", "timestamp_utc"} for event in events
    )


def allocate_run_dir(
    root: Path, run_root: Path, prefix: str, requested: Path | None
) -> Path:
    base = (root / run_root).resolve()
    path = requested or run_root / f"{prefix}-{utc_stamp()}"
    path = path if path.is_absolute() else root / path
    if path.is_symlink():
        raise LiveCoreError("run directory must not be a symlink")
    resolved = path.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise LiveCoreError("run directory is outside the private run root") from exc
    resolved.mkdir(parents=True, exist_ok=False)
    _fsync_directory(resolved.parent)
    return resolved


def read_stable_file(path: Path, *, maximum: int | None = None) -> bytes:
    """Read one direct regular file while binding descriptor and path identity."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise LiveCoreError(f"not a direct regular file: {path}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if maximum is not None and total > maximum:
                raise LiveCoreError(f"file exceeds bound: {path} > {maximum}")
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = path.stat(follow_symlinks=False)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    identity_current = (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
    )
    if identity_before != identity_after or identity_after != identity_current:
        raise LiveCoreError(f"file identity changed during read: {path}")
    return b"".join(chunks)


def capture_adb_exec_out(
    serial: str,
    command: str,
    output_path: Path,
    *,
    root: bool,
    timeout: float,
    maximum: int,
) -> dict[str, Any]:
    """Stream one adb exec-out command to EOF with a live size and time bound."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path = output_path.with_suffix(output_path.suffix + ".stderr")
    remote = f"su -c {shlex.quote(command)}" if root else f"sh -c {shlex.quote(command)}"
    argv = ["adb", "-s", serial, "exec-out", remote]
    started = time.monotonic()
    name = re.sub(r"[^a-z0-9]+", "-", output_path.stem.lower()).strip("-")
    if not name:
        raise LiveCoreError("observer output name is invalid")
    try:
        handle = raw_capture.acquire_command(
            argv,
            output_path.parent,
            name[:96],
            timeout=timeout,
            stdout_maximum=maximum,
            stderr_maximum=64 * 1024,
            stdout_name=output_path.name,
            stderr_name=stderr_path.name,
        )
        raw_capture.require_success(handle)
        payload = raw_capture.read_stdout(handle, maximum=maximum)
    except raw_capture.RawCaptureError as exc:
        raise LiveCoreError(f"observer raw capture failed: {command}: {exc}") from exc
    size = len(payload)
    stderr_size = int(handle.stderr["size"])
    return {
        "path": str(output_path),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "returncode": handle.returncode,
        "stderr_bytes": stderr_size,
        "read_to_eof": True,
        "elapsed_sec": round(time.monotonic() - started, 6),
        "raw_capture_receipt": {
            "path": str(handle.receipt_path),
            "size": handle.receipt_path.stat().st_size,
            "sha256": sha256_bytes(handle.receipt_path.read_bytes()),
        },
    }


def classify_marker_family(
    payload: bytes,
    *,
    exact_marker: bytes,
    family_prefix: bytes,
    historical_family: bytes | None = None,
) -> dict[str, Any]:
    """Classify one delimiter-anchored marker family without loose substrings."""

    if not exact_marker.startswith(b"\n") or not exact_marker.endswith(b"\n"):
        raise LiveCoreError("exact marker must include leading and trailing newlines")
    if not family_prefix.startswith(b"[[") or not family_prefix.endswith(b"|"):
        raise LiveCoreError("marker family must be delimiter anchored")
    exact_core = exact_marker[1:-1]
    records: list[tuple[int, bytes]] = []
    partial_offsets: list[int] = []
    cursor = 0
    while True:
        start = payload.find(family_prefix, cursor)
        if start < 0:
            break
        end = payload.find(b"]]", start + len(family_prefix))
        if end < 0:
            partial_offsets.append(start)
            cursor = start + len(family_prefix)
            continue
        records.append((start, payload[start : end + 2]))
        cursor = end + 2

    exact_count = payload.count(exact_marker)
    exact_record_count = sum(record == exact_core for _, record in records)
    foreign_records = [record for _, record in records if record != exact_core]
    delimiter_mismatch_count = max(0, exact_record_count - exact_count)
    minimum = len(family_prefix)
    partial_tail = any(
        payload.endswith(exact_marker[:length])
        for length in range(minimum, len(exact_marker))
    )
    partial_head = any(
        payload.startswith(exact_marker[-length:])
        for length in range(minimum, len(exact_marker))
    )
    family_count = len(records) + len(partial_offsets)
    integrity_issue = bool(
        foreign_records
        or partial_offsets
        or partial_head
        or partial_tail
        or delimiter_mismatch_count
        or exact_record_count != exact_count
    )
    if integrity_issue:
        classification = "MARKER_FAMILY_INTEGRITY_FAILURE"
    elif exact_count >= 1:
        classification = "EXACT_MARKER_PRESENT"
    else:
        classification = "MARKER_FAMILY_ABSENT"
    return {
        "classification": classification,
        "exact_count": exact_count,
        "exact_record_count": exact_record_count,
        "family_count": family_count,
        "foreign_count": len(foreign_records),
        "foreign_records_hex": [record.hex() for record in foreign_records],
        "unterminated_offsets": partial_offsets,
        "delimiter_mismatch_count": delimiter_mismatch_count,
        "partial_at_head": partial_head,
        "partial_at_tail": partial_tail,
        "historical_family_count": (
            payload.count(historical_family) if historical_family is not None else 0
        ),
        "integrity_issue": integrity_issue,
        "baseline_absent": family_count == 0 and not partial_head and not partial_tail,
        "acceptance_present": exact_count >= 1 and not integrity_issue,
    }
