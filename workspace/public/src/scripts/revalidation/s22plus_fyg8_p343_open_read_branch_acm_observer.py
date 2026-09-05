#!/usr/bin/env python3
"""Host-only P3.43 authenticated ACM observer binding.

The P3.42 parser is loaded into a private namespace and rebound to the fresh
P3.43 runtime.  Its host-first OPEN ordering, framing, HMAC, and retained
four-session/120-second idle proof geometry remain unchanged.  The parser's
default command tuple is still the initial ``kernel`` action; the device-side
named catalog is represented as metadata and is not a caller-selected shell.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_p342_open_read_branch_acm_observer as predecessor
import s22plus_fyg8_p343_open_read_branch_runtime as runtime


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 13_864,
    "sha256": "8f94477f694816edd536334afd1ef08e80a865b0af25a2a1f010bc3788dba19e",
}
P342_PREDECESSOR_RUN_ID_HEX = runtime.P342_PREDECESSOR_RUN_ID_HEX
P342_PREDECESSOR_RUN_ID = runtime.P342_PREDECESSOR_RUN_ID
P343_RUN_ID_HEX = runtime.P343_RUN_ID_HEX
P343_RUN_ID = runtime.P343_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
CATALOG = runtime.CATALOG
CATALOG_ACTIONS = tuple(CATALOG)

MAX_INITIAL_SESSIONS = predecessor.MAX_INITIAL_SESSIONS
MAX_SESSIONS = predecessor.MAX_SESSIONS
MAX_RECONNECTS = predecessor.MAX_RECONNECTS
MAX_PHYSICAL_REOPENS = predecessor.MAX_PHYSICAL_REOPENS
PHYSICAL_REOPEN_COUNT = predecessor.PHYSICAL_REOPEN_COUNT
MAX_PREAMBLE_PAIRS = predecessor.MAX_PREAMBLE_PAIRS
MAX_RESYNC_BYTES = predecessor.MAX_RESYNC_BYTES
SESSION_TIMEOUT_SEC = predecessor.SESSION_TIMEOUT_SEC
HEADER = predecessor.HEADER
DIAGNOSTIC = predecessor.DIAGNOSTIC
SCHEMA = "s22plus-fyg8-p343-readonly-exploration-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p343-readonly-exploration-acm-observer-v1"
IDLE_SECONDS = predecessor.IDLE_SECONDS
SAME_FD_SESSIONS = predecessor.SAME_FD_SESSIONS
TOTAL_SESSIONS = predecessor.TOTAL_SESSIONS
TOTAL_COMMANDS = TOTAL_SESSIONS * len(DEFAULT_COMMANDS)


class P343ObserverBindingError(ValueError):
    """The exact P3.42 parser or P3.43 runtime binding differs."""


AuthObserverError = P343ObserverBindingError


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


try:
    _payload = SOURCE.read_bytes()
except OSError as exc:
    raise P343ObserverBindingError("P3.42 observer source is unavailable") from exc
if identity(_payload) != SOURCE_IDENTITY:
    raise P343ObserverBindingError("P3.42 observer source identity differs")
if predecessor.P342_RUN_ID_HEX != P342_PREDECESSOR_RUN_ID_HEX:
    raise P343ObserverBindingError("P3.42 observer predecessor binding differs")

_parser = types.ModuleType("s22plus_fyg8_p342_parser_bound_for_p343")
_parser.__file__ = str(SOURCE)
try:
    exec(compile(_payload, str(SOURCE), "exec", dont_inherit=True), _parser.__dict__)  # noqa: S102
except Exception as exc:
    raise P343ObserverBindingError("P3.42 observer parser failed to load") from exc

# Rebind only the private parser and every nested predecessor parser.  No
# imported P342 observer or parser globals are mutated.
_parser.runtime = runtime
for _name in ("P341_RUN_ID_HEX", "P342_RUN_ID_HEX"):
    if _name in _parser.__dict__:
        _parser.__dict__[_name] = P343_RUN_ID_HEX
for _name in ("P341_RUN_ID", "P342_RUN_ID"):
    if _name in _parser.__dict__:
        _parser.__dict__[_name] = P343_RUN_ID
_parser.DEVICE_BANNER = DEVICE_BANNER
_parser.DEFAULT_COMMANDS = DEFAULT_COMMANDS
_parser.SCHEMA = SCHEMA
_parser.CONTRACT_ID = CONTRACT_ID
_rebind = getattr(_parser, "_parser", None)
while isinstance(_rebind, types.ModuleType):
    _rebind.runtime = runtime
    for _prefix in ("P339", "P340", "P341", "P342"):
        if any(
            key in _rebind.__dict__
            for key in (f"{_prefix}_RUN_ID_HEX", f"{_prefix}_RUN_ID")
        ):
            _rebind.__dict__[f"{_prefix}_RUN_ID_HEX"] = P343_RUN_ID_HEX
            _rebind.__dict__[f"{_prefix}_RUN_ID"] = P343_RUN_ID
    _rebind.DEVICE_BANNER = DEVICE_BANNER
    _rebind.DEFAULT_COMMANDS = DEFAULT_COMMANDS
    _rebind.SCHEMA = SCHEMA
    _rebind.CONTRACT_ID = CONTRACT_ID
    _rebind = getattr(_rebind, "_parser", None)

P343ParserError = getattr(
    _parser, "P342ObserverBindingError", P343ObserverBindingError
)


def decode_frame(payload: bytes) -> Any:
    try:
        return _parser.decode_frame(payload)
    except Exception as exc:
        raise P343ObserverBindingError(str(exc)) from exc


def parse_open_read_branch_frame(payload: bytes) -> dict[str, Any]:
    try:
        value = dict(_parser.parse_open_read_branch_frame(payload))
    except Exception as exc:
        raise P343ObserverBindingError(str(exc)) from exc
    value.update({"run_id_hex": P343_RUN_ID_HEX, "idle_reuse": False})
    return value


def parse_open_read_diagnostic_frame(payload: bytes) -> dict[str, Any]:
    return parse_open_read_branch_frame(payload)


def parse_retained_open_read_branch(payload: bytes) -> dict[str, Any]:
    """Parse retained diagnostics without manufacturing a missing banner."""

    if type(payload) is not bytes or not payload.startswith(DEVICE_BANNER):
        raise P343ObserverBindingError(
            "P343 retained stream has no exact leading device banner"
        )
    try:
        value = dict(_parser.parse_retained_open_read_branch(payload))
    except Exception as exc:
        raise P343ObserverBindingError(str(exc)) from exc
    value.update(
        {
            "run_id_hex": P343_RUN_ID_HEX,
            "banner_seen": True,
            "idle_reuse": False,
            "proof_class": "NO_PROOF_OBSERVER",
            "candidate_success": False,
            "causal_result_allowed": False,
        }
    )
    return value


def parse_retained_open_read_diagnostic(payload: bytes) -> dict[str, Any]:
    return parse_retained_open_read_branch(payload)


def _command_identity(command: bytes) -> dict[str, Any]:
    return {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}


def validate_four_session_proof(value: Any) -> dict[str, Any]:
    """Validate the inherited three-same-FD/one-reopen proof shape."""

    if type(value) is not dict:
        raise P343ObserverBindingError("P343 proof is not an object")
    for name, expected in (
        ("schema", SCHEMA),
        ("contract_id", CONTRACT_ID),
        ("run_id_hex", P343_RUN_ID_HEX),
        ("fixed_command_count", len(DEFAULT_COMMANDS)),
        ("same_fd_session_count", SAME_FD_SESSIONS),
        ("idle_seconds", IDLE_SECONDS),
        ("total_session_count", TOTAL_SESSIONS),
        ("total_command_count", TOTAL_COMMANDS),
    ):
        if name in value:
            if name.endswith("count") or name.endswith("seconds"):
                if type(value[name]) is not int:
                    raise P343ObserverBindingError(f"P343 proof {name} type differs")
            if value[name] != expected:
                raise P343ObserverBindingError(f"P343 proof {name} differs")
    expected_commands = [_command_identity(command) for command in DEFAULT_COMMANDS]
    if "fixed_commands" in value:
        fixed = value["fixed_commands"]
        if type(fixed) is not list or len(fixed) != len(expected_commands):
            raise P343ObserverBindingError("P343 fixed command identities differ")
        for actual, expected in zip(fixed, expected_commands):
            if (
                type(actual) is not dict
                or set(actual) != set(expected)
                or any(
                    type(actual[key]) is not type(expected[key])
                    or actual[key] != expected[key]
                    for key in actual
                )
            ):
                raise P343ObserverBindingError("P343 fixed command identities differ")
    sessions = value.get("sessions")
    if type(sessions) is not list or len(sessions) != TOTAL_SESSIONS:
        raise P343ObserverBindingError("P343 proof session count differs")
    descriptors: list[Any] = []
    for index, session in enumerate(sessions):
        if type(session) is not dict:
            raise P343ObserverBindingError(f"P343 session {index} is not an object")
        expected_reopen = 0 if index < SAME_FD_SESSIONS else 1
        if (
            type(session.get("physical_reopen_index")) is not int
            or session["physical_reopen_index"] != expected_reopen
        ):
            raise P343ObserverBindingError(f"P343 session {index} reopen binding differs")
        if "descriptor" in session:
            descriptors.append(session["descriptor"])
        commands = session.get("commands")
        if type(commands) is not list or len(commands) != len(expected_commands):
            raise P343ObserverBindingError(f"P343 session {index} command count differs")
        for command, expected in zip(commands, expected_commands):
            if (
                type(command) is not dict
                or type(command.get("command_sha256")) is not str
                or command.get("command_sha256") != expected["sha256"]
            ):
                raise P343ObserverBindingError(
                    f"P343 session {index} command identity differs"
                )
    if descriptors:
        if len(descriptors) != TOTAL_SESSIONS:
            raise P343ObserverBindingError("P343 descriptor projection is partial")
        if any(item != descriptors[0] for item in descriptors[:SAME_FD_SESSIONS]):
            raise P343ObserverBindingError("P343 same-FD descriptor binding differs")
    for name, expected in (
        ("session_count", TOTAL_SESSIONS),
        ("successful_sessions", TOTAL_SESSIONS),
        ("session_cap", TOTAL_SESSIONS),
        ("reconnect_count", MAX_RECONNECTS),
        ("reconnect_cap", MAX_RECONNECTS),
        ("physical_reopen_count", PHYSICAL_REOPEN_COUNT),
        ("command_count", TOTAL_COMMANDS),
    ):
        if name in value:
            if type(value[name]) is not int:
                raise P343ObserverBindingError(f"P343 proof {name} type differs")
            if value[name] != expected:
                raise P343ObserverBindingError(f"P343 proof {name} differs")
    return value


validate_proof_value = validate_four_session_proof


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise P343ObserverBindingError("P3.42 observer source changed")
    if predecessor.P342_RUN_ID_HEX != P342_PREDECESSOR_RUN_ID_HEX:
        raise P343ObserverBindingError("P3.42 observer predecessor changed")
    try:
        value = dict(_parser.audit_binding())
    except Exception as exc:
        raise P343ObserverBindingError(str(exc)) from exc
    value.update(
        {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "predecessor_source": dict(SOURCE_IDENTITY),
            "predecessor_run_id": P342_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P342_PREDECESSOR_RUN_ID_HEX,
            "run_id_hex": P343_RUN_ID_HEX,
            "max_initial_sessions": MAX_INITIAL_SESSIONS,
            "max_sessions": MAX_SESSIONS,
            "max_reconnects": MAX_RECONNECTS,
            "max_physical_reopens": MAX_PHYSICAL_REOPENS,
            "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
            "same_fd_sessions": SAME_FD_SESSIONS,
            "idle_seconds": IDLE_SECONDS,
            "total_sessions": TOTAL_SESSIONS,
            "total_commands": TOTAL_COMMANDS,
            "host_first_open": True,
            "host_open_before_banner": True,
            "device_banner_after_open": True,
            "stage_zero_after_banner": True,
            "open_parsed_after_stage_zero": True,
            "no_unsolicited_device_tx": True,
            "silent_no_peer_no_proof": True,
            "consumed_partial_open_no_replay": True,
            "no_banner_is_raw_no_proof": True,
            "successful_wire_exchange_unchanged": False,
            "wire_frames_unchanged": True,
            "authentication_unchanged": True,
            "catalog_unchanged": False,
            "catalog_allowlist_expanded": True,
            "catalog_allowlist_actions": CATALOG_ACTIONS,
            "middle_command_allowlist": True,
            "middle_command_allowlist_count": len(CATALOG_ACTIONS),
            "default_command_tuple_unchanged": True,
            "default_runtime_behavior_unchanged": True,
            "runtime_behavior_unchanged": False,
            "idle_listener_unchanged": True,
            "caller_selected_command": False,
            "selected_command_integration": False,
            "initial_proof_default_action": "kernel",
            "device_contact": False,
            "live_authorized": False,
        }
    )
    return value


install_initial_capture = getattr(_parser, "install_initial_capture", None)


def __getattr__(name: str) -> Any:
    return getattr(_parser, name)


__all__ = sorted(
    {
        "AuthObserverError",
        "CATALOG",
        "CATALOG_ACTIONS",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DIAGNOSTIC",
        "DEVICE_BANNER",
        "HEADER",
        "IDLE_SECONDS",
        "MAX_INITIAL_SESSIONS",
        "MAX_PHYSICAL_REOPENS",
        "MAX_PREAMBLE_PAIRS",
        "MAX_RECONNECTS",
        "MAX_RESYNC_BYTES",
        "MAX_SESSIONS",
        "P342_PREDECESSOR_RUN_ID",
        "P342_PREDECESSOR_RUN_ID_HEX",
        "P343ParserError",
        "P343ObserverBindingError",
        "P343_RUN_ID",
        "P343_RUN_ID_HEX",
        "PHYSICAL_REOPEN_COUNT",
        "SAME_FD_SESSIONS",
        "SCHEMA",
        "SESSION_TIMEOUT_SEC",
        "SOURCE",
        "SOURCE_IDENTITY",
        "TOTAL_COMMANDS",
        "TOTAL_SESSIONS",
        "audit_binding",
        "decode_frame",
        "identity",
        "install_initial_capture",
        "parse_open_read_branch_frame",
        "parse_open_read_diagnostic_frame",
        "parse_retained_open_read_branch",
        "parse_retained_open_read_diagnostic",
        "validate_four_session_proof",
        "validate_proof_value",
    }
)
