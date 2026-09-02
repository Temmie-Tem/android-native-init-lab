#!/usr/bin/env python3
"""Host-only P3.28 authenticated, bounded ACM command-session transform.

P3.28 keeps the P3.27 PID-1 framing and child lifecycle, but separates the
wire protocol with a fresh magic and authenticates every request with a
materialized 32-byte HMAC-SHA256 key.  The key is deliberately absent from
this tracked module: ``transform_artifacts`` accepts it from a private build
input and injects it only into the generated private C source.  This module
contacts no device and grants no live authority.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import s22plus_fyg8_p327_framed_exec_runtime as p327


CONTRACT_ID = "s22plus-fyg8-p328-auth-exec-runtime-v1"
SCHEMA = CONTRACT_ID
TARGET = p327.TARGET
RUNTIME_KEY = p327.RUNTIME_KEY

# This identity is intentionally distinct from every predecessor.  The build
# closure supplies the same bytes as the inherited k_run_id initializer.
P328_RUN_ID_HEX = "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P328_RUN_ID = bytes.fromhex(P328_RUN_ID_HEX)
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P328_RUN_ID_HEX}\n".encode("ascii")

FRAME_MAGIC = b"S328"
FRAME_VERSION = 1
FRAME_OPEN = 1
FRAME_EXEC = 2
FRAME_CLOSE = 3
FRAME_AUTH = 4
FRAME_READY = 0x81
FRAME_DATA = 0x82
FRAME_EXIT = 0x83
FRAME_DONE = 0x84
FRAME_CHALLENGE = 0x85
FRAME_HEADER_SIZE = 16
AUTH_KEY_SIZE = 32
AUTH_TAG_SIZE = 32
NONCE_SIZE = 32
MAX_COMMAND_SIZE = 1023
# An EXEC frame carries the 32-byte tag in addition to the command bound.
MAX_FRAME_PAYLOAD = AUTH_TAG_SIZE + MAX_COMMAND_SIZE
MAX_COMMANDS = 16
COMMAND_TIMEOUT_SEC = 15
MAX_OUTPUT_BYTES = 128 * 1024

AUTH_DOMAIN_OPEN = b"S22PLUS-FYG8-P328-AUTH-OPEN-v1"
AUTH_DOMAIN_READY = b"S22PLUS-FYG8-P328-AUTH-READY-v1"
AUTH_DOMAIN_EXEC = b"S22PLUS-FYG8-P328-AUTH-EXEC-v1"
AUTH_DOMAIN_CLOSE = b"S22PLUS-FYG8-P328-AUTH-CLOSE-v1"

DEFAULT_COMMANDS = (
    b"/bin/busybox id",
    b"/bin/busybox uname -a",
    f"/bin/busybox echo P328-NONCE {P328_RUN_ID_HEX}".encode("ascii"),
)

PUBLISHER = p327.PUBLISHER
P328_ENTRY = p327.P327_ENTRY.replace(b"p327_", b"p328_").replace(
    b"P327", b"P328"
)
AUTH_KEY_PLACEHOLDER = "P328_AUTH_KEY_BYTES"
_AUTH_KEY_DECL_PREFIX = (
    b"static const uint8_t p328_auth_key[P328_AUTH_KEY_SIZE] = { "
)
_AUTH_KEY_DECL_SUFFIX = b" };\n"


def _derive_helper_template() -> bytes:
    """Derive the P3.28 C body from exactly the proved P3.27 helper shape.

    Keeping this mechanical makes the inherited pipe/deadline/reap path easy
    to audit.  The two altered C regions are the command policy and the
    framed-session state machine; the child remains the P3.27 non-PTY
    ``ash -c`` child with its process-group cleanup.
    """

    value = p327.P327_HELPER.decode("ascii")
    value = value.replace("P3.27", "P3.28")
    value = value.replace("P327", "P328")
    value = value.replace("p327", "p328")
    value = value.replace("#define P328_MAGIC_3 0x37U", "#define P328_MAGIC_3 0x38U")
    value = value.replace(
        "#define P328_MAX_PAYLOAD 1024U",
        f"#define P328_MAX_PAYLOAD {MAX_FRAME_PAYLOAD}U",
    )
    value = value.replace(
        "#define P328_MAX_COMMANDS 3U",
        f"#define P328_MAX_COMMANDS {MAX_COMMANDS}U",
    )
    value = value.replace(
        "#define P328_COMMAND_TIMEOUT_SEC 10LL",
        f"#define P328_COMMAND_TIMEOUT_SEC {COMMAND_TIMEOUT_SEC}LL",
    )

    constants_start = value.index("#define p328_run_id k_run_id")
    constants_end = value.index("\n\nstatic uint16_t p328_load_le16", constants_start)
    constants = f'''#define p328_run_id k_run_id
#define P328_AUTH_KEY_SIZE {AUTH_KEY_SIZE}U
#define P328_AUTH_TAG_SIZE {AUTH_TAG_SIZE}U
#define P328_NONCE_SIZE {NONCE_SIZE}U
#define P328_FRAME_AUTH 4U
#define P328_FRAME_CHALLENGE 0x85U
#define P328_NR_GETRANDOM 278
#define P328_GRND_NONBLOCK 1U
static const uint8_t p328_auth_key[P328_AUTH_KEY_SIZE] = {{ {AUTH_KEY_PLACEHOLDER} }};
#define p328_run_id_bytes p328_run_id
static const char p328_auth_domain_open[] = "{AUTH_DOMAIN_OPEN.decode('ascii')}";
static const char p328_auth_domain_ready[] = "{AUTH_DOMAIN_READY.decode('ascii')}";
static const char p328_auth_domain_exec[] = "{AUTH_DOMAIN_EXEC.decode('ascii')}";
static const char p328_auth_domain_close[] = "{AUTH_DOMAIN_CLOSE.decode('ascii')}";

'''
    value = value[:constants_start] + constants + value[constants_end + 2 :]

    crypto = r'''static int p328_constant_time_equal(
    const uint8_t *left, const uint8_t *right, size_t length) {
    uint8_t difference = 0U;
    for (size_t index = 0U; index < length; ++index)
        difference |= (uint8_t)(left[index] ^ right[index]);
    return difference == 0U;
}

static void p328_hmac_message(
    uint8_t digest[P328_AUTH_TAG_SIZE],
    const char *domain, size_t domain_length,
    const uint8_t *run_id, const uint8_t *nonce,
    uint32_t sequence, int include_sequence,
    const uint8_t *command, size_t command_length) {
    struct s22plus_max77705_runtime_sha256 inner_context;
    struct s22plus_max77705_runtime_sha256 outer_context;
    uint8_t inner_digest[P328_AUTH_TAG_SIZE];
    uint8_t inner_pad[64];
    uint8_t outer_pad[64];
    uint8_t sequence_bytes[4];

    for (size_t index = 0U; index < sizeof(inner_pad); ++index) {
        uint8_t key_byte = index < P328_AUTH_KEY_SIZE
            ? p328_auth_key[index] : 0U;
        inner_pad[index] = (uint8_t)(key_byte ^ 0x36U);
        outer_pad[index] = (uint8_t)(key_byte ^ 0x5cU);
    }
    s22plus_max77705_runtime_sha256_init(&inner_context);
    s22plus_max77705_runtime_sha256_update(
        &inner_context, inner_pad, sizeof(inner_pad));
    s22plus_max77705_runtime_sha256_update(
        &inner_context, (const uint8_t *)domain, domain_length);
    s22plus_max77705_runtime_sha256_update(
        &inner_context, run_id, sizeof(p328_run_id_bytes));
    s22plus_max77705_runtime_sha256_update(
        &inner_context, nonce, P328_NONCE_SIZE);
    if (include_sequence) {
        sequence_bytes[0] = (uint8_t)sequence;
        sequence_bytes[1] = (uint8_t)(sequence >> 8);
        sequence_bytes[2] = (uint8_t)(sequence >> 16);
        sequence_bytes[3] = (uint8_t)(sequence >> 24);
        s22plus_max77705_runtime_sha256_update(
            &inner_context, sequence_bytes, sizeof(sequence_bytes));
    }
    if (command != NULL && command_length != 0U)
        s22plus_max77705_runtime_sha256_update(
            &inner_context, command, command_length);
    s22plus_max77705_runtime_sha256_final(&inner_context, inner_digest);

    s22plus_max77705_runtime_sha256_init(&outer_context);
    s22plus_max77705_runtime_sha256_update(
        &outer_context, outer_pad, sizeof(outer_pad));
    s22plus_max77705_runtime_sha256_update(
        &outer_context, inner_digest, sizeof(inner_digest));
    s22plus_max77705_runtime_sha256_final(&outer_context, digest);
    s22plus_max77705_runtime_zero(inner_pad, sizeof(inner_pad));
    s22plus_max77705_runtime_zero(outer_pad, sizeof(outer_pad));
    s22plus_max77705_runtime_zero(inner_digest, sizeof(inner_digest));
    s22plus_max77705_runtime_zero(sequence_bytes, sizeof(sequence_bytes));
}

static long p328_getrandom_nonce(uint8_t nonce[P328_NONCE_SIZE]) {
    long amount = syscall6(
        P328_NR_GETRANDOM, (long)(uintptr_t)nonce,
        P328_NONCE_SIZE, P328_GRND_NONBLOCK, 0, 0, 0);
    if (amount != (long)P328_NONCE_SIZE)
        return -EIO;
    uint8_t nonzero = 0U;
    for (size_t index = 0U; index < P328_NONCE_SIZE; ++index)
        nonzero |= nonce[index];
    return nonzero == 0U ? -EIO : 0;
}

'''
    value = value.replace(
        "static uint16_t p328_load_le16",
        crypto + "static uint16_t p328_load_le16",
        1,
    )

    command_start = value.index("static int p328_command_valid")
    command_end = value.index("\n\nstatic long p328_dup_to", command_start)
    command_validator = r'''static int p328_command_valid(
    const uint8_t *command, uint16_t length) {
    if (command == NULL || length == 0U || length > P328_MAX_COMMAND)
        return 0;
    for (size_t index = 0U; index < (size_t)length; ++index) {
        uint8_t value = command[index];
        if (value < 0x20U || value > 0x7eU || value == 0U
            || value == '\r' || value == '\n')
            return 0;
    }
    return 1;
}'''
    value = value[:command_start] + command_validator + value[command_end:]

    old_guard = (
        "if (tty_fd <= 2 || !p328_command_valid(sequence, input, input_length))"
        "\n        return -P260_EPROTO;"
    )
    if old_guard not in value:
        raise RuntimeError("P327 command guard anchor is unavailable")
    value = value.replace(
        old_guard,
        "if (tty_fd <= 2 || !p328_command_valid(input, input_length))"
        "\n        return -P260_EPROTO;",
        1,
    )

    console_start = value.index("static long p328_framed_console")
    console = r'''static long p328_framed_console(int tty_fd) {
    uint8_t type = 0U;
    uint32_t sequence = 0U;
    uint16_t length = 0U;
    uint8_t payload[P328_MAX_PAYLOAD];
    uint8_t nonce[P328_NONCE_SIZE];
    uint8_t expected_tag[P328_AUTH_TAG_SIZE];
    long rc = p328_read_frame(
        tty_fd, &type, &sequence, payload, &length);
    if (rc != 0 || type != P328_FRAME_OPEN || sequence != 0U
        || length != sizeof(p328_run_id_bytes)
        || !p328_constant_time_equal(
            payload, p328_run_id_bytes, sizeof(p328_run_id_bytes)))
        return rc != 0 ? rc : -P260_EPROTO;

    rc = p328_getrandom_nonce(nonce);
    if (rc != 0) return rc;
    rc = p328_write_frame(
        tty_fd, P328_FRAME_CHALLENGE, 0U,
        nonce, (uint16_t)sizeof(nonce));
    if (rc != 0) return rc;

    rc = p328_read_frame(
        tty_fd, &type, &sequence, payload, &length);
    if (rc != 0 || type != P328_FRAME_AUTH || sequence != 1U
        || length != P328_AUTH_TAG_SIZE)
        return rc != 0 ? rc : -P260_EPROTO;
    p328_hmac_message(
        expected_tag, p328_auth_domain_open,
        sizeof(p328_auth_domain_open) - 1U,
        p328_run_id_bytes, nonce, 0U, 0, NULL, 0U);
    if (!p328_constant_time_equal(
        payload, expected_tag, P328_AUTH_TAG_SIZE)) return -P260_EPROTO;

    p328_hmac_message(
        expected_tag, p328_auth_domain_ready,
        sizeof(p328_auth_domain_ready) - 1U,
        p328_run_id_bytes, nonce, 0U, 0, NULL, 0U);
    rc = p328_write_frame(
        tty_fd, P328_FRAME_READY, 1U,
        expected_tag, P328_AUTH_TAG_SIZE);
    if (rc != 0) return rc;

    uint32_t expected_sequence = 2U;
    uint32_t handled = 0U;
    for (;;) {
        rc = p328_read_frame(
            tty_fd, &type, &sequence, payload, &length);
        if (rc != 0 || sequence != expected_sequence)
            return rc != 0 ? rc : -P260_EPROTO;
        if (type == P328_FRAME_EXEC && handled < P328_MAX_COMMANDS
            && length >= P328_AUTH_TAG_SIZE) {
            uint16_t command_length =
                (uint16_t)(length - P328_AUTH_TAG_SIZE);
            const uint8_t *command = payload + P328_AUTH_TAG_SIZE;
            if (!p328_command_valid(command, command_length))
                return -P260_EPROTO;
            p328_hmac_message(
                expected_tag, p328_auth_domain_exec,
                sizeof(p328_auth_domain_exec) - 1U,
                p328_run_id_bytes, nonce, sequence, 1,
                command, command_length);
            if (!p328_constant_time_equal(
                payload, expected_tag, P328_AUTH_TAG_SIZE))
                return -P260_EPROTO;
            rc = p328_exec_command(
                tty_fd, sequence, command, command_length);
            if (rc != 0) return rc;
            ++handled;
            ++expected_sequence;
            if (handled == P328_MAX_COMMANDS) {
                /* The next frame must be CLOSE; no seventeenth EXEC. */
                expected_sequence = handled + 2U;
            }
            continue;
        }
        if (type == P328_FRAME_CLOSE && length == P328_AUTH_TAG_SIZE
            && handled != 0U) {
            p328_hmac_message(
                expected_tag, p328_auth_domain_close,
                sizeof(p328_auth_domain_close) - 1U,
                p328_run_id_bytes, nonce, sequence, 1, NULL, 0U);
            if (!p328_constant_time_equal(
                payload, expected_tag, P328_AUTH_TAG_SIZE))
                return -P260_EPROTO;
            uint8_t done[4];
            p328_store_le32(done, handled);
            return p328_write_frame(
                tty_fd, P328_FRAME_DONE, sequence, done, sizeof(done));
        }
        return -P260_EPROTO;
    }
}
'''
    value = value[:console_start] + console
    return value.encode("ascii")


P328_HELPER_TEMPLATE = _derive_helper_template()
# Public source contains only this marker, never a usable key.
P328_HELPER = P328_HELPER_TEMPLATE


class AuthRuntimeError(ValueError):
    """The P3.27 preimage or authenticated P3.28 runtime delta differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _validate_auth_key(auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise AuthRuntimeError("auth_key must be exactly 32 bytes")
    return auth_key


def auth_key_sha256(auth_key: bytes) -> str:
    return hashlib.sha256(_validate_auth_key(auth_key)).hexdigest()


def _key_initializer(auth_key: bytes) -> str:
    key = _validate_auth_key(auth_key)
    return ", ".join(f"0x{byte:02x}U" for byte in key)


def materialize_helper(auth_key: bytes) -> bytes:
    """Return the private C helper containing exactly ``auth_key`` bytes."""

    _validate_auth_key(auth_key)
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P328_HELPER_TEMPLATE.count(marker) != 1:
        raise AuthRuntimeError("P328 key marker multiplicity differs")
    return P328_HELPER_TEMPLATE.replace(
        marker, _key_initializer(auth_key).encode("ascii"), 1
    )


def _extract_materialized_key(value: bytes) -> bytes:
    try:
        start = value.index(_AUTH_KEY_DECL_PREFIX) + len(_AUTH_KEY_DECL_PREFIX)
        end = value.index(_AUTH_KEY_DECL_SUFFIX, start)
    except ValueError as exc:
        raise AuthRuntimeError("P328 materialized key declaration is missing") from exc
    fields = value[start:end].split(b", ")
    if len(fields) != AUTH_KEY_SIZE:
        raise AuthRuntimeError("P328 materialized key size differs")
    output = bytearray()
    for field in fields:
        if not field.startswith(b"0x") or not field.endswith(b"U"):
            raise AuthRuntimeError("P328 materialized key literal differs")
        try:
            number = int(field[2:-1], 16)
        except ValueError as exc:
            raise AuthRuntimeError("P328 materialized key literal is invalid") from exc
        if not 0 <= number <= 0xFF:
            raise AuthRuntimeError("P328 materialized key byte is out of range")
        output.append(number)
    return bytes(output)


def validate_p327_runtime(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes:
        raise AuthRuntimeError("P3.27 runtime must be bytes")
    try:
        return dict(p327.validate_p327_runtime(value))
    except Exception as exc:
        raise AuthRuntimeError(f"P3.27 predecessor differs: {exc}") from exc


def validate_p328_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise AuthRuntimeError("P3.28 runtime must be bytes")
    if value.count(P328_ENTRY) != 1 or value.count(PUBLISHER) != 1:
        raise AuthRuntimeError("P3.28 entry/publisher anchors differ")
    if p327.P327_HELPER in value or p327.P327_ENTRY in value:
        raise AuthRuntimeError("P3.27 predecessor anchor remains")
    key = _extract_materialized_key(value)
    key_digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and auth_key_sha256 != key_digest:
        raise AuthRuntimeError("P3.28 materialized auth key digest differs")
    helper_prefix = P328_HELPER_TEMPLATE.split(
        AUTH_KEY_PLACEHOLDER.encode("ascii"), 1
    )[0]
    helper_suffix = P328_HELPER_TEMPLATE.split(
        AUTH_KEY_PLACEHOLDER.encode("ascii"), 1
    )[1]
    if value.count(helper_prefix) != 1 or value.count(helper_suffix) != 1:
        raise AuthRuntimeError("P3.28 helper anchor differs")
    helper_offset = value.index(helper_prefix)
    publisher_offset = value.index(PUBLISHER)
    entry_offset = value.index(P328_ENTRY, publisher_offset)
    if not helper_offset < publisher_offset < entry_offset:
        raise AuthRuntimeError("P3.28 helper/publisher order differs")
    required = (
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
        b"P328_NR_GETRANDOM 278",
        b"P328_AUTH_TAG_SIZE 32U",
        b"p328_constant_time_equal",
        b"p328_getrandom_nonce",
        b"P328_FRAME_CHALLENGE 0x85U",
    )
    if any(item not in value for item in required) or b"ash -i" in value:
        raise AuthRuntimeError("P3.28 authenticated execution contract differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P328_RUN_ID_HEX,
        "wire_magic": FRAME_MAGIC.decode("ascii"),
        "frame_version": FRAME_VERSION,
        "frame_header_size": FRAME_HEADER_SIZE,
        "max_frame_payload": MAX_FRAME_PAYLOAD,
        "max_command_size": MAX_COMMAND_SIZE,
        "max_commands": MAX_COMMANDS,
        "command_timeout_sec": COMMAND_TIMEOUT_SEC,
        "max_output_bytes": MAX_OUTPUT_BYTES,
        "command_policy": "caller_selected_ascii_printable_hmac_v1",
        "caller_selected_command": True,
        "auth_key_sha256": key_digest,
        "auth_algorithm": "hmac-sha256",
        "per_session_random_nonce": True,
        "child_kill_and_reap": True,
        "child_session_isolated": True,
        "descendant_group_cleanup": True,
        "interactive_pty": False,
        "stdin_dev_null": True,
        "carrier_path_retained": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    validate_p327_runtime(before)
    result = validate_p328_runtime(after, auth_key_sha256=auth_key_sha256)
    key = _extract_materialized_key(after)
    expected = before.replace(p327.P327_HELPER, materialize_helper(key), 1)
    expected = expected.replace(p327.P327_ENTRY, P328_ENTRY, 1)
    if after != expected:
        raise AuthRuntimeError("P3.28 delta exceeds the two P3.27 console anchors")
    return result | {
        "changed_anchors": ["p327_console_helper", "p319_stock_publish"],
        "source_identity": identity(before),
        "target_identity": identity(after),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    validate_p327_runtime(value)
    key = _validate_auth_key(auth_key)
    result = value.replace(p327.P327_HELPER, materialize_helper(key), 1)
    result = result.replace(p327.P327_ENTRY, P328_ENTRY, 1)
    validate_transform(
        value, result, auth_key_sha256=auth_key_sha256(key)
    )
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise AuthRuntimeError("P3.27 source bundle lacks the runtime include")
    _validate_auth_key(auth_key)
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(
        source[RUNTIME_KEY], auth_key=auth_key
    )
    changed = {key for key in result if result[key] != source[key]}
    if changed != {RUNTIME_KEY}:
        raise AuthRuntimeError("P3.28 source delta differs")
    return result


__all__ = [
    "AUTH_DOMAIN_CLOSE",
    "AUTH_DOMAIN_EXEC",
    "AUTH_DOMAIN_OPEN",
    "AUTH_DOMAIN_READY",
    "AUTH_KEY_SIZE",
    "AUTH_KEY_PLACEHOLDER",
    "AUTH_TAG_SIZE",
    "AuthRuntimeError",
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
    "FRAME_HEADER_SIZE",
    "FRAME_MAGIC",
    "FRAME_OPEN",
    "FRAME_READY",
    "FRAME_VERSION",
    "MAX_COMMANDS",
    "MAX_COMMAND_SIZE",
    "MAX_FRAME_PAYLOAD",
    "MAX_OUTPUT_BYTES",
    "NONCE_SIZE",
    "P328_ENTRY",
    "P328_HELPER",
    "P328_HELPER_TEMPLATE",
    "P328_RUN_ID",
    "P328_RUN_ID_HEX",
    "PUBLISHER",
    "RUNTIME_KEY",
    "SCHEMA",
    "TARGET",
    "auth_key_sha256",
    "identity",
    "materialize_helper",
    "transform_artifacts",
    "transform_runtime_include",
    "validate_p327_runtime",
    "validate_p328_runtime",
    "validate_transform",
]
