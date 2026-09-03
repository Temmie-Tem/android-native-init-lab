#!/usr/bin/env python3
"""Host-only P3.35 retained listener transform.

P3.35 is derived from the exact P3.34 runtime.  The authenticated S328
framing, HMAC domains, diagnostics, BusyBox child isolation, and initial
same-FD two-session shape remain inherited.  The bounded delta adds one
authenticated per-boot identity frame, binds the three fixed commands in the
device validator, and leaves an explicit low-duty listener after the two
initial sessions.  This module never contacts a device.
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
    "s22plus_fyg8_p334_first_read_rc_runtime.py"
)
SOURCE_IDENTITY = {
    "size": 14_564,
    "sha256": "05d21599c95a40abc679c3e5bd7ee0447dd708f52ac0734b53902f27f434c323",
}
P334_PREDECESSOR_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_PREDECESSOR_RUN_ID = bytes.fromhex(P334_PREDECESSOR_RUN_ID_HEX)
P335_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P335_RUN_ID = bytes.fromhex(P335_RUN_ID_HEX)

P335_FRAME_BOOT_ID = 0x87
P335_BOOT_ID_SEQUENCE = 2
P335_BOOT_ID_SIZE = 32
P335_COMMANDS_PER_SESSION = 3
P335_IDLE_POLL_SEC = 0.1
P335_DETAIL_BOOT_ID = 0xC350
P335_DETAIL_INITIAL_SESSION = 0xC351
P335_DETAIL_LISTENER_BANNER = 0xC352
P335_DETAIL_LISTENER_PROTOCOL = 0xC353
AUTH_DOMAIN_BOOT_ID = b"S22PLUS-FYG8-P335-AUTH-BOOT-ID-v1"

# Compatibility values consumed while the exact P3.34 observer is rebound.
# P3.35's public observer owns the three-session/reopen proof below; these
# names merely let the inherited two-session module load without becoming a
# second execution path.
SESSION_COUNT = 2
RECONNECT_COUNT = 0
MAX_SESSIONS = SESSION_COUNT
MAX_RECONNECTS = RECONNECT_COUNT
MAX_PHYSICAL_REOPENS = 1
PHYSICAL_REOPEN_COUNT = 1
LOGICAL_RESIDENT = True


class P335RuntimeError(ValueError):
    """The exact P3.34 predecessor or bounded P3.35 delta differs."""


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
        raise P335RuntimeError("P3.34 runtime source is unavailable") from exc
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
        raise P335RuntimeError("P3.34 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p334_runtime_bound_for_p335")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P335RuntimeError("P3.34 runtime source failed to load") from exc
    if getattr(module, "P334_RUN_ID_HEX", None) != P334_PREDECESSOR_RUN_ID_HEX:
        raise P335RuntimeError("P3.34 runtime binding differs")
    return module


def _replace_function(value: str, name: str, replacement: str) -> str:
    start = value.index(f"static int {name}") if name == "p328_command_valid" else value.index(
        f"static long {name}"
    )
    end = value.index("\n}\n", start) + 3
    return value[:start] + replacement + value[end:]


def _c_string(value: bytes) -> str:
    return "".join(f"\\x{byte:02x}" for byte in value)


_P334 = _load()
P334_ENTRY = _P334.P334_ENTRY
P334_DETAIL_ANCHOR = _P334.P334_DETAIL_ANCHOR
_ENTRY_TAIL = b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
if P334_ENTRY.count(_ENTRY_TAIL) != 1:
    raise P335RuntimeError("P3.34 publisher entry anchor differs")


def _derive_helper_template(predecessor: bytes) -> bytes:
    value = predecessor.decode("ascii")
    constants_anchor = "#define P330_RNG_EAGAIN_RETRY_LIMIT 64U\n"
    if value.count(constants_anchor) != 1:
        raise P335RuntimeError("P3.34 diagnostic constant anchor differs")
    constants = (
        constants_anchor
        + f"#define P335_FRAME_BOOT_ID 0x{P335_FRAME_BOOT_ID:02x}U\n"
        + f"#define P335_BOOT_ID_SEQUENCE {P335_BOOT_ID_SEQUENCE}U\n"
        + f"#define P335_BOOT_ID_SIZE {P335_BOOT_ID_SIZE}U\n"
        + f"#define P335_COMMANDS_PER_SESSION {P335_COMMANDS_PER_SESSION}U\n"
        + f"#define P335_DETAIL_BOOT_ID 0x{P335_DETAIL_BOOT_ID:04x}U\n"
        + f"#define P335_DETAIL_INITIAL_SESSION 0x{P335_DETAIL_INITIAL_SESSION:04x}U\n"
        + f"#define P335_DETAIL_LISTENER_BANNER 0x{P335_DETAIL_LISTENER_BANNER:04x}U\n"
        + f"#define P335_DETAIL_LISTENER_PROTOCOL 0x{P335_DETAIL_LISTENER_PROTOCOL:04x}U\n"
    )
    value = value.replace(constants_anchor, constants, 1)

    domain_anchor = (
        'static const char p328_auth_domain_close[] = '
        '"S22PLUS-FYG8-P328-AUTH-CLOSE-v1";\n'
    )
    if value.count(domain_anchor) != 1:
        raise P335RuntimeError("P3.34 HMAC domain anchor differs")
    value = value.replace(
        domain_anchor,
        domain_anchor
        + f'static const char p335_auth_domain_boot_id[] = "{AUTH_DOMAIN_BOOT_ID.decode("ascii")}";\n',
        1,
    )

    command_constants = (
        f'static const char p335_command_1[] = "{_c_string(DEFAULT_COMMANDS[0])}";\n'
        f'static const char p335_command_2[] = "{_c_string(DEFAULT_COMMANDS[1])}";\n'
        f'static const char p335_command_3[] = "{_c_string(DEFAULT_COMMANDS[2])}";\n'
    )
    command_anchor = "static uint16_t p328_load_le16"
    if value.count(command_anchor) != 1:
        raise P335RuntimeError("P3.34 helper codec anchor differs")
    value = value.replace(command_anchor, command_constants + command_anchor, 1)

    command_validator = f'''static int p335_command_valid(
    uint32_t sequence, const uint8_t *command, uint16_t length) {{
    const char *expected = NULL;
    size_t expected_length = 0U;
    if (sequence == 3U) {{
        expected = p335_command_1;
        expected_length = sizeof(p335_command_1) - 1U;
    }} else if (sequence == 4U) {{
        expected = p335_command_2;
        expected_length = sizeof(p335_command_2) - 1U;
    }} else if (sequence == 5U) {{
        expected = p335_command_3;
        expected_length = sizeof(p335_command_3) - 1U;
    }} else {{
        return 0;
    }}
    return command != NULL && length == expected_length
        && p260_bytes_equal(
            (const char *)command, expected, expected_length);
}}'''
    value = _replace_function(value, "p328_command_valid", command_validator)
    old_guard = (
        "if (tty_fd <= 2 || !p328_command_valid(input, input_length))\n"
        "        return -P260_EPROTO;"
    )
    if value.count(old_guard) != 1:
        raise P335RuntimeError("P3.34 command guard anchor differs")
    value = value.replace(
        old_guard,
        "if (tty_fd <= 2 || !p335_command_valid(sequence, input, input_length))\n"
        "        return -P260_EPROTO;",
        1,
    )

    console = f'''static long p335_framed_console(
    int tty_fd, const uint8_t *boot_id, uint8_t *open_seen) {{
    uint8_t type = 0U;
    uint32_t sequence = 0U;
    uint16_t length = 0U;
    uint8_t payload[P328_MAX_PAYLOAD];
    uint8_t nonce[P328_NONCE_SIZE];
    uint8_t expected_tag[P328_AUTH_TAG_SIZE];
    if (open_seen == NULL) return -P260_EPROTO;
    *open_seen = 0U;
    long rc = p328_read_frame(
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
    uint32_t rng_retries = 0U;
    for (;;) {{
        rc = p328_getrandom_nonce(nonce);
        if (rc == 0) break;
        if (rc != -EAGAIN || rng_retries == P330_RNG_EAGAIN_RETRY_LIMIT) {{
            (void)p330_write_diagnostic(
                tty_fd, P330_DIAG_RNG, (int32_t)rc);
            return rc;
        }}
        ++rng_retries;
        p282_poll_delay();
    }}
    rc = p330_write_diagnostic(
        tty_fd, P330_DIAG_RNG, (int32_t)rng_retries);
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
    if (boot_id == NULL) return -P260_EPROTO;
    uint8_t boot_payload[P335_BOOT_ID_SIZE + P328_AUTH_TAG_SIZE];
    memcpy(boot_payload, boot_id, P335_BOOT_ID_SIZE);
    p328_hmac_message(
        boot_payload + P335_BOOT_ID_SIZE,
        p335_auth_domain_boot_id,
        sizeof(p335_auth_domain_boot_id) - 1U,
        p328_run_id_bytes, nonce, P335_BOOT_ID_SEQUENCE, 1,
        boot_id, P335_BOOT_ID_SIZE);
    rc = p328_write_frame(
        tty_fd, P335_FRAME_BOOT_ID, P335_BOOT_ID_SEQUENCE,
        boot_payload, (uint16_t)sizeof(boot_payload));
    if (rc != 0) return rc;

    uint32_t expected_sequence = 3U;
    uint32_t handled = 0U;
    for (;;) {{
        rc = p328_read_frame(
            tty_fd, &type, &sequence, payload, &length);
        if (rc != 0 || sequence != expected_sequence)
            return rc != 0 ? rc : -P260_EPROTO;
        if (type == P328_FRAME_EXEC
            && handled < P335_COMMANDS_PER_SESSION
            && length >= P328_AUTH_TAG_SIZE) {{
            uint16_t command_length =
                (uint16_t)(length - P328_AUTH_TAG_SIZE);
            const uint8_t *command = payload + P328_AUTH_TAG_SIZE;
            if (!p335_command_valid(sequence, command, command_length))
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
            continue;
        }}
        if (type == P328_FRAME_CLOSE
            && sequence == P335_BOOT_ID_SEQUENCE + P335_COMMANDS_PER_SESSION + 1U
            && length == P328_AUTH_TAG_SIZE
            && handled == P335_COMMANDS_PER_SESSION) {{
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
        }}
        return -P260_EPROTO;
    }}
}}

static long p335_getrandom_boot_id(uint8_t boot_id[P335_BOOT_ID_SIZE]) {{
    if (boot_id == NULL) return -EINVAL;
    uint32_t retries = 0U;
    for (;;) {{
        long rc = p328_getrandom_nonce(boot_id);
        if (rc == 0) return 0;
        if (rc != -EAGAIN || retries == P330_RNG_EAGAIN_RETRY_LIMIT)
            return rc;
        ++retries;
        p282_poll_delay();
    }}
}}

static int p335_is_waiting_error(long rc) {{
    return rc == -EIO || rc == -ETIMEDOUT
        || rc == -S22PLUS_P318_ERRNO_EPIPE
        || rc == -ENODEV || rc == -EAGAIN || rc == -P260_EINTR;
}}

static int p335_banner_is_waiting(unsigned int outcome) {{
    return outcome == S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE
        || outcome == S22PLUS_P318_BANNER_ERROR_EINTR_DEADLINE
        || outcome == S22PLUS_P318_BANNER_ERROR_EPIPE
        || outcome == S22PLUS_P318_BANNER_ERROR_ENODEV
        || outcome == S22PLUS_P318_BANNER_ERROR_ETIMEDOUT
        || outcome == S22PLUS_P318_BANNER_ERROR_ZERO_WRITE;
}}
'''
    value = _replace_function(value, "p328_framed_console", console)
    return value.encode("ascii")


P334_HELPER_TEMPLATE = _P334.P334_HELPER_TEMPLATE
P335_DEFAULT_COMMANDS = (
    _P334.DEFAULT_COMMANDS[0],
    _P334.DEFAULT_COMMANDS[1],
    f"/bin/busybox echo P328-NONCE {P335_RUN_ID_HEX}".encode("ascii"),
)
DEFAULT_COMMANDS = P335_DEFAULT_COMMANDS
P335_HELPER_TEMPLATE = _derive_helper_template(P334_HELPER_TEMPLATE)
P335_HELPER = P335_HELPER_TEMPLATE
P328_HELPER_TEMPLATE = P335_HELPER_TEMPLATE
P328_HELPER = P335_HELPER_TEMPLATE
P330_HELPER_TEMPLATE = P335_HELPER_TEMPLATE
P330_HELPER = P335_HELPER_TEMPLATE
P332_HELPER_TEMPLATE = P335_HELPER_TEMPLATE
P332_HELPER = P335_HELPER_TEMPLATE
P333_HELPER_TEMPLATE = P335_HELPER_TEMPLATE
P333_HELPER = P335_HELPER_TEMPLATE
P334_HELPER = P334_HELPER_TEMPLATE

P335_ENTRY = (
    b"    uint8_t p335_boot_id[P335_BOOT_ID_SIZE] = {0};\n"
    b"    long p335_boot_id_rc = p335_getrandom_boot_id(p335_boot_id);\n"
    b"    if (p335_boot_id_rc != 0)\n"
    b"        p290_fail_next(P335_DETAIL_BOOT_ID);\n"
    b"    long p335_first_session_rc = -EIO;\n"
    b"    long p335_second_session_rc = -EIO;\n"
    b"    uint8_t p335_first_open_seen = 0U;\n"
    b"    uint8_t p335_second_open_seen = 0U;\n"
    b"    struct s22plus_p318_banner_result p335_banner_1 =\n"
    b"        s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p335_banner_1.outcome == S22PLUS_P318_BANNER_WRITTEN) {\n"
    b"        if (p330_write_diagnostic(tty_fd, 0U, 0) == 0)\n"
    b"            p335_first_session_rc = p335_framed_console(\n"
    b"                tty_fd, p335_boot_id, &p335_first_open_seen);\n"
    b"        else\n"
    b"            p335_first_session_rc = -EIO;\n"
    b"    }\n"
    b"    if (p335_first_session_rc != 0\n"
    b"        && (p335_first_open_seen\n"
    b"            || !p335_is_waiting_error(p335_first_session_rc)))\n"
    b"        p290_fail_next(P335_DETAIL_INITIAL_SESSION);\n"
    b"    if (p335_first_session_rc == 0) {\n"
    b"        struct s22plus_p318_banner_result p335_banner_2 =\n"
    b"            s22plus_p318_banner_attempt(tty_fd);\n"
    b"        if (p335_banner_2.outcome == S22PLUS_P318_BANNER_WRITTEN) {\n"
    b"            if (p330_write_diagnostic(tty_fd, 0U, 0) == 0)\n"
    b"                p335_second_session_rc = p335_framed_console(\n"
    b"                    tty_fd, p335_boot_id, &p335_second_open_seen);\n"
    b"            else\n"
    b"                p335_second_session_rc = -EIO;\n"
    b"        }\n"
    b"    }\n"
    b"    if (p335_first_session_rc == 0\n"
    b"        && p335_second_session_rc != 0\n"
    b"        && (p335_second_open_seen\n"
    b"            || !p335_is_waiting_error(p335_second_session_rc)))\n"
    b"        p290_fail_next(P335_DETAIL_INITIAL_SESSION);\n"
    b"    if (p335_first_session_rc == 0 && p335_second_session_rc == 0) {\n"
    b"        for (;;) {\n"
    b"            p282_poll_delay();\n"
    b"            struct s22plus_p318_banner_result p335_listener_banner =\n"
    b"                s22plus_p318_banner_attempt(tty_fd);\n"
    b"            if (p335_listener_banner.outcome !=\n"
    b"                S22PLUS_P318_BANNER_WRITTEN) {\n"
    b"                if (p335_banner_is_waiting(\n"
    b"                        p335_listener_banner.outcome)) {\n"
    b"                    p282_poll_delay();\n"
    b"                    continue;\n"
    b"                }\n"
    b"                p290_fail_next(P335_DETAIL_LISTENER_BANNER);\n"
    b"            }\n"
    b"            uint8_t p335_listener_open_seen = 0U;\n"
    b"            long p335_listener_diag_rc =\n"
    b"                p330_write_diagnostic(tty_fd, 0U, 0);\n"
    b"            if (p335_listener_diag_rc != 0) {\n"
    b"                if (p335_is_waiting_error(p335_listener_diag_rc)) {\n"
    b"                    p282_poll_delay();\n"
    b"                    continue;\n"
    b"                }\n"
    b"                p290_fail_next(P335_DETAIL_LISTENER_PROTOCOL);\n"
    b"            }\n"
    b"            long p335_listener_rc = p335_framed_console(\n"
    b"                tty_fd, p335_boot_id, &p335_listener_open_seen);\n"
    b"            if (p335_listener_rc == 0)\n"
    b"                continue;\n"
    b"            if (!p335_listener_open_seen\n"
    b"                && p335_is_waiting_error(p335_listener_rc)) {\n"
    b"                p282_poll_delay();\n"
    b"                continue;\n"
    b"            }\n"
    b"            p290_fail_next(P335_DETAIL_LISTENER_PROTOCOL);\n"
    b"        }\n"
    b"    }\n"
    + _ENTRY_TAIL
)

P335_DETAIL_ANCHOR = (
    b"    if (s22plus_max77705_p319_stock_encode(\n"
    b"            &witness, terminal_state, envelope, &detail) != 0)\n"
    b"        p290_fail_next(S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS);\n"
    b"    detail = 0xbfffU;\n"
    b"    p319_stock_bypass_to_pair();\n"
)


CONTRACT_ID = "s22plus-fyg8-p335-retained-listener-runtime-v1"
SCHEMA = CONTRACT_ID
TARGET = _P334.TARGET
RUNTIME_KEY = _P334.RUNTIME_KEY
PUBLISHER = _P334.PUBLISHER
AUTH_KEY_PLACEHOLDER = _P334.AUTH_KEY_PLACEHOLDER
AUTH_KEY_SIZE = _P334.AUTH_KEY_SIZE
AUTH_TAG_SIZE = _P334.AUTH_TAG_SIZE
NONCE_SIZE = _P334.NONCE_SIZE
FRAME_MAGIC = _P334.FRAME_MAGIC
FRAME_VERSION = _P334.FRAME_VERSION
FRAME_OPEN = _P334.FRAME_OPEN
FRAME_EXEC = _P334.FRAME_EXEC
FRAME_CLOSE = _P334.FRAME_CLOSE
FRAME_AUTH = _P334.FRAME_AUTH
FRAME_READY = _P334.FRAME_READY
FRAME_DATA = _P334.FRAME_DATA
FRAME_EXIT = _P334.FRAME_EXIT
FRAME_DONE = _P334.FRAME_DONE
FRAME_CHALLENGE = _P334.FRAME_CHALLENGE
FRAME_HEADER_SIZE = _P334.FRAME_HEADER_SIZE
MAX_COMMAND_SIZE = _P334.MAX_COMMAND_SIZE
MAX_COMMANDS = _P334.MAX_COMMANDS
MAX_FRAME_PAYLOAD = _P334.MAX_FRAME_PAYLOAD
MAX_OUTPUT_BYTES = _P334.MAX_OUTPUT_BYTES
COMMAND_TIMEOUT_SEC = _P334.COMMAND_TIMEOUT_SEC
AUTH_DOMAIN_OPEN = _P334.AUTH_DOMAIN_OPEN
AUTH_DOMAIN_READY = _P334.AUTH_DOMAIN_READY
AUTH_DOMAIN_EXEC = _P334.AUTH_DOMAIN_EXEC
AUTH_DOMAIN_CLOSE = _P334.AUTH_DOMAIN_CLOSE
DIAGNOSTIC_FRAME_TYPE = _P334.DIAGNOSTIC_FRAME_TYPE
DIAGNOSTIC_PAYLOAD_SIZE = _P334.DIAGNOSTIC_PAYLOAD_SIZE
DIAGNOSTIC_STAGE_OPEN_PARSED = _P334.DIAGNOSTIC_STAGE_OPEN_PARSED
DIAGNOSTIC_STAGE_RNG = _P334.DIAGNOSTIC_STAGE_RNG
DIAGNOSTIC_STAGE_CONSOLE_ENTER = _P334.DIAGNOSTIC_STAGE_CONSOLE_ENTER
RNG_EAGAIN_RETRY_LIMIT = _P334.RNG_EAGAIN_RETRY_LIMIT
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P335_RUN_ID_HEX}\n".encode("ascii")

P334_RUN_ID_HEX = P335_RUN_ID_HEX
P334_RUN_ID = P335_RUN_ID
P333_RUN_ID_HEX = P335_RUN_ID_HEX
P333_RUN_ID = P335_RUN_ID
P332_RUN_ID_HEX = P335_RUN_ID_HEX
P332_RUN_ID = P335_RUN_ID
P330_RUN_ID_HEX = P335_RUN_ID_HEX
P330_RUN_ID = P335_RUN_ID
P328_RUN_ID_HEX = P335_RUN_ID_HEX
P328_RUN_ID = P335_RUN_ID
DEFAULT_COMMANDS = P335_DEFAULT_COMMANDS
P334_DEFAULT_COMMANDS = P335_DEFAULT_COMMANDS
P335_ARTIFACT_SOURCE = Path(__file__).resolve()
P334_ARTIFACT_SOURCE = _P334.P334_ARTIFACT_SOURCE

_AUTH_KEY_DECL_PREFIX = (
    b"static const uint8_t p328_auth_key[P328_AUTH_KEY_SIZE] = { "
)
_AUTH_KEY_DECL_SUFFIX = b" };\n"


def _key_initializer(auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != AUTH_KEY_SIZE:
        raise P335RuntimeError("auth_key must be exactly 32 bytes")
    return ", ".join(f"0x{byte:02x}U" for byte in auth_key).encode("ascii")


def auth_key_sha256(auth_key: bytes) -> str:
    _key_initializer(auth_key)
    return hashlib.sha256(auth_key).hexdigest()


def _materialized_key(value: bytes) -> bytes:
    try:
        start = value.index(_AUTH_KEY_DECL_PREFIX) + len(_AUTH_KEY_DECL_PREFIX)
        end = value.index(_AUTH_KEY_DECL_SUFFIX, start)
    except ValueError as exc:
        raise P335RuntimeError("materialized key declaration is missing") from exc
    fields = value[start:end].split(b", ")
    if len(fields) != AUTH_KEY_SIZE:
        raise P335RuntimeError("materialized key size differs")
    result = bytearray()
    for field in fields:
        if not field.startswith(b"0x") or not field.endswith(b"U"):
            raise P335RuntimeError("materialized key literal differs")
        try:
            number = int(field[2:-1], 16)
        except ValueError as exc:
            raise P335RuntimeError("materialized key literal is invalid") from exc
        if not 0 <= number <= 0xFF:
            raise P335RuntimeError("materialized key byte is out of range")
        result.append(number)
    return bytes(result)


def materialize_helper(auth_key: bytes) -> bytes:
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    if P335_HELPER_TEMPLATE.count(marker) != 1:
        raise P335RuntimeError("key marker multiplicity differs")
    return P335_HELPER_TEMPLATE.replace(marker, _key_initializer(auth_key), 1)


def _validate_p334_predecessor(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        result = dict(
            _P334.validate_p334_runtime(
                value, auth_key_sha256=auth_key_sha256
            )
        )
    except Exception as exc:
        raise P335RuntimeError(f"P3.34 predecessor differs: {exc}") from exc
    return result


def _validate_restored_p334(
    value: bytes, *, auth_key_sha256: str | None = None
) -> None:
    key = _materialized_key(value)
    restored = value.replace(materialize_helper(key), _P334.materialize_helper(key), 1)
    restored = restored.replace(P335_ENTRY, P334_ENTRY, 1).replace(
        P335_DETAIL_ANCHOR, P334_DETAIL_ANCHOR, 1
    )
    try:
        _validate_p334_predecessor(restored, auth_key_sha256=auth_key_sha256)
    except Exception as exc:
        raise P335RuntimeError(f"P3.34 helper/entry differs: {exc}") from exc


def validate_p335_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes:
        raise P335RuntimeError("P3.35 runtime must be bytes")
    marker = AUTH_KEY_PLACEHOLDER.encode("ascii")
    helper_prefix, helper_suffix = P335_HELPER_TEMPLATE.split(marker, 1)
    if (
        value.count(PUBLISHER) != 1
        or value.count(P335_ENTRY) != 1
        or value.count(P334_ENTRY) != 0
        or value.count(P335_DETAIL_ANCHOR) != 1
        or value.count(P334_DETAIL_ANCHOR) != 0
        or value.count(helper_prefix) != 1
        or value.count(helper_suffix) != 1
    ):
        raise P335RuntimeError("P3.35 runtime anchors differ")
    key = _materialized_key(value)
    key_digest = hashlib.sha256(key).hexdigest()
    if auth_key_sha256 is not None and auth_key_sha256 != key_digest:
        raise P335RuntimeError("P3.35 materialized auth key digest differs")
    required = (
        f"P335_FRAME_BOOT_ID 0x{P335_FRAME_BOOT_ID:02x}U".encode("ascii"),
        f"P335_BOOT_ID_SEQUENCE {P335_BOOT_ID_SEQUENCE}U".encode("ascii"),
        f"P335_BOOT_ID_SIZE {P335_BOOT_ID_SIZE}U".encode("ascii"),
        f"P335_COMMANDS_PER_SESSION {P335_COMMANDS_PER_SESSION}U".encode("ascii"),
        b"p335_auth_domain_boot_id",
        b"p335_getrandom_boot_id",
        b"p335_is_waiting_error",
        b"p335_banner_is_waiting",
        b"static int p335_command_valid(",
        b"p335_command_valid(sequence, input, input_length)",
        b"expected_sequence = 3U",
        b"p335_framed_console(",
        b"P335_FRAME_BOOT_ID, P335_BOOT_ID_SEQUENCE",
        b"p328_hmac_message(",
        b"for (;;) {",
    )
    if any(item not in value for item in required):
        raise P335RuntimeError("P3.35 helper/listener anchors differ")
    if value.count(b"p335_command_1") < 2 or value.count(b"p335_command_2") < 2:
        raise P335RuntimeError("P3.35 fixed command anchors differ")
    if value.count(b"p335_command_3") < 2:
        raise P335RuntimeError("P3.35 third command anchor differs")
    if P335_ENTRY.count(b"s22plus_p318_banner_attempt(tty_fd);") != 3:
        raise P335RuntimeError("P3.35 banner/session count differs")
    if P335_ENTRY.count(b"p335_framed_console(") != 3:
        raise P335RuntimeError("P3.35 session call count differs")
    if P335_ENTRY.count(b"p330_write_diagnostic(tty_fd, 0U, 0)") != 3:
        raise P335RuntimeError("P3.35 stage-0 diagnostic count differs")
    if b"p328_framed_console" in P335_ENTRY or b"close(" in P335_ENTRY or b"open(" in P335_ENTRY:
        raise P335RuntimeError("P3.35 entry adds an unapproved transport path")
    if P335_ENTRY.count(b"for (;;) {") != 1 or b"continue;" not in P335_ENTRY:
        raise P335RuntimeError("P3.35 listener loop differs")
    _validate_restored_p334(value, auth_key_sha256=key_digest)
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P335_RUN_ID_HEX,
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
        "auth_algorithm": "hmac-sha256",
        "per_session_random_nonce": True,
        "per_boot_identity": True,
        "per_boot_identity_size": P335_BOOT_ID_SIZE,
        "per_boot_identity_frame": P335_FRAME_BOOT_ID,
        "session_count": 2,
        "listener": True,
        "listener_low_duty": True,
        "listener_replays_commands": False,
        "reconnect_count": 1,
        "physical_reopen_count": 1,
        "same_tty_fd_initial_sessions": True,
        "persistent_state": False,
        "interactive_pty": False,
        "stdin_dev_null": True,
        "arbitrary_file_transfer": False,
        "child_kill_and_reap": True,
        "child_session_isolated": True,
        "descendant_group_cleanup": True,
        "carrier_path_retained": True,
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    predecessor = _validate_p334_predecessor(
        before, auth_key_sha256=auth_key_sha256
    )
    key = _materialized_key(before)
    expected = before.replace(
        _P334.materialize_helper(key), materialize_helper(key), 1
    ).replace(P334_ENTRY, P335_ENTRY, 1).replace(
        P334_DETAIL_ANCHOR, P335_DETAIL_ANCHOR, 1
    )
    if after != expected:
        raise P335RuntimeError("P3.35 delta exceeds helper and publisher entry")
    result = validate_p335_runtime(after, auth_key_sha256=auth_key_sha256)
    return result | {
        "changed_anchors": [
            "p334_authenticated_helper",
            "p334_publisher_entry",
            "p334_stock_terminal_detail",
        ],
        "source_identity": identity(before),
        "target_identity": identity(after),
        "predecessor": predecessor,
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    predecessor = _validate_p334_predecessor(value)
    key = _key_initializer(auth_key)
    del key
    materialized_predecessor = _P334.materialize_helper(auth_key)
    if value.count(materialized_predecessor) != 1:
        raise P335RuntimeError("P3.34 helper is not materialized with auth_key")
    result = value.replace(
        materialized_predecessor, materialize_helper(auth_key), 1
    ).replace(P334_ENTRY, P335_ENTRY, 1).replace(
        P334_DETAIL_ANCHOR, P335_DETAIL_ANCHOR, 1
    )
    validate_transform(
        value, result, auth_key_sha256=auth_key_sha256(auth_key)
    )
    del predecessor
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P335RuntimeError("P3.34 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise P335RuntimeError("P3.35 source delta differs")
    return result


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
        "DIAGNOSTIC_FRAME_TYPE",
        "DIAGNOSTIC_PAYLOAD_SIZE",
        "DIAGNOSTIC_STAGE_CONSOLE_ENTER",
        "DIAGNOSTIC_STAGE_OPEN_PARSED",
        "DIAGNOSTIC_STAGE_RNG",
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
        "P334_ARTIFACT_SOURCE",
        "P334_DEFAULT_COMMANDS",
        "P334_DETAIL_ANCHOR",
        "P334_ENTRY",
        "P334_HELPER_TEMPLATE",
        "P334_PREDECESSOR_RUN_ID",
        "P334_PREDECESSOR_RUN_ID_HEX",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P335_ARTIFACT_SOURCE",
        "P335_BOOT_ID_SEQUENCE",
        "P335_BOOT_ID_SIZE",
        "P335_COMMANDS_PER_SESSION",
        "P335_DEFAULT_COMMANDS",
        "P335_DETAIL_BOOT_ID",
        "P335_DETAIL_ANCHOR",
        "P335_DETAIL_INITIAL_SESSION",
        "P335_DETAIL_LISTENER_BANNER",
        "P335_DETAIL_LISTENER_PROTOCOL",
        "P335_ENTRY",
        "P335_FRAME_BOOT_ID",
        "P335_HELPER",
        "P335_HELPER_TEMPLATE",
        "P335_RUN_ID",
        "P335_RUN_ID_HEX",
        "P335RuntimeError",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P330_RUN_ID",
        "P330_RUN_ID_HEX",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "RNG_EAGAIN_RETRY_LIMIT",
        "RUNTIME_KEY",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "TARGET",
        "auth_key_sha256",
        "identity",
        "materialize_helper",
        "transform_artifacts",
        "transform_runtime_include",
        "validate_p335_runtime",
        "validate_transform",
    }
)
