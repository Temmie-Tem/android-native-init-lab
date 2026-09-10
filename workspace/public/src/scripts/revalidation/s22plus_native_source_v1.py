"""Direct FYG8 native sources; identity injection does not grant device authority.

The default profile preserves the historical post-authentication HUD lifetime.
The explicit local-display-v1 profile is prospective H0 and grants no live use.
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
HELPER_SEPARATORS = (b"\n\n\n", b"\n", b"", b"\n", b"\n")
AUTH_KEY_PLACEHOLDER = b"P328_AUTH_KEY_BYTES"
CONSOLE_PROFILE = "console-v1"
LOCAL_PROFILE = "local-display-v1"
BASELINE_PROFILE = "native-baseline-v1"
PROFILE_PARTS = ("console_terminal.inc.c.in", "local_display.inc.c.in",
                 "local_entry.inc.c.in", "local_publish.inc.c.in",
                 "baseline_runtime.inc.c.in", "baseline_entry.inc.c.in")
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


def profile_contract(profile: str = CONSOLE_PROFILE) -> dict:
    if type(profile) is not str or profile not in (CONSOLE_PROFILE, LOCAL_PROFILE, BASELINE_PROFILE):
        raise SourceError("unknown native lifecycle profile")
    local = profile != CONSOLE_PROFILE
    value = {"profile": profile, "live_activation": False,
            "root_work_stages_61_62": "cached-before-auth" if local else "inline-after-auth",
            "display_frame_limit": 916 if local else 601,
            "display_state_limit": 8 if local else 2,
            "local_hud_log_limit": 1048576 if local else 262144,
            "collector_sample_limit": 601}
    if profile == BASELINE_PROFILE:
        value.update(native_lifetime_ms=900000, authentication_limit=8,
                     clean_detach_required=True, preparation_scope="boot-once-cached-on-reattach")
    return value


def _profile_hooks(profile: str) -> dict[bytes, bytes]:
    local = profile_contract(profile)["profile"] != CONSOLE_PROFILE
    baseline = profile == BASELINE_PROFILE
    hooks = {
        b"HUD_LOG_LIMIT": b"1048576" if local else b"262144",
        b"LOCAL_DECLARATIONS": b"static long local_pre_auth(void);\nstatic long local_write_all(int,const char *,size_t,long);\n" if local else b"",
        b"READ_SERVICE": b"        rc=local_pre_auth();if(rc)return rc;\n" if local else b"",
        b"READ_ABSENT_PEER": b"        if(input_seen!=NULL && *input_seen==0U && used==0U &&\n           (amount==0 || amount==-EIO || amount==-ENODEV || amount==-S22PLUS_P318_ERRNO_EPIPE))amount=-EAGAIN;\n" if local else b"",
        b"FRAME_WRITER": b"local_write_all" if local else b"p260_write_all",
        b"LOCAL_LIFECYCLE": _read(TEMPLATES / "local_display.inc.c.in") if local else b"",
        b"CONSOLE_HUD_START": b"    local_phase(0U);local_service();" if local else b"    struct hud1_state hud={0};hud1_start(&hud);",
        b"CONSOLE_HUD_TICK": b"        local_phase(s.control?8U:s.blocked?2U:s.active?1U:0U);local_service();" if local else b"        if(s.control)hud1_stop(&hud);else hud1_tick(&hud,now,s.blocked?2U:s.active?1U:0U);",
        b"CONSOLE_HUD_STOP": b"" if local else b"hud1_stop(&hud);",
        b"FRAMED_ENTRY": b"local_authenticated_console" if local else b"p345_framed_console",
        b"AUTHENTICATED": b"    rc=local_pre_auth();if(rc)return rc;\n    local_display.authenticated=1;local_phase(6U);local_service();\n" if local else b"",
        b"ROOT_DIRECTORY_RESULT": b"local_display.directory_rc" if local else b'syscall6(34,-100,(long)(uintptr_t)"/s22-root-work",0700,0,0,0)',
        b"ROOT_MOUNT_RESULT": b"local_display.mount_rc" if local else b'sys_mount("tmpfs","/s22-root-work","tmpfs",6UL,"size=64m,nr_inodes=4096,mode=0700")',
        b"AUTH_TERMINAL": b"    return rc;" if local else _read(TEMPLATES / "console_terminal.inc.c.in").removesuffix(b"\n"),
        b"LOCAL_ENTRY": _read(TEMPLATES / "local_entry.inc.c.in") if local else b"",
        b"WAITING_ATTRIBUTE": b"__attribute__((unused)) " if local else b"",
        b"BASELINE_DECLARATIONS": b"",
        b"BASELINE_REQUEST": b"",
        b"BASELINE_CONTROL_TICK": b"",
        b"BASELINE_CONSOLE_BUDGET": b"",
        b"BASELINE_DETACH_COMPLETE": b"",
        b"BASELINE_OPEN_ADMISSION": b"",
        b"BASELINE_NONCE_CHECK": b"",
        b"PREPARE_RETURN": b"    rc=@@NAMESPACE@@_diag_start(tty_fd,nonce);\n    if(rc==0)rc=@@NAMESPACE@@_prepare_return();",
    }
    if baseline:
        lifecycle = hooks[b"LOCAL_LIFECYCLE"]
        old = b"#define LOCAL_PREAUTH_MS 120000U"
        if lifecycle.count(old) != 1:
            raise SourceError("baseline preauth lifetime boundary differs")
        hooks[b"LOCAL_LIFECYCLE"] = (lifecycle.replace(old, b"#define LOCAL_PREAUTH_MS 900000U", 1)
            + _read(TEMPLATES / "baseline_runtime.inc.c.in"))
        hooks[b"LOCAL_ENTRY"] = _read(TEMPLATES / "baseline_entry.inc.c.in")
        hooks[b"BASELINE_DECLARATIONS"] = (b"#define RC1_DETACH 36U\n#define RC1_DETACH_ACK 167U\n"
            b"static long baseline_check(void);\nstatic int baseline_detach_available(void);\n")
        hooks[b"BASELINE_REQUEST"] = (
            b"    if(type==RC1_DETACH && !size) {\n"
            b"        if(s->active || s->pid || s->blocked || s->qcount || s->overload ||\n"
            b"           s->fault_sent || s->flags || s->dropped || !baseline_detach_available())return -P260_EPROTO;\n"
            b"        s->blocked=1;s->control=3;s->control_seq=seq;s->control_start=now;\n"
            b"        return rc1_reply_state(s,RC1_DETACH_ACK,seq,0U);\n    }\n")
        hooks[b"BASELINE_CONTROL_TICK"] = b"    if(s->control==3)return 0;\n"
        hooks[b"BASELINE_CONSOLE_BUDGET"] = b"        rc=baseline_check();if(rc)break;\n"
        hooks[b"BASELINE_DETACH_COMPLETE"] = (
            b"        if(s.control==3 && !s.qcount){rc1_close_pipes(&s);return 2;}\n")
        hooks[b"BASELINE_OPEN_ADMISSION"] = b"    rc=baseline_admit();if(rc)return rc;\n"
        hooks[b"BASELINE_NONCE_CHECK"] = b"    rc=baseline_nonce(nonce);if(rc)return rc;\n"
        hooks[b"PREPARE_RETURN"] = b"    rc=baseline_prepare(tty_fd,nonce);"
    return hooks


def helper_template(identity: Identity, *, profile: str = CONSOLE_PROFILE) -> bytes:
    raw = b"".join(_read(TEMPLATES / name) + gap
                   for name, gap in zip(HELPER_PARTS, HELPER_SEPARATORS, strict=True))
    if raw.count(b"@@AUTH_KEY_BYTES@@") != 1:
        raise SourceError("authentication key slot differs")
    hooks = _profile_hooks(profile)
    if not set(hooks).issubset(_SLOT.findall(raw)):
        raise SourceError("source profile slots differ")
    raw = _SLOT.sub(lambda match: hooks.get(match[1], match[0]), raw)
    return _expand(raw, {
        b"NAMESPACE": identity.namespace.encode("ascii"),
        b"NAMESPACE_UPPER": identity.namespace.upper().encode("ascii"),
        b"RUN_ID_HEX": identity.run_id_hex.encode("ascii"),
        b"RUN_ID_ESCAPED": "".join(f"\\x{byte:02x}" for byte in
                                   identity.run_id_hex.encode("ascii")).encode("ascii"),
        b"AUTH_KEY_BYTES": AUTH_KEY_PLACEHOLDER,
    })


def materialize_helper(identity: Identity, auth_key: bytes, *, profile: str = CONSOLE_PROFILE) -> bytes:
    if type(auth_key) is not bytes or len(auth_key) != 32:
        raise SourceError("authentication key must be exactly 32 bytes")
    source = helper_template(identity, profile=profile)
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


def render_display(identity: Identity, modules: Iterable[MemoryModule], *, profile: str = CONSOLE_PROFILE) -> bytes:
    contract = profile_contract(profile)
    states = b'hud_console_state==0?"CONSOLE: READY":hud_console_state==1?"CONSOLE: BUSY":"CONSOLE: BLOCKED"'
    if profile != CONSOLE_PROFILE:
        labels = ("CONSOLE: READY", "CONSOLE: BUSY", "CONSOLE: BLOCKED", "WAITING FOR AUTH",
                  "AUTH FAILED", "TIME EXPIRED", "PREPARING", "RUNTIME FAILED", "CLOSING")
        states = b"((const char *const[]){" + b",".join(b'"' + x.encode() + b'"' for x in labels) + b"})[hud_console_state]"
    return _expand(_read(TEMPLATES / "display.c.in"), {
        b"DISPLAY_VERSION": identity.display_version.encode("ascii"),
        b"MEMORY_CENSUS": memory_census(modules),
        b"DISPLAY_FRAME_LIMIT": str(contract["display_frame_limit"]).encode(),
        b"DISPLAY_STATE_LIMIT": str(contract["display_state_limit"]).encode(),
        b"DISPLAY_STATE_TEXT": states,
    })


def join_platform(runtime: bytes, identity: Identity, auth_key: bytes, *, profile: str) -> bytes:
    """One explicit join to an externally bound platform envelope (H0 only).

    The caller verifies the full platform source identity. No old generator is
    imported, and local publication replaces the historical listener wholesale.
    """
    profile_contract(profile)
    before = materialize_helper(identity, auth_key)
    if runtime.count(before) != 1:
        raise SourceError("platform production helper boundary differs")
    result = runtime.replace(before, materialize_helper(identity, auth_key, profile=profile), 1)
    if profile == CONSOLE_PROFILE:
        return result
    anchor = b"static __attribute__((noreturn)) void p319_stock_publish(int tty_fd) {\n"
    if result.count(anchor) != 1:
        raise SourceError("platform publication boundary differs")
    start = result.index(anchor)
    end = result.index(b"\n}\n", start) + 3
    previous = result[start:end]
    if (previous.count(b"p335_getrandom_boot_id(") != 1 or
            not previous.endswith(b"    p290_park_after_confirmed_publication();\n}\n")):
        raise SourceError("unsupported platform publication body")
    result = result[:start] + _read(TEMPLATES / "local_publish.inc.c.in") + result[end:]
    # Three legacy publication-only witnesses are now unreachable. Preserve
    # their bodies without weakening global compiler warnings or invoking them.
    for signature in (b"static int p320_observer_chain_ambiguous(",
                      b"static void p319_stock_bypass_to_pair(",
                      b"static int s22plus_max77705_p319_stock_encode("):
        if result.count(signature) != 1:
            raise SourceError("legacy publication witness boundary differs")
        result = result.replace(signature, signature.replace(b"static ", b"static __attribute__((unused)) ", 1), 1)
    return result


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
    pending = [TEMPLATES / name for name in (*HELPER_PARTS, *PROFILE_PARTS, "display.c.in")]
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
