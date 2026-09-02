#!/usr/bin/env python3
"""P3.30 pre-auth diagnostic and finite early-entropy repair.

The authenticated command protocol, key, command bounds, and S328 wire magic
remain P3.28/P3.29.  P3.30 adds two non-authoritative diagnostic frames around
the device nonce acquisition and retries only ``getrandom`` ``EAGAIN`` a fixed
number of times.  No command executes before the unchanged HMAC exchange.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


SOURCE = Path(__file__).with_name("s22plus_fyg8_p329_auth_exec_runtime.py")
SOURCE_IDENTITY = {
    "size": 3_738,
    "sha256": "6b3bcb98bf02358cbeb3faff24604d0f2168fe843147797a6f3acdc618edea2e",
}
P329_PREDECESSOR_RUN_ID_HEX = "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P330_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_RUN_ID = bytes.fromhex(P330_RUN_ID_HEX)
DIAGNOSTIC_FRAME_TYPE = 0x86
DIAGNOSTIC_PAYLOAD_SIZE = 8
DIAGNOSTIC_STAGE_OPEN_PARSED = 1
DIAGNOSTIC_STAGE_RNG = 2
RNG_EAGAIN_RETRY_LIMIT = 64


class P330RuntimeError(ValueError):
    """The exact predecessor or bounded P3.30 transform differs."""


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
        raise P330RuntimeError("P3.29 runtime source is unavailable") from exc
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
        raise P330RuntimeError("P3.29 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p329_runtime_bound_for_p330")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P330RuntimeError("P3.29 runtime source failed to load") from exc
    if getattr(module, "P329_RUN_ID_HEX", None) != P329_PREDECESSOR_RUN_ID_HEX:
        raise P330RuntimeError("P3.29 runtime binding differs")
    return module


def _replace_function(value: str, name: str, replacement: str) -> str:
    start = value.index(f"static long {name}")
    end = value.index("\n}\n", start) + 3
    return value[:start] + replacement + value[end:]


def _derive_helper_template(predecessor: bytes) -> bytes:
    value = predecessor.decode("ascii")
    anchor = "#define P328_FRAME_CHALLENGE 0x85U\n"
    if value.count(anchor) != 1:
        raise P330RuntimeError("P3.29 diagnostic constant anchor differs")
    value = value.replace(
        anchor,
        anchor
        + f"#define P330_FRAME_DIAGNOSTIC 0x{DIAGNOSTIC_FRAME_TYPE:02x}U\n"
        + f"#define P330_DIAG_OPEN_PARSED {DIAGNOSTIC_STAGE_OPEN_PARSED}U\n"
        + f"#define P330_DIAG_RNG {DIAGNOSTIC_STAGE_RNG}U\n"
        + f"#define P330_RNG_EAGAIN_RETRY_LIMIT {RNG_EAGAIN_RETRY_LIMIT}U\n",
        1,
    )
    nonce = r'''static long p328_getrandom_nonce(uint8_t nonce[P328_NONCE_SIZE]) {
    long amount = syscall6(
        P328_NR_GETRANDOM, (long)(uintptr_t)nonce,
        P328_NONCE_SIZE, P328_GRND_NONBLOCK, 0, 0, 0);
    if (amount == -EAGAIN) return -EAGAIN;
    if (amount != (long)P328_NONCE_SIZE)
        return amount < 0 ? amount : -EIO;
    uint8_t nonzero = 0U;
    for (size_t index = 0U; index < P328_NONCE_SIZE; ++index)
        nonzero |= nonce[index];
    return nonzero == 0U ? -EIO : 0;
}
'''
    value = _replace_function(value, "p328_getrandom_nonce", nonce)
    console_start = value.index("static long p328_framed_console")
    diagnostic = r'''static long p330_write_diagnostic(
    int tty_fd, uint32_t stage, int32_t code) {
    uint8_t payload[8];
    p328_store_le32(payload, stage);
    p328_store_le32(payload + 4U, (uint32_t)code);
    return p328_write_frame(
        tty_fd, P330_FRAME_DIAGNOSTIC, 0U, payload, sizeof(payload));
}

'''
    value = value[:console_start] + diagnostic + value[console_start:]
    old = r'''    rc = p328_getrandom_nonce(nonce);
    if (rc != 0) return rc;
    rc = p328_write_frame(
        tty_fd, P328_FRAME_CHALLENGE, 0U,
        nonce, (uint16_t)sizeof(nonce));
    if (rc != 0) return rc;
'''
    new = r'''    rc = p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0);
    if (rc != 0) return rc;

    uint32_t rng_retries = 0U;
    for (;;) {
        rc = p328_getrandom_nonce(nonce);
        if (rc == 0) break;
        if (rc != -EAGAIN || rng_retries == P330_RNG_EAGAIN_RETRY_LIMIT) {
            (void)p330_write_diagnostic(tty_fd, P330_DIAG_RNG, (int32_t)rc);
            return rc;
        }
        ++rng_retries;
        p282_poll_delay();
    }
    rc = p330_write_diagnostic(
        tty_fd, P330_DIAG_RNG, (int32_t)rng_retries);
    if (rc != 0) return rc;
    rc = p328_write_frame(
        tty_fd, P328_FRAME_CHALLENGE, 0U,
        nonce, (uint16_t)sizeof(nonce));
    if (rc != 0) return rc;
'''
    if value.count(old) != 1:
        raise P330RuntimeError("P3.29 nonce/challenge anchor differs")
    value = value.replace(old, new, 1)
    return value.encode("ascii")


_P329 = _load()
_BASE = _P329._P328
P330_HELPER_TEMPLATE = _derive_helper_template(_P329.P328_HELPER_TEMPLATE)
_BASE.P328_HELPER_TEMPLATE = P330_HELPER_TEMPLATE
_BASE.P328_HELPER = P330_HELPER_TEMPLATE
_P329.P328_HELPER_TEMPLATE = P330_HELPER_TEMPLATE
_P329.P328_HELPER = P330_HELPER_TEMPLATE
for _module in (_BASE, _P329):
    _module.P328_RUN_ID_HEX = P330_RUN_ID_HEX
    _module.P328_RUN_ID = P330_RUN_ID
    _module.DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P330_RUN_ID_HEX}\n".encode("ascii")
    _module.DEFAULT_COMMANDS = (
        b"/bin/busybox id",
        b"/bin/busybox uname -a",
        f"/bin/busybox echo P328-NONCE {P330_RUN_ID_HEX}".encode("ascii"),
    )
    _module.CONTRACT_ID = "s22plus-fyg8-p330-auth-exec-runtime-v1"
    _module.SCHEMA = _module.CONTRACT_ID

for _name in getattr(_P329, "__all__", ()):
    globals()[_name] = getattr(_P329, _name)

CONTRACT_ID = _P329.CONTRACT_ID
SCHEMA = _P329.SCHEMA
P328_RUN_ID_HEX = P330_RUN_ID_HEX
P328_RUN_ID = P330_RUN_ID
DEVICE_BANNER = _P329.DEVICE_BANNER
DEFAULT_COMMANDS = _P329.DEFAULT_COMMANDS
P328_HELPER_TEMPLATE = P330_HELPER_TEMPLATE
P328_HELPER = P330_HELPER_TEMPLATE


def validate_p330_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        result = dict(
            _BASE.validate_p328_runtime(
                value, auth_key_sha256=auth_key_sha256
            )
        )
    except Exception as exc:
        raise P330RuntimeError(f"P3.30 runtime differs: {exc}") from exc
    required = (
        b"P330_FRAME_DIAGNOSTIC 0x86U",
        b"P330_DIAG_OPEN_PARSED 1U",
        b"P330_DIAG_RNG 2U",
        b"P330_RNG_EAGAIN_RETRY_LIMIT 64U",
        b"if (amount == -EAGAIN) return -EAGAIN;",
        b"if (rc != -EAGAIN || rng_retries == P330_RNG_EAGAIN_RETRY_LIMIT)",
        b"p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0)",
        b"p330_write_diagnostic(tty_fd, P330_DIAG_RNG, (int32_t)rc)",
    )
    if any(anchor not in value for anchor in required):
        raise P330RuntimeError("P3.30 diagnostic/retry anchors differ")
    result.update(
        {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "run_id_hex": P330_RUN_ID_HEX,
            "preauth_diagnostic_frame": DIAGNOSTIC_FRAME_TYPE,
            "rng_eagain_retry_limit": RNG_EAGAIN_RETRY_LIMIT,
            "non_eagain_retry": False,
        }
    )
    return result


validate_p329_runtime = validate_p330_runtime

__all__ = sorted(
    set(getattr(_P329, "__all__", ()))
    | {
        "DIAGNOSTIC_FRAME_TYPE",
        "DIAGNOSTIC_PAYLOAD_SIZE",
        "DIAGNOSTIC_STAGE_OPEN_PARSED",
        "DIAGNOSTIC_STAGE_RNG",
        "P330_HELPER_TEMPLATE",
        "P330_RUN_ID",
        "P330_RUN_ID_HEX",
        "P330RuntimeError",
        "RNG_EAGAIN_RETRY_LIMIT",
        "SOURCE",
        "SOURCE_IDENTITY",
        "validate_p330_runtime",
    }
)
