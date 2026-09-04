#!/usr/bin/env python3
"""Host-only P3.40 runtime identity transform.

This module loads the exact P3.39 rejected-OPEN runtime and changes only the
third fixed command's run-ID marker.  The P339 stage-3 grammar/semantic
branches and four existing header-word diagnostics remain byte-identical.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p339_open_read_branch_runtime as predecessor


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {"size": 21_479, "sha256": "5e494f03526b6c8818784880b4c76afbdf3b5d6bd41bbc9c2a927a88722ceedd"}
P339_PREDECESSOR_RUN_ID_HEX = "c339f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P339_PREDECESSOR_RUN_ID = bytes.fromhex(P339_PREDECESSOR_RUN_ID_HEX)
P340_RUN_ID_HEX = "c340f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P340_RUN_ID = bytes.fromhex(P340_RUN_ID_HEX)

# The inherited observer/engine imports these names while resolving the
# current candidate namespace.  They all intentionally bind to the fresh
# candidate; the sole predecessor identity remains P339_PREDECESSOR_* above.
for _compatibility_prefix in ("P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336", "P337", "P338", "P339"):
    globals()[f"{_compatibility_prefix}_RUN_ID_HEX"] = P340_RUN_ID_HEX
    globals()[f"{_compatibility_prefix}_RUN_ID"] = P340_RUN_ID

P339_COMMAND = f"/bin/busybox echo P328-NONCE {P339_PREDECESSOR_RUN_ID_HEX}".encode("ascii")
P340_COMMAND = f"/bin/busybox echo P328-NONCE {P340_RUN_ID_HEX}".encode("ascii")


class RuntimeIdentityError(ValueError):
    """The exact P3.39 runtime or P3.40 one-ID delta differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


_OLD_MARKER = _c_string(P339_COMMAND)
_NEW_MARKER = _c_string(P340_COMMAND)
if predecessor.P339_HELPER_TEMPLATE.count(_OLD_MARKER) != 1:
    raise RuntimeIdentityError("P3.39 command marker is not unique")
if predecessor.P339_HELPER_TEMPLATE.count(_NEW_MARKER):
    raise RuntimeIdentityError("P3.40 command marker already exists")
P340_HELPER_TEMPLATE = predecessor.P339_HELPER_TEMPLATE.replace(_OLD_MARKER, _NEW_MARKER, 1)
P340_HELPER = P340_HELPER_TEMPLATE
P340_DEFAULT_COMMANDS = (
    predecessor.DEFAULT_COMMANDS[0], predecessor.DEFAULT_COMMANDS[1], P340_COMMAND
)
DEFAULT_COMMANDS = P340_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P340_RUN_ID_HEX}\n".encode("ascii")
P340_ENTRY = predecessor.P339_ENTRY
P340_DETAIL_ANCHOR = predecessor.P339_DETAIL_ANCHOR
CONTRACT_ID = "s22plus-fyg8-p340-open-header-capture-runtime-v1"
SCHEMA = CONTRACT_ID
RUNTIME_KEY = predecessor.RUNTIME_KEY
TARGET = predecessor.TARGET
PUBLISHER = predecessor.PUBLISHER
AUTH_KEY_PLACEHOLDER = predecessor.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
P340_ARTIFACT_SOURCE = Path(__file__).resolve()


def materialize_helper(auth_key: bytes) -> bytes:
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P340_HELPER_TEMPLATE.count(marker) != 1:
        raise RuntimeIdentityError("P3.40 key marker differs")
    return P340_HELPER_TEMPLATE.replace(marker, predecessor._key_initializer(auth_key), 1)


def auth_key_sha256(auth_key: bytes) -> str:
    return predecessor.auth_key_sha256(auth_key)


def classify_open_read_branch(stage: int, code: int) -> str:
    return predecessor.classify_open_read_branch(stage, code)


def classify_open_read_diagnostic(stage: int, code: int) -> str:
    return classify_open_read_branch(stage, code)


def validate_p340_runtime(value: bytes, *, auth_key_sha256: str | None = None) -> dict[str, Any]:
    if type(value) is not bytes:
        raise RuntimeIdentityError("P3.40 runtime must be bytes")
    try:
        key = predecessor._materialized_key(value)
        current = materialize_helper(key)
        old = predecessor.materialize_helper(key)
        base = predecessor.validate_p339_runtime(value.replace(current, old, 1), auth_key_sha256=hashlib.sha256(key).hexdigest())
    except Exception as exc:
        raise RuntimeIdentityError(str(exc)) from exc
    if value.count(current) != 1 or value.count(old):
        raise RuntimeIdentityError("P3.40 runtime marker delta differs")
    digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and digest != auth_key_sha256:
        raise RuntimeIdentityError("P3.40 auth key digest differs")
    return dict(base) | {
        "schema": SCHEMA, "contract_id": CONTRACT_ID, "run_id_hex": P340_RUN_ID_HEX,
        "default_commands": tuple(DEFAULT_COMMANDS),
        "open_read_branch_ordinals": dict(predecessor.OPEN_READ_BRANCHES),
        "open_read_branch_count": len(predecessor.OPEN_READ_BRANCHES),
        "open_header_word_stages": predecessor.OPEN_HEADER_WORD_STAGES,
        "open_header_size": predecessor.OPEN_HEADER_SIZE,
        "open_header_capture_on": ["header-grammar", "open-semantic"],
        "diagnostic_payload_unchanged": True, "diagnostic_frame_type_unchanged": True,
        "successful_wire_exchange_unchanged": True, "retry_added": False,
        "timeout_changed": False, "console_body_changed": False,
        "original_errno_returned_unchanged": True,
    }


def validate_transform(before: bytes, after: bytes, *, auth_key_sha256: str | None = None) -> dict[str, Any]:
    try:
        key = predecessor._materialized_key(before)
        expected = before.replace(predecessor.materialize_helper(key), materialize_helper(key), 1)
        base = predecessor.validate_p339_runtime(before, auth_key_sha256=hashlib.sha256(key).hexdigest())
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.39 input differs: {exc}") from exc
    if after != expected:
        raise RuntimeIdentityError("P3.40 delta exceeds one fixed-command marker")
    value = validate_p340_runtime(after, auth_key_sha256=auth_key_sha256)
    return value | {
        "changed_anchors": ["p340_fixed_command_identity_only"],
        "source_identity": identity(before), "target_identity": identity(after),
        "predecessor": dict(base),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = auth_key_sha256(auth_key)
    try:
        predecessor.validate_p339_runtime(value, auth_key_sha256=digest)
        old = predecessor.materialize_helper(auth_key)
        if value.count(old) != 1:
            raise RuntimeIdentityError("P3.39 helper occurrence differs")
        result = value.replace(old, materialize_helper(auth_key), 1)
        validate_transform(value, result, auth_key_sha256=digest)
        return result
    except RuntimeIdentityError:
        raise
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.39 input differs: {exc}") from exc


def transform_artifacts(source: Mapping[str, bytes], auth_key: bytes) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise RuntimeIdentityError("P3.39 runtime input is missing")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise RuntimeIdentityError("P3.40 source delta differs")
    return result


def audit_binding() -> dict[str, Any]:
    if predecessor.identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise RuntimeIdentityError("P3.39 runtime source identity differs")
    if predecessor.OPEN_READ_BRANCHES != {0: "header-read-errno", 1: "header-grammar", 2: "body-read-errno", 3: "crc", 4: "open-semantic"}:
        raise RuntimeIdentityError("P3.39 branch table differs")
    if predecessor.OPEN_HEADER_WORD_STAGES != (4, 5, 6, 7) or predecessor.OPEN_HEADER_SIZE != 16:
        raise RuntimeIdentityError("P3.39 header capture geometry differs")
    return {
        "schema": SCHEMA, "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "predecessor_run_id": P339_PREDECESSOR_RUN_ID_HEX, "run_id_hex": P340_RUN_ID_HEX,
        "open_read_diagnostic_stage": predecessor.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "open_read_branch_ordinals": dict(predecessor.OPEN_READ_BRANCHES),
        "open_read_branch_count": 5, "open_header_word_stages": (4, 5, 6, 7),
        "open_header_size": 16, "open_header_capture_on": ["header-grammar", "open-semantic"],
        "diagnostic_payload_unchanged": True, "diagnostic_frame_type_unchanged": True,
        "successful_wire_exchange_unchanged": True, "original_errno_returned_unchanged": True,
        "retry_added": False, "timeout_changed": False,
        "device_contact": False, "live_authorized": False,
    }


def __getattr__(name: str) -> Any:
    return getattr(predecessor, name)


__all__ = sorted({
    "AUTH_KEY_PLACEHOLDER", "AUTH_KEY_SIZE", "CONTRACT_ID", "DEFAULT_COMMANDS",
    "DEVICE_BANNER", "P340_ARTIFACT_SOURCE", "P340_DEFAULT_COMMANDS", "P340_ENTRY",
    "P340_HELPER", "P340_HELPER_TEMPLATE", "P340_RUN_ID", "P340_RUN_ID_HEX",
    "P339_PREDECESSOR_RUN_ID", "P339_PREDECESSOR_RUN_ID_HEX", "RUNTIME_KEY", "SCHEMA",
    "SOURCE", "SOURCE_IDENTITY", "TARGET", "audit_binding", "auth_key_sha256",
    "classify_open_read_branch", "classify_open_read_diagnostic", "identity",
    "materialize_helper", "transform_artifacts", "transform_runtime_include",
    "validate_p340_runtime", "validate_transform",
} | {
    f"{prefix}_RUN_ID{suffix}"
    for prefix in ("P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336", "P337", "P338", "P339")
    for suffix in ("", "_HEX")
})
