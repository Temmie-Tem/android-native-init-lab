#!/usr/bin/env python3
"""Host-only observer for the P3.35 retained listener proof.

The observer keeps P3.34's stage-0 and authenticated S328 exchange shape,
then consumes the P3.35 boot-identity frame and the shifted fixed-command
sequences.  It runs exactly two sessions on the caller's initial descriptor,
closes it once, obtains exactly one caller-owned reopened connection, and runs
one final session.  It never retries a failed session and accepts no command,
path, PTY, persistence, or device-control option.
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
import sys
import threading
import time
import types
from collections.abc import Callable
from typing import Any

import s22plus_fyg8_p335_retained_listener_runtime as runtime


SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p334_first_read_rc_acm_observer.py"
)
SOURCE_IDENTITY = {
    "size": 5_523,
    "sha256": "4644eede3280c29c5619cb5b8e70a0af50b2993ab05de1df9e3f92632e860399",
}
SCHEMA = "s22plus-fyg8-p335-retained-listener-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p335-retained-listener-acm-observer-v1"


class P335ObserverBindingError(ValueError):
    """The exact P3.34 observer could not be rebound to P3.35."""


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


def _load() -> types.ModuleType:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise P335ObserverBindingError("P3.34 observer source is unavailable") from exc
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
        raise P335ObserverBindingError("P3.34 observer source identity differs")
    module = types.ModuleType("s22plus_fyg8_p334_observer_bound_for_p335")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    runtime_name = "s22plus_fyg8_p334_first_read_rc_runtime"
    module_name = module.__name__
    previous_runtime = sys.modules.get(runtime_name)
    previous_module = sys.modules.get(module_name)
    sys.modules[runtime_name] = runtime
    sys.modules[module_name] = module
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P335ObserverBindingError("P3.34 observer source failed to load") from exc
    finally:
        if previous_runtime is None:
            sys.modules.pop(runtime_name, None)
        else:
            sys.modules[runtime_name] = previous_runtime
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
    if module.runtime is not runtime:
        raise P335ObserverBindingError("P3.34 observer runtime rebind differs")
    return module


_P334 = _load()
_P333 = _P334._P333
_P332 = _P333._P332
_BASE = _P332._P330
_CODEC = _BASE._BASE

Frame = _BASE.Frame
CommandResult = _BASE.CommandResult
Diagnostic = _P333.Diagnostic
ExchangeAudit = _BASE.ExchangeAudit
SessionResult = _BASE.SessionResult
AuthObserverError = _BASE.AuthObserverError
HEADER = _BASE.HEADER
EXIT = _BASE.EXIT
DONE = _BASE.DONE
DIAGNOSTIC = _P333.DIAGNOSTIC
FLAG_TIMEOUT = _BASE.FLAG_TIMEOUT
FLAG_TRUNCATED = _BASE.FLAG_TRUNCATED
FLAG_EXEC_FAILURE = _BASE.FLAG_EXEC_FAILURE
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
P335_RUN_ID_HEX = runtime.P335_RUN_ID_HEX
P335_RUN_ID = runtime.P335_RUN_ID
P334_RUN_ID_HEX = P335_RUN_ID_HEX
P334_RUN_ID = P335_RUN_ID
P333_RUN_ID_HEX = P335_RUN_ID_HEX
P333_RUN_ID = P335_RUN_ID
P332_RUN_ID_HEX = P335_RUN_ID_HEX
P332_RUN_ID = P335_RUN_ID
P328_RUN_ID_HEX = P335_RUN_ID_HEX
P328_RUN_ID = P335_RUN_ID
SESSION_TIMEOUT_SEC = float(getattr(_P334, "SESSION_TIMEOUT_SEC", 30.0))
COMMAND_TIMEOUT_SEC = runtime.COMMAND_TIMEOUT_SEC
MAX_INITIAL_SESSIONS = 2
MAX_SESSIONS = 3
MAX_RECONNECTS = 1
MAX_PHYSICAL_REOPENS = 1
PHYSICAL_REOPEN_COUNT = 1


def compute_open_tag(auth_key: bytes, run_id: bytes, nonce: bytes) -> bytes:
    return _BASE.compute_open_tag(auth_key, run_id, nonce)


def compute_ready_tag(auth_key: bytes, run_id: bytes, nonce: bytes) -> bytes:
    return _BASE.compute_ready_tag(auth_key, run_id, nonce)


def compute_exec_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, sequence: int, command: bytes
) -> bytes:
    return _BASE.compute_exec_tag(auth_key, run_id, nonce, sequence, command)


def compute_close_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, sequence: int
) -> bytes:
    return _BASE.compute_close_tag(auth_key, run_id, nonce, sequence)


def _validate_boot_id(boot_id: bytes) -> bytes:
    if type(boot_id) is not bytes or len(boot_id) != runtime.P335_BOOT_ID_SIZE:
        raise AuthObserverError("P335 boot identity size differs")
    if not any(boot_id):
        raise AuthObserverError("P335 boot identity must not be all zero")
    return boot_id


def compute_boot_id_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, boot_id: bytes
) -> bytes:
    key = _CODEC._validate_key(auth_key)  # noqa: SLF001
    rid = _CODEC._validate_run_id(run_id)  # noqa: SLF001
    random_nonce = _CODEC._validate_nonce(nonce)  # noqa: SLF001
    boot = _validate_boot_id(boot_id)
    message = (
        AUTH_DOMAIN_BOOT_ID
        + rid
        + random_nonce
        + struct.pack("<I", runtime.P335_BOOT_ID_SEQUENCE)
        + boot
    )
    return hmac.new(key, message, hashlib.sha256).digest()


def decode_boot_id_frame(
    frame: Frame, auth_key: bytes, run_id: bytes, nonce: bytes
) -> bytes:
    if not isinstance(frame, Frame):
        raise AuthObserverError("P335 boot identity frame differs")
    if frame.frame_type != FRAME_BOOT_ID or frame.sequence != runtime.P335_BOOT_ID_SEQUENCE:
        raise AuthObserverError("P335 boot identity frame type/sequence differs")
    expected_size = runtime.P335_BOOT_ID_SIZE + runtime.AUTH_TAG_SIZE
    if len(frame.payload) != expected_size:
        raise AuthObserverError("P335 boot identity payload differs")
    boot_id = _validate_boot_id(frame.payload[: runtime.P335_BOOT_ID_SIZE])
    tag = frame.payload[runtime.P335_BOOT_ID_SIZE :]
    if not hmac.compare_digest(
        tag, compute_boot_id_tag(auth_key, run_id, nonce, boot_id)
    ):
        raise AuthObserverError("P335 boot identity authentication differs")
    return boot_id


class RetainedListenerObserverError(AuthObserverError):
    """A retained-listener failure carrying all records retained so far."""

    def __init__(
        self,
        message: str,
        *,
        result: "RetainedResult",
        session_index: int,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.result = result
        self.session_index = session_index
        self.cause = cause
        failed = result.sessions[-1] if result.sessions else None
        self.audit = failed.audit if failed is not None else None
        self.raw_tx = failed.raw_tx if failed is not None else b""
        self.raw_rx = failed.raw_rx if failed is not None else b""


class _RawWriter:
    def __init__(self, delegate: Any | None) -> None:
        self.payload = bytearray()
        self.delegate = delegate

    def write_stdout(self, value: bytes) -> None:
        self.payload.extend(value)
        if self.delegate is not None:
            self.delegate.write_stdout(value)


@dataclass(frozen=True)
class RetainedSession:
    index: int
    physical_reopen_index: int
    descriptor: int | None
    result: SessionResult | None
    audit: ExchangeAudit | None
    raw_tx: bytes
    raw_rx: bytes
    error_type: str | None = None
    error_message: str | None = None

    @property
    def session_index(self) -> int:
        return self.index

    @property
    def authenticated(self) -> bool:
        return bool(self.audit is not None and self.audit.authenticated)

    @property
    def clean_close(self) -> bool:
        return bool(self.audit is not None and self.audit.done_seen)

    @property
    def nonce(self) -> bytes:
        return b"" if self.audit is None else self.audit.nonce

    @property
    def boot_id(self) -> bytes:
        return b"" if self.audit is None else bytes(getattr(self.audit, "boot_id", b""))

    @property
    def failure_stage(self) -> str | None:
        return None if self.audit is None else self.audit.failure_stage

    @property
    def ok(self) -> bool:
        return (
            self.result is not None
            and self.error_type is None
            and all(item.ok for item in self.result.commands)
            and self.authenticated
            and self.clean_close
        )


@dataclass(frozen=True)
class RetainedResult:
    sessions: tuple[RetainedSession, ...]
    session_cap: int
    reconnect_cap: int
    reconnect_attempts: int
    physical_reopen_count: int
    terminal: str

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    @property
    def successful_sessions(self) -> int:
        return sum(item.ok for item in self.sessions)

    @property
    def reconnect_count(self) -> int:
        return self.reconnect_attempts

    @property
    def reconnects(self) -> int:
        return self.reconnect_attempts

    @property
    def same_initial_fd(self) -> bool:
        return bool(
            len(self.sessions) >= 2
            and self.sessions[0].descriptor is not None
            and self.sessions[0].descriptor == self.sessions[1].descriptor
            and self.sessions[0].physical_reopen_index == 0
            and self.sessions[1].physical_reopen_index == 0
        )

    @property
    def same_boot_id(self) -> bool:
        boot_ids = [item.boot_id for item in self.sessions]
        return bool(
            len(boot_ids) == MAX_SESSIONS
            and all(len(item) == runtime.P335_BOOT_ID_SIZE and any(item) for item in boot_ids)
            and len(set(boot_ids)) == 1
        )

    @property
    def complete(self) -> bool:
        return (
            self.terminal == "session-cap"
            and self.session_cap == MAX_SESSIONS
            and self.reconnect_cap == MAX_RECONNECTS
            and self.session_count == MAX_SESSIONS
            and self.successful_sessions == MAX_SESSIONS
            and self.reconnect_attempts == 1
            and self.physical_reopen_count == PHYSICAL_REOPEN_COUNT
            and self.same_initial_fd
            and self.same_boot_id
        )


_EXCHANGE_LOCK = threading.RLock()


def _validate_timeout(timeout_sec: float) -> float:
    if (
        type(timeout_sec) not in (int, float)
        or timeout_sec <= 0
        or not math.isfinite(float(timeout_sec))
        or timeout_sec > SESSION_TIMEOUT_SEC
    ):
        raise ValueError("P335 session timeout exceeds the fixed bound")
    return float(timeout_sec)


def _descriptor(connection: Any) -> int:
    if type(connection) is int:
        descriptor = connection
    else:
        fileno = getattr(connection, "fileno", None)
        if not callable(fileno):
            raise ValueError("P335 connection lacks fileno")
        descriptor = fileno()
    if type(descriptor) is not int or descriptor < 0:
        raise ValueError("P335 descriptor differs")
    return descriptor


def _close(connection: Any, descriptor: int) -> None:
    closer = getattr(connection, "close", None)
    if callable(closer):
        closer()
    elif type(connection) is int:
        os.close(descriptor)
    else:
        os.close(descriptor)


def _raise_partial(
    exc: Exception, audit: ExchangeAudit, stage: str, *, code: int | None = None
) -> None:
    if isinstance(exc, AuthObserverError) and getattr(exc, "audit", None) is audit:
        raise exc
    audit.failure_stage = stage
    audit.failure_code = code
    audit.exception_type = type(exc).__name__
    preimage = f"{type(exc).__name__}:{exc}".encode("utf-8", "replace")
    audit.exception_sha256 = hashlib.sha256(preimage).hexdigest()
    raise AuthObserverError(
        f"P335 exchange stopped at {stage}",
        audit=audit,
        stage=stage,
        code=code,
    ) from exc


def _exchange_one(
    descriptor: int,
    auth_key: bytes,
    writer: _RawWriter,
    seen_nonces: set[bytes],
    expected_boot_id: bytes | None,
    timeout_sec: float,
) -> SessionResult:
    key = _CODEC._validate_key(auth_key)  # noqa: SLF001
    if type(descriptor) is not int or descriptor < 0:
        raise AuthObserverError("P335 exchange descriptor differs")
    if type(expected_boot_id) not in (bytes, type(None)):
        raise AuthObserverError("P335 expected boot identity differs")
    deadline = time.monotonic() + timeout_sec
    audit = ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())

    def stage(name: str) -> None:
        audit.current_stage = name

    try:
        stage("banner-read")
        banner = _CODEC._read_exact(  # noqa: SLF001
            descriptor, len(runtime.DEVICE_BANNER), deadline, audit, writer
        )
        if banner != runtime.DEVICE_BANNER:
            raise AuthObserverError("P335 banner differs")
        audit.banner_seen = True

        stage("open-write")
        _CODEC._send(  # noqa: SLF001
            descriptor, runtime.FRAME_OPEN, 0, runtime.P335_RUN_ID,
            deadline, audit,
        )

        stage("entry-diagnostic-read")
        entry = _P333.parse_diagnostic_frame(  # noqa: SLF001
            _CODEC._read_frame(descriptor, deadline, audit, writer),
            runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
        )
        audit.diagnostics.append(entry)

        stage("open-diagnostic-read")
        opened = _P333.parse_diagnostic_frame(  # noqa: SLF001
            _CODEC._read_frame(descriptor, deadline, audit, writer),
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
        )
        audit.diagnostics.append(opened)

        stage("rng-diagnostic-read")
        rng = _P333.parse_diagnostic_frame(  # noqa: SLF001
            _CODEC._read_frame(descriptor, deadline, audit, writer),
            runtime.DIAGNOSTIC_STAGE_RNG,
        )
        audit.diagnostics.append(rng)
        if rng.code < 0:
            raise AuthObserverError("P335 device RNG failed", code=rng.code)
        audit.rng_eagain_retries = rng.code

        stage("challenge-read")
        challenge = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
        nonce = _CODEC._expect(challenge, runtime.FRAME_CHALLENGE, 0)  # noqa: SLF001
        _CODEC._validate_nonce(nonce)  # noqa: SLF001
        if nonce in seen_nonces:
            raise AuthObserverError("P335 challenge nonce was replayed")
        seen_nonces.add(nonce)
        audit.nonce = nonce
        audit.challenge_seen = True

        stage("auth-write")
        _CODEC._send(
            descriptor,
            runtime.FRAME_AUTH,
            1,
            compute_open_tag(key, runtime.P335_RUN_ID, nonce),
            deadline,
            audit,
        )

        stage("ready-read")
        ready = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
        ready_tag = _CODEC._expect(ready, runtime.FRAME_READY, 1)  # noqa: SLF001
        if not _CODEC.constant_time_equal(  # noqa: SLF001
            ready_tag, compute_ready_tag(key, runtime.P335_RUN_ID, nonce)
        ):
            raise AuthObserverError("P335 READY authentication differs")
        audit.ready_seen = True
        audit.authenticated = True

        stage("boot-id-read")
        boot_frame = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
        boot_id = decode_boot_id_frame(
            boot_frame, key, runtime.P335_RUN_ID, nonce
        )
        setattr(audit, "boot_id", boot_id)
        if expected_boot_id is not None and boot_id != expected_boot_id:
            raise AuthObserverError("P335 per-boot identity changed")

        results: list[CommandResult] = []
        for sequence, command in enumerate(DEFAULT_COMMANDS, start=3):
            stage("exec-write")
            _CODEC._send(  # noqa: SLF001
                descriptor,
                runtime.FRAME_EXEC,
                sequence,
                compute_exec_tag(
                    key, runtime.P335_RUN_ID, nonce, sequence, command
                ) + command,
                deadline,
                audit,
            )
            output = bytearray()
            while True:
                stage("exec-read")
                frame = _CODEC._read_frame(  # noqa: SLF001
                    descriptor, deadline, audit, writer
                )
                if frame.sequence != sequence:
                    raise AuthObserverError("P335 command response sequence differs")
                if frame.frame_type == runtime.FRAME_DATA:
                    if not frame.payload:
                        raise AuthObserverError("P335 DATA payload is empty")
                    output.extend(frame.payload)
                    if len(output) > runtime.MAX_OUTPUT_BYTES:
                        raise AuthObserverError("P335 DATA exceeds output bound")
                    continue
                if frame.frame_type != runtime.FRAME_EXIT:
                    raise AuthObserverError("P335 command response type differs")
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

        close_sequence = runtime.P335_BOOT_ID_SEQUENCE + runtime.P335_COMMANDS_PER_SESSION + 1
        stage("close-write")
        _CODEC._send(  # noqa: SLF001
            descriptor,
            runtime.FRAME_CLOSE,
            close_sequence,
            compute_close_tag(
                key, runtime.P335_RUN_ID, nonce, close_sequence
            ),
            deadline,
            audit,
        )
        stage("done-read")
        done = _CODEC._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
        done_payload = _CODEC._expect(  # noqa: SLF001
            done, runtime.FRAME_DONE, close_sequence
        )
        if (
            len(done_payload) != DONE.size
            or DONE.unpack(done_payload)[0] != len(DEFAULT_COMMANDS)
        ):
            raise AuthObserverError("P335 DONE count differs")
        audit.done_seen = True
        stage("complete")
        return SessionResult(tuple(results), audit)
    except Exception as exc:
        _raise_partial(
            exc, audit, audit.current_stage, code=getattr(exc, "code", None)
        )


def _record_failure(
    index: int,
    physical_reopen_index: int,
    descriptor: int | None,
    exc: BaseException,
    raw_writer: _RawWriter,
    session_result: SessionResult | None = None,
) -> RetainedSession:
    audit = getattr(exc, "audit", None)
    if session_result is not None:
        audit = session_result.audit
    return RetainedSession(
        index=index,
        physical_reopen_index=physical_reopen_index,
        descriptor=descriptor,
        result=session_result,
        audit=audit,
        raw_tx=bytes(audit.tx) if audit is not None else b"",
        raw_rx=(
            bytes(audit.rx)
            if audit is not None
            else bytes(raw_writer.payload)
        ),
        error_type=type(exc).__name__,
        error_message=str(exc),
    )


def _record_success(
    index: int,
    physical_reopen_index: int,
    descriptor: int,
    result: SessionResult,
) -> RetainedSession:
    audit = result.audit
    return RetainedSession(
        index=index,
        physical_reopen_index=physical_reopen_index,
        descriptor=descriptor,
        result=result,
        audit=audit,
        raw_tx=bytes(audit.tx),
        raw_rx=bytes(audit.rx),
    )


def _validate_one_session(
    session: RetainedSession, expected_boot_id: bytes | None = None
) -> dict[str, Any]:
    if (
        session.result is None
        or session.audit is None
        or session.error_type is not None
        or not session.ok
        or len(session.result.commands) != len(DEFAULT_COMMANDS)
        or tuple(item.command for item in session.result.commands) != DEFAULT_COMMANDS
        or tuple(item.sequence for item in session.result.commands) != (3, 4, 5)
        or session.raw_tx != bytes(session.audit.tx)
        or session.raw_rx != bytes(session.audit.rx)
        or len(session.nonce) != runtime.NONCE_SIZE
        or not any(session.nonce)
        or len(session.boot_id) != runtime.P335_BOOT_ID_SIZE
        or not any(session.boot_id)
    ):
        raise AuthObserverError("P335 session shape differs")
    if expected_boot_id is not None and session.boot_id != expected_boot_id:
        raise AuthObserverError("P335 session boot identity differs")
    audit = session.audit
    diagnostics = getattr(audit, "diagnostics", ())
    if (
        len(diagnostics) != 3
        or [(item.stage, item.code) for item in diagnostics[:2]]
        != [
            (runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER, 0),
            (runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0),
        ]
        or diagnostics[2].stage != runtime.DIAGNOSTIC_STAGE_RNG
        or not 0 <= diagnostics[2].code <= runtime.RNG_EAGAIN_RETRY_LIMIT
        or audit.rng_eagain_retries != diagnostics[2].code
        or audit.failure_stage is not None
        or audit.exception_type is not None
        or audit.current_stage != "complete"
        or not all(
            (
                audit.banner_seen,
                audit.challenge_seen,
                audit.ready_seen,
                audit.authenticated,
                audit.done_seen,
            )
        )
    ):
        raise AuthObserverError("P335 diagnostic/session proof differs")
    first, second, third = session.result.commands
    if (
        not first.ok
        or b"uid=0" not in first.output
        or b"gid=0" not in first.output
        or not second.ok
        or b"Linux" not in second.output
        or not second.output.endswith(b"\n")
        or not third.ok
        or third.output
        != f"P328-NONCE {runtime.P335_RUN_ID_HEX}\n".encode("ascii")
    ):
        raise AuthObserverError("P335 fixed command result differs")
    return {
        "pid1_authenticated_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "interactive_pty_proof": False,
        "caller_selected_command": False,
    }


def exchange_retained(
    initial_connection: Any,
    auth_key: bytes,
    *,
    reopen: Callable[[], Any],
    timeout_sec: float = SESSION_TIMEOUT_SEC,
    writer: Any | None = None,
) -> RetainedResult:
    """Prove two initial same-FD sessions and one physical reopen session.

    ``initial_connection`` is used for exactly two sessions and closed once.
    ``reopen`` is called exactly once after that close and supplies the third
    connection.  A failed exchange or reopen is retained and raised; no
    failed session is retried and no command is replayed.
    """

    if type(auth_key) is not bytes or len(auth_key) != runtime.AUTH_KEY_SIZE:
        raise ValueError("auth_key must be exactly 32 bytes")
    if not callable(reopen):
        raise ValueError("P335 reopen must be callable")
    timeout = _validate_timeout(timeout_sec)
    try:
        descriptor = _descriptor(initial_connection)
    except BaseException as exc:
        result = RetainedResult((), MAX_SESSIONS, MAX_RECONNECTS, 0, 0, "connection-failed")
        raise RetainedListenerObserverError(
            "P335 initial connection is invalid",
            result=result,
            session_index=0,
            cause=exc,
        ) from exc

    records: list[RetainedSession] = []
    seen_nonces: set[bytes] = set()
    expected_boot_id: bytes | None = None
    for index in range(MAX_INITIAL_SESSIONS):
        raw_writer = _RawWriter(writer)
        session_result: SessionResult | None = None
        try:
            with _EXCHANGE_LOCK:
                session_result = _exchange_one(
                    descriptor,
                    auth_key,
                    raw_writer,
                    seen_nonces,
                    expected_boot_id,
                    timeout,
                )
            record = _record_success(index, 0, descriptor, session_result)
            if expected_boot_id is None:
                expected_boot_id = record.boot_id
            _validate_one_session(record, expected_boot_id)
            records.append(record)
        except BaseException as exc:
            records.append(
                _record_failure(
                    index, 0, descriptor, exc, raw_writer, session_result
                )
            )
            result = RetainedResult(
                tuple(records), MAX_SESSIONS, MAX_RECONNECTS, 0, 0, "session-failed"
            )
            try:
                _close(initial_connection, descriptor)
            except BaseException:
                pass
            raise RetainedListenerObserverError(
                f"P335 initial session {index} failed",
                result=result,
                session_index=index,
                cause=exc,
            ) from exc

    try:
        _close(initial_connection, descriptor)
    except BaseException as exc:
        result = RetainedResult(
            tuple(records), MAX_SESSIONS, MAX_RECONNECTS, 0, 0, "close-failed"
        )
        raise RetainedListenerObserverError(
            "P335 initial connection close failed",
            result=result,
            session_index=MAX_INITIAL_SESSIONS - 1,
            cause=exc,
        ) from exc

    reconnect_attempts = 1
    try:
        reopened = reopen()
        reopened_descriptor = _descriptor(reopened)
    except BaseException as exc:
        records.append(
            RetainedSession(
                MAX_INITIAL_SESSIONS,
                1,
                None,
                None,
                None,
                b"",
                b"",
                type(exc).__name__,
                str(exc),
            )
        )
        result = RetainedResult(
            tuple(records), MAX_SESSIONS, MAX_RECONNECTS, reconnect_attempts, 1,
            "reopen-failed",
        )
        raise RetainedListenerObserverError(
            "P335 physical reopen failed",
            result=result,
            session_index=MAX_INITIAL_SESSIONS,
            cause=exc,
        ) from exc

    raw_writer = _RawWriter(writer)
    session_result = None
    try:
        with _EXCHANGE_LOCK:
            session_result = _exchange_one(
                reopened_descriptor,
                auth_key,
                raw_writer,
                seen_nonces,
                expected_boot_id,
                timeout,
            )
        record = _record_success(
            MAX_INITIAL_SESSIONS, 1, reopened_descriptor, session_result
        )
        _validate_one_session(record, expected_boot_id)
        records.append(record)
    except BaseException as exc:
        records.append(
            _record_failure(
                MAX_INITIAL_SESSIONS,
                1,
                reopened_descriptor,
                exc,
                raw_writer,
                session_result,
            )
        )
        result = RetainedResult(
            tuple(records), MAX_SESSIONS, MAX_RECONNECTS, reconnect_attempts, 1,
            "session-failed",
        )
        try:
            _close(reopened, reopened_descriptor)
        except BaseException:
            pass
        raise RetainedListenerObserverError(
            "P335 reopened session failed",
            result=result,
            session_index=MAX_INITIAL_SESSIONS,
            cause=exc,
        ) from exc

    try:
        _close(reopened, reopened_descriptor)
    except BaseException as exc:
        result = RetainedResult(
            tuple(records), MAX_SESSIONS, MAX_RECONNECTS, reconnect_attempts, 1,
            "close-failed",
        )
        raise RetainedListenerObserverError(
            "P335 reopened connection close failed",
            result=result,
            session_index=MAX_INITIAL_SESSIONS,
            cause=exc,
        ) from exc
    return RetainedResult(
        tuple(records), MAX_SESSIONS, MAX_RECONNECTS, reconnect_attempts, 1,
        "session-cap",
    )


def _render_session(session: RetainedSession) -> dict[str, Any]:
    proof = _validate_one_session(session, session.boot_id)
    audit = session.audit
    assert audit is not None and session.result is not None
    return {
        "session_index": session.index,
        "physical_reopen_index": session.physical_reopen_index,
        "challenge_nonce_sha256": hashlib.sha256(session.nonce).hexdigest(),
        "boot_id_sha256": hashlib.sha256(session.boot_id).hexdigest(),
        "auth_key_sha256": audit.auth_key_sha256,
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
        "tx": identity(session.raw_tx),
        "rx": identity(session.raw_rx),
        "raw_tx": identity(session.raw_tx),
        "raw_rx": identity(session.raw_rx),
        "diagnostics": [
            {"stage": item.stage, "code": item.code}
            for item in audit.diagnostics
        ],
        **proof,
    }


def validate_retained_proof(value: RetainedResult) -> dict[str, Any]:
    if not isinstance(value, RetainedResult) or not value.complete:
        result = (
            value
            if isinstance(value, RetainedResult)
            else RetainedResult((), MAX_SESSIONS, MAX_RECONNECTS, 0, 0, "invalid")
        )
        raise RetainedListenerObserverError(
            "P335 retained listener proof result differs",
            result=result,
            session_index=0,
        )
    if (
        value.sessions[0].physical_reopen_index != 0
        or value.sessions[1].physical_reopen_index != 0
        or value.sessions[2].physical_reopen_index != 1
        or value.sessions[0].descriptor != value.sessions[1].descriptor
    ):
        raise RetainedListenerObserverError(
            "P335 initial same-FD/reopen proof differs",
            result=value,
            session_index=2,
        )
    rendered: list[dict[str, Any]] = []
    for session in value.sessions:
        try:
            rendered.append(_render_session(session))
        except Exception as exc:
            raise RetainedListenerObserverError(
                "P335 retained listener session proof differs",
                result=value,
                session_index=session.index,
                cause=exc,
            ) from exc
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P335_RUN_ID_HEX,
        "session_cap": MAX_SESSIONS,
        "reconnect_cap": MAX_RECONNECTS,
        "session_count": value.session_count,
        "successful_sessions": value.successful_sessions,
        "reconnect_count": value.reconnect_count,
        "physical_reopen_count": value.physical_reopen_count,
        "sessions": rendered,
        "fixed_command_count": len(DEFAULT_COMMANDS),
        "fixed_commands": [identity(command) for command in DEFAULT_COMMANDS],
        "hmac_authenticated": True,
        "pid1_authenticated_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "diagnostic_order_proof": True,
        "per_boot_identity_proof": True,
        "same_initial_fd": True,
        "same_tty_fd": True,
        "same_boot_id": True,
        "descriptor_reopened": True,
        "caller_selected_command": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
        "retained_listener_proof": True,
        "listener_replays_commands": False,
        "partial_raw_retention": all(
            len(item.raw_tx) >= HEADER.size
            and len(item.raw_rx) >= len(DEVICE_BANNER)
            for item in value.sessions
        ),
    }


_PROOF_KEYS = frozenset(
    {
        "schema",
        "contract_id",
        "target",
        "run_id_hex",
        "session_cap",
        "reconnect_cap",
        "session_count",
        "successful_sessions",
        "reconnect_count",
        "physical_reopen_count",
        "sessions",
        "fixed_command_count",
        "fixed_commands",
        "hmac_authenticated",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "diagnostic_order_proof",
        "per_boot_identity_proof",
        "same_initial_fd",
        "same_tty_fd",
        "same_boot_id",
        "descriptor_reopened",
        "caller_selected_command",
        "interactive_pty",
        "arbitrary_file_transfer",
        "persistent_state",
        "retained_listener_proof",
        "listener_replays_commands",
        "partial_raw_retention",
    }
)
_SESSION_KEYS = frozenset(
    {
        "session_index",
        "physical_reopen_index",
        "challenge_nonce_sha256",
        "boot_id_sha256",
        "auth_key_sha256",
        "commands",
        "tx",
        "rx",
        "raw_tx",
        "raw_rx",
        "diagnostics",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "interactive_pty_proof",
        "caller_selected_command",
    }
)
_COMMAND_KEYS = frozenset(
    {"sequence", "command_sha256", "output", "exit_code", "term_signal", "duration_ms"}
)
_IDENTITY_KEYS = frozenset({"size", "sha256"})
_HEX64 = frozenset("0123456789abcdef")


def _proof_failure(message: str) -> AuthObserverError:
    return AuthObserverError(f"P335 serialized proof differs: {message}")


def _proof_identity(value: Any, label: str, *, minimum_size: int = 1) -> None:
    if (
        type(value) is not dict
        or set(value) != _IDENTITY_KEYS
        or type(value["size"]) is not int
        or value["size"] < minimum_size
        or type(value["sha256"]) is not str
        or len(value["sha256"]) != 64
        or any(char not in _HEX64 for char in value["sha256"])
        or value["sha256"] == "0" * 64
    ):
        raise _proof_failure(f"{label} identity differs")


def validate_proof_value(
    value: Any, *, expected_auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PROOF_KEYS:
        raise _proof_failure("proof key set differs")
    for key, expected in (
        ("schema", SCHEMA),
        ("contract_id", CONTRACT_ID),
        ("target", TARGET),
        ("run_id_hex", P335_RUN_ID_HEX),
    ):
        if value[key] != expected:
            raise _proof_failure(f"{key} differs")
    integer_fields = (
        "session_cap",
        "reconnect_cap",
        "session_count",
        "successful_sessions",
        "reconnect_count",
        "physical_reopen_count",
        "fixed_command_count",
    )
    if any(type(value[key]) is not int for key in integer_fields):
        raise _proof_failure("integer field type differs")
    if any(
        value[key] != expected
        for key, expected in (
            ("session_cap", MAX_SESSIONS),
            ("reconnect_cap", MAX_RECONNECTS),
            ("session_count", MAX_SESSIONS),
            ("successful_sessions", MAX_SESSIONS),
            ("reconnect_count", 1),
            ("physical_reopen_count", PHYSICAL_REOPEN_COUNT),
            ("fixed_command_count", len(DEFAULT_COMMANDS)),
        )
    ):
        raise _proof_failure("session/reopen bounds differ")
    expected_true = (
        "hmac_authenticated",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "diagnostic_order_proof",
        "per_boot_identity_proof",
        "same_initial_fd",
        "same_tty_fd",
        "same_boot_id",
        "descriptor_reopened",
        "retained_listener_proof",
        "partial_raw_retention",
    )
    expected_false = (
        "caller_selected_command",
        "interactive_pty",
        "arbitrary_file_transfer",
        "persistent_state",
        "listener_replays_commands",
    )
    if any(value[key] is not True for key in expected_true) or any(
        value[key] is not False for key in expected_false
    ):
        raise _proof_failure("proof flags differ")
    commands = value["fixed_commands"]
    if type(commands) is not list or len(commands) != len(DEFAULT_COMMANDS):
        raise _proof_failure("fixed command list differs")
    for rendered, command in zip(commands, DEFAULT_COMMANDS):
        if type(rendered) is not dict or set(rendered) != _IDENTITY_KEYS:
            raise _proof_failure("fixed command identity keys differ")
        if rendered != identity(command):
            raise _proof_failure("fixed command identity differs")

    sessions = value["sessions"]
    if type(sessions) is not list or len(sessions) != MAX_SESSIONS:
        raise _proof_failure("session list differs")
    nonces: set[str] = set()
    boot_ids: set[str] = set()
    auth_digests: set[str] = set()
    for index, session in enumerate(sessions):
        if type(session) is not dict or set(session) != _SESSION_KEYS:
            raise _proof_failure(f"session {index} keys differ")
        if (
            type(session["session_index"]) is not int
            or session["session_index"] != index
            or type(session["physical_reopen_index"]) is not int
            or session["physical_reopen_index"] != (0 if index < 2 else 1)
        ):
            raise _proof_failure(f"session {index} reopen binding differs")
        for label in ("challenge_nonce_sha256", "boot_id_sha256", "auth_key_sha256"):
            digest = session[label]
            if (
                type(digest) is not str
                or len(digest) != 64
                or any(char not in _HEX64 for char in digest)
                or digest == "0" * 64
            ):
                raise _proof_failure(f"session {index} {label} differs")
        if session["challenge_nonce_sha256"] in nonces:
            raise _proof_failure("challenge nonce was repeated")
        nonces.add(session["challenge_nonce_sha256"])
        boot_ids.add(session["boot_id_sha256"])
        auth_digests.add(session["auth_key_sha256"])
        if expected_auth_key_sha256 is not None and session["auth_key_sha256"] != expected_auth_key_sha256:
            raise _proof_failure(f"session {index} auth key binding differs")
        session_commands = session["commands"]
        if type(session_commands) is not list or len(session_commands) != len(DEFAULT_COMMANDS):
            raise _proof_failure(f"session {index} command list differs")
        for command_proof, command, sequence in zip(
            session_commands, DEFAULT_COMMANDS, (3, 4, 5)
        ):
            if type(command_proof) is not dict or set(command_proof) != _COMMAND_KEYS:
                raise _proof_failure(f"session {index} command keys differ")
            if (
                type(command_proof["sequence"]) is not int
                or command_proof["sequence"] != sequence
                or command_proof["command_sha256"] != hashlib.sha256(command).hexdigest()
                or type(command_proof["exit_code"]) is not int
                or command_proof["exit_code"] != 0
                or type(command_proof["term_signal"]) is not int
                or command_proof["term_signal"] != 0
                or type(command_proof["duration_ms"]) is not int
                or command_proof["duration_ms"] < 0
            ):
                raise _proof_failure(f"session {index} command proof differs")
            _proof_identity(command_proof["output"], f"session {index} output")
        for label, minimum in (
            ("tx", HEADER.size),
            ("raw_tx", HEADER.size),
            ("rx", len(DEVICE_BANNER)),
            ("raw_rx", len(DEVICE_BANNER)),
        ):
            _proof_identity(session[label], f"session {index} {label}", minimum_size=minimum)
        if session["tx"] != session["raw_tx"] or session["rx"] != session["raw_rx"]:
            raise _proof_failure(f"session {index} raw identity differs")
        diagnostics = session["diagnostics"]
        if type(diagnostics) is not list or len(diagnostics) != 3:
            raise _proof_failure(f"session {index} diagnostics differ")
        expected_stages = (
            runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
            runtime.DIAGNOSTIC_STAGE_RNG,
        )
        for item, stage in zip(diagnostics, expected_stages):
            if (
                type(item) is not dict
                or set(item) != {"stage", "code"}
                or type(item["stage"]) is not int
                or item["stage"] != stage
                or type(item["code"]) is not int
                or item["code"] < 0
                or item["code"] > runtime.RNG_EAGAIN_RETRY_LIMIT
                or (stage != runtime.DIAGNOSTIC_STAGE_RNG and item["code"] != 0)
            ):
                raise _proof_failure(f"session {index} diagnostic proof differs")
        if any(
            session[key] is not expected
            for key, expected in (
                ("pid1_authenticated_framed_exec_proof", True),
                ("busybox_ash_command_proof", True),
                ("interactive_pty_proof", False),
                ("caller_selected_command", False),
            )
        ):
            raise _proof_failure(f"session {index} proof flags differ")
    if len(boot_ids) != 1 or len(auth_digests) != 1:
        raise _proof_failure("same boot/key binding differs")
    return value


def audit_binding() -> dict[str, Any]:
    if (
        _P334.runtime is not runtime
        or DEFAULT_COMMANDS != tuple(runtime.DEFAULT_COMMANDS)
        or DEVICE_BANNER != runtime.DEVICE_BANNER
        or P335_RUN_ID_HEX != runtime.P335_RUN_ID_HEX
    ):
        raise P335ObserverBindingError("P3.35 observer binding differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P335_RUN_ID_HEX,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "initial_same_fd_sessions": MAX_INITIAL_SESSIONS,
        "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
        "per_boot_identity_frame": FRAME_BOOT_ID,
        "retry_added": False,
        "command_replay": False,
    }


exchange_resident = exchange_retained
exchange_resident_sessions = exchange_retained
exchange_commands = exchange_retained
validate_default_proof = validate_retained_proof
validate_resident_proof = validate_retained_proof
ResidentSession = RetainedSession
ResidentResult = RetainedResult
ResidentObserverError = RetainedListenerObserverError
RetainedObserverError = RetainedListenerObserverError


__all__ = sorted(
    {
        "AUTH_DOMAIN_BOOT_ID",
        "AUTH_DOMAIN_CLOSE",
        "AUTH_DOMAIN_EXEC",
        "AUTH_DOMAIN_OPEN",
        "AUTH_DOMAIN_READY",
        "AuthObserverError",
        "COMMAND_TIMEOUT_SEC",
        "CommandResult",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "DIAGNOSTIC",
        "Diagnostic",
        "DONE",
        "EXIT",
        "ExchangeAudit",
        "FLAG_EXEC_FAILURE",
        "FLAG_TIMEOUT",
        "FLAG_TRUNCATED",
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
        "MAX_INITIAL_SESSIONS",
        "MAX_PHYSICAL_REOPENS",
        "MAX_RECONNECTS",
        "MAX_SESSIONS",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P335_RUN_ID",
        "P335_RUN_ID_HEX",
        "P335ObserverBindingError",
        "PHYSICAL_REOPEN_COUNT",
        "ResidentObserverError",
        "ResidentResult",
        "ResidentSession",
        "RetainedListenerObserverError",
        "RetainedObserverError",
        "RetainedResult",
        "RetainedSession",
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
        "exchange_commands",
        "exchange_resident",
        "exchange_resident_sessions",
        "exchange_retained",
        "frame_crc",
        "identity",
        "parse_diagnostic_frame",
        "validate_default_proof",
        "validate_proof_value",
        "validate_resident_proof",
        "validate_retained_proof",
    }
)

# Keep the codec helpers discoverable without introducing another protocol
# implementation.  They are all exact aliases from the bound P3.34 engine.
decode_frame = _BASE.decode_frame
encode_frame = _BASE.encode_frame
frame_crc = _BASE.frame_crc
constant_time_equal = _BASE.constant_time_equal
validate_command = _BASE.validate_command
validate_commands = _BASE.validate_commands
parse_diagnostic_frame = _P333.parse_diagnostic_frame
