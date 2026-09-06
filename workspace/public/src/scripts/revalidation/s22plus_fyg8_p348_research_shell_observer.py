#!/usr/bin/env python3
"""P348 initial observer: five P347 sessions plus one clean tty reopen.

The inherited P347 exchange, frame parser and semantic checks remain the wire
implementation.  This successor adds exactly one host-owned close/idle/reopen
callback between the five same-descriptor sessions and a fixed sixth witness;
it does not select endpoints, retry an exchange, or grant live authority.
"""

from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import math
import time
from typing import Any, Mapping


TEMPLATE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p347_research_shell_observer.py"
)
TEMPLATE_IDENTITY = {
    "size": 3084,
    "sha256": "a3fd9c964f3a9d40892c73c65b162340f9373c755c772957d71b66d0fe1bac0a",
}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P348 source template identity differs")
_template = _template.replace(b"P347", b"P348").replace(b"p347", b"p348")
_template = _template.replace(
    b"s22plus_fyg8_p347_research_shell_runtime",
    b"s22plus_fyg8_p348_research_shell_runtime",
)
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p348", "exec"), globals())


# Retain the reviewed P347 cases and protocol vocabulary exactly.  Only the
# fresh P348 identity and sixth witness are successor inputs.
_P347_QUALIFICATION_COMMANDS = tuple(QUALIFICATION_COMMANDS)
_P347_VALIDATE_COMMAND_RESULTS = _validate_command_results
_P347_SESSION_ROW = _session_row
_P347_BASE_RECEIPT = _base_receipt
_P347_VALIDATE_QUALIFICATION = validate_qualification
_P347_FAILURE_RECEIPT = _failure_receipt

SCHEMA = "s22plus-fyg8-p348-research-shell-qualification-v1"
CONTRACT_ID = "s22plus-fyg8-p348-research-shell-qualification-observer-v1"
TARGET = runtime.TARGET
RUN_ID = runtime.P348_RUN_ID
RUN_ID_HEX = runtime.P348_RUN_ID_HEX
QUALIFICATION_TIMEOUT_SEC = 300.0
INITIAL_OBSERVATION = "p348_readonly_research_shell_qualification"
INITIAL_OBSERVATION_FIELD = "p348_readonly_research_shell"
INITIAL_SESSION_COUNT = 5
SESSION_COUNT = 6
SAME_FD_SESSION_COUNT = 5
RECONNECT_COUNT = 1
PHYSICAL_REOPEN_COUNT = 1
IDLE_SECONDS = 120
TOTAL_SESSIONS = 6
TOTAL_COMMANDS = 18
MAX_SESSIONS = SESSION_COUNT
MAX_RECONNECTS = RECONNECT_COUNT
MAX_INITIAL_SESSIONS = INITIAL_SESSION_COUNT
CANCEL_DELAY_SEC = 0.2

REOPEN_WITNESS_MARKER = b"P348-REOPEN-WITNESS\n"
REOPEN_WITNESS_COMMAND = b"printf 'P348-REOPEN-WITNESS\\n'"
REOPEN_STEP = QualificationStep(
    6, "clean-tty-reopen-witness", REOPEN_WITNESS_COMMAND, "ok"
)
QUALIFICATION_COMMANDS = _P347_QUALIFICATION_COMMANDS + (REOPEN_STEP,)

# The retained lease's first-use gate is a separate finite sequence from the
# six-session initial observation.  Caller-selected later commands remain
# unrestricted by this table after the capability roles have been proved.
CHECKED_SNAPSHOT_MARKER = b"P348-SNAPSHOT-CHECKED\n"
CHECKED_SNAPSHOT_COMMAND = (
    b"v=$(/bin/busybox cat /proc/version) || exit 74; "
    b"test -n \"$v\" || exit 75; "
    b"printf 'P348-SNAPSHOT-CHECKED\\n' | /bin/busybox tr a-z A-Z"
)
LATER_ACCEPTANCE_COMMANDS = {
    "checked-snapshot": {
        "command": CHECKED_SNAPSHOT_COMMAND,
        "outcome": "ok",
        "middle": {
            "output": CHECKED_SNAPSHOT_MARKER,
            "flags": 0,
            "exit_code": 0,
            "signal_number": 0,
        },
    },
    "known-nonzero": {
        "command": EXIT7_COMMAND,
        "outcome": "command-failed",
        "middle": {
            "output": b"",
            "flags": 0,
            "exit_code": 7,
            "signal_number": 0,
        },
    },
    "timeout": {
        "command": TIMEOUT_COMMAND,
        "outcome": "timeout",
        "middle": {
            "output": b"",
            "flags": 1,
            "exit_code": -1,
            "signal_number": 9,
            "duration_ms_min": 15000,
        },
    },
    "active-cancel": {
        "command": CANCEL_COMMAND,
        "outcome": "cancelled",
        "middle": {
            "output": CANCEL_MARKER,
            "flags": runtime.P345_CANCELLED_FLAG,
            "exit_code": -1,
            "signal_number": 9,
            "cancel_sent": True,
            "cancel_ack": runtime.P345_CANCEL_STATUS_CONSUMED,
        },
    },
    "post-cancel-success": {
        "command": PIPELINE_COMMAND,
        "outcome": "ok",
        "middle": {
            "output": PIPELINE_MARKER,
            "flags": 0,
            "exit_code": 0,
            "signal_number": 0,
        },
    },
}


def later_acceptance_binding() -> dict[str, Any]:
    """Return JSON-safe identities for the finite later-use acceptance table."""

    value: dict[str, Any] = {}
    for role, spec in LATER_ACCEPTANCE_COMMANDS.items():
        middle = spec["middle"]
        checked = {
            key: (identity(item) if isinstance(item, bytes) else item)
            for key, item in middle.items()
        }
        value[role] = {
            "command": identity(spec["command"]),
            "outcome": spec["outcome"],
            "middle": checked,
        }
    return value


def _validate_command_results(
    step: QualificationStep, session: Any, shell_result: Any
) -> dict[str, Any]:
    result = _P347_VALIDATE_COMMAND_RESULTS(step, session, shell_result)
    if step.ordinal == REOPEN_STEP.ordinal:
        middle = session.commands[1]
        if not (
            middle.flags == 0
            and middle.exit_code == 0
            and middle.term_signal == 0
            and middle.output == REOPEN_WITNESS_MARKER
        ):
            raise QualificationError("P348 clean tty reopen witness differs")
        result["semantic"] = {
            "reopen_witness": True,
            "marker_seen": REOPEN_WITNESS_MARKER in middle.output,
        }
    return result


def _session_row(
    step: QualificationStep,
    shell_result: Any,
    *,
    rx_offset: int,
    tx_offset: int,
    capture_span: Mapping[str, int] | None,
) -> dict[str, Any]:
    row = _P347_SESSION_ROW(
        step,
        shell_result,
        rx_offset=rx_offset,
        tx_offset=tx_offset,
        capture_span=capture_span,
    )
    row["descriptor_reused"] = step.ordinal <= INITIAL_SESSION_COUNT
    row["physical_reopen_index"] = 0 if step.ordinal <= INITIAL_SESSION_COUNT else 1
    return row


def _base_receipt(
    sessions: list[dict[str, Any]],
    *,
    expected_boot_sha256: str | None,
    proved: bool,
    failure: Mapping[str, Any] | None = None,
    reopen: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reopened = reopen is not None or len(sessions) >= SESSION_COUNT
    value: dict[str, Any] = {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": RUN_ID_HEX,
        "initial_observation": INITIAL_OBSERVATION,
        "initial_observation_field": INITIAL_OBSERVATION_FIELD,
        "session_count": len(sessions),
        "required_session_count": SESSION_COUNT,
        "same_fd_session_count": SAME_FD_SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT if reopened else 0,
        "same_descriptor": not reopened,
        "initial_five_same_tty_fd": len(sessions) >= INITIAL_SESSION_COUNT,
        "same_tty_fd": not reopened,
        "physical_reopen_count": PHYSICAL_REOPEN_COUNT if reopened else 0,
        "total_command_count": len(sessions) * len(runtime.DEFAULT_COMMANDS),
        "idle_seconds": IDLE_SECONDS if reopened else 0,
        "idle_duration_ms": (
            int(reopen["idle_duration_ms"])
            if reopen is not None and type(reopen.get("idle_duration_ms")) is int
            else 0
        ),
        "expected_boot_sha256": expected_boot_sha256,
        "sessions": list(sessions),
        "proved": proved,
        "authority_granted_by_observer": False,
    }
    if reopen is not None:
        value["reopen"] = dict(reopen)
    if failure is not None:
        value["failure"] = dict(failure)
    return value


def _failure_receipt(
    sessions: list[dict[str, Any]],
    *,
    expected_boot_sha256: str | None,
    step: QualificationStep,
    exc: BaseException,
    audit: Any | None,
    reopen: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    value = _P347_FAILURE_RECEIPT(
        sessions,
        expected_boot_sha256=expected_boot_sha256,
        step=step,
        exc=exc,
        audit=audit,
    )
    if reopen is not None:
        value["reopen"] = dict(reopen)
        value["reconnect_count"] = RECONNECT_COUNT
        value["physical_reopen_count"] = PHYSICAL_REOPEN_COUNT
        value["same_descriptor"] = False
        value["same_tty_fd"] = False
    return value


def _validate_reopen(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise QualificationError("P348 reopen metadata is absent")
    duration = value.get("idle_duration_ms")
    if (
        type(duration) is not int
        or duration < IDLE_SECONDS * 1000
        or type(value.get("physical_reopen_count")) is not int
        or value.get("physical_reopen_count") != PHYSICAL_REOPEN_COUNT
        or value.get("initial_five_same_tty_fd") is not True
        or value.get("same_tty_fd") is not False
        or value.get("callback_invoked") is not True
    ):
        raise QualificationError("P348 idle/reopen proof differs")
    return dict(value)


def validate_qualification(value: Mapping[str, Any]) -> dict[str, Any]:
    """Revalidate all P347 rows plus P348 descriptor/reopen geometry."""

    if not isinstance(value, Mapping):
        raise QualificationError("P348 qualification receipt is not an object")
    # The P347 JSON validator checks every command, digest and boot binding but
    # encodes its five-session descriptor geometry.  Temporarily project only
    # those two geometry fields for that unchanged core check, then validate
    # P348's explicit six-session geometry below without mutating the caller.
    core = copy.deepcopy(dict(value))
    core["same_descriptor"] = True
    for session in core.get("sessions", ()):
        if isinstance(session, dict):
            session["descriptor_reused"] = True
    _P347_VALIDATE_QUALIFICATION(core)

    required = {
        "initial_observation",
        "initial_observation_field",
        "initial_five_same_tty_fd",
        "same_tty_fd",
        "physical_reopen_count",
        "total_command_count",
        "idle_seconds",
        "reopen",
    }
    if not required <= set(value):
        raise QualificationError("P348 qualification geometry fields differ")
    if (
        value.get("initial_observation") != INITIAL_OBSERVATION
        or value.get("initial_observation_field") != INITIAL_OBSERVATION_FIELD
        or value.get("same_descriptor") is not False
        or value.get("initial_five_same_tty_fd") is not True
        or value.get("same_tty_fd") is not False
        or type(value.get("physical_reopen_count")) is not int
        or value.get("physical_reopen_count") != PHYSICAL_REOPEN_COUNT
        or type(value.get("reconnect_count")) is not int
        or value.get("reconnect_count") != RECONNECT_COUNT
        or type(value.get("total_command_count")) is not int
        or value.get("total_command_count") != TOTAL_COMMANDS
        or type(value.get("idle_seconds")) is not int
        or value.get("idle_seconds") != IDLE_SECONDS
        or type(value.get("idle_duration_ms")) is not int
        or value.get("proved") is not True
    ):
        raise QualificationError("P348 qualification identity differs")
    reopen = _validate_reopen(value["reopen"])
    if value["idle_duration_ms"] != reopen["idle_duration_ms"]:
        raise QualificationError("P348 top-level idle duration differs")
    sessions = value.get("sessions")
    if not isinstance(sessions, list) or len(sessions) != SESSION_COUNT:
        raise QualificationError("P348 qualification session count differs")
    for index, session in enumerate(sessions):
        if not isinstance(session, Mapping):
            raise QualificationError("P348 qualification session row differs")
        expected_reused = index < INITIAL_SESSION_COUNT
        expected_reopen = 0 if expected_reused else PHYSICAL_REOPEN_COUNT
        if (
            session.get("descriptor_reused") is not expected_reused
            or type(session.get("physical_reopen_index")) is not int
            or session.get("physical_reopen_index") != expected_reopen
        ):
            raise QualificationError("P348 descriptor/reopen placement differs")
    final = sessions[-1]
    semantic = final.get("semantic")
    middle = final.get("commands", [None, {}, None])[1]
    if (
        not isinstance(semantic, Mapping)
        or semantic.get("reopen_witness") is not True
        or semantic.get("marker_seen") is not True
        or not isinstance(middle, Mapping)
        or middle.get("output") != identity(REOPEN_WITNESS_MARKER)
        or middle.get("flags") != 0
        or middle.get("exit_code") != 0
        or middle.get("term_signal") != 0
    ):
        raise QualificationError("P348 reopen witness receipt differs")
    return dict(value)


def _failure_error(
    sessions: list[dict[str, Any]],
    parsed_sessions: list[Any],
    *,
    bound_boot: str | None,
    step: QualificationStep,
    exc: BaseException,
    audit: Any | None,
    reopen: Mapping[str, Any] | None = None,
) -> QualificationError:
    partial = _failure_receipt(
        sessions,
        expected_boot_sha256=bound_boot,
        step=step,
        exc=exc,
        audit=audit,
        reopen=reopen,
    )
    return QualificationError(
        f"P348 qualification stopped at {step.name}",
        partial_receipt=partial,
        failed_session=step.name,
        audit=audit,
        category=(
            "transport"
            if audit is not None and not isinstance(exc, QualificationError)
            else "semantic"
        ),
        sessions=tuple(parsed_sessions),
    )


def qualify(
    observer: Any,
    descriptor: int,
    auth_key: bytes,
    expected_boot_sha256: str | None,
    seen_nonces: set[str],
    writer: Any,
    *,
    deadline: float,
    reopen_after_idle: Any,
) -> QualificationResult:
    """Run five P347 sessions, one clean 120-second reopen, then one witness.

    ``reopen_after_idle`` is caller-owned: it closes the settled descriptor,
    waits for and proves the fixed idle interval, opens the exact endpoint once,
    and returns the new descriptor.  This function invokes it once and never
    retries or selects a transport endpoint.
    """

    _validate_arguments(
        descriptor,
        auth_key,
        expected_boot_sha256,
        seen_nonces,
        writer,
        deadline,
    )
    if not callable(reopen_after_idle):
        raise QualificationError("P348 reopen callback is absent")

    sessions: list[dict[str, Any]] = []
    parsed_sessions: list[Any] = []
    bound_boot = expected_boot_sha256
    rx_offset = 0
    tx_offset = 0

    def run_step(step: QualificationStep, active_descriptor: int) -> None:
        nonlocal bound_boot, rx_offset, tx_offset
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
                active_descriptor,
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
            boot_sha = hashlib.sha256(audit.boot_id).hexdigest()
            if bound_boot is None:
                bound_boot = boot_sha
            elif boot_sha != bound_boot:
                raise QualificationError("P348 boot changed between sessions")
            capture_after = _writer_sizes(writer)
            rx = _audit_bytes(audit, "rx")
            tx = _audit_bytes(audit, "tx")
            sessions.append(
                _session_row(
                    step,
                    shell_result,
                    rx_offset=rx_offset,
                    tx_offset=tx_offset,
                    capture_span=_capture_span(capture_before, capture_after),
                )
            )
            parsed_sessions.append(shell_result)
            rx_offset += len(rx)
            tx_offset += len(tx)
        except Exception as exc:
            audit = getattr(exc, "audit", None) or audit
            raise _failure_error(
                sessions,
                parsed_sessions,
                bound_boot=bound_boot,
                step=step,
                exc=exc,
                audit=audit,
                reopen=reopen_metadata,
            ) from exc

    reopen_metadata: dict[str, Any] | None = None
    for step in _P347_QUALIFICATION_COMMANDS:
        run_step(step, descriptor)

    if deadline - time.monotonic() < IDLE_SECONDS:
        error = QualificationError("P348 deadline cannot cover idle reopen")
        raise _failure_error(
            sessions,
            parsed_sessions,
            bound_boot=bound_boot,
            step=REOPEN_STEP,
            exc=error,
            audit=None,
        ) from error

    idle_started = time.monotonic()
    try:
        reopened_descriptor = reopen_after_idle()
    except Exception as exc:
        raise _failure_error(
            sessions,
            parsed_sessions,
            bound_boot=bound_boot,
            step=REOPEN_STEP,
            exc=exc,
            audit=getattr(exc, "audit", None),
        ) from exc
    idle_duration_ms = int(round((time.monotonic() - idle_started) * 1000.0))
    reopen_metadata = {
        "idle_seconds": IDLE_SECONDS,
        "idle_duration_ms": idle_duration_ms,
        "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
        "initial_five_same_tty_fd": True,
        "same_tty_fd": False,
        "callback_invoked": True,
    }
    if type(reopened_descriptor) is not int or reopened_descriptor < 0:
        error = QualificationError("P348 reopen callback returned an invalid descriptor")
        raise _failure_error(
            sessions,
            parsed_sessions,
            bound_boot=bound_boot,
            step=REOPEN_STEP,
            exc=error,
            audit=None,
            reopen=reopen_metadata,
        ) from error
    if idle_duration_ms < IDLE_SECONDS * 1000:
        error = QualificationError("P348 idle reopen duration is shorter than 120 seconds")
        raise _failure_error(
            sessions,
            parsed_sessions,
            bound_boot=bound_boot,
            step=REOPEN_STEP,
            exc=error,
            audit=None,
            reopen=reopen_metadata,
        ) from error
    if time.monotonic() >= deadline:
        error = QualificationError("P348 deadline expired after idle reopen")
        raise _failure_error(
            sessions,
            parsed_sessions,
            bound_boot=bound_boot,
            step=REOPEN_STEP,
            exc=error,
            audit=None,
            reopen=reopen_metadata,
        ) from error

    run_step(REOPEN_STEP, reopened_descriptor)
    receipt = _base_receipt(
        sessions,
        expected_boot_sha256=bound_boot,
        proved=True,
        reopen=reopen_metadata,
    )
    validated = validate_qualification(receipt)
    return QualificationResult(validated, tuple(parsed_sessions))


def audit_binding() -> dict[str, Any]:
    """Return P348 H0 observer metadata without selecting a descriptor."""

    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": RUN_ID_HEX,
        "initial_observation": INITIAL_OBSERVATION,
        "initial_observation_field": INITIAL_OBSERVATION_FIELD,
        "qualification_timeout_sec": QUALIFICATION_TIMEOUT_SEC,
        "session_count": SESSION_COUNT,
        "required_session_count": SESSION_COUNT,
        "same_fd_session_count": SAME_FD_SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT,
        "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
        "idle_seconds": IDLE_SECONDS,
        "total_session_count": TOTAL_SESSIONS,
        "total_command_count": TOTAL_COMMANDS,
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
        "later_acceptance_commands": later_acceptance_binding(),
        "same_descriptor": False,
        "initial_five_same_tty_fd": True,
        "same_tty_fd": False,
        "reopen_after_idle_callback": True,
        "no_endpoint_selection": True,
        "no_retry": True,
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
    "IDLE_SECONDS",
    "INITIAL_OBSERVATION",
    "INITIAL_OBSERVATION_FIELD",
    "INITIAL_SESSION_COUNT",
    "MAX_INITIAL_SESSIONS",
    "MAX_RECONNECTS",
    "MAX_SESSIONS",
    "PHYSICAL_REOPEN_COUNT",
    "PIPELINE_COMMAND",
    "QUALIFICATION_COMMANDS",
    "QUALIFICATION_TIMEOUT_SEC",
    "QualificationError",
    "QualificationResult",
    "QualificationStep",
    "RECONNECT_COUNT",
    "REOPEN_STEP",
    "REOPEN_WITNESS_COMMAND",
    "REOPEN_WITNESS_MARKER",
    "CHECKED_SNAPSHOT_COMMAND",
    "CHECKED_SNAPSHOT_MARKER",
    "LATER_ACCEPTANCE_COMMANDS",
    "RUN_ID",
    "RUN_ID_HEX",
    "SCHEMA",
    "SESSION_COUNT",
    "SAME_FD_SESSION_COUNT",
    "TARGET",
    "TIMEOUT_COMMAND",
    "TOTAL_COMMANDS",
    "TOTAL_SESSIONS",
    "UID",
    "audit_binding",
    "identity",
    "later_acceptance_binding",
    "parse_captured_session",
    "qualify",
    "validate_qualification",
    "validate_session_result",
]
