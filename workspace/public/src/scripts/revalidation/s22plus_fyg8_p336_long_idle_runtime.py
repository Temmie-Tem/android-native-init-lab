#!/usr/bin/env python3
"""Host-only P3.36 runtime binding for the long-idle resynchronization unit.

P3.36 keeps the authenticated P3.35 device behavior byte-for-byte.  Its only
runtime-source delta is a fresh run identity in the fixed nonce echo used by
the existing three-command tuple.  The P3.36 host observer owns the bounded
long-idle preamble resynchronization; this module never contacts a device.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from collections.abc import Mapping
from typing import Any


SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p335_retained_listener_runtime.py"
)
SOURCE_IDENTITY = {
    "size": 32_035,
    "sha256": "d13ed7fe6fb40f5f68e829369ef75975f53a7796722bde566b2ce7f544ee05e7",
}
P335_PREDECESSOR_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P335_PREDECESSOR_RUN_ID = bytes.fromhex(P335_PREDECESSOR_RUN_ID_HEX)
P336_RUN_ID_HEX = "c336f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P336_RUN_ID = bytes.fromhex(P336_RUN_ID_HEX)


class P336RuntimeError(ValueError):
    """The exact P3.35 predecessor or P3.36 identity delta differs."""


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
        raise P336RuntimeError("P3.35 runtime source is unavailable") from exc
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
        raise P336RuntimeError("P3.35 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p335_runtime_bound_for_p336")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P336RuntimeError("P3.35 runtime source failed to load") from exc
    if getattr(module, "P335_RUN_ID_HEX", None) != P335_PREDECESSOR_RUN_ID_HEX:
        raise P336RuntimeError("P3.35 runtime binding differs")
    return module


_P335 = _load()

# Export the immutable protocol constants from the bound predecessor.  Values
# carrying the run identity are re-pinned below, rather than mutating the
# predecessor module or its source graph.
for _name in getattr(_P335, "__all__", ()):
    if hasattr(_P335, _name):
        globals()[_name] = getattr(_P335, _name)

CONTRACT_ID = "s22plus-fyg8-p336-long-idle-runtime-v1"
SCHEMA = CONTRACT_ID
P335_RUN_ID_HEX = P336_RUN_ID_HEX
P335_RUN_ID = P336_RUN_ID
P334_RUN_ID_HEX = P336_RUN_ID_HEX
P334_RUN_ID = P336_RUN_ID
P333_RUN_ID_HEX = P336_RUN_ID_HEX
P333_RUN_ID = P336_RUN_ID
P332_RUN_ID_HEX = P336_RUN_ID_HEX
P332_RUN_ID = P336_RUN_ID
P328_RUN_ID_HEX = P336_RUN_ID_HEX
P328_RUN_ID = P336_RUN_ID
P336_DEFAULT_COMMANDS = (
    _P335.DEFAULT_COMMANDS[0],
    _P335.DEFAULT_COMMANDS[1],
    f"/bin/busybox echo P328-NONCE {P336_RUN_ID_HEX}".encode("ascii"),
)
DEFAULT_COMMANDS = P336_DEFAULT_COMMANDS
P335_DEFAULT_COMMANDS = P336_DEFAULT_COMMANDS
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P336_RUN_ID_HEX}\n".encode("ascii")
FRAME_BOOT_ID = P335_FRAME_BOOT_ID


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


_PREDECESSOR_COMMAND = (
    f"/bin/busybox echo P328-NONCE {P335_PREDECESSOR_RUN_ID_HEX}".encode(
        "ascii"
    )
)
_P336_COMMAND_MARKER = _c_string(DEFAULT_COMMANDS[2])
_P335_COMMAND_MARKER = _c_string(_PREDECESSOR_COMMAND)
if _P335.P335_HELPER_TEMPLATE.count(_P335_COMMAND_MARKER) != 1:
    raise P336RuntimeError("P3.35 fixed command marker differs")
P335_HELPER_TEMPLATE = _P335.P335_HELPER_TEMPLATE
P336_HELPER_TEMPLATE = P335_HELPER_TEMPLATE.replace(
    _P335_COMMAND_MARKER, _P336_COMMAND_MARKER, 1
)
P336_HELPER = P336_HELPER_TEMPLATE
P335_HELPER = P336_HELPER_TEMPLATE
P334_HELPER_TEMPLATE = P336_HELPER_TEMPLATE
P334_HELPER = P336_HELPER_TEMPLATE
P333_HELPER_TEMPLATE = P336_HELPER_TEMPLATE
P333_HELPER = P336_HELPER_TEMPLATE
P332_HELPER_TEMPLATE = P336_HELPER_TEMPLATE
P332_HELPER = P336_HELPER_TEMPLATE
P330_HELPER_TEMPLATE = P336_HELPER_TEMPLATE
P330_HELPER = P336_HELPER_TEMPLATE
P328_HELPER_TEMPLATE = P336_HELPER_TEMPLATE
P328_HELPER = P336_HELPER_TEMPLATE
P336_ENTRY = _P335.P335_ENTRY
P335_ENTRY = P336_ENTRY
P334_ENTRY = _P335.P334_ENTRY
P336_DETAIL_ANCHOR = _P335.P335_DETAIL_ANCHOR
P335_DETAIL_ANCHOR = P336_DETAIL_ANCHOR
P334_DETAIL_ANCHOR = _P335.P334_DETAIL_ANCHOR


def _key_initializer(auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise P336RuntimeError("auth_key must be exactly 32 bytes")
    return ", ".join(f"0x{byte:02x}U" for byte in auth_key).encode("ascii")


def auth_key_sha256(auth_key: bytes) -> str:
    _key_initializer(auth_key)
    return hashlib.sha256(auth_key).hexdigest()


_AUTH_KEY_DECL_PREFIX = (
    b"static const uint8_t p328_auth_key[P328_AUTH_KEY_SIZE] = { "
)
_AUTH_KEY_DECL_SUFFIX = b" };\n"


def _materialized_key(value: bytes) -> bytes:
    try:
        start = value.index(_AUTH_KEY_DECL_PREFIX) + len(_AUTH_KEY_DECL_PREFIX)
        end = value.index(_AUTH_KEY_DECL_SUFFIX, start)
    except ValueError as exc:
        raise P336RuntimeError("materialized key declaration is missing") from exc
    fields = value[start:end].split(b", ")
    if len(fields) != AUTH_KEY_SIZE:
        raise P336RuntimeError("materialized key size differs")
    result = bytearray()
    for field in fields:
        if not field.startswith(b"0x") or not field.endswith(b"U"):
            raise P336RuntimeError("materialized key literal differs")
        try:
            number = int(field[2:-1], 16)
        except ValueError as exc:
            raise P336RuntimeError("materialized key literal is invalid") from exc
        if not 0 <= number <= 0xFF:
            raise P336RuntimeError("materialized key byte is out of range")
        result.append(number)
    return bytes(result)


def materialize_helper(auth_key: bytes) -> bytes:
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P336_HELPER_TEMPLATE.count(marker) != 1:
        raise P336RuntimeError("key marker multiplicity differs")
    return P336_HELPER_TEMPLATE.replace(marker, _key_initializer(auth_key), 1)


def _validate_p335(value: bytes, *, auth_key_sha256: str | None = None) -> dict[str, Any]:
    try:
        return dict(_P335.validate_p335_runtime(value, auth_key_sha256=auth_key_sha256))
    except Exception as exc:
        raise P336RuntimeError(f"P3.35 predecessor differs: {exc}") from exc


def validate_p336_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise P336RuntimeError("P3.36 runtime must be bytes")
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    helper_prefix, helper_suffix = P336_HELPER_TEMPLATE.split(marker, 1)
    if (
        value.count(PUBLISHER) != 1
        or value.count(P336_ENTRY) != 1
        or value.count(P334_ENTRY) != 0
        or value.count(P336_DETAIL_ANCHOR) != 1
        or value.count(P334_DETAIL_ANCHOR) != 0
        or value.count(helper_prefix) != 1
        or value.count(helper_suffix) != 1
        or value.count(_P336_COMMAND_MARKER) != 1
        or value.count(_P335_COMMAND_MARKER) != 0
    ):
        raise P336RuntimeError("P3.36 runtime anchors differ")
    key = _materialized_key(value)
    key_digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and auth_key_sha256 != key_digest:
        raise P336RuntimeError("P3.36 materialized auth key digest differs")
    # Restoring exactly the predecessor helper/entry/detail must pass the
    # predecessor validator.  This proves the P336 delta did not alter the
    # framing, HMAC, listener, or child-isolation implementation.
    restored = value.replace(materialize_helper(key), _P335.materialize_helper(key), 1)
    restored = restored.replace(P336_ENTRY, _P335.P335_ENTRY, 1).replace(
        P336_DETAIL_ANCHOR, _P335.P335_DETAIL_ANCHOR, 1
    )
    _validate_p335(restored, auth_key_sha256=key_digest)
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P336_RUN_ID_HEX,
        "wire_magic": FRAME_MAGIC.decode("ascii"),
        "frame_version": FRAME_VERSION,
        "frame_header_size": FRAME_HEADER_SIZE,
        "max_frame_payload": MAX_FRAME_PAYLOAD,
        "max_command_size": MAX_COMMAND_SIZE,
        "max_commands": MAX_COMMANDS,
        "command_timeout_sec": COMMAND_TIMEOUT_SEC,
        "max_output_bytes": MAX_OUTPUT_BYTES,
        "command_policy": "fixed_p335_three_commands_v1",
        "default_commands": tuple(DEFAULT_COMMANDS),
        "caller_selected_command": False,
        "auth_key_sha256": key_digest,
        "per_session_random_nonce": True,
        "per_boot_identity": True,
        "per_boot_identity_size": P335_BOOT_ID_SIZE,
        "per_boot_identity_frame": P335_FRAME_BOOT_ID,
        "listener": True,
        "listener_low_duty": True,
        "listener_replays_commands": False,
        "long_idle_host_resync": True,
        "persistent_state": False,
        "interactive_pty": False,
        "stdin_dev_null": True,
        "arbitrary_file_transfer": False,
        "child_kill_and_reap": True,
        "child_session_isolated": True,
        "descendant_group_cleanup": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    predecessor = _validate_p335(before, auth_key_sha256=auth_key_sha256)
    key = _materialized_key(before)
    expected = before.replace(
        _P335.materialize_helper(key), materialize_helper(key), 1
    )
    if after != expected:
        raise P336RuntimeError("P3.36 delta exceeds the fixed command identity")
    result = validate_p336_runtime(after, auth_key_sha256=auth_key_sha256)
    return result | {
        "changed_anchors": ["p335_fixed_command_identity"],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": predecessor,
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    _validate_p335(value)
    key = _key_initializer(auth_key)
    del key
    old_materialized = _P335.materialize_helper(auth_key)
    if value.count(old_materialized) != 1:
        raise P336RuntimeError("P3.35 helper is not materialized with auth_key")
    result = value.replace(old_materialized, materialize_helper(auth_key), 1)
    validate_transform(
        value, result, auth_key_sha256=auth_key_sha256(auth_key)
    )
    return result


def audit_binding() -> dict[str, Any]:
    if (
        _P335.P335_RUN_ID_HEX != P335_PREDECESSOR_RUN_ID_HEX
        or _P335.DEFAULT_COMMANDS[2] != _PREDECESSOR_COMMAND
        or P336_HELPER_TEMPLATE.count(_P336_COMMAND_MARKER) != 1
        or P336_HELPER_TEMPLATE.count(_P335_COMMAND_MARKER) != 0
    ):
        raise P336RuntimeError("P3.35 predecessor binding differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "predecessor_source": dict(SOURCE_IDENTITY),
        "run_id_hex": P336_RUN_ID_HEX,
        "fresh_run_identity": True,
        "device_behavior_reused": True,
        "long_idle_host_resync": True,
        "retry_added": False,
        "command_replay": False,
        "persistent_state": False,
    }


RUNTIME_KEY = getattr(_P335, "RUNTIME_KEY", "init/ramdisk/sbin/init")
TARGET = _P335.TARGET
PUBLISHER = _P335.PUBLISHER
# Re-pin inherited compatibility names after the predecessor's ``__all__``
# projection; the P336 source receipt must name this exact P335 predecessor.
SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p335_retained_listener_runtime.py"
)
SOURCE_IDENTITY = {
    "size": 32_035,
    "sha256": "d13ed7fe6fb40f5f68e829369ef75975f53a7796722bde566b2ce7f544ee05e7",
}
P336_ARTIFACT_SOURCE = Path(__file__).resolve()
P335_ARTIFACT_SOURCE = SOURCE

__all__ = sorted(
    {
        "AUTH_DOMAIN_BOOT_ID",
        "AUTH_DOMAIN_CLOSE",
        "AUTH_DOMAIN_EXEC",
        "AUTH_DOMAIN_OPEN",
        "AUTH_DOMAIN_READY",
        "AUTH_KEY_PLACEHOLDER",
        "AUTH_KEY_SIZE",
        "AUTH_TAG_SIZE",
        "COMMAND_TIMEOUT_SEC",
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "FRAME_AUTH",
        "FRAME_CHALLENGE",
        "FRAME_CLOSE",
        "FRAME_DATA",
        "FRAME_DONE",
        "FRAME_EXEC",
        "FRAME_EXIT",
        "FRAME_MAGIC",
        "FRAME_OPEN",
        "FRAME_READY",
        "FRAME_VERSION",
        "MAX_COMMAND_SIZE",
        "MAX_COMMANDS",
        "MAX_FRAME_PAYLOAD",
        "MAX_OUTPUT_BYTES",
        "NONCE_SIZE",
        "P335_BOOT_ID_SIZE",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P335_BOOT_ID_SEQUENCE",
        "P335_DEFAULT_COMMANDS",
        "P335_DETAIL_ANCHOR",
        "P335_FRAME_BOOT_ID",
        "P335_HELPER",
        "P335_HELPER_TEMPLATE",
        "P335_RUN_ID",
        "P335_RUN_ID_HEX",
        "P336_ARTIFACT_SOURCE",
        "P336_DEFAULT_COMMANDS",
        "P336_ENTRY",
        "P336_HELPER",
        "P336_HELPER_TEMPLATE",
        "P336_RUN_ID",
        "P336_RUN_ID_HEX",
        "P336RuntimeError",
        "P334_ENTRY",
        "P334_DETAIL_ANCHOR",
        "P335_PREDECESSOR_RUN_ID",
        "P335_PREDECESSOR_RUN_ID_HEX",
        "RUNTIME_KEY",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "TARGET",
        "audit_binding",
        "auth_key_sha256",
        "identity",
        "materialize_helper",
        "transform_runtime_include",
        "transform_artifacts",
        "validate_p336_runtime",
        "validate_transform",
    }
)


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P336RuntimeError("P3.35 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise P336RuntimeError("P3.36 source delta differs")
    return result
