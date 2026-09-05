"""Dormant H0 successor seam: existing OPEN before any device preamble.

No live registration, candidate identity, artifact, manifest or device action.
P340 is consumed; transformed bytes must never be used with its identity.
The caller must supply a privately loaded observer, not a shared live module.
Later-action integration is deliberately outside this three-session H0 unit.
"""
from __future__ import annotations

import inspect
import termios
from typing import Any

import s22plus_fyg8_p340_open_read_branch_runtime as base


def _once(value: bytes, old: bytes, new: bytes) -> bytes:
    if value.count(old) != 1:
        raise ValueError("host-first source anchor is absent or ambiguous")
    return value.replace(old, new, 1)


def helper(value: bytes) -> bytes:
    """Change only first-OPEN input accounting and post-OPEN preamble."""
    value = _once(value, b"static long p328_read_exact(\n    int fd, uint8_t *output, size_t size, long timeout_sec) {",
        b"static long p341_read_exact(\n    int fd, uint8_t *output, size_t size, long timeout_sec,\n    uint8_t *input_seen) {")
    value = _once(value, b"            used += (size_t)amount;\n",
        b"            if (input_seen != NULL) *input_seen = 1U;\n            used += (size_t)amount;\n")
    wrapper = b"""static long p328_read_exact(
    int fd, uint8_t *output, size_t size, long timeout_sec) {
    return p341_read_exact(fd, output, size, timeout_sec, NULL);
}

"""
    value = _once(value, b"static long p328_read_frame(\n", wrapper + b"static long p328_read_frame(\n")
    value = _once(value, b"    uint8_t open_header[P328_HEADER_SIZE], uint8_t *open_branch) {",
        b"    uint8_t open_header[P328_HEADER_SIZE], uint8_t *open_branch,\n    uint8_t *input_seen) {")
    value = _once(value, b"    long rc = p328_read_exact(\n        fd, header, sizeof(header), P328_INPUT_DEADLINE_SEC);",
        b"    long rc = p341_read_exact(\n        fd, header, sizeof(header), P328_INPUT_DEADLINE_SEC, input_seen);")
    # Later AUTH/EXEC readers retain their exact behavior through the wrapper.
    if value.count(b"NULL, NULL);") != 2:
        raise ValueError("later frame call sites differ")
    value = value.replace(b"NULL, NULL);", b"NULL, NULL, NULL);")
    value = _once(value, b"        p339_open_header, &p339_open_branch);\n    if (rc != 0) {",
        b"        p339_open_header, &p339_open_branch, open_seen);\n    if (rc != 0) {\n        if (*open_seen == 0U) return rc; /* no peer: no unsolicited TX */")
    value = _once(value, b"    *open_seen = 0U;\n",
        b"    /* This flag means any consumed OPEN byte, not authentication. */\n    *open_seen = 0U;\n")
    value = _once(value, b"    *open_seen = 1U;\n\n    rc = p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0);",
        b"""    *open_seen = 1U;
    struct s22plus_p318_banner_result banner =
        s22plus_p318_banner_attempt(tty_fd);
    if (banner.outcome != S22PLUS_P318_BANNER_WRITTEN) return -EIO;
    rc = p330_write_diagnostic(tty_fd, 0U, 0);
    if (rc != 0) return rc;
    rc = p330_write_diagnostic(tty_fd, P330_DIAG_OPEN_PARSED, 0);
    if (rc != 0) return rc;""")
    return value


def entry(value: bytes) -> bytes:
    """Remove all three unsolicited preambles; reuse one console entry."""
    start = value.index(b"    struct s22plus_p318_banner_result p335_banner_1 =")
    end = value.index(b"    if (p335_first_session_rc != 0", start)
    value = _once(value, value[start:end], b"""    p335_first_session_rc = p335_framed_console(
        tty_fd, p335_boot_id, &p335_first_open_seen);
""")
    start = value.index(b"        struct s22plus_p318_banner_result p335_banner_2 =")
    end = value.index(b"    }\n    if (p335_first_session_rc == 0", start)
    value = _once(value, value[start:end], b"""        p335_second_session_rc = p335_framed_console(
            tty_fd, p335_boot_id, &p335_second_open_seen);
""")
    start = value.index(b"            struct s22plus_p318_banner_result p335_listener_banner =")
    end = value.index(b"            long p335_listener_rc =", start)
    value = _once(value, value[start:end], b"            uint8_t p335_listener_open_seen = 0U;\n")
    if b"banner_attempt" in value or b"p330_write_diagnostic" in value:
        raise ValueError("unsolicited publisher output remains")
    return value


def transform_runtime_include(value: bytes, auth_key: bytes) -> bytes:
    """H0 only: retain P340 identity for source comparison, never packaging."""
    base.validate_p340_runtime(value, auth_key_sha256=base.auth_key_sha256(auth_key))
    original = base.materialize_helper(auth_key)
    result = _once(value, original, helper(original))
    return _once(result, base.P340_ENTRY, entry(base.P340_ENTRY))


def require_raw(descriptor: int) -> None:
    """Check echo/canonical/signal suppression, not full raw-mode identity.

    The existing caller still performs full raw setup before this codec.
    """
    flags = termios.tcgetattr(descriptor)
    if flags[3] & (termios.ECHO | termios.ICANON | termios.ISIG):
        raise ValueError("host-first OPEN requires an already raw TTY")


def install_observer(module: Any) -> None:
    """Reorder the existing privately loaded codec, without a second OPEN."""
    source = inspect.getsource(module._exchange_one)
    block = '''        stage("open-write")
        _CODEC._send(  # noqa: SLF001
            descriptor, runtime.FRAME_OPEN, 0, runtime.P335_RUN_ID,
            deadline, audit,
        )

'''
    if source.count(block) != 1 or source.count('        stage("banner-read")') != 1:
        raise ValueError("observer OPEN ordering source differs")
    source = source.replace(block, "", 1).replace(
        '        stage("banner-read")',
        '        _host_first_require_raw(descriptor)\n' + block + '        stage("banner-read")', 1,
    )
    module.__dict__["_host_first_require_raw"] = require_raw
    exec(compile(source, "<host-first-open-h0>", "exec", dont_inherit=True), module.__dict__)
