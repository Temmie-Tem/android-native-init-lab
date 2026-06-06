"""Single-writer device command client for A90 native-init validation."""

from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

from a90ctl import ProtocolResult, run_cmdv1_command
from a90_broker import PROTO as BROKER_PROTO
from a90_broker import connect_and_call

from a90harness.schema import CommandRecord


class DeviceClient:
    """Thread-safe wrapper around direct cmdv1 or the A90B1 broker protocol."""

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 54321,
                 timeout: float = 20.0,
                 *,
                 backend: str = "direct",
                 broker_socket: Path | None = None,
                 client_id: str | None = None) -> None:
        if backend not in {"direct", "broker"}:
            raise ValueError(f"unsupported device backend: {backend}")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.backend = backend
        self.broker_socket = broker_socket
        self.client_id = client_id or f"harness:{os.getpid()}"
        self._lock = threading.RLock()
        if self.backend == "broker" and self.broker_socket is None:
            raise ValueError("broker backend requires broker_socket")

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        """Reserve this process' command client while an external tool runs."""

        with self._lock:
            yield

    def metadata(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "broker_socket": str(self.broker_socket) if self.broker_socket is not None else None,
            "client_id": self.client_id,
        }

    def _run_direct(self,
                    command: list[str],
                    *,
                    timeout: float | None,
                    retry_unsafe: bool) -> tuple[int, str, str]:
        result: ProtocolResult = run_cmdv1_command(
            self.host,
            self.port,
            self.timeout if timeout is None else timeout,
            command,
            retry_unsafe=retry_unsafe,
        )
        return result.rc, result.status, result.text

    def _run_broker(self,
                    name: str,
                    command: list[str],
                    *,
                    timeout: float | None) -> tuple[int | None, str, str, str]:
        if self.broker_socket is None:
            raise RuntimeError("broker socket is not configured")
        timeout_sec = self.timeout if timeout is None else timeout
        payload = {
            "proto": BROKER_PROTO,
            "id": f"{name}-{uuid4().hex}",
            "client_id": self.client_id,
            "op": "cmd",
            "argv": command,
            "timeout_ms": int(timeout_sec * 1000),
        }
        response = connect_and_call(self.broker_socket, payload, timeout_sec + 5.0)
        status = str(response.get("status", "missing"))
        text = str(response.get("text") or "")
        error = str(response.get("error") or "")
        rc_raw = response.get("rc")
        rc = rc_raw if isinstance(rc_raw, int) else None
        return rc, status, text, error

    def run(self,
            name: str,
            command: list[str],
            *,
            timeout: float | None = None,
            retry_unsafe: bool = False,
            transcript: str = "") -> tuple[CommandRecord, str]:
        started = time.monotonic()
        with self._lock:
            try:
                if self.backend == "broker":
                    rc, status, text, broker_error = self._run_broker(name, command, timeout=timeout)
                    ok = rc == 0 and status == "ok"
                    error = "" if ok else broker_error
                    output = text if text else (broker_error + "\n" if broker_error else "")
                else:
                    rc, status, output = self._run_direct(
                        command,
                        timeout=timeout,
                        retry_unsafe=retry_unsafe,
                    )
                    ok = rc == 0 and status == "ok"
                    error = ""
                duration = time.monotonic() - started
                record = CommandRecord(
                    name=name,
                    command=command,
                    ok=ok,
                    rc=rc,
                    status=status,
                    duration_sec=duration,
                    transcript=transcript,
                    error=error,
                )
                return record, output
            except Exception as exc:  # noqa: BLE001 - harness records exact failure evidence
                duration = time.monotonic() - started
                record = CommandRecord(
                    name=name,
                    command=command,
                    ok=False,
                    rc=None,
                    status="exception",
                    duration_sec=duration,
                    transcript=transcript,
                    error=f"{type(exc).__name__}: {exc}",
                )
                return record, record.error + "\n"
