#!/usr/bin/env python3
"""Regular-path Odin transport primitives for checked boot-only AP files.

Odin4 identifies AP inputs by filename and rejects anonymous proc-fd paths.  This
module keeps each source descriptor open, verifies its exact identity, passes the
real ``.tar.md5`` pathname to Odin, and verifies the same pathname again after
the subprocess returns.  It owns no target, policy, or candidate decisions.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import stat
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


ODIN_DEVICE_RE = re.compile(r"/dev/bus/usb/[0-9]{3}/[0-9]{3}")
BOOT_MEMBER = "boot.img.lz4"


class F1TransportError(RuntimeError):
    pass


def _identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


@dataclass(frozen=True)
class PinnedRegularFile:
    path: Path
    descriptor: int
    size: int
    sha256: str
    identity: tuple[int, int, int, int, int]

    def receipt(self) -> dict[str, str | int]:
        return {
            "path": str(self.path),
            "size": self.size,
            "sha256": self.sha256,
        }


def _direct_absolute_path(path: Path, label: str) -> Path:
    absolute = path.absolute()
    try:
        entry = os.lstat(absolute)
    except OSError as exc:
        raise F1TransportError(f"{label} is unavailable: {absolute}") from exc
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
        raise F1TransportError(f"{label} is not a direct regular file: {absolute}")
    resolved = absolute.resolve(strict=True)
    if resolved != absolute:
        raise F1TransportError(f"{label} has an indirect path component: {absolute}")
    return absolute


def _hash_descriptor(descriptor: int, maximum: int) -> tuple[int, str]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            raise F1TransportError(f"pinned file exceeds bound: {total} > {maximum}")
        digest.update(chunk)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return total, digest.hexdigest()


def revalidate_pinned_path(pinned: PinnedRegularFile) -> None:
    descriptor_identity = _identity(os.fstat(pinned.descriptor))
    try:
        path_value = os.lstat(pinned.path)
    except OSError as exc:
        raise F1TransportError(f"pinned path disappeared: {pinned.path}") from exc
    if stat.S_ISLNK(path_value.st_mode) or not stat.S_ISREG(path_value.st_mode):
        raise F1TransportError(f"pinned path is no longer direct: {pinned.path}")
    if descriptor_identity != pinned.identity or _identity(path_value) != pinned.identity:
        raise F1TransportError(f"pinned path identity changed: {pinned.path}")


@contextlib.contextmanager
def pin_regular_file(
    path: Path,
    *,
    label: str,
    expected_size: int,
    expected_sha256: str,
) -> Iterator[PinnedRegularFile]:
    if expected_size <= 0 or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise F1TransportError(f"invalid identity pin for {label}")
    direct = _direct_absolute_path(path, label)
    descriptor = os.open(
        direct,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    pinned: PinnedRegularFile | None = None
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise F1TransportError(f"{label} descriptor is not regular")
        identity = _identity(opened)
        if _identity(os.lstat(direct)) != identity:
            raise F1TransportError(f"{label} path changed while opening")
        size, digest = _hash_descriptor(descriptor, expected_size)
        if size != expected_size or digest != expected_sha256:
            raise F1TransportError(f"{label} identity does not match its pin")
        pinned = PinnedRegularFile(direct, descriptor, size, digest, identity)
        revalidate_pinned_path(pinned)
        yield pinned
        revalidate_pinned_path(pinned)
    finally:
        os.close(descriptor)


@contextlib.contextmanager
def pin_boot_only_ap(
    path: Path,
    *,
    label: str,
    expected_size: int,
    expected_sha256: str,
) -> Iterator[PinnedRegularFile]:
    if not path.name.endswith(".tar.md5"):
        raise F1TransportError(f"{label} must use a .tar.md5 pathname")
    with pin_regular_file(
        path,
        label=label,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
    ) as pinned:
        os.lseek(pinned.descriptor, 0, os.SEEK_SET)
        try:
            with os.fdopen(os.dup(pinned.descriptor), "rb") as stream:
                with tarfile.open(fileobj=stream, mode="r:*") as archive:
                    members = archive.getmembers()
        except (OSError, tarfile.TarError) as exc:
            raise F1TransportError(f"{label} is not a readable AP archive") from exc
        finally:
            os.lseek(pinned.descriptor, 0, os.SEEK_SET)
        if (
            len(members) != 1
            or members[0].name != BOOT_MEMBER
            or not members[0].isfile()
        ):
            raise F1TransportError(f"{label} is not exactly boot-only")
        revalidate_pinned_path(pinned)
        yield pinned


def build_odin_boot_only_command(
    odin_path: Path, ap_path: Path, device: str
) -> list[str]:
    if not odin_path.is_absolute() or not ap_path.is_absolute():
        raise F1TransportError("Odin and AP paths must be absolute")
    if not ap_path.name.endswith(".tar.md5"):
        raise F1TransportError("Odin AP argument must retain its .tar.md5 suffix")
    if str(odin_path).startswith("/proc/") or str(ap_path).startswith("/proc/"):
        raise F1TransportError("anonymous proc-fd paths are forbidden for Odin inputs")
    if ODIN_DEVICE_RE.fullmatch(device) is None:
        raise F1TransportError(f"non-canonical Odin device path: {device}")
    return [str(odin_path), "--reboot", "-a", str(ap_path), "-d", device]


def execute_odin_boot_only(
    odin_path: Path,
    ap_path: Path,
    device: str,
    *,
    odin_size: int,
    odin_sha256: str,
    ap_size: int,
    ap_sha256: str,
    label: str,
    timeout: float = 240.0,
    maximum_output: int = 8 * 1024 * 1024,
) -> tuple[dict[str, object], bytes, bytes]:
    if not 1 <= timeout <= 600 or not 1 <= maximum_output <= 64 * 1024 * 1024:
        raise F1TransportError("invalid Odin execution bound")
    with pin_regular_file(
        odin_path,
        label="Odin4",
        expected_size=odin_size,
        expected_sha256=odin_sha256,
    ) as odin, pin_boot_only_ap(
        ap_path,
        label=label,
        expected_size=ap_size,
        expected_sha256=ap_sha256,
    ) as ap:
        if not os.access(odin.path, os.X_OK):
            raise F1TransportError("pinned Odin4 is not executable")
        command = build_odin_boot_only_command(odin.path, ap.path, device)
        revalidate_pinned_path(odin)
        revalidate_pinned_path(ap)
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
        if len(stdout) + len(stderr) > maximum_output:
            raise F1TransportError("Odin output exceeded its bound")
        revalidate_pinned_path(odin)
        revalidate_pinned_path(ap)
        receipt: dict[str, object] = {
            "label": label,
            "returncode": completed.returncode,
            "command_shape": ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"],
            "regular_path_inputs": True,
            "anonymous_proc_fd_inputs": False,
            "odin": odin.receipt(),
            "ap": ap.receipt(),
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        }
        return receipt, stdout, stderr
