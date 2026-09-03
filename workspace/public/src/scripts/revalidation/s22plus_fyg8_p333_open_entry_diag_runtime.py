#!/usr/bin/env python3
"""P3.33 same-FD runtime with one pre-OPEN entry diagnostic.

P3.30's successful single call was inlined into ``p318_run``.  P3.31 and
P3.32 both compiled ``p328_framed_console`` out of line and both stopped
before the existing OPEN_PARSED diagnostic.  P3.33 keeps the complete P3.32
two-session runtime and adds only one stage-0 diagnostic immediately before
each out-of-line console call.  It changes no frame grammar, authentication,
command, endpoint, retry, persistence, or recovery behavior.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import types
from typing import Any, Mapping


SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p332_logical_resident_exec_runtime.py"
)
SOURCE_IDENTITY = {
    "size": 17_003,
    "sha256": "fc4f6a98855ef4fb58c417b351ef24e91d21823e08267d83030c846a58cc1f93",
}
P332_PREDECESSOR_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_PREDECESSOR_RUN_ID = bytes.fromhex(P332_PREDECESSOR_RUN_ID_HEX)
P333_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_RUN_ID = bytes.fromhex(P333_RUN_ID_HEX)
DIAGNOSTIC_STAGE_CONSOLE_ENTER = 0


class P333RuntimeError(ValueError):
    """The exact P3.32 predecessor or one-anchor delta differs."""


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
        raise P333RuntimeError("P3.32 runtime source is unavailable") from exc
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
        raise P333RuntimeError("P3.32 runtime source identity differs")
    module = types.ModuleType("s22plus_fyg8_p332_runtime_bound_for_p333")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise P333RuntimeError("P3.32 runtime source failed to load") from exc
    if getattr(module, "P332_RUN_ID_HEX", None) != P332_PREDECESSOR_RUN_ID_HEX:
        raise P333RuntimeError("P3.32 runtime binding differs")
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


_P332 = _load()
P332_ENTRY = _P332.P332_ENTRY
_ENTRY_TAIL = b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
if P332_ENTRY.count(_ENTRY_TAIL) != 1:
    raise P333RuntimeError("P3.32 publisher entry anchor differs")

P333_ENTRY = (
    b"    long p333_first_session_rc = -EIO;\n"
    b"    struct s22plus_p318_banner_result p333_banner_1 =\n"
    b"        s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p333_banner_1.outcome == S22PLUS_P318_BANNER_WRITTEN) {\n"
    b"        if (p330_write_diagnostic(tty_fd, 0U, 0) == 0)\n"
    b"            p333_first_session_rc = p328_framed_console(tty_fd);\n"
    b"    }\n"
    b"    if (p333_first_session_rc == 0) {\n"
    b"        struct s22plus_p318_banner_result p333_banner_2 =\n"
    b"            s22plus_p318_banner_attempt(tty_fd);\n"
    b"        if (p333_banner_2.outcome == S22PLUS_P318_BANNER_WRITTEN) {\n"
    b"            if (p330_write_diagnostic(tty_fd, 0U, 0) == 0)\n"
    b"                (void)p328_framed_console(tty_fd);\n"
    b"        }\n"
    b"    }\n"
    + _ENTRY_TAIL
)

for _module in _modules(_P332):
    for _name, _value in tuple(vars(_module).items()):
        if _value == P332_PREDECESSOR_RUN_ID:
            setattr(_module, _name, P333_RUN_ID)
        elif _value == P332_PREDECESSOR_RUN_ID_HEX:
            setattr(_module, _name, P333_RUN_ID_HEX)
        elif callable(_value) and getattr(_value, "__kwdefaults__", None):
            _defaults = dict(_value.__kwdefaults__)
            _changed = False
            for _key, _default in tuple(_defaults.items()):
                if _default == P332_PREDECESSOR_RUN_ID:
                    _defaults[_key] = P333_RUN_ID
                    _changed = True
                elif _default == P332_PREDECESSOR_RUN_ID_HEX:
                    _defaults[_key] = P333_RUN_ID_HEX
                    _changed = True
            if _changed:
                _value.__kwdefaults__ = _defaults

P330_DEFAULT_COMMANDS = tuple(_P332.P330_DEFAULT_COMMANDS)
P333_DEFAULT_COMMANDS = (
    P330_DEFAULT_COMMANDS[0],
    P330_DEFAULT_COMMANDS[1],
    f"/bin/busybox echo P328-NONCE {P333_RUN_ID_HEX}".encode("ascii"),
)
for _module in _modules(_P332):
    for _name in ("DEFAULT_COMMANDS", "P332_DEFAULT_COMMANDS"):
        if hasattr(_module, _name):
            setattr(_module, _name, P333_DEFAULT_COMMANDS)
    if hasattr(_module, "DEVICE_BANNER"):
        _module.DEVICE_BANNER = (
            f"S22PLUS-FYG8-E3:{P333_RUN_ID_HEX}\n".encode("ascii")
        )

for _name in getattr(_P332, "__all__", ()):
    globals()[_name] = getattr(_P332, _name)

CONTRACT_ID = "s22plus-fyg8-p333-open-entry-diagnostic-runtime-v1"
SCHEMA = CONTRACT_ID
P332_RUN_ID_HEX = P333_RUN_ID_HEX
P332_RUN_ID = P333_RUN_ID
P330_RUN_ID_HEX = P333_RUN_ID_HEX
P330_RUN_ID = P333_RUN_ID
P328_RUN_ID_HEX = P333_RUN_ID_HEX
P328_RUN_ID = P333_RUN_ID
DEVICE_BANNER = f"S22PLUS-FYG8-E3:{P333_RUN_ID_HEX}\n".encode("ascii")
DEFAULT_COMMANDS = P333_DEFAULT_COMMANDS
P333_HELPER_TEMPLATE = _P332.P332_HELPER_TEMPLATE
P333_HELPER = P333_HELPER_TEMPLATE
P332_HELPER_TEMPLATE = P333_HELPER_TEMPLATE
P332_HELPER = P333_HELPER_TEMPLATE
P330_HELPER_TEMPLATE = P333_HELPER_TEMPLATE
P330_HELPER = P333_HELPER_TEMPLATE
P328_HELPER_TEMPLATE = P333_HELPER_TEMPLATE
P328_HELPER = P333_HELPER_TEMPLATE
P328_ENTRY = P333_ENTRY


def materialize_helper(auth_key: bytes) -> bytes:
    return _P332.materialize_helper(auth_key)


def validate_p333_runtime(
    value: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    if type(value) is not bytes or value.count(P333_ENTRY) != 1 or value.count(P332_ENTRY):
        raise P333RuntimeError("P3.33 runtime entry differs")
    entry = P333_ENTRY
    if (
        entry.count(b"p330_write_diagnostic(tty_fd, 0U, 0) == 0") != 2
        or entry.count(b"p328_framed_console(tty_fd)") != 2
        or entry.count(b"s22plus_p318_banner_attempt(tty_fd)") != 2
        or b"for (" in entry
        or b"while (" in entry
        or b"close(" in entry
        or b"open(" in entry
    ):
        raise P333RuntimeError("P3.33 entry diagnostic contract differs")
    restored = value.replace(P333_ENTRY, P332_ENTRY, 1)
    try:
        predecessor = dict(
            _P332.validate_p332_runtime(
                restored, auth_key_sha256=auth_key_sha256
            )
        )
    except Exception as exc:
        raise P333RuntimeError(f"P3.32 predecessor differs: {exc}") from exc
    return {
        **predecessor,
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "run_id_hex": P333_RUN_ID_HEX,
        "default_commands": tuple(DEFAULT_COMMANDS),
        "entry_diagnostic_stage": DIAGNOSTIC_STAGE_CONSOLE_ENTER,
        "entry_diagnostic_count": 2,
        "entry_diagnostic_before_console": True,
        "changed_anchors": ["p332_publisher_entry"],
    }


def validate_transform(
    before: bytes, after: bytes, *, auth_key_sha256: str | None = None
) -> dict[str, Any]:
    try:
        _P332.validate_p332_runtime(before, auth_key_sha256=auth_key_sha256)
    except Exception as exc:
        raise P333RuntimeError(f"P3.32 transform input differs: {exc}") from exc
    if after != before.replace(P332_ENTRY, P333_ENTRY, 1):
        raise P333RuntimeError("P3.33 delta exceeds the P3.32 publisher entry")
    result = validate_p333_runtime(after, auth_key_sha256=auth_key_sha256)
    return {
        **result,
        "source_identity": identity(before),
        "target_identity": identity(after),
    }


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    digest = hashlib.sha256(auth_key).hexdigest()
    if value.count(materialize_helper(auth_key)) != 1:
        raise P333RuntimeError("P3.32 helper is not materialized with auth_key")
    result = value.replace(P332_ENTRY, P333_ENTRY, 1)
    validate_transform(value, result, auth_key_sha256=digest)
    return result


def transform_artifacts(
    source: Mapping[str, bytes], auth_key: bytes
) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise P333RuntimeError("P3.32 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY], auth_key)
    if {key for key in result if result[key] != source[key]} != {RUNTIME_KEY}:
        raise P333RuntimeError("P3.33 source delta differs")
    return result


P333_ARTIFACT_SOURCE = Path(__file__).resolve()

__all__ = sorted(
    set(getattr(_P332, "__all__", ()))
    | {
        "CONTRACT_ID",
        "DEFAULT_COMMANDS",
        "DEVICE_BANNER",
        "DIAGNOSTIC_STAGE_CONSOLE_ENTER",
        "P328_ENTRY",
        "P328_HELPER",
        "P328_HELPER_TEMPLATE",
        "P328_RUN_ID",
        "P328_RUN_ID_HEX",
        "P330_HELPER",
        "P330_HELPER_TEMPLATE",
        "P330_RUN_ID",
        "P330_RUN_ID_HEX",
        "P332_ENTRY",
        "P332_HELPER",
        "P332_HELPER_TEMPLATE",
        "P332_PREDECESSOR_RUN_ID",
        "P332_PREDECESSOR_RUN_ID_HEX",
        "P332_RUN_ID",
        "P332_RUN_ID_HEX",
        "P333_DEFAULT_COMMANDS",
        "P333_ENTRY",
        "P333_HELPER",
        "P333_HELPER_TEMPLATE",
        "P333_RUN_ID",
        "P333_RUN_ID_HEX",
        "P333RuntimeError",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "identity",
        "materialize_helper",
        "transform_artifacts",
        "transform_runtime_include",
        "validate_p333_runtime",
        "validate_transform",
    }
)
