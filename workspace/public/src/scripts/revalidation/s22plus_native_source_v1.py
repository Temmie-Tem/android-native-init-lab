"""Direct FYG8 native sources; identity injection does not grant device authority.

The five C fragments are the current production helper, including its existing
post-authentication HUD lifetime. Historical candidate generators remain sealed.
This module imports no candidate namespace and evaluates no generated Python.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import stat
from typing import Iterable


ROOT = Path(__file__).resolve().parents[5]
NATIVE = ROOT / "workspace/public/src/native-init"
TEMPLATES = NATIVE / "s22plus_runtime_v1"
HELPER_PARTS = (
    "protocol.inc.c.in",
    "return.inc.c.in",
    "commands.inc.c.in",
    "hud.inc.c.in",
    "session.inc.c.in",
)
# Preserve exact original inter-fragment spacing without blank lines at each
# source file's EOF. These bytes are part of the generated C comparison.
HELPER_SEPARATORS = (b"\n\n\n", b"\n", b"", b"\n", b"\n\n")
AUTH_KEY_PLACEHOLDER = b"P328_AUTH_KEY_BYTES"
_SLOT = re.compile(rb"@@([A-Z_]+)@@")
_MODULE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\.ko")


class SourceError(ValueError):
    pass


@dataclass(frozen=True)
class Identity:
    namespace: str
    run_id_hex: str
    display_version: str

    def __post_init__(self) -> None:
        fields = (
            (self.namespace, r"p[0-9]{3,6}"),
            (self.run_id_hex, r"[0-9a-f]{32}"),
            (self.display_version, r"v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?"),
        )
        if any(type(value) is not str or re.fullmatch(pattern, value) is None
               for value, pattern in fields):
            raise SourceError("native identity has an invalid field")


@dataclass(frozen=True)
class MemoryModule:
    name: str
    size: int
    mode: int


@dataclass(frozen=True)
class DisplayModule:
    name: str
    size: int
    display: bool


def _read(path: Path) -> bytes:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise SourceError("source is not a direct regular file: " + path.name)
    raw = path.read_bytes()
    after = path.lstat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ) or len(raw) != before.st_size:
        raise SourceError("source changed while reading: " + path.name)
    raw.decode("ascii")
    return raw


def _expand(raw: bytes, values: dict[bytes, bytes]) -> bytes:
    if set(_SLOT.findall(raw)) != set(values):
        raise SourceError("source identity slots differ")
    result = _SLOT.sub(lambda match: values[match[1]], raw)
    if _SLOT.search(result):
        raise SourceError("unexpanded source slot")
    return result


def helper_template(identity: Identity) -> bytes:
    raw = b"".join(_read(TEMPLATES / name) + gap
                   for name, gap in zip(HELPER_PARTS, HELPER_SEPARATORS, strict=True))
    if raw.count(b"@@AUTH_KEY_BYTES@@") != 1:
        raise SourceError("authentication key slot differs")
    return _expand(raw, {
        b"NAMESPACE": identity.namespace.encode("ascii"),
        b"NAMESPACE_UPPER": identity.namespace.upper().encode("ascii"),
        b"RUN_ID_HEX": identity.run_id_hex.encode("ascii"),
        b"RUN_ID_ESCAPED": "".join(f"\\x{byte:02x}" for byte in
                                   identity.run_id_hex.encode("ascii")).encode("ascii"),
        b"AUTH_KEY_BYTES": AUTH_KEY_PLACEHOLDER,
    })


def materialize_helper(identity: Identity, auth_key: bytes) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != 32:
        raise SourceError("authentication key must be exactly 32 bytes")
    source = helper_template(identity)
    if source.count(AUTH_KEY_PLACEHOLDER) != 1:
        raise SourceError("authentication key placeholder differs")
    initializer = b", ".join(f"0x{byte:02x}U".encode("ascii") for byte in auth_key)
    return source.replace(AUTH_KEY_PLACEHOLDER, initializer, 1)


def _module(name: str, size: int) -> None:
    if (type(name) is not str or _MODULE_NAME.fullmatch(name) is None
            or type(size) is not int or not 0 < size <= 128 * 1024 * 1024):
        raise SourceError("module metadata differs")


def memory_census(modules: Iterable[MemoryModule]) -> bytes:
    rows = tuple(modules)
    if not rows or len(rows) > 4096:
        raise SourceError("memory census count differs")
    names = []
    for row in rows:
        if type(row) is not MemoryModule:
            raise SourceError("memory census row type differs")
        _module(row.name, row.size)
        if type(row.mode) is not int or not 0 <= row.mode <= 0o7777:
            raise SourceError("module mode differs")
        names.append(row.name)
    if names != sorted(set(names)):
        raise SourceError("memory census must have unique sorted names")
    lines = [
        "/* Fixed metadata census; no file content is read by the device helper. */",
        f"#define MS_MANIFEST_COUNT {len(rows)}U",
        "#define MS_MANIFEST_ROWS \\",
    ]
    for index, row in enumerate(rows):
        suffix = ", \\" if index + 1 < len(rows) else ""
        lines.append(f'    {{"{row.name}", {row.size}ULL, 0{row.mode:o}U}}{suffix}')
    return ("\n".join(lines) + "\n").encode("ascii")


def render_display(identity: Identity, modules: Iterable[MemoryModule]) -> bytes:
    return _expand(_read(TEMPLATES / "display.c.in"), {
        b"DISPLAY_VERSION": identity.display_version.encode("ascii"),
        b"MEMORY_CENSUS": memory_census(modules),
    })


def display_plan(modules: Iterable[DisplayModule]) -> bytes:
    rows = tuple(modules)
    if not rows or len(rows) > 256:
        raise SourceError("display module count differs")
    names = set()
    for row in rows:
        if type(row) is not DisplayModule:
            raise SourceError("display plan row type differs")
        _module(row.name, row.size)
        if row.name in names or type(row.display) is not bool:
            raise SourceError("display plan duplicate or role differs")
        names.add(row.name)
    if sum(row.display for row in rows) != 1:
        raise SourceError("display plan needs one DRM owner")
    lines = [
        f"#define P350_DISPLAY_MODULE_COUNT {len(rows)}U",
        "struct p350_display_module { const char *path; unsigned long long size; int display; };",
        "static const struct p350_display_module p350_display_modules[] = {",
    ]
    lines += [f'    {{"/s22-display-modules/{r.name}", {r.size}ULL, {int(r.display)}}},'
              for r in rows]
    return ("\n".join(lines + ["};"]) + "\n").encode("ascii")


def source_files() -> tuple[Path, ...]:
    """Explicit templates plus reachable quoted C includes, never sys.modules."""
    pending = [TEMPLATES / name for name in (*HELPER_PARTS, "display.c.in")]
    files = {Path(__file__).resolve()}
    while pending:
        path = pending.pop()
        if path in files:
            continue
        raw = _read(path)
        files.add(path)
        for name in re.findall(rb'^\s*#include\s+"([^"\n]+)"', raw, re.MULTILINE):
            relative = name.decode("ascii")
            if Path(relative).name != relative:
                raise SourceError("nonlocal quoted source include")
            # This header is generated by display_plan and bound as a build
            # input alongside the census, rather than read from the source tree.
            if relative == "s22plus_native_display_plan.h":
                continue
            include = NATIVE / relative
            if include not in files:
                pending.append(include)
    return tuple(sorted(files))


def source_receipts() -> dict[str, dict[str, int | str]]:
    return {str(path.relative_to(ROOT)): {
        "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()
    } for path in source_files() for raw in (_read(path),)}
