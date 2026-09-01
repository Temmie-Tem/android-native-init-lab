#!/usr/bin/env python3
"""Add one bounded bidirectional ACM handshake and BusyBox ash child to P3.25.

The P3.25 runtime is accepted only by its complete byte identity.  P3.26 keeps
the proved banner and stock Carrier path, but between them PID 1 reads one
run-bound PING, writes one PONG, and starts one ``/bin/busybox ash`` child.  The
child consumes one run-bound SHELL line, emits the fixed SHELL-OK line, and
then exits.  This first round trip proves that BusyBox ash executed without
mixing an unbounded interactive stream into the proof receipt.  This module is
host-only source transformation; it does not contact a device.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any


CONTRACT_ID = "s22plus-fyg8-p326-bidirectional-console-runtime-v1"
SCHEMA = CONTRACT_ID
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
RUNTIME_KEY = "p290_e3_runtime_include"

P326_RUN_ID_HEX = "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_RUNTIME_IDENTITY = {
    "size": 454_072,
    "sha256": "6dd50438f01f241c020918c1f9774cfeabe4c15bc33da4dcc337cd6c517d5cf0",
}

DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P326_RUN_ID_HEX}\n".encode("ascii")
HOST_PING = f"PING {P326_RUN_ID_HEX}\n".encode("ascii")
DEVICE_PONG = f"PONG {P326_RUN_ID_HEX} pid=1\n".encode("ascii")
HOST_SHELL = f"SHELL {P326_RUN_ID_HEX}\n".encode("ascii")
DEVICE_SHELL_OK = f"SHELL-OK {P326_RUN_ID_HEX} busybox=1\n".encode("ascii")
HOST_TRANSCRIPT = HOST_PING + HOST_SHELL
DEVICE_TRANSCRIPT = DEVICE_BANNER + DEVICE_PONG + DEVICE_SHELL_OK

PUBLISHER = b"static __attribute__((noreturn)) void p319_stock_publish(int tty_fd) {"
P325_ENTRY = (
    b"    (void)s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
)
P326_ENTRY = (
    b"    struct s22plus_p318_banner_result p326_banner =\n"
    b"        s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p326_banner.outcome == S22PLUS_P318_BANNER_WRITTEN)\n"
    b"        (void)p326_bidirectional_console(tty_fd);\n"
    b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
)


def _c_string(value: bytes) -> str:
    return "".join(
        "\\n" if byte == 10 else f"\\x{byte:02x}" for byte in value
    )


_SHELL_SCRIPT = (
    "read p326_kind p326_nonce; "
    f"if [ \"$p326_kind\" = SHELL ] && [ \"$p326_nonce\" = {P326_RUN_ID_HEX} ]; "
    f"then printf 'SHELL-OK {P326_RUN_ID_HEX} busybox=1\\n'; "
    "exit 0; fi; exit 64"
).encode("ascii")

P326_HELPER = f'''/* P3.26 bounded PID1 ACM round trip and BusyBox ash child. */
#define P326_INPUT_DEADLINE_SEC 30LL
#define P326_INPUT_POLL_NS 100000000LL

static const char p326_ping[] = "{_c_string(HOST_PING)}";
static const char p326_pong[] = "{_c_string(DEVICE_PONG)}";
static const char p326_shell_script[] = "{_c_string(_SHELL_SCRIPT)}";

static long p326_read_exact(int fd, const char *expected, size_t size) {{
    struct timespec64 deadline = {{0}};
    size_t used = 0U;
    long rc = p241_clock_gettime(&deadline);
    if (rc != 0 || deadline.tv_sec > 0x7fffffffffffffffLL - P326_INPUT_DEADLINE_SEC)
        return rc != 0 ? rc : -EIO;
    deadline.tv_sec += P326_INPUT_DEADLINE_SEC;
    while (used < size) {{
        struct timespec64 now = {{0}};
        long amount;
        char input[64];
        size_t remaining = size - used;
        if (remaining > sizeof(input)) remaining = sizeof(input);
        amount = sys_read(fd, input, remaining);
        if (amount > 0) {{
            if ((size_t)amount > remaining ||
                !p260_bytes_equal(input, expected + used, (size_t)amount))
                return -P260_EPROTO;
            used += (size_t)amount;
            continue;
        }}
        if (amount != -EAGAIN && amount != -P260_EINTR)
            return amount == 0 ? -EIO : amount;
        rc = p241_clock_gettime(&now);
        if (rc != 0) return rc;
        if (!p241_timespec_before(&now, &deadline)) return -ETIMEDOUT;
        (void)sys_nanosleep(P326_INPUT_POLL_NS);
    }}
    return 0;
}}

static long p326_spawn_busybox_shell(int tty_fd) {{
    if (tty_fd <= 2) return -EIO;
    long pid = sys_clone();
    if (pid == 0) {{
        char *const argv[] = {{
            (char *)"/bin/busybox", (char *)"ash", (char *)"-c",
            (char *)p326_shell_script, NULL,
        }};
        char *const envp[] = {{
            (char *)"PATH=/bin", (char *)"HOME=/", (char *)"TERM=vt100", NULL,
        }};
        for (int target = 0; target <= 2; ++target) {{
            if (sys_dup3(tty_fd, target, 0) != target) sys_exit(126);
        }}
        (void)sys_close(tty_fd);
        (void)sys_execve("/bin/busybox", argv, envp);
        sys_exit(127);
    }}
    return pid < 0 ? pid : 0;
}}

static long p326_bidirectional_console(int tty_fd) {{
    long rc = p326_read_exact(tty_fd, p326_ping, sizeof(p326_ping) - 1U);
    if (rc != 0) return rc;
    rc = p260_write_all(tty_fd, p326_pong, sizeof(p326_pong) - 1U, 1);
    if (rc != 0) return rc;
    return p326_spawn_busybox_shell(tty_fd);
}}

'''.encode("ascii")


class ConsoleRuntimeError(ValueError):
    """The P3.25 preimage or the P3.26 source delta differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def validate_p325_runtime(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes or identity(value) != P325_RUNTIME_IDENTITY:
        raise ConsoleRuntimeError("P325 runtime identity differs")
    if value.count(PUBLISHER) != 1 or value.count(P325_ENTRY) != 1:
        raise ConsoleRuntimeError("P325 publisher preimage differs")
    if P326_ENTRY in value or P326_HELPER in value:
        raise ConsoleRuntimeError("P325 runtime already contains P326 bytes")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "bidirectional": False,
    }


def validate_p326_runtime(value: bytes) -> dict[str, Any]:
    if type(value) is not bytes:
        raise ConsoleRuntimeError("P326 runtime must be bytes")
    if (
        value.count(PUBLISHER) != 1
        or value.count(P326_ENTRY) != 1
        or value.count(P326_HELPER) != 1
        or P325_ENTRY in value
    ):
        raise ConsoleRuntimeError("P326 runtime anchors differ")
    helper_offset = value.index(P326_HELPER)
    publisher_offset = value.index(PUBLISHER)
    entry_offset = value.index(P326_ENTRY, publisher_offset)
    carrier_offset = value.index(b"s22plus_max77705_p319_stock_encode", entry_offset)
    if not helper_offset < publisher_offset < entry_offset < carrier_offset:
        raise ConsoleRuntimeError("P326 console/Carrier order differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "run_id_hex": P326_RUN_ID_HEX,
        "pid1_ping_pong": True,
        "busybox_ash_child": True,
        "busybox_ash_exits_after_proof": True,
        "host_tx_size": len(HOST_TRANSCRIPT),
        "device_rx_size": len(DEVICE_TRANSCRIPT),
        "carrier_path_retained": True,
        "input_deadline_sec": 30,
    }


def validate_transform(before: bytes, after: bytes) -> dict[str, Any]:
    validate_p325_runtime(before)
    result = validate_p326_runtime(after)
    publisher_offset = before.index(PUBLISHER)
    inserted = before[:publisher_offset] + P326_HELPER + before[publisher_offset:]
    expected = inserted.replace(P325_ENTRY, P326_ENTRY, 1)
    if after != expected:
        raise ConsoleRuntimeError("P326 delta exceeds the console anchors")
    return result | {
        "changed_anchors": ["p319_stock_publish", "p326_console_helper"],
        "source_identity": identity(before),
        "target_identity": identity(after),
    }


def transform_runtime_include(value: bytes) -> bytes:
    validate_p325_runtime(value)
    publisher_offset = value.index(PUBLISHER)
    result = value[:publisher_offset] + P326_HELPER + value[publisher_offset:]
    result = result.replace(P325_ENTRY, P326_ENTRY, 1)
    validate_transform(value, result)
    return result


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise ConsoleRuntimeError("P326 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY])
    changed = {key for key in result if result[key] != source[key]}
    if changed != {RUNTIME_KEY}:
        raise ConsoleRuntimeError("P326 source delta differs")
    return result


__all__ = [
    "CONTRACT_ID",
    "ConsoleRuntimeError",
    "DEVICE_BANNER",
    "DEVICE_PONG",
    "DEVICE_SHELL_OK",
    "DEVICE_TRANSCRIPT",
    "HOST_PING",
    "HOST_SHELL",
    "HOST_TRANSCRIPT",
    "P325_RUNTIME_IDENTITY",
    "P326_ENTRY",
    "P326_HELPER",
    "P326_RUN_ID_HEX",
    "RUNTIME_KEY",
    "SCHEMA",
    "TARGET",
    "identity",
    "transform_artifacts",
    "transform_runtime_include",
    "validate_p325_runtime",
    "validate_p326_runtime",
    "validate_transform",
]
