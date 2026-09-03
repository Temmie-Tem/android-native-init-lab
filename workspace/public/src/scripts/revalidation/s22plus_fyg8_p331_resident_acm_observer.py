#!/usr/bin/env python3
"""Host-only observer for the P3.31 bounded resident ACM loop.

The one-session exchange is delegated to the committed P3.30 observer, so
its S328 framing, HMAC-SHA256 domains, diagnostics, command bounds, and raw
capture semantics remain unchanged.  This module adds only a fixed two
session/one-reconnect coordinator.  Each session sends one fixed heartbeat,
requires a clean DONE close, and records its own raw TX/RX bytes, including a
partial receipt when authentication or a timeout fails.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import sys
import threading
import types
from collections.abc import Callable
from typing import Any

import s22plus_fyg8_p331_resident_exec_runtime as runtime


SOURCE = Path(__file__).with_name("s22plus_fyg8_p330_auth_acm_observer.py")
SOURCE_IDENTITY = {
    "size": 15_035,
    "sha256": "a00589310609cbab776dd99a23325644406d4d52cc0038ab34ab11ae726b3240",
}
SCHEMA = "s22plus_fyg8_p331_resident_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p331-resident-acm-observer-v1"
SESSION_TIMEOUT_SEC = runtime.RESIDENT_SESSION_TIMEOUT_SEC
MAX_SESSIONS = runtime.MAX_SESSIONS
MAX_RECONNECTS = runtime.MAX_RECONNECTS
DEFAULT_COMMANDS = (runtime.HEARTBEAT_COMMAND,)


class P331ObserverBindingError(ValueError):
    """The exact P3.30 observer source could not be rebound to P3.31."""


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
        raise P331ObserverBindingError("P3.30 observer source is unavailable") from exc
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
        raise P331ObserverBindingError("P3.30 observer source identity differs")
    module = types.ModuleType("s22plus_fyg8_p330_observer_bound_for_p331")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    runtime_key = "s22plus_fyg8_p330_auth_exec_runtime"
    module_key = module.__name__
    previous_runtime = sys.modules.get(runtime_key)
    previous_module = sys.modules.get(module_key)
    sys.modules[runtime_key] = runtime
    sys.modules[module_key] = module
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P331ObserverBindingError("P3.30 observer source failed to load") from exc
    finally:
        if previous_runtime is None:
            sys.modules.pop(runtime_key, None)
        else:
            sys.modules[runtime_key] = previous_runtime
        if previous_module is None:
            sys.modules.pop(module_key, None)
        else:
            sys.modules[module_key] = previous_module
    module.runtime = runtime
    return module


_P330 = _load()
_BASE = _P330._BASE

# The P330 module's frame classes and parser are the compatibility surface for
# one session.  They use runtime aliases supplied by the P331 runtime module.
Frame = _P330.Frame
ExchangeAudit = _P330.ExchangeAudit
SessionResult = _P330.SessionResult
AuthObserverError = _P330.AuthObserverError
HEADER = _P330.HEADER
EXIT = _P330.EXIT
DONE = _P330.DONE
DIAGNOSTIC = _P330.DIAGNOSTIC
AUTH_DOMAIN_OPEN = _P330.AUTH_DOMAIN_OPEN
AUTH_DOMAIN_READY = _P330.AUTH_DOMAIN_READY
AUTH_DOMAIN_EXEC = _P330.AUTH_DOMAIN_EXEC
AUTH_DOMAIN_CLOSE = _P330.AUTH_DOMAIN_CLOSE
FLAG_TIMEOUT = _P330.FLAG_TIMEOUT
FLAG_TRUNCATED = _P330.FLAG_TRUNCATED
FLAG_EXEC_FAILURE = _P330.FLAG_EXEC_FAILURE
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
compute_open_tag = _P330.compute_open_tag
compute_ready_tag = _P330.compute_ready_tag
compute_exec_tag = _P330.compute_exec_tag
compute_close_tag = _P330.compute_close_tag
constant_time_equal = _P330.constant_time_equal
encode_frame = _P330.encode_frame
decode_frame = _P330.decode_frame
frame_crc = _P330.frame_crc
parse_diagnostic_frame = _P330.parse_diagnostic_frame
validate_command = _P330.validate_command
validate_commands = _P330.validate_commands


class ResidentObserverError(AuthObserverError):
    """A resident loop failure carrying all sessions retained so far."""

    def __init__(
        self,
        message: str,
        *,
        result: "ResidentResult",
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
class ResidentSession:
    index: int
    reconnect_index: int
    result: SessionResult | None
    audit: ExchangeAudit | None
    raw_tx: bytes
    raw_rx: bytes
    error_type: str | None = None
    error_message: str | None = None

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
    def ok(self) -> bool:
        return (
            self.result is not None
            and self.error_type is None
            and self.authenticated
            and self.clean_close
        )


@dataclass(frozen=True)
class ResidentResult:
    sessions: tuple[ResidentSession, ...]
    session_cap: int
    reconnect_cap: int
    reconnect_attempts: int
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
    def complete(self) -> bool:
        return (
            self.terminal == "session-cap"
            and self.session_count == self.session_cap
            and self.successful_sessions == self.session_cap
        )


_EXCHANGE_LOCK = threading.RLock()


def _exchange_one(
    descriptor: int,
    auth_key: bytes,
    writer: _RawWriter,
    seen_nonces: set[bytes],
    timeout_sec: float,
) -> SessionResult:
    """Delegate one P330 exchange while rejecting a reused nonce pre-AUTH."""

    # P330's exchange looks up _BASE._read_frame at call time.  Serialize this
    # tiny compatibility hook so two host observers cannot cross-patch it.
    with _EXCHANGE_LOCK:
        original_read_frame = _BASE._read_frame  # noqa: SLF001

        def read_frame_guarded(
            fd: int, deadline: float, audit: ExchangeAudit, raw_writer: Any
        ) -> Frame:
            frame = original_read_frame(fd, deadline, audit, raw_writer)
            if frame.frame_type == runtime.FRAME_CHALLENGE:
                nonce = _BASE._expect(  # noqa: SLF001
                    frame, runtime.FRAME_CHALLENGE, 0
                )
                if nonce in seen_nonces:
                    raise AuthObserverError("P331 challenge nonce was replayed")
            return frame

        _BASE._read_frame = read_frame_guarded
        try:
            result = _P330.exchange_commands(
                descriptor,
                auth_key,
                DEFAULT_COMMANDS,
                timeout_sec=timeout_sec,
                writer=writer,
            )
        finally:
            _BASE._read_frame = original_read_frame
    nonce = result.audit.nonce
    if nonce in seen_nonces:
        raise AuthObserverError("P331 challenge nonce was replayed")
    seen_nonces.add(nonce)
    return result


def _descriptor(connection: Any) -> int:
    if type(connection) is int:
        descriptor = connection
    else:
        fileno = getattr(connection, "fileno", None)
        if not callable(fileno):
            raise ResidentObserverError(
                "P331 connection lacks fileno",
                result=ResidentResult((), 0, 0, 0, "connection-invalid"),
                session_index=0,
            )
        descriptor = fileno()
    if type(descriptor) is not int or descriptor < 0:
        raise ValueError("P331 descriptor differs")
    return descriptor


def _close(connection: Any, descriptor: int) -> None:
    closer = getattr(connection, "close", None)
    if callable(closer):
        closer()
    elif type(connection) is int:
        os.close(descriptor)
    else:
        os.close(descriptor)


def _validate_caps(max_sessions: int, max_reconnects: int) -> tuple[int, int]:
    if (
        type(max_sessions) is not int
        or not 1 <= max_sessions <= MAX_SESSIONS
        or type(max_reconnects) is not int
        or not 0 <= max_reconnects <= MAX_RECONNECTS
    ):
        raise ValueError("P331 resident caps exceed the fixed bounds")
    return max_sessions, max_reconnects


def _validate_timeout(timeout_sec: float) -> float:
    if (
        type(timeout_sec) not in (int, float)
        or timeout_sec <= 0
        or timeout_sec > SESSION_TIMEOUT_SEC
    ):
        raise ValueError("P331 session timeout exceeds the fixed bound")
    return float(timeout_sec)


def _source_factory(source: Any) -> tuple[Callable[[int], Any], bool]:
    if callable(source):
        return source, False
    if type(source) is int or callable(getattr(source, "fileno", None)):
        # A single descriptor/object is a resident transport: keep it open
        # while the fixed loop admits its second session.
        return lambda _index: source, True
    try:
        iterator = iter(source)
    except TypeError as exc:
        raise ValueError("P331 connection source differs") from exc
    return lambda _index: next(iterator), False


def exchange_resident(
    source: Any,
    auth_key: bytes,
    *,
    timeout_sec: float = SESSION_TIMEOUT_SEC,
    writer: Any | None = None,
    max_sessions: int = MAX_SESSIONS,
    max_reconnects: int = MAX_RECONNECTS,
) -> ResidentResult:
    """Run at most two fixed-heartbeat sessions over a bounded reconnect.

    ``source`` is either a callable receiving the zero-based session index, an
    iterable of already opened connection objects, or one descriptor/socket
    reused for the resident loop.  A reconnect obtains a fresh connection and
    never retries a failed session.  The callable/iterable is host-test
    plumbing only; it cannot select a command, path, service, or file.
    """

    if type(auth_key) is not bytes or len(auth_key) != runtime.AUTH_KEY_SIZE:
        raise ValueError("auth_key must be exactly 32 bytes")
    session_cap, reconnect_cap = _validate_caps(max_sessions, max_reconnects)
    timeout = _validate_timeout(timeout_sec)
    factory, reuse_single = _source_factory(source)
    records: list[ResidentSession] = []
    seen_nonces: set[bytes] = set()
    reconnect_attempts = 0
    connection: Any | None = None
    descriptor: int | None = None

    for index in range(session_cap):
        reconnect_index = index
        if index > 0:
            if reconnect_attempts >= reconnect_cap:
                return ResidentResult(
                    tuple(records),
                    session_cap,
                    reconnect_cap,
                    reconnect_attempts,
                    "reconnect-cap",
                )
            reconnect_attempts += 1
            try:
                connection = factory(index)
                descriptor = _descriptor(connection)
            except BaseException as exc:
                failed = ResidentSession(
                    index,
                    reconnect_index,
                    None,
                    None,
                    b"",
                    b"",
                    type(exc).__name__,
                    str(exc),
                )
                records.append(failed)
                result = ResidentResult(
                    tuple(records),
                    session_cap,
                    reconnect_cap,
                    reconnect_attempts,
                    "reconnect-failed",
                )
                raise ResidentObserverError(
                    "P331 reconnect failed",
                    result=result,
                    session_index=index,
                    cause=exc,
                ) from exc
        elif connection is None:
            try:
                connection = factory(index)
                descriptor = _descriptor(connection)
            except BaseException as exc:
                result = ResidentResult(
                    tuple(records),
                    session_cap,
                    reconnect_cap,
                    reconnect_attempts,
                    "connection-failed",
                )
                raise ResidentObserverError(
                    "P331 initial connection failed",
                    result=result,
                    session_index=index,
                    cause=exc,
                ) from exc

        assert connection is not None and descriptor is not None
        raw_writer = _RawWriter(writer)
        try:
            session_result = _exchange_one(
                descriptor,
                auth_key,
                raw_writer,
                seen_nonces,
                timeout,
            )
            audit = session_result.audit
            record = ResidentSession(
                index,
                reconnect_index,
                session_result,
                audit,
                bytes(audit.tx),
                bytes(audit.rx),
            )
            records.append(record)
        except BaseException as exc:
            audit = getattr(exc, "audit", None)
            records.append(
                ResidentSession(
                    index,
                    reconnect_index,
                    None,
                    audit,
                    bytes(audit.tx) if audit is not None else b"",
                    bytes(audit.rx) if audit is not None else bytes(raw_writer.payload),
                    type(exc).__name__,
                    str(exc),
                )
            )
            result = ResidentResult(
                tuple(records),
                session_cap,
                reconnect_cap,
                reconnect_attempts,
                "session-failed",
            )
            try:
                _close(connection, descriptor)
            except BaseException:
                pass
            raise ResidentObserverError(
                f"P331 resident session {index} failed",
                result=result,
                session_index=index,
                cause=exc,
            ) from exc
        if not reuse_single:
            try:
                _close(connection, descriptor)
            except BaseException as exc:
                result = ResidentResult(
                    tuple(records),
                    session_cap,
                    reconnect_cap,
                    reconnect_attempts,
                    "close-failed",
                )
                raise ResidentObserverError(
                    "P331 session close failed",
                    result=result,
                    session_index=index,
                    cause=exc,
                ) from exc
            connection = None
            descriptor = None

    if reuse_single and connection is not None and descriptor is not None:
        try:
            _close(connection, descriptor)
        except BaseException as exc:
            result = ResidentResult(
                tuple(records),
                session_cap,
                reconnect_cap,
                reconnect_attempts,
                "close-failed",
            )
            raise ResidentObserverError(
                "P331 resident close failed",
                result=result,
                session_index=len(records) - 1,
                cause=exc,
            ) from exc
    return ResidentResult(
        tuple(records),
        session_cap,
        reconnect_cap,
        reconnect_attempts,
        "session-cap" if len(records) == session_cap else "reconnect-cap",
    )


def exchange_session(
    descriptor: int,
    auth_key: bytes,
    *,
    timeout_sec: float = SESSION_TIMEOUT_SEC,
    writer: Any | None = None,
    seen_nonces: set[bytes] | None = None,
) -> SessionResult:
    """Observe one fixed-heartbeat session on an already opened descriptor."""

    capture = _RawWriter(writer)
    return _exchange_one(
        _descriptor(descriptor),
        auth_key,
        capture,
        set() if seen_nonces is None else seen_nonces,
        _validate_timeout(timeout_sec),
    )


exchange_commands = exchange_session


def _validate_heartbeat_session(value: Any) -> dict[str, Any]:
    """Validate the one P331 command while retaining P330 diagnostics/HMAC."""
    if not isinstance(value, SessionResult) or len(value.commands) != 1:
        raise AuthObserverError("P331 heartbeat session shape differs")
    command = value.commands[0]
    audit = value.audit
    if not isinstance(audit, ExchangeAudit):
        raise AuthObserverError("P331 heartbeat audit type differs")
    expected_diagnostics = [
        _P330.Diagnostic(runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0),
        _P330.Diagnostic(
            runtime.DIAGNOSTIC_STAGE_RNG, audit.rng_eagain_retries
        ),
    ]
    if (
        command.sequence != 2
        or command.command != runtime.HEARTBEAT_COMMAND
        or command.output != runtime.HEARTBEAT_OUTPUT
        or not command.ok
        or audit.diagnostics != expected_diagnostics
        or type(audit.rng_eagain_retries) is not int
        or not 0
        <= audit.rng_eagain_retries
        <= runtime.RNG_EAGAIN_RETRY_LIMIT
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
        or len(audit.nonce) != runtime.NONCE_SIZE
    ):
        raise AuthObserverError("P331 heartbeat session proof differs")
    return {
        "hmac_authenticated": True,
        "pid1_authenticated_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
    }


def validate_resident_proof(value: ResidentResult) -> dict[str, Any]:
    if not isinstance(value, ResidentResult) or not value.complete:
        raise ResidentObserverError(
            "P331 resident proof result differs",
            result=value if isinstance(value, ResidentResult) else ResidentResult((), 0, 0, 0, "invalid"),
            session_index=0,
        )
    nonces: set[bytes] = set()
    rendered: list[dict[str, Any]] = []
    for session in value.sessions:
        try:
            one_session_proof = (
                _validate_heartbeat_session(session.result)
                if session.result is not None
                else None
            )
        except AuthObserverError as exc:
            raise ResidentObserverError(
                "P331 resident session proof differs",
                result=value,
                session_index=session.index,
                cause=exc,
            ) from exc
        if (
            not session.ok
            or session.result is None
            or not isinstance(one_session_proof, dict)
            or one_session_proof.get("hmac_authenticated") is not True
            or one_session_proof.get("busybox_ash_command_proof") is not True
            or one_session_proof.get("pid1_authenticated_framed_exec_proof")
            is not True
            or session.result.commands != session.result.commands[:1]
            or len(session.result.commands) != 1
            or session.result.commands[0].command != runtime.HEARTBEAT_COMMAND
            or session.result.commands[0].output != runtime.HEARTBEAT_OUTPUT
            or session.nonce in nonces
            or len(session.nonce) != runtime.NONCE_SIZE
        ):
            raise ResidentObserverError(
                "P331 resident heartbeat proof differs",
                result=value,
                session_index=session.index,
            )
        nonces.add(session.nonce)
        rendered.append(
            {
                "session_index": session.index,
                "reconnect_index": session.reconnect_index,
                "challenge_nonce_sha256": hashlib.sha256(session.nonce).hexdigest(),
                "auth_key_sha256": session.audit.auth_key_sha256,
                "tx": identity(session.raw_tx),
                "rx": identity(session.raw_rx),
                "authenticated": True,
                "clean_close": True,
                "command": identity(runtime.HEARTBEAT_COMMAND),
                "output": identity(runtime.HEARTBEAT_OUTPUT),
            }
        )
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": runtime.TARGET,
        "run_id_hex": runtime.P331_RUN_ID_HEX,
        "session_cap": value.session_cap,
        "reconnect_cap": value.reconnect_cap,
        "session_count": value.session_count,
        "successful_sessions": value.successful_sessions,
        "reconnect_count": value.reconnect_count,
        "sessions": rendered,
        "banner_attempts": sum(
            bool(item.audit is not None and item.audit.banner_seen)
            for item in value.sessions
        ),
        "banner_scope": "resident_loop_per_session",
        "fixed_heartbeat_status": True,
        "caller_selected_command": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
        "resident_loop_proof": True,
        "partial_raw_retention": all(
            len(item.raw_tx) >= HEADER.size and len(item.raw_rx) >= len(runtime.DEVICE_BANNER)
            for item in value.sessions
        ),
    }


# Descriptive aliases make the single public coordinator easy to find without
# introducing a second code path.
exchange_resident_sessions = exchange_resident
exchange_reconnectable = exchange_resident
validate_default_proof = validate_resident_proof


__all__ = [
    "AUTH_DOMAIN_CLOSE",
    "AUTH_DOMAIN_EXEC",
    "AUTH_DOMAIN_OPEN",
    "AUTH_DOMAIN_READY",
    "AuthObserverError",
    "CONTRACT_ID",
    "DEFAULT_COMMANDS",
    "DIAGNOSTIC",
    "DONE",
    "EXIT",
    "ExchangeAudit",
    "FLAG_EXEC_FAILURE",
    "FLAG_TIMEOUT",
    "FLAG_TRUNCATED",
    "Frame",
    "HEADER",
    "FRAME_AUTH",
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
    "MAX_RECONNECTS",
    "MAX_SESSIONS",
    "P331ObserverBindingError",
    "ResidentObserverError",
    "ResidentResult",
    "ResidentSession",
    "SCHEMA",
    "SESSION_TIMEOUT_SEC",
    "SessionResult",
    "SOURCE",
    "SOURCE_IDENTITY",
    "compute_close_tag",
    "compute_exec_tag",
    "compute_open_tag",
    "compute_ready_tag",
    "constant_time_equal",
    "decode_frame",
    "encode_frame",
    "exchange_reconnectable",
    "exchange_resident",
    "exchange_resident_sessions",
    "exchange_commands",
    "exchange_session",
    "frame_crc",
    "identity",
    "parse_diagnostic_frame",
    "validate_command",
    "validate_commands",
    "validate_default_proof",
    "validate_resident_proof",
]
