#!/usr/bin/env python3
"""Non-authoritative host USB trace sidecar for an attended F1 window."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "device_action_usb_trace_sidecar_v1"
DEFAULT_DURATION_SEC = 45 * 60
MAX_DURATION_SEC = 60 * 60
MAX_LOG_BYTES = 32 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 1024 * 1024
JOURNALCTL = Path("/usr/bin/journalctl")
UDEVADM = Path("/usr/bin/udevadm")
LSUSB = Path("/usr/bin/lsusb")
SOURCE_COMMANDS = {
    "kernel": (
        str(JOURNALCTL),
        "--dmesg",
        "--follow",
        "--lines=0",
        "--no-pager",
        "--output=short-iso-precise",
    ),
    "udev": (
        str(UDEVADM),
        "monitor",
        "--kernel",
        "--udev",
        "--property",
        "--subsystem-match=usb",
        "--subsystem-match=tty",
    ),
}


class SidecarError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_exclusive(path: Path, payload: bytes) -> dict[str, Any]:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        if os.write(descriptor, payload) != len(payload):
            raise SidecarError(f"short durable write: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_dir(path.parent)
    return {
        "name": path.name,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def repo_private_root() -> Path:
    return Path(__file__).resolve().parents[5] / "workspace/private"


def create_output_dir(output_dir: Path, private_root: Path) -> Path:
    root = private_root.resolve(strict=True)
    if output_dir.exists() or output_dir.is_symlink():
        raise SidecarError("sidecar output directory already exists")
    parent = output_dir.parent.resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as exc:
        raise SidecarError("sidecar output must be below workspace/private") from exc
    output_dir.mkdir(mode=0o700)
    resolved = output_dir.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SidecarError("sidecar output escaped workspace/private") from exc
    if resolved != output_dir.absolute():
        raise SidecarError("sidecar output path is indirect")
    fsync_dir(parent)
    return resolved


def bounded_snapshot(
    command: Sequence[str],
    *,
    timeout_sec: float = 5.0,
    maximum: int = MAX_SNAPSHOT_BYTES,
) -> dict[str, Any]:
    if not command or maximum <= 0:
        raise SidecarError("snapshot command is invalid")
    try:
        completed = subprocess.run(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            check=False,
            env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        )
        stdout = completed.stdout[:maximum]
        stderr = completed.stderr[:maximum]
        return {
            "available": True,
            "command": list(command),
            "returncode": completed.returncode,
            "stdout_text": stdout.decode("utf-8", "backslashreplace"),
            "stderr_text": stderr.decode("utf-8", "backslashreplace"),
            "stdout_truncated": len(completed.stdout) > maximum,
            "stderr_truncated": len(completed.stderr) > maximum,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "available": False,
            "command": list(command),
            "error_type": type(exc).__name__,
        }


@dataclass
class SourceCapture:
    name: str
    command: tuple[str, ...]
    path: Path
    process: subprocess.Popen[bytes] | None = None
    thread: threading.Thread | None = None
    bytes_written: int = 0
    truncated: bool = False
    error_type: str | None = None

    def start(self) -> None:
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            self.process = subprocess.Popen(
                list(self.command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
        except Exception:
            os.close(descriptor)
            raise
        self.thread = threading.Thread(
            target=self._drain,
            args=(descriptor,),
            name=f"usb-trace-{self.name}",
            daemon=False,
        )
        self.thread.start()

    def _drain(self, descriptor: int) -> None:
        try:
            assert self.process is not None
            assert self.process.stdout is not None
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                prefix = f"{utc_now()} source={self.name} ".encode("ascii")
                record = prefix + line
                if not record.endswith(b"\n"):
                    record += b"\n"
                remaining = MAX_LOG_BYTES - self.bytes_written
                if remaining > 0:
                    chunk = record[:remaining]
                    written = os.write(descriptor, chunk)
                    if written != len(chunk):
                        raise SidecarError(f"short {self.name} log write")
                    self.bytes_written += written
                if len(record) > remaining:
                    self.truncated = True
            os.fsync(descriptor)
        except Exception as exc:
            self.error_type = type(exc).__name__
        finally:
            os.close(descriptor)

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.thread is not None:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise SidecarError(f"{self.name} capture thread did not stop")
        if self.process.stdout is not None:
            self.process.stdout.close()

    def receipt(self) -> dict[str, Any]:
        payload = self.path.read_bytes()
        return {
            "command": list(self.command),
            "returncode": self.process.returncode if self.process else None,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "truncated": self.truncated,
            "error_type": self.error_type,
        }


class StopRequest:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.signal_name: str | None = None

    def handler(self, signum: int, _frame: Any) -> None:
        self.signal_name = signal.Signals(signum).name
        self.event.set()


def capture(
    output_dir: Path,
    *,
    duration_sec: float,
    private_root: Path,
    source_commands: dict[str, tuple[str, ...]] = SOURCE_COMMANDS,
    snapshot_command: tuple[str, ...] = (str(LSUSB),),
    install_signal_handlers: bool = True,
) -> dict[str, Any]:
    if duration_sec <= 0 or duration_sec > MAX_DURATION_SEC:
        raise SidecarError("sidecar duration is outside the bounded range")
    destination = create_output_dir(output_dir, private_root)
    started_utc = utc_now()
    started = time.monotonic()
    start_value = {
        "schema": SCHEMA,
        "phase": "start",
        "started_utc": started_utc,
        "requested_duration_sec": duration_sec,
        "non_authoritative": True,
        "device_actions": False,
        "opens_candidate_acm": False,
        "contains_private_usb_identifiers": True,
        "public_raw_export_forbidden": True,
        "sources": {name: list(command) for name, command in source_commands.items()},
    }
    start_receipt = write_exclusive(
        destination / "start.json", canonical_json(start_value)
    )
    start_snapshot_receipt = write_exclusive(
        destination / "lsusb-start.json",
        canonical_json(bounded_snapshot(snapshot_command)),
    )

    captures = [
        SourceCapture(name, command, destination / f"{name}.log")
        for name, command in source_commands.items()
    ]
    stop = StopRequest()
    previous_handlers: dict[int, Any] = {}
    if install_signal_handlers:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous_handlers[signum] = signal.signal(signum, stop.handler)
    try:
        for source in captures:
            source.start()
        deadline = started + duration_sec
        while time.monotonic() < deadline and not stop.event.wait(0.2):
            pass
        stop_reason = (
            f"signal:{stop.signal_name}"
            if stop.signal_name is not None
            else "duration-expired"
        )
    finally:
        for source in reversed(captures):
            source.stop()
        if install_signal_handlers:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)

    end_snapshot_receipt = write_exclusive(
        destination / "lsusb-end.json",
        canonical_json(bounded_snapshot(snapshot_command)),
    )
    ended_utc = utc_now()
    result = {
        "schema": SCHEMA,
        "phase": "complete",
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "elapsed_sec": round(time.monotonic() - started, 6),
        "requested_duration_sec": duration_sec,
        "stop_reason": stop_reason,
        "non_authoritative": True,
        "device_actions": False,
        "opens_candidate_acm": False,
        "contains_private_usb_identifiers": True,
        "public_raw_export_forbidden": True,
        "supporting": {
            "start": start_receipt,
            "lsusb_start": start_snapshot_receipt,
            "lsusb_end": end_snapshot_receipt,
        },
        "sources": {source.name: source.receipt() for source in captures},
    }
    write_exclusive(destination / "result.json", canonical_json(result))
    return result


def bounded_duration(value: str) -> int:
    try:
        duration = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("duration must be an integer") from exc
    if duration < 60 or duration > MAX_DURATION_SEC:
        raise argparse.ArgumentTypeError(
            f"duration must be between 60 and {MAX_DURATION_SEC} seconds"
        )
    return duration


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new capture directory below workspace/private",
    )
    parser.add_argument(
        "--duration-sec",
        type=bounded_duration,
        default=DEFAULT_DURATION_SEC,
        metavar="SECONDS",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "status": "starting",
                "output_dir": str(args.output_dir.absolute()),
                "requested_duration_sec": args.duration_sec,
                "non_authoritative": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    result = capture(
        args.output_dir,
        duration_sec=args.duration_sec,
        private_root=repo_private_root(),
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "output_dir": str(args.output_dir.resolve()),
                "stop_reason": result["stop_reason"],
                "elapsed_sec": result["elapsed_sec"],
                "non_authoritative": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, SidecarError, ValueError) as exc:
        print(f"device-action USB trace sidecar error: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
