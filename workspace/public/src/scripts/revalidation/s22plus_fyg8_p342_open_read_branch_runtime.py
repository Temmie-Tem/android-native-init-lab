#!/usr/bin/env python3
"""Host-only P3.42 runtime identity binding.

P3.42 is an identity successor to the consumed P3.41 host-first OPEN
runtime.  The device/runtime implementation and wire ordering are unchanged;
only the fixed run marker in the existing helper and the public namespace are
rebound.  The separate H0 idle-reuse helper owns the three-same-FD/one-reopen
qualification and is deliberately not installed here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p341_open_read_branch_runtime as predecessor


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 15_544,
    "sha256": "4dfa7b0be0ee5180960f8e43ba2f460029efa54394e388a21376b5f71207f869",
}

P341_PREDECESSOR_RUN_ID_HEX = predecessor.P341_RUN_ID_HEX
P341_PREDECESSOR_RUN_ID = predecessor.P341_RUN_ID
P342_RUN_ID_HEX = "c342f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P342_RUN_ID = bytes.fromhex(P342_RUN_ID_HEX)


class RuntimeIdentityError(ValueError):
    """The exact P3.41 runtime or P3.42 identity projection differs."""


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


_P341_SOURCE_PAYLOAD = _stable_source(
    SOURCE, SOURCE_IDENTITY, "P3.41 runtime source"
)
if predecessor.P341_RUN_ID_HEX != P341_PREDECESSOR_RUN_ID_HEX:
    raise RuntimeIdentityError("P3.41 runtime predecessor binding differs")


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


P341_COMMAND = predecessor.P341_COMMAND
P342_COMMAND = f"/bin/busybox echo P328-NONCE {P342_RUN_ID_HEX}".encode("ascii")


def _derive_helper() -> bytes:
    old = _c_string(P341_COMMAND)
    new = _c_string(P342_COMMAND)
    if predecessor.P341_HELPER_TEMPLATE.count(old) != 1:
        raise RuntimeIdentityError("P3.41 command marker is not unique")
    if predecessor.P341_HELPER_TEMPLATE.count(new):
        raise RuntimeIdentityError("P3.42 command marker already exists")
    value = predecessor.P341_HELPER_TEMPLATE.replace(old, new, 1)
    if value.count(old) or value.count(new) != 1:
        raise RuntimeIdentityError("P3.42 helper command delta differs")
    return value


P342_HELPER_TEMPLATE = _derive_helper()
P342_HELPER = P342_HELPER_TEMPLATE
P342_ENTRY = predecessor.P341_ENTRY
P342_DEFAULT_COMMANDS = (
    predecessor.DEFAULT_COMMANDS[0],
    predecessor.DEFAULT_COMMANDS[1],
    P342_COMMAND,
)
DEFAULT_COMMANDS = P342_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P342_RUN_ID_HEX}\n".encode("ascii")
P342_DETAIL_ANCHOR = predecessor.P341_DETAIL_ANCHOR
CONTRACT_ID = "s22plus-fyg8-p342-idle-reuse-runtime-v1"
SCHEMA = CONTRACT_ID
RUNTIME_KEY = predecessor.RUNTIME_KEY
TARGET = predecessor.TARGET
PUBLISHER = predecessor.PUBLISHER
AUTH_KEY_PLACEHOLDER = predecessor.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
AUTH_KEY_SCHEMA = getattr(
    predecessor, "AUTH_KEY_SCHEMA", "s22plus_fyg8_p328_auth_key_v1"
)
P342_ARTIFACT_SOURCE = Path(__file__).resolve()

# The inherited parser/runtime imports use compatibility labels.  They all
# resolve to the fresh P342 identity; P341 is retained explicitly above as the
# consumed predecessor only.
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
    globals()[f"{_prefix}_RUN_ID_HEX"] = P342_RUN_ID_HEX
    globals()[f"{_prefix}_RUN_ID"] = P342_RUN_ID

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
        raise RuntimeIdentityError("P342 authentication key is not 32 bytes")
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P342_HELPER_TEMPLATE.count(marker) != 1:
        raise RuntimeIdentityError("P342 key marker differs")
    return P342_HELPER_TEMPLATE.replace(marker, predecessor._key_initializer(auth_key), 1)


def auth_key_sha256(auth_key: bytes) -> str:
    return predecessor.auth_key_sha256(auth_key)


def classify_open_read_branch(stage: int, code: int) -> str:
    return predecessor.classify_open_read_branch(stage, code)


def classify_open_read_diagnostic(stage: int, code: int) -> str:
    return classify_open_read_branch(stage, code)


def validate_p342_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise RuntimeIdentityError("P342 runtime must be bytes")
    try:
        key = predecessor._materialized_key(value)
        current = materialize_helper(key)
        old = predecessor.materialize_helper(key)
        if value.count(current) != 1 or value.count(old):
            raise RuntimeIdentityError("P342 helper marker delta differs")
        if value.count(P342_ENTRY) != 1:
            raise RuntimeIdentityError("P342 entry marker differs")
        restored = value.replace(current, old, 1)
        base = predecessor.validate_p341_runtime(
            restored, auth_key_sha256=hashlib.sha256(key).hexdigest()
        )
    except RuntimeIdentityError:
        raise
    except Exception as exc:
        raise RuntimeIdentityError(str(exc)) from exc
    digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and digest != auth_key_sha256:
        raise RuntimeIdentityError("P342 auth key digest differs")
    return dict(base) | {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P342_RUN_ID_HEX,
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
        "catalog_unchanged": True,
        "runtime_behavior_unchanged": True,
        "runtime_order_changed": True,
        "successful_wire_exchange_unchanged": False,
        "retry_added": False,
        "timeout_changed": False,
        "console_body_changed": False,
        "original_errno_returned_unchanged": True,
        "idle_listener_unchanged": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        key = predecessor._materialized_key(before)
        digest = hashlib.sha256(key).hexdigest()
        predecessor.validate_p341_runtime(before, auth_key_sha256=digest)
        expected = transform_runtime_include(before, key)
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.41 input differs: {exc}") from exc
    if after != expected:
        raise RuntimeIdentityError("P3.42 delta exceeds identity-only command marker")
    result = validate_p342_runtime(
        after, auth_key_sha256=auth_key_sha256 or digest
    )
    return result | {
        "changed_anchors": ["p342_fixed_command_identity_only"],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": dict(
            predecessor.validate_p341_runtime(before, auth_key_sha256=digest)
        ),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = auth_key_sha256(auth_key)
    try:
        predecessor.validate_p341_runtime(value, auth_key_sha256=digest)
        old = predecessor.materialize_helper(auth_key)
        if value.count(old) != 1:
            raise RuntimeIdentityError("P3.41 helper occurrence differs")
        result = value.replace(old, materialize_helper(auth_key), 1)
        if result.count(P342_ENTRY) != 1:
            raise RuntimeIdentityError("P3.41 entry occurrence differs")
        validate_p342_runtime(result, auth_key_sha256=digest)
        return result
    except RuntimeIdentityError:
        raise
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.41 input differs: {exc}") from exc


def transform_artifacts(source: Mapping[str, bytes], auth_key: bytes) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise RuntimeIdentityError("P3.41 runtime input is missing")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise RuntimeIdentityError("P3.42 source delta differs")
    return result


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise RuntimeIdentityError("P3.41 runtime source identity differs")
    if predecessor.OPEN_READ_BRANCHES != {
        0: "header-read-errno",
        1: "header-grammar",
        2: "body-read-errno",
        3: "crc",
        4: "open-semantic",
    }:
        raise RuntimeIdentityError("P3.41 branch table differs")
    if (
        predecessor.OPEN_HEADER_WORD_STAGES != (4, 5, 6, 7)
        or predecessor.OPEN_HEADER_SIZE != 16
    ):
        raise RuntimeIdentityError("P3.41 header capture geometry differs")
    if predecessor.P341_ENTRY != P342_ENTRY:
        raise RuntimeIdentityError("P3.42 device entry changed")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "predecessor_run_id": P341_PREDECESSOR_RUN_ID_HEX,
        "run_id_hex": P342_RUN_ID_HEX,
        "open_read_diagnostic_stage": DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
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
        "catalog_unchanged": True,
        "runtime_behavior_unchanged": True,
        "runtime_order_changed": True,
        "successful_wire_exchange_unchanged": False,
        "idle_listener_unchanged": True,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "device_contact": False,
        "live_authorized": False,
    }


def __getattr__(name: str) -> Any:
    return getattr(predecessor, name)


__all__ = sorted(
    {
        "AUTH_KEY_PLACEHOLDER",
        "AUTH_KEY_SCHEMA",
        "AUTH_KEY_SIZE",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "OPEN_HEADER_SIZE",
        "OPEN_HEADER_WORD_STAGES",
        "OPEN_READ_BRANCHES",
        "P341_COMMAND",
        "P341_PREDECESSOR_RUN_ID",
        "P341_PREDECESSOR_RUN_ID_HEX",
        "P342_ARTIFACT_SOURCE",
        "P342_COMMAND",
        "P342_DEFAULT_COMMANDS",
        "P342_DETAIL_ANCHOR",
        "P342_ENTRY",
        "P342_HELPER",
        "P342_HELPER_TEMPLATE",
        "P342_RUN_ID",
        "P342_RUN_ID_HEX",
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
        "validate_p342_runtime",
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
        )
        for suffix in ("", "_HEX")
    }
)
