#!/usr/bin/env python3
"""P3.34 outer return-code latch for the unchanged P3.33 console.

P3.33 proves that native PID1 reaches the first ``p328_framed_console`` call,
but the tty closes before a post-return diagnostic could be trusted.  P3.34
keeps the complete P3.33 console body, frame protocol, timeouts, commands and
two-session shape unchanged.  It records only the first call's returned
negative errno in the existing checkpoint terminal-detail field after the
console returns.  That errno identifies the first read/OPEN boundary only when
paired with stage 0 and no later diagnostic.  No retry or new command path is
added.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any, Mapping


SOURCE = Path(__file__).with_name("s22plus_fyg8_p333_open_entry_diag_runtime.py")
SOURCE_IDENTITY = {
    "size": 10_991,
    "sha256": "fb61a41719df431fc465d763eebb63e412f68c95adaa21300f20e8a603ba7397",
}
P333_PREDECESSOR_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_PREDECESSOR_RUN_ID = bytes.fromhex(P333_PREDECESSOR_RUN_ID_HEX)
P334_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_RUN_ID = bytes.fromhex(P334_RUN_ID_HEX)

P334_DETAIL_PREFIX = 0xB000
P334_DETAIL_PREFIX_MASK = 0xF000
P334_DETAIL_ERRNO_MASK = 0x0FFF
P334_DETAIL_SENTINEL = 0xBFFF
P334_MAX_ENCODED_ERRNO = 4094


class P334RuntimeError(ValueError):
    """The exact P3.33 predecessor or two-anchor delta differs."""


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
        raise P334RuntimeError("P3.33 runtime source is unavailable") from exc
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
        raise P334RuntimeError("P3.33 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p333_runtime_bound_for_p334")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P334RuntimeError("P3.33 runtime source failed to load") from exc
    if getattr(module, "P333_RUN_ID_HEX", None) != P333_PREDECESSOR_RUN_ID_HEX:
        raise P334RuntimeError("P3.33 runtime binding differs")
    return module


def _modules(root: types.ModuleType) -> list[types.ModuleType]:
    result: list[types.ModuleType] = []
    pending = [root]
    while pending:
        module = pending.pop()
        if module in result:
            continue
        result.append(module)
        for name, value in vars(module).items():
            if name.startswith("_P") and isinstance(value, types.ModuleType):
                pending.append(value)
    return result


_P333 = _load()
P333_ENTRY = _P333.P333_ENTRY
_ENTRY_TAIL = b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
if P333_ENTRY.count(_ENTRY_TAIL) != 1:
    raise P334RuntimeError("P3.33 publisher entry anchor differs")

P334_ENTRY = (
    b"    long p334_first_session_rc = -EIO;\n"
    b"    int p334_first_console_called = 0;\n"
    b"    struct s22plus_p318_banner_result p334_banner_1 =\n"
    b"        s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p334_banner_1.outcome == S22PLUS_P318_BANNER_WRITTEN) {\n"
    b"        if (p330_write_diagnostic(tty_fd, 0U, 0) == 0) {\n"
    b"            p334_first_console_called = 1;\n"
    b"            p334_first_session_rc = p328_framed_console(tty_fd);\n"
    b"        }\n"
    b"    }\n"
    b"    if (p334_first_session_rc == 0) {\n"
    b"        struct s22plus_p318_banner_result p334_banner_2 =\n"
    b"            s22plus_p318_banner_attempt(tty_fd);\n"
    b"        if (p334_banner_2.outcome == S22PLUS_P318_BANNER_WRITTEN) {\n"
    b"            if (p330_write_diagnostic(tty_fd, 0U, 0) == 0)\n"
    b"                (void)p328_framed_console(tty_fd);\n"
    b"        }\n"
    b"    }\n"
    + _ENTRY_TAIL
)

P333_DETAIL_ANCHOR = (
    b"    if (s22plus_max77705_p319_stock_encode(\n"
    b"            &witness, terminal_state, envelope, &detail) != 0)\n"
    b"        p290_fail_next(S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS);\n"
    b"    p319_stock_bypass_to_pair();\n"
)
P334_DETAIL_ANCHOR = (
    b"    if (s22plus_max77705_p319_stock_encode(\n"
    b"            &witness, terminal_state, envelope, &detail) != 0)\n"
    b"        p290_fail_next(S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS);\n"
    b"    if (!p334_first_console_called || p334_first_session_rc > 0\n"
    b"        || p334_first_session_rc < -4094L)\n"
    b"        detail = 0xbfffU;\n"
    b"    else\n"
    b"        detail = (uint16_t)(0xb000U\n"
    b"            | (uint16_t)(-p334_first_session_rc));\n"
    b"    p319_stock_bypass_to_pair();\n"
)

for _module in _modules(_P333):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P333_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P334_RUN_ID)
        elif _value == P333_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P334_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            _changed = False
            for _key, _default in tuple(_defaults.items()):
                if _default == P333_PREDECESSOR_RUN_ID:
                    _defaults[_key] = P334_RUN_ID
                    _changed = True
                elif _default == P333_PREDECESSOR_RUN_ID_HEX:
                    _defaults[_key] = P334_RUN_ID_HEX
                    _changed = True
            if _changed:
                _value.__kwdefaults__ = _defaults

P333_DEFAULT_COMMANDS = tuple(_P333.DEFAULT_COMMANDS)
P334_DEFAULT_COMMANDS = (
    P333_DEFAULT_COMMANDS[0],
    P333_DEFAULT_COMMANDS[1],
    f"/bin/busybox echo P328-NONCE {P334_RUN_ID_HEX}".encode("ascii"),
)
for _module in _modules(_P333):
    for _name in ("DEFAULT_COMMANDS", "P333_DEFAULT_COMMANDS"):
        if hasattr(_module, _name):
            setattr(_module, _name, P334_DEFAULT_COMMANDS)
    if hasattr(_module, "DEVICE_BANNER"):
        _module.DEVICE_BANNER = (
            f"S22PLUS-FYG8-E3:{P334_RUN_ID_HEX}\n".encode("ascii")
        )

for _name in getattr(_P333, "__all__", ()):
    globals()[_name] = getattr(_P333, _name)

SOURCE = Path(__file__).with_name("s22plus_fyg8_p333_open_entry_diag_runtime.py")
SOURCE_IDENTITY = {
    "size": 10_991,
    "sha256": "fb61a41719df431fc465d763eebb63e412f68c95adaa21300f20e8a603ba7397",
}
CONTRACT_ID = "s22plus-fyg8-p334-first-read-rc-runtime-v1"
SCHEMA = CONTRACT_ID
P333_RUN_ID_HEX = P334_RUN_ID_HEX
P333_RUN_ID = P334_RUN_ID
P332_RUN_ID_HEX = P334_RUN_ID_HEX
P332_RUN_ID = P334_RUN_ID
P330_RUN_ID_HEX = P334_RUN_ID_HEX
P330_RUN_ID = P334_RUN_ID
P328_RUN_ID_HEX = P334_RUN_ID_HEX
P328_RUN_ID = P334_RUN_ID
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P334_RUN_ID_HEX}\n".encode("ascii")
DEFAULT_COMMANDS = P334_DEFAULT_COMMANDS
P334_HELPER_TEMPLATE = _P333.P333_HELPER_TEMPLATE
P334_HELPER = P334_HELPER_TEMPLATE
P333_HELPER_TEMPLATE = P334_HELPER_TEMPLATE
P333_HELPER = P334_HELPER_TEMPLATE
P332_HELPER_TEMPLATE = P334_HELPER_TEMPLATE
P332_HELPER = P334_HELPER_TEMPLATE
P330_HELPER_TEMPLATE = P334_HELPER_TEMPLATE
P330_HELPER = P334_HELPER_TEMPLATE
P328_HELPER_TEMPLATE = P334_HELPER_TEMPLATE
P328_HELPER = P334_HELPER_TEMPLATE
P328_ENTRY = P334_ENTRY


def materialize_helper(auth_key: bytes) -> bytes:
    return _P333.materialize_helper(auth_key)


def encode_first_read_detail(*, console_called: bool, return_code: int) -> int:
    if type(console_called) is not bool or type(return_code) is not int:
        raise P334RuntimeError("P3.34 return-code inputs differ")
    if not console_called or return_code > 0 or return_code < -P334_MAX_ENCODED_ERRNO:
        return P334_DETAIL_SENTINEL
    return P334_DETAIL_PREFIX | (-return_code)


def decode_first_read_detail(detail: int) -> dict[str, Any]:
    if type(detail) is not int or not 0 <= detail <= 0xFFFF:
        raise P334RuntimeError("P3.34 terminal detail differs")
    if detail == P334_DETAIL_SENTINEL:
        return {"valid": False, "console_called": None, "return_code": None}
    if detail & P334_DETAIL_PREFIX_MASK != P334_DETAIL_PREFIX:
        raise P334RuntimeError("P3.34 terminal detail prefix differs")
    errno_value = detail & P334_DETAIL_ERRNO_MASK
    if errno_value > P334_MAX_ENCODED_ERRNO:
        raise P334RuntimeError("P3.34 terminal errno differs")
    return {
        "valid": True,
        "console_called": True,
        "return_code": -errno_value,
    }


def validate_p334_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if (
        type(value) is not bytes
        or value.count(P334_ENTRY) != 1
        or value.count(P333_ENTRY)
        or value.count(P334_DETAIL_ANCHOR) != 1
        or value.count(P333_DETAIL_ANCHOR)
    ):
        raise P334RuntimeError("P3.34 runtime anchors differ")
    if (
        P334_ENTRY.count(b"p328_framed_console(tty_fd)") != 2
        or P334_ENTRY.count(b"p330_write_diagnostic(tty_fd, 0U, 0)") != 2
        or b"for (" in P334_ENTRY
        or b"while (" in P334_ENTRY
        or b"close(" in P334_ENTRY
        or b"open(" in P334_ENTRY
        or b"p328_read_frame" in P334_ENTRY
        or b"p328_framed_console" in P334_DETAIL_ANCHOR
    ):
        raise P334RuntimeError("P3.34 outer-only delta differs")
    restored = value.replace(P334_ENTRY, P333_ENTRY, 1).replace(
        P334_DETAIL_ANCHOR, P333_DETAIL_ANCHOR, 1
    )
    try:
        predecessor = dict(
            _P333.validate_p333_runtime(
                restored, auth_key_sha256=auth_key_sha256
            )
        )
    except Exception as exc:
        raise P334RuntimeError(f"P3.33 predecessor differs: {exc}") from exc
    return {
        **predecessor,
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P334_RUN_ID_HEX,
        "default_commands": tuple(DEFAULT_COMMANDS),
        "first_console_return_detail": {
            "prefix": P334_DETAIL_PREFIX,
            "sentinel": P334_DETAIL_SENTINEL,
            "max_errno": P334_MAX_ENCODED_ERRNO,
            "field": "checkpoint_terminal_detail",
        },
        "first_read_interpretation_requires_stage0_without_stage1": True,
        "console_body_changed": False,
        "changed_anchors": ["p333_publisher_entry", "stock_terminal_detail"],
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        _P333.validate_p333_runtime(before, auth_key_sha256=auth_key_sha256)
    except Exception as exc:
        raise P334RuntimeError(f"P3.33 transform input differs: {exc}") from exc
    expected = before.replace(P333_ENTRY, P334_ENTRY, 1).replace(
        P333_DETAIL_ANCHOR, P334_DETAIL_ANCHOR, 1
    )
    if after != expected:
        raise P334RuntimeError("P3.34 delta exceeds two outer anchors")
    result = validate_p334_runtime(after, auth_key_sha256=auth_key_sha256)
    return {
        **result,
        "source_identity": identity(before),
        "target_identity": identity(after),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = hashlib.sha256(auth_key).hexdigest()
    if value.count(materialize_helper(auth_key)) != 1:
        raise P334RuntimeError("P3.33 helper is not materialized with auth_key")
    result = value.replace(P333_ENTRY, P334_ENTRY, 1).replace(
        P333_DETAIL_ANCHOR, P334_DETAIL_ANCHOR, 1
    )
    validate_transform(value, result, auth_key_sha256=digest)
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P334RuntimeError("P3.33 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise P334RuntimeError("P3.34 source delta differs")
    return result


P334_ARTIFACT_SOURCE = Path(__file__).resolve()

__all__ = sorted(
    set(getattr(_P333, "__all__", ()))
    | {
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "P328_ENTRY",
        "P328_HELPER",
        "P328_HELPER_TEMPLATE",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P330_HELPER",
        "P330_HELPER_TEMPLATE",
        "P330_RUN_ID",
        "P330_RUN_ID_HEX",
        "P332_HELPER",
        "P332_HELPER_TEMPLATE",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P333_DETAIL_ANCHOR",
        "P333_ENTRY",
        "P333_HELPER",
        "P333_HELPER_TEMPLATE",
        "P333_PREDECESSOR_RUN_ID",
        "P333_PREDECESSOR_RUN_ID_HEX",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "P334_ARTIFACT_SOURCE",
        "P334_DEFAULT_COMMANDS",
        "P334_DETAIL_ANCHOR",
        "P334_DETAIL_ERRNO_MASK",
        "P334_DETAIL_PREFIX",
        "P334_DETAIL_PREFIX_MASK",
        "P334_DETAIL_SENTINEL",
        "P334_ENTRY",
        "P334_HELPER",
        "P334_HELPER_TEMPLATE",
        "P334_MAX_ENCODED_ERRNO",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P334RuntimeError",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "decode_first_read_detail",
        "encode_first_read_detail",
        "identity",
        "materialize_helper",
        "transform_artifacts",
        "transform_runtime_include",
        "validate_p334_runtime",
        "validate_transform",
    }
)
