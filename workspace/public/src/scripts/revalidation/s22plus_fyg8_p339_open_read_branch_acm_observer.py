#!/usr/bin/env python3
"""Host-only P3.39 observer for first-OPEN site and header capture.

The inherited P3.38 frame codec and retained-session grammar remain unchanged.
One stage-3 reason frame is followed, for grammar/semantic rejection only, by
up to four existing diagnostic frames whose signed code fields preserve the
four little-endian words of the rejected 16-byte header.  Partial best-effort
capture remains no-proof.  This module performs no USB or device I/O.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p338_open_read_branch_acm_observer as predecessor
import s22plus_fyg8_p339_open_read_branch_runtime as runtime


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 7_927,
    "sha256": "af34d6aca1431ea328fc568c4d3cdec9ea1d1532cf3cef0260d66c902e560f1f",
}
SCHEMA = "s22plus-fyg8-p339-open-header-capture-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p339-open-header-capture-acm-observer-v1"
P339_RUN_ID_HEX = runtime.P339_RUN_ID_HEX
P339_RUN_ID = runtime.P339_RUN_ID
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
DIAGNOSTIC = predecessor.DIAGNOSTIC


class P339ObserverBindingError(ValueError):
    """The exact P3.38 observer or P3.39 runtime binding differs."""


AuthObserverError = P339ObserverBindingError


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
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
        raise P339ObserverBindingError("P3.38 observer source is unavailable") from exc
    if (
        direct != direct.resolve(strict=True)
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or identity(payload) != SOURCE_IDENTITY
        or predecessor.P338_RUN_ID_HEX != runtime.P338_PREDECESSOR_RUN_ID_HEX
    ):
        raise P339ObserverBindingError("P3.38 observer binding differs")
    return payload


_PREDECESSOR_PAYLOAD = _stable_predecessor()


def decode_frame(payload: bytes) -> Any:
    try:
        return predecessor.decode_frame(payload)
    except Exception as exc:
        raise P339ObserverBindingError(str(exc)) from exc


def parse_open_read_branch_frame(payload: bytes) -> dict[str, Any]:
    """Decode one exact stage-3 branch frame without inferring causality."""

    frame = decode_frame(payload)
    try:
        if (
            frame.frame_type != runtime.DIAGNOSTIC_FRAME_TYPE
            or frame.sequence != 0
            or len(frame.payload) != DIAGNOSTIC.size
        ):
            raise P339ObserverBindingError("P3.39 diagnostic frame differs")
        stage, code = DIAGNOSTIC.unpack(frame.payload)
        classification = runtime.classify_open_read_branch(stage, code)
    except (ValueError, P339ObserverBindingError) as exc:
        raise P339ObserverBindingError(str(exc)) from exc
    return {
        "stage": stage,
        "code": code,
        "branch_ordinal": code,
        "classification": classification,
        "raw": identity(payload),
        "causal_result_allowed": False,
        "candidate_success": False,
    }


def parse_open_read_diagnostic_frame(payload: bytes) -> dict[str, Any]:
    """Compatibility spelling retained for the inherited P338 runner ABI."""

    return parse_open_read_branch_frame(payload)


def _header_detail(header: bytes, branch: int) -> str:
    magic, version, frame_type, length, sequence, _crc = HEADER.unpack(header)
    if branch == runtime.OPEN_READ_BRANCH_HEADER_VALIDATION:
        if magic != runtime.FRAME_MAGIC:
            return "magic"
        if version != runtime.FRAME_VERSION:
            return "version"
        if length > runtime.MAX_FRAME_PAYLOAD:
            return "maximum-length"
        return "unexplained-header-grammar"
    if branch == runtime.OPEN_READ_BRANCH_OPEN_SEMANTIC:
        if frame_type != runtime.FRAME_OPEN:
            return "type"
        if sequence != 0:
            return "sequence"
        if length != len(runtime.P339_RUN_ID):
            return "exact-length"
        return "run-id"
    raise P339ObserverBindingError("P3.39 header detail branch differs")


def parse_retained_open_read_branch(payload: bytes) -> dict[str, Any]:
    """Decode one reason and its ordered best-effort header-word suffix."""

    if type(payload) is not bytes or len(payload) < HEADER.size:
        raise P339ObserverBindingError("P3.39 retained payload is too short")
    offset = 0
    frames: list[bytes] = []
    while offset < len(payload):
        if payload.startswith(DEVICE_BANNER, offset):
            offset += len(DEVICE_BANNER)
            continue
        if offset + HEADER.size > len(payload):
            raise P339ObserverBindingError("P3.39 retained frame is truncated")
        header = payload[offset : offset + HEADER.size]
        fields = HEADER.unpack(header)
        length = fields[3]
        if type(length) is not int or length > runtime.MAX_FRAME_PAYLOAD:
            raise P339ObserverBindingError("P3.39 retained frame length differs")
        end = offset + HEADER.size + length
        if end > len(payload):
            raise P339ObserverBindingError("P3.39 retained frame body is truncated")
        frames.append(payload[offset:end])
        offset = end
    if not frames:
        raise P339ObserverBindingError("P3.39 retained diagnostic is absent")

    decoded: list[tuple[int, int]] = []
    for encoded in frames:
        frame = decode_frame(encoded)
        if (
            frame.frame_type != runtime.DIAGNOSTIC_FRAME_TYPE
            or frame.sequence != 0
            or len(frame.payload) != DIAGNOSTIC.size
        ):
            raise P339ObserverBindingError("P3.39 retained frame is not diagnostic")
        decoded.append(DIAGNOSTIC.unpack(frame.payload))
    reason_indices = [
        index
        for index, (stage, code) in enumerate(decoded)
        if stage == runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
        and code in runtime.OPEN_READ_BRANCHES
    ]
    if len(reason_indices) != 1:
        raise P339ObserverBindingError("P3.39 reason frame count differs")
    reason_index = reason_indices[0]
    reason = parse_open_read_branch_frame(frames[reason_index])
    suffix = decoded[reason_index + 1 :]
    expected_stages = runtime.OPEN_HEADER_WORD_STAGES
    branch = reason["branch_ordinal"]
    capture_expected = branch in {
        runtime.OPEN_READ_BRANCH_HEADER_VALIDATION,
        runtime.OPEN_READ_BRANCH_OPEN_SEMANTIC,
    }
    if not capture_expected and suffix:
        raise P339ObserverBindingError("P3.39 unexpected header capture exists")
    if capture_expected:
        stages = tuple(stage for stage, _code in suffix)
        if len(suffix) > len(expected_stages) or stages != expected_stages[: len(stages)]:
            raise P339ObserverBindingError("P3.39 header word order differs")
    words = [code & 0xFFFFFFFF for _stage, code in suffix]
    header = b"".join(word.to_bytes(4, "little") for word in words)
    complete = len(header) == runtime.OPEN_HEADER_SIZE
    if len(header) > runtime.OPEN_HEADER_SIZE:
        raise P339ObserverBindingError("P3.39 header capture exceeds its bound")
    header_fields: dict[str, Any] | None = None
    mismatch: str | None = None
    if complete:
        magic, version, frame_type, length, sequence, crc = HEADER.unpack(header)
        header_fields = {
            "magic_hex": magic.hex(),
            "version": version,
            "frame_type": frame_type,
            "payload_length": length,
            "sequence": sequence,
            "crc": crc,
        }
        mismatch = _header_detail(header, branch)
    return reason | {
        "frame_count": len(frames),
        "retained": identity(payload),
        "reason_frame_index": reason_index,
        "header_word_stages": list(expected_stages),
        "header_word_count": len(words),
        "header_snapshot_complete": complete,
        "header_snapshot_hex": header.hex(),
        "header_snapshot": identity(header),
        "header_fields": header_fields,
        "mismatch": mismatch,
    }


def parse_retained_open_read_diagnostic(payload: bytes) -> dict[str, Any]:
    """Compatibility spelling retained for the inherited P338 runner ABI."""

    return parse_retained_open_read_branch(payload)


def audit_binding() -> dict[str, Any]:
    _stable_predecessor()
    runtime_receipt = runtime.audit_binding()
    if (
        runtime_receipt.get("run_id_hex") != P339_RUN_ID_HEX
        or DEVICE_BANNER == predecessor.DEVICE_BANNER
        or DEFAULT_COMMANDS == tuple(predecessor.DEFAULT_COMMANDS)
        or MAX_SESSIONS != 3
        or runtime_receipt.get("open_read_branch_count") != 5
        or tuple(runtime_receipt.get("open_header_word_stages", ())) != (4, 5, 6, 7)
    ):
        raise P339ObserverBindingError("P3.39 observer/runtime binding differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "run_id_hex": P339_RUN_ID_HEX,
        "successful_session_grammar_unchanged": True,
        "failure_diagnostic_stage": runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "failure_diagnostic_best_effort": True,
        "open_read_branch_ordinals": dict(runtime.OPEN_READ_BRANCHES),
        "open_read_branch_count": 5,
        "open_header_word_stages": list(runtime.OPEN_HEADER_WORD_STAGES),
        "open_header_size": runtime.OPEN_HEADER_SIZE,
        "diagnostic_payload_unchanged": True,
        "diagnostic_frame_type_unchanged": True,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "device_contact": False,
        "live_authorized": False,
    }


__all__ = sorted(
    {
        "AuthObserverError",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DIAGNOSTIC",
        "DEVICE_BANNER",
        "HEADER",
        "MAX_INITIAL_SESSIONS",
        "MAX_PHYSICAL_REOPENS",
        "MAX_PREAMBLE_PAIRS",
        "MAX_RECONNECTS",
        "MAX_RESYNC_BYTES",
        "MAX_SESSIONS",
        "P339ObserverBindingError",
        "P339_RUN_ID",
        "P339_RUN_ID_HEX",
        "PHYSICAL_REOPEN_COUNT",
        "SCHEMA",
        "SESSION_TIMEOUT_SEC",
        "SOURCE",
        "SOURCE_IDENTITY",
        "audit_binding",
        "decode_frame",
        "identity",
        "parse_open_read_branch_frame",
        "parse_open_read_diagnostic_frame",
        "parse_retained_open_read_branch",
        "parse_retained_open_read_diagnostic",
    }
)
