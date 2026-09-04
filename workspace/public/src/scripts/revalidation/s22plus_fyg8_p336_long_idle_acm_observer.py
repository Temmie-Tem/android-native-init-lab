#!/usr/bin/env python3
"""Host-only P3.36 long-idle ACM session resynchronization.

The caller-owned descriptor is treated as a newly opened later-action
connection.  Exactly one authenticated ``OPEN`` is sent before any read.  A
bounded stream of exact ``banner``/stage-0 preambles is consumed until the
exact stage-1 ``OPEN_PARSED`` diagnostic is seen; only then are RNG,
challenge, AUTH, boot-ID, and the immutable three-command tuple exchanged.

This module never retries, opens a path, accepts a caller command, allocates a
PTY, transfers a file, reboots, or persists state.  Every failed exchange
retains the raw bytes and an audit digest for the caller's durable failure
receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
import os
from pathlib import Path
import stat
import struct
import time
from collections.abc import Callable
from typing import Any

import s22plus_fyg8_p335_retained_listener_acm_observer as predecessor
import s22plus_fyg8_p336_long_idle_runtime as runtime


SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p335_retained_listener_acm_observer.py"
)
SOURCE_IDENTITY = {
    "size": 47_411,
    "sha256": "26e2c98a7ba6a660f0c4c85b2432082303deb1b076304f20d1899ac125363281",
}
SCHEMA = "s22plus-fyg8-p336-long-idle-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p336-long-idle-acm-observer-v1"


class P336ObserverBindingError(ValueError):
    """The exact P3.35 observer or P3.36 protocol binding differs."""


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
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise P336ObserverBindingError("P3.35 observer source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != SOURCE_IDENTITY
    ):
        raise P336ObserverBindingError("P3.35 observer source identity differs")
    return payload


# The P3.35 observer is imported only as an exact protocol/codec source.  No
# P3.35 session function is invoked: the later-action exchange below owns the
# new preamble boundary and fresh P336 wire identity.
_PREDECESSOR_PAYLOAD = _stable_predecessor()
if identity(_PREDECESSOR_PAYLOAD) != SOURCE_IDENTITY:
    raise P336ObserverBindingError("P3.35 observer receipt differs")

_CODEC = predecessor._CODEC
_P333 = predecessor._P333
_EXCHANGE_LOCK = predecessor._EXCHANGE_LOCK
Frame = predecessor.Frame
CommandResult = predecessor.CommandResult
Diagnostic = predecessor.Diagnostic
ExchangeAudit = predecessor.ExchangeAudit
SessionResult = predecessor.SessionResult
AuthObserverError = predecessor.AuthObserverError
_RawWriter = predecessor._RawWriter
HEADER = predecessor.HEADER
EXIT = predecessor.EXIT
DONE = predecessor.DONE
DIAGNOSTIC = predecessor.DIAGNOSTIC
FRAME_MAGIC = runtime.FRAME_MAGIC
FRAME_VERSION = runtime.FRAME_VERSION
FRAME_OPEN = runtime.FRAME_OPEN
FRAME_EXEC = runtime.FRAME_EXEC
FRAME_CLOSE = runtime.FRAME_CLOSE
FRAME_AUTH = runtime.FRAME_AUTH
FRAME_READY = runtime.FRAME_READY
FRAME_DATA = runtime.FRAME_DATA
FRAME_EXIT = runtime.FRAME_EXIT
FRAME_DONE = runtime.FRAME_DONE
FRAME_CHALLENGE = runtime.FRAME_CHALLENGE
FRAME_BOOT_ID = runtime.P335_FRAME_BOOT_ID
AUTH_DOMAIN_OPEN = runtime.AUTH_DOMAIN_OPEN
AUTH_DOMAIN_READY = runtime.AUTH_DOMAIN_READY
AUTH_DOMAIN_EXEC = runtime.AUTH_DOMAIN_EXEC
AUTH_DOMAIN_CLOSE = runtime.AUTH_DOMAIN_CLOSE
AUTH_DOMAIN_BOOT_ID = runtime.AUTH_DOMAIN_BOOT_ID
TARGET = runtime.TARGET
DEVICE_BANNER = runtime.DEVICE_BANNER
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
P336_RUN_ID_HEX = runtime.P336_RUN_ID_HEX
P336_RUN_ID = runtime.P336_RUN_ID
P335_RUN_ID_HEX = P336_RUN_ID_HEX
P335_RUN_ID = P336_RUN_ID
P334_RUN_ID_HEX = P336_RUN_ID_HEX
P334_RUN_ID = P336_RUN_ID
P333_RUN_ID_HEX = P336_RUN_ID_HEX
P333_RUN_ID = P336_RUN_ID
P332_RUN_ID_HEX = P336_RUN_ID_HEX
P332_RUN_ID = P336_RUN_ID
P328_RUN_ID_HEX = P336_RUN_ID_HEX
P328_RUN_ID = P336_RUN_ID
AUTH_KEY_SIZE = runtime.AUTH_KEY_SIZE
AUTH_TAG_SIZE = runtime.AUTH_TAG_SIZE
NONCE_SIZE = runtime.NONCE_SIZE
P336_BOOT_ID_SIZE = runtime.P335_BOOT_ID_SIZE
P336_BOOT_ID_SEQUENCE = runtime.P335_BOOT_ID_SEQUENCE
SESSION_TIMEOUT_SEC = float(getattr(predecessor, "SESSION_TIMEOUT_SEC", 30.0))
MAX_OUTPUT_BYTES = runtime.MAX_OUTPUT_BYTES
MAX_INITIAL_SESSIONS = 2
MAX_SESSIONS = 3
MAX_RECONNECTS = 1
MAX_PHYSICAL_REOPENS = 1
PHYSICAL_REOPEN_COUNT = 1
MAX_PREAMBLE_PAIRS = 8
MAX_RESYNC_BYTES = 64 * 1024


def compute_open_tag(auth_key: bytes, run_id: bytes, nonce: bytes) -> bytes:
    return predecessor.compute_open_tag(auth_key, run_id, nonce)


def compute_ready_tag(auth_key: bytes, run_id: bytes, nonce: bytes) -> bytes:
    return predecessor.compute_ready_tag(auth_key, run_id, nonce)


def compute_exec_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, sequence: int, command: bytes
) -> bytes:
    return predecessor.compute_exec_tag(auth_key, run_id, nonce, sequence, command)


def compute_close_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, sequence: int
) -> bytes:
    return predecessor.compute_close_tag(auth_key, run_id, nonce, sequence)


def compute_boot_id_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, boot_id: bytes
) -> bytes:
    return predecessor.compute_boot_id_tag(auth_key, run_id, nonce, boot_id)


def decode_boot_id_frame(
    frame: Frame, auth_key: bytes, run_id: bytes, nonce: bytes
) -> bytes:
    return predecessor.decode_boot_id_frame(frame, auth_key, run_id, nonce)


def encode_frame(frame_type: int, sequence: int, payload: bytes) -> bytes:
    return predecessor.encode_frame(frame_type, sequence, payload)


def decode_frame(payload: bytes) -> Frame:
    return predecessor.decode_frame(payload)


def frame_crc(prefix: bytes, payload: bytes) -> int:
    return predecessor.frame_crc(prefix, payload)


constant_time_equal = predecessor.constant_time_equal
parse_diagnostic_frame = predecessor.parse_diagnostic_frame


def _validate_timeout(timeout_sec: float) -> float:
    if (
        type(timeout_sec) not in (int, float)
        or timeout_sec <= 0
        or not math.isfinite(float(timeout_sec))
        or timeout_sec > SESSION_TIMEOUT_SEC
    ):
        raise ValueError("P336 session timeout exceeds the fixed bound")
    return float(timeout_sec)


def _descriptor(connection: Any) -> int:
    if type(connection) is int:
        descriptor = connection
    else:
        fileno = getattr(connection, "fileno", None)
        if not callable(fileno):
            raise ValueError("P336 connection lacks fileno")
        descriptor = fileno()
    if type(descriptor) is not int or descriptor < 0:
        raise ValueError("P336 descriptor differs")
    return descriptor


def _exception_digest(exc: BaseException) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(f"{type(current).__name__}:{current}")
        current = current.__cause__ or current.__context__
    return hashlib.sha256("\n".join(parts).encode("utf-8", "replace")).hexdigest()


def _raw_bound(audit: ExchangeAudit) -> None:
    if len(audit.rx) > MAX_RESYNC_BYTES:
        raise AuthObserverError("P336 preamble backlog exceeds the fixed bound")


def _read_bounded(
    descriptor: int,
    size: int,
    deadline: float,
    audit: ExchangeAudit,
    writer: _RawWriter,
) -> bytes:
    """Read one exact preamble component without crossing the byte bound."""
    if type(size) is not int or size < 0 or len(audit.rx) + size > MAX_RESYNC_BYTES:
        raise AuthObserverError("P336 preamble backlog exceeds the fixed bound")
    payload = _CODEC._read_exact(  # noqa: SLF001
        descriptor, size, deadline, audit, writer
    )
    _raw_bound(audit)
    return payload


def _read_prefix_or_frame(
    descriptor: int,
    deadline: float,
    audit: ExchangeAudit,
    writer: _RawWriter,
) -> tuple[str, bytes | Frame]:
    """Read either an exact banner or one complete frame without peeking.

    A four-byte discriminator avoids consuming a S328 header as if it were a
    49-byte banner.  Every byte is read through the predecessor codec so the
    audit's raw RX buffer remains the authoritative receipt.
    """

    prefix = _read_bounded(descriptor, 4, deadline, audit, writer)
    if prefix == DEVICE_BANNER[:4]:
        rest = _read_bounded(
            descriptor, len(DEVICE_BANNER) - 4, deadline, audit, writer
        )
        banner = prefix + rest
        if banner != DEVICE_BANNER:
            raise AuthObserverError("P336 buffered banner differs")
        return "banner", banner
    if prefix != FRAME_MAGIC:
        raise AuthObserverError("P336 buffered preamble prefix is foreign")
    rest = _read_bounded(
        descriptor, HEADER.size - 4, deadline, audit, writer
    )
    header = prefix + rest
    fields = HEADER.unpack(header)
    payload_length = fields[3]
    if type(payload_length) is not int or payload_length > runtime.MAX_FRAME_PAYLOAD:
        raise AuthObserverError("P336 buffered frame exceeds the fixed bound")
    payload = _read_bounded(descriptor, payload_length, deadline, audit, writer)
    return "frame", decode_frame(header + payload)


def _raise_partial(
    exc: BaseException,
    audit: ExchangeAudit,
    stage: str,
    *,
    code: int | None = None,
) -> None:
    audit.current_stage = stage
    audit.failure_stage = stage
    audit.failure_code = code
    audit.exception_type = type(exc).__name__
    digest = _exception_digest(exc)
    audit.exception_sha256 = digest
    setattr(audit, "nested_exception_sha256", digest)
    setattr(audit, "resync_open_before_read", True)
    raise AuthObserverError(
        f"P336 exchange stopped at {stage}",
        audit=audit,
        stage=stage,
        code=code,
    ) from exc


def _consume_preambles_until_open_parsed(
    descriptor: int,
    deadline: float,
    audit: ExchangeAudit,
    writer: _RawWriter,
) -> int:
    count = 0
    while True:
        audit.current_stage = "resync-prefix"
        kind, value = _read_prefix_or_frame(descriptor, deadline, audit, writer)
        if kind == "banner":
            if count >= MAX_PREAMBLE_PAIRS:
                raise AuthObserverError("P336 buffered preamble count exceeds the fixed bound")
            audit.banner_seen = True
            audit.current_stage = "resync-stage0"
            header = _read_bounded(descriptor, HEADER.size, deadline, audit, writer)
            fields = HEADER.unpack(header)
            payload_length = fields[3]
            if type(payload_length) is not int or payload_length > runtime.MAX_FRAME_PAYLOAD:
                raise AuthObserverError("P336 buffered frame exceeds the fixed bound")
            payload = _read_bounded(
                descriptor, payload_length, deadline, audit, writer
            )
            frame = decode_frame(header + payload)
            diagnostic = _P333.parse_diagnostic_frame(  # noqa: SLF001
                frame, runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER
            )
            audit.diagnostics.append(diagnostic)
            count += 1
            setattr(audit, "resync_preamble_count", count)
            continue
        audit.current_stage = "resync-open-parsed"
        diagnostic = _P333.parse_diagnostic_frame(  # noqa: SLF001
            value, runtime.DIAGNOSTIC_STAGE_OPEN_PARSED
        )
        audit.diagnostics.append(diagnostic)
        setattr(audit, "resync_open_parsed_seen", True)
        setattr(audit, "resync_preamble_count", count)
        return count


def _exchange_after_open_parsed(
    descriptor: int,
    key: bytes,
    writer: _RawWriter,
    audit: ExchangeAudit,
    expected_boot_id_sha256: str,
    seen_nonces: set[bytes],
    seen_nonce_sha256: set[str],
    deadline: float,
) -> SessionResult:
    audit.current_stage = "rng-diagnostic-read"
    rng = _P333.parse_diagnostic_frame(  # noqa: SLF001
        _CODEC._read_frame(descriptor, deadline, audit, writer),  # noqa: SLF001
        runtime.DIAGNOSTIC_STAGE_RNG,
    )
    audit.diagnostics.append(rng)
    if rng.code < 0:
        raise AuthObserverError("P336 device RNG failed", code=rng.code)
    audit.rng_eagain_retries = rng.code

    audit.current_stage = "challenge-read"
    challenge = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
    nonce = _CODEC._expect(challenge, runtime.FRAME_CHALLENGE, 0)  # noqa: SLF001
    _CODEC._validate_nonce(nonce)  # noqa: SLF001
    nonce_sha256 = hashlib.sha256(nonce).hexdigest()
    if nonce in seen_nonces or nonce_sha256 in seen_nonce_sha256:
        raise AuthObserverError("P336 challenge nonce was replayed")
    seen_nonces.add(nonce)
    seen_nonce_sha256.add(nonce_sha256)
    audit.nonce = nonce
    audit.challenge_seen = True

    audit.current_stage = "auth-write"
    _CODEC._send(  # noqa: SLF001
        descriptor,
        runtime.FRAME_AUTH,
        1,
        compute_open_tag(key, runtime.P336_RUN_ID, nonce),
        deadline,
        audit,
    )
    audit.current_stage = "ready-read"
    ready = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
    ready_tag = _CODEC._expect(ready, runtime.FRAME_READY, 1)  # noqa: SLF001
    if not _CODEC.constant_time_equal(  # noqa: SLF001
        ready_tag, compute_ready_tag(key, runtime.P336_RUN_ID, nonce)
    ):
        raise AuthObserverError("P336 READY authentication differs")
    audit.ready_seen = True
    audit.authenticated = True

    audit.current_stage = "boot-id-read"
    boot_frame = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
    boot_id = decode_boot_id_frame(
        boot_frame, key, runtime.P336_RUN_ID, nonce
    )
    setattr(audit, "boot_id", boot_id)
    if hashlib.sha256(boot_id).hexdigest() != expected_boot_id_sha256:
        raise AuthObserverError("P336 per-boot identity changed")

    results: list[CommandResult] = []
    for sequence, command in enumerate(DEFAULT_COMMANDS, start=3):
        audit.current_stage = "exec-write"
        _CODEC._send(  # noqa: SLF001
            descriptor,
            runtime.FRAME_EXEC,
            sequence,
            compute_exec_tag(
                key, runtime.P336_RUN_ID, nonce, sequence, command
            ) + command,
            deadline,
            audit,
        )
        output = bytearray()
        while True:
            audit.current_stage = "exec-read"
            frame = _CODEC._read_frame(  # noqa: SLF001
                descriptor, deadline, audit, writer
            )
            if frame.sequence != sequence:
                raise AuthObserverError("P336 command response sequence differs")
            if frame.frame_type == runtime.FRAME_DATA:
                if not frame.payload:
                    raise AuthObserverError("P336 DATA payload is empty")
                output.extend(frame.payload)
                if len(output) > MAX_OUTPUT_BYTES:
                    raise AuthObserverError("P336 DATA exceeds output bound")
                continue
            if frame.frame_type != runtime.FRAME_EXIT:
                raise AuthObserverError("P336 command response type differs")
            flags, exit_code, signal_number, duration_ms = _CODEC._parse_exit(  # noqa: SLF001
                frame.payload, len(output)
            )
            results.append(
                CommandResult(
                    sequence,
                    command,
                    bytes(output),
                    flags,
                    exit_code,
                    signal_number,
                    duration_ms,
                )
            )
            break

    close_sequence = runtime.P335_BOOT_ID_SEQUENCE + len(DEFAULT_COMMANDS) + 1
    audit.current_stage = "close-write"
    _CODEC._send(  # noqa: SLF001
        descriptor,
        runtime.FRAME_CLOSE,
        close_sequence,
        compute_close_tag(
            key, runtime.P336_RUN_ID, nonce, close_sequence
        ),
        deadline,
        audit,
    )
    audit.current_stage = "done-read"
    done = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
    done_payload = _CODEC._expect(  # noqa: SLF001
        done, runtime.FRAME_DONE, close_sequence
    )
    if (
        len(done_payload) != DONE.size
        or DONE.unpack(done_payload)[0] != len(DEFAULT_COMMANDS)
    ):
        raise AuthObserverError("P336 DONE count differs")
    audit.done_seen = True
    audit.current_stage = "complete"
    return SessionResult(tuple(results), audit)


def _exchange_one_late(
    descriptor: int,
    auth_key: bytes,
    writer: _RawWriter,
    seen_nonces: set[bytes],
    seen_nonce_sha256: set[str],
    expected_boot_id_sha256: str,
    timeout_sec: float,
) -> SessionResult:
    key = _CODEC._validate_key(auth_key)  # noqa: SLF001
    if type(descriptor) is not int or descriptor < 0:
        raise AuthObserverError("P336 exchange descriptor differs")
    if (
        type(expected_boot_id_sha256) is not str
        or len(expected_boot_id_sha256) != 64
        or any(char not in "0123456789abcdef" for char in expected_boot_id_sha256)
        or expected_boot_id_sha256 == "0" * 64
    ):
        raise AuthObserverError("P336 expected boot identity differs")
    deadline = time.monotonic() + timeout_sec
    audit = ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
    setattr(audit, "resync_preamble_count", 0)
    setattr(audit, "resync_open_before_read", True)
    setattr(audit, "resync_open_parsed_seen", False)
    try:
        # This is intentionally the first wire action.  It establishes the
        # boundary before consuming any bytes retained during long idle.
        audit.current_stage = "open-write-before-resync"
        _CODEC._send(  # noqa: SLF001
            descriptor,
            runtime.FRAME_OPEN,
            0,
            runtime.P336_RUN_ID,
            deadline,
            audit,
        )
        _consume_preambles_until_open_parsed(
            descriptor, deadline, audit, writer
        )
        return _exchange_after_open_parsed(
            descriptor,
            key,
            writer,
            audit,
            expected_boot_id_sha256,
            seen_nonces,
            seen_nonce_sha256,
            deadline,
        )
    except BaseException as exc:
        _raise_partial(
            exc, audit, audit.current_stage, code=getattr(exc, "code", None)
        )


@dataclass(frozen=True)
class LongIdleSession:
    descriptor: int | None
    result: SessionResult | None
    audit: ExchangeAudit | None
    raw_tx: bytes
    raw_rx: bytes
    preamble_count: int
    error_type: str | None = None
    error_message: str | None = None

    @property
    def nonce(self) -> bytes:
        return b"" if self.audit is None else self.audit.nonce

    @property
    def boot_id(self) -> bytes:
        return b"" if self.audit is None else bytes(getattr(self.audit, "boot_id", b""))

    @property
    def authenticated(self) -> bool:
        return bool(self.audit is not None and self.audit.authenticated)

    @property
    def clean_close(self) -> bool:
        return bool(self.audit is not None and self.audit.done_seen)

    @property
    def ok(self) -> bool:
        return bool(
            self.result is not None
            and self.error_type is None
            and self.authenticated
            and self.clean_close
            and len(self.result.commands) == len(DEFAULT_COMMANDS)
            and all(item.ok for item in self.result.commands)
        )


@dataclass(frozen=True)
class LongIdleResult:
    session: LongIdleSession
    terminal: str

    @property
    def complete(self) -> bool:
        return self.terminal == "accepted" and self.session.ok


class LongIdleObserverError(AuthObserverError):
    """A failure carrying the complete partial raw/audit session."""

    def __init__(
        self,
        message: str,
        *,
        result: LongIdleResult,
        cause: BaseException | None = None,
    ) -> None:
        audit = result.session.audit
        super().__init__(
            message,
            audit=audit,
            stage=None if audit is None else audit.failure_stage,
            code=None if audit is None else audit.failure_code,
        )
        self.result = result
        self.session = result.session
        self.cause = cause
        self.audit = audit
        self.raw_tx = result.session.raw_tx
        self.raw_rx = result.session.raw_rx


def _make_session(
    descriptor: int | None,
    result: SessionResult | None,
    audit: ExchangeAudit | None,
    raw_writer: _RawWriter,
    *,
    error: BaseException | None = None,
) -> LongIdleSession:
    raw_tx = bytes(audit.tx) if audit is not None else b""
    raw_rx = bytes(audit.rx) if audit is not None else bytes(raw_writer.payload)
    preamble_count = 0 if audit is None else int(
        getattr(audit, "resync_preamble_count", 0)
    )
    return LongIdleSession(
        descriptor,
        result,
        audit,
        raw_tx,
        raw_rx,
        preamble_count,
        None if error is None else type(error).__name__,
        None if error is None else str(error),
    )


def exchange_late_action(
    connection: Any,
    auth_key: bytes,
    *,
    expected_boot_id: bytes | None = None,
    expected_boot_id_sha256: str | None = None,
    seen_nonces: set[bytes] | None = None,
    seen_nonce_sha256: set[str] | None = None,
    timeout_sec: float = SESSION_TIMEOUT_SEC,
    writer: Any | None = None,
) -> LongIdleResult:
    """Run one no-retry later action with the P336 resynchronization boundary.

    ``connection`` is already opened by the exact host endpoint owner.  This
    primitive never closes or reopens it, and it accepts no path or command.
    """

    if type(auth_key) is not bytes or len(auth_key) != runtime.AUTH_KEY_SIZE:
        raise ValueError("auth_key must be exactly 32 bytes")
    if expected_boot_id is not None and expected_boot_id_sha256 is not None:
        raise ValueError("supply one expected boot identity form")
    if expected_boot_id is not None:
        if (
            type(expected_boot_id) is not bytes
            or len(expected_boot_id) != runtime.P335_BOOT_ID_SIZE
            or not any(expected_boot_id)
        ):
            raise ValueError("expected_boot_id must be a nonzero exact boot identity")
        expected_boot_id_sha256 = hashlib.sha256(expected_boot_id).hexdigest()
    if (
        type(expected_boot_id_sha256) is not str
        or len(expected_boot_id_sha256) != 64
        or any(char not in "0123456789abcdef" for char in expected_boot_id_sha256)
        or expected_boot_id_sha256 == "0" * 64
    ):
        raise ValueError("expected_boot_id_sha256 must be a nonzero digest")
    timeout = _validate_timeout(timeout_sec)
    nonces = set() if seen_nonces is None else seen_nonces
    if type(nonces) is not set or any(
        type(nonce) is not bytes or len(nonce) != runtime.NONCE_SIZE
        for nonce in nonces
    ):
        raise ValueError("seen_nonces must be a set of exact nonce bytes")
    nonce_digests = set() if seen_nonce_sha256 is None else seen_nonce_sha256
    if type(nonce_digests) is not set or any(
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
        or value == "0" * 64
        for value in nonce_digests
    ):
        raise ValueError("seen_nonce_sha256 must be a set of nonzero digests")
    try:
        descriptor = _descriptor(connection)
    except BaseException as exc:
        session = _make_session(None, None, None, _RawWriter(writer), error=exc)
        result = LongIdleResult(session, "connection-failed")
        raise LongIdleObserverError(
            "P336 later-action connection is invalid", result=result, cause=exc
        ) from exc
    raw_writer = _RawWriter(writer)
    session_result: SessionResult | None = None
    try:
        with _EXCHANGE_LOCK:
            session_result = _exchange_one_late(
                descriptor,
                auth_key,
                raw_writer,
                nonces,
                nonce_digests,
                expected_boot_id_sha256,
                timeout,
            )
        session = _make_session(
            descriptor, session_result, session_result.audit, raw_writer
        )
        result = LongIdleResult(session, "accepted")
        validate_late_result(result)
        return result
    except BaseException as exc:
        audit = getattr(exc, "audit", None)
        if session_result is not None:
            audit = session_result.audit
        session = _make_session(
            descriptor, session_result, audit, raw_writer, error=exc
        )
        result = LongIdleResult(session, "session-failed")
        raise LongIdleObserverError(
            "P336 later-action exchange failed", result=result, cause=exc
        ) from exc


def _validate_command_results(session: LongIdleSession) -> None:
    if session.result is None or len(session.result.commands) != len(DEFAULT_COMMANDS):
        raise AuthObserverError("P336 fixed command tuple differs")
    if tuple(item.sequence for item in session.result.commands) != (3, 4, 5):
        raise AuthObserverError("P336 fixed command sequence differs")
    if tuple(item.command for item in session.result.commands) != DEFAULT_COMMANDS:
        raise AuthObserverError("P336 fixed command bytes differ")
    first, second, third = session.result.commands
    if (
        not first.ok
        or b"uid=0" not in first.output
        or b"gid=0" not in first.output
        or not second.ok
        or b"Linux" not in second.output
        or not second.output.endswith(b"\n")
        or not third.ok
        or third.output != f"P328-NONCE {P336_RUN_ID_HEX}\n".encode("ascii")
    ):
        raise AuthObserverError("P336 fixed command result differs")


def validate_late_result(value: LongIdleResult) -> LongIdleResult:
    if not isinstance(value, LongIdleResult) or value.terminal != "accepted":
        raise AuthObserverError("P336 later-action result is not accepted")
    session = value.session
    if (
        not session.ok
        or session.audit is None
        or not getattr(session.audit, "resync_open_before_read", False)
        or not getattr(session.audit, "resync_open_parsed_seen", False)
        or session.preamble_count < 0
        or session.preamble_count > MAX_PREAMBLE_PAIRS
        or len(session.nonce) != runtime.NONCE_SIZE
        or not any(session.nonce)
        or len(session.boot_id) != runtime.P335_BOOT_ID_SIZE
        or not any(session.boot_id)
        or hashlib.sha256(session.raw_tx).hexdigest() == "0" * 64
        or hashlib.sha256(session.raw_rx).hexdigest() == "0" * 64
    ):
        raise AuthObserverError("P336 later-action session proof differs")
    _validate_command_results(session)
    return value


def render_late_result(value: LongIdleResult) -> dict[str, Any]:
    validate_late_result(value)
    session = value.session
    assert session.audit is not None
    assert session.result is not None
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P336_RUN_ID_HEX,
        "terminal": value.terminal,
        "preamble_count": session.preamble_count,
        "open_sent_before_resync": True,
        "open_parsed_seen": True,
        "authenticated": session.authenticated,
        "clean_close": session.clean_close,
        "challenge_nonce_sha256": hashlib.sha256(session.nonce).hexdigest(),
        "boot_id_sha256": hashlib.sha256(session.boot_id).hexdigest(),
        "commands": [
            {
                "sequence": item.sequence,
                "command_sha256": hashlib.sha256(item.command).hexdigest(),
                "output": identity(item.output),
                "exit_code": item.exit_code,
                "term_signal": item.term_signal,
                "duration_ms": item.duration_ms,
            }
            for item in session.result.commands
        ],
        "raw_tx": identity(session.raw_tx),
        "raw_rx": identity(session.raw_rx),
        "diagnostics": [
            {"stage": item.stage, "code": item.code}
            for item in session.audit.diagnostics
        ],
        "audit": {
            "current_stage": session.audit.current_stage,
            "failure_stage": session.audit.failure_stage,
            "failure_code": session.audit.failure_code,
            "exception_type": session.audit.exception_type,
            "exception_sha256": session.audit.exception_sha256,
            "nested_exception_sha256": getattr(
                session.audit, "nested_exception_sha256", None
            ),
        },
        "caller_selected_command": False,
        "interactive_pty": False,
        "file_transfer": False,
        "persistent_state": False,
        "replay_authorized": False,
    }


def render_failure(exc: BaseException) -> dict[str, Any]:
    audit = getattr(exc, "audit", None)
    raw_tx = b"" if audit is None else bytes(audit.tx)
    raw_rx = b"" if audit is None else bytes(audit.rx)
    return {
        "schema": "s22plus_fyg8_p336_long_idle_failure_v1",
        "run_id_hex": P336_RUN_ID_HEX,
        "classification": "uncertain",
        "error_type": type(exc).__name__,
        "exception_sha256": _exception_digest(exc),
        "nested_exception_sha256": (
            None if audit is None else getattr(audit, "nested_exception_sha256", None)
        ),
        "failure_stage": None if audit is None else audit.failure_stage,
        "failure_code": None if audit is None else audit.failure_code,
        "current_stage": None if audit is None else audit.current_stage,
        "resync_preamble_count": (
            0 if audit is None else getattr(audit, "resync_preamble_count", 0)
        ),
        "open_sent_before_resync": (
            False if audit is None else getattr(audit, "resync_open_before_read", False)
        ),
        "raw_tx": identity(raw_tx),
        "raw_rx": identity(raw_rx),
        "replay_authorized": False,
    }


def audit_binding() -> dict[str, Any]:
    if (
        identity(_PREDECESSOR_PAYLOAD) != SOURCE_IDENTITY
        or DEVICE_BANNER == predecessor.DEVICE_BANNER
        or P336_RUN_ID_HEX == predecessor.P335_RUN_ID_HEX
        or len(DEFAULT_COMMANDS) != 3
    ):
        raise P336ObserverBindingError("P3.35 observer/P3.36 identity binding differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "run_id_hex": P336_RUN_ID_HEX,
        "open_before_resync": True,
        "max_preamble_pairs": MAX_PREAMBLE_PAIRS,
        "max_resync_bytes": MAX_RESYNC_BYTES,
        "terminator": "exact_stage_1_open_parsed",
        "fixed_command_count": len(DEFAULT_COMMANDS),
        "retry_added": False,
        "command_replay": False,
        "partial_raw_retention": True,
        "nested_exception_digest": True,
        "caller_selected_command": False,
        "interactive_pty": False,
        "file_transfer": False,
        "persistent_state": False,
        "reboot": False,
    }


__all__ = sorted(
    {
        "AUTH_DOMAIN_BOOT_ID",
        "AUTH_DOMAIN_CLOSE",
        "AUTH_DOMAIN_EXEC",
        "AUTH_DOMAIN_OPEN",
        "AUTH_DOMAIN_READY",
        "AUTH_KEY_SIZE",
        "AUTH_TAG_SIZE",
        "AuthObserverError",
        "CommandResult",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "DIAGNOSTIC",
        "Diagnostic",
        "DONE",
        "EXIT",
        "ExchangeAudit",
        "FRAME_AUTH",
        "FRAME_BOOT_ID",
        "FRAME_CHALLENGE",
        "FRAME_CLOSE",
        "FRAME_DATA",
        "FRAME_DONE",
        "FRAME_EXEC",
        "FRAME_EXIT",
        "FRAME_MAGIC",
        "FRAME_OPEN",
        "FRAME_READY",
        "FRAME_VERSION",
        "Frame",
        "HEADER",
        "LongIdleObserverError",
        "LongIdleResult",
        "LongIdleSession",
        "MAX_OUTPUT_BYTES",
        "MAX_PREAMBLE_PAIRS",
        "MAX_RESYNC_BYTES",
        "NONCE_SIZE",
        "P336_RUN_ID",
        "P336_RUN_ID_HEX",
        "P336ObserverBindingError",
        "SCHEMA",
        "SESSION_TIMEOUT_SEC",
        "SessionResult",
        "SOURCE",
        "SOURCE_IDENTITY",
        "TARGET",
        "audit_binding",
        "compute_boot_id_tag",
        "compute_close_tag",
        "compute_exec_tag",
        "compute_open_tag",
        "compute_ready_tag",
        "decode_boot_id_frame",
        "decode_frame",
        "encode_frame",
        "exchange_late_action",
        "frame_crc",
        "identity",
        "parse_diagnostic_frame",
        "render_failure",
        "render_late_result",
        "validate_late_result",
    }
)
