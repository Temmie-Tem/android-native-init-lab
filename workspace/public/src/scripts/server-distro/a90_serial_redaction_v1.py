#!/usr/bin/env python3
"""Fail-closed in-process redaction for A90 ADB endpoint identities.

The redactor is used only by the reviewed owner path.  It keeps raw values in
memory long enough to issue the bound command, but all diagnostic text,
command renderings, and persisted child output pass through this boundary.
Unknown ADB inventory serial columns are registered before digest-only
persistence; registered values are also replaced in arbitrary
stderr/exception text after the inventory.
"""

from __future__ import annotations

import hashlib
import os
import re
import signal
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Callable


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SERIAL_RE = re.compile(r"^[!-~]{1,256}$")
TOKEN_TEXT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}")
ADB_FIRST_TOKEN_RE = re.compile(r"^([!-~]{1,256})(?=\s|$)")
ADB_STATE_RE = re.compile(r"^(?:device|recovery|offline|unauthorized|no permissions)(?:\s|$)")
ADB_STDOUT_DIGEST_PREFIX = "<A90-ADB-INVENTORY-STDOUT-SHA256:"
ADB_STDERR_DIGEST_PREFIX = "<A90-ADB-INVENTORY-STDERR-SHA256:"


def _marker(digest: str) -> str:
    return f"<A90-ADB-SERIAL-SHA256:{digest}>"


class SerialRedactor:
    """Owner-only redaction registry; its representation never exposes secrets."""

    def __init__(self, hashes: Iterable[str] = ()) -> None:
        self._hashes: set[str] = set()
        self._secrets: dict[str, str] = {}
        for digest in hashes:
            self.register_hash(digest)

    def __repr__(self) -> str:
        return "SerialRedactor(<registered>)"

    def register_hash(self, digest: str) -> None:
        if type(digest) is not str or SHA256_RE.fullmatch(digest) is None:
            raise ValueError("serial redaction hash is not exact")
        self._hashes.add(digest)

    def register_secret(self, value: str) -> str:
        if type(value) is not str or SERIAL_RE.fullmatch(value) is None:
            raise ValueError("serial redaction value is not exact")
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        self._hashes.add(digest)
        self._secrets[value] = digest
        return digest

    def _token_replacement(self, token: str) -> str:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if digest in self._hashes:
            return _marker(digest)
        return token

    def text(self, value: object) -> str:
        if type(value) is str:
            rendered = value
        elif isinstance(value, bytes):
            rendered = value.decode("utf-8", errors="replace")
        else:
            rendered = str(value)
        for secret, digest in sorted(
            self._secrets.items(), key=lambda item: len(item[0]), reverse=True
        ):
            rendered = rendered.replace(secret, _marker(digest))
        return re.sub(
            TOKEN_TEXT_RE,
            lambda match: self._token_replacement(match.group(0)),
            rendered,
        )

    def register_adb_inventory_tokens(self, value: bytes) -> bool:
        """Register first-column tokens and report whether the envelope is safe to redact."""
        try:
            rendered = value.decode("ascii")
        except UnicodeDecodeError:
            return False
        lines = rendered.replace("\r", "").splitlines()
        if not lines or lines[0] != "List of devices attached":
            return False
        safe = True
        for line in lines[1:]:
            if not line:
                continue
            match = ADB_FIRST_TOKEN_RE.match(line)
            if match is None:
                safe = False
                continue
            self.register_secret(match.group(1))
            if ADB_STATE_RE.match(line[match.end(1) :].lstrip()) is None:
                safe = False
        return safe

    @staticmethod
    def _inventory_digest_marker(prefix: str, value: bytes, status: str) -> bytes:
        digest = hashlib.sha256(value).hexdigest()
        return f"{prefix}{digest}> len={len(value)} status={status}\n".encode()

    def prepare_adb_inventory(
        self,
        stdout: bytes,
        stderr: bytes,
        *,
        returncode: int,
        timed_out: bool,
    ) -> tuple[bytes, bytes]:
        """Return digest-only inventory streams after a complete first pass."""
        stdout_safe = self.register_adb_inventory_tokens(stdout)
        status = (
            "timeout"
            if timed_out
            else "nonzero"
            if returncode != 0
            else "valid"
            if stdout_safe
            else "malformed"
        )
        safe_stdout = self._inventory_digest_marker(
            ADB_STDOUT_DIGEST_PREFIX, stdout, status
        )
        safe_stderr = (
            b""
            if not stderr
            else self._inventory_digest_marker(
                ADB_STDERR_DIGEST_PREFIX, stderr, "nonempty"
            )
        )
        return safe_stdout, safe_stderr

    def bytes(self, value: bytes) -> bytes:
        if type(value) is not bytes:
            raise ValueError("redaction input is not bytes")
        return self.text(value).encode("utf-8")

    def argv(self, argv: Sequence[object]) -> list[str]:
        return [self.text(item) for item in argv]


def marker_for_hash(digest: str) -> str:
    if type(digest) is not str or SHA256_RE.fullmatch(digest) is None:
        raise ValueError("serial redaction hash is not exact")
    return _marker(digest)


def run_owner_process(
    argv: Sequence[str],
    timeout_sec: int,
    *,
    cwd: Path,
    log_directory: Path,
    stdout_path: Path,
    stderr_path: Path,
    redactor: SerialRedactor,
    max_output_bytes: int,
    adb_inventory: bool,
    preexec_fn: Callable[[], None],
    process_group_exists: Callable[[int], bool],
) -> tuple[int, bytes, bytes, bool]:
    """Run one owner child and persist only redacted stdout/stderr."""
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    stdout_fd = os.open(stdout_path, flags, 0o600)
    stderr_fd = os.open(stderr_path, flags, 0o600)
    process: subprocess.Popen[bytes] | None = None
    timed_out = False
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env={"HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            start_new_session=True,
            preexec_fn=preexec_fn,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        if len(stdout) > max_output_bytes or len(stderr) > max_output_bytes:
            raise RuntimeError("adapter output exceeds its fixed bound")
        if adb_inventory:
            safe_stdout, safe_stderr = redactor.prepare_adb_inventory(
                stdout,
                stderr,
                returncode=124 if timed_out else process.returncode,
                timed_out=timed_out,
            )
        else:
            safe_stdout = redactor.bytes(stdout)
            safe_stderr = redactor.bytes(stderr)
        if len(safe_stdout) > max_output_bytes or len(safe_stderr) > max_output_bytes:
            raise RuntimeError("redacted adapter output exceeds its fixed bound")
        for descriptor, payload in ((stdout_fd, safe_stdout), (stderr_fd, safe_stderr)):
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise RuntimeError("adapter output write stalled")
                offset += written
            os.fsync(descriptor)
        descriptor = os.open(log_directory, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        quiescent = not process_group_exists(process.pid)
        return (124 if timed_out else process.returncode), stdout, stderr, quiescent
    finally:
        os.close(stdout_fd)
        os.close(stderr_fd)
