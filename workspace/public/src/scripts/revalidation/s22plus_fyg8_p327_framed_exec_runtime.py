#!/usr/bin/env python3
"""Transform the proved P3.26 console into one bounded framed exec session.

P3.27 keeps the P3.26 ACM topology, banner, BusyBox payload and Carrier path.
It replaces only the fixed PING/SHELL exchange with a small run-bound protocol:
OPEN, three fixed EXEC requests, streamed DATA and one EXIT per request, then
CLOSE/DONE.  The PID-1 parent owns the command timeout, output bound and child
reap.  P3.27 deliberately does not accept a caller-selected shell command.
This module only transforms host-side source bytes; it contacts no device and
grants no live authority.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import s22plus_fyg8_p326_bidirectional_console_runtime as p326


CONTRACT_ID = "s22plus-fyg8-p327-framed-exec-runtime-v1"
SCHEMA = CONTRACT_ID
TARGET = p326.TARGET
RUNTIME_KEY = p326.RUNTIME_KEY

P327_RUN_ID_HEX = "c327f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P327_RUN_ID = bytes.fromhex(P327_RUN_ID_HEX)
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P327_RUN_ID_HEX}\n".encode("ascii")

FRAME_MAGIC = b"S327"
FRAME_VERSION = 1
FRAME_OPEN = 1
FRAME_EXEC = 2
FRAME_CLOSE = 3
FRAME_READY = 0x81
FRAME_DATA = 0x82
FRAME_EXIT = 0x83
FRAME_DONE = 0x84
FRAME_HEADER_SIZE = 16
MAX_FRAME_PAYLOAD = 1024
MAX_COMMAND_SIZE = 1023
MAX_COMMANDS = 3
COMMAND_TIMEOUT_SEC = 10
MAX_OUTPUT_BYTES = 128 * 1024

DEFAULT_COMMANDS = (
    b"/bin/busybox id",
    b"/bin/busybox uname -a",
    f"/bin/busybox echo P327-NONCE {P327_RUN_ID_HEX}".encode("ascii"),
)

P326_SOURCE = Path(p326.__file__).resolve()
P326_SOURCE_IDENTITY = {
    "size": 9_043,
    "sha256": "7898fe3ab728bed2a50790a107928835852e7d84dffe1a7646167efa89eccdb6",
}
P326_RUNTIME_IDENTITY = {
    "size": 457_784,
    "sha256": "20dd261f0acd065c711a327bbbe3f7c03452db3979e12b443f36d4b02ab0a93a",
}

PUBLISHER = p326.PUBLISHER
P327_ENTRY = (
    b"    struct s22plus_p318_banner_result p327_banner =\n"
    b"        s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p327_banner.outcome == S22PLUS_P318_BANNER_WRITTEN)\n"
    b"        (void)p327_framed_console(tty_fd);\n"
    b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
)


def _c_string(value: bytes) -> str:
    return "".join(f"\\x{byte:02x}" for byte in value)


P327_HELPER = f'''/* P3.27 bounded framed PID1 BusyBox command session. */
#define P327_MAGIC_0 0x53U
#define P327_MAGIC_1 0x33U
#define P327_MAGIC_2 0x32U
#define P327_MAGIC_3 0x37U
#define P327_FRAME_VERSION 1U
#define P327_FRAME_OPEN 1U
#define P327_FRAME_EXEC 2U
#define P327_FRAME_CLOSE 3U
#define P327_FRAME_READY 0x81U
#define P327_FRAME_DATA 0x82U
#define P327_FRAME_EXIT 0x83U
#define P327_FRAME_DONE 0x84U
#define P327_HEADER_SIZE {FRAME_HEADER_SIZE}U
#define P327_MAX_PAYLOAD {MAX_FRAME_PAYLOAD}U
#define P327_MAX_COMMAND {MAX_COMMAND_SIZE}U
#define P327_MAX_COMMANDS {MAX_COMMANDS}U
#define P327_INPUT_DEADLINE_SEC 30LL
#define P327_COMMAND_TIMEOUT_SEC {COMMAND_TIMEOUT_SEC}LL
#define P327_MAX_OUTPUT {MAX_OUTPUT_BYTES}U
#define P327_FLAG_TIMEOUT 0x01U
#define P327_FLAG_TRUNCATED 0x02U
#define P327_FLAG_EXEC_FAILURE 0x04U
#define P327_ECHILD 10
#define P327_NR_SETSID 157

#define p327_run_id k_run_id
static const char p327_command_1[] = "{_c_string(DEFAULT_COMMANDS[0])}";
static const char p327_command_2[] = "{_c_string(DEFAULT_COMMANDS[1])}";
static const char p327_command_3[] = "{_c_string(DEFAULT_COMMANDS[2])}";

static uint16_t p327_load_le16(const uint8_t *value) {{
    return (uint16_t)value[0] | ((uint16_t)value[1] << 8);
}}

static uint32_t p327_load_le32(const uint8_t *value) {{
    return (uint32_t)value[0] | ((uint32_t)value[1] << 8)
        | ((uint32_t)value[2] << 16) | ((uint32_t)value[3] << 24);
}}

static void p327_store_le16(uint8_t *value, uint16_t input) {{
    value[0] = (uint8_t)input;
    value[1] = (uint8_t)(input >> 8);
}}

static void p327_store_le32(uint8_t *value, uint32_t input) {{
    value[0] = (uint8_t)input;
    value[1] = (uint8_t)(input >> 8);
    value[2] = (uint8_t)(input >> 16);
    value[3] = (uint8_t)(input >> 24);
}}

static void p327_store_le64(uint8_t *value, uint64_t input) {{
    p327_store_le32(value, (uint32_t)input);
    p327_store_le32(value + 4U, (uint32_t)(input >> 32));
}}

static uint32_t p327_crc32_update(
    uint32_t crc, const uint8_t *data, size_t length) {{
    crc = ~crc;
    for (size_t index = 0; index < length; ++index) {{
        crc ^= data[index];
        for (unsigned int bit = 0; bit < 8U; ++bit) {{
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1U);
            crc = (crc >> 1) ^ (0xedb88320U & mask);
        }}
    }}
    return ~crc;
}}

static uint32_t p327_frame_crc(
    const uint8_t header[P327_HEADER_SIZE],
    const uint8_t *payload, size_t length) {{
    uint32_t crc = p327_crc32_update(0U, header, 12U);
    return p327_crc32_update(crc, payload, length);
}}

static long p327_read_exact(
    int fd, uint8_t *output, size_t size, long timeout_sec) {{
    struct timespec64 deadline = {{0}};
    long rc = p282_deadline_after(timeout_sec, &deadline);
    if (rc != 0) return rc;
    size_t used = 0U;
    while (used < size) {{
        long amount = sys_read(fd, output + used, size - used);
        if (amount > 0) {{
            if ((size_t)amount > size - used) return -EIO;
            used += (size_t)amount;
            continue;
        }}
        if (amount != -EAGAIN && amount != -P260_EINTR)
            return amount == 0 ? -EIO : amount;
        if (p282_deadline_expired(&deadline)) return -ETIMEDOUT;
        p282_poll_delay();
    }}
    return 0;
}}

static long p327_read_frame(
    int fd, uint8_t *type, uint32_t *sequence,
    uint8_t payload[P327_MAX_PAYLOAD], uint16_t *payload_length) {{
    uint8_t header[P327_HEADER_SIZE];
    long rc = p327_read_exact(
        fd, header, sizeof(header), P327_INPUT_DEADLINE_SEC);
    if (rc != 0) return rc;
    uint16_t length = p327_load_le16(header + 6U);
    if (header[0] != P327_MAGIC_0 || header[1] != P327_MAGIC_1
        || header[2] != P327_MAGIC_2 || header[3] != P327_MAGIC_3
        || header[4] != P327_FRAME_VERSION || length > P327_MAX_PAYLOAD)
        return -P260_EPROTO;
    rc = p327_read_exact(fd, payload, length, P327_INPUT_DEADLINE_SEC);
    if (rc != 0) return rc;
    if (p327_frame_crc(header, payload, length)
        != p327_load_le32(header + 12U)) return -P260_EPROTO;
    *type = header[5];
    *sequence = p327_load_le32(header + 8U);
    *payload_length = length;
    return 0;
}}

static long p327_write_frame(
    int fd, uint8_t type, uint32_t sequence,
    const uint8_t *payload, uint16_t payload_length) {{
    if (payload_length > P327_MAX_PAYLOAD
        || (payload_length != 0U && payload == NULL)) return -EINVAL;
    uint8_t header[P327_HEADER_SIZE] = {{
        P327_MAGIC_0, P327_MAGIC_1, P327_MAGIC_2, P327_MAGIC_3,
        P327_FRAME_VERSION, type,
    }};
    p327_store_le16(header + 6U, payload_length);
    p327_store_le32(header + 8U, sequence);
    p327_store_le32(header + 12U, p327_frame_crc(
        header, payload, payload_length));
    long rc = p260_write_all(
        fd, (const char *)header, sizeof(header), 1);
    if (rc == 0 && payload_length != 0U)
        rc = p260_write_all(
            fd, (const char *)payload, payload_length, 1);
    return rc;
}}

static uint64_t p327_elapsed_ms(
    const struct timespec64 *start, const struct timespec64 *end) {{
    int64_t seconds = end->tv_sec - start->tv_sec;
    int64_t nanoseconds = end->tv_nsec - start->tv_nsec;
    if (nanoseconds < 0) {{ --seconds; nanoseconds += 1000000000LL; }}
    if (seconds < 0) return 0U;
    return (uint64_t)seconds * 1000U + (uint64_t)nanoseconds / 1000000U;
}}

static long p327_reap_after_kill(long pid, int *status) {{
    struct timespec64 deadline = {{0}};
    long rc = p282_deadline_after(1LL, &deadline);
    if (rc != 0) return rc;
    while (!p282_deadline_expired(&deadline)) {{
        long waited = sys_wait4(pid, status, WNOHANG);
        if (waited == pid) return 0;
        if (waited < 0 && waited != -P260_EINTR) return waited;
        p282_poll_delay();
    }}
    return -ETIMEDOUT;
}}

static int p327_command_valid(
    uint32_t sequence, const uint8_t *command, uint16_t length) {{
    const char *expected = NULL;
    size_t expected_length = 0U;
    if (sequence == 1U) {{
        expected = p327_command_1;
        expected_length = sizeof(p327_command_1) - 1U;
    }} else if (sequence == 2U) {{
        expected = p327_command_2;
        expected_length = sizeof(p327_command_2) - 1U;
    }} else if (sequence == 3U) {{
        expected = p327_command_3;
        expected_length = sizeof(p327_command_3) - 1U;
    }} else {{
        return 0;
    }}
    return length == expected_length
        && p260_bytes_equal(
            (const char *)command, expected, expected_length);
}}

static long p327_dup_to(int source, int target) {{
    return source == target ? target : sys_dup3(source, target, 0);
}}

static long p327_setsid(void) {{
    return syscall6(P327_NR_SETSID, 0, 0, 0, 0, 0, 0);
}}

static long p327_cleanup_process_group(long pid) {{
    (void)sys_kill(-pid, SIGKILL);
    struct timespec64 deadline = {{0}};
    long rc = p282_deadline_after(1LL, &deadline);
    if (rc != 0) return rc;
    for (;;) {{
        int status = 0;
        long waited = sys_wait4(-pid, &status, WNOHANG);
        if (waited > 0) continue;
        if (waited == -P327_ECHILD) return 0;
        if (waited < 0 && waited != -P260_EINTR) return waited;
        if (p282_deadline_expired(&deadline)) return -ETIMEDOUT;
        p282_poll_delay();
    }}
}}

static long p327_exec_command(
    int tty_fd, uint32_t sequence,
    const uint8_t *input, uint16_t input_length) {{
    if (tty_fd <= 2 || !p327_command_valid(sequence, input, input_length))
        return -P260_EPROTO;
    char command[P327_MAX_COMMAND + 1U];
    memcpy(command, input, input_length);
    command[input_length] = '\\0';

    int pipe_fds[2] = {{-1, -1}};
    long rc = sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK);
    if (rc != 0) return rc;
    struct timespec64 started = {{0}};
    rc = p241_clock_gettime(&started);
    if (rc != 0) {{
        (void)sys_close(pipe_fds[0]);
        (void)sys_close(pipe_fds[1]);
        return rc;
    }}
    long pid = sys_clone();
    if (pid < 0) {{
        (void)sys_close(pipe_fds[0]);
        (void)sys_close(pipe_fds[1]);
        return pid;
    }}
    if (pid == 0) {{
        (void)sys_close(pipe_fds[0]);
        if (p327_setsid() < 0) sys_exit(126);
        if (p327_dup_to(pipe_fds[1], 1) != 1
            || p327_dup_to(pipe_fds[1], 2) != 2) sys_exit(126);
        if (pipe_fds[1] > 2) (void)sys_close(pipe_fds[1]);
        long null_fd = sys_openat("/dev/null", O_RDONLY | O_CLOEXEC, 0);
        if (null_fd < 0 || p327_dup_to((int)null_fd, 0) != 0) sys_exit(126);
        if (null_fd != 0) (void)sys_close((int)null_fd);
        (void)sys_close(tty_fd);
        char *const argv[] = {{
            (char *)"/bin/busybox", (char *)"ash", (char *)"-c",
            command, NULL,
        }};
        char *const envp[] = {{
            (char *)"PATH=/bin", (char *)"HOME=/", (char *)"TERM=dumb", NULL,
        }};
        (void)sys_execve("/bin/busybox", argv, envp);
        sys_exit(127);
    }}
    (void)sys_close(pipe_fds[1]);

    struct timespec64 deadline = started;
    deadline.tv_sec += P327_COMMAND_TIMEOUT_SEC;
    uint32_t forwarded = 0U;
    uint32_t flags = 0U;
    int status = 0;
    int reaped = 0;
    int timeout_attempted = 0;
    uint8_t output[P327_MAX_PAYLOAD];
    for (;;) {{
        long amount = sys_read(pipe_fds[0], output, sizeof(output));
        if (amount > 0) {{
            if ((size_t)amount > sizeof(output)) {{ rc = -EIO; break; }}
            uint32_t allowed = (uint32_t)amount;
            if (forwarded >= P327_MAX_OUTPUT) allowed = 0U;
            else if (allowed > P327_MAX_OUTPUT - forwarded)
                allowed = P327_MAX_OUTPUT - forwarded;
            if (allowed != 0U) {{
                rc = p327_write_frame(
                    tty_fd, P327_FRAME_DATA, sequence, output,
                    (uint16_t)allowed);
                if (rc != 0) break;
                forwarded += allowed;
            }}
            if (allowed != (uint32_t)amount) flags |= P327_FLAG_TRUNCATED;
        }}
        if (amount < 0 && amount != -EAGAIN && amount != -P260_EINTR) {{
            rc = amount;
            break;
        }}
        if (!reaped) {{
            long waited = sys_wait4(pid, &status, WNOHANG);
            if (waited == pid) reaped = 1;
            else if (waited < 0 && waited != -P260_EINTR) {{
                rc = waited;
                break;
            }}
        }}
        if (reaped) {{
            if (amount == 0 || amount == -EAGAIN) break;
            continue;
        }}
        if (p282_deadline_expired(&deadline)) {{
            timeout_attempted = 1;
            (void)sys_kill(pid, SIGKILL);
            rc = p327_reap_after_kill(pid, &status);
            if (rc != 0) break;
            reaped = 1;
            continue;
        }}
        if (amount <= 0) p282_poll_delay();
    }}
    if (rc != 0 && !reaped) {{
        (void)sys_kill(pid, SIGKILL);
        long cleanup = p327_reap_after_kill(pid, &status);
        if (cleanup != 0) rc = cleanup;
    }}
    (void)sys_close(pipe_fds[0]);
    long group_cleanup = p327_cleanup_process_group(pid);
    if (rc == 0 && group_cleanup != 0) rc = group_cleanup;
    if (rc != 0) return rc;

    uint32_t signal_number = (uint32_t)status & 0x7fU;
    int32_t exit_code = signal_number == 0U
        ? (int32_t)(((uint32_t)status >> 8) & 0xffU) : -1;
    if (timeout_attempted && signal_number == SIGKILL)
        flags |= P327_FLAG_TIMEOUT;
    if (exit_code == 126 || exit_code == 127)
        flags |= P327_FLAG_EXEC_FAILURE;
    struct timespec64 finished = {{0}};
    rc = p241_clock_gettime(&finished);
    if (rc != 0) return rc;
    uint8_t exit_payload[24];
    p327_store_le32(exit_payload, flags);
    p327_store_le32(exit_payload + 4U, (uint32_t)exit_code);
    p327_store_le32(exit_payload + 8U, signal_number);
    p327_store_le32(exit_payload + 12U, forwarded);
    p327_store_le64(exit_payload + 16U, p327_elapsed_ms(&started, &finished));
    return p327_write_frame(
        tty_fd, P327_FRAME_EXIT, sequence,
        exit_payload, (uint16_t)sizeof(exit_payload));
}}

static long p327_framed_console(int tty_fd) {{
    uint8_t type = 0U;
    uint32_t sequence = 0U;
    uint16_t length = 0U;
    uint8_t payload[P327_MAX_PAYLOAD];
    long rc = p327_read_frame(
        tty_fd, &type, &sequence, payload, &length);
    if (rc != 0 || type != P327_FRAME_OPEN || sequence != 0U
        || length != sizeof(p327_run_id)
        || !p260_bytes_equal(
            (const char *)payload, (const char *)p327_run_id,
            sizeof(p327_run_id))) return rc != 0 ? rc : -P260_EPROTO;
    rc = p327_write_frame(
        tty_fd, P327_FRAME_READY, 0U,
        p327_run_id, (uint16_t)sizeof(p327_run_id));
    if (rc != 0) return rc;

    uint32_t expected_sequence = 1U;
    uint32_t handled = 0U;
    for (;;) {{
        rc = p327_read_frame(
            tty_fd, &type, &sequence, payload, &length);
        if (rc != 0 || sequence != expected_sequence)
            return rc != 0 ? rc : -P260_EPROTO;
        if (type == P327_FRAME_EXEC && handled < P327_MAX_COMMANDS) {{
            rc = p327_exec_command(tty_fd, sequence, payload, length);
            if (rc != 0) return rc;
            ++handled;
            ++expected_sequence;
            continue;
        }}
        if (type == P327_FRAME_CLOSE && length == 0U
            && handled == P327_MAX_COMMANDS) {{
            uint8_t done[4];
            p327_store_le32(done, handled);
            return p327_write_frame(
                tty_fd, P327_FRAME_DONE, sequence, done, sizeof(done));
        }}
        return -P260_EPROTO;
    }}
}}

'''.encode("ascii")


class FramedRuntimeError(ValueError):
    """The P3.26 preimage or bounded P3.27 runtime delta differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _validate_p326_source() -> None:
    try:
        payload = P326_SOURCE.read_bytes()
    except OSError as exc:
        raise FramedRuntimeError("P326 runtime helper is unavailable") from exc
    if identity(payload) != P326_SOURCE_IDENTITY:
        raise FramedRuntimeError("P326 runtime helper identity differs")


def validate_p326_runtime(value: bytes) -> dict[str, Any]:
    _validate_p326_source()
    if type(value) is not bytes or identity(value) != P326_RUNTIME_IDENTITY:
        raise FramedRuntimeError("P326 runtime identity differs")
    try:
        receipt = p326.validate_p326_runtime(value)
    except Exception as exc:
        raise FramedRuntimeError(str(exc)) from exc
    return dict(receipt)


def validate_p327_runtime(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes:
        raise FramedRuntimeError("P327 runtime must be bytes")
    if (
        value.count(PUBLISHER) != 1
        or value.count(P327_HELPER) != 1
        or value.count(P327_ENTRY) != 1
        or p326.P326_HELPER in value
        or p326.P326_ENTRY in value
    ):
        raise FramedRuntimeError("P327 runtime anchors differ")
    helper_offset = value.index(P327_HELPER)
    publisher_offset = value.index(PUBLISHER)
    entry_offset = value.index(P327_ENTRY, publisher_offset)
    carrier_offset = value.index(b"s22plus_max77705_p319_stock_encode", entry_offset)
    if not helper_offset < publisher_offset < entry_offset < carrier_offset:
        raise FramedRuntimeError("P327 framed-session/Carrier order differs")
    required = (
        b"sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK)",
        b"sys_kill(pid, SIGKILL)",
        b"sys_kill(-pid, SIGKILL)",
        b"sys_wait4(pid, status, WNOHANG)",
        b"sys_wait4(-pid, &status, WNOHANG)",
        b"p327_setsid() < 0",
        b'"/bin/busybox", (char *)"ash", (char *)"-c"',
        b"P327_MAX_COMMANDS 3U",
        b"P327_COMMAND_TIMEOUT_SEC 10LL",
        b"P327_MAX_OUTPUT 131072U",
        b"#define p327_run_id k_run_id",
    )
    if any(item not in value for item in required) or b"ash -i" in value:
        raise FramedRuntimeError("P327 bounded execution contract differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P327_RUN_ID_HEX,
        "wire_magic": FRAME_MAGIC.decode("ascii"),
        "frame_header_size": FRAME_HEADER_SIZE,
        "max_frame_payload": MAX_FRAME_PAYLOAD,
        "max_command_size": MAX_COMMAND_SIZE,
        "max_commands": MAX_COMMANDS,
        "command_timeout_sec": COMMAND_TIMEOUT_SEC,
        "max_output_bytes": MAX_OUTPUT_BYTES,
        "command_policy": "fixed_three_command_proof_v1",
        "caller_selected_command": False,
        "child_kill_and_reap": True,
        "child_session_isolated": True,
        "descendant_group_cleanup": True,
        "interactive_pty": False,
        "carrier_path_retained": True,
    }


def validate_transform(before: bytes, after: bytes) -> dict[str, Any]:
    validate_p326_runtime(before)
    result = validate_p327_runtime(after)
    expected = before.replace(p326.P326_HELPER, P327_HELPER, 1)
    expected = expected.replace(p326.P326_ENTRY, P327_ENTRY, 1)
    if after != expected:
        raise FramedRuntimeError("P327 delta exceeds the two console anchors")
    return result | {
        "changed_anchors": ["p326_console_helper", "p319_stock_publish"],
        "source_identity": identity(before),
        "target_identity": identity(after),
    }


def transform_runtime_include(value: bytes) -> bytes:
    validate_p326_runtime(value)
    result = value.replace(p326.P326_HELPER, P327_HELPER, 1)
    result = result.replace(p326.P326_ENTRY, P327_ENTRY, 1)
    validate_transform(value, result)
    return result


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise FramedRuntimeError("P327 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY])
    changed = {key for key in result if result[key] != source[key]}
    if changed != {RUNTIME_KEY}:
        raise FramedRuntimeError("P327 source delta differs")
    return result


__all__ = [
    "COMMAND_TIMEOUT_SEC",
    "CONTRACT_ID",
    "DEVICE_BANNER",
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
    "FramedRuntimeError",
    "MAX_COMMANDS",
    "MAX_COMMAND_SIZE",
    "MAX_FRAME_PAYLOAD",
    "MAX_OUTPUT_BYTES",
    "P326_RUNTIME_IDENTITY",
    "P327_ENTRY",
    "P327_HELPER",
    "P327_RUN_ID",
    "P327_RUN_ID_HEX",
    "RUNTIME_KEY",
    "SCHEMA",
    "TARGET",
    "identity",
    "transform_artifacts",
    "transform_runtime_include",
    "validate_p326_runtime",
    "validate_p327_runtime",
    "validate_transform",
]
