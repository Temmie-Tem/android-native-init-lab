#!/usr/bin/env python3
"""Fixed inherited-FD launch contract for the A90 boot-only F1 helper.

This module performs no device action.  The future reviewed owner imports its
fixed loader string and passes only an already validated bootstrap descriptor.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Python executes this capability-bound string under ``-I -c``.  It never
# opens the source-package pathname.  The pathname is diagnostic metadata;
# every executable helper byte comes from the sealed inherited FD.
FD_EXEC_PROGRAM = r'''import hashlib
import fcntl
import os
import stat
import sys

fd = int(sys.argv[1], 10)
bootstrap_path = sys.argv[2]
expected_size = int(sys.argv[3], 10)
expected_sha256 = sys.argv[4]
helper_argv = sys.argv[5:]
metadata = os.fstat(fd)
required_seals = (
    fcntl.F_SEAL_SEAL
    | fcntl.F_SEAL_SHRINK
    | fcntl.F_SEAL_GROW
    | fcntl.F_SEAL_WRITE
)
if (
    not stat.S_ISREG(metadata.st_mode)
    or metadata.st_nlink != 0
    or fcntl.fcntl(fd, fcntl.F_GET_SEALS) != required_seals
):
    raise RuntimeError("bootstrap inherited FD is not one sealed source capability")
if metadata.st_size != expected_size:
    raise RuntimeError("bootstrap inherited FD size mismatch")
os.lseek(fd, 0, os.SEEK_SET)
chunks = []
remaining = expected_size
while remaining:
    chunk = os.read(fd, min(remaining, 1 << 20))
    if not chunk:
        raise RuntimeError("bootstrap inherited FD ended early")
    chunks.append(chunk)
    remaining -= len(chunk)
if os.read(fd, 1):
    raise RuntimeError("bootstrap inherited FD exceeds bound size")
source = b"".join(chunks)
if hashlib.sha256(source).hexdigest() != expected_sha256:
    raise RuntimeError("bootstrap inherited FD digest mismatch")
os.close(fd)
sys.argv = [bootstrap_path, *helper_argv]
bootstrap_globals = {
    "__name__": "__main__",
    "__file__": bootstrap_path,
    "__package__": None,
    "__cached__": None,
    "__a90_bootstrap_fd_bound__": True,
}
exec(compile(source, bootstrap_path, "exec", dont_inherit=True), bootstrap_globals)
'''


def bootstrap_command(
    python_executable: Path,
    bootstrap_fd: int,
    bootstrap_path: Path,
    bootstrap_size: int,
    bootstrap_sha256: str,
    helper_arguments: Sequence[str],
) -> tuple[str, ...]:
    """Return the sole isolated command for an inherited bootstrap FD."""

    if not python_executable.is_absolute() or not bootstrap_path.is_absolute():
        raise ValueError("bootstrap command paths must be absolute")
    if type(bootstrap_fd) is not int or bootstrap_fd < 0:
        raise ValueError("bootstrap descriptor must be one nonnegative integer")
    if type(bootstrap_size) is not int or bootstrap_size <= 0:
        raise ValueError("bootstrap size must be one positive integer")
    if type(bootstrap_sha256) is not str or not SHA256_RE.fullmatch(bootstrap_sha256):
        raise ValueError("bootstrap SHA256 must be lowercase canonical hex")
    if any(type(argument) is not str for argument in helper_arguments):
        raise ValueError("helper arguments must be strings")
    return (
        str(python_executable),
        "-I",
        "-c",
        FD_EXEC_PROGRAM,
        str(bootstrap_fd),
        str(bootstrap_path),
        str(bootstrap_size),
        bootstrap_sha256,
        *helper_arguments,
    )


def bootstrap_pass_fds(bootstrap_fd: int) -> tuple[int]:
    """Return the exact subprocess ``pass_fds`` tuple for the bootstrap."""

    if type(bootstrap_fd) is not int or bootstrap_fd < 0:
        raise ValueError("bootstrap descriptor must be one nonnegative integer")
    return (bootstrap_fd,)
