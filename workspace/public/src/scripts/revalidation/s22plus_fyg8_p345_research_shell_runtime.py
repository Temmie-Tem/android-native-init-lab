#!/usr/bin/env python3
"""Host-only P3.45 research-shell runtime transform.

P3.44 is the consumed named-read runtime.  This thin successor keeps S328
framing, authentication, fixed sequence-3/5 commands, output and timeout
limits, and the reviewed child-drain transform.  Sequence 4 alone accepts
bounded arbitrary ash text through the artifact-owned read-only child entry.
An authenticated CANCEL is multiplexed with output reads; no device or live
authority is exposed here.
"""

from __future__ import annotations

import binascii
import hashlib
import hmac
import importlib
from pathlib import Path
import struct
from typing import Any, Mapping

import s22plus_fyg8_p344_open_read_branch_runtime as predecessor
import s22plus_fyg8_research_shell_child as child_drain


SOURCE = Path(predecessor.__file__).resolve()
P344_SOURCE_IDENTITY = {
    "size": 14_035,
    "sha256": "9b4493e4c2c1eefd5bab9dc08b467f2b242dfc9c5797fdefada221daf93335f9",
}
SOURCE_IDENTITY = dict(P344_SOURCE_IDENTITY)
P344_PREDECESSOR_RUN_ID_HEX = predecessor.P344_RUN_ID_HEX
P344_PREDECESSOR_RUN_ID = predecessor.P344_RUN_ID
P344_RUN_ID_HEX = P344_PREDECESSOR_RUN_ID_HEX
P344_RUN_ID = P344_PREDECESSOR_RUN_ID
P345_RUN_ID_HEX = "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a"
P345_RUN_ID = bytes.fromhex(P345_RUN_ID_HEX)

FRAME_MAGIC = predecessor.FRAME_MAGIC
FRAME_VERSION = predecessor.FRAME_VERSION
FRAME_OPEN = predecessor.FRAME_OPEN
FRAME_EXEC = predecessor.FRAME_EXEC
FRAME_CLOSE = predecessor.FRAME_CLOSE
FRAME_READY = predecessor.FRAME_READY
FRAME_DATA = predecessor.FRAME_DATA
FRAME_EXIT = predecessor.FRAME_EXIT
FRAME_DONE = predecessor.FRAME_DONE
FRAME_CHALLENGE = predecessor.FRAME_CHALLENGE
FRAME_AUTH = predecessor.FRAME_AUTH
FRAME_BOOT_ID = predecessor.P335_FRAME_BOOT_ID
FRAME_CANCEL = 5
FRAME_CANCEL_ACK = 0x88

P345_FRAME_CANCEL = FRAME_CANCEL
P345_FRAME_CANCEL_ACK = FRAME_CANCEL_ACK
P345_CANCEL_SEQUENCE = 4
P345_CANCEL_STATUS_CONSUMED = 0
P345_CANCEL_STATUS_ALREADY_COMPLETED = 1
P345_CANCEL_STATUS_NONE = 0xFF
P345_CANCEL_PAYLOAD_SIZE = 32
P345_CANCELLED_FLAG = 0x08
P345_FLAG_CANCELLED = P345_CANCELLED_FLAG
FLAG_CANCELLED = P345_CANCELLED_FLAG
AUTH_DOMAIN_CANCEL = b"S22PLUS-FYG8-P345-AUTH-CANCEL-v1"
P345_AUTH_DOMAIN_CANCEL = AUTH_DOMAIN_CANCEL

HEADER = struct.Struct("<4sBBHII")
EXIT = struct.Struct("<IiIIQ")
FRAME_HEADER_SIZE = HEADER.size
EXIT_SIZE = EXIT.size
KNOWN_FLAGS = 0x01 | 0x02 | 0x04 | P345_CANCELLED_FLAG

MAX_FRAME_PAYLOAD = predecessor.MAX_FRAME_PAYLOAD
MAX_COMMAND_SIZE = predecessor.MAX_COMMAND_SIZE
MAX_COMMANDS = predecessor.MAX_COMMANDS
COMMAND_TIMEOUT_SEC = predecessor.COMMAND_TIMEOUT_SEC
MAX_OUTPUT_BYTES = predecessor.MAX_OUTPUT_BYTES
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
NONCE_SIZE = predecessor.NONCE_SIZE
P345_COMMAND = f"/bin/busybox echo P328-NONCE {P345_RUN_ID_HEX}".encode("ascii")
P344_COMMAND = predecessor.P344_COMMAND
P343_COMMAND = predecessor.P343_COMMAND
P344_DEFAULT_COMMANDS = tuple(predecessor.DEFAULT_COMMANDS)
P345_DEFAULT_COMMANDS = (
    P344_DEFAULT_COMMANDS[0],
    P344_DEFAULT_COMMANDS[1],
    P345_COMMAND,
)
DEFAULT_COMMANDS = P345_DEFAULT_COMMANDS
CATALOG = dict(predecessor.CATALOG)
CATALOG_ACTIONS = tuple(CATALOG)
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P345_RUN_ID_HEX}\n".encode("ascii")
P345_DETAIL_ANCHOR = predecessor.P344_DETAIL_ANCHOR
RUNTIME_KEY = predecessor.RUNTIME_KEY
TARGET = predecessor.TARGET
PUBLISHER = predecessor.PUBLISHER
AUTH_DOMAIN_OPEN = predecessor.AUTH_DOMAIN_OPEN
AUTH_DOMAIN_READY = predecessor.AUTH_DOMAIN_READY
AUTH_DOMAIN_EXEC = predecessor.AUTH_DOMAIN_EXEC
AUTH_DOMAIN_CLOSE = predecessor.AUTH_DOMAIN_CLOSE
AUTH_DOMAIN_BOOT_ID = predecessor.AUTH_DOMAIN_BOOT_ID
AUTH_KEY_PLACEHOLDER = predecessor.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = predecessor.AUTH_KEY_SIZE
AUTH_KEY_SCHEMA = predecessor.AUTH_KEY_SCHEMA
AUTH_TAG_SIZE = predecessor.AUTH_TAG_SIZE
RNG_EAGAIN_RETRY_LIMIT = predecessor.RNG_EAGAIN_RETRY_LIMIT

# Existing host readers use the retained-listener names.  Rebind them to the
# fresh P345 identity rather than silently selecting consumed P344 bytes.
P335_RUN_ID_HEX = P345_RUN_ID_HEX
P335_RUN_ID = P345_RUN_ID
P335_BOOT_ID_SEQUENCE = predecessor.P335_BOOT_ID_SEQUENCE
P335_BOOT_ID_SIZE = predecessor.P335_BOOT_ID_SIZE
P335_COMMANDS_PER_SESSION = predecessor.P335_COMMANDS_PER_SESSION
P335_FRAME_BOOT_ID = predecessor.P335_FRAME_BOOT_ID
DIAGNOSTIC_STAGE_CONSOLE_ENTER = predecessor.DIAGNOSTIC_STAGE_CONSOLE_ENTER
DIAGNOSTIC_STAGE_OPEN_PARSED = predecessor.DIAGNOSTIC_STAGE_OPEN_PARSED
DIAGNOSTIC_STAGE_RNG = predecessor.DIAGNOSTIC_STAGE_RNG
DIAGNOSTIC_FRAME_TYPE = predecessor.DIAGNOSTIC_FRAME_TYPE
OPEN_READ_BRANCHES = dict(predecessor.OPEN_READ_BRANCHES)
OPEN_HEADER_WORD_STAGES = tuple(predecessor.OPEN_HEADER_WORD_STAGES)
OPEN_HEADER_SIZE = predecessor.OPEN_HEADER_SIZE
DIAGNOSTIC_STAGE_OPEN_READ_RESULT = predecessor.DIAGNOSTIC_STAGE_OPEN_READ_RESULT


class RuntimeIdentityError(ValueError):
    """The exact P3.44 predecessor or P3.45 transform differs."""


try:
    _P344_SOURCE_PAYLOAD = SOURCE.read_bytes()
except OSError as exc:
    raise RuntimeIdentityError("P3.44 runtime source is unavailable") from exc


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


if identity(_P344_SOURCE_PAYLOAD) != SOURCE_IDENTITY:
    raise RuntimeIdentityError("P3.44 runtime source identity differs")


def _function_slice(value: bytes, declaration: bytes) -> tuple[int, int]:
    start = value.find(declaration)
    if start < 0:
        raise RuntimeIdentityError(f"missing C declaration: {declaration!r}")
    brace = value.find(b"{", start)
    if brace < 0:
        raise RuntimeIdentityError("C function body is absent")
    depth = 0
    quote: int | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(value):
        byte = value[index]
        next_byte = value[index + 1] if index + 1 < len(value) else None
        if line_comment:
            if byte == 0x0A:
                line_comment = False
            index += 1
            continue
        if block_comment:
            if byte == 0x2A and next_byte == 0x2F:
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == quote:
                quote = None
            index += 1
            continue
        if byte == 0x2F and next_byte == 0x2F:
            line_comment = True
            index += 2
            continue
        if byte == 0x2F and next_byte == 0x2A:
            block_comment = True
            index += 2
            continue
        if byte in (0x22, 0x27):
            quote = byte
        elif byte == 0x7B:
            depth += 1
        elif byte == 0x7D:
            depth -= 1
            if depth == 0:
                return start, index + 1
        index += 1
    raise RuntimeIdentityError("unterminated C function body")


def _replace_function(value: bytes, declaration: bytes, replacement: bytes) -> bytes:
    start, end = _function_slice(value, declaration)
    return value[:start] + replacement + value[end:]


def _insert_once(value: bytes, anchor: bytes, insertion: bytes) -> bytes:
    if value.count(anchor) != 1:
        raise RuntimeIdentityError(f"source anchor occurrence differs: {anchor!r}")
    return value.replace(anchor, insertion + anchor, 1)


def _validate_child_source(value: bytes) -> bytes:
    if type(value) is not bytes or not value:
        raise RuntimeIdentityError("P3.45 read-only child source is unavailable")
    try:
        value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise RuntimeIdentityError("P3.45 child source is not ASCII C") from exc
    declaration = b"static long p345_enter_readonly_child(void)"
    if value.count(declaration) != 1:
        raise RuntimeIdentityError("P3.45 child entry declaration differs")
    _function_slice(value, declaration)
    if value.count(b"p345_enter_readonly_child()"):
        raise RuntimeIdentityError("P3.45 child source contains an integration hook")
    return value


def _load_child_source() -> bytes:
    try:
        module = importlib.import_module("s22plus_fyg8_p345_readonly_child")
    except ModuleNotFoundError as exc:
        if exc.name != "s22plus_fyg8_p345_readonly_child":
            raise
        raise RuntimeIdentityError(
            "P3.45 read-only child source is not yet available"
        ) from exc
    payload = getattr(module, "CHILD_SOURCE")
    validator = getattr(module, "validate_child_source", None)
    if callable(validator):
        try:
            validator(payload)
        except Exception as exc:
            raise RuntimeIdentityError(
                f"P3.45 child source validation failed: {exc}"
            ) from exc
    return _validate_child_source(payload)


def child_source() -> bytes:
    return _load_child_source()


def fixture_child_source() -> bytes:
    """Minimal test-only child entry; never used by an artifact path."""
    return b"static long p345_enter_readonly_child(void) { return 0; }"


def _c_string(value: bytes) -> bytes:
    return "".join(f"\\x{byte:02x}" for byte in value).encode("ascii")


def _command_validator() -> bytes:
    return b"""static int p345_command_valid(
    uint32_t sequence, const uint8_t *command, uint16_t length) {
    if (command == NULL || length == 0U || length > P328_MAX_COMMAND)
        return 0;
    if (sequence == 3U)
        return length == sizeof(p335_command_1) - 1U
            && p260_bytes_equal((const char *)command, p335_command_1, length);
    if (sequence == 4U) {
        for (uint16_t index = 0U; index < length; ++index) {
            uint8_t byte = command[index];
            if (byte == 0U || byte == 127U
                || (byte < 32U && byte != '\\t' && byte != '\\n'))
                return 0;
        }
        return 1;
    }
    if (sequence == 5U)
        return length == sizeof(p335_command_3) - 1U
            && p260_bytes_equal((const char *)command, p335_command_3, length);
    return 0;
}"""


def _cancel_helpers() -> bytes:
    return b"""static void p345_report_child_setup_failure(long result) {
    static const char prefix[] =
        "P345_READONLY_CHILD_SETUP_FAILED rc=0x";
    static const char digits[] = "0123456789abcdef";
    char output[sizeof(prefix) - 1U + 8U + 1U];
    memcpy(output, prefix, sizeof(prefix) - 1U);
    uint32_t value = (uint32_t)result;
    for (uint32_t index = 0U; index < 8U; ++index) {
        uint32_t shift = 28U - index * 4U;
        output[sizeof(prefix) - 1U + index] =
            digits[(value >> shift) & 0x0fU];
    }
    output[sizeof(output) - 1U] = '\\n';
    (void)sys_write(2, output, sizeof(output));
}

static int p345_cancel_tag_valid(
    const uint8_t *payload, uint16_t length, uint32_t sequence,
    const uint8_t nonce[P328_NONCE_SIZE]) {
    if (payload == NULL || nonce == NULL
        || sequence != P345_CANCEL_SEQUENCE
        || length != P345_CANCEL_PAYLOAD_SIZE)
        return 0;
    uint8_t expected[P328_AUTH_TAG_SIZE];
    p328_hmac_message(
        expected, p345_auth_domain_cancel,
        sizeof(p345_auth_domain_cancel) - 1U,
        p328_run_id_bytes, nonce, sequence, 1, NULL, 0U);
    return p328_constant_time_equal(
        payload, expected, P328_AUTH_TAG_SIZE);
}

static long p345_try_read_cancel(
    int tty_fd, uint32_t active_sequence,
    const uint8_t nonce[P328_NONCE_SIZE],
    uint8_t header[P328_HEADER_SIZE], uint16_t *header_used,
    uint8_t payload[P345_CANCEL_PAYLOAD_SIZE], uint16_t *payload_used,
    uint8_t *observed) {
    if (header == NULL || header_used == NULL || payload == NULL
        || payload_used == NULL || observed == NULL
        || active_sequence != P345_CANCEL_SEQUENCE)
        return -EINVAL;
    *observed = P345_CANCEL_NONE;
    while (*header_used < P328_HEADER_SIZE) {
        long amount = sys_read(
            tty_fd, header + *header_used,
            P328_HEADER_SIZE - *header_used);
        if (amount == -EAGAIN || amount == -P260_EINTR) {
            if (*header_used != 0U) *observed = P345_CANCEL_PENDING;
            return 0;
        }
        if (amount <= 0) return amount == 0 ? -EIO : amount;
        if ((size_t)amount > (size_t)(P328_HEADER_SIZE - *header_used))
            return -EIO;
        *header_used = (uint16_t)(*header_used + (uint16_t)amount);
    }
    uint16_t length = p328_load_le16(header + 6U);
    if (header[0] != P328_MAGIC_0 || header[1] != P328_MAGIC_1
        || header[2] != P328_MAGIC_2 || header[3] != P328_MAGIC_3
        || header[4] != P328_FRAME_VERSION
        || header[5] != P345_FRAME_CANCEL
        || p328_load_le32(header + 8U) != active_sequence
        || length != P345_CANCEL_PAYLOAD_SIZE)
        return -P260_EPROTO;
    while (*payload_used < P345_CANCEL_PAYLOAD_SIZE) {
        long amount = sys_read(
            tty_fd, payload + *payload_used,
            P345_CANCEL_PAYLOAD_SIZE - *payload_used);
        if (amount == -EAGAIN || amount == -P260_EINTR) {
            *observed = P345_CANCEL_PENDING;
            return 0;
        }
        if (amount <= 0) return amount == 0 ? -EIO : amount;
        if ((size_t)amount > (size_t)(P345_CANCEL_PAYLOAD_SIZE - *payload_used))
            return -EIO;
        *payload_used = (uint16_t)(*payload_used + (uint16_t)amount);
    }
    if (p328_frame_crc(header, payload, P345_CANCEL_PAYLOAD_SIZE)
        != p328_load_le32(header + 12U)
        || !p345_cancel_tag_valid(
            payload, P345_CANCEL_PAYLOAD_SIZE, active_sequence, nonce))
        return -P260_EPROTO;
    *header_used = 0U;
    *payload_used = 0U;
    *observed = P345_CANCEL_VALID;
    return 0;
}

static long p345_write_cancel_ack(
    int tty_fd, uint32_t sequence, uint32_t status) {
    uint8_t payload[4];
    p328_store_le32(payload, status);
    return p328_write_frame(
        tty_fd, P345_FRAME_CANCEL_ACK, sequence,
        payload, (uint16_t)sizeof(payload));
}"""


def _exec_function(value: bytes) -> bytes:
    start, end = _function_slice(value, b"static long p328_exec_command(")
    function = value[start:end]
    function = function.replace(
        b"static long p328_exec_command(",
        b"static long p345_exec_command(",
        1,
    )
    old_signature = (
        b"    int tty_fd, uint32_t sequence,\n"
        b"    const uint8_t *input, uint16_t input_length) {"
    )
    new_signature = (
        b"    int tty_fd, uint32_t sequence,\n"
        b"    const uint8_t *input, uint16_t input_length,\n"
        b"    const uint8_t nonce[P328_NONCE_SIZE],\n"
        b"    uint8_t *cancel_status) {"
    )
    if function.count(old_signature) != 1:
        raise RuntimeIdentityError("P3.44 exec signature anchor differs")
    function = function.replace(old_signature, new_signature, 1)
    child_anchor = (
        b"        (void)sys_close(tty_fd);\n"
        b"        char *const argv[] = {"
    )
    child_replacement = (
        b"        (void)sys_close(tty_fd);\n"
        b"        if (sequence == P345_CANCEL_SEQUENCE) {\n"
        b"            long child_setup = p345_enter_readonly_child();\n"
        b"            if (child_setup != 0) {\n"
        b"                p345_report_child_setup_failure(child_setup);\n"
        b"                sys_exit(126);\n"
        b"            }\n"
        b"        }\n"
        b"        char *const argv[] = {"
    )
    if function.count(child_anchor) != 1:
        raise RuntimeIdentityError("P3.44 child setup anchor differs")
    function = function.replace(child_anchor, child_replacement, 1)
    locals_anchor = b"    int timeout_attempted = 0;\n"
    locals_replacement = locals_anchor + (
        b"    int cancelled = 0;\n"
        b"    int late_cancel = 0;\n"
        b"    uint8_t cancel_header[P328_HEADER_SIZE] = {0};\n"
        b"    uint16_t cancel_header_used = 0U;\n"
        b"    uint8_t cancel_payload[P345_CANCEL_PAYLOAD_SIZE] = {0};\n"
        b"    uint16_t cancel_payload_used = 0U;\n"
    )
    if function.count(locals_anchor) != 1:
        raise RuntimeIdentityError("P3.44 exec locals anchor differs")
    function = function.replace(locals_anchor, locals_replacement, 1)
    wait_anchor = b"        if (!reaped) {\n            long waited = sys_wait4"
    cancel_poll = b"""        if (sequence == P345_CANCEL_SEQUENCE
            && !cancelled && !late_cancel) {
            uint8_t observed = P345_CANCEL_NONE;
            rc = p345_try_read_cancel(
                tty_fd, sequence, nonce,
                cancel_header, &cancel_header_used,
                cancel_payload, &cancel_payload_used, &observed);
            if (rc != 0) break;
            if (observed == P345_CANCEL_VALID) {
                if (reaped) {
                    late_cancel = 1;
                    if (cancel_status != NULL)
                        *cancel_status =
                            P345_CANCEL_STATUS_ALREADY_COMPLETED;
                } else {
                    cancelled = 1;
                    if (cancel_status != NULL)
                        *cancel_status = P345_CANCEL_STATUS_CONSUMED;
                    (void)sys_kill(-pid, SIGKILL);
                    rc = p328_reap_after_kill(pid, &status);
                    if (rc != 0) break;
                    reaped = 1;
                }
            }
        }
"""
    if function.count(wait_anchor) != 1:
        raise RuntimeIdentityError("P3.44 exec wait anchor differs")
    post_wait_anchor = b"        }\n        if (reaped) {\n"
    if function.count(post_wait_anchor) != 1:
        raise RuntimeIdentityError("P3.44 post-wait anchor differs")
    function = function.replace(post_wait_anchor, b"        }\n" + cancel_poll + b"        if (reaped) {\n", 1)
    reaped_anchor = (
        b"        if (reaped) {\n"
        b"            if (amount == 0 || amount == -EAGAIN) break;"
    )
    reaped_replacement = (
        b"        if (reaped) {\n"
        b"            if (!cancelled && (cancel_header_used != 0U\n"
        b"                || cancel_payload_used != 0U)) {\n"
        b"                rc = -P260_EPROTO;\n"
        b"                break;\n"
        b"            }\n"
        b"            if (amount == 0 || amount == -EAGAIN) break;"
    )
    if function.count(reaped_anchor) != 1:
        raise RuntimeIdentityError("P3.44 exec reap anchor differs")
    function = function.replace(reaped_anchor, reaped_replacement, 1)
    signal_anchor = b"    uint32_t signal_number = (uint32_t)status & 0x7fU;"
    if function.count(signal_anchor) != 1:
        raise RuntimeIdentityError("P3.44 exec exit anchor differs")
    function = function.replace(
        signal_anchor,
        b"    if (cancelled) flags |= P345_CANCELLED_FLAG;\n\n" + signal_anchor,
        1,
    )
    return_anchor = (
        b"    return p328_write_frame(\n"
        b"        tty_fd, P328_FRAME_EXIT, sequence,\n"
        b"        exit_payload, (uint16_t)sizeof(exit_payload));"
    )
    return_replacement = b"""    rc = p328_write_frame(
        tty_fd, P328_FRAME_EXIT, sequence,
        exit_payload, (uint16_t)sizeof(exit_payload));
    if (rc != 0 || (!cancelled && !late_cancel)) return rc;
    return p345_write_cancel_ack(
        tty_fd, sequence,
        late_cancel ? P345_CANCEL_STATUS_ALREADY_COMPLETED
            : P345_CANCEL_STATUS_CONSUMED);"""
    if function.count(return_anchor) != 1:
        raise RuntimeIdentityError("P3.44 exec EXIT writer anchor differs")
    function = function.replace(return_anchor, return_replacement, 1)
    if function.count(b"p345_enter_readonly_child()") != 1:
        raise RuntimeIdentityError("P3.45 child entry call differs")
    return value[:start] + function + value[end:]


def _console_function(value: bytes) -> bytes:
    start, end = _function_slice(value, b"static long p335_framed_console(")
    function = value[start:end].replace(
        b"static long p335_framed_console(",
        b"static long p345_framed_console(",
        1,
    )
    handled_anchor = b"    uint32_t handled = 0U;\n"
    if function.count(handled_anchor) != 1:
        raise RuntimeIdentityError("P3.44 console handled anchor differs")
    function = function.replace(
        handled_anchor,
        handled_anchor + b"    uint8_t p345_cancel_ack_sent = 0U;\n",
        1,
    )
    read_anchor = b"""        rc = p328_read_frame(
            tty_fd, &type, &sequence, payload, &length, NULL, NULL, NULL);
        if (rc != 0 || sequence != expected_sequence)
            return rc != 0 ? rc : -P260_EPROTO;
"""
    read_replacement = b"""        rc = p328_read_frame(
            tty_fd, &type, &sequence, payload, &length, NULL, NULL, NULL);
        if (rc != 0) return rc;
        if (type == P345_FRAME_CANCEL) {
            if (sequence != P345_CANCEL_SEQUENCE
                || expected_sequence != P345_CANCEL_SEQUENCE + 1U
                || p345_cancel_ack_sent != 0U
                || !p345_cancel_tag_valid(
                    payload, length, sequence, nonce))
                return -P260_EPROTO;
            rc = p345_write_cancel_ack(
                tty_fd, sequence, P345_CANCEL_STATUS_ALREADY_COMPLETED);
            if (rc != 0) return rc;
            p345_cancel_ack_sent = 1U;
            continue;
        }
        if (sequence != expected_sequence)
            return -P260_EPROTO;
"""
    if function.count(read_anchor) != 1:
        raise RuntimeIdentityError("P3.44 console frame anchor differs")
    function = function.replace(read_anchor, read_replacement, 1)
    exec_anchor = b"""            rc = p328_exec_command(
                tty_fd, sequence, command, command_length);
            if (rc != 0) return rc;
            ++handled;
"""
    exec_replacement = b"""            uint8_t p345_cancel_status = P345_CANCEL_STATUS_NONE;
            rc = p345_exec_command(
                tty_fd, sequence, command, command_length,
                nonce, &p345_cancel_status);
            if (rc != 0) return rc;
            if (p345_cancel_status == P345_CANCEL_STATUS_CONSUMED
                || p345_cancel_status
                    == P345_CANCEL_STATUS_ALREADY_COMPLETED)
                p345_cancel_ack_sent = 1U;
            ++handled;
"""
    if function.count(exec_anchor) != 1:
        raise RuntimeIdentityError("P3.44 console EXEC anchor differs")
    function = function.replace(exec_anchor, exec_replacement, 1)
    return value[:start] + function + value[end:]


def build_helper(child: bytes | None = None) -> bytes:
    child_payload = (
        _load_child_source() if child is None else _validate_child_source(child)
    )
    value = child_drain.bound_child_drain(predecessor.P344_HELPER_TEMPLATE)
    old_command = _c_string(P344_COMMAND)
    new_command = _c_string(P345_COMMAND)
    if value.count(old_command) != 1 or value.count(new_command):
        raise RuntimeIdentityError("P3.44 nonce command anchor differs")
    value = value.replace(old_command, new_command, 1)
    constants_anchor = b"#define P328_FRAME_DONE 0x84U\n"
    constants = constants_anchor + (
        b"#define P345_FRAME_CANCEL 5U\n"
        b"#define P345_FRAME_CANCEL_ACK 0x88U\n"
        b"#define P345_CANCEL_SEQUENCE 4U\n"
        b"#define P345_CANCEL_STATUS_CONSUMED 0U\n"
        b"#define P345_CANCEL_STATUS_ALREADY_COMPLETED 1U\n"
        b"#define P345_CANCEL_STATUS_NONE 0xffU\n"
        b"#define P345_CANCEL_PAYLOAD_SIZE P328_AUTH_TAG_SIZE\n"
        b"#define P345_CANCEL_NONE 0U\n"
        b"#define P345_CANCEL_PENDING 1U\n"
        b"#define P345_CANCEL_VALID 2U\n"
        b"#define P345_CANCELLED_FLAG 0x08U\n"
    )
    if value.count(constants_anchor) != 1:
        raise RuntimeIdentityError("P3.44 frame constants anchor differs")
    value = value.replace(constants_anchor, constants, 1)
    domain_anchor = (
        b'static const char p328_auth_domain_close[] = '
        b'"S22PLUS-FYG8-P328-AUTH-CLOSE-v1";\n'
    )
    domain = domain_anchor + (
        b'static const char p345_auth_domain_cancel[] = '
        b'"S22PLUS-FYG8-P345-AUTH-CANCEL-v1";\n'
    )
    if value.count(domain_anchor) != 1:
        raise RuntimeIdentityError("P3.44 auth domain anchor differs")
    value = value.replace(domain_anchor, domain, 1)
    value = _replace_function(
        value, b"static int p335_command_valid(", _command_validator()
    )
    value = value.replace(b"p335_command_valid", b"p345_command_valid")
    value = _insert_once(
        value,
        b"static long p328_dup_to(",
        _cancel_helpers() + b"\n\n" + child_payload + b"\n\n",
    )
    value = _exec_function(value)
    value = _console_function(value)
    if value.count(b"p345_framed_console(") != 1:
        raise RuntimeIdentityError("P3.45 console transform differs")
    return value


def _entry_for_p345() -> bytes:
    value = predecessor.P344_ENTRY.replace(
        b"p335_framed_console(", b"p345_framed_console("
    )
    old_ascii = P344_RUN_ID_HEX.encode("ascii")
    if old_ascii in value:
        value = value.replace(old_ascii, P345_RUN_ID_HEX.encode("ascii"))
    return value


P345_ENTRY = _entry_for_p345()

# Inherited retained-session readers import historical labels while they are
# rebound to the current runtime.  Keep the consumed predecessor explicit and
# make every compatibility label resolve to the fresh P345 identity.
for _prefix in (
    "P328",
    "P329",
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
    "P343",
    "P344",
):
    globals()[f"{_prefix}_RUN_ID_HEX"] = P345_RUN_ID_HEX
    globals()[f"{_prefix}_RUN_ID"] = P345_RUN_ID


try:
    _AVAILABLE_CHILD_SOURCE = _load_child_source()
except RuntimeIdentityError:
    _AVAILABLE_CHILD_SOURCE = None

if _AVAILABLE_CHILD_SOURCE is not None:
    P345_HELPER_TEMPLATE = build_helper(_AVAILABLE_CHILD_SOURCE)
    P345_HELPER = P345_HELPER_TEMPLATE
else:
    P345_HELPER_TEMPLATE = b""
    P345_HELPER = b""


def materialize_helper(
    auth_key: bytes, *, child: bytes | None = None
) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise RuntimeIdentityError("P3.45 authentication key is not 32 bytes")
    helper = build_helper(
        _load_child_source() if child is None else _validate_child_source(child)
    )
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if helper.count(marker) != 1:
        raise RuntimeIdentityError("P3.45 key marker differs")
    return helper.replace(marker, predecessor._key_initializer(auth_key), 1)


def auth_key_sha256(auth_key: bytes) -> str:
    return predecessor.auth_key_sha256(auth_key)


def cancel_tag(
    auth_key: bytes,
    run_id_or_nonce: bytes,
    nonce: bytes | None = None,
    sequence: int = P345_CANCEL_SEQUENCE,
) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise RuntimeIdentityError("P3.45 cancel key is not 32 bytes")
    if nonce is None:
        run_id = P345_RUN_ID
        nonce = run_id_or_nonce
    else:
        run_id = run_id_or_nonce
    if type(run_id) is not bytes or run_id != P345_RUN_ID:
        raise RuntimeIdentityError("P3.45 cancel run identity differs")
    if type(nonce) is not bytes or len(nonce) != NONCE_SIZE or not any(nonce):
        raise RuntimeIdentityError("P3.45 cancel nonce differs")
    if type(sequence) is not int or sequence != P345_CANCEL_SEQUENCE:
        raise RuntimeIdentityError("P3.45 cancel sequence differs")
    message = AUTH_DOMAIN_CANCEL + run_id + nonce + struct.pack("<I", sequence)
    return hmac.new(auth_key, message, hashlib.sha256).digest()


def _frame_crc(prefix: bytes, payload: bytes) -> int:
    if len(prefix) != 12:
        raise RuntimeIdentityError("P3.45 frame prefix size differs")
    return binascii.crc32(payload, binascii.crc32(prefix)) & 0xFFFFFFFF


def encode_frame(frame_type: int, sequence: int, payload: bytes) -> bytes:
    if type(frame_type) is not int or not 0 <= frame_type <= 0xFF:
        raise RuntimeIdentityError("P3.45 frame type differs")
    if type(sequence) is not int or not 0 <= sequence <= 0xFFFFFFFF:
        raise RuntimeIdentityError("P3.45 frame sequence differs")
    if type(payload) is not bytes or len(payload) > MAX_FRAME_PAYLOAD:
        raise RuntimeIdentityError("P3.45 frame payload differs")
    prefix = struct.pack(
        "<4sBBHI", FRAME_MAGIC, FRAME_VERSION, frame_type, len(payload), sequence
    )
    return prefix + struct.pack("<I", _frame_crc(prefix, payload)) + payload


def encode_cancel_frame(
    auth_key: bytes,
    nonce: bytes,
    *,
    run_id: bytes = P345_RUN_ID,
    sequence: int = P345_CANCEL_SEQUENCE,
) -> bytes:
    return encode_frame(
        FRAME_CANCEL, sequence, cancel_tag(auth_key, run_id, nonce, sequence)
    )


def cancel_frame(
    auth_key: bytes,
    nonce: bytes,
    *,
    run_id: bytes = P345_RUN_ID,
    active_sequence: int = P345_CANCEL_SEQUENCE,
) -> bytes:
    return encode_cancel_frame(
        auth_key, nonce, run_id=run_id, sequence=active_sequence
    )


def decode_cancel_ack(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes or len(value) != FRAME_HEADER_SIZE + 4:
        raise RuntimeIdentityError("P3.45 CANCEL ACK frame size differs")
    magic, version, frame_type, length, sequence, received_crc = HEADER.unpack(
        value[:FRAME_HEADER_SIZE]
    )
    payload = value[FRAME_HEADER_SIZE:]
    if (
        magic != FRAME_MAGIC
        or version != FRAME_VERSION
        or frame_type != FRAME_CANCEL_ACK
        or length != 4
        or sequence != P345_CANCEL_SEQUENCE
        or _frame_crc(value[:12], payload) != received_crc
    ):
        raise RuntimeIdentityError("P3.45 CANCEL ACK identity differs")
    status = struct.unpack("<I", payload)[0]
    if status not in (
        P345_CANCEL_STATUS_CONSUMED,
        P345_CANCEL_STATUS_ALREADY_COMPLETED,
    ):
        raise RuntimeIdentityError("P3.45 CANCEL ACK status differs")
    return {
        "frame_type": frame_type,
        "sequence": sequence,
        "status": status,
        "active": status == P345_CANCEL_STATUS_CONSUMED,
        "already_completed": status == P345_CANCEL_STATUS_ALREADY_COMPLETED,
    }


def parse_exit(
    payload: bytes, output_size: int, *, cancel_ack: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if type(payload) is not bytes or len(payload) != EXIT_SIZE:
        raise RuntimeIdentityError("P3.45 EXIT size differs")
    if type(output_size) is not int or not 0 <= output_size <= MAX_OUTPUT_BYTES:
        raise RuntimeIdentityError("P3.45 EXIT output size differs")
    flags, exit_code, signal_number, forwarded, duration_ms = EXIT.unpack(payload)
    if (
        flags & ~KNOWN_FLAGS
        or forwarded != output_size
        or signal_number > 127
        or duration_ms > 0x7FFFFFFFFFFFFFFF
    ):
        raise RuntimeIdentityError("P3.45 EXIT accounting differs")
    if (signal_number == 0 and not 0 <= exit_code <= 255) or (
        signal_number != 0 and exit_code != -1
    ):
        raise RuntimeIdentityError("P3.45 EXIT status differs")
    if flags & 0x01 and (signal_number != 9 or exit_code != -1):
        raise RuntimeIdentityError("P3.45 timeout status differs")
    if flags & 0x04 and exit_code not in (126, 127):
        raise RuntimeIdentityError("P3.45 exec-failure status differs")
    if flags & P345_CANCELLED_FLAG:
        if flags & 0x01:
            raise RuntimeIdentityError("P3.45 cancel is mislabeled timeout")
        if cancel_ack is None or cancel_ack.get("status") != P345_CANCEL_STATUS_CONSUMED:
            raise RuntimeIdentityError("P3.45 cancelled EXIT lacks active ACK")
    elif cancel_ack is not None and cancel_ack.get("status") != P345_CANCEL_STATUS_ALREADY_COMPLETED:
        raise RuntimeIdentityError("P3.45 normal EXIT has active CANCEL ACK")
    return {
        "flags": flags,
        "exit_code": exit_code,
        "signal_number": signal_number,
        "forwarded": forwarded,
        "duration_ms": duration_ms,
        "cancelled": bool(flags & P345_CANCELLED_FLAG),
    }


def completion_state(
    exit_payload: bytes, output_size: int, ack_frame: bytes | None = None
) -> dict[str, Any]:
    ack = decode_cancel_ack(ack_frame) if ack_frame is not None else None
    parsed = parse_exit(exit_payload, output_size, cancel_ack=ack)
    flags = parsed["flags"]
    if parsed["cancelled"]:
        outcome = "cancelled"
    elif flags & 0x01:
        outcome = "timeout"
    elif flags & 0x02:
        outcome = "truncated"
    elif flags & 0x04:
        outcome = "exec-failed"
    elif parsed["exit_code"] != 0 or parsed["signal_number"] != 0:
        outcome = "command-failed"
    else:
        outcome = "completed"
    return {
        **parsed,
        "outcome": outcome,
        "terminal_proved": True,
        "transport_uncertain": False,
        "cancel_ack": ack,
    }


def transform_runtime_include(
    value: bytes, auth_key: bytes, *, child: bytes | None = None
) -> bytes:
    if type(value) is not bytes:
        raise RuntimeIdentityError("P3.44 runtime input is not bytes")
    key_digest = auth_key_sha256(auth_key)
    try:
        predecessor.validate_p344_runtime(value, auth_key_sha256=key_digest)
        old_helper = predecessor.materialize_helper(auth_key)
        current_helper = materialize_helper(auth_key, child=child)
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.44 input differs: {exc}") from exc
    if value.count(old_helper) != 1:
        raise RuntimeIdentityError("P3.44 helper occurrence differs")
    result = value.replace(old_helper, current_helper, 1)
    old_entry = predecessor.P344_ENTRY
    if result.count(old_entry) != 1:
        raise RuntimeIdentityError("P3.44 entry occurrence differs")
    result = result.replace(old_entry, P345_ENTRY, 1)
    validate_p345_runtime(result, auth_key_sha256=key_digest, child=child)
    return result


def validate_p345_runtime(
    value: bytes,
    *,
    auth_key_sha256: str | None = None,
    child: bytes | None = None,
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise RuntimeIdentityError("P3.45 runtime must be bytes")
    try:
        key = predecessor._materialized_key(value)
        digest = hashlib.sha256(key).hexdigest()
        current_helper = materialize_helper(key, child=child)
        old_helper = predecessor.materialize_helper(key)
    except Exception as exc:
        raise RuntimeIdentityError(f"P3.45 key/helper binding differs: {exc}") from exc
    if value.count(current_helper) != 1 or value.count(old_helper):
        raise RuntimeIdentityError("P3.45 helper identity differs")
    if value.count(P345_ENTRY) != 1 or value.count(predecessor.P344_ENTRY):
        raise RuntimeIdentityError("P3.45 entry identity differs")
    if auth_key_sha256 is not None and digest != auth_key_sha256:
        raise RuntimeIdentityError("P3.45 auth key digest differs")
    restored = value.replace(current_helper, old_helper, 1)
    restored = restored.replace(P345_ENTRY, predecessor.P344_ENTRY, 1)
    predecessor.validate_p344_runtime(restored, auth_key_sha256=digest)
    return audit_binding(child=child) | {
        "auth_key_sha256": digest,
        "source_identity": identity(restored),
        "target_identity": identity(value),
    }


def validate_transform(
    before: bytes,
    after: bytes,
    *,
    auth_key_sha256: str | None = None,
    child: bytes | None = None,
) -> dict[str, Any]:
    key = predecessor._materialized_key(before)
    expected = transform_runtime_include(before, key, child=child)
    if after != expected:
        raise RuntimeIdentityError("P3.45 delta exceeds child/cancel transform")
    return validate_p345_runtime(
        after, auth_key_sha256=auth_key_sha256, child=child
    ) | {
        "changed_anchors": [
            "p344_child_drain_deadline",
            "p345_readonly_child_sequence_4",
            "p345_authenticated_cancel",
        ],
        "predecessor_run_id": P344_PREDECESSOR_RUN_ID_HEX,
        "run_id_hex": P345_RUN_ID_HEX,
    }


def transform_artifacts(
    source: Mapping[str, bytes],
    auth_key: bytes,
    *,
    child: bytes | None = None,
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise RuntimeIdentityError("P3.44 runtime input is missing")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(
        source[RUNTIME_KEY], auth_key, child=child
    )
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise RuntimeIdentityError("P3.45 source delta differs")
    return result


def audit_binding(*, child: bytes | None = None) -> dict[str, Any]:
    available = child is not None or _AVAILABLE_CHILD_SOURCE is not None
    value = {
        "schema": "s22plus-fyg8-p345-research-shell-runtime-v1",
        "contract_id": "s22plus-fyg8-p345-research-shell-runtime-v1",
        "predecessor_source": dict(SOURCE_IDENTITY),
        "predecessor_run_id": P344_PREDECESSOR_RUN_ID_HEX,
        "fresh_run_id": P345_RUN_ID_HEX,
        "run_id_hex": P345_RUN_ID_HEX,
        "frame_cancel": FRAME_CANCEL,
        "frame_cancel_ack": FRAME_CANCEL_ACK,
        "cancel_sequence": P345_CANCEL_SEQUENCE,
        "cancel_status_consumed": P345_CANCEL_STATUS_CONSUMED,
        "cancel_status_already_completed": P345_CANCEL_STATUS_ALREADY_COMPLETED,
        "cancel_status_none": P345_CANCEL_STATUS_NONE,
        "cancel_payload_size": P345_CANCEL_PAYLOAD_SIZE,
        "cancelled_flag": P345_CANCELLED_FLAG,
        "auth_domain_cancel": AUTH_DOMAIN_CANCEL.decode("ascii"),
        "sequence_3_fixed": True,
        "sequence_4_arbitrary_ash": True,
        "sequence_4_readonly_child": available,
        "sequence_5_fixed": True,
        "cancel_multiplexes_tty_and_pipe": True,
        "cancel_kills_owned_group": True,
        "cancel_preserves_exit_status": True,
        "cancel_no_scan_or_retry": True,
        "late_cancel_ack_status_1": True,
        "partial_cancel_stops": True,
        "command_timeout_sec": COMMAND_TIMEOUT_SEC,
        "max_output_bytes": MAX_OUTPUT_BYTES,
        "runtime_behavior_unchanged": False,
        "authentication_unchanged": True,
        "device_contact": False,
        "live_authorized": False,
        "child_source_bound": available,
    }
    if child is not None:
        value["child_source"] = identity(_validate_child_source(child))
    elif _AVAILABLE_CHILD_SOURCE is not None:
        value["child_source"] = identity(_AVAILABLE_CHILD_SOURCE)
    return value


__all__ = [
    "AUTH_DOMAIN_BOOT_ID", "AUTH_DOMAIN_CANCEL", "AUTH_DOMAIN_CLOSE",
    "AUTH_DOMAIN_EXEC", "AUTH_DOMAIN_OPEN", "AUTH_DOMAIN_READY",
    "AUTH_KEY_SCHEMA", "AUTH_KEY_SIZE", "AUTH_TAG_SIZE",
    "CATALOG", "CATALOG_ACTIONS", "COMMAND_TIMEOUT_SEC", "DEFAULT_COMMANDS",
    "DEVICE_BANNER", "EXIT", "FLAG_CANCELLED", "FRAME_AUTH", "FRAME_BOOT_ID",
    "FRAME_CANCEL", "FRAME_CANCEL_ACK", "FRAME_CHALLENGE", "FRAME_CLOSE",
    "FRAME_DATA", "FRAME_DONE", "FRAME_EXEC", "FRAME_EXIT", "FRAME_MAGIC",
    "FRAME_OPEN", "FRAME_READY", "FRAME_VERSION", "MAX_COMMAND_SIZE",
    "MAX_FRAME_PAYLOAD", "MAX_OUTPUT_BYTES", "RNG_EAGAIN_RETRY_LIMIT",
    "P335_BOOT_ID_SEQUENCE", "P335_BOOT_ID_SIZE", "P335_COMMANDS_PER_SESSION",
    "P335_FRAME_BOOT_ID", "P335_RUN_ID", "P335_RUN_ID_HEX",
    "P344_SOURCE_IDENTITY",
    "P344_PREDECESSOR_RUN_ID", "P344_PREDECESSOR_RUN_ID_HEX",
    "P345_CANCELLED_FLAG", "P345_CANCEL_SEQUENCE",
    "P345_CANCEL_STATUS_ALREADY_COMPLETED", "P345_CANCEL_STATUS_CONSUMED",
    "P345_CANCEL_STATUS_NONE",
    "P345_COMMAND", "P345_DEFAULT_COMMANDS", "P345_ENTRY", "P345_HELPER",
    "P345_HELPER_TEMPLATE", "P345_RUN_ID", "P345_RUN_ID_HEX",
    "RuntimeIdentityError", "audit_binding", "build_helper", "cancel_frame",
    "cancel_tag", "child_source", "completion_state", "decode_cancel_ack",
    "encode_cancel_frame", "encode_frame", "fixture_child_source", "identity",
    "materialize_helper", "parse_exit", "transform_artifacts",
    "transform_runtime_include", "validate_p345_runtime", "validate_transform",
]
__all__ += [
    f"{prefix}_RUN_ID{suffix}"
    for prefix in (
        "P328", "P329", "P330", "P331", "P332", "P333", "P334",
        "P335", "P336", "P337", "P338", "P339", "P340", "P341",
        "P342", "P343", "P344",
    )
    for suffix in ("", "_HEX")
    if f"{prefix}_RUN_ID{suffix}" not in __all__
]
