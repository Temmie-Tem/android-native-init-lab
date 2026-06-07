#!/usr/bin/env python3
"""Shared host-side lock for A90 serial bridge transactions."""

from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path

from _workspace_bootstrap import repo_root


DEFAULT_LOCK_REL = "workspace/private/run/a90-serial-bridge.lock"
LOCK_POLL_INTERVAL_SEC = 0.05
ENV_LOCK_TIMEOUT_SEC = "A90_SERIAL_LOCK_TIMEOUT_SEC"


class SerialBridgeLockBusy(TimeoutError):
    """Raised when another host process owns the serial bridge transaction lock."""


def lock_path(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else repo_root() / DEFAULT_LOCK_REL


def default_timeout(timeout_sec: float | None) -> float | None:
    if timeout_sec is not None:
        return timeout_sec
    value = os.environ.get(ENV_LOCK_TIMEOUT_SEC)
    if value in {None, ""}:
        return None
    return max(0.0, float(value))


class SerialBridgeLock:
    def __init__(self,
                 *,
                 timeout_sec: float | None = None,
                 purpose: str = "serial-bridge",
                 path: str | Path | None = None) -> None:
        self.path = lock_path(path)
        self.timeout_sec = default_timeout(timeout_sec)
        self.purpose = purpose
        self.handle = None

    def __enter__(self) -> "SerialBridgeLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        deadline = None if self.timeout_sec is None else time.monotonic() + self.timeout_sec

        while True:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if deadline is not None and time.monotonic() >= deadline:
                    self.handle.close()
                    self.handle = None
                    raise SerialBridgeLockBusy(
                        f"serial bridge transaction lock busy: {self.path}"
                    ) from exc
                time.sleep(LOCK_POLL_INTERVAL_SEC)

        metadata = {
            "pid": os.getpid(),
            "purpose": self.purpose,
            "started_monotonic": time.monotonic(),
        }
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(json.dumps(metadata, sort_keys=True) + "\n")
        self.handle.flush()
        os.fsync(self.handle.fileno())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - context manager protocol
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.flush()
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None
