#!/usr/bin/env python3
"""Host-only P3.42 observer/parser binding.

The P3.41 parser is loaded into a private module namespace and rebound to the
fresh P3.42 runtime identity.  Its framing, authentication, diagnostics and
host-first ordering are unchanged.  This public wrapper records the strict
P3.42 four-session geometry used by the dormant idle-reuse qualification;
actual listener installation remains owned by the live integration layer.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_p341_open_read_branch_acm_observer as predecessor
import s22plus_fyg8_p342_open_read_branch_runtime as runtime


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 8_664,
    "sha256": "dc76437606c3cf84585a95315b8ec8e569c3868adf7ba82d3ce219f48f52b372",
}
P341_PREDECESSOR_RUN_ID_HEX = runtime.P341_PREDECESSOR_RUN_ID_HEX
P341_PREDECESSOR_RUN_ID = runtime.P341_PREDECESSOR_RUN_ID
P342_RUN_ID_HEX = runtime.P342_RUN_ID_HEX
P342_RUN_ID = runtime.P342_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)

MAX_INITIAL_SESSIONS = 3
MAX_SESSIONS = 4
MAX_RECONNECTS = 1
MAX_PHYSICAL_REOPENS = 1
PHYSICAL_REOPEN_COUNT = 1
MAX_PREAMBLE_PAIRS = predecessor.MAX_PREAMBLE_PAIRS
MAX_RESYNC_BYTES = predecessor.MAX_RESYNC_BYTES
SESSION_TIMEOUT_SEC = predecessor.SESSION_TIMEOUT_SEC
HEADER = predecessor.HEADER
DIAGNOSTIC = predecessor.DIAGNOSTIC
SCHEMA = "s22plus-fyg8-p342-idle-reuse-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p342-idle-reuse-acm-observer-v1"
IDLE_SECONDS = 120
SAME_FD_SESSIONS = 3
TOTAL_SESSIONS = 4
TOTAL_COMMANDS = TOTAL_SESSIONS * len(DEFAULT_COMMANDS)


class P342ObserverBindingError(ValueError):
    """The exact P3.41 parser or P3.42 runtime binding differs."""


AuthObserverError = P342ObserverBindingError


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


try:
    _payload = SOURCE.read_bytes()
except OSError as exc:
    raise P342ObserverBindingError("P3.41 observer source is unavailable") from exc
if identity(_payload) != SOURCE_IDENTITY:
    raise P342ObserverBindingError("P3.41 observer source identity differs")
if predecessor.P341_RUN_ID_HEX != P341_PREDECESSOR_RUN_ID_HEX:
    raise P342ObserverBindingError("P3.41 observer predecessor binding differs")

_parser = types.ModuleType("s22plus_fyg8_p341_parser_bound_for_p342")
_parser.__file__ = str(SOURCE)
try:
    exec(compile(_payload, str(SOURCE), "exec", dont_inherit=True), _parser.__dict__)  # noqa: S102
except Exception as exc:
    raise P342ObserverBindingError("P3.41 observer parser failed to load") from exc

# Rebind only the privately loaded parser.  No shared P341 module is mutated.
_parser.runtime = runtime
_parser.P341_RUN_ID_HEX = P342_RUN_ID_HEX
_parser.P341_RUN_ID = P342_RUN_ID
_parser.DEVICE_BANNER = DEVICE_BANNER
_parser.DEFAULT_COMMANDS = DEFAULT_COMMANDS
_parser.SCHEMA = SCHEMA
_parser.CONTRACT_ID = CONTRACT_ID
_nested_parser = getattr(_parser, "_parser", None)
_rebind = _nested_parser
while isinstance(_rebind, types.ModuleType):
    _rebind.runtime = runtime
    for _prefix in ("P339", "P340", "P341"):
        if any(
            key in _rebind.__dict__
            for key in (f"{_prefix}_RUN_ID_HEX", f"{_prefix}_RUN_ID")
        ):
            _rebind.__dict__[f"{_prefix}_RUN_ID_HEX"] = P342_RUN_ID_HEX
            _rebind.__dict__[f"{_prefix}_RUN_ID"] = P342_RUN_ID
    _rebind.DEVICE_BANNER = DEVICE_BANNER
    _rebind.DEFAULT_COMMANDS = DEFAULT_COMMANDS
    _rebind.SCHEMA = SCHEMA
    _rebind.CONTRACT_ID = CONTRACT_ID
    _rebind = getattr(_rebind, "_parser", None)


P342ParserError = getattr(_parser, "P341ObserverBindingError", P342ObserverBindingError)


def decode_frame(payload: bytes) -> Any:
    try:
        return _parser.decode_frame(payload)
    except Exception as exc:
        raise P342ObserverBindingError(str(exc)) from exc


def parse_open_read_branch_frame(payload: bytes) -> dict[str, Any]:
    try:
        value = dict(_parser.parse_open_read_branch_frame(payload))
    except Exception as exc:
        raise P342ObserverBindingError(str(exc)) from exc
    value.update({"run_id_hex": P342_RUN_ID_HEX, "idle_reuse": False})
    return value


def parse_open_read_diagnostic_frame(payload: bytes) -> dict[str, Any]:
    return parse_open_read_branch_frame(payload)


def parse_retained_open_read_branch(payload: bytes) -> dict[str, Any]:
    """Parse retained diagnostics without manufacturing a missing banner."""

    if type(payload) is not bytes or not payload.startswith(DEVICE_BANNER):
        raise P342ObserverBindingError(
            "P342 retained stream has no exact leading device banner"
        )
    try:
        value = dict(_parser.parse_retained_open_read_branch(payload))
    except Exception as exc:
        raise P342ObserverBindingError(str(exc)) from exc
    value.update(
        {
            "run_id_hex": P342_RUN_ID_HEX,
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


def _strict_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return set(actual) == set(expected) and all(
            _strict_equal(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            _strict_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def validate_four_session_proof(value: Any) -> dict[str, Any]:
    """Strictly validate the P3.42 three-same-FD/one-reopen proof shape.

    The proof producer is installed by the private H0 idle-reuse helper.  This
    validator is intentionally serialization-only: it does not infer timing,
    causality, device health or candidate success from the session list.
    """

    if type(value) is not dict:
        raise P342ObserverBindingError("P342 proof is not an object")
    for name, expected in (
        ("schema", SCHEMA),
        ("contract_id", CONTRACT_ID),
        ("run_id_hex", P342_RUN_ID_HEX),
        ("fixed_command_count", len(DEFAULT_COMMANDS)),
        ("same_fd_session_count", SAME_FD_SESSIONS),
        ("idle_seconds", IDLE_SECONDS),
        ("total_session_count", TOTAL_SESSIONS),
        ("total_command_count", TOTAL_COMMANDS),
    ):
        if name in value:
            if name.endswith("count") or name.endswith("seconds"):
                if type(value[name]) is not int:
                    raise P342ObserverBindingError(f"P342 proof {name} type differs")
            if value[name] != expected:
                raise P342ObserverBindingError(f"P342 proof {name} differs")
    if "fixed_commands" in value:
        expected_fixed = [_command_identity(command) for command in DEFAULT_COMMANDS]
        if type(value["fixed_commands"]) is not list or len(value["fixed_commands"]) != len(expected_fixed):
            raise P342ObserverBindingError("P342 fixed command identities differ")
        if any(
            type(actual) is not type(expected)
            or set(actual) != set(expected)
            or any(actual[key] != expected[key] or type(actual[key]) is not type(expected[key]) for key in actual)
            for actual, expected in zip(value["fixed_commands"], expected_fixed)
        ):
            raise P342ObserverBindingError("P342 fixed command identities differ")
    sessions = value.get("sessions")
    if type(sessions) is not list or len(sessions) != TOTAL_SESSIONS:
        raise P342ObserverBindingError("P342 proof session count differs")
    expected_commands = [_command_identity(command) for command in DEFAULT_COMMANDS]
    descriptors: list[Any] = []
    for index, session in enumerate(sessions):
        if type(session) is not dict:
            raise P342ObserverBindingError(f"P342 session {index} is not an object")
        expected_reopen = 0 if index < SAME_FD_SESSIONS else 1
        if (
            type(session.get("physical_reopen_index")) is not int
            or session["physical_reopen_index"] != expected_reopen
        ):
            raise P342ObserverBindingError(f"P342 session {index} reopen binding differs")
        if "descriptor" in session:
            descriptors.append(session["descriptor"])
        commands = session.get("commands")
        if type(commands) is not list or len(commands) != len(expected_commands):
            raise P342ObserverBindingError(f"P342 session {index} command count differs")
        for command, expected in zip(commands, expected_commands):
            if (
                type(command) is not dict
                or type(command.get("command_sha256")) is not str
                or command.get("command_sha256") != expected["sha256"]
            ):
                raise P342ObserverBindingError(
                    f"P342 session {index} command identity differs"
                )
    if descriptors:
        if len(descriptors) != TOTAL_SESSIONS:
            raise P342ObserverBindingError("P342 descriptor projection is partial")
        if any(item != descriptors[0] for item in descriptors[:SAME_FD_SESSIONS]):
            raise P342ObserverBindingError("P342 same-FD descriptor binding differs")
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
                raise P342ObserverBindingError(f"P342 proof {name} type differs")
            if value[name] != expected:
                raise P342ObserverBindingError(f"P342 proof {name} differs")
    return value


# Compatibility spelling for callers that use the inherited proof validator.
validate_proof_value = validate_four_session_proof


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise P342ObserverBindingError("P3.41 observer source changed")
    if predecessor.P341_RUN_ID_HEX != P341_PREDECESSOR_RUN_ID_HEX:
        raise P342ObserverBindingError("P3.41 observer predecessor changed")
    try:
        value = dict(_parser.audit_binding())
    except Exception as exc:
        raise P342ObserverBindingError(str(exc)) from exc
    value.update(
        {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "predecessor_source": dict(SOURCE_IDENTITY),
            "run_id_hex": P342_RUN_ID_HEX,
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
            "catalog_unchanged": True,
            "runtime_behavior_unchanged": True,
            "idle_listener_unchanged": True,
            "device_contact": False,
            "live_authorized": False,
        }
    )
    return value


# Compatibility spelling used by the inherited initial collector.  The live
# factory loads the collector into a fresh private retained-session module.
install_initial_capture = getattr(predecessor, "install_initial_capture", None)


def __getattr__(name: str) -> Any:
    return getattr(_parser, name)


__all__ = sorted(
    {
        "AuthObserverError",
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
        "P341_PREDECESSOR_RUN_ID",
        "P341_PREDECESSOR_RUN_ID_HEX",
        "P342ParserError",
        "P342ObserverBindingError",
        "P342_RUN_ID",
        "P342_RUN_ID_HEX",
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
