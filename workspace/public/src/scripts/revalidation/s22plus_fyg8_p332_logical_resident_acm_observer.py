#!/usr/bin/env python3
"""Host-only observer for the P3.32 logical resident ACM exchange.

Each bounded session delegates to the exact P3.30 observer protocol: S328
framing, pre-auth diagnostics, HMAC-SHA256, the three fixed commands, and the
DONE close.  The coordinator runs two sessions sequentially on one descriptor
owned by its caller.  It never closes or reopens that descriptor, and it stops
at the first failed session while retaining that session's partial audit.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import stat
import sys
import threading
import types
from typing import Any

import s22plus_fyg8_p332_logical_resident_exec_runtime as runtime


SOURCE = Path(__file__).with_name("s22plus_fyg8_p330_auth_acm_observer.py")
SOURCE_IDENTITY = {
    "size": 15_035,
    "sha256": "a00589310609cbab776dd99a23325644406d4d52cc0038ab34ab11ae726b3240",
}
SCHEMA = "s22plus_fyg8_p332_logical_resident_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p332-logical-resident-acm-observer-v1"
P332_RUN_ID_HEX = runtime.P332_RUN_ID_HEX
P332_RUN_ID = runtime.P332_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
TARGET = runtime.TARGET
MAX_SESSIONS = runtime.SESSION_COUNT
MAX_RECONNECTS = runtime.RECONNECT_COUNT
PHYSICAL_REOPEN_COUNT = runtime.PHYSICAL_REOPEN_COUNT
MAX_PHYSICAL_REOPENS = runtime.MAX_PHYSICAL_REOPENS
SESSION_TIMEOUT_SEC = float(
    getattr(runtime, "RESIDENT_SESSION_TIMEOUT_SEC", 30.0)
)
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)


class P332ObserverBindingError(ValueError):
    """The exact P3.30 observer source could not be rebound to P3.32."""


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
        raise P332ObserverBindingError("P3.30 observer source is unavailable") from exc
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
        raise P332ObserverBindingError("P3.30 observer source identity differs")
    module = types.ModuleType("s22plus_fyg8_p330_observer_bound_for_p332")
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
        raise P332ObserverBindingError("P3.30 observer source failed to load") from exc
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

Frame = _P330.Frame
CommandResult = _P330.CommandResult
Diagnostic = _P330.Diagnostic
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
decode_diagnostic = _P330.decode_diagnostic
validate_command = _P330.validate_command
validate_commands = _P330.validate_commands
COMMAND_TIMEOUT_SEC = _P330.COMMAND_TIMEOUT_SEC
OPEN_DIAGNOSTIC_TIMEOUT_SEC = _P330.OPEN_DIAGNOSTIC_TIMEOUT_SEC
RNG_DIAGNOSTIC_TIMEOUT_SEC = _P330.RNG_DIAGNOSTIC_TIMEOUT_SEC


class LogicalResidentObserverError(AuthObserverError):
    """A logical resident failure carrying every session retained so far."""

    def __init__(
        self,
        message: str,
        *,
        result: "LogicalResidentResult",
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
class LogicalResidentSession:
    index: int
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
class LogicalResidentResult:
    sessions: tuple[LogicalResidentSession, ...]
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


# The P330 module's exchange patches its shared base reader only for the
# duration of one call.  Serialize that small compatibility seam so unrelated
# host observers cannot cross-patch it.
_EXCHANGE_LOCK = threading.RLock()


def _exchange_one(
    descriptor: int,
    auth_key: bytes,
    writer: _RawWriter,
    seen_nonces: set[bytes],
    timeout_sec: float,
) -> SessionResult:
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
                    raise AuthObserverError("P332 challenge nonce was replayed")
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
        raise AuthObserverError("P332 challenge nonce was replayed")
    seen_nonces.add(nonce)
    return result


def _descriptor(connection: Any) -> int:
    if type(connection) is int:
        descriptor = connection
    else:
        fileno = getattr(connection, "fileno", None)
        if not callable(fileno):
            raise ValueError("P332 connection lacks fileno")
        descriptor = fileno()
    if type(descriptor) is not int or descriptor < 0:
        raise ValueError("P332 descriptor differs")
    return descriptor


def _validate_timeout(timeout_sec: float) -> float:
    if (
        type(timeout_sec) not in (int, float)
        or timeout_sec <= 0
        or not math.isfinite(float(timeout_sec))
        or timeout_sec > SESSION_TIMEOUT_SEC
    ):
        raise ValueError("P332 session timeout exceeds the fixed bound")
    return float(timeout_sec)


def _record_failure(
    index: int,
    exc: BaseException,
    raw_writer: _RawWriter,
) -> LogicalResidentSession:
    audit = getattr(exc, "audit", None)
    return LogicalResidentSession(
        index=index,
        result=None,
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


def exchange_resident(
    connection: Any,
    auth_key: bytes,
    *,
    timeout_sec: float = SESSION_TIMEOUT_SEC,
    writer: Any | None = None,
) -> LogicalResidentResult:
    """Run exactly two fixed-command sessions on one caller-owned descriptor.

    ``connection`` must already be open and is never closed or reopened here.
    A failed first or second session raises ``LogicalResidentObserverError``
    with all completed/partial session records attached.  No caller command,
    path, file, PTY, or persistence option is accepted.
    """

    if type(auth_key) is not bytes or len(auth_key) != runtime.AUTH_KEY_SIZE:
        raise ValueError("auth_key must be exactly 32 bytes")
    if len(DEFAULT_COMMANDS) != 3:
        raise P332ObserverBindingError("P330 fixed command set differs")
    timeout = _validate_timeout(timeout_sec)
    try:
        descriptor = _descriptor(connection)
    except BaseException as exc:
        result = LogicalResidentResult((), MAX_SESSIONS, MAX_RECONNECTS, 0, "connection-failed")
        raise LogicalResidentObserverError(
            "P332 initial connection is invalid",
            result=result,
            session_index=0,
            cause=exc,
        ) from exc

    records: list[LogicalResidentSession] = []
    seen_nonces: set[bytes] = set()
    for index in range(MAX_SESSIONS):
        raw_writer = _RawWriter(writer)
        session_result: SessionResult | None = None
        try:
            session_result = _exchange_one(
                descriptor,
                auth_key,
                raw_writer,
                seen_nonces,
                timeout,
            )
            audit = session_result.audit
            records.append(
                record := LogicalResidentSession(
                    index=index,
                    result=session_result,
                    audit=audit,
                    raw_tx=bytes(audit.tx),
                    raw_rx=bytes(audit.rx),
                )
            )
            _validate_one_session(record)
        except BaseException as exc:
            if session_result is not None:
                audit = session_result.audit
                records[-1] = LogicalResidentSession(
                    index=index,
                    result=session_result,
                    audit=audit,
                    raw_tx=bytes(audit.tx),
                    raw_rx=bytes(audit.rx),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            else:
                records.append(_record_failure(index, exc, raw_writer))
            result = LogicalResidentResult(
                tuple(records), MAX_SESSIONS, MAX_RECONNECTS, 0, "session-failed"
            )
            raise LogicalResidentObserverError(
                f"P332 logical resident session {index} failed",
                result=result,
                session_index=index,
                cause=exc,
            ) from exc

    return LogicalResidentResult(
        tuple(records), MAX_SESSIONS, MAX_RECONNECTS, 0, "session-cap"
    )


def _validate_one_session(session: LogicalResidentSession) -> dict[str, Any]:
    if (
        not session.ok
        or session.result is None
        or session.audit is None
        or len(session.result.commands) != len(DEFAULT_COMMANDS)
        or tuple(item.command for item in session.result.commands)
        != DEFAULT_COMMANDS
        or session.raw_tx != bytes(session.audit.tx)
        or session.raw_rx != bytes(session.audit.rx)
        or len(session.nonce) != runtime.NONCE_SIZE
    ):
        raise AuthObserverError("P332 session shape differs")
    # This exact predecessor proof rejects nonzero/invalid EXIT fields as well
    # as malformed diagnostics, HMAC, command output, or DONE closure.
    proof = dict(_P330.validate_default_proof(session.result))
    # P330 exposes a caller-selected command API; P332 binds that API to its
    # exact runtime tuple before invoking it.
    proof["caller_selected_command"] = False
    return proof


def validate_resident_proof(value: LogicalResidentResult) -> dict[str, Any]:
    if (
        not isinstance(value, LogicalResidentResult)
        or not value.complete
        or value.session_cap != MAX_SESSIONS
        or value.reconnect_cap != MAX_RECONNECTS
        or value.reconnect_attempts != 0
        or value.session_count != MAX_SESSIONS
    ):
        result = value if isinstance(value, LogicalResidentResult) else LogicalResidentResult((), MAX_SESSIONS, MAX_RECONNECTS, 0, "invalid")
        raise LogicalResidentObserverError(
            "P332 logical resident proof result differs",
            result=result,
            session_index=0,
        )

    nonces: set[bytes] = set()
    rendered: list[dict[str, Any]] = []
    for session in value.sessions:
        try:
            one = _validate_one_session(session)
        except Exception as exc:
            raise LogicalResidentObserverError(
                "P332 logical resident session proof differs",
                result=value,
                session_index=session.index,
                cause=exc,
            ) from exc
        if session.nonce in nonces:
            raise LogicalResidentObserverError(
                "P332 challenge nonce was repeated",
                result=value,
                session_index=session.index,
            )
        nonces.add(session.nonce)
        one["session_index"] = session.index
        one["raw_tx"] = identity(session.raw_tx)
        one["raw_rx"] = identity(session.raw_rx)
        one["diagnostics"] = [
            {"stage": item.stage, "code": item.code}
            for item in session.audit.diagnostics
        ]
        rendered.append(one)

    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P332_RUN_ID_HEX,
        "session_cap": MAX_SESSIONS,
        "reconnect_cap": MAX_RECONNECTS,
        "session_count": value.session_count,
        "successful_sessions": value.successful_sessions,
        "reconnect_count": 0,
        "sessions": rendered,
        "fixed_command_count": len(DEFAULT_COMMANDS),
        "fixed_commands": [identity(command) for command in DEFAULT_COMMANDS],
        "hmac_authenticated": True,
        "pid1_authenticated_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "diagnostic_order_proof": True,
        "logical_resident_proof": True,
        "same_descriptor": True,
        "same_fd": True,
        "same_tty_fd": True,
        "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
        "descriptor_reopened": False,
        "caller_selected_command": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
        "partial_raw_retention": all(
            len(item.raw_tx) >= HEADER.size
            and len(item.raw_rx) >= len(runtime.DEVICE_BANNER)
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
        "sessions",
        "fixed_command_count",
        "fixed_commands",
        "hmac_authenticated",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "diagnostic_order_proof",
        "logical_resident_proof",
        "same_descriptor",
        "same_fd",
        "same_tty_fd",
        "physical_reopen_count",
        "descriptor_reopened",
        "caller_selected_command",
        "interactive_pty",
        "arbitrary_file_transfer",
        "persistent_state",
        "partial_raw_retention",
    }
)
_SESSION_PROOF_KEYS = frozenset(
    {
        "schema",
        "contract_id",
        "target",
        "run_id_hex",
        "command_count",
        "commands",
        "challenge_nonce_sha256",
        "auth_key_sha256",
        "tx",
        "rx",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "interactive_pty_proof",
        "caller_selected_command",
        "session_index",
        "raw_tx",
        "raw_rx",
        "diagnostics",
        "rng_eagain_retries",
        "preauth_diagnostics_only",
    }
)
_COMMAND_PROOF_KEYS = frozenset(
    {"sequence", "command_sha256", "output", "exit_code", "term_signal", "duration_ms"}
)
_IDENTITY_KEYS = frozenset({"size", "sha256"})
_HEX64 = frozenset("0123456789abcdef")


def _proof_failure(message: str) -> AuthObserverError:
    return AuthObserverError(f"P332 serialized proof differs: {message}")


def _proof_identity(value: Any, label: str, *, minimum_size: int = 1) -> None:
    if (
        type(value) is not dict
        or set(value) != _IDENTITY_KEYS
        or type(value["size"]) is not int
        or value["size"] < minimum_size
        or type(value["sha256"]) is not str
        or len(value["sha256"]) != 64
        or any(char not in _HEX64 for char in value["sha256"])
    ):
        raise _proof_failure(f"{label} identity differs")


def validate_proof_value(
    value: Any, *, expected_auth_key_sha256: str | None = None
) -> dict[str, Any]:
    """Strictly validate a JSON-decoded P3.32 resident proof receipt.

    The receipt contains only identities for private key/raw bytes.  An
    optional expected digest lets a caller bind that private key without
    passing the key itself through this host-only validator.
    """

    if type(value) is not dict or set(value) != _PROOF_KEYS:
        raise _proof_failure("proof key set differs")
    for key, expected in (
        ("schema", SCHEMA),
        ("contract_id", CONTRACT_ID),
        ("target", TARGET),
        ("run_id_hex", P332_RUN_ID_HEX),
    ):
        if value[key] != expected:
            raise _proof_failure(f"{key} differs")
    integer_values = (
        "session_cap",
        "reconnect_cap",
        "session_count",
        "successful_sessions",
        "reconnect_count",
        "fixed_command_count",
        "physical_reopen_count",
    )
    if any(type(value[key]) is not int for key in integer_values):
        raise _proof_failure("integer field type differs")
    if any(
        value[key] != expected
        for key, expected in (
            ("session_cap", MAX_SESSIONS),
            ("reconnect_cap", MAX_RECONNECTS),
            ("session_count", MAX_SESSIONS),
            ("successful_sessions", MAX_SESSIONS),
            ("reconnect_count", 0),
            ("fixed_command_count", len(DEFAULT_COMMANDS)),
            ("physical_reopen_count", PHYSICAL_REOPEN_COUNT),
        )
    ):
        raise _proof_failure("session/reconnect bound differs")
    expected_true = (
        "hmac_authenticated",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "diagnostic_order_proof",
        "logical_resident_proof",
        "same_descriptor",
        "same_fd",
        "same_tty_fd",
        "partial_raw_retention",
    )
    expected_false = (
        "descriptor_reopened",
        "caller_selected_command",
        "interactive_pty",
        "arbitrary_file_transfer",
        "persistent_state",
    )
    if any(value[key] is not True for key in expected_true) or any(
        value[key] is not False for key in expected_false
    ):
        raise _proof_failure("proof flags differ")

    commands = value["fixed_commands"]
    if type(commands) is not list or len(commands) != len(DEFAULT_COMMANDS):
        raise _proof_failure("fixed command list differs")
    for command_identity, command in zip(commands, DEFAULT_COMMANDS):
        if type(command_identity) is not dict or set(command_identity) != _IDENTITY_KEYS:
            raise _proof_failure("fixed command identity key set differs")
        expected = identity(command)
        if command_identity != expected:
            raise _proof_failure("fixed command identity differs")

    sessions = value["sessions"]
    if type(sessions) is not list or len(sessions) != MAX_SESSIONS:
        raise _proof_failure("session list differs")
    nonces: set[str] = set()
    auth_digests: set[str] = set()
    for index, session in enumerate(sessions):
        if type(session) is not dict or set(session) != _SESSION_PROOF_KEYS:
            raise _proof_failure(f"session {index} key set differs")
        for key, expected in (
            # Each row is the exact predecessor P330 per-session proof;
            # the outer receipt carries the fresh P332 wrapper identity.
            ("schema", _P330.SCHEMA),
            ("contract_id", _P330.CONTRACT_ID),
            ("target", TARGET),
            ("run_id_hex", P332_RUN_ID_HEX),
            ("command_count", len(DEFAULT_COMMANDS)),
            ("session_index", index),
        ):
            if session[key] != expected or type(session[key]) is not type(expected):
                raise _proof_failure(f"session {index} header differs")
        nonce_hash = session["challenge_nonce_sha256"]
        auth_digest = session["auth_key_sha256"]
        if (
            type(nonce_hash) is not str
            or len(nonce_hash) != 64
            or any(char not in _HEX64 for char in nonce_hash)
            or nonce_hash == "0" * 64
            or nonce_hash in nonces
            or type(auth_digest) is not str
            or len(auth_digest) != 64
            or any(char not in _HEX64 for char in auth_digest)
            or auth_digest == "0" * 64
        ):
            raise _proof_failure(f"session {index} nonce/key digest differs")
        if expected_auth_key_sha256 is not None and auth_digest != expected_auth_key_sha256:
            raise _proof_failure(f"session {index} auth key binding differs")
        nonces.add(nonce_hash)
        auth_digests.add(auth_digest)
        session_commands = session["commands"]
        if type(session_commands) is not list or len(session_commands) != len(DEFAULT_COMMANDS):
            raise _proof_failure(f"session {index} command list differs")
        for sequence, (command_proof, command) in enumerate(
            zip(session_commands, DEFAULT_COMMANDS), start=2
        ):
            if type(command_proof) is not dict or set(command_proof) != _COMMAND_PROOF_KEYS:
                raise _proof_failure(f"session {index} command key set differs")
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
        for key in (
            "tx",
            "rx",
            "raw_tx",
            "raw_rx",
        ):
            _proof_identity(
                session[key],
                f"session {index} {key}",
                minimum_size=HEADER.size if key.endswith("tx") else len(DEVICE_BANNER),
            )
        if session["tx"] != session["raw_tx"] or session["rx"] != session["raw_rx"]:
            raise _proof_failure(f"session {index} raw identity differs")
        diagnostics = session["diagnostics"]
        if type(diagnostics) is not list or len(diagnostics) != 2:
            raise _proof_failure(f"session {index} diagnostics differ")
        expected_stage = (runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, runtime.DIAGNOSTIC_STAGE_RNG)
        for item, stage in zip(diagnostics, expected_stage):
            if (
                type(item) is not dict
                or set(item) != {"stage", "code"}
                or type(item["stage"]) is not int
                or item["stage"] != stage
                or type(item["code"]) is not int
                or item["code"] < 0
                or item["code"] > runtime.RNG_EAGAIN_RETRY_LIMIT
                or (
                    stage == runtime.DIAGNOSTIC_STAGE_OPEN_PARSED
                    and item["code"] != 0
                )
            ):
                raise _proof_failure(f"session {index} diagnostic proof differs")
        if (
            type(session["rng_eagain_retries"]) is not int
            or session["rng_eagain_retries"] != diagnostics[1]["code"]
            or session["rng_eagain_retries"] < 0
            or session["rng_eagain_retries"] > runtime.RNG_EAGAIN_RETRY_LIMIT
            or session["preauth_diagnostics_only"] is not True
        ):
            raise _proof_failure(f"session {index} diagnostic summary differs")
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
    if len(auth_digests) != 1:
        raise _proof_failure("session auth key digests differ")
    return value


# Compatibility spellings keep the coordinator discoverable to a narrow live
# adapter without creating another execution path.
exchange_resident_sessions = exchange_resident
exchange_commands = exchange_resident
validate_default_proof = validate_resident_proof
ResidentSession = LogicalResidentSession
ResidentResult = LogicalResidentResult
ResidentObserverError = LogicalResidentObserverError


__all__ = [
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
    "LogicalResidentObserverError",
    "LogicalResidentResult",
    "LogicalResidentSession",
    "MAX_RECONNECTS",
    "MAX_SESSIONS",
    "MAX_PHYSICAL_REOPENS",
    "OPEN_DIAGNOSTIC_TIMEOUT_SEC",
    "P332_RUN_ID",
    "P332_RUN_ID_HEX",
    "P332ObserverBindingError",
    "PHYSICAL_REOPEN_COUNT",
    "ResidentObserverError",
    "ResidentResult",
    "ResidentSession",
    "SCHEMA",
    "SOURCE",
    "SOURCE_IDENTITY",
    "SessionResult",
    "SESSION_TIMEOUT_SEC",
    "TARGET",
    "RNG_DIAGNOSTIC_TIMEOUT_SEC",
    "compute_close_tag",
    "compute_exec_tag",
    "compute_open_tag",
    "compute_ready_tag",
    "constant_time_equal",
    "decode_diagnostic",
    "decode_frame",
    "encode_frame",
    "exchange_commands",
    "exchange_resident",
    "exchange_resident_sessions",
    "frame_crc",
    "identity",
    "parse_diagnostic_frame",
    "validate_command",
    "validate_commands",
    "validate_default_proof",
    "validate_proof_value",
    "validate_resident_proof",
]
