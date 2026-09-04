#!/usr/bin/env python3
"""Host-only P3.37 observer binding for the first-OPEN diagnostic.

The successful P3.36 session grammar is unchanged.  This small wrapper binds
that codec to the fresh P3.37 runtime and decodes only the new failure-only
stage-3 diagnostic from retained raw bytes.  It performs no USB or device I/O.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p336_long_idle_acm_observer as predecessor
import s22plus_fyg8_p337_open_read_diag_runtime as runtime


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 33_714,
    "sha256": "f9882a9ae69711cdaa76edc6f754ea14e6192ae54a620b68475e438da97c1bb8",
}
SCHEMA = "s22plus-fyg8-p337-open-read-diagnostic-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p337-open-read-diagnostic-acm-observer-v1"
P337_RUN_ID_HEX = runtime.P337_RUN_ID_HEX
P337_RUN_ID = runtime.P337_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
MAX_INITIAL_SESSIONS = predecessor.MAX_INITIAL_SESSIONS
MAX_SESSIONS = predecessor.MAX_SESSIONS
MAX_RECONNECTS = predecessor.MAX_RECONNECTS
MAX_PHYSICAL_REOPENS = predecessor.MAX_PHYSICAL_REOPENS
PHYSICAL_REOPEN_COUNT = predecessor.PHYSICAL_REOPEN_COUNT
MAX_PREAMBLE_PAIRS = predecessor.MAX_PREAMBLE_PAIRS
MAX_RESYNC_BYTES = predecessor.MAX_RESYNC_BYTES
SESSION_TIMEOUT_SEC = predecessor.SESSION_TIMEOUT_SEC
HEADER = predecessor.HEADER


class P337ObserverBindingError(ValueError):
    """The exact P3.36 observer or P3.37 runtime binding differs."""


# The shared retained-session receipt validator raises this historical name.
# Keep one P337 error type so malformed evidence degrades to NO_PROOF instead
# of escaping the normal rollback path as AttributeError.
AuthObserverError = P337ObserverBindingError


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _stable_predecessor() -> bytes:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise P337ObserverBindingError("P3.36 observer source is unavailable") from exc
    if (
        direct != direct.resolve(strict=True)
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or identity(payload) != SOURCE_IDENTITY
    ):
        raise P337ObserverBindingError("P3.36 observer source identity differs")
    return payload


_PREDECESSOR_PAYLOAD = _stable_predecessor()


def decode_frame(payload: bytes) -> Any:
    try:
        return predecessor.decode_frame(payload)
    except Exception as exc:
        raise P337ObserverBindingError(str(exc)) from exc


def parse_open_read_diagnostic_frame(payload: bytes) -> dict[str, Any]:
    """Decode one exact retained stage-3 frame without inferring causality."""
    frame = decode_frame(payload)
    try:
        if (
            frame.frame_type != runtime.DIAGNOSTIC_FRAME_TYPE
            or frame.sequence != 0
            or len(frame.payload) != predecessor.DIAGNOSTIC.size
        ):
            raise P337ObserverBindingError("P3.37 diagnostic frame differs")
        stage, code = predecessor.DIAGNOSTIC.unpack(frame.payload)
        classification = runtime.classify_open_read_diagnostic(stage, code)
    except (ValueError, P337ObserverBindingError) as exc:
        raise P337ObserverBindingError(str(exc)) from exc
    return {
        "stage": stage,
        "code": code,
        "classification": classification,
        "raw": identity(payload),
        "causal_result_allowed": False,
        "candidate_success": False,
    }


def parse_retained_open_read_diagnostic(payload: bytes) -> dict[str, Any]:
    """Find the final exact frame after one or more complete preambles."""
    if type(payload) is not bytes or len(payload) < HEADER.size:
        raise P337ObserverBindingError("P3.37 retained payload is too short")
    offset = 0
    frames: list[bytes] = []
    while offset < len(payload):
        if payload.startswith(DEVICE_BANNER, offset):
            offset += len(DEVICE_BANNER)
            continue
        if offset + HEADER.size > len(payload):
            raise P337ObserverBindingError("P3.37 retained frame is truncated")
        header = payload[offset : offset + HEADER.size]
        fields = HEADER.unpack(header)
        length = fields[3]
        if type(length) is not int or length > runtime.MAX_FRAME_PAYLOAD:
            raise P337ObserverBindingError("P3.37 retained frame length differs")
        end = offset + HEADER.size + length
        if end > len(payload):
            raise P337ObserverBindingError("P3.37 retained frame body is truncated")
        frames.append(payload[offset:end])
        offset = end
    if not frames:
        raise P337ObserverBindingError("P3.37 retained diagnostic is absent")
    return parse_open_read_diagnostic_frame(frames[-1]) | {
        "frame_count": len(frames),
        "retained": identity(payload),
    }


def audit_binding() -> dict[str, Any]:
    _stable_predecessor()
    runtime_receipt = runtime.audit_binding()
    if (
        runtime_receipt.get("run_id_hex") != P337_RUN_ID_HEX
        or DEVICE_BANNER == predecessor.DEVICE_BANNER
        or DEFAULT_COMMANDS == tuple(predecessor.DEFAULT_COMMANDS)
        or MAX_SESSIONS != 3
    ):
        raise P337ObserverBindingError("P3.37 observer/runtime binding differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "run_id_hex": P337_RUN_ID_HEX,
        "successful_session_grammar_unchanged": True,
        "failure_diagnostic_stage": runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "failure_diagnostic_best_effort": True,
        "retry_added": False,
        "timeout_changed": False,
        "device_contact": False,
        "live_authorized": False,
    }


__all__ = sorted({
    "CONTRACT_ID", "DEFAULT_COMMANDS", "DEVICE_BANNER", "HEADER",
    "MAX_INITIAL_SESSIONS", "MAX_PHYSICAL_REOPENS", "MAX_PREAMBLE_PAIRS",
    "MAX_RECONNECTS", "MAX_RESYNC_BYTES", "MAX_SESSIONS",
    "AuthObserverError", "P337ObserverBindingError", "P337_RUN_ID", "P337_RUN_ID_HEX",
    "PHYSICAL_REOPEN_COUNT", "SCHEMA", "SESSION_TIMEOUT_SEC", "SOURCE",
    "SOURCE_IDENTITY", "audit_binding", "decode_frame", "identity",
    "parse_open_read_diagnostic_frame", "parse_retained_open_read_diagnostic",
})
