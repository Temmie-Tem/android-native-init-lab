#!/usr/bin/env python3
"""Host-only P3.38 first-OPEN read branch diagnostic transform.

P3.38 carries the exact P3.37 authenticated resident exchange and changes
only the first OPEN read.  The device-side ``p328_read_frame`` receives an
optional diagnostic sink for that one call; the sink records one of four
bounded branch ordinals (header read errno, header validation, body read
errno, or CRC).  Every original errno/EPROTO return is immediate and is
returned unchanged.  No retry, second OPEN, wait, command, lease, shell, or
permission behavior is added.

This module is a host-only source transform.  It never contacts a device.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Mapping

import s22plus_fyg8_p337_open_read_diag_runtime as predecessor


SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {
    "size": 13_499,
    "sha256": "424291646d213a979dc0b5049d72f3ce2c795a71530731cfe7c9730737f1f69b",
}
P337_PREDECESSOR_RUN_ID_HEX = "c337f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P337_PREDECESSOR_RUN_ID = bytes.fromhex(P337_PREDECESSOR_RUN_ID_HEX)
P338_RUN_ID_HEX = "c338f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P338_RUN_ID = bytes.fromhex(P338_RUN_ID_HEX)
# Compatibility labels consumed by the inherited P328 builder seam.  They
# resolve to the fresh P338 bytes; predecessor identities are never accepted.
P328_RUN_ID_HEX = P338_RUN_ID_HEX
P328_RUN_ID = P338_RUN_ID
P337_RUN_ID_HEX = P338_RUN_ID_HEX
P337_RUN_ID = P338_RUN_ID
P336_RUN_ID_HEX = P338_RUN_ID_HEX
P336_RUN_ID = P338_RUN_ID
P335_RUN_ID_HEX = P338_RUN_ID_HEX
P335_RUN_ID = P338_RUN_ID
P334_RUN_ID_HEX = P338_RUN_ID_HEX
P334_RUN_ID = P338_RUN_ID
P333_RUN_ID_HEX = P338_RUN_ID_HEX
P333_RUN_ID = P338_RUN_ID
P332_RUN_ID_HEX = P338_RUN_ID_HEX
P332_RUN_ID = P338_RUN_ID

# Exact four-way ordinal carried in the existing stage-3/type-0x86 code
# field.  The original p328_read_frame return remains the process result.
OPEN_READ_BRANCH_HEADER_READ_ERRNO = 0
OPEN_READ_BRANCH_HEADER_VALIDATION = 1
OPEN_READ_BRANCH_BODY_READ_ERRNO = 2
OPEN_READ_BRANCH_CRC = 3
OPEN_READ_BRANCH_MIN = OPEN_READ_BRANCH_HEADER_READ_ERRNO
OPEN_READ_BRANCH_MAX = OPEN_READ_BRANCH_CRC
# Short aliases make the source receipt and host decoder unambiguous while
# preserving the long names used by audit/reporting code.
OPEN_READ_BRANCH_HEADER_READ = OPEN_READ_BRANCH_HEADER_READ_ERRNO
OPEN_READ_BRANCH_BODY_READ = OPEN_READ_BRANCH_BODY_READ_ERRNO
OPEN_READ_BRANCHES = {
    OPEN_READ_BRANCH_HEADER_READ_ERRNO: "header-read-errno",
    OPEN_READ_BRANCH_HEADER_VALIDATION: "header-validation",
    OPEN_READ_BRANCH_BODY_READ_ERRNO: "body-read-errno",
    OPEN_READ_BRANCH_CRC: "crc",
}

DIAGNOSTIC_STAGE_CONSOLE_ENTER = predecessor.DIAGNOSTIC_STAGE_CONSOLE_ENTER
DIAGNOSTIC_STAGE_OPEN_PARSED = predecessor.DIAGNOSTIC_STAGE_OPEN_PARSED
DIAGNOSTIC_STAGE_RNG = predecessor.DIAGNOSTIC_STAGE_RNG
DIAGNOSTIC_STAGE_OPEN_READ_RESULT = predecessor.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
DIAGNOSTIC_FRAME_TYPE = predecessor.DIAGNOSTIC_FRAME_TYPE
P338_DIAG_OPEN_READ_BRANCH = 3


class P338RuntimeError(ValueError):
    """The exact P3.37 predecessor or P3.38 branch transform differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
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
        raise P338RuntimeError("P3.37 runtime source is unavailable") from exc
    if (
        direct != direct.resolve(strict=True)
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or identity(payload) != SOURCE_IDENTITY
        or predecessor.P337_RUN_ID_HEX != P337_PREDECESSOR_RUN_ID_HEX
        or predecessor.DIAGNOSTIC_STAGE_OPEN_READ_RESULT != 3
    ):
        raise P338RuntimeError("P3.37 runtime binding differs")


_check_predecessor()


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


_P337_COMMAND = f"/bin/busybox echo P328-NONCE {P337_PREDECESSOR_RUN_ID_HEX}".encode(
    "ascii"
)
_P338_COMMAND = f"/bin/busybox echo P328-NONCE {P338_RUN_ID_HEX}".encode("ascii")
_P337_COMMAND_MARKER = _c_string(_P337_COMMAND)
_P338_COMMAND_MARKER = _c_string(_P338_COMMAND)

# P337's first-OPEN prefix is retained solely to prove the successful path
# and to restore the exact predecessor for validation.
_P337_OPEN_START = predecessor.P337_HELPER_TEMPLATE.index(
    b"    long rc = p328_read_frame("
)
_P337_OPEN_END = predecessor.P337_HELPER_TEMPLATE.index(
    b"    uint32_t rng_retries", _P337_OPEN_START
)
_P337_OPEN_PREFIX = predecessor.P337_HELPER_TEMPLATE[_P337_OPEN_START:_P337_OPEN_END]

_DEFINE_OLD = (
    b"#define P337_DIAG_OPEN_READ_RESULT 3U\n"
    b"#define P337_OPEN_READ_VALIDATION_REJECTED 1\n"
)
_DEFINE_NEW = (
    b"#define P338_DIAG_OPEN_READ_BRANCH 3U\n"
    b"#define P338_OPEN_READ_BRANCH_HEADER_READ_ERRNO 0U\n"
    b"#define P338_OPEN_READ_BRANCH_HEADER_VALIDATION 1U\n"
    b"#define P338_OPEN_READ_BRANCH_BODY_READ_ERRNO 2U\n"
    b"#define P338_OPEN_READ_BRANCH_CRC 3U\n"
)

_FRAME_START = predecessor.P337_HELPER_TEMPLATE.index(
    b"static long p328_read_frame("
)
_FRAME_END = predecessor.P337_HELPER_TEMPLATE.index(
    b"\n\nstatic long p328_write_frame", _FRAME_START
)
_FRAME_OLD = predecessor.P337_HELPER_TEMPLATE[_FRAME_START:_FRAME_END]
_FRAME_NEW = b"""static long p328_read_frame(
    int fd, uint8_t *type, uint32_t *sequence,
    uint8_t payload[P328_MAX_PAYLOAD], uint16_t *payload_length,
    uint8_t *open_branch) {
    uint8_t header[P328_HEADER_SIZE];
    if (open_branch != NULL)
        *open_branch = P338_OPEN_READ_BRANCH_HEADER_READ_ERRNO;
    long rc = p328_read_exact(
        fd, header, sizeof(header), P328_INPUT_DEADLINE_SEC);
    if (rc != 0) return rc;
    uint16_t length = p328_load_le16(header + 6U);
    if (open_branch != NULL)
        *open_branch = P338_OPEN_READ_BRANCH_HEADER_VALIDATION;
    if (header[0] != P328_MAGIC_0 || header[1] != P328_MAGIC_1
        || header[2] != P328_MAGIC_2 || header[3] != P328_MAGIC_3
        || header[4] != P328_FRAME_VERSION || length > P328_MAX_PAYLOAD)
        return -P260_EPROTO;
    if (open_branch != NULL)
        *open_branch = P338_OPEN_READ_BRANCH_BODY_READ_ERRNO;
    rc = p328_read_exact(fd, payload, length, P328_INPUT_DEADLINE_SEC);
    if (rc != 0) return rc;
    if (open_branch != NULL)
        *open_branch = P338_OPEN_READ_BRANCH_CRC;
    if (p328_frame_crc(header, payload, length)
        != p328_load_le32(header + 12U)) return -P260_EPROTO;
    *type = header[5];
    *sequence = p328_load_le32(header + 8U);
    *payload_length = length;
    return 0;
}"""

_OPEN_NEW = b"""    uint8_t p338_open_branch =
        P338_OPEN_READ_BRANCH_HEADER_READ_ERRNO;
    long rc = p328_read_frame(
        tty_fd, &type, &sequence, payload, &length, &p338_open_branch);
    if (rc != 0) {
        (void)p330_write_diagnostic(
            tty_fd, P338_DIAG_OPEN_READ_BRANCH, (int32_t)p338_open_branch);
        return rc;
    }
    if (type != P328_FRAME_OPEN || sequence != 0U
        || length != sizeof(p328_run_id_bytes)
        || !p328_constant_time_equal(
            payload, p328_run_id_bytes, sizeof(p328_run_id_bytes))) {
        (void)p330_write_diagnostic(
            tty_fd, P338_DIAG_OPEN_READ_BRANCH,
            P338_OPEN_READ_BRANCH_HEADER_VALIDATION);
        return -P260_EPROTO;
    }
    *open_seen = 1U;

    rc = p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0);
"""


def _derive_helper() -> bytes:
    value = predecessor.P337_HELPER_TEMPLATE
    if (
        value.count(_P337_COMMAND_MARKER) != 1
        or value.count(_P338_COMMAND_MARKER)
        or value.count(_DEFINE_OLD) != 1
        or value.count(_DEFINE_NEW)
        or value.count(_FRAME_OLD) != 1
        or value.count(_FRAME_NEW)
        or value.count(_P337_OPEN_PREFIX) != 1
        or value.count(_OPEN_NEW)
    ):
        raise P338RuntimeError("P3.37 helper anchors differ")
    value = value.replace(_P337_COMMAND_MARKER, _P338_COMMAND_MARKER, 1)
    value = value.replace(_DEFINE_OLD, _DEFINE_NEW, 1)
    value = value.replace(_FRAME_OLD, _FRAME_NEW, 1)
    value = value.replace(_P337_OPEN_PREFIX, _OPEN_NEW, 1)
    # All non-OPEN calls use the unchanged frame reader without a diagnostic
    # sink.  This is an ABI-only addition and does not alter their byte path.
    call = b"        tty_fd, &type, &sequence, payload, &length);"
    replacement = b"        tty_fd, &type, &sequence, payload, &length, NULL);"
    if value.count(call) != 2:
        raise P338RuntimeError("P3.37 non-OPEN frame call count differs")
    value = value.replace(call, replacement)
    return value


P338_HELPER_TEMPLATE = _derive_helper()
P338_HELPER = P338_HELPER_TEMPLATE
P338_DEFAULT_COMMANDS = (
    predecessor.DEFAULT_COMMANDS[0],
    predecessor.DEFAULT_COMMANDS[1],
    _P338_COMMAND,
)
DEFAULT_COMMANDS = P338_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P338_RUN_ID_HEX}\n".encode("ascii")
P338_ENTRY = predecessor.P337_ENTRY
P338_DETAIL_ANCHOR = predecessor.P337_DETAIL_ANCHOR
CONTRACT_ID = "s22plus-fyg8-p338-open-read-branch-runtime-v1"
SCHEMA = CONTRACT_ID
RUNTIME_KEY = predecessor.RUNTIME_KEY
TARGET = predecessor.TARGET
PUBLISHER = predecessor.PUBLISHER
AUTH_KEY_PLACEHOLDER = predecessor.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
P338_ARTIFACT_SOURCE = Path(__file__).resolve()


def materialize_helper(auth_key: bytes) -> bytes:
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P338_HELPER_TEMPLATE.count(marker) != 1:
        raise P338RuntimeError("P3.38 key marker differs")
    try:
        initializer = predecessor._key_initializer(auth_key)  # noqa: SLF001
    except Exception as exc:
        raise P338RuntimeError(str(exc)) from exc
    return P338_HELPER_TEMPLATE.replace(marker, initializer, 1)


def auth_key_sha256(auth_key: bytes) -> str:
    try:
        return predecessor.auth_key_sha256(auth_key)
    except Exception as exc:
        raise P338RuntimeError(str(exc)) from exc


def classify_open_read_branch(stage: int, code: int) -> str:
    if type(stage) is not int or type(code) is not int:
        raise P338RuntimeError("P3.38 diagnostic scalar differs")
    if stage == DIAGNOSTIC_STAGE_OPEN_PARSED and code == 0:
        return "open-accepted"
    if stage != DIAGNOSTIC_STAGE_OPEN_READ_RESULT:
        raise P338RuntimeError("P3.38 diagnostic stage differs")
    try:
        return OPEN_READ_BRANCHES[code]
    except KeyError as exc:
        raise P338RuntimeError("P3.38 branch ordinal differs") from exc


def classify_open_read_diagnostic(stage: int, code: int) -> str:
    """Compatibility spelling for the P337 stage-3 decoder API."""

    return classify_open_read_branch(stage, code)


def validate_p338_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise P338RuntimeError("P3.38 runtime must be bytes")
    try:
        key = predecessor._materialized_key(value)  # noqa: SLF001
    except Exception as exc:
        raise P338RuntimeError(str(exc)) from exc
    current = materialize_helper(key)
    previous = predecessor.materialize_helper(key)
    if value.count(current) != 1 or value.count(previous):
        raise P338RuntimeError("P3.38 runtime anchors differ")
    digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and digest != auth_key_sha256:
        raise P338RuntimeError("P3.38 auth key digest differs")
    # Restore both the command/runtime and the frame-reader ABI to the exact
    # P337 bytes.  The predecessor validator then proves the successful path.
    restored = value.replace(current, previous, 1)
    restored = restored.replace(_FRAME_NEW, _FRAME_OLD, 1)
    restored = restored.replace(_OPEN_NEW, _P337_OPEN_PREFIX, 1)
    restored = restored.replace(
        b"        tty_fd, &type, &sequence, payload, &length, NULL);",
        b"        tty_fd, &type, &sequence, payload, &length);",
    )
    try:
        base = predecessor.validate_p337_runtime(
            restored, auth_key_sha256=digest
        )
    except Exception as exc:
        raise P338RuntimeError(f"P3.37 predecessor differs: {exc}") from exc
    return dict(base) | {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P338_RUN_ID_HEX,
        "default_commands": tuple(DEFAULT_COMMANDS),
        "open_read_diagnostic_stage": DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "open_read_branch_ordinals": dict(OPEN_READ_BRANCHES),
        "open_read_branch_count": len(OPEN_READ_BRANCHES),
        "open_read_success_uses_existing_open_parsed": True,
        "open_read_failure_diagnostic_best_effort": True,
        "successful_wire_exchange_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "console_body_changed": True,
        "original_errno_returned_unchanged": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        key = predecessor._materialized_key(before)  # noqa: SLF001
        base = predecessor.validate_p337_runtime(
            before, auth_key_sha256=hashlib.sha256(key).hexdigest()
        )
    except Exception as exc:
        raise P338RuntimeError(f"P3.37 input differs: {exc}") from exc
    expected = before.replace(
        predecessor.materialize_helper(key), materialize_helper(key), 1
    )
    if after != expected:
        raise P338RuntimeError("P3.38 delta exceeds branch instrumentation")
    result = validate_p338_runtime(after, auth_key_sha256=auth_key_sha256)
    return result | {
        "changed_anchors": [
            "p337_fixed_command_identity",
            "p338_first_open_read_branch_ordinal",
        ],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": dict(base),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = auth_key_sha256(auth_key)
    try:
        predecessor.validate_p337_runtime(value, auth_key_sha256=digest)
    except Exception as exc:
        raise P338RuntimeError(f"P3.37 input differs: {exc}") from exc
    old = predecessor.materialize_helper(auth_key)
    if value.count(old) != 1:
        raise P338RuntimeError("P3.37 helper occurrence differs")
    result = value.replace(old, materialize_helper(auth_key), 1)
    validate_transform(value, result, auth_key_sha256=digest)
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P338RuntimeError("P3.37 runtime input is missing")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise P338RuntimeError("P3.38 source delta differs")
    return result


def audit_binding() -> dict[str, Any]:
    _check_predecessor()
    if len(OPEN_READ_BRANCHES) != 4 or set(OPEN_READ_BRANCHES) != set(range(4)):
        raise P338RuntimeError("P3.38 branch table differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "predecessor_run_id": P337_PREDECESSOR_RUN_ID_HEX,
        "run_id_hex": P338_RUN_ID_HEX,
        "open_read_diagnostic_stage": DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
        "open_read_branch_ordinals": dict(OPEN_READ_BRANCHES),
        "open_read_branch_count": 4,
        "successful_wire_exchange_unchanged": True,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "device_contact": False,
        "live_authorized": False,
    }


def __getattr__(name: str) -> Any:
    """Forward unchanged ABI constants/codecs to the exact P3.37 runtime."""

    try:
        return getattr(predecessor, name)
    except AttributeError as exc:
        raise AttributeError(name) from exc


__all__ = sorted(
    {
        "AUTH_KEY_PLACEHOLDER",
        "AUTH_KEY_SIZE",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "DIAGNOSTIC_FRAME_TYPE",
        "DIAGNOSTIC_STAGE_CONSOLE_ENTER",
        "DIAGNOSTIC_STAGE_OPEN_PARSED",
        "DIAGNOSTIC_STAGE_OPEN_READ_RESULT",
        "DIAGNOSTIC_STAGE_RNG",
        "OPEN_READ_BRANCHES",
        "OPEN_READ_BRANCH_BODY_READ",
        "OPEN_READ_BRANCH_BODY_READ_ERRNO",
        "OPEN_READ_BRANCH_CRC",
        "OPEN_READ_BRANCH_HEADER_READ",
        "OPEN_READ_BRANCH_HEADER_READ_ERRNO",
        "OPEN_READ_BRANCH_HEADER_VALIDATION",
        "OPEN_READ_BRANCH_MAX",
        "OPEN_READ_BRANCH_MIN",
        "P337_PREDECESSOR_RUN_ID",
        "P337_PREDECESSOR_RUN_ID_HEX",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P338_ARTIFACT_SOURCE",
        "P338_DIAG_OPEN_READ_BRANCH",
        "P338_DEFAULT_COMMANDS",
        "P338_DETAIL_ANCHOR",
        "P338_ENTRY",
        "P338_HELPER",
        "P338_HELPER_TEMPLATE",
        "P338_RUN_ID",
        "P338_RUN_ID_HEX",
        "P338RuntimeError",
        "PUBLISHER",
        "RUNTIME_KEY",
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
        "validate_p338_runtime",
        "validate_transform",
    }
)
