#!/usr/bin/env python3
"""P3.30 authenticated ACM observer with bounded pre-auth diagnostics.

The S328 authenticated command protocol is unchanged.  P3.30 reads two fixed
device diagnostics between OPEN and CHALLENGE and preserves the actual partial
exchange when any step fails.  Diagnostics can localize a failure but can
never satisfy the authenticated command proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import os
from pathlib import Path
import stat
import struct
import sys
import time
import types
from collections.abc import Sequence
from typing import Any

import s22plus_fyg8_p330_auth_exec_runtime as runtime


SOURCE = Path(__file__).with_name("s22plus_fyg8_p329_auth_acm_observer.py")
SOURCE_IDENTITY = {
    "size": 3_579,
    "sha256": "ddcc7ab2cc8e6fd70f096b4b19606d9e9fde8355eaa9cb65534b43eb917bbe76",
}
SCHEMA = "s22plus_fyg8_p330_auth_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p330-auth-acm-observer-v1"
DIAGNOSTIC = struct.Struct("<Ii")
# Short enough to avoid P329's opaque 120-second wait, but deliberately wider
# than an immediate scheduling turn and the fixed 6.4-second EAGAIN loop.
OPEN_DIAGNOSTIC_TIMEOUT_SEC = 5.0
RNG_DIAGNOSTIC_TIMEOUT_SEC = 10.0


class P330ObserverBindingError(ValueError):
    """The exact P3.29 observer source could not be rebound to P3.30."""


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
        raise P330ObserverBindingError("P3.29 observer source is unavailable") from exc
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
        raise P330ObserverBindingError("P3.29 observer source identity differs")
    module = types.ModuleType("s22plus_fyg8_p329_observer_bound_for_p330")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    runtime_key = "s22plus_fyg8_p329_auth_exec_runtime"
    module_key = module.__name__
    previous_runtime = sys.modules.get(runtime_key)
    previous_module = sys.modules.get(module_key)
    sys.modules[runtime_key] = runtime
    sys.modules[module_key] = module
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P330ObserverBindingError("P3.29 observer source failed to load") from exc
    finally:
        if previous_runtime is None:
            sys.modules.pop(runtime_key, None)
        else:
            sys.modules[runtime_key] = previous_runtime
        if previous_module is None:
            sys.modules.pop(module_key, None)
        else:
            sys.modules[module_key] = previous_module
    return module


_P329 = _load()
_BASE = _P329._P328
_BASE.runtime = runtime
_BASE.DEFAULT_COMMANDS = runtime.DEFAULT_COMMANDS
_BASE.CONTRACT_ID = CONTRACT_ID
_BASE.SCHEMA = SCHEMA
for _name in getattr(_P329, "__all__", ()):
    globals()[_name] = getattr(_P329, _name)
SCHEMA = "s22plus_fyg8_p330_auth_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p330-auth-acm-observer-v1"


@dataclass(frozen=True)
class Diagnostic:
    stage: int
    code: int


@dataclass
class ExchangeAudit(_BASE.ExchangeAudit):
    diagnostics: list[Diagnostic] = field(default_factory=list)
    current_stage: str = "start"
    failure_stage: str | None = None
    failure_code: int | None = None
    exception_type: str | None = None
    exception_sha256: str | None = None
    rng_eagain_retries: int | None = None


class AuthObserverError(_BASE.AuthObserverError):
    """P3.30 failure carrying the actual partial exchange audit."""

    def __init__(
        self,
        message: str,
        *,
        audit: ExchangeAudit | None = None,
        stage: str | None = None,
        code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.audit = audit
        self.stage = stage
        self.code = code


def decode_diagnostic(payload: bytes) -> Diagnostic:
    if type(payload) is not bytes or len(payload) != DIAGNOSTIC.size:
        raise AuthObserverError("P330 diagnostic payload differs")
    stage, code = DIAGNOSTIC.unpack(payload)
    if stage not in (
        runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
        runtime.DIAGNOSTIC_STAGE_RNG,
    ):
        raise AuthObserverError("P330 diagnostic stage differs")
    return Diagnostic(stage, code)


def parse_diagnostic_frame(frame: Any, expected_stage: int) -> Diagnostic:
    if (
        not isinstance(frame, _BASE.Frame)
        or frame.frame_type != runtime.DIAGNOSTIC_FRAME_TYPE
        or frame.sequence != 0
    ):
        raise AuthObserverError("P330 diagnostic frame differs")
    diagnostic = decode_diagnostic(frame.payload)
    if diagnostic.stage != expected_stage:
        raise AuthObserverError("P330 diagnostic order differs")
    if expected_stage == runtime.DIAGNOSTIC_STAGE_OPEN_PARSED:
        if diagnostic.code != 0:
            raise AuthObserverError("P330 OPEN diagnostic code differs")
    elif not -4095 <= diagnostic.code <= runtime.RNG_EAGAIN_RETRY_LIMIT:
        raise AuthObserverError("P330 RNG diagnostic code differs")
    return diagnostic


def _bounded_deadline(overall: float, seconds: float) -> float:
    return min(overall, time.monotonic() + seconds)


def _raise_partial(
    exc: Exception,
    audit: ExchangeAudit,
    stage: str,
    *,
    code: int | None = None,
) -> None:
    if isinstance(exc, AuthObserverError) and exc.audit is audit:
        raise exc
    audit.failure_stage = stage
    audit.failure_code = code
    audit.exception_type = type(exc).__name__
    preimage = f"{type(exc).__name__}:{exc}".encode("utf-8", "replace")
    audit.exception_sha256 = hashlib.sha256(preimage).hexdigest()
    raise AuthObserverError(
        f"P330 exchange stopped at {stage}",
        audit=audit,
        stage=stage,
        code=code,
    ) from exc


def exchange_commands(
    descriptor: int,
    auth_key: bytes,
    commands: Sequence[bytes] = runtime.DEFAULT_COMMANDS,
    *,
    timeout_sec: float = 300.0,
    writer: Any | None = None,
) -> Any:
    key = _BASE._validate_key(auth_key)  # noqa: SLF001
    selected = _BASE.validate_commands(commands)
    if (
        type(descriptor) is not int
        or descriptor < 0
        or type(timeout_sec) not in (int, float)
        or timeout_sec <= 0
        or timeout_sec > 600
        or not math.isfinite(float(timeout_sec))
    ):
        raise AuthObserverError("P330 exchange arguments differ")
    deadline = time.monotonic() + float(timeout_sec)
    audit = ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())

    def stage(name: str) -> None:
        audit.current_stage = name

    try:
        stage("banner-read")
        banner = _BASE._read_exact(  # noqa: SLF001
            descriptor, len(runtime.DEVICE_BANNER), deadline, audit, writer
        )
        if banner != runtime.DEVICE_BANNER:
            raise AuthObserverError("P330 banner differs")
        audit.banner_seen = True

        stage("open-write")
        _BASE._send(  # noqa: SLF001
            descriptor, runtime.FRAME_OPEN, 0, runtime.P330_RUN_ID, deadline, audit
        )

        stage("open-diagnostic-read")
        opened = parse_diagnostic_frame(
            _BASE._read_frame(  # noqa: SLF001
                descriptor,
                _bounded_deadline(deadline, OPEN_DIAGNOSTIC_TIMEOUT_SEC),
                audit,
                writer,
            ),
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
        )
        audit.diagnostics.append(opened)

        stage("rng-diagnostic-read")
        rng = parse_diagnostic_frame(
            _BASE._read_frame(  # noqa: SLF001
                descriptor,
                _bounded_deadline(deadline, RNG_DIAGNOSTIC_TIMEOUT_SEC),
                audit,
                writer,
            ),
            runtime.DIAGNOSTIC_STAGE_RNG,
        )
        audit.diagnostics.append(rng)
        if rng.code < 0:
            raise AuthObserverError("P330 device RNG failed", code=rng.code)
        audit.rng_eagain_retries = rng.code

        stage("challenge-read")
        challenge = _BASE._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
        nonce = _BASE._expect(challenge, runtime.FRAME_CHALLENGE, 0)  # noqa: SLF001
        _BASE._validate_nonce(nonce)  # noqa: SLF001
        audit.nonce = nonce
        audit.challenge_seen = True

        stage("auth-write")
        _BASE._send(  # noqa: SLF001
            descriptor,
            runtime.FRAME_AUTH,
            1,
            _BASE.compute_open_tag(key, runtime.P330_RUN_ID, nonce),
            deadline,
            audit,
        )
        stage("ready-read")
        ready = _BASE._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
        ready_tag = _BASE._expect(ready, runtime.FRAME_READY, 1)  # noqa: SLF001
        if not _BASE.constant_time_equal(
            ready_tag, _BASE.compute_ready_tag(key, runtime.P330_RUN_ID, nonce)
        ):
            raise AuthObserverError("P330 READY authentication differs")
        audit.ready_seen = True
        audit.authenticated = True

        results: list[Any] = []
        for sequence, command in enumerate(selected, start=2):
            stage("exec-write")
            tag = _BASE.compute_exec_tag(
                key, runtime.P330_RUN_ID, nonce, sequence, command
            )
            _BASE._send(  # noqa: SLF001
                descriptor,
                runtime.FRAME_EXEC,
                sequence,
                tag + command,
                deadline,
                audit,
            )
            output = bytearray()
            while True:
                stage("exec-read")
                frame = _BASE._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
                if frame.sequence != sequence:
                    raise AuthObserverError("P330 command response sequence differs")
                if frame.frame_type == runtime.FRAME_DATA:
                    if not frame.payload:
                        raise AuthObserverError("P330 DATA payload is empty")
                    output.extend(frame.payload)
                    if len(output) > runtime.MAX_OUTPUT_BYTES:
                        raise AuthObserverError("P330 DATA exceeds output bound")
                    continue
                if frame.frame_type != runtime.FRAME_EXIT:
                    raise AuthObserverError("P330 command response type differs")
                flags, exit_code, signal_number, duration_ms = _BASE._parse_exit(  # noqa: SLF001
                    frame.payload, len(output)
                )
                results.append(
                    _BASE.CommandResult(
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

        close_sequence = len(selected) + 2
        stage("close-write")
        _BASE._send(  # noqa: SLF001
            descriptor,
            runtime.FRAME_CLOSE,
            close_sequence,
            _BASE.compute_close_tag(
                key, runtime.P330_RUN_ID, nonce, close_sequence
            ),
            deadline,
            audit,
        )
        stage("done-read")
        done = _BASE._read_frame(descriptor, deadline, audit, writer)  # noqa: SLF001
        done_payload = _BASE._expect(done, runtime.FRAME_DONE, close_sequence)  # noqa: SLF001
        if (
            len(done_payload) != _BASE.DONE.size
            or _BASE.DONE.unpack(done_payload)[0] != len(selected)
        ):
            raise AuthObserverError("P330 DONE count differs")
        audit.done_seen = True
        stage("complete")
        return _BASE.SessionResult(tuple(results), audit)
    except Exception as exc:
        _raise_partial(
            exc,
            audit,
            audit.current_stage,
            code=getattr(exc, "code", None),
        )


def validate_default_proof(value: Any) -> dict[str, Any]:
    try:
        result = dict(_BASE.validate_default_proof(value))
    except Exception as exc:
        raise AuthObserverError(f"P330 authenticated proof differs: {exc}") from exc
    audit = value.audit
    expected = [
        Diagnostic(runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0),
        Diagnostic(runtime.DIAGNOSTIC_STAGE_RNG, audit.rng_eagain_retries),
    ]
    if (
        not isinstance(audit, ExchangeAudit)
        or audit.diagnostics != expected
        or type(audit.rng_eagain_retries) is not int
        or not 0 <= audit.rng_eagain_retries <= runtime.RNG_EAGAIN_RETRY_LIMIT
        or audit.failure_stage is not None
        or audit.exception_type is not None
        or audit.current_stage != "complete"
    ):
        raise AuthObserverError("P330 diagnostic proof projection differs")
    result.update(
        {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "run_id_hex": runtime.P330_RUN_ID_HEX,
            "diagnostics": [
                {"stage": item.stage, "code": item.code}
                for item in audit.diagnostics
            ],
            "rng_eagain_retries": audit.rng_eagain_retries,
            "preauth_diagnostics_only": True,
        }
    )
    return result


DEFAULT_COMMANDS = runtime.DEFAULT_COMMANDS
TARGET = runtime.TARGET
Frame = _BASE.Frame
CommandResult = _BASE.CommandResult
SessionResult = _BASE.SessionResult
HEADER = _BASE.HEADER
EXIT = _BASE.EXIT
DONE = _BASE.DONE

__all__ = sorted(
    set(getattr(_P329, "__all__", ()))
    | {
        "AuthObserverError",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DIAGNOSTIC",
        "Diagnostic",
        "ExchangeAudit",
        "OPEN_DIAGNOSTIC_TIMEOUT_SEC",
        "P330ObserverBindingError",
        "RNG_DIAGNOSTIC_TIMEOUT_SEC",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "decode_diagnostic",
        "exchange_commands",
        "parse_diagnostic_frame",
        "validate_default_proof",
    }
)
