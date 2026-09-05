#!/usr/bin/env python3
"""Host-only P3.43 runtime identity and named-read validator binding.

P3.42 is a consumed boot-only candidate.  P3.43 keeps its host-first OPEN
ordering, authenticated wire format, and four-session idle-reuse geometry,
then gives the device validator one closed middle-command allowlist.  The
normal/default tuple remains identity, ``uname -a`` (the initial proof), and
the fresh run nonce.  This module performs no device or transport operation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p342_open_read_branch_runtime as predecessor
import s22plus_fyg8_readonly_exploration as exploration


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 13_607,
    "sha256": "526976455962ab4abf70a83df5416f1c2a34bab5ee8c392226b029b45da67489",
}

P342_PREDECESSOR_RUN_ID_HEX = predecessor.P342_RUN_ID_HEX
P342_PREDECESSOR_RUN_ID = predecessor.P342_RUN_ID
P343_RUN_ID_HEX = "c343f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P343_RUN_ID = bytes.fromhex(P343_RUN_ID_HEX)
# Keep the consumed predecessor's conventional names available for callers;
# the compatibility aliases below deliberately stop at P341, as in P342.
P342_RUN_ID_HEX = P342_PREDECESSOR_RUN_ID_HEX
P342_RUN_ID = P342_PREDECESSOR_RUN_ID


class RuntimeIdentityError(ValueError):
    """The exact P3.42 runtime or P3.43 transform differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_source(path: Path, expected: Mapping[str, Any], label: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise RuntimeIdentityError(f"{label} is unavailable") from exc
    if identity(payload) != dict(expected):
        raise RuntimeIdentityError(f"{label} identity differs")
    return payload


_P342_SOURCE_PAYLOAD = _stable_source(
    SOURCE, SOURCE_IDENTITY, "P3.42 runtime source"
)
if predecessor.P342_RUN_ID_HEX != P342_PREDECESSOR_RUN_ID_HEX:
    raise RuntimeIdentityError("P3.42 runtime predecessor binding differs")


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


P342_COMMAND = predecessor.P342_COMMAND
P343_COMMAND = f"/bin/busybox echo P328-NONCE {P343_RUN_ID_HEX}".encode("ascii")


def _rebind_nonce(value: bytes) -> bytes:
    old = _c_string(P342_COMMAND)
    new = _c_string(P343_COMMAND)
    if value.count(old) != 1 or value.count(new):
        raise RuntimeIdentityError("P3.42 command marker is not unique")
    result = value.replace(old, new, 1)
    if result.count(old) or result.count(new) != 1:
        raise RuntimeIdentityError("P3.43 command marker delta differs")
    return result


def _derive_helper() -> bytes:
    try:
        nonce_rebound = _rebind_nonce(predecessor.P342_HELPER_TEMPLATE)
        return exploration.transform_validator(nonce_rebound, P343_RUN_ID_HEX)
    except Exception as exc:
        raise RuntimeIdentityError(
            "P3.43 named exploration validator anchors differ"
        ) from exc


P343_HELPER_TEMPLATE = _derive_helper()
P343_HELPER = P343_HELPER_TEMPLATE
P343_ENTRY = predecessor.P342_ENTRY
P342_DEFAULT_COMMANDS = tuple(predecessor.DEFAULT_COMMANDS)
P343_DEFAULT_COMMANDS = (
    P342_DEFAULT_COMMANDS[0],
    P342_DEFAULT_COMMANDS[1],
    P343_COMMAND,
)
DEFAULT_COMMANDS = P343_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P343_RUN_ID_HEX}\n".encode("ascii")
P343_DETAIL_ANCHOR = predecessor.P342_DETAIL_ANCHOR
CONTRACT_ID = "s22plus-fyg8-p343-readonly-exploration-runtime-v1"
SCHEMA = CONTRACT_ID
RUNTIME_KEY = predecessor.RUNTIME_KEY
TARGET = predecessor.TARGET
PUBLISHER = predecessor.PUBLISHER
AUTH_KEY_PLACEHOLDER = predecessor.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
AUTH_KEY_SCHEMA = getattr(
    predecessor, "AUTH_KEY_SCHEMA", "s22plus_fyg8_p328_auth_key_v1"
)
P343_ARTIFACT_SOURCE = Path(__file__).resolve()
CATALOG = exploration.CATALOG
CATALOG_ACTIONS = tuple(CATALOG)

# Compatibility labels used by the inherited runtime/observer loaders all
# resolve to this fresh P343 identity.  P342 remains explicitly named above
# as the consumed predecessor and is never silently reused as current.
for _prefix in (
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
):
    globals()[f"{_prefix}_RUN_ID_HEX"] = P343_RUN_ID_HEX
    globals()[f"{_prefix}_RUN_ID"] = P343_RUN_ID

# Preserve all wire geometry and timing bounds exactly.
OPEN_READ_BRANCHES = dict(predecessor.OPEN_READ_BRANCHES)
OPEN_HEADER_WORD_STAGES = tuple(predecessor.OPEN_HEADER_WORD_STAGES)
OPEN_HEADER_SIZE = predecessor.OPEN_HEADER_SIZE
DIAGNOSTIC_STAGE_OPEN_READ_RESULT = predecessor.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
DIAGNOSTIC_FRAME_TYPE = predecessor.DIAGNOSTIC_FRAME_TYPE
FRAME_MAGIC = predecessor.FRAME_MAGIC
FRAME_VERSION = predecessor.FRAME_VERSION
FRAME_OPEN = predecessor.FRAME_OPEN
MAX_FRAME_PAYLOAD = predecessor.MAX_FRAME_PAYLOAD


def materialize_helper(auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise RuntimeIdentityError("P343 authentication key is not 32 bytes")
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P343_HELPER_TEMPLATE.count(marker) != 1:
        raise RuntimeIdentityError("P343 key marker differs")
    return P343_HELPER_TEMPLATE.replace(marker, predecessor._key_initializer(auth_key), 1)


def auth_key_sha256(auth_key: bytes) -> str:
    return predecessor.auth_key_sha256(auth_key)


def classify_open_read_branch(stage: int, code: int) -> str:
    return predecessor.classify_open_read_branch(stage, code)


def classify_open_read_diagnostic(stage: int, code: int) -> str:
    return classify_open_read_branch(stage, code)


def _transform_from_p342(value: bytes, key: bytes) -> bytes:
    """Transform one complete P342 include, retaining its surrounding bytes."""

    old = predecessor.materialize_helper(key)
    if value.count(old) != 1:
        raise RuntimeIdentityError("P3.42 helper occurrence differs")
    intermediate = value.replace(old, _rebind_nonce(old), 1)
    return exploration.transform_validator(intermediate, P343_RUN_ID_HEX)


def _metadata(base: Mapping[str, Any]) -> dict[str, Any]:
    return dict(base) | {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P343_RUN_ID_HEX,
        "default_commands": tuple(DEFAULT_COMMANDS),
        "device_banner_hex": DEVICE_BANNER.hex(),
        "open_read_branch_ordinals": dict(OPEN_READ_BRANCHES),
        "open_read_branch_count": len(OPEN_READ_BRANCHES),
        "open_header_word_stages": OPEN_HEADER_WORD_STAGES,
        "open_header_size": OPEN_HEADER_SIZE,
        "host_first_open": True,
        "host_open_before_banner": True,
        "device_banner_after_open": True,
        "stage_zero_after_banner": True,
        "open_parsed_after_stage_zero": True,
        "no_unsolicited_device_tx": True,
        "silent_no_peer_no_proof": True,
        "consumed_partial_open_no_replay": True,
        "diagnostic_payload_unchanged": True,
        "diagnostic_frame_type_unchanged": True,
        "wire_frames_unchanged": True,
        "authentication_unchanged": True,
        "catalog_unchanged": False,
        "catalog_allowlist_expanded": True,
        "catalog_allowlist_actions": CATALOG_ACTIONS,
        "middle_command_allowlist": True,
        "middle_command_allowlist_count": len(CATALOG_ACTIONS),
        "middle_command_default_action": "kernel",
        "default_command_tuple_unchanged": True,
        "default_runtime_behavior_unchanged": True,
        "runtime_behavior_unchanged": False,
        "runtime_order_changed": True,
        "successful_wire_exchange_unchanged": False,
        "retry_added": False,
        "timeout_changed": False,
        "console_body_changed": False,
        "original_errno_returned_unchanged": True,
        "idle_listener_unchanged": True,
        "caller_selected_command": False,
        "selected_command_integration": False,
        "initial_proof_default_action": "kernel",
        "device_contact": False,
        "live_authorized": False,
    }


def validate_p343_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise RuntimeIdentityError("P343 runtime must be bytes")
    try:
        key = predecessor._materialized_key(value)
        digest = hashlib.sha256(key).hexdigest()
        current = materialize_helper(key)
        old = predecessor.materialize_helper(key)
        if value.count(current) != 1 or value.count(old):
            raise RuntimeIdentityError("P343 helper marker delta differs")
        # Reconstruct the exact consumed P342 include by replacing only the
        # current materialized helper.  The predecessor validator then checks
        # all surrounding runtime bytes before the fresh transform is compared.
        restored = value.replace(current, old, 1)
        base = predecessor.validate_p342_runtime(restored, auth_key_sha256=digest)
        expected = _transform_from_p342(restored, key)
        if value != expected:
            raise RuntimeIdentityError(
                "P343 helper differs beyond nonce and middle-command allowlist"
            )
    except RuntimeIdentityError:
        raise
    except Exception as exc:
        raise RuntimeIdentityError(str(exc)) from exc
    if auth_key_sha256 is not None and digest != auth_key_sha256:
        raise RuntimeIdentityError("P343 auth key digest differs")
    return _metadata({"predecessor_runtime": dict(base)})


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        key = predecessor._materialized_key(before)
        digest = hashlib.sha256(key).hexdigest()
        predecessor.validate_p342_runtime(before, auth_key_sha256=digest)
        expected = transform_runtime_include(before, key)
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.42 input differs: {exc}") from exc
    if after != expected:
        raise RuntimeIdentityError(
            "P3.43 delta exceeds fresh nonce and named-validator transform"
        )
    result = validate_p343_runtime(
        after, auth_key_sha256=auth_key_sha256 or digest
    )
    return result | {
        "changed_anchors": [
            "p343_fixed_command_identity_only",
            "p343_middle_command_named_allowlist",
        ],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": dict(
            predecessor.validate_p342_runtime(before, auth_key_sha256=digest)
        ),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = auth_key_sha256(auth_key)
    try:
        predecessor.validate_p342_runtime(value, auth_key_sha256=digest)
        old = predecessor.materialize_helper(auth_key)
        if value.count(old) != 1:
            raise RuntimeIdentityError("P3.42 helper occurrence differs")
        result = _transform_from_p342(value, auth_key)
        if result.count(P343_ENTRY) != 1:
            raise RuntimeIdentityError("P3.42 entry occurrence differs")
        validate_p343_runtime(result, auth_key_sha256=digest)
        return result
    except RuntimeIdentityError:
        raise
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.42 input differs: {exc}") from exc


def transform_artifacts(source: Mapping[str, bytes], auth_key: bytes) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise RuntimeIdentityError("P3.42 runtime input is missing")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise RuntimeIdentityError("P3.43 source delta differs")
    return result


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise RuntimeIdentityError("P3.42 runtime source identity differs")
    if predecessor.P342_RUN_ID_HEX != P342_PREDECESSOR_RUN_ID_HEX:
        raise RuntimeIdentityError("P3.42 runtime predecessor changed")
    if predecessor.OPEN_READ_BRANCHES != {
        0: "header-read-errno",
        1: "header-grammar",
        2: "body-read-errno",
        3: "crc",
        4: "open-semantic",
    }:
        raise RuntimeIdentityError("P3.42 branch table differs")
    if (
        predecessor.OPEN_HEADER_WORD_STAGES != (4, 5, 6, 7)
        or predecessor.OPEN_HEADER_SIZE != 16
    ):
        raise RuntimeIdentityError("P3.42 header capture geometry differs")
    if P343_ENTRY != predecessor.P342_ENTRY:
        raise RuntimeIdentityError("P3.43 device entry changed")
    try:
        expected_template = exploration.transform_validator(
            _rebind_nonce(predecessor.P342_HELPER_TEMPLATE), P343_RUN_ID_HEX
        )
    except Exception as exc:
        raise RuntimeIdentityError("P3.43 validator transform failed") from exc
    if P343_HELPER_TEMPLATE != expected_template:
        raise RuntimeIdentityError("P3.43 helper validator differs")
    return _metadata(
        {
            "predecessor_source": dict(SOURCE_IDENTITY),
            "predecessor_run_id": P342_PREDECESSOR_RUN_ID_HEX,
            "open_read_diagnostic_stage": DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        }
    ) | {
        "catalog_source": identity(
            Path(exploration.__file__).read_bytes()
        ),
        "catalog_source_commit": "f482210165",
        "fresh_run_id": P343_RUN_ID_HEX,
        "predecessor_run_id_rejected": P342_PREDECESSOR_RUN_ID_HEX,
    }


def __getattr__(name: str) -> Any:
    return getattr(predecessor, name)


__all__ = sorted(
    {
        "AUTH_KEY_PLACEHOLDER",
        "AUTH_KEY_SCHEMA",
        "AUTH_KEY_SIZE",
        "CATALOG",
        "CATALOG_ACTIONS",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "OPEN_HEADER_SIZE",
        "OPEN_HEADER_WORD_STAGES",
        "OPEN_READ_BRANCHES",
        "P342_COMMAND",
        "P342_DEFAULT_COMMANDS",
        "P342_PREDECESSOR_RUN_ID",
        "P342_PREDECESSOR_RUN_ID_HEX",
        "P343_ARTIFACT_SOURCE",
        "P343_COMMAND",
        "P343_DEFAULT_COMMANDS",
        "P343_DETAIL_ANCHOR",
        "P343_ENTRY",
        "P343_HELPER",
        "P343_HELPER_TEMPLATE",
        "P343_RUN_ID",
        "P343_RUN_ID_HEX",
        "RUNTIME_KEY",
        "RuntimeIdentityError",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "TARGET",
        "audit_binding",
        "auth_key_sha256",
        "classify_open_read_branch",
        "classify_open_read_diagnostic",
        "identity",
        "materialize_helper",
        "transform_artifacts",
        "transform_runtime_include",
        "validate_p343_runtime",
        "validate_transform",
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
