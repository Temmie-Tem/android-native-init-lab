#!/usr/bin/env python3
"""Host-only P3.31 bounded resident-session runtime transform.

P3.31 keeps the P3.30 S328 authenticated framing, HMAC domains, per-session
kernel-random challenge, pre-auth diagnostics, command process limits, and
P324/P325/P329 source lane.  The only runtime delta is a two-session resident
loop.  Each session accepts exactly one fixed heartbeat command, closes with a
DONE frame, and the loop then admits at most one reconnect.  No state is
persisted and the helper has no file-transfer or PTY path.

This module only transforms host-side source bytes.  It never contacts a
device and does not grant live or candidate authority.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
import os
import stat
import types
from typing import Any


SOURCE = Path(__file__).with_name("s22plus_fyg8_p330_auth_exec_runtime.py")
SOURCE_IDENTITY = {
    "size": 8_818,
    "sha256": "c281a19568569195640fa73de72ae62fafca8481e17037934e595e8da6a77e6a",
}

P330_PREDECESSOR_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P331_RUN_ID_HEX = "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P331_RUN_ID = bytes.fromhex(P331_RUN_ID_HEX)

# These are deliberately constants, rather than caller-selectable limits.
MAX_SESSIONS = 2
MAX_RECONNECTS = 1
RESIDENT_SESSION_TIMEOUT_SEC = 30.0
HEARTBEAT_COMMAND = (
    f"/bin/busybox echo P331-HEARTBEAT {P331_RUN_ID_HEX}".encode("ascii")
)
HEARTBEAT_OUTPUT = f"P331-HEARTBEAT {P331_RUN_ID_HEX}\n".encode("ascii")
# Friendly aliases keep the single fixed status operation explicit to callers.
STATUS_COMMAND = HEARTBEAT_COMMAND
STATUS_OUTPUT = HEARTBEAT_OUTPUT
RESIDENT_COMMAND = HEARTBEAT_COMMAND

CONTRACT_ID = "s22plus-fyg8-p331-resident-runtime-v1"
SCHEMA = CONTRACT_ID


class P331RuntimeError(ValueError):
    """The exact P3.30 predecessor or bounded P3.31 transform differs."""


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
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise P331RuntimeError("P3.30 runtime source is unavailable") from exc
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
        raise P331RuntimeError("P3.30 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p330_runtime_bound_for_p331")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P331RuntimeError("P3.30 runtime source failed to load") from exc
    if getattr(module, "P330_RUN_ID_HEX", None) != P330_PREDECESSOR_RUN_ID_HEX:
        raise P331RuntimeError("P3.30 runtime binding differs")
    return module


def _replace_function(value: str, name: str, replacement: str) -> str:
    start = value.index(f"static int {name}")
    end = value.index("\n}\n", start) + 3
    return value[:start] + replacement + value[end:]


def _c_string(value: bytes) -> str:
    return "".join(f"\\x{byte:02x}" for byte in value)


def _derive_helper_template(predecessor: bytes) -> bytes:
    value = predecessor.decode("ascii")
    heartbeat = _c_string(HEARTBEAT_COMMAND)
    command_validator = f'''static const char p331_heartbeat_command[] =
    "{heartbeat}";

static int p328_command_valid(
    const uint8_t *command, uint16_t length) {{
    return command != NULL
        && length == sizeof(p331_heartbeat_command) - 1U
        && p260_bytes_equal(
            (const char *)command, p331_heartbeat_command,
            sizeof(p331_heartbeat_command) - 1U);
}}'''
    try:
        value = _replace_function(value, "p328_command_valid", command_validator)
    except ValueError as exc:
        raise P331RuntimeError("P3.30 command validator anchor differs") from exc

    # A resident session is exactly one fixed status request.  The inherited
    # P3.30 parser still retains its frame-size and output bounds.
    if value.count("handled < P328_MAX_COMMANDS") != 1:
        raise P331RuntimeError("P3.30 command-count anchor differs")
    value = value.replace(
        "handled < P328_MAX_COMMANDS", "handled < P331_COMMANDS_PER_SESSION", 1
    )
    if value.count("handled != 0U") != 1:
        raise P331RuntimeError("P3.30 close-count anchor differs")
    value = value.replace(
        "handled != 0U", "handled == P331_COMMANDS_PER_SESSION", 1
    )

    marker = "#define P330_RNG_EAGAIN_RETRY_LIMIT 64U\n"
    if value.count(marker) != 1:
        raise P331RuntimeError("P3.30 diagnostic constants anchor differs")
    value = value.replace(
        marker,
        marker
        + "#define P331_COMMANDS_PER_SESSION 1U\n"
        + f"#define P331_MAX_SESSIONS {MAX_SESSIONS}U\n"
        + f"#define P331_MAX_RECONNECTS {MAX_RECONNECTS}U\n",
        1,
    )

    # Keep p328_framed_console byte-for-byte except for the fixed operation
    # above.  Calling it once per loop gives every session a fresh nonce and
    # reruns the unchanged OPEN/diagnostic/CHALLENGE/HMAC exchange.
    resident = f'''
static long p331_resident_loop(int tty_fd) {{
    uint32_t sessions = 0U;
    uint32_t reconnects = 0U;
    for (;;) {{
        if (sessions >= P331_MAX_SESSIONS
            || reconnects > P331_MAX_RECONNECTS)
            return 0;
        struct s22plus_p318_banner_result p331_banner =
            s22plus_p318_banner_attempt(tty_fd);
        if (p331_banner.outcome != S22PLUS_P318_BANNER_WRITTEN)
            return -EIO;
        long rc = p328_framed_console(tty_fd);
        if (rc != 0) return rc;
        ++sessions;
        if (sessions >= P331_MAX_SESSIONS)
            return 0;
        if (reconnects >= P331_MAX_RECONNECTS)
            return 0;
        ++reconnects;
    }}
}}
'''
    if not value.endswith("\n"):
        raise P331RuntimeError("P3.30 helper termination differs")
    return (value + resident).encode("ascii")


_P330 = _load()
# Export predecessor protocol names before defining P3.31 wrappers.  This
# keeps the delegated observer/runtime compatibility surface while ensuring
# the local transform functions below are not overwritten by the loop.
for _name in getattr(_P330, "__all__", ()):
    globals()[_name] = getattr(_P330, _name)
CONTRACT_ID = "s22plus-fyg8-p331-resident-runtime-v1"
SCHEMA = CONTRACT_ID
P330_HELPER_TEMPLATE = _P330.P330_HELPER_TEMPLATE
P331_HELPER_TEMPLATE = _derive_helper_template(P330_HELPER_TEMPLATE)

# P330 uses the P328 C symbol and entry anchor for compatibility.  P331 owns
# banner construction inside its bounded loop so every session gets exactly
# one banner and the entry does not emit a duplicate outer banner.
P330_ENTRY = _P330.P328_ENTRY
_ENTRY_TAIL = b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
if P330_ENTRY.count(_ENTRY_TAIL) != 1:
    raise P331RuntimeError("P3.30 entry anchor differs")
P331_ENTRY = b"    (void)p331_resident_loop(tty_fd);\n" + _ENTRY_TAIL

PUBLISHER = _P330.PUBLISHER
RUNTIME_KEY = _P330.RUNTIME_KEY
TARGET = _P330.TARGET
AUTH_KEY_PLACEHOLDER = _P330.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = _P330.AUTH_KEY_SIZE
_AUTH_KEY_DECL_PREFIX = b"static const uint8_t p328_auth_key[P328_AUTH_KEY_SIZE] = { "
_AUTH_KEY_DECL_SUFFIX = b" };\n"


def _materialized_key(value: bytes) -> bytes:
    prefix = _AUTH_KEY_DECL_PREFIX
    suffix = _AUTH_KEY_DECL_SUFFIX
    try:
        start = value.index(prefix) + len(prefix)
        end = value.index(suffix, start)
    except ValueError as exc:
        raise P331RuntimeError("P3.31 materialized key declaration is missing") from exc
    fields = value[start:end].split(b", ")
    if len(fields) != AUTH_KEY_SIZE:
        raise P331RuntimeError("P3.31 materialized key size differs")
    result = bytearray()
    for field in fields:
        if not field.startswith(b"0x") or not field.endswith(b"U"):
            raise P331RuntimeError("P3.31 materialized key literal differs")
        try:
            number = int(field[2:-1], 16)
        except ValueError as exc:
            raise P331RuntimeError("P3.31 materialized key literal is invalid") from exc
        if not 0 <= number <= 0xFF:
            raise P331RuntimeError("P3.31 materialized key byte is out of range")
        result.append(number)
    return bytes(result)


def _key_initializer(auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise P331RuntimeError("auth_key must be exactly 32 bytes")
    return ", ".join(f"0x{byte:02x}U" for byte in auth_key).encode("ascii")


def materialize_helper(auth_key: bytes) -> bytes:
    """Return the private C helper with exactly one materialized HMAC key."""

    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P331_HELPER_TEMPLATE.count(marker) != 1:
        raise P331RuntimeError("P3.31 key marker multiplicity differs")
    return P331_HELPER_TEMPLATE.replace(marker, _key_initializer(auth_key), 1)


def _materialize_p330_helper(auth_key: bytes) -> bytes:
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    return P330_HELPER_TEMPLATE.replace(marker, _key_initializer(auth_key), 1)


def _validate_p330_predecessor(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        result = dict(
            _P330.validate_p330_runtime(value, auth_key_sha256=auth_key_sha256)
        )
    except Exception as exc:
        raise P331RuntimeError(f"P3.30 predecessor differs: {exc}") from exc
    if value.count(P330_ENTRY) != 1 or value.count(PUBLISHER) != 1:
        raise P331RuntimeError("P3.30 predecessor entry/publisher differs")
    return result


def validate_p331_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise P331RuntimeError("P3.31 runtime must be bytes")
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    helper_prefix, helper_suffix = P331_HELPER_TEMPLATE.split(marker, 1)
    if (
        value.count(PUBLISHER) != 1
        or value.count(helper_prefix) != 1
        or value.count(helper_suffix) != 1
        or value.count(P331_ENTRY) != 1
        or value.count(P330_ENTRY) != 0
        or _P330.P328_HELPER in value
    ):
        raise P331RuntimeError("P3.31 runtime anchors differ")
    helper_offset = value.index(helper_prefix)
    publisher_offset = value.index(PUBLISHER)
    entry_offset = value.index(P331_ENTRY, publisher_offset)
    carrier = b"s22plus_max77705_p319_stock_encode"
    try:
        carrier_offset = value.index(carrier, entry_offset)
    except ValueError as exc:
        raise P331RuntimeError("P3.31 Carrier anchor is missing") from exc
    if not helper_offset < publisher_offset < entry_offset < carrier_offset:
        raise P331RuntimeError("P3.31 helper/entry/Carrier order differs")
    key = _materialized_key(value)
    key_digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and auth_key_sha256 != key_digest:
        raise P331RuntimeError("P3.31 materialized auth key digest differs")
    required = (
        b"P330_FRAME_DIAGNOSTIC 0x86U",
        b"P330_DIAG_OPEN_PARSED 1U",
        b"P330_DIAG_RNG 2U",
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
        b"P331_COMMANDS_PER_SESSION 1U",
        b"P331_MAX_SESSIONS 2U",
        b"P331_MAX_RECONNECTS 1U",
        b"p331_heartbeat_command",
        b"p331_resident_loop",
        b"++reconnects;",
        b"s22plus_p318_banner_attempt(tty_fd);",
        b"p331_banner.outcome != S22PLUS_P318_BANNER_WRITTEN",
    )
    if any(anchor not in value for anchor in required) or b"ash -i" in value:
        raise P331RuntimeError("P3.31 resident runtime contract differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P331_RUN_ID_HEX,
        "wire_magic": _P330.FRAME_MAGIC.decode("ascii"),
        "frame_version": _P330.FRAME_VERSION,
        "frame_header_size": _P330.FRAME_HEADER_SIZE,
        "max_frame_payload": _P330.MAX_FRAME_PAYLOAD,
        "max_command_size": _P330.MAX_COMMAND_SIZE,
        "max_commands": _P330.MAX_COMMANDS,
        "commands_per_session": 1,
        "command_timeout_sec": _P330.COMMAND_TIMEOUT_SEC,
        "max_output_bytes": _P330.MAX_OUTPUT_BYTES,
        "command_policy": "fixed_heartbeat_status_v1",
        "heartbeat_command": identity(HEARTBEAT_COMMAND),
        "caller_selected_command": False,
        "auth_key_sha256": key_digest,
        "auth_algorithm": "hmac-sha256",
        "per_session_random_nonce": True,
        "session_cap": MAX_SESSIONS,
        "reconnect_cap": MAX_RECONNECTS,
        "clean_close_required": True,
        "banner_scope": "resident_loop_per_session",
        "banner_attempts_per_loop": 1,
        "child_kill_and_reap": True,
        "child_session_isolated": True,
        "descendant_group_cleanup": True,
        "interactive_pty": False,
        "stdin_dev_null": True,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
        "bounded_resident_session": True,
        "resident_service": False,
        "carrier_path_retained": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    predecessor = _validate_p330_predecessor(
        before, auth_key_sha256=auth_key_sha256
    )
    key = _materialized_key(before)
    old_helper = _materialize_p330_helper(key)
    expected = before.replace(
        old_helper, materialize_helper(key), 1
    ).replace(P330_ENTRY, P331_ENTRY, 1)
    if after != expected:
        raise P331RuntimeError("P3.31 delta exceeds the P3.30 helper/entry anchors")
    result = validate_p331_runtime(after, auth_key_sha256=auth_key_sha256)
    return result | {
        "changed_anchors": ["p330_resident_helper", "p330_resident_entry"],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": predecessor,
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    _validate_p330_predecessor(value)
    # Validate before transformation so an invalid key cannot produce a
    # partially materialized artifact.
    _key_initializer(auth_key)
    old_helper = _materialize_p330_helper(auth_key)
    result = value.replace(old_helper, materialize_helper(auth_key), 1)
    result = result.replace(P330_ENTRY, P331_ENTRY, 1)
    validate_transform(
        value,
        result,
        auth_key_sha256=hashlib.sha256(auth_key).hexdigest(),
    )
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P331RuntimeError("P3.30 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    changed = {key for key in result if result[key] != source[key]}
    if changed != {RUNTIME_KEY}:
        raise P331RuntimeError("P3.31 source delta differs")
    return result


# Compatibility labels are kept so the delegated P330 observer can use the
# exact same HMAC/framing implementation with this fresh run identity.
P330_RUN_ID_HEX = P331_RUN_ID_HEX
P330_RUN_ID = P331_RUN_ID
P328_RUN_ID_HEX = P331_RUN_ID_HEX
P328_RUN_ID = P331_RUN_ID
P329_RUN_ID_HEX = getattr(_P330, "P329_RUN_ID_HEX", "")
P329_RUN_ID = getattr(_P330, "P329_RUN_ID", b"")
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P331_RUN_ID_HEX}\n".encode("ascii")
DEFAULT_COMMANDS = (HEARTBEAT_COMMAND,)
P328_HELPER_TEMPLATE = P331_HELPER_TEMPLATE
P328_HELPER = P331_HELPER_TEMPLATE
P331_HELPER = P331_HELPER_TEMPLATE
P328_ENTRY = P331_ENTRY


def auth_key_sha256(auth_key: bytes) -> str:
    _key_initializer(auth_key)
    return hashlib.sha256(auth_key).hexdigest()


__all__ = sorted(
    set(getattr(_P330, "__all__", ()))
    | {
        "AUTH_KEY_PLACEHOLDER",
        "AUTH_KEY_SIZE",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "HEARTBEAT_COMMAND",
        "HEARTBEAT_OUTPUT",
        "MAX_RECONNECTS",
        "MAX_SESSIONS",
        "P331_ENTRY",
        "P331_HELPER",
        "P331_HELPER_TEMPLATE",
        "P331_RUN_ID",
        "P331_RUN_ID_HEX",
        "P331RuntimeError",
        "RESIDENT_COMMAND",
        "RESIDENT_SESSION_TIMEOUT_SEC",
        "RUNTIME_KEY",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STATUS_COMMAND",
        "STATUS_OUTPUT",
        "TARGET",
        "auth_key_sha256",
        "identity",
        "materialize_helper",
        "transform_artifacts",
        "transform_runtime_include",
        "validate_p331_runtime",
        "validate_transform",
    }
)
