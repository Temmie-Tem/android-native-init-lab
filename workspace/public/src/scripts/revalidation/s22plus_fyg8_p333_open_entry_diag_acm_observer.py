#!/usr/bin/env python3
"""P3.33 observer for the stage-0 console-entry diagnostic.

The exact P3.32 same-FD observer remains the protocol engine.  P3.33 consumes
one additional non-authoritative diagnostic frame immediately before each
P3.30 session's existing OPEN_PARSED/RNG sequence.  It neither retries nor
changes the OPEN, HMAC, fixed-command, close, descriptor, or raw-first rules.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any

import s22plus_fyg8_p333_open_entry_diag_runtime as runtime


SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p332_logical_resident_acm_observer.py"
)
SOURCE_IDENTITY = {
    "size": 30_892,
    "sha256": "af64b65806bf0c521c375b2db158022e0bd1b625f82862fa47769f31e1cb481f",
}
SCHEMA = "s22plus_fyg8_p333_open_entry_diag_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p333-open-entry-diag-acm-observer-v1"


class P333ObserverBindingError(ValueError):
    """The exact P3.32 observer source could not be rebound."""


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
        raise P333ObserverBindingError("P3.32 observer source is unavailable") from exc
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
        raise P333ObserverBindingError("P3.32 observer source identity differs")
    module = types.ModuleType("s22plus_fyg8_p332_observer_bound_for_p333")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    runtime_name = "s22plus_fyg8_p332_logical_resident_exec_runtime"
    module_name = module.__name__
    previous = sys.modules.get(runtime_name)
    previous_module = sys.modules.get(module_name)
    sys.modules[runtime_name] = runtime
    sys.modules[module_name] = module
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P333ObserverBindingError("P3.32 observer source failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(runtime_name, None)
        else:
            sys.modules[runtime_name] = previous
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
    module.runtime = runtime
    return module


_P332 = _load()
_BASE = _P332._BASE

Frame = _P332.Frame
CommandResult = _P332.CommandResult
Diagnostic = _P332.Diagnostic
ExchangeAudit = _P332.ExchangeAudit
SessionResult = _P332.SessionResult
LogicalResidentSession = _P332.LogicalResidentSession
LogicalResidentResult = _P332.LogicalResidentResult
AuthObserverError = _P332.AuthObserverError
LogicalResidentObserverError = _P332.LogicalResidentObserverError
ResidentObserverError = LogicalResidentObserverError
ResidentSession = LogicalResidentSession
ResidentResult = LogicalResidentResult

HEADER = _P332.HEADER
EXIT = _P332.EXIT
DONE = _P332.DONE
DIAGNOSTIC = _P332.DIAGNOSTIC
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
compute_open_tag = _P332.compute_open_tag
compute_ready_tag = _P332.compute_ready_tag
compute_exec_tag = _P332.compute_exec_tag
compute_close_tag = _P332.compute_close_tag
constant_time_equal = _P332.constant_time_equal
encode_frame = _P332.encode_frame
decode_frame = _P332.decode_frame
frame_crc = _P332.frame_crc
validate_command = _P332.validate_command
validate_commands = _P332.validate_commands

P333_RUN_ID_HEX = runtime.P333_RUN_ID_HEX
P333_RUN_ID = runtime.P333_RUN_ID
P332_RUN_ID_HEX = P333_RUN_ID_HEX
P332_RUN_ID = P333_RUN_ID
P328_RUN_ID_HEX = P333_RUN_ID_HEX
P328_RUN_ID = P333_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
TARGET = runtime.TARGET
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
MAX_SESSIONS = runtime.MAX_SESSIONS
MAX_RECONNECTS = 0
PHYSICAL_REOPEN_COUNT = 0
SESSION_TIMEOUT_SEC = _P332.SESSION_TIMEOUT_SEC
OPEN_DIAGNOSTIC_TIMEOUT_SEC = _P332.OPEN_DIAGNOSTIC_TIMEOUT_SEC
RNG_DIAGNOSTIC_TIMEOUT_SEC = _P332.RNG_DIAGNOSTIC_TIMEOUT_SEC


def decode_diagnostic(payload: bytes) -> Diagnostic:
    if type(payload) is not bytes or len(payload) != DIAGNOSTIC.size:
        raise AuthObserverError("P333 diagnostic payload differs")
    stage, code = DIAGNOSTIC.unpack(payload)
    if stage == runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER:
        if code != 0:
            raise AuthObserverError("P333 console-entry diagnostic code differs")
        return Diagnostic(stage, code)
    return _P332.decode_diagnostic(payload)


def parse_diagnostic_frame(frame: Any, expected_stage: int) -> Diagnostic:
    if expected_stage != runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER:
        return _P332.parse_diagnostic_frame(frame, expected_stage)
    if (
        not isinstance(frame, Frame)
        or frame.frame_type != runtime.DIAGNOSTIC_FRAME_TYPE
        or frame.sequence != 0
    ):
        raise AuthObserverError("P333 console-entry diagnostic frame differs")
    diagnostic = decode_diagnostic(frame.payload)
    if diagnostic.stage != expected_stage:
        raise AuthObserverError("P333 console-entry diagnostic order differs")
    return diagnostic


def _exchange_one(
    descriptor: int,
    auth_key: bytes,
    writer: Any,
    seen_nonces: set[bytes],
    timeout_sec: float,
) -> SessionResult:
    with _P332._EXCHANGE_LOCK:
        original = _BASE._read_frame  # noqa: SLF001
        entry_seen = False

        def read_with_entry(
            fd: int, deadline: float, audit: ExchangeAudit, raw_writer: Any
        ) -> Frame:
            nonlocal entry_seen
            frame = original(fd, deadline, audit, raw_writer)
            if not entry_seen:
                parse_diagnostic_frame(
                    frame, runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER
                )
                audit.p333_console_enter_seen = True
                entry_seen = True
                frame = original(fd, deadline, audit, raw_writer)
            if frame.frame_type == runtime.FRAME_CHALLENGE:
                nonce = _BASE._expect(frame, runtime.FRAME_CHALLENGE, 0)  # noqa: SLF001
                if nonce in seen_nonces:
                    raise AuthObserverError("P333 challenge nonce was replayed")
            return frame

        _BASE._read_frame = read_with_entry  # noqa: SLF001
        try:
            result = _P332._P330.exchange_commands(  # noqa: SLF001
                descriptor,
                auth_key,
                DEFAULT_COMMANDS,
                timeout_sec=timeout_sec,
                writer=writer,
            )
        finally:
            _BASE._read_frame = original  # noqa: SLF001
    if not entry_seen or getattr(result.audit, "p333_console_enter_seen", False) is not True:
        raise AuthObserverError("P333 console-entry diagnostic is absent", audit=result.audit)
    nonce = result.audit.nonce
    if nonce in seen_nonces:
        raise AuthObserverError("P333 challenge nonce was replayed")
    seen_nonces.add(nonce)
    return result


def exchange_resident(
    connection: Any,
    auth_key: bytes,
    *,
    timeout_sec: float = SESSION_TIMEOUT_SEC,
    writer: Any | None = None,
) -> LogicalResidentResult:
    with _P332._EXCHANGE_LOCK:
        original = _P332._exchange_one  # noqa: SLF001
        _P332._exchange_one = _exchange_one  # noqa: SLF001
        try:
            return _P332.exchange_resident(
                connection,
                auth_key,
                timeout_sec=timeout_sec,
                writer=writer,
            )
        finally:
            _P332._exchange_one = original  # noqa: SLF001


def validate_resident_proof(value: LogicalResidentResult) -> dict[str, Any]:
    try:
        proof = deepcopy(_P332.validate_resident_proof(value))
    except Exception as exc:
        if isinstance(exc, LogicalResidentObserverError):
            raise
        raise AuthObserverError(f"P333 resident proof differs: {exc}") from exc
    for session, rendered in zip(value.sessions, proof["sessions"]):
        if (
            session.audit is None
            or getattr(session.audit, "p333_console_enter_seen", False) is not True
        ):
            raise LogicalResidentObserverError(
                "P333 console-entry proof is absent",
                result=value,
                session_index=session.index,
            )
        rendered["diagnostics"].insert(
            0,
            {"stage": runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER, "code": 0},
        )
    proof["schema"] = SCHEMA
    proof["contract_id"] = CONTRACT_ID
    proof["run_id_hex"] = P333_RUN_ID_HEX
    return proof


def validate_proof_value(
    value: Any, *, expected_auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not dict:
        raise AuthObserverError("P333 serialized proof is not an object")
    if (
        value.get("schema") != SCHEMA
        or value.get("contract_id") != CONTRACT_ID
        or value.get("run_id_hex") != P333_RUN_ID_HEX
    ):
        raise AuthObserverError("P333 serialized proof header differs")
    predecessor = deepcopy(value)
    predecessor["schema"] = _P332.SCHEMA
    predecessor["contract_id"] = _P332.CONTRACT_ID
    sessions = predecessor.get("sessions")
    if type(sessions) is not list or len(sessions) != MAX_SESSIONS:
        raise AuthObserverError("P333 serialized session list differs")
    for index, session in enumerate(sessions):
        diagnostics = session.get("diagnostics") if isinstance(session, dict) else None
        if (
            type(diagnostics) is not list
            or len(diagnostics) != 3
            or diagnostics[0]
            != {"stage": runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER, "code": 0}
        ):
            raise AuthObserverError(
                f"P333 serialized session {index} entry diagnostic differs"
            )
        session["diagnostics"] = diagnostics[1:]
    try:
        _P332.validate_proof_value(
            predecessor,
            expected_auth_key_sha256=expected_auth_key_sha256,
        )
    except Exception as exc:
        raise AuthObserverError(f"P333 serialized proof differs: {exc}") from exc
    return value


exchange_resident_sessions = exchange_resident
exchange_commands = exchange_resident
validate_default_proof = validate_resident_proof

__all__ = sorted(
    {
        *getattr(_P332, "__all__", ()),
        "AuthObserverError",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "DIAGNOSTIC",
        "Diagnostic",
        "ExchangeAudit",
        "LogicalResidentObserverError",
        "LogicalResidentResult",
        "LogicalResidentSession",
        "MAX_RECONNECTS",
        "MAX_SESSIONS",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "P333ObserverBindingError",
        "PHYSICAL_REOPEN_COUNT",
        "ResidentObserverError",
        "ResidentResult",
        "ResidentSession",
        "SCHEMA",
        "SESSION_TIMEOUT_SEC",
        "SOURCE",
        "SOURCE_IDENTITY",
        "compute_close_tag",
        "compute_exec_tag",
        "compute_open_tag",
        "compute_ready_tag",
        "decode_diagnostic",
        "decode_frame",
        "encode_frame",
        "exchange_commands",
        "exchange_resident",
        "exchange_resident_sessions",
        "frame_crc",
        "identity",
        "parse_diagnostic_frame",
        "validate_default_proof",
        "validate_proof_value",
        "validate_resident_proof",
    }
)
