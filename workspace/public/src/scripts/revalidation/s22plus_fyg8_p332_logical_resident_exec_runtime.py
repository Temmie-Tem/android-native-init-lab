#!/usr/bin/env python3
"""Host-only P3.32 logical-resident two-session runtime transform.

P3.32 is derived from the exact P3.30 authenticated runtime.  Its helper,
S328 framing, three fixed commands, diagnostics, HMAC domains, and child
lifecycle remain byte-for-byte P3.30.  The only generated C-source change is
the publisher entry: one tty descriptor performs two unrolled banner to
``p328_framed_console`` sessions, with the second session gated on a zero
return from the first.  No device is contacted by this module.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
import os
from pathlib import Path
import stat
import types
from typing import Any


SOURCE = Path(__file__).with_name("s22plus_fyg8_p330_auth_exec_runtime.py")
SOURCE_IDENTITY = {
    "size": 8_818,
    "sha256": "c281a19568569195640fa73de72ae62fafca8481e17037934e595e8da6a77e6a",
}
P330_PREDECESSOR_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P332_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_RUN_ID = bytes.fromhex(P332_RUN_ID_HEX)

SESSION_COUNT = 2
SESSION_TRANSITIONS = SESSION_COUNT - 1
LOGICAL_SESSION_TRANSITIONS = SESSION_TRANSITIONS
# There is no physical tty close/open or reconnect.  Keep these names
# explicit so evidence cannot mistake the bounded second session for a
# transport reconnect.
RECONNECT_COUNT = 0
MAX_SESSIONS = SESSION_COUNT
MAX_RECONNECTS = 0
PHYSICAL_REOPEN_COUNT = 0
MAX_PHYSICAL_REOPENS = 0
LOGICAL_RESIDENT = True


class P332RuntimeError(ValueError):
    """The exact P3.30 predecessor or bounded P3.32 delta differs."""


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


def _load() -> types.ModuleType:
    """Load the exact P3.30 source after a stable identity check."""

    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise P332RuntimeError("P3.30 runtime source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != SOURCE_IDENTITY
    ):
        raise P332RuntimeError("P3.30 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p330_runtime_bound_for_p332")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P332RuntimeError("P3.30 runtime source failed to load") from exc
    if getattr(module, "P330_RUN_ID_HEX", None) != P330_PREDECESSOR_RUN_ID_HEX:
        raise P332RuntimeError("P3.30 runtime binding differs")
    return module


_P330 = _load()
for _name in getattr(_P330, "__all__", ()):
    globals()[_name] = getattr(_P330, _name)

CONTRACT_ID = "s22plus-fyg8-p332-logical-resident-runtime-v1"
SCHEMA = CONTRACT_ID
TARGET = _P330.TARGET
RUNTIME_KEY = _P330.RUNTIME_KEY
PUBLISHER = _P330.PUBLISHER

# The helper is deliberately not regenerated.  This preserves every P3.30
# command, diagnostic, framing, HMAC, timeout, and child-lifecycle byte.
P330_HELPER_TEMPLATE = _P330.P330_HELPER_TEMPLATE
P332_HELPER_TEMPLATE = P330_HELPER_TEMPLATE
P330_HELPER = P330_HELPER_TEMPLATE
P332_HELPER = P332_HELPER_TEMPLATE
P328_HELPER_TEMPLATE = P332_HELPER_TEMPLATE
P328_HELPER = P332_HELPER_TEMPLATE

P330_ENTRY = _P330.P328_ENTRY
_ENTRY_TAIL = b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
if P330_ENTRY.count(_ENTRY_TAIL) != 1:
    raise P332RuntimeError("P3.30 publisher entry anchor differs")

# This is intentionally unrolled.  Session two is not entered unless the
# first banner was written and its complete framed-console call returned 0.
P332_ENTRY = (
    b"    long p332_first_session_rc = -EIO;\n"
    b"    struct s22plus_p318_banner_result p332_banner_1 =\n"
    b"        s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p332_banner_1.outcome == S22PLUS_P318_BANNER_WRITTEN)\n"
    b"        p332_first_session_rc = p328_framed_console(tty_fd);\n"
    b"    if (p332_first_session_rc == 0) {\n"
    b"        struct s22plus_p318_banner_result p332_banner_2 =\n"
    b"            s22plus_p318_banner_attempt(tty_fd);\n"
    b"        if (p332_banner_2.outcome == S22PLUS_P318_BANNER_WRITTEN)\n"
    b"            (void)p328_framed_console(tty_fd);\n"
    b"    }\n"
    + _ENTRY_TAIL
)

# Compatibility labels let existing source packagers and observers consume
# the same helper while binding fresh P3.32 identity at their outer layer.
P330_RUN_ID_HEX = P332_RUN_ID_HEX
P330_RUN_ID = P332_RUN_ID
P328_RUN_ID_HEX = P332_RUN_ID_HEX
P328_RUN_ID = P332_RUN_ID
# The materialized P3.30 helper remains untouched.  The host-side fixed
# command policy is the fresh P3.32 proof echo consumed by observers/build
# metadata; its first two commands and P328-NONCE grammar stay unchanged.
P330_DEFAULT_COMMANDS = tuple(_P330.DEFAULT_COMMANDS)
P332_DEFAULT_COMMANDS = (
    P330_DEFAULT_COMMANDS[0],
    P330_DEFAULT_COMMANDS[1],
    f"/bin/busybox echo P328-NONCE {P332_RUN_ID_HEX}".encode("ascii"),
)
DEFAULT_COMMANDS = P332_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P332_RUN_ID_HEX}\n".encode("ascii")

AUTH_KEY_PLACEHOLDER = _P330.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = _P330.AUTH_KEY_SIZE
_AUTH_KEY_DECL_PREFIX = (
    b"static const uint8_t p328_auth_key[P328_AUTH_KEY_SIZE] = { "
)
_AUTH_KEY_DECL_SUFFIX = b" };\n"


def _key_initializer(auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise P332RuntimeError("auth_key must be exactly 32 bytes")
    return ", ".join(f"0x{byte:02x}U" for byte in auth_key).encode("ascii")


def auth_key_sha256(auth_key: bytes) -> str:
    _key_initializer(auth_key)
    return hashlib.sha256(auth_key).hexdigest()


def _materialized_key(value: bytes) -> bytes:
    try:
        start = value.index(_AUTH_KEY_DECL_PREFIX) + len(_AUTH_KEY_DECL_PREFIX)
        end = value.index(_AUTH_KEY_DECL_SUFFIX, start)
    except ValueError as exc:
        raise P332RuntimeError("materialized key declaration is missing") from exc
    fields = value[start:end].split(b", ")
    if len(fields) != AUTH_KEY_SIZE:
        raise P332RuntimeError("materialized key size differs")
    result = bytearray()
    for field in fields:
        if not field.startswith(b"0x") or not field.endswith(b"U"):
            raise P332RuntimeError("materialized key literal differs")
        try:
            number = int(field[2:-1], 16)
        except ValueError as exc:
            raise P332RuntimeError("materialized key literal is invalid") from exc
        if not 0 <= number <= 0xFF:
            raise P332RuntimeError("materialized key byte is out of range")
        result.append(number)
    return bytes(result)


def materialize_helper(auth_key: bytes) -> bytes:
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P332_HELPER_TEMPLATE.count(marker) != 1:
        raise P332RuntimeError("key marker multiplicity differs")
    return P332_HELPER_TEMPLATE.replace(marker, _key_initializer(auth_key), 1)


def _validate_p330_predecessor(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise P332RuntimeError("P3.30 predecessor must be bytes")
    try:
        result = dict(
            _P330.validate_p330_runtime(value, auth_key_sha256=auth_key_sha256)
        )
    except Exception as exc:
        raise P332RuntimeError(f"P3.30 predecessor differs: {exc}") from exc
    if value.count(P330_ENTRY) != 1 or value.count(PUBLISHER) != 1:
        raise P332RuntimeError("P3.30 predecessor entry/publisher differs")
    key = _materialized_key(value)
    if value.count(materialize_helper(key)) != 1:
        raise P332RuntimeError("P3.30 helper bytes differ")
    return result


def _validate_restored_p330(value: bytes, *, auth_key_sha256: str | None = None) -> None:
    restored = value.replace(P332_ENTRY, P330_ENTRY, 1)
    try:
        _validate_p330_predecessor(restored, auth_key_sha256=auth_key_sha256)
    except Exception as exc:
        raise P332RuntimeError(f"P3.30 helper/diagnostics differ: {exc}") from exc


def validate_p332_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise P332RuntimeError("P3.32 runtime must be bytes")
    if (
        value.count(PUBLISHER) != 1
        or value.count(P332_HELPER_TEMPLATE.split(AUTH_KEY_PLACEHOLDER.encode("ascii"), 1)[0]) != 1
        or value.count(P332_ENTRY) != 1
        or value.count(P330_ENTRY) != 0
    ):
        raise P332RuntimeError("P3.32 runtime anchors differ")
    helper_offset = value.index(P332_HELPER_TEMPLATE.split(AUTH_KEY_PLACEHOLDER.encode("ascii"), 1)[0])
    publisher_offset = value.index(PUBLISHER)
    entry_offset = value.index(P332_ENTRY, publisher_offset)
    carrier = b"s22plus_max77705_p319_stock_encode"
    try:
        carrier_offset = value.index(carrier, entry_offset)
    except ValueError as exc:
        raise P332RuntimeError("P3.32 Carrier anchor is missing") from exc
    if not helper_offset < publisher_offset < entry_offset < carrier_offset:
        raise P332RuntimeError("P3.32 helper/entry/Carrier order differs")

    key = _materialized_key(value)
    key_digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and auth_key_sha256 != key_digest:
        raise P332RuntimeError("P3.32 materialized auth key digest differs")

    required = (
        b"P330_FRAME_DIAGNOSTIC 0x86U",
        b"P330_DIAG_OPEN_PARSED 1U",
        b"P330_DIAG_RNG 2U",
        b"P330_RNG_EAGAIN_RETRY_LIMIT 64U",
        b"p328_getrandom_nonce",
        b"P328_FRAME_CHALLENGE 0x85U",
        b"p328_constant_time_equal",
        b"p328_auth_domain_open",
        b"p328_auth_domain_ready",
        b"p328_auth_domain_exec",
        b"p328_auth_domain_close",
        b"sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK)",
        b"sys_kill(pid, SIGKILL)",
        b"sys_kill(-pid, SIGKILL)",
        b"sys_wait4(pid, status, WNOHANG)",
        b"sys_wait4(-pid, &status, WNOHANG)",
        b"p328_setsid() < 0",
        b'"/bin/busybox", (char *)"ash", (char *)"-c"',
        b"P328_MAX_COMMANDS 16U",
        b"P328_COMMAND_TIMEOUT_SEC 15LL",
        b"P328_MAX_OUTPUT 131072U",
    )
    if any(anchor not in value for anchor in required) or b"ash -i" in value:
        raise P332RuntimeError("P3.32 P3.30 helper contract differs")

    entry = P332_ENTRY
    if (
        entry.count(b"s22plus_p318_banner_attempt(tty_fd);") != SESSION_COUNT
        or entry.count(b"p328_framed_console(tty_fd)") != SESSION_COUNT
        or b"for (" in entry
        or b"while (" in entry
        or b"close(" in entry
        or b"open(" in entry
        or b"TCSETS" in entry
    ):
        raise P332RuntimeError("P3.32 unrolled same-fd entry contract differs")
    if entry.count(b"if (p332_first_session_rc == 0) {") != 1:
        raise P332RuntimeError("P3.32 second-session gate differs")

    # Replacing only the new entry must recover the exact, independently
    # validated P3.30 runtime.  This catches helper, HMAC, and diagnostics
    # drift without permitting a broad semantic rewrite.
    _validate_restored_p330(value, auth_key_sha256=auth_key_sha256)
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P332_RUN_ID_HEX,
        "wire_magic": _P330.FRAME_MAGIC.decode("ascii"),
        "frame_version": _P330.FRAME_VERSION,
        "frame_header_size": _P330.FRAME_HEADER_SIZE,
        "max_frame_payload": _P330.MAX_FRAME_PAYLOAD,
        "max_command_size": _P330.MAX_COMMAND_SIZE,
        "max_commands": _P330.MAX_COMMANDS,
        "command_timeout_sec": _P330.COMMAND_TIMEOUT_SEC,
        "max_output_bytes": _P330.MAX_OUTPUT_BYTES,
        "command_policy": "fixed_p330_commands_v1",
        "default_commands": tuple(DEFAULT_COMMANDS),
        "caller_selected_command": False,
        "auth_key_sha256": key_digest,
        "auth_algorithm": "hmac-sha256",
        "per_session_random_nonce": True,
        "session_count": SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT,
        "session_transitions": SESSION_TRANSITIONS,
        "logical_session_transitions": LOGICAL_SESSION_TRANSITIONS,
        "max_sessions": MAX_SESSIONS,
        "max_reconnects": MAX_RECONNECTS,
        "physical_reopen_count": PHYSICAL_REOPEN_COUNT,
        "max_physical_reopens": MAX_PHYSICAL_REOPENS,
        "same_tty_fd": True,
        "unrolled_sessions": True,
        "session_loop": False,
        "close_open": False,
        "tty_reconfiguration": False,
        "interactive_pty": False,
        "stdin_dev_null": True,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
        "child_kill_and_reap": True,
        "child_session_isolated": True,
        "descendant_group_cleanup": True,
        "carrier_path_retained": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    predecessor = _validate_p330_predecessor(
        before, auth_key_sha256=auth_key_sha256
    )
    expected = before.replace(P330_ENTRY, P332_ENTRY, 1)
    if after != expected:
        raise P332RuntimeError("P3.32 delta exceeds the P3.30 publisher entry")
    result = validate_p332_runtime(after, auth_key_sha256=auth_key_sha256)
    return result | {
        "changed_anchors": ["p330_publisher_entry"],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": predecessor,
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    _validate_p330_predecessor(value)
    # Validate the key before the exact source delta so no partial artifact is
    # ever returned for an invalid private input.
    _key_initializer(auth_key)
    if value.count(materialize_helper(auth_key)) != 1:
        raise P332RuntimeError("P3.30 helper is not materialized with auth_key")
    result = value.replace(P330_ENTRY, P332_ENTRY, 1)
    validate_transform(value, result, auth_key_sha256=auth_key_sha256(auth_key))
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P332RuntimeError("P3.30 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    changed = {key for key in result if result[key] != source[key]}
    if changed != {RUNTIME_KEY}:
        raise P332RuntimeError("P3.32 source delta differs")
    return result


P332_DEFAULT_COMMANDS = DEFAULT_COMMANDS
P328_ENTRY = P332_ENTRY
P330_RUNTIME_SOURCE = SOURCE
P330_RUNTIME_SOURCE_IDENTITY = SOURCE_IDENTITY

__all__ = sorted(
    set(getattr(_P330, "__all__", ()))
    | {
        "AUTH_KEY_PLACEHOLDER",
        "AUTH_KEY_SIZE",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "LOGICAL_RESIDENT",
        "MAX_RECONNECTS",
        "MAX_SESSIONS",
        "MAX_PHYSICAL_REOPENS",
        "P328_ENTRY",
        "P328_HELPER",
        "P328_HELPER_TEMPLATE",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P330_DEFAULT_COMMANDS",
        "P330_ENTRY",
        "P330_HELPER",
        "P330_HELPER_TEMPLATE",
        "P330_PREDECESSOR_RUN_ID_HEX",
        "P330_RUN_ID",
        "P330_RUN_ID_HEX",
        "P330_RUNTIME_SOURCE",
        "P330_RUNTIME_SOURCE_IDENTITY",
        "P332_DEFAULT_COMMANDS",
        "P332_ENTRY",
        "P332_HELPER",
        "P332_HELPER_TEMPLATE",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P332RuntimeError",
        "PHYSICAL_REOPEN_COUNT",
        "RECONNECT_COUNT",
        "RUNTIME_KEY",
        "SCHEMA",
        "SESSION_COUNT",
        "SESSION_TRANSITIONS",
        "LOGICAL_SESSION_TRANSITIONS",
        "SOURCE",
        "SOURCE_IDENTITY",
        "TARGET",
        "auth_key_sha256",
        "identity",
        "materialize_helper",
        "transform_artifacts",
        "transform_runtime_include",
        "validate_p332_runtime",
        "validate_transform",
    }
)
