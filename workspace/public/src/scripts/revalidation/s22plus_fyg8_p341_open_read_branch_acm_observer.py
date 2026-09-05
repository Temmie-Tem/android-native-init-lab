#!/usr/bin/env python3
"""Host-only P3.41 observer/parser binding.

The P340 retained-session parser is loaded into a private module namespace and
rebound to the P341 runtime.  It does not create a banner or proof when a
no-banner/partial observation is received: those bytes remain raw
``NO_PROOF_OBSERVER`` evidence.  The host-first OPEN ordering is owned by the
separate H0 helper and is never installed into a shared observer module.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_host_first_open as host_first
import s22plus_fyg8_p340_open_read_branch_acm_observer as predecessor
import s22plus_fyg8_p341_open_read_branch_runtime as runtime


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 2_398,
    "sha256": "a83d9187b1e5439ee4cce1db5dd3cedb23a67a8d38835b3a5b0d2bd74da779ab",
}
HOST_FIRST_SOURCE = Path(host_first.__file__).resolve()
HOST_FIRST_SOURCE_IDENTITY = dict(runtime.HOST_FIRST_SOURCE_IDENTITY)
P340_PREDECESSOR_RUN_ID_HEX = runtime.P340_PREDECESSOR_RUN_ID_HEX
P340_PREDECESSOR_RUN_ID = runtime.P340_PREDECESSOR_RUN_ID
P341_RUN_ID_HEX = runtime.P341_RUN_ID_HEX
P341_RUN_ID = runtime.P341_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)

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
SCHEMA = "s22plus-fyg8-p341-host-first-open-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p341-host-first-open-acm-observer-v1"


class P341ObserverBindingError(ValueError):
    """The exact P340 parser or P341 runtime binding differs."""


AuthObserverError = P341ObserverBindingError


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
    raise P341ObserverBindingError("P340 observer source identity differs")
if identity(HOST_FIRST_SOURCE.read_bytes()) != HOST_FIRST_SOURCE_IDENTITY:
    raise P341ObserverBindingError("host-first helper source identity differs")
if predecessor.P340_RUN_ID_HEX != P340_PREDECESSOR_RUN_ID_HEX:
    raise P341ObserverBindingError("P340 observer predecessor binding differs")

_payload = SOURCE.read_bytes()
_parser = types.ModuleType("s22plus_fyg8_p340_parser_bound_for_p341")
_parser.__file__ = str(SOURCE)
try:
    exec(compile(_payload, str(SOURCE), "exec", dont_inherit=True), _parser.__dict__)  # noqa: S102
except Exception as exc:
    raise P341ObserverBindingError("P340 observer parser failed to load") from exc

# All callable parser globals below are now private to this module.  Rebind
# only the wire namespace; no source is rewritten and no shared P340 module is
# mutated.
_parser.runtime = runtime
_parser.P340_RUN_ID_HEX = P341_RUN_ID_HEX
_parser.P340_RUN_ID = P341_RUN_ID
_parser.DEVICE_BANNER = DEVICE_BANNER
_parser.DEFAULT_COMMANDS = DEFAULT_COMMANDS
_parser.SCHEMA = SCHEMA
_parser.CONTRACT_ID = CONTRACT_ID
# P340 itself privately loads the P339 parser.  Its parser functions retain
# their own globals, so rebind that nested module as well; otherwise a valid
# P341 diagnostic would still be checked against the P340 runtime limits.
_nested_parser = getattr(_parser, "_parser", None)
if isinstance(_nested_parser, types.ModuleType):
    _nested_parser.runtime = runtime
    _nested_parser.P339_RUN_ID_HEX = P341_RUN_ID_HEX
    _nested_parser.P339_RUN_ID = P341_RUN_ID
    _nested_parser.DEVICE_BANNER = DEVICE_BANNER
    _nested_parser.DEFAULT_COMMANDS = DEFAULT_COMMANDS
    _nested_parser.SCHEMA = SCHEMA
    _nested_parser.CONTRACT_ID = CONTRACT_ID
P341ParserError = _parser.P340ObserverBindingError


def decode_frame(payload: bytes) -> Any:
    try:
        return _parser.decode_frame(payload)
    except Exception as exc:
        raise P341ObserverBindingError(str(exc)) from exc


def parse_open_read_branch_frame(payload: bytes) -> dict[str, Any]:
    try:
        value = dict(_parser.parse_open_read_branch_frame(payload))
    except Exception as exc:
        raise P341ObserverBindingError(str(exc)) from exc
    value.update({"run_id_hex": P341_RUN_ID_HEX, "host_first_open": True})
    return value


def parse_open_read_diagnostic_frame(payload: bytes) -> dict[str, Any]:
    return parse_open_read_branch_frame(payload)


def parse_retained_open_read_branch(payload: bytes) -> dict[str, Any]:
    """Parse retained diagnostics without manufacturing a missing banner."""
    # A diagnostic-only or partial stream has no synchronization proof.  Keep
    # it in the caller's raw receipt and let the live result path project the
    # ordinary ``NO_PROOF_OBSERVER`` bucket; never invent a banner to make the
    # inherited parser's reason index look complete.
    if type(payload) is not bytes or not payload.startswith(DEVICE_BANNER):
        raise P341ObserverBindingError(
            "P341 retained stream has no exact leading device banner"
        )
    try:
        value = dict(_parser.parse_retained_open_read_branch(payload))
    except Exception as exc:
        raise P341ObserverBindingError(str(exc)) from exc
    banner_seen = True
    value.update(
        {
            "run_id_hex": P341_RUN_ID_HEX,
            "banner_seen": banner_seen,
            "host_first_open": True,
            "no_banner_is_raw_no_proof": not banner_seen,
            "proof_class": "NO_PROOF_OBSERVER",
            "candidate_success": False,
            "causal_result_allowed": False,
        }
    )
    return value


def parse_retained_open_read_diagnostic(payload: bytes) -> dict[str, Any]:
    return parse_retained_open_read_branch(payload)


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise P341ObserverBindingError("P340 observer source changed")
    if identity(HOST_FIRST_SOURCE.read_bytes()) != HOST_FIRST_SOURCE_IDENTITY:
        raise P341ObserverBindingError("host-first helper source changed")
    try:
        value = dict(_parser.audit_binding())
    except Exception as exc:
        raise P341ObserverBindingError(str(exc)) from exc
    value.update(
        {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "predecessor_source": dict(SOURCE_IDENTITY),
            "host_first_source": dict(HOST_FIRST_SOURCE_IDENTITY),
            "run_id_hex": P341_RUN_ID_HEX,
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
            "initial_failure_suffix_capture": False,
            "device_contact": False,
            "live_authorized": False,
        }
    )
    return value


# Compatibility spelling used by the P340 initial collector.  P341 callers
# intentionally do not install this collector; partial/no-banner bytes are
# retained by the P335 raw writer and classified as no-proof.
install_initial_capture = getattr(predecessor, "install_initial_capture", None)


def __getattr__(name: str) -> Any:
    return getattr(_parser, name)


__all__ = sorted(
    {
        "AuthObserverError", "CONTRACT_ID", "DEFAULT_COMMANDS", "DIAGNOSTIC",
        "DEVICE_BANNER", "HEADER", "HOST_FIRST_SOURCE", "HOST_FIRST_SOURCE_IDENTITY",
        "MAX_INITIAL_SESSIONS", "MAX_PHYSICAL_REOPENS", "MAX_PREAMBLE_PAIRS",
        "MAX_RECONNECTS", "MAX_RESYNC_BYTES", "MAX_SESSIONS", "P341ParserError",
        "P341ObserverBindingError", "P341_RUN_ID", "P341_RUN_ID_HEX", "PHYSICAL_REOPEN_COUNT",
        "SCHEMA", "SESSION_TIMEOUT_SEC", "SOURCE", "SOURCE_IDENTITY",
        "audit_binding", "decode_frame", "identity", "install_initial_capture",
        "parse_open_read_branch_frame", "parse_open_read_diagnostic_frame",
        "parse_retained_open_read_branch", "parse_retained_open_read_diagnostic",
    }
)
