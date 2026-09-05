#!/usr/bin/env python3
"""Host-only P3.45 first-F1 runtime qualification observer.

The caller supplies an already-owned descriptor and one bounded raw-capture
writer.  This observer performs exactly five logical P345 sessions on that
same descriptor, with no endpoint selection, reopen, retry, lease, device
authority, or candidate publication.  The existing authenticated exchange
does all framing and transport parsing; this module verifies the semantic
canary and the expected command outcomes around it.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
import re
import struct
import time
from typing import Any, Mapping

import s22plus_fyg8_p345_research_shell_runtime as runtime
import s22plus_fyg8_research_shell_exchange as shell_exchange


SCHEMA = "s22plus-fyg8-p345-research-shell-qualification-v1"
CONTRACT_ID = "s22plus-fyg8-p345-research-shell-qualification-observer-v1"
TARGET = runtime.TARGET
RUN_ID = runtime.P345_RUN_ID
RUN_ID_HEX = runtime.P345_RUN_ID_HEX
QUALIFICATION_TIMEOUT_SEC = 300.0
SESSION_COUNT = 5
SAME_FD_SESSION_COUNT = 5
RECONNECT_COUNT = 0
CANCEL_DELAY_SEC = 0.2
UID = 65534
GID = 65534
PROBE_DENIED_MARKER = b"P345-PROBE-DENIED\n"
PROBE_CREATED_MARKER = b"P345-PROBE-CREATED\n"
PROBE_ABSENT_MARKER = b"P345-PROBE-ABSENT\n"
PROBE_PRESENT_MARKER = b"P345-PROBE-PRESENT\n"
CANARY_MARKER = b"P345-CANARY\n"
CANCEL_MARKER = b"P345-CANCEL-MARKER\n"
PIPELINE_MARKER = b"P345-PIPE-MARKER\n"

CANARY_COMMAND = (
    b"/bin/busybox id; /bin/busybox cat /proc/uptime; "
    b"if ( : >/probe ); then printf 'P345-PROBE-CREATED\\n'; "
    b"else printf 'P345-PROBE-DENIED\\n'; fi; "
    b"if test ! -e /probe; then printf 'P345-PROBE-ABSENT\\n'; "
    b"else printf 'P345-PROBE-PRESENT\\n'; fi; "
    b"printf 'P345-CANARY\\n'"
)
EXIT7_COMMAND = b"exit 7"
TIMEOUT_COMMAND = b"/bin/busybox sleep 30"
CANCEL_COMMAND = (
    b"printf 'P345-CANCEL-MARKER\\n'; /bin/busybox sleep 30"
)
PIPELINE_COMMAND = (
    b"printf 'P345-PIPE-%s\\n' \"$(printf marker)\" | /bin/busybox tr a-z A-Z"
)


@dataclass(frozen=True)
class QualificationStep:
    ordinal: int
    name: str
    command: bytes
    expected_outcome: str


QUALIFICATION_COMMANDS: tuple[QualificationStep, ...] = (
    QualificationStep(1, "readonly-canary", CANARY_COMMAND, "ok"),
    QualificationStep(2, "expected-command-failure", EXIT7_COMMAND, "command-failed"),
    QualificationStep(3, "command-timeout", TIMEOUT_COMMAND, "timeout"),
    QualificationStep(4, "authenticated-cancel", CANCEL_COMMAND, "cancelled"),
    QualificationStep(5, "post-cancel-pipeline", PIPELINE_COMMAND, "ok"),
)


class QualificationError(ValueError):
    """A semantic or transport failure in the bounded qualification unit."""

    def __init__(
        self,
        message: str,
        *,
        partial_receipt: Mapping[str, Any] | None = None,
        failed_session: str | None = None,
        audit: Any | None = None,
        category: str = "qualification",
        sessions: tuple[Any, ...] = (),
    ) -> None:
        super().__init__(message)
        self.partial_receipt = dict(partial_receipt or {})
        self.failed_session = failed_session
        self.audit = audit
        self.category = category
        self.sessions = tuple(sessions)
        self.completed_sessions = self.sessions
        self.failed_audit = audit


@dataclass(frozen=True)
class QualificationResult(Mapping[str, Any]):
    """Completed receipt plus parsed session objects for the caller's publisher."""

    receipt: Mapping[str, Any]
    sessions: tuple[Any, ...]

    def __getitem__(self, key: str) -> Any:
        return self.receipt[key]

    def __iter__(self):
        return iter(self.receipt)

    def __len__(self) -> int:
        return len(self.receipt)


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def _audit_bytes(audit: Any, name: str) -> bytes:
    value = getattr(audit, name, b"")
    if type(value) not in (bytes, bytearray):
        raise QualificationError(f"P345 {name} audit stream differs")
    return bytes(value)


def _writer_sizes(writer: Any) -> tuple[int, int] | None:
    current_sizes = getattr(writer, "current_sizes", None)
    if not callable(current_sizes):
        return None
    try:
        value = current_sizes()
    except Exception:
        return None
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(item) is not int or item < 0 for item in value)
    ):
        return None
    return value


def _capture_span(
    before: tuple[int, int] | None, after: tuple[int, int] | None
) -> dict[str, int] | None:
    if before is None or after is None:
        return None
    if any(after[index] < before[index] for index in (0, 1)):
        return None
    return {
        "stdout_offset": before[0],
        "stdout_size": after[0] - before[0],
        "stderr_offset": before[1],
        "stderr_size": after[1] - before[1],
    }


def _validate_step(step: QualificationStep) -> QualificationStep:
    if not isinstance(step, QualificationStep):
        raise QualificationError("P345 qualification step type differs")
    if (
        type(step.ordinal) is not int
        or type(step.name) is not str
        or type(step.command) is not bytes
        or type(step.expected_outcome) is not str
        or not 1 <= step.ordinal <= SESSION_COUNT
        or not step.name
        or not 1 <= len(step.command) <= runtime.MAX_COMMAND_SIZE
        or step.expected_outcome
        not in {"ok", "command-failed", "timeout", "cancelled"}
    ):
        raise QualificationError("P345 qualification step values differ")
    return step


def _session_audit_checks(audit: Any) -> None:
    if audit is None:
        raise QualificationError("P345 session audit is absent")
    if not all(
        getattr(audit, name, False) is True
        for name in (
            "banner_seen",
            "challenge_seen",
            "ready_seen",
            "authenticated",
            "done_seen",
        )
    ):
        raise QualificationError("P345 authenticated session closure differs")
    nonce = getattr(audit, "nonce", b"")
    boot_id = getattr(audit, "boot_id", b"")
    if (
        type(nonce) is not bytes
        or len(nonce) != runtime.NONCE_SIZE
        or not any(nonce)
        or type(boot_id) is not bytes
        or len(boot_id) != runtime.P335_BOOT_ID_SIZE
    ):
        raise QualificationError("P345 authenticated identity audit differs")


def _canary_semantics(output: bytes) -> dict[str, Any]:
    if type(output) is not bytes:
        raise QualificationError("P345 canary output type differs")
    uid_seen = re.search(rb"\buid=65534(?:\([^\n)]*\))?\b", output) is not None
    gid_seen = re.search(rb"\bgid=65534(?:\([^\n)]*\))?\b", output) is not None
    uptime_seen = re.search(
        rb"(?m)^[0-9]+(?:\.[0-9]+)?[ \t]+[0-9]+(?:\.[0-9]+)?[ \t]*$",
        output,
    ) is not None
    semantics = {
        "uid_65534": uid_seen,
        "gid_65534": gid_seen,
        "read_proc_uptime": uptime_seen,
        "attempted_create_probe": True,
        "probe_create_denied": PROBE_DENIED_MARKER in output,
        "probe_create_succeeded": PROBE_CREATED_MARKER in output,
        "probe_absent": PROBE_ABSENT_MARKER in output,
        "probe_present": PROBE_PRESENT_MARKER in output,
        "marker_seen": CANARY_MARKER in output,
    }
    if not (
        semantics["uid_65534"]
        and semantics["gid_65534"]
        and semantics["read_proc_uptime"]
        and semantics["probe_create_denied"]
        and not semantics["probe_create_succeeded"]
        and semantics["probe_absent"]
        and not semantics["probe_present"]
        and semantics["marker_seen"]
    ):
        raise QualificationError("P345 read-only canary semantics differ")
    return semantics


def _validate_command_results(
    step: QualificationStep, session: Any, shell_result: Any
) -> dict[str, Any]:
    _validate_step(step)
    if session is None or not hasattr(session, "commands"):
        raise QualificationError("P345 session result is absent")
    commands = getattr(session, "commands")
    if not isinstance(commands, (tuple, list)) or len(commands) != 3:
        raise QualificationError("P345 three-command session shape differs")
    expected = (runtime.DEFAULT_COMMANDS[0], step.command, runtime.DEFAULT_COMMANDS[2])
    command_rows: list[dict[str, Any]] = []
    for index, (item, expected_command) in enumerate(zip(commands, expected), 3):
        if (
            getattr(item, "sequence", None) != index
            or getattr(item, "command", None) != expected_command
        ):
            raise QualificationError("P345 command identity differs")
        output = getattr(item, "output", None)
        if type(output) is not bytes:
            raise QualificationError("P345 command output type differs")
        flags = getattr(item, "flags", None)
        exit_code = getattr(item, "exit_code", None)
        term_signal = getattr(item, "term_signal", None)
        duration_ms = getattr(item, "duration_ms", None)
        if (
            type(flags) is not int
            or type(exit_code) is not int
            or type(term_signal) is not int
            or type(duration_ms) is not int
            or flags < 0
            or exit_code < -1
            or term_signal < 0
            or duration_ms < 0
        ):
            raise QualificationError("P345 command result values differ")
        command_rows.append(
            {
                "sequence": index,
                "command": identity(expected_command),
                "output": identity(output),
                "flags": flags,
                "exit_code": exit_code,
                "term_signal": term_signal,
                "duration_ms": duration_ms,
            }
        )

    first, middle, last = commands
    if not (
        first.flags == 0
        and first.exit_code == 0
        and first.term_signal == 0
        and first.output.startswith(b"uid=0(root) gid=0(root)")
        and first.output.endswith(b"\n")
    ):
        raise QualificationError("P345 parent identity witness differs")
    expected_nonce = b"P328-NONCE " + RUN_ID_HEX.encode("ascii") + b"\n"
    if not (
        last.flags == 0
        and last.exit_code == 0
        and last.term_signal == 0
        and last.output == expected_nonce
    ):
        raise QualificationError("P345 nonce witness differs")

    outcome = getattr(shell_result, "outcome", None)
    if outcome != step.expected_outcome:
        raise QualificationError("P345 command outcome differs")
    cancel_sent = getattr(shell_result, "cancel_sent", None)
    cancel_ack = getattr(shell_result, "cancel_ack", None)
    if step.ordinal == 4:
        if (
            cancel_sent is not True
            or cancel_ack != runtime.P345_CANCEL_STATUS_CONSUMED
            or not (middle.flags & runtime.P345_CANCELLED_FLAG)
            or middle.output.find(CANCEL_MARKER) < 0
        ):
            raise QualificationError("P345 active cancellation proof differs")
    elif cancel_sent is not False or cancel_ack is not None:
        raise QualificationError("P345 cancellation occurred outside sequence 4")

    semantic: dict[str, Any] = {}
    if step.ordinal == 1:
        if not (middle.flags == 0 and middle.exit_code == 0 and middle.term_signal == 0):
            raise QualificationError("P345 canary exit differs")
        semantic = _canary_semantics(middle.output)
    elif step.ordinal == 2:
        if not (middle.flags == 0 and middle.exit_code == 7 and middle.term_signal == 0):
            raise QualificationError("P345 expected command failure differs")
    elif step.ordinal == 3:
        if not (
            middle.flags & 0x01
            and middle.flags & ~0x01 == 0
            and middle.exit_code == -1
            and middle.term_signal == 9
        ):
            raise QualificationError("P345 timeout result differs")
    elif step.ordinal == 5:
        if not (
            middle.flags == 0
            and middle.exit_code == 0
            and middle.term_signal == 0
            and middle.output == PIPELINE_MARKER
        ):
            raise QualificationError("P345 post-cancel pipeline differs")

    return {
        "outcome": outcome,
        "cancel_sent": cancel_sent,
        "cancel_ack": cancel_ack,
        "commands": command_rows,
        "semantic": semantic,
    }


def _session_row(
    step: QualificationStep,
    shell_result: Any,
    *,
    rx_offset: int,
    tx_offset: int,
    capture_span: Mapping[str, int] | None,
) -> dict[str, Any]:
    session = getattr(shell_result, "session", None)
    audit = getattr(session, "audit", None)
    _session_audit_checks(audit)
    checked = _validate_command_results(step, session, shell_result)
    rx = _audit_bytes(audit, "rx")
    tx = _audit_bytes(audit, "tx")
    row: dict[str, Any] = {
        "ordinal": step.ordinal,
        "name": step.name,
        "descriptor_reused": True,
        "command": identity(step.command),
        "outcome": checked["outcome"],
        "cancel_sent": checked["cancel_sent"],
        "cancel_ack": checked["cancel_ack"],
        "boot_id_sha256": hashlib.sha256(audit.boot_id).hexdigest(),
        "nonce_sha256": hashlib.sha256(audit.nonce).hexdigest(),
        "rx": {"offset": rx_offset, **identity(rx)},
        "tx": {"offset": tx_offset, **identity(tx)},
        "commands": checked["commands"],
        "semantic": checked["semantic"],
    }
    if capture_span is not None:
        row["raw_capture"] = dict(capture_span)
    return row


def _base_receipt(
    sessions: list[dict[str, Any]],
    *,
    expected_boot_sha256: str | None,
    proved: bool,
    failure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": RUN_ID_HEX,
        "session_count": len(sessions),
        "required_session_count": SESSION_COUNT,
        "same_fd_session_count": SAME_FD_SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT,
        "same_descriptor": True,
        "expected_boot_sha256": expected_boot_sha256,
        "sessions": list(sessions),
        "proved": proved,
        "authority_granted_by_observer": False,
    }
    if failure is not None:
        value["failure"] = dict(failure)
    return value


class _CapturedFrameCursor:
    """Bounded cursor over one already-captured S328 byte stream."""

    def __init__(self, value: bytes, codec: Any) -> None:
        if type(value) is not bytes:
            raise QualificationError("P345 captured stream type differs")
        self.value = value
        self.codec = codec
        self.offset = 0

    def take(self, size: int) -> bytes:
        if type(size) is not int or size < 0:
            raise QualificationError("P345 captured stream span differs")
        end = self.offset + size
        if end > len(self.value):
            raise QualificationError("P345 captured stream is truncated")
        result = self.value[self.offset:end]
        self.offset = end
        return result

    def frame(self) -> Any:
        header_size = self.codec.HEADER.size
        header = self.take(header_size)
        _magic, _version, _frame_type, length, _sequence, _crc = (
            self.codec.HEADER.unpack(header)
        )
        if length > runtime.MAX_FRAME_PAYLOAD:
            raise QualificationError("P345 captured frame exceeds its bound")
        payload = self.take(length)
        try:
            return self.codec.decode_frame(header + payload)
        except Exception as exc:
            raise QualificationError("P345 captured frame fails codec validation") from exc


def _captured_expect(cursor: _CapturedFrameCursor, frame_type: int, sequence: int) -> Any:
    frame = cursor.frame()
    if frame.frame_type != frame_type or frame.sequence != sequence:
        raise QualificationError("P345 captured frame type/sequence differs")
    return frame


def _captured_hmac(
    key: bytes,
    domain: bytes,
    run_id: bytes,
    nonce: bytes,
    sequence: int | None = None,
    command: bytes = b"",
) -> bytes:
    message = bytearray(domain)
    message.extend(run_id)
    message.extend(nonce)
    if sequence is not None:
        message.extend(struct.pack("<I", sequence))
    message.extend(command)
    return hmac.new(key, bytes(message), hashlib.sha256).digest()


def parse_captured_session(
    observer: Any,
    rx: bytes,
    tx: bytes,
    auth_key: bytes,
) -> Any:
    """Reparse one raw P345 session without I/O, then return ``ShellExchange``.

    The captured streams are the exact audit RX/TX bytes produced by the
    existing exchange.  This parser consumes the fixed banner, diagnostics,
    authenticated OPEN/READY/BOOT, three EXECs, optional sequence-4 CANCEL and
    ACK, CLOSE, and DONE, rejecting any trailing or missing byte.  It does not
    open descriptors, resynchronize, or retry.
    """

    if type(rx) is not bytes or type(tx) is not bytes:
        raise QualificationError("P345 captured RX/TX type differs")
    if type(auth_key) is not bytes or len(auth_key) != runtime.AUTH_KEY_SIZE:
        raise QualificationError("P345 captured authentication key differs")
    codec = getattr(observer, "_CODEC", None)
    if codec is None:
        raise QualificationError("P345 captured observer codec is absent")
    audit: Any | None = None
    try:
        audit = observer.ExchangeAudit(
            auth_key_sha256=hashlib.sha256(auth_key).hexdigest()
        )
        # Preserve the caller's exact bounded streams even if a later
        # semantic/frame check rejects this replay.
        audit.rx = bytearray(rx)
        audit.tx = bytearray(tx)
        rx_cursor = _CapturedFrameCursor(rx, codec)
        tx_cursor = _CapturedFrameCursor(tx, codec)

        if rx_cursor.take(len(runtime.DEVICE_BANNER)) != runtime.DEVICE_BANNER:
            raise QualificationError("P345 captured device banner differs")
        audit.banner_seen = True
        diagnostics = []
        for stage in (
            runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
            runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
            runtime.DIAGNOSTIC_STAGE_RNG,
        ):
            frame = rx_cursor.frame()
            diagnostics.append(observer._P333.parse_diagnostic_frame(frame, stage))
        audit.diagnostics = diagnostics
        if diagnostics[-1].code < 0:
            raise QualificationError("P345 captured RNG diagnostic differs")
        audit.rng_eagain_retries = diagnostics[-1].code

        challenge = _captured_expect(
            rx_cursor, runtime.FRAME_CHALLENGE, 0
        )
        nonce = bytes(challenge.payload)
        codec._validate_nonce(nonce)
        audit.nonce = nonce
        audit.challenge_seen = True

        run_id = runtime.P335_RUN_ID
        opened = _captured_expect(tx_cursor, runtime.FRAME_OPEN, 0)
        if opened.payload != run_id:
            raise QualificationError("P345 captured OPEN identity differs")
        auth = _captured_expect(tx_cursor, runtime.FRAME_AUTH, 1)
        if not hmac.compare_digest(
            auth.payload,
            _captured_hmac(auth_key, runtime.AUTH_DOMAIN_OPEN, run_id, nonce),
        ):
            raise QualificationError("P345 captured OPEN authentication differs")

        ready = _captured_expect(rx_cursor, runtime.FRAME_READY, 1)
        if not hmac.compare_digest(
            ready.payload,
            _captured_hmac(auth_key, runtime.AUTH_DOMAIN_READY, run_id, nonce),
        ):
            raise QualificationError("P345 captured READY authentication differs")
        audit.ready_seen = True
        audit.authenticated = True

        boot_frame = _captured_expect(
            rx_cursor, runtime.FRAME_BOOT_ID, runtime.P335_BOOT_ID_SEQUENCE
        )
        boot_id = observer.decode_boot_id_frame(
            boot_frame, auth_key, run_id, nonce
        )
        audit.boot_id = boot_id

        tx_commands: dict[int, bytes] = {}
        for sequence in (3, 4):
            frame = _captured_expect(tx_cursor, runtime.FRAME_EXEC, sequence)
            if len(frame.payload) < runtime.AUTH_TAG_SIZE:
                raise QualificationError("P345 captured EXEC payload is short")
            command = bytes(frame.payload[runtime.AUTH_TAG_SIZE :])
            shell_exchange.command_bytes(command)
            expected_tag = _captured_hmac(
                auth_key,
                runtime.AUTH_DOMAIN_EXEC,
                run_id,
                nonce,
                sequence,
                command,
            )
            if not hmac.compare_digest(frame.payload[: runtime.AUTH_TAG_SIZE], expected_tag):
                raise QualificationError("P345 captured EXEC authentication differs")
            tx_commands[sequence] = command
        if tx_commands[3] != runtime.DEFAULT_COMMANDS[0]:
            raise QualificationError("P345 captured identity command differs")

        cancel_sent = False
        cancel_ack: int | None = None
        next_frame = tx_cursor.frame()
        if next_frame.frame_type == runtime.FRAME_CANCEL:
            if (
                next_frame.sequence != runtime.P345_CANCEL_SEQUENCE
                or len(next_frame.payload) != runtime.P345_CANCEL_PAYLOAD_SIZE
                or not hmac.compare_digest(
                    next_frame.payload,
                    runtime.cancel_tag(auth_key, run_id, nonce),
                )
            ):
                raise QualificationError("P345 captured CANCEL authentication differs")
            cancel_sent = True
            next_frame = _captured_expect(tx_cursor, runtime.FRAME_EXEC, 5)
        elif next_frame.frame_type != runtime.FRAME_EXEC or next_frame.sequence != 5:
            raise QualificationError("P345 captured sequence-5 EXEC differs")
        if len(next_frame.payload) < runtime.AUTH_TAG_SIZE:
            raise QualificationError("P345 captured sequence-5 payload is short")
        command = bytes(next_frame.payload[runtime.AUTH_TAG_SIZE :])
        if command != runtime.DEFAULT_COMMANDS[2]:
            raise QualificationError("P345 captured nonce command differs")
        if not hmac.compare_digest(
            next_frame.payload[: runtime.AUTH_TAG_SIZE],
            _captured_hmac(
                auth_key,
                runtime.AUTH_DOMAIN_EXEC,
                run_id,
                nonce,
                5,
                command,
            ),
        ):
            raise QualificationError("P345 captured nonce authentication differs")
        tx_commands[5] = command

        close = _captured_expect(tx_cursor, runtime.FRAME_CLOSE, 6)
        if not hmac.compare_digest(
            close.payload,
            _captured_hmac(
                auth_key, runtime.AUTH_DOMAIN_CLOSE, run_id, nonce, 6
            ),
        ):
            raise QualificationError("P345 captured CLOSE authentication differs")
        if tx_cursor.offset != len(tx):
            raise QualificationError("P345 captured TX has trailing bytes")

        results = []
        for sequence in (3, 4, 5):
            output = bytearray()
            while True:
                frame = rx_cursor.frame()
                if frame.sequence != sequence:
                    raise QualificationError("P345 captured response sequence differs")
                if frame.frame_type == runtime.FRAME_DATA:
                    if not frame.payload or len(output) + len(frame.payload) > runtime.MAX_OUTPUT_BYTES:
                        raise QualificationError("P345 captured DATA bound differs")
                    output.extend(frame.payload)
                    continue
                if frame.frame_type != runtime.FRAME_EXIT:
                    raise QualificationError("P345 captured response type differs")
                flags, exit_code, signal_number, duration_ms = shell_exchange.parse_exit(
                    codec, frame.payload, len(output)
                )
                if sequence != 4 and (flags or exit_code or signal_number):
                    raise QualificationError("P345 captured fixed command failed")
                results.append(
                    observer.CommandResult(
                        sequence,
                        tx_commands[sequence],
                        bytes(output),
                        flags,
                        exit_code,
                        signal_number,
                        duration_ms,
                    )
                )
                if sequence == 4:
                    if cancel_sent:
                        ack = _captured_expect(
                            rx_cursor, runtime.FRAME_CANCEL_ACK, 4
                        )
                        if len(ack.payload) != 4:
                            raise QualificationError("P345 captured CANCEL ACK size differs")
                        cancel_ack = struct.unpack("<I", ack.payload)[0]
                        if cancel_ack not in (
                            runtime.P345_CANCEL_STATUS_CONSUMED,
                            runtime.P345_CANCEL_STATUS_ALREADY_COMPLETED,
                        ) or bool(flags & runtime.P345_CANCELLED_FLAG) != (
                            cancel_ack == runtime.P345_CANCEL_STATUS_CONSUMED
                        ):
                            raise QualificationError("P345 captured CANCEL ACK outcome differs")
                    elif flags & runtime.P345_CANCELLED_FLAG:
                        raise QualificationError("P345 captured unsolicited cancellation")
                break

        done = _captured_expect(rx_cursor, runtime.FRAME_DONE, 6)
        if (
            len(done.payload) != 4
            or struct.unpack("<I", done.payload)[0] != 3
        ):
            raise QualificationError("P345 captured DONE count differs")
        if rx_cursor.offset != len(rx):
            raise QualificationError("P345 captured RX has trailing bytes")
        audit.rx = bytearray(rx)
        audit.tx = bytearray(tx)
        audit.done_seen = True
        audit.current_stage = "complete"
        outcome_result = results[1]
        outcome = (
            "cancelled"
            if outcome_result.flags & runtime.P345_CANCELLED_FLAG
            else "timeout"
            if outcome_result.flags & 0x01
            else "truncated"
            if outcome_result.flags & 0x02
            else "exec-failed"
            if outcome_result.flags & 0x04
            else "command-failed"
            if outcome_result.exit_code or outcome_result.term_signal
            else "ok"
        )
        session = observer.SessionResult(tuple(results), audit)
        return shell_exchange.ShellExchange(
            session, outcome, cancel_sent, cancel_ack
        )
    except QualificationError as exc:
        if getattr(exc, "audit", None) is None:
            exc.audit = audit
        raise
    except Exception as exc:
        raise QualificationError(
            "P345 captured session parse failed",
            audit=audit,
            category="transport",
        ) from exc


def validate_session_result(
    shell_result: Any, step: QualificationStep
) -> dict[str, Any]:
    """Validate one already-parsed exchange without opening its descriptor."""

    step = _validate_step(step)
    return _session_row(
        step,
        shell_result,
        rx_offset=0,
        tx_offset=0,
        capture_span=None,
    )


def validate_qualification(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a completed JSON-shaped qualification receipt."""

    if not isinstance(value, Mapping):
        raise QualificationError("P345 qualification receipt is not an object")
    required = {
        "schema",
        "contract_id",
        "target",
        "run_id_hex",
        "session_count",
        "required_session_count",
        "same_fd_session_count",
        "reconnect_count",
        "same_descriptor",
        "expected_boot_sha256",
        "sessions",
        "proved",
        "authority_granted_by_observer",
    }
    if not required <= set(value):
        raise QualificationError("P345 qualification receipt fields differ")
    if (
        type(value["session_count"]) is not int
        or type(value["required_session_count"]) is not int
        or type(value["same_fd_session_count"]) is not int
        or type(value["reconnect_count"]) is not int
        or value["schema"] != SCHEMA
        or value["contract_id"] != CONTRACT_ID
        or value["target"] != TARGET
        or value["run_id_hex"] != RUN_ID_HEX
        or value["required_session_count"] != SESSION_COUNT
        or value["same_fd_session_count"] != SAME_FD_SESSION_COUNT
        or value["reconnect_count"] != RECONNECT_COUNT
        or value["same_descriptor"] is not True
        or value["authority_granted_by_observer"] is not False
        or value["proved"] is not True
    ):
        raise QualificationError("P345 qualification receipt identity differs")
    sessions = value["sessions"]
    if (
        not isinstance(sessions, list)
        or len(sessions) != SESSION_COUNT
        or value["session_count"] != SESSION_COUNT
    ):
        raise QualificationError("P345 qualification session count differs")
    boot_ids: set[str] = set()
    expected_boot = value.get("expected_boot_sha256")
    if (
        type(expected_boot) is not str
        or re.fullmatch(r"[0-9a-f]{64}", expected_boot) is None
    ):
        raise QualificationError("P345 qualification expected boot digest differs")
    expected_rx_offset = 0
    expected_tx_offset = 0
    for expected, session in zip(QUALIFICATION_COMMANDS, sessions):
        if (
            not isinstance(session, Mapping)
            or session.get("ordinal") != expected.ordinal
            or session.get("name") != expected.name
            or session.get("outcome") != expected.expected_outcome
            or session.get("descriptor_reused") is not True
            or session.get("command") != identity(expected.command)
            or not isinstance(session.get("commands"), list)
            or len(session["commands"]) != 3
        ):
            raise QualificationError("P345 qualification session identity differs")
        for sequence, command_row, command in zip(
            (3, 4, 5), session["commands"],
            (runtime.DEFAULT_COMMANDS[0], expected.command, runtime.DEFAULT_COMMANDS[2]),
        ):
            if (
                not isinstance(command_row, Mapping)
                or command_row.get("sequence") != sequence
                or command_row.get("command") != identity(command)
                or type(command_row.get("flags")) is not int
                or type(command_row.get("exit_code")) is not int
                or type(command_row.get("term_signal")) is not int
                or type(command_row.get("duration_ms")) is not int
                or not isinstance(command_row.get("output"), Mapping)
            ):
                raise QualificationError("P345 qualification command receipt differs")
        middle = session["commands"][1]
        if expected.ordinal == 1 and (
            middle["flags"] != 0
            or middle["exit_code"] != 0
            or middle["term_signal"] != 0
        ):
            raise QualificationError("P345 qualification canary exit differs")
        if expected.ordinal == 2 and (
            middle["flags"] != 0
            or middle["exit_code"] != 7
            or middle["term_signal"] != 0
        ):
            raise QualificationError("P345 qualification expected failure differs")
        if expected.ordinal == 3 and (
            middle["flags"] != 1
            or middle["exit_code"] != -1
            or middle["term_signal"] != 9
        ):
            raise QualificationError("P345 qualification timeout differs")
        if expected.ordinal == 5 and (
            middle["flags"] != 0
            or middle["exit_code"] != 0
            or middle["term_signal"] != 0
            or middle["output"] != identity(PIPELINE_MARKER)
        ):
            raise QualificationError("P345 qualification pipeline differs")
        rx = session.get("rx")
        tx = session.get("tx")
        for stream, offset in ((rx, expected_rx_offset), (tx, expected_tx_offset)):
            if (
                not isinstance(stream, Mapping)
                or stream.get("offset") != offset
                or type(stream.get("size")) is not int
                or stream["size"] < 0
                or not isinstance(stream.get("sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", stream["sha256"]) is None
            ):
                raise QualificationError("P345 qualification raw span differs")
        expected_rx_offset += rx["size"]
        expected_tx_offset += tx["size"]
        boot_id = session.get("boot_id_sha256")
        if not isinstance(boot_id, str) or len(boot_id) != 64:
            raise QualificationError("P345 qualification boot binding differs")
        boot_ids.add(boot_id)
        if expected.ordinal == 1:
            semantic = session.get("semantic")
            if (
                not isinstance(semantic, Mapping)
                or semantic.get("uid_65534") is not True
                or semantic.get("gid_65534") is not True
                or semantic.get("read_proc_uptime") is not True
                or semantic.get("probe_create_denied") is not True
                or semantic.get("probe_create_succeeded") is not False
                or semantic.get("probe_absent") is not True
                or semantic.get("probe_present") is not False
                or semantic.get("marker_seen") is not True
            ):
                raise QualificationError("P345 qualification canary semantics differ")
        if expected.ordinal == 4:
            if (
                session.get("cancel_sent") is not True
                or session.get("cancel_ack")
                != runtime.P345_CANCEL_STATUS_CONSUMED
                or not (session["commands"][1].get("flags", 0) & runtime.P345_CANCELLED_FLAG)
            ):
                raise QualificationError("P345 qualification cancel proof differs")
        else:
            if session.get("cancel_sent") is not False or session.get("cancel_ack") is not None:
                raise QualificationError("P345 qualification cancel scope differs")
    if len(boot_ids) != 1:
        raise QualificationError("P345 qualification boot changed between sessions")
    if expected_boot is not None and expected_boot not in boot_ids:
        raise QualificationError("P345 qualification expected boot differs")
    return dict(value)


def _failure_receipt(
    sessions: list[dict[str, Any]],
    *,
    expected_boot_sha256: str | None,
    step: QualificationStep,
    exc: BaseException,
    audit: Any | None,
) -> dict[str, Any]:
    failure: dict[str, Any] = {
        "session": step.name,
        "ordinal": step.ordinal,
        "exception_type": type(exc).__name__,
        "exception_sha256": _digest_text(f"{type(exc).__name__}:{exc}"),
    }
    if audit is not None:
        try:
            rx = _audit_bytes(audit, "rx")
            tx = _audit_bytes(audit, "tx")
            failure["audit"] = {
                "rx": identity(rx),
                "tx": identity(tx),
                "failure_stage": getattr(audit, "current_stage", None),
                "cancel_sent": getattr(exc, "cancel_sent", False),
            }
        except QualificationError:
            failure["audit"] = {"available": False}
    return _base_receipt(
        sessions,
        expected_boot_sha256=expected_boot_sha256,
        proved=False,
        failure=failure,
    )


def _validate_arguments(
    descriptor: int,
    auth_key: bytes,
    expected_boot_sha256: str | None,
    seen_nonces: set[str],
    writer: Any,
    deadline: float,
) -> None:
    now = time.monotonic()
    if type(descriptor) is not int or descriptor < 0:
        raise QualificationError("P345 qualification descriptor differs")
    if type(auth_key) is not bytes or len(auth_key) != runtime.AUTH_KEY_SIZE:
        raise QualificationError("P345 qualification key differs")
    if expected_boot_sha256 is not None and (
        type(expected_boot_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", expected_boot_sha256)
    ):
        raise QualificationError("P345 qualification boot digest differs")
    if type(seen_nonces) is not set:
        raise QualificationError("P345 qualification nonce set differs")
    if writer is None:
        raise QualificationError("P345 qualification raw writer is absent")
    if (
        type(deadline) not in (int, float)
        or not math.isfinite(float(deadline))
        or deadline <= now
        or deadline - now > QUALIFICATION_TIMEOUT_SEC + 1.0
    ):
        raise QualificationError("P345 qualification deadline differs")
    if expected_boot_sha256 is None and seen_nonces:
        raise QualificationError("P345 initial boot binding requires an unused nonce set")


def qualify(
    observer: Any,
    descriptor: int,
    auth_key: bytes,
    expected_boot_sha256: str | None,
    seen_nonces: set[str],
    writer: Any,
    *,
    deadline: float,
) -> QualificationResult:
    """Run the five-session qualification on one caller-owned descriptor.

    The first session may establish the boot digest when ``expected_boot_sha256``
    is ``None`` and ``seen_nonces`` is empty.  Every later session is bound to
    that digest.  The raw writer remains owned by the caller and is never
    finalized here; partial exchange audits are attached to failures.
    """

    _validate_arguments(
        descriptor,
        auth_key,
        expected_boot_sha256,
        seen_nonces,
        writer,
        deadline,
    )
    sessions: list[dict[str, Any]] = []
    parsed_sessions: list[Any] = []
    bound_boot = expected_boot_sha256
    rx_offset = 0
    tx_offset = 0
    for step in QUALIFICATION_COMMANDS:
        capture_before = _writer_sizes(writer)
        cancel_armed_at: float | None = None
        audit: Any | None = None

        def cancel_requested() -> bool:
            nonlocal cancel_armed_at
            if step.ordinal != 4:
                return False
            if cancel_armed_at is None:
                cancel_armed_at = time.monotonic()
            return time.monotonic() - cancel_armed_at >= CANCEL_DELAY_SEC

        try:
            shell_result = shell_exchange.exchange(
                observer,
                descriptor,
                auth_key,
                step.command,
                bound_boot,
                seen_nonces,
                writer,
                deadline=deadline,
                cancel_requested=cancel_requested,
            )
            session = getattr(shell_result, "session", None)
            audit = getattr(session, "audit", None)
            _session_audit_checks(audit)
            if bound_boot is None:
                bound_boot = hashlib.sha256(audit.boot_id).hexdigest()
            elif hashlib.sha256(audit.boot_id).hexdigest() != bound_boot:
                raise QualificationError("P345 boot changed between sessions")
            capture_after = _writer_sizes(writer)
            rx = _audit_bytes(audit, "rx")
            tx = _audit_bytes(audit, "tx")
            row = _session_row(
                step,
                shell_result,
                rx_offset=rx_offset,
                tx_offset=tx_offset,
                capture_span=_capture_span(capture_before, capture_after),
            )
            sessions.append(row)
            parsed_sessions.append(shell_result)
            rx_offset += len(rx)
            tx_offset += len(tx)
        except Exception as exc:
            audit = getattr(exc, "audit", None) or audit
            partial = _failure_receipt(
                sessions,
                expected_boot_sha256=bound_boot,
                step=step,
                exc=exc,
                audit=audit,
            )
            raise QualificationError(
                f"P345 qualification stopped at {step.name}",
                partial_receipt=partial,
                failed_session=step.name,
                audit=audit,
                category=(
                    "transport"
                    if audit is not None
                    and not isinstance(exc, QualificationError)
                    else "semantic"
                ),
                sessions=tuple(parsed_sessions),
            ) from exc

    receipt = _base_receipt(
        sessions,
        expected_boot_sha256=bound_boot,
        proved=True,
    )
    validated = validate_qualification(receipt)
    return QualificationResult(validated, tuple(parsed_sessions))


def audit_binding() -> dict[str, Any]:
    """Return H0 qualification metadata without selecting a descriptor."""

    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": RUN_ID_HEX,
        "qualification_timeout_sec": QUALIFICATION_TIMEOUT_SEC,
        "session_count": SESSION_COUNT,
        "same_fd_session_count": SAME_FD_SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT,
        "cancel_delay_sec": CANCEL_DELAY_SEC,
        "commands": [
            {
                "ordinal": step.ordinal,
                "name": step.name,
                "command": identity(step.command),
                "expected_outcome": step.expected_outcome,
            }
            for step in QUALIFICATION_COMMANDS
        ],
        "same_descriptor": True,
        "no_endpoint_selection": True,
        "no_reconnect_or_retry": True,
        "raw_writer_caller_owned": True,
        "device_contact": False,
        "live_authorized": False,
        "f1_ready": False,
    }


__all__ = [
    "CANARY_COMMAND",
    "CANCEL_COMMAND",
    "CANCEL_DELAY_SEC",
    "CONTRACT_ID",
    "EXIT7_COMMAND",
    "GID",
    "PIPELINE_COMMAND",
    "QUALIFICATION_COMMANDS",
    "QUALIFICATION_TIMEOUT_SEC",
    "QualificationError",
    "QualificationResult",
    "QualificationStep",
    "RECONNECT_COUNT",
    "RUN_ID",
    "RUN_ID_HEX",
    "SCHEMA",
    "SESSION_COUNT",
    "SAME_FD_SESSION_COUNT",
    "TARGET",
    "TIMEOUT_COMMAND",
    "UID",
    "audit_binding",
    "identity",
    "parse_captured_session",
    "qualify",
    "validate_qualification",
    "validate_session_result",
]
