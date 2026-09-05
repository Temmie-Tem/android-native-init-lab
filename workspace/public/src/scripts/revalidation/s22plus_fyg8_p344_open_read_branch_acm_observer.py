#!/usr/bin/env python3
"""Host-only P3.44 authenticated ACM observer binding.

The reviewed P3.43 observer is loaded into a private namespace and rebound to
the fresh P3.44 runtime.  Host-first OPEN ordering, framing, HMAC, five named
queries, and the four-session/120-second idle proof are unchanged.  This
module performs no device or transport operation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_p343_open_read_branch_acm_observer as predecessor
import s22plus_fyg8_p344_open_read_branch_runtime as runtime


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 14_081,
    "sha256": "febb80cb70edd1ea115ed361fbd25b2a1127ed0f5c1d1b1743cda7f53d773ec1",
}
P343_PREDECESSOR_RUN_ID_HEX = runtime.P343_PREDECESSOR_RUN_ID_HEX
P343_PREDECESSOR_RUN_ID = runtime.P343_PREDECESSOR_RUN_ID
P343_RUN_ID_HEX = P343_PREDECESSOR_RUN_ID_HEX
P343_RUN_ID = P343_PREDECESSOR_RUN_ID
P344_RUN_ID_HEX = runtime.P344_RUN_ID_HEX
P344_RUN_ID = runtime.P344_RUN_ID
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
SCHEMA = "s22plus-fyg8-p344-readonly-exploration-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p344-readonly-exploration-acm-observer-v1"
IDLE_SECONDS = predecessor.IDLE_SECONDS
SAME_FD_SESSIONS = predecessor.SAME_FD_SESSIONS
TOTAL_SESSIONS = predecessor.TOTAL_SESSIONS
TOTAL_COMMANDS = TOTAL_SESSIONS * len(DEFAULT_COMMANDS)


class P344ObserverBindingError(ValueError):
    """The exact P3.43 parser or P3.44 runtime binding differs."""


AuthObserverError = P344ObserverBindingError


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


try:
    _payload = SOURCE.read_bytes()
except OSError as exc:
    raise P344ObserverBindingError("P3.43 observer source is unavailable") from exc
if identity(_payload) != SOURCE_IDENTITY:
    raise P344ObserverBindingError("P3.43 observer source identity differs")
if predecessor.P343_RUN_ID_HEX != P343_PREDECESSOR_RUN_ID_HEX:
    raise P344ObserverBindingError("P3.43 observer predecessor binding differs")

# Execute the frozen P343 wrapper privately, then rebind every parser layer to
# P344.  The imported P343 module and its parser globals remain untouched.
_BOUND = types.ModuleType("s22plus_fyg8_p343_observer_bound_for_p344")
_BOUND.__file__ = str(SOURCE)
try:
    exec(compile(_payload, str(SOURCE), "exec", dont_inherit=True), _BOUND.__dict__)  # noqa: S102
except Exception as exc:
    raise P344ObserverBindingError("P3.43 observer parser failed to load") from exc

_BOUND.SOURCE = SOURCE
_BOUND.SOURCE_IDENTITY = dict(SOURCE_IDENTITY)
_BOUND.runtime = runtime
_BOUND.P343_PREDECESSOR_RUN_ID_HEX = P343_PREDECESSOR_RUN_ID_HEX
_BOUND.P343_PREDECESSOR_RUN_ID = P343_PREDECESSOR_RUN_ID
_BOUND.P343_RUN_ID_HEX = P344_RUN_ID_HEX
_BOUND.P343_RUN_ID = P344_RUN_ID
_BOUND.DEVICE_BANNER = DEVICE_BANNER
_BOUND.DEFAULT_COMMANDS = DEFAULT_COMMANDS
_BOUND.CATALOG = CATALOG
_BOUND.CATALOG_ACTIONS = CATALOG_ACTIONS
_BOUND.SCHEMA = SCHEMA
_BOUND.CONTRACT_ID = CONTRACT_ID
_rebind = getattr(_BOUND, "_parser", None)
while isinstance(_rebind, types.ModuleType):
    _rebind.runtime = runtime
    for _prefix in (
        "P339",
        "P340",
        "P341",
        "P342",
        "P343",
        "P344",
    ):
        if any(
            key in _rebind.__dict__
            for key in (f"{_prefix}_RUN_ID_HEX", f"{_prefix}_RUN_ID")
        ):
            _rebind.__dict__[f"{_prefix}_RUN_ID_HEX"] = P344_RUN_ID_HEX
            _rebind.__dict__[f"{_prefix}_RUN_ID"] = P344_RUN_ID
    _rebind.DEVICE_BANNER = DEVICE_BANNER
    _rebind.DEFAULT_COMMANDS = DEFAULT_COMMANDS
    _rebind.SCHEMA = SCHEMA
    _rebind.CONTRACT_ID = CONTRACT_ID
    _rebind = getattr(_rebind, "_parser", None)

P344ParserError = getattr(_BOUND, "P343ParserError", P344ObserverBindingError)


def decode_frame(payload: bytes) -> Any:
    try:
        return _BOUND.decode_frame(payload)
    except Exception as exc:
        raise P344ObserverBindingError(str(exc)) from exc


def parse_open_read_branch_frame(payload: bytes) -> dict[str, Any]:
    try:
        value = dict(_BOUND.parse_open_read_branch_frame(payload))
    except Exception as exc:
        raise P344ObserverBindingError(str(exc)) from exc
    value.update({"run_id_hex": P344_RUN_ID_HEX, "idle_reuse": False})
    return value


def parse_open_read_diagnostic_frame(payload: bytes) -> dict[str, Any]:
    return parse_open_read_branch_frame(payload)


def parse_retained_open_read_branch(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes or not payload.startswith(DEVICE_BANNER):
        raise P344ObserverBindingError(
            "P344 retained stream has no exact leading device banner"
        )
    try:
        value = dict(_BOUND.parse_retained_open_read_branch(payload))
    except Exception as exc:
        raise P344ObserverBindingError(str(exc)) from exc
    value.update(
        {
            "run_id_hex": P344_RUN_ID_HEX,
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


def validate_four_session_proof(value: Any) -> dict[str, Any]:
    try:
        return _BOUND.validate_four_session_proof(value)
    except Exception as exc:
        raise P344ObserverBindingError(str(exc)) from exc


validate_proof_value = validate_four_session_proof


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise P344ObserverBindingError("P3.43 observer source changed")
    if predecessor.P343_RUN_ID_HEX != P343_PREDECESSOR_RUN_ID_HEX:
        raise P344ObserverBindingError("P3.43 observer predecessor changed")
    try:
        value = dict(_BOUND.audit_binding())
    except Exception as exc:
        raise P344ObserverBindingError(str(exc)) from exc
    value.update(
        {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "predecessor_source": dict(SOURCE_IDENTITY),
            "predecessor_run_id": P343_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P343_PREDECESSOR_RUN_ID_HEX,
            "run_id_hex": P344_RUN_ID_HEX,
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
            "catalog_allowlist_expanded": False,
            "catalog_allowlist_actions": CATALOG_ACTIONS,
            "middle_command_allowlist": True,
            "middle_command_allowlist_count": len(CATALOG_ACTIONS),
            "default_command_tuple_unchanged": True,
            "default_runtime_behavior_unchanged": True,
            "runtime_behavior_unchanged": True,
            "runtime_delta_identity_only": True,
            "runtime_order_changed": True,
            "idle_listener_unchanged": True,
            "caller_selected_command": False,
            "selected_command_integration": False,
            "initial_proof_default_action": "kernel",
            "device_contact": False,
            "live_authorized": False,
        }
    )
    return value


install_initial_capture = getattr(_BOUND, "install_initial_capture", None)


def __getattr__(name: str) -> Any:
    return getattr(_BOUND, name)


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
        "P343_PREDECESSOR_RUN_ID",
        "P343_PREDECESSOR_RUN_ID_HEX",
        "P344ParserError",
        "P344ObserverBindingError",
        "P344_RUN_ID",
        "P344_RUN_ID_HEX",
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
    | {
        f"{prefix}_RUN_ID{suffix}"
        for prefix in (
            "P328",
            "P330",
            "P331",
            "P332",
            "P333",
            "P334",
            "P335",
            "P336",
            "P337",
            "P338",
            "P339",
            "P340",
            "P341",
            "P342",
        )
        for suffix in ("", "_HEX")
    }
)
