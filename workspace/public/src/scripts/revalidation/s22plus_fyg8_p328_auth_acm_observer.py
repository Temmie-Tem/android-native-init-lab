#!/usr/bin/env python3
"""Host codec and bounded observer for the P3.28 authenticated ACM session."""

from __future__ import annotations

import binascii
from dataclasses import dataclass, field
import hashlib
import hmac
import math
import os
import select
import struct
import time
from collections.abc import Sequence
from typing import Any

import s22plus_fyg8_p328_auth_exec_runtime as runtime


SCHEMA = "s22plus_fyg8_p328_auth_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p328-auth-acm-observer-v1"
TARGET = runtime.TARGET
HEADER = struct.Struct("<4sBBHII")
EXIT = struct.Struct("<IiIIQ")
DONE = struct.Struct("<I")
FLAG_TIMEOUT = 0x01
FLAG_TRUNCATED = 0x02
FLAG_EXEC_FAILURE = 0x04
KNOWN_FLAGS = FLAG_TIMEOUT | FLAG_TRUNCATED | FLAG_EXEC_FAILURE
COMMAND_TIMEOUT_SEC = runtime.COMMAND_TIMEOUT_SEC
DEFAULT_COMMANDS = runtime.DEFAULT_COMMANDS
AUTH_DOMAIN_OPEN = runtime.AUTH_DOMAIN_OPEN
AUTH_DOMAIN_READY = runtime.AUTH_DOMAIN_READY
AUTH_DOMAIN_EXEC = runtime.AUTH_DOMAIN_EXEC
AUTH_DOMAIN_CLOSE = runtime.AUTH_DOMAIN_CLOSE


class AuthObserverError(ValueError):
    """The P3.28 frame stream or authenticated command result differs."""


@dataclass(frozen=True)
class Frame:
    frame_type: int
    sequence: int
    payload: bytes


@dataclass(frozen=True)
class CommandResult:
    sequence: int
    command: bytes
    output: bytes
    flags: int
    exit_code: int
    term_signal: int
    duration_ms: int

    @property
    def ok(self) -> bool:
        return (
            self.flags == 0
            and self.exit_code == 0
            and self.term_signal == 0
        )


@dataclass
class ExchangeAudit:
    tx: bytearray = field(default_factory=bytearray)
    rx: bytearray = field(default_factory=bytearray)
    banner_seen: bool = False
    challenge_seen: bool = False
    ready_seen: bool = False
    authenticated: bool = False
    done_seen: bool = False
    nonce: bytes = b""
    auth_key_sha256: str = ""


@dataclass(frozen=True)
class SessionResult:
    commands: tuple[CommandResult, ...]
    audit: ExchangeAudit


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _validate_key(auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != runtime.AUTH_KEY_SIZE:
        raise AuthObserverError("auth_key must be exactly 32 bytes")
    return auth_key


def _validate_run_id(run_id: bytes) -> bytes:
    if type(run_id) is not bytes or len(run_id) != len(runtime.P328_RUN_ID):
        raise AuthObserverError("run_id must be exactly 16 bytes")
    return run_id


def _validate_nonce(nonce: bytes) -> bytes:
    if type(nonce) is not bytes or len(nonce) != runtime.NONCE_SIZE:
        raise AuthObserverError("nonce must be exactly 32 bytes")
    if not any(nonce):
        raise AuthObserverError("nonce must not be all zero")
    return nonce


def _validate_sequence(sequence: int) -> int:
    if type(sequence) is not int or not 0 <= sequence <= 0xFFFFFFFF:
        raise AuthObserverError("sequence is out of range")
    return sequence


def _validate_command(command: bytes) -> bytes:
    if type(command) is not bytes:
        raise AuthObserverError("command must be bytes")
    if not 1 <= len(command) <= runtime.MAX_COMMAND_SIZE:
        raise AuthObserverError("command size differs")
    if any(byte < 0x20 or byte > 0x7E for byte in command):
        raise AuthObserverError("command must be ASCII printable")
    if b"\x00" in command or b"\r" in command or b"\n" in command:
        raise AuthObserverError("command contains a forbidden delimiter")
    return command


def validate_command(command: bytes) -> bytes:
    """Validate one caller-selected ASCII-printable command payload."""

    return _validate_command(command)


def validate_commands(commands: Sequence[bytes]) -> tuple[bytes, ...]:
    if not isinstance(commands, Sequence) or isinstance(commands, (bytes, str)):
        raise AuthObserverError("commands must be a sequence")
    result = tuple(_validate_command(command) for command in commands)
    if not 1 <= len(result) <= runtime.MAX_COMMANDS:
        raise AuthObserverError("command count differs")
    return result


def _hmac_message(
    auth_key: bytes,
    domain: bytes,
    run_id: bytes,
    nonce: bytes,
    sequence: int | None = None,
    command: bytes = b"",
) -> bytes:
    key = _validate_key(auth_key)
    rid = _validate_run_id(run_id)
    random_nonce = _validate_nonce(nonce)
    if sequence is not None:
        _validate_sequence(sequence)
    if type(domain) is not bytes or not domain:
        raise AuthObserverError("authentication domain differs")
    if sequence is None and command:
        raise AuthObserverError("command requires a sequence")
    if command:
        _validate_command(command)
    message = bytearray(domain)
    message.extend(rid)
    message.extend(random_nonce)
    if sequence is not None:
        message.extend(struct.pack("<I", sequence))
    message.extend(command)
    return hmac.new(key, bytes(message), hashlib.sha256).digest()


def compute_open_tag(auth_key: bytes, run_id: bytes, nonce: bytes) -> bytes:
    return _hmac_message(auth_key, runtime.AUTH_DOMAIN_OPEN, run_id, nonce)


def compute_ready_tag(auth_key: bytes, run_id: bytes, nonce: bytes) -> bytes:
    return _hmac_message(auth_key, runtime.AUTH_DOMAIN_READY, run_id, nonce)


def compute_exec_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, sequence: int, command: bytes
) -> bytes:
    return _hmac_message(
        auth_key,
        runtime.AUTH_DOMAIN_EXEC,
        run_id,
        nonce,
        sequence,
        _validate_command(command),
    )


def compute_close_tag(
    auth_key: bytes, run_id: bytes, nonce: bytes, sequence: int
) -> bytes:
    return _hmac_message(
        auth_key, runtime.AUTH_DOMAIN_CLOSE, run_id, nonce, sequence
    )


def constant_time_equal(left: bytes, right: bytes) -> bool:
    if type(left) is not bytes or type(right) is not bytes:
        return False
    return hmac.compare_digest(left, right)


def frame_crc(prefix: bytes, payload: bytes) -> int:
    if len(prefix) != 12:
        raise AuthObserverError("frame prefix size differs")
    return binascii.crc32(payload, binascii.crc32(prefix)) & 0xFFFFFFFF


def encode_frame(frame_type: int, sequence: int, payload: bytes) -> bytes:
    if type(frame_type) is not int or not 0 <= frame_type <= 0xFF:
        raise AuthObserverError("frame type is out of range")
    _validate_sequence(sequence)
    if type(payload) is not bytes or len(payload) > runtime.MAX_FRAME_PAYLOAD:
        raise AuthObserverError("frame payload differs")
    prefix = struct.pack(
        "<4sBBHI",
        runtime.FRAME_MAGIC,
        runtime.FRAME_VERSION,
        frame_type,
        len(payload),
        sequence,
    )
    return prefix + struct.pack("<I", frame_crc(prefix, payload)) + payload


def decode_frame(value: bytes) -> Frame:
    if type(value) is not bytes or len(value) < HEADER.size:
        raise AuthObserverError("frame is short")
    magic, version, frame_type, length, sequence, received_crc = HEADER.unpack(
        value[: HEADER.size]
    )
    payload = value[HEADER.size :]
    if magic != runtime.FRAME_MAGIC or version != runtime.FRAME_VERSION:
        raise AuthObserverError("frame magic/version differs")
    if length != len(payload) or length > runtime.MAX_FRAME_PAYLOAD:
        raise AuthObserverError("frame payload length differs")
    if frame_crc(value[:12], payload) != received_crc:
        raise AuthObserverError("frame CRC differs")
    return Frame(frame_type, sequence, payload)


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("P328 authenticated exchange timed out")
    return remaining


def _read_exact(
    descriptor: int,
    size: int,
    deadline: float,
    audit: ExchangeAudit,
    writer: Any | None,
) -> bytes:
    output = bytearray()
    while len(output) < size:
        readable, _, _ = select.select(
            [descriptor], [], [], min(0.1, _remaining(deadline))
        )
        if not readable:
            continue
        try:
            chunk = os.read(descriptor, size - len(output))
        except BlockingIOError:
            continue
        if not chunk:
            raise AuthObserverError("P328 endpoint returned EOF")
        output.extend(chunk)
        audit.rx.extend(chunk)
        if writer is not None:
            writer.write_stdout(chunk)
    return bytes(output)


def _read_frame(
    descriptor: int,
    deadline: float,
    audit: ExchangeAudit,
    writer: Any | None,
) -> Frame:
    header = _read_exact(descriptor, HEADER.size, deadline, audit, writer)
    magic, version, _frame_type, length, _sequence, _crc = HEADER.unpack(header)
    if magic != runtime.FRAME_MAGIC or version != runtime.FRAME_VERSION:
        raise AuthObserverError("P328 peer magic/version differs")
    if length > runtime.MAX_FRAME_PAYLOAD:
        raise AuthObserverError("P328 peer payload exceeds its bound")
    payload = _read_exact(descriptor, length, deadline, audit, writer)
    return decode_frame(header + payload)


def _write_all(
    descriptor: int, value: bytes, deadline: float, audit: ExchangeAudit
) -> None:
    offset = 0
    while offset < len(value):
        _, writable, _ = select.select(
            [], [descriptor], [], min(0.1, _remaining(deadline))
        )
        if not writable:
            continue
        try:
            amount = os.write(descriptor, value[offset:])
        except BlockingIOError:
            continue
        if amount <= 0 or amount > len(value) - offset:
            raise AuthObserverError("P328 endpoint made no write progress")
        audit.tx.extend(value[offset : offset + amount])
        offset += amount


def _send(
    descriptor: int,
    frame_type: int,
    sequence: int,
    payload: bytes,
    deadline: float,
    audit: ExchangeAudit,
) -> None:
    _write_all(descriptor, encode_frame(frame_type, sequence, payload), deadline, audit)


def _expect(frame: Frame, frame_type: int, sequence: int) -> bytes:
    if frame.frame_type != frame_type or frame.sequence != sequence:
        raise AuthObserverError("P328 response type/sequence differs")
    return frame.payload


def _parse_exit(payload: bytes, output_size: int) -> tuple[int, int, int, int]:
    if len(payload) != EXIT.size:
        raise AuthObserverError("P328 EXIT size differs")
    flags, exit_code, signal_number, forwarded, duration_ms = EXIT.unpack(payload)
    if flags & ~KNOWN_FLAGS or forwarded != output_size:
        raise AuthObserverError("P328 EXIT accounting differs")
    if signal_number > 127 or duration_ms > 0x7FFFFFFFFFFFFFFF:
        raise AuthObserverError("P328 EXIT scalar differs")
    if (signal_number == 0 and not 0 <= exit_code <= 255) or (
        signal_number != 0 and exit_code != -1
    ):
        raise AuthObserverError("P328 EXIT status differs")
    if bool(flags & FLAG_TIMEOUT) and (signal_number != 9 or exit_code != -1):
        raise AuthObserverError("P328 timeout status differs")
    if bool(flags & FLAG_TRUNCATED) and output_size != runtime.MAX_OUTPUT_BYTES:
        raise AuthObserverError("P328 truncation accounting differs")
    if bool(flags & FLAG_EXEC_FAILURE) != (exit_code in (126, 127)):
        raise AuthObserverError("P328 exec-failure status differs")
    return flags, exit_code, signal_number, duration_ms


def exchange_commands(
    descriptor: int,
    auth_key: bytes,
    commands: Sequence[bytes] = DEFAULT_COMMANDS,
    *,
    timeout_sec: float = 300.0,
    writer: Any | None = None,
) -> SessionResult:
    key = _validate_key(auth_key)
    selected = validate_commands(commands)
    if (
        type(descriptor) is not int
        or descriptor < 0
        or type(timeout_sec) not in (int, float)
        or timeout_sec <= 0
        or timeout_sec > 600
        or not math.isfinite(float(timeout_sec))
    ):
        raise AuthObserverError("P328 exchange arguments differ")
    deadline = time.monotonic() + float(timeout_sec)
    audit = ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
    banner = _read_exact(
        descriptor, len(runtime.DEVICE_BANNER), deadline, audit, writer
    )
    if banner != runtime.DEVICE_BANNER:
        raise AuthObserverError("P328 banner differs")
    audit.banner_seen = True

    _send(descriptor, runtime.FRAME_OPEN, 0, runtime.P328_RUN_ID, deadline, audit)
    challenge = _read_frame(descriptor, deadline, audit, writer)
    nonce = _expect(challenge, runtime.FRAME_CHALLENGE, 0)
    _validate_nonce(nonce)
    audit.nonce = nonce
    audit.challenge_seen = True

    _send(
        descriptor,
        runtime.FRAME_AUTH,
        1,
        compute_open_tag(key, runtime.P328_RUN_ID, nonce),
        deadline,
        audit,
    )
    ready = _read_frame(descriptor, deadline, audit, writer)
    ready_tag = _expect(ready, runtime.FRAME_READY, 1)
    if not constant_time_equal(
        ready_tag, compute_ready_tag(key, runtime.P328_RUN_ID, nonce)
    ):
        raise AuthObserverError("P328 READY authentication differs")
    audit.ready_seen = True
    audit.authenticated = True

    results: list[CommandResult] = []
    for sequence, command in enumerate(selected, start=2):
        tag = compute_exec_tag(key, runtime.P328_RUN_ID, nonce, sequence, command)
        _send(
            descriptor,
            runtime.FRAME_EXEC,
            sequence,
            tag + command,
            deadline,
            audit,
        )
        output = bytearray()
        while True:
            frame = _read_frame(descriptor, deadline, audit, writer)
            if frame.sequence != sequence:
                raise AuthObserverError("P328 command response sequence differs")
            payload = frame.payload
            if frame.frame_type == runtime.FRAME_DATA:
                if not payload:
                    raise AuthObserverError("P328 DATA payload is empty")
                output.extend(payload)
                if len(output) > runtime.MAX_OUTPUT_BYTES:
                    raise AuthObserverError("P328 DATA exceeds output bound")
                continue
            if frame.frame_type != runtime.FRAME_EXIT:
                raise AuthObserverError("P328 command response type differs")
            flags, exit_code, signal_number, duration_ms = _parse_exit(
                payload, len(output)
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

    close_sequence = len(selected) + 2
    _send(
        descriptor,
        runtime.FRAME_CLOSE,
        close_sequence,
        compute_close_tag(key, runtime.P328_RUN_ID, nonce, close_sequence),
        deadline,
        audit,
    )
    done = _read_frame(descriptor, deadline, audit, writer)
    done_payload = _expect(done, runtime.FRAME_DONE, close_sequence)
    if len(done_payload) != DONE.size or DONE.unpack(done_payload)[0] != len(selected):
        raise AuthObserverError("P328 DONE count differs")
    audit.done_seen = True
    return SessionResult(tuple(results), audit)


def validate_default_proof(value: SessionResult) -> dict[str, Any]:
    if not isinstance(value, SessionResult):
        raise AuthObserverError("P328 proof result type differs")
    if tuple(item.command for item in value.commands) != DEFAULT_COMMANDS:
        raise AuthObserverError("P328 proof commands differ")
    if not all(item.ok for item in value.commands):
        raise AuthObserverError("P328 proof command failed")
    first, second, third = value.commands
    if b"uid=0" not in first.output or b"gid=0" not in first.output:
        raise AuthObserverError("P328 id proof differs")
    if b"Linux" not in second.output or not second.output.endswith(b"\n"):
        raise AuthObserverError("P328 uname proof differs")
    expected_nonce = f"P328-NONCE {runtime.P328_RUN_ID_HEX}\n".encode("ascii")
    if third.output != expected_nonce:
        raise AuthObserverError("P328 nonce proof differs")
    if not (
        value.audit.banner_seen
        and value.audit.challenge_seen
        and value.audit.ready_seen
        and value.audit.authenticated
        and value.audit.done_seen
    ):
        raise AuthObserverError("P328 authenticated session closure differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": runtime.P328_RUN_ID_HEX,
        "command_count": len(value.commands),
        "commands": [
            {
                "sequence": item.sequence,
                "command_sha256": hashlib.sha256(item.command).hexdigest(),
                "output": identity(item.output),
                "exit_code": item.exit_code,
                "term_signal": item.term_signal,
                "duration_ms": item.duration_ms,
            }
            for item in value.commands
        ],
        "challenge_nonce_sha256": hashlib.sha256(value.audit.nonce).hexdigest(),
        "auth_key_sha256": value.audit.auth_key_sha256,
        "tx": identity(bytes(value.audit.tx)),
        "rx": identity(bytes(value.audit.rx)),
        "pid1_authenticated_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "interactive_pty_proof": False,
        "caller_selected_command": True,
    }


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
    "DONE",
    "EXIT",
    "ExchangeAudit",
    "FLAG_EXEC_FAILURE",
    "FLAG_TIMEOUT",
    "FLAG_TRUNCATED",
    "Frame",
    "HEADER",
    "SCHEMA",
    "SessionResult",
    "TARGET",
    "compute_close_tag",
    "compute_exec_tag",
    "compute_open_tag",
    "compute_ready_tag",
    "constant_time_equal",
    "decode_frame",
    "encode_frame",
    "exchange_commands",
    "frame_crc",
    "identity",
    "validate_command",
    "validate_commands",
    "validate_default_proof",
]
