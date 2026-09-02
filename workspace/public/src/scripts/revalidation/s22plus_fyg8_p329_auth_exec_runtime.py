#!/usr/bin/env python3
"""P3.29 identity-only binding of the reviewed P3.28 auth runtime.

The device protocol, HMAC domains, key, command bounds, and wire magic stay
byte-for-byte P3.28.  Only the candidate run identity and the proof echo are
rotated.  The module is host-only and never reads the private key.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any


SOURCE = Path(__file__).with_name("s22plus_fyg8_p328_auth_exec_runtime.py")
SOURCE_IDENTITY = {
    "size": 21_068,
    "sha256": "e69b5603998c19f2c24f48b16d8149c3c5046ae9a42a8baf9de497c3f56d328a",
}
P328_RUN_ID_HEX = "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P329_RUN_ID_HEX = "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P329_RUN_ID = bytes.fromhex(P329_RUN_ID_HEX)


class P329RuntimeError(ValueError):
    """The exact P3.28 runtime source or P3.29 identity differs."""


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
        raise P329RuntimeError("P3.28 runtime source is unavailable") from exc
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
        raise P329RuntimeError("P3.28 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p328_runtime_bound_for_p329")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P329RuntimeError("P3.28 runtime source failed to load") from exc
    if getattr(module, "P328_RUN_ID_HEX", None) != P328_RUN_ID_HEX:
        raise P329RuntimeError("P3.28 runtime binding differs")
    return module


_P328 = _load()
_P328.P328_RUN_ID_HEX = P329_RUN_ID_HEX
_P328.P328_RUN_ID = P329_RUN_ID
_P328.DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P329_RUN_ID_HEX}\n".encode("ascii")
# P328-NONCE and S328 are retained protocol namespaces, not candidate IDs.
_P328.DEFAULT_COMMANDS = (
    b"/bin/busybox id",
    b"/bin/busybox uname -a",
    f"/bin/busybox echo P328-NONCE {P329_RUN_ID_HEX}".encode("ascii"),
)
_P328.CONTRACT_ID = "s22plus-fyg8-p329-auth-exec-runtime-v1"
_P328.SCHEMA = _P328.CONTRACT_ID

for _name in getattr(_P328, "__all__", ()):
    globals()[_name] = getattr(_P328, _name)

CONTRACT_ID = _P328.CONTRACT_ID
SCHEMA = _P328.SCHEMA
P328_RUN_ID_HEX = P329_RUN_ID_HEX
P328_RUN_ID = P329_RUN_ID
DEVICE_BANNER = _P328.DEVICE_BANNER
DEFAULT_COMMANDS = _P328.DEFAULT_COMMANDS
validate_p329_runtime = _P328.validate_p328_runtime

__all__ = sorted(
    set(getattr(_P328, "__all__", ()))
    | {
        "P329_RUN_ID",
        "P329_RUN_ID_HEX",
        "P329RuntimeError",
        "SOURCE",
        "SOURCE_IDENTITY",
        "validate_p329_runtime",
    }
)
