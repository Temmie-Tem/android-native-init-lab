"""Narrow host-only linkat(AT_EMPTY_PATH) adapter for P3.19 publication."""

from __future__ import annotations

import ctypes
import errno
import os


AT_EMPTY_PATH = 0x1000


def link_fd_to_name(descriptor: int, parent_fd: int, final_name: str) -> int:
    """Link one unnamed regular fd into one already-open parent directory.

    Return zero on success or the captured errno on failure.  The caller owns
    all policy, inode, directory, and no-replay checks.
    """

    if (
        type(descriptor) is not int
        or descriptor < 0
        or type(parent_fd) is not int
        or parent_fd < 0
        or not isinstance(final_name, str)
        or not final_name
        or final_name in {".", ".."}
        or "/" in final_name
        or "\x00" in final_name
    ):
        return errno.EINVAL
    libc = ctypes.CDLL(None, use_errno=True)
    linkat = libc.linkat
    linkat.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
    ]
    linkat.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = linkat(
        descriptor,
        b"",
        parent_fd,
        os.fsencode(final_name),
        AT_EMPTY_PATH,
    )
    return 0 if result == 0 else ctypes.get_errno()
