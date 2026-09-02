#!/usr/bin/env python3
"""Small host codec and bounded observer for the P3.27 ACM exec session."""

from __future__ import annotations

import binascii
from dataclasses import dataclass, field
import hashlib
import math
import os
import select
import struct
import time
from collections.abc import Sequence
from typing import Any

import s22plus_fyg8_p327_framed_exec_runtime as runtime


SCHEMA = "s22plus_fyg8_p327_framed_acm_session_v1"
CONTRACT_ID = "s22plus-fyg8-p327-framed-acm-observer-v1"
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


class FramedObserverError(ValueError):
    """The P3.27 frame stream or bounded command result differs."""


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
    ready_seen: bool = False
    done_seen: bool = False


@dataclass(frozen=True)
class SessionResult:
    commands: tuple[CommandResult, ...]
    audit: ExchangeAudit


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def frame_crc(prefix: bytes, payload: bytes) -> int:
    if len(prefix) != 12:
        raise FramedObserverError("frame prefix size differs")
    return binascii.crc32(payload, binascii.crc32(prefix)) & 0xFFFFFFFF


def encode_frame(frame_type: int, sequence: int, payload: bytes) -> bytes:
    if type(frame_type) is not int or not 0 <= frame_type <= 0xFF:
        raise FramedObserverError("frame type is out of range")
    if type(sequence) is not int or not 0 <= sequence <= 0xFFFFFFFF:
        raise FramedObserverError("frame sequence is out of range")
    if type(payload) is not bytes or len(payload) > runtime.MAX_FRAME_PAYLOAD:
        raise FramedObserverError("frame payload differs")
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
        raise FramedObserverError("frame is short")
    magic, version, frame_type, length, sequence, received_crc = HEADER.unpack(
        value[: HEADER.size]
    )
    payload = value[HEADER.size :]
    if magic != runtime.FRAME_MAGIC or version != runtime.FRAME_VERSION:
        raise FramedObserverError("frame magic/version differs")
    if length != len(payload) or length > runtime.MAX_FRAME_PAYLOAD:
        raise FramedObserverError("frame payload length differs")
    if frame_crc(value[:12], payload) != received_crc:
        raise FramedObserverError("frame CRC differs")
    return Frame(frame_type, sequence, payload)


def validate_commands(commands: Sequence[bytes]) -> tuple[bytes, ...]:
    if not isinstance(commands, Sequence) or isinstance(commands, (bytes, str)):
        raise FramedObserverError("commands must be a sequence")
    result = tuple(commands)
    if result != DEFAULT_COMMANDS:
        raise FramedObserverError("fixed proof commands differ")
    return result


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("P327 framed exchange timed out")
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
            raise FramedObserverError("P327 endpoint returned EOF")
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
        raise FramedObserverError("P327 peer magic/version differs")
    if length > runtime.MAX_FRAME_PAYLOAD:
        raise FramedObserverError("P327 peer payload exceeds its bound")
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
            raise FramedObserverError("P327 endpoint made no write progress")
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
    _write_all(
        descriptor,
        encode_frame(frame_type, sequence, payload),
        deadline,
        audit,
    )


def _expect(frame: Frame, frame_type: int, sequence: int) -> bytes:
    if frame.frame_type != frame_type or frame.sequence != sequence:
        raise FramedObserverError("P327 response type/sequence differs")
    return frame.payload


def _parse_exit(payload: bytes, output_size: int) -> tuple[int, int, int, int]:
    if len(payload) != EXIT.size:
        raise FramedObserverError("P327 EXIT size differs")
    flags, exit_code, signal_number, forwarded, duration_ms = EXIT.unpack(payload)
    if flags & ~KNOWN_FLAGS or forwarded != output_size:
        raise FramedObserverError("P327 EXIT accounting differs")
    if signal_number > 127 or duration_ms > 0x7FFFFFFFFFFFFFFF:
        raise FramedObserverError("P327 EXIT scalar differs")
    if (signal_number == 0 and not 0 <= exit_code <= 255) or (
        signal_number != 0 and exit_code != -1
    ):
        raise FramedObserverError("P327 EXIT status differs")
    if bool(flags & FLAG_TIMEOUT) and (signal_number != 9 or exit_code != -1):
        raise FramedObserverError("P327 timeout status differs")
    if bool(flags & FLAG_TRUNCATED) and output_size != runtime.MAX_OUTPUT_BYTES:
        raise FramedObserverError("P327 truncation accounting differs")
    if bool(flags & FLAG_EXEC_FAILURE) != (exit_code in (126, 127)):
        raise FramedObserverError("P327 exec-failure status differs")
    return flags, exit_code, signal_number, duration_ms


def exchange_commands(
    descriptor: int,
    commands: Sequence[bytes] = DEFAULT_COMMANDS,
    *,
    timeout_sec: float = 100.0,
    writer: Any | None = None,
) -> SessionResult:
    selected = validate_commands(commands)
    if (
        type(descriptor) is not int
        or descriptor < 0
        or type(timeout_sec) not in (int, float)
        or timeout_sec <= 0
        or timeout_sec > 120
        or not math.isfinite(float(timeout_sec))
    ):
        raise FramedObserverError("P327 exchange arguments differ")
    deadline = time.monotonic() + timeout_sec
    audit = ExchangeAudit()
    banner = _read_exact(
        descriptor, len(runtime.DEVICE_BANNER), deadline, audit, writer
    )
    if banner != runtime.DEVICE_BANNER:
        raise FramedObserverError("P327 banner differs")
    audit.banner_seen = True

    _send(
        descriptor,
        runtime.FRAME_OPEN,
        0,
        runtime.P327_RUN_ID,
        deadline,
        audit,
    )
    ready = _read_frame(descriptor, deadline, audit, writer)
    if _expect(ready, runtime.FRAME_READY, 0) != runtime.P327_RUN_ID:
        raise FramedObserverError("P327 READY binding differs")
    audit.ready_seen = True

    results: list[CommandResult] = []
    for sequence, command in enumerate(selected, start=1):
        _send(
            descriptor,
            runtime.FRAME_EXEC,
            sequence,
            command,
            deadline,
            audit,
        )
        output = bytearray()
        while True:
            frame = _read_frame(descriptor, deadline, audit, writer)
            if frame.sequence != sequence:
                raise FramedObserverError("P327 command response sequence differs")
            payload = frame.payload
            if frame.frame_type == runtime.FRAME_DATA:
                if not payload:
                    raise FramedObserverError("P327 DATA payload is empty")
                output.extend(payload)
                if len(output) > runtime.MAX_OUTPUT_BYTES:
                    raise FramedObserverError("P327 DATA exceeds output bound")
                continue
            if frame.frame_type != runtime.FRAME_EXIT:
                raise FramedObserverError("P327 command response type differs")
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

    close_sequence = len(selected) + 1
    _send(
        descriptor,
        runtime.FRAME_CLOSE,
        close_sequence,
        b"",
        deadline,
        audit,
    )
    done = _read_frame(descriptor, deadline, audit, writer)
    done_payload = _expect(done, runtime.FRAME_DONE, close_sequence)
    if len(done_payload) != DONE.size or DONE.unpack(done_payload)[0] != len(selected):
        raise FramedObserverError("P327 DONE count differs")
    audit.done_seen = True
    return SessionResult(tuple(results), audit)


def validate_default_proof(value: SessionResult) -> dict[str, Any]:
    if not isinstance(value, SessionResult):
        raise FramedObserverError("P327 proof result type differs")
    if tuple(item.command for item in value.commands) != DEFAULT_COMMANDS:
        raise FramedObserverError("P327 proof commands differ")
    if not all(item.ok for item in value.commands):
        raise FramedObserverError("P327 proof command failed")
    first, second, third = value.commands
    if b"uid=0" not in first.output or b"gid=0" not in first.output:
        raise FramedObserverError("P327 id proof differs")
    if b"Linux" not in second.output or not second.output.endswith(b"\n"):
        raise FramedObserverError("P327 uname proof differs")
    expected_nonce = f"P327-NONCE {runtime.P327_RUN_ID_HEX}\n".encode("ascii")
    if third.output != expected_nonce:
        raise FramedObserverError("P327 nonce proof differs")
    if not (
        value.audit.banner_seen
        and value.audit.ready_seen
        and value.audit.done_seen
    ):
        raise FramedObserverError("P327 session closure differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": runtime.P327_RUN_ID_HEX,
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
        "tx": identity(bytes(value.audit.tx)),
        "rx": identity(bytes(value.audit.rx)),
        "pid1_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "interactive_pty_proof": False,
    }


__all__ = [
    "COMMAND_TIMEOUT_SEC",
    "CONTRACT_ID",
    "CommandResult",
    "DEFAULT_COMMANDS",
    "DONE",
    "EXIT",
    "ExchangeAudit",
    "FLAG_EXEC_FAILURE",
    "FLAG_TIMEOUT",
    "FLAG_TRUNCATED",
    "Frame",
    "FramedObserverError",
    "HEADER",
    "SCHEMA",
    "SessionResult",
    "TARGET",
    "decode_frame",
    "encode_frame",
    "exchange_commands",
    "frame_crc",
    "identity",
    "validate_commands",
    "validate_default_proof",
]
