#!/usr/bin/env python3
"""P3.37 failure-only diagnostic for the first framed OPEN read.

The successful P3.36 exchange is unchanged: stage 1/code 0 still means that
the exact OPEN was accepted. On either first-OPEN failure branch, P3.37 makes
one best-effort write of the existing type-0x86 frame at stage 3. A negative
code is the bounded ``read_frame`` errno; code 1 means a complete frame was
read but rejected. No retry, timeout, command, or recovery behavior changes.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Mapping

import s22plus_fyg8_p336_long_idle_runtime as predecessor


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 15_052,
    "sha256": "33c943ad80422e63004ac69114d8e7b77ed53c684a611d1effe1c7be1e408e7a",
}
HELPER_IDENTITY = {
    "size": 22_776,
    "sha256": "640b2cb55ab7e04d1d1e3892cf4d6f2d9b991a37564b50de18a34a77458867f2",
}
ENTRY_IDENTITY = {
    "size": 3_158,
    "sha256": "86a94c973815329e7283771861b780a90140515c2df4f491b4eff52cd339caf7",
}
P336_PREDECESSOR_RUN_ID_HEX = "c336f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P336_PREDECESSOR_RUN_ID = bytes.fromhex(P336_PREDECESSOR_RUN_ID_HEX)
P337_RUN_ID_HEX = "c337f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P337_RUN_ID = bytes.fromhex(P337_RUN_ID_HEX)
# Compatibility labels used only by the exact-loaded packaging graph.  Every
# one resolves to the fresh P337 bytes; none accepts a predecessor identity.
P336_RUN_ID_HEX = P337_RUN_ID_HEX
P336_RUN_ID = P337_RUN_ID
P335_RUN_ID_HEX = P337_RUN_ID_HEX
P335_RUN_ID = P337_RUN_ID
P334_RUN_ID_HEX = P337_RUN_ID_HEX
P334_RUN_ID = P337_RUN_ID
P333_RUN_ID_HEX = P337_RUN_ID_HEX
P333_RUN_ID = P337_RUN_ID
P332_RUN_ID_HEX = P337_RUN_ID_HEX
P332_RUN_ID = P337_RUN_ID
P328_RUN_ID_HEX = P337_RUN_ID_HEX
P328_RUN_ID = P337_RUN_ID
DIAGNOSTIC_STAGE_CONSOLE_ENTER = 0
DIAGNOSTIC_STAGE_OPEN_PARSED = 1
DIAGNOSTIC_STAGE_RNG = 2
DIAGNOSTIC_STAGE_OPEN_READ_RESULT = 3
DIAGNOSTIC_FRAME_TYPE = 0x86
OPEN_READ_VALIDATION_REJECTED = 1
OPEN_READ_ERRNO_MIN = -4095
OPEN_READ_ERRNO_MAX = -1


class P337RuntimeError(ValueError):
    pass


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _check_predecessor() -> None:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise P337RuntimeError("P3.36 runtime source is unavailable") from exc
    if (
        direct != direct.resolve(strict=True)
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or identity(payload) != SOURCE_IDENTITY
        or predecessor.P336_RUN_ID_HEX != P336_PREDECESSOR_RUN_ID_HEX
        or identity(predecessor.P336_HELPER_TEMPLATE) != HELPER_IDENTITY
        or identity(predecessor.P336_ENTRY) != ENTRY_IDENTITY
    ):
        raise P337RuntimeError("P3.36 runtime binding differs")


_check_predecessor()


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


_P336_COMMAND = (
    f"/bin/busybox echo P328-NONCE {P336_PREDECESSOR_RUN_ID_HEX}".encode()
)
_P337_COMMAND = f"/bin/busybox echo P328-NONCE {P337_RUN_ID_HEX}".encode()
_P336_COMMAND_MARKER = _c_string(_P336_COMMAND)
_P337_COMMAND_MARKER = _c_string(_P337_COMMAND)
_DEFINE_OLD = b"#define P330_DIAG_RNG 2U\n"
_DEFINE_NEW = (
    _DEFINE_OLD
    + b"#define P337_DIAG_OPEN_READ_RESULT 3U\n"
    + b"#define P337_OPEN_READ_VALIDATION_REJECTED 1\n"
)
_OPEN_OLD = b"""    long rc = p328_read_frame(
        tty_fd, &type, &sequence, payload, &length);
    if (rc != 0) return rc;
    if (type != P328_FRAME_OPEN || sequence != 0U
        || length != sizeof(p328_run_id_bytes)
        || !p328_constant_time_equal(
            payload, p328_run_id_bytes, sizeof(p328_run_id_bytes)))
        return -P260_EPROTO;
    *open_seen = 1U;

    rc = p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0);
    if (rc != 0) return rc;
"""
_OPEN_NEW = b"""    long rc = p328_read_frame(
        tty_fd, &type, &sequence, payload, &length);
    if (rc != 0) {
        int32_t p337_read_code =
            (rc >= -4095 && rc <= -1) ? (int32_t)rc : -EIO;
        (void)p330_write_diagnostic(
            tty_fd, P337_DIAG_OPEN_READ_RESULT, p337_read_code);
        return rc;
    }
    if (type != P328_FRAME_OPEN || sequence != 0U
        || length != sizeof(p328_run_id_bytes)
        || !p328_constant_time_equal(
            payload, p328_run_id_bytes, sizeof(p328_run_id_bytes))) {
        (void)p330_write_diagnostic(
            tty_fd, P337_DIAG_OPEN_READ_RESULT,
            P337_OPEN_READ_VALIDATION_REJECTED);
        return -P260_EPROTO;
    }
    *open_seen = 1U;

    rc = p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0);
    if (rc != 0) return rc;
"""


def _derive_helper() -> bytes:
    value = predecessor.P336_HELPER_TEMPLATE
    if (
        value.count(_P336_COMMAND_MARKER) != 1
        or value.count(_P337_COMMAND_MARKER)
        or value.count(_DEFINE_OLD) != 1
        or value.count(_OPEN_OLD) != 1
        or value.count(_OPEN_NEW)
    ):
        raise P337RuntimeError("P3.36 helper anchors differ")
    return (
        value.replace(_P336_COMMAND_MARKER, _P337_COMMAND_MARKER, 1)
        .replace(_DEFINE_OLD, _DEFINE_NEW, 1)
        .replace(_OPEN_OLD, _OPEN_NEW, 1)
    )


P337_HELPER_TEMPLATE = _derive_helper()
P337_HELPER = P337_HELPER_TEMPLATE
P337_DEFAULT_COMMANDS = (
    predecessor.DEFAULT_COMMANDS[0], predecessor.DEFAULT_COMMANDS[1], _P337_COMMAND
)
DEFAULT_COMMANDS = P337_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P337_RUN_ID_HEX}\n".encode()
P337_ENTRY = predecessor.P336_ENTRY
P337_DETAIL_ANCHOR = predecessor.P336_DETAIL_ANCHOR
CONTRACT_ID = "s22plus-fyg8-p337-open-read-diagnostic-runtime-v1"
SCHEMA = CONTRACT_ID
RUNTIME_KEY = predecessor.RUNTIME_KEY
TARGET = predecessor.TARGET
PUBLISHER = predecessor.PUBLISHER
AUTH_KEY_PLACEHOLDER = predecessor.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
P337_ARTIFACT_SOURCE = Path(__file__).resolve()


def materialize_helper(auth_key: bytes) -> bytes:
    marker = AUTH_KEY_PLACEHOLDER.encode()
    if P337_HELPER_TEMPLATE.count(marker) != 1:
        raise P337RuntimeError("P3.37 key marker differs")
    try:
        initializer = predecessor._key_initializer(auth_key)  # noqa: SLF001
    except Exception as exc:
        raise P337RuntimeError(str(exc)) from exc
    return P337_HELPER_TEMPLATE.replace(marker, initializer, 1)


def auth_key_sha256(auth_key: bytes) -> str:
    try:
        return predecessor.auth_key_sha256(auth_key)
    except Exception as exc:
        raise P337RuntimeError(str(exc)) from exc


def classify_open_read_diagnostic(stage: int, code: int) -> str:
    if type(stage) is not int or type(code) is not int:
        raise P337RuntimeError("P3.37 diagnostic scalar differs")
    if stage == DIAGNOSTIC_STAGE_OPEN_PARSED and code == 0:
        return "open-accepted"
    if stage != DIAGNOSTIC_STAGE_OPEN_READ_RESULT:
        raise P337RuntimeError("P3.37 diagnostic stage differs")
    if code == OPEN_READ_VALIDATION_REJECTED:
        return "open-validation-rejected"
    if OPEN_READ_ERRNO_MIN <= code <= OPEN_READ_ERRNO_MAX:
        return "open-read-error"
    raise P337RuntimeError("P3.37 diagnostic code differs")


def validate_p337_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise P337RuntimeError("P3.37 runtime must be bytes")
    try:
        key = predecessor._materialized_key(value)  # noqa: SLF001
    except Exception as exc:
        raise P337RuntimeError(str(exc)) from exc
    current = materialize_helper(key)
    previous = predecessor.materialize_helper(key)
    if value.count(current) != 1 or value.count(previous):
        raise P337RuntimeError("P3.37 runtime anchors differ")
    digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and digest != auth_key_sha256:
        raise P337RuntimeError("P3.37 auth key digest differs")
    restored = value.replace(current, previous, 1)
    try:
        base = predecessor.validate_p336_runtime(restored, auth_key_sha256=digest)
    except Exception as exc:
        raise P337RuntimeError(f"P3.36 predecessor differs: {exc}") from exc
    return dict(base) | {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P337_RUN_ID_HEX,
        "default_commands": tuple(DEFAULT_COMMANDS),
        "open_read_diagnostic_stage": DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "open_read_validation_rejected_code": OPEN_READ_VALIDATION_REJECTED,
        "open_read_success_uses_existing_open_parsed": True,
        "open_read_failure_diagnostic_best_effort": True,
        "successful_wire_exchange_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "console_body_changed": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        key = predecessor._materialized_key(before)  # noqa: SLF001
        base = predecessor.validate_p336_runtime(
            before, auth_key_sha256=hashlib.sha256(key).hexdigest()
        )
    except Exception as exc:
        raise P337RuntimeError(f"P3.36 input differs: {exc}") from exc
    expected = before.replace(
        predecessor.materialize_helper(key), materialize_helper(key), 1
    )
    if after != expected:
        raise P337RuntimeError("P3.37 delta exceeds one helper replacement")
    result = validate_p337_runtime(after, auth_key_sha256=auth_key_sha256)
    return result | {
        "changed_anchors": [
            "p336_fixed_command_identity",
            "p335_framed_console_open_read_failure_diagnostic",
        ],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": dict(base),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = auth_key_sha256(auth_key)
    try:
        predecessor.validate_p336_runtime(value, auth_key_sha256=digest)
    except Exception as exc:
        raise P337RuntimeError(f"P3.36 input differs: {exc}") from exc
    old = predecessor.materialize_helper(auth_key)
    if value.count(old) != 1:
        raise P337RuntimeError("P3.36 helper occurrence differs")
    result = value.replace(old, materialize_helper(auth_key), 1)
    validate_transform(value, result, auth_key_sha256=digest)
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P337RuntimeError("P3.36 runtime input is missing")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise P337RuntimeError("P3.37 source delta differs")
    return result


def audit_binding() -> dict[str, Any]:
    _check_predecessor()
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "predecessor_run_id": P336_PREDECESSOR_RUN_ID_HEX,
        "run_id_hex": P337_RUN_ID_HEX,
        "open_read_diagnostic_stage": DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "successful_wire_exchange_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "device_contact": False,
        "live_authorized": False,
    }


def __getattr__(name: str) -> Any:
    """Forward unchanged ABI constants/codecs to the exact P3.36 runtime."""
    try:
        return getattr(predecessor, name)
    except AttributeError as exc:
        raise AttributeError(name) from exc


__all__ = sorted({
    "AUTH_KEY_PLACEHOLDER", "AUTH_KEY_SIZE", "CONTRACT_ID", "DEFAULT_COMMANDS",
    "DEVICE_BANNER", "DIAGNOSTIC_FRAME_TYPE", "DIAGNOSTIC_STAGE_CONSOLE_ENTER",
    "DIAGNOSTIC_STAGE_OPEN_PARSED", "DIAGNOSTIC_STAGE_OPEN_READ_RESULT",
    "DIAGNOSTIC_STAGE_RNG", "OPEN_READ_ERRNO_MAX", "OPEN_READ_ERRNO_MIN",
    "OPEN_READ_VALIDATION_REJECTED", "P336_PREDECESSOR_RUN_ID",
    "P336_PREDECESSOR_RUN_ID_HEX", "P337_ARTIFACT_SOURCE",
    "P337_DEFAULT_COMMANDS", "P337_DETAIL_ANCHOR", "P337_ENTRY", "P337_HELPER",
    "P337_HELPER_TEMPLATE", "P337_RUN_ID", "P337_RUN_ID_HEX", "P337RuntimeError",
    "P328_RUN_ID", "P328_RUN_ID_HEX", "P332_RUN_ID", "P332_RUN_ID_HEX",
    "P333_RUN_ID", "P333_RUN_ID_HEX", "P334_RUN_ID", "P334_RUN_ID_HEX",
    "P335_RUN_ID", "P335_RUN_ID_HEX", "P336_RUN_ID", "P336_RUN_ID_HEX",
    "PUBLISHER", "RUNTIME_KEY", "SCHEMA", "SOURCE", "SOURCE_IDENTITY", "TARGET",
    "audit_binding", "auth_key_sha256", "classify_open_read_diagnostic", "identity",
    "materialize_helper", "transform_artifacts", "transform_runtime_include",
    "validate_p337_runtime", "validate_transform",
})
