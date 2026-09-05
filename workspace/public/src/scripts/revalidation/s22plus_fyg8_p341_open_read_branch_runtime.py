#!/usr/bin/env python3
"""Host-only P3.41 host-first OPEN runtime binding.

P3.40 is a consumed candidate.  P3.41 is a fresh boot-only identity whose
only protocol change is the already-qualified ``host_first_open`` transform:
the host writes one OPEN before waiting for the native banner, and the
device emits its banner, stage-zero diagnostic, and OPEN_PARSED diagnostic
after that accepted OPEN.  The P340 three-session/HMAC/catalog/deadline
geometry is retained.  This module never contacts a device.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_host_first_open as host_first
import s22plus_fyg8_p340_open_read_branch_runtime as predecessor


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 9_616,
    "sha256": "c93601501f13344734f86a241673d9c42aaae9aad44ac8e9edf6c496db1815d1",
}
HOST_FIRST_SOURCE = Path(host_first.__file__).resolve()
HOST_FIRST_SOURCE_IDENTITY = {
    "size": 6_341,
    "sha256": "970b06eb0df52c93e9c59f8867bca81d653e04d502c95429e27947d7dde2603a",
}

P340_PREDECESSOR_RUN_ID_HEX = "c340f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P340_PREDECESSOR_RUN_ID = bytes.fromhex(P340_PREDECESSOR_RUN_ID_HEX)
P341_RUN_ID_HEX = "c341f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P341_RUN_ID = bytes.fromhex(P341_RUN_ID_HEX)


class RuntimeIdentityError(ValueError):
    """The exact P340 runtime or P341 transform differs."""


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


# Pin both inputs at import time.  In particular, changing the shared H0
# helper after this module is loaded must fail closed rather than silently
# changing the P341 execution closure.
_P340_SOURCE_PAYLOAD = _stable_source(SOURCE, SOURCE_IDENTITY, "P3.40 runtime source")
_HOST_FIRST_SOURCE_PAYLOAD = _stable_source(
    HOST_FIRST_SOURCE, HOST_FIRST_SOURCE_IDENTITY, "host-first OPEN helper"
)
if predecessor.P340_RUN_ID_HEX != P340_PREDECESSOR_RUN_ID_HEX:
    raise RuntimeIdentityError("P3.40 runtime predecessor binding differs")


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


P340_COMMAND = f"/bin/busybox echo P328-NONCE {P340_PREDECESSOR_RUN_ID_HEX}".encode(
    "ascii"
)
P341_COMMAND = f"/bin/busybox echo P328-NONCE {P341_RUN_ID_HEX}".encode("ascii")


def _derive_helper() -> bytes:
    try:
        host_template = host_first.helper(predecessor.P340_HELPER_TEMPLATE)
    except Exception as exc:
        raise RuntimeIdentityError("host-first OPEN helper anchors differ") from exc
    old = _c_string(P340_COMMAND)
    new = _c_string(P341_COMMAND)
    if host_template.count(old) != 1 or host_template.count(new):
        raise RuntimeIdentityError("P340/P341 command marker is not unique")
    return host_template.replace(old, new, 1)


P341_HELPER_TEMPLATE = _derive_helper()
P341_HELPER = P341_HELPER_TEMPLATE
P341_ENTRY = host_first.entry(predecessor.P340_ENTRY)
P341_DEFAULT_COMMANDS = (
    predecessor.DEFAULT_COMMANDS[0],
    predecessor.DEFAULT_COMMANDS[1],
    P341_COMMAND,
)
DEFAULT_COMMANDS = P341_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P341_RUN_ID_HEX}\n".encode("ascii")
P341_DETAIL_ANCHOR = predecessor.P340_DETAIL_ANCHOR
CONTRACT_ID = "s22plus-fyg8-p341-host-first-open-runtime-v1"
SCHEMA = CONTRACT_ID
RUNTIME_KEY = predecessor.RUNTIME_KEY
TARGET = predecessor.TARGET
PUBLISHER = predecessor.PUBLISHER
AUTH_KEY_PLACEHOLDER = predecessor.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
AUTH_KEY_SCHEMA = getattr(predecessor, "AUTH_KEY_SCHEMA", "s22plus_fyg8_p328_auth_key_v1")
P341_ARTIFACT_SOURCE = Path(__file__).resolve()

# The inherited parser/runtime imports use these compatibility labels.  They
# are aliases for the fresh P341 bytes, never authority for a predecessor.
for _prefix in (
    "P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336",
    "P337", "P338", "P339", "P340",
):
    globals()[f"{_prefix}_RUN_ID_HEX"] = P341_RUN_ID_HEX
    globals()[f"{_prefix}_RUN_ID"] = P341_RUN_ID

# Preserve the exact P340 branch vocabulary and timing bounds.
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
        raise RuntimeIdentityError("P341 authentication key is not 32 bytes")
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P341_HELPER_TEMPLATE.count(marker) != 1:
        raise RuntimeIdentityError("P341 key marker differs")
    return P341_HELPER_TEMPLATE.replace(marker, predecessor._key_initializer(auth_key), 1)


def auth_key_sha256(auth_key: bytes) -> str:
    return predecessor.auth_key_sha256(auth_key)


def classify_open_read_branch(stage: int, code: int) -> str:
    return predecessor.classify_open_read_branch(stage, code)


def classify_open_read_diagnostic(stage: int, code: int) -> str:
    return classify_open_read_branch(stage, code)


def _restore_p340(value: bytes, key: bytes) -> bytes:
    """Restore a P341 include to P340 solely for the pinned validator."""
    current = materialize_helper(key)
    old = predecessor.materialize_helper(key)
    if value.count(current) != 1 or value.count(old):
        raise RuntimeIdentityError("P341 helper marker delta differs")
    restored = value.replace(current, old, 1)
    if restored.count(P341_RUN_ID) or restored.count(P341_RUN_ID_HEX.encode("ascii")):
        raise RuntimeIdentityError("P341 run ID remains after helper restore")
    if restored.count(P341_ENTRY) != 0:
        raise RuntimeIdentityError("P341 entry marker remains after helper restore")
    # The entry is source text, not materialized key data.  P341_ENTRY can be
    # empty only in a malformed input; require a single exact replacement.
    # host_first has no P341 run bytes in the entry, so the P340 entry is the
    # authoritative inverse anchor.
    return restored


def validate_p341_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise RuntimeIdentityError("P341 runtime must be bytes")
    try:
        key = predecessor._materialized_key(value)
        current = materialize_helper(key)
        old = predecessor.materialize_helper(key)
        if value.count(current) != 1 or value.count(old):
            raise RuntimeIdentityError("P341 helper marker delta differs")
        if value.count(P341_ENTRY) != 1 or value.count(predecessor.P340_ENTRY):
            raise RuntimeIdentityError("P341 entry marker delta differs")
        # Make the exact inverse for the P340 validator.  The old entry is
        # restored independently of the helper, preserving its source check.
        restored = value.replace(current, old, 1).replace(P341_ENTRY, predecessor.P340_ENTRY, 1)
        base = predecessor.validate_p340_runtime(
            restored, auth_key_sha256=hashlib.sha256(key).hexdigest()
        )
    except RuntimeIdentityError:
        raise
    except Exception as exc:
        raise RuntimeIdentityError(str(exc)) from exc
    digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and digest != auth_key_sha256:
        raise RuntimeIdentityError("P341 auth key digest differs")
    return dict(base) | {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P341_RUN_ID_HEX,
        "default_commands": tuple(DEFAULT_COMMANDS),
        "open_read_branch_ordinals": dict(OPEN_READ_BRANCHES),
        "open_read_branch_count": len(OPEN_READ_BRANCHES),
        "open_header_word_stages": OPEN_HEADER_WORD_STAGES,
        "open_header_size": OPEN_HEADER_SIZE,
        "open_header_capture_on": ["header-grammar", "open-semantic"],
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
        # Device frame/auth/catalog bytes are unchanged, but the successful
        # exchange ordering now begins with host OPEN, so the whole wire
        # exchange is not byte/order-identical to P340.
        "successful_wire_exchange_unchanged": False,
        "wire_frames_unchanged": True,
        "authentication_unchanged": True,
        "catalog_unchanged": True,
        "runtime_order_changed": True,
        "retry_added": False,
        "timeout_changed": False,
        "console_body_changed": False,
        "original_errno_returned_unchanged": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        key = predecessor._materialized_key(before)
        digest = hashlib.sha256(key).hexdigest()
        predecessor.validate_p340_runtime(before, auth_key_sha256=digest)
        expected = transform_runtime_include(before, key)
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.40 input differs: {exc}") from exc
    if after != expected:
        raise RuntimeIdentityError("P3.41 delta exceeds host-first OPEN and run marker")
    result = validate_p341_runtime(after, auth_key_sha256=auth_key_sha256 or digest)
    return result | {
        "changed_anchors": [
            "p341_host_first_open_order",
            "p341_host_first_banner_stage_order",
            "p341_fixed_command_identity_only",
        ],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": dict(predecessor.validate_p340_runtime(before, auth_key_sha256=digest)),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = auth_key_sha256(auth_key)
    try:
        predecessor.validate_p340_runtime(value, auth_key_sha256=digest)
        old = predecessor.materialize_helper(auth_key)
        if value.count(old) != 1:
            raise RuntimeIdentityError("P3.40 helper occurrence differs")
        result = value.replace(old, materialize_helper(auth_key), 1)
        if result.count(predecessor.P340_ENTRY) != 1:
            raise RuntimeIdentityError("P3.40 entry occurrence differs")
        result = result.replace(predecessor.P340_ENTRY, P341_ENTRY, 1)
        validate_p341_runtime(result, auth_key_sha256=digest)
        return result
    except RuntimeIdentityError:
        raise
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.40 input differs: {exc}") from exc


def transform_artifacts(source: Mapping[str, bytes], auth_key: bytes) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise RuntimeIdentityError("P3.40 runtime input is missing")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise RuntimeIdentityError("P3.41 source delta differs")
    return result


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise RuntimeIdentityError("P3.40 runtime source identity differs")
    if identity(HOST_FIRST_SOURCE.read_bytes()) != HOST_FIRST_SOURCE_IDENTITY:
        raise RuntimeIdentityError("host-first OPEN helper source identity differs")
    if predecessor.OPEN_READ_BRANCHES != {
        0: "header-read-errno", 1: "header-grammar", 2: "body-read-errno",
        3: "crc", 4: "open-semantic",
    }:
        raise RuntimeIdentityError("P3.40 branch table differs")
    if predecessor.OPEN_HEADER_WORD_STAGES != (4, 5, 6, 7) or predecessor.OPEN_HEADER_SIZE != 16:
        raise RuntimeIdentityError("P3.40 header capture geometry differs")
    # Exercise both transforms on the pinned P340 source with the public test
    # key only when a caller asks for the full receipt; no private key is read.
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "host_first_source": dict(HOST_FIRST_SOURCE_IDENTITY),
        "predecessor_run_id": P340_PREDECESSOR_RUN_ID_HEX,
        "run_id_hex": P341_RUN_ID_HEX,
        "open_read_diagnostic_stage": DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "open_read_branch_ordinals": dict(OPEN_READ_BRANCHES),
        "open_read_branch_count": len(OPEN_READ_BRANCHES),
        "open_header_word_stages": OPEN_HEADER_WORD_STAGES,
        "open_header_size": OPEN_HEADER_SIZE,
        "open_header_capture_on": ["header-grammar", "open-semantic"],
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
        "successful_wire_exchange_unchanged": False,
        "wire_frames_unchanged": True,
        "authentication_unchanged": True,
        "catalog_unchanged": True,
        "runtime_order_changed": True,
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
        "AUTH_KEY_PLACEHOLDER", "AUTH_KEY_SCHEMA", "AUTH_KEY_SIZE", "CONTRACT_ID",
        "DEFAULT_COMMANDS", "DEVICE_BANNER", "HOST_FIRST_SOURCE", "HOST_FIRST_SOURCE_IDENTITY",
        "OPEN_HEADER_SIZE", "OPEN_HEADER_WORD_STAGES", "OPEN_READ_BRANCHES",
        "P340_COMMAND", "P340_PREDECESSOR_RUN_ID", "P340_PREDECESSOR_RUN_ID_HEX",
        "P341_ARTIFACT_SOURCE", "P341_COMMAND", "P341_DEFAULT_COMMANDS", "P341_ENTRY",
        "P341_HELPER", "P341_HELPER_TEMPLATE", "P341_RUN_ID", "P341_RUN_ID_HEX",
        "RUNTIME_KEY", "SCHEMA", "SOURCE", "SOURCE_IDENTITY", "TARGET", "audit_binding",
        "auth_key_sha256", "classify_open_read_branch", "classify_open_read_diagnostic",
        "identity", "materialize_helper", "transform_artifacts", "transform_runtime_include",
        "validate_p341_runtime", "validate_transform",
    }
    | {
        f"{prefix}_RUN_ID{suffix}"
        for prefix in (
            "P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336",
            "P337", "P338", "P339", "P340",
        )
        for suffix in ("", "_HEX")
    }
)
