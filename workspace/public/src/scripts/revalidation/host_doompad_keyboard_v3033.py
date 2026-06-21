#!/usr/bin/env python3
"""Drive the A90 serial doompad from a host terminal keyboard.

This intentionally uses the existing `a90ctl.py doompad key <role> <0|1>`
command path. It does not use OTG, evdev, uinput, or host USB HID injection.
"""

from __future__ import annotations

import argparse
import os
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass, field
from typing import Iterable

import a90ctl


EXPECTED_WAD_SHA256 = "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
DEFAULT_HOLD_MS = 180
DEFAULT_POLL_MS = 30
DEFAULT_LOOP_FRAMES = 300
DEFAULT_LOOP_FRAME_MS = 33
DEFAULT_LOOP_RESTART_GRACE_MS = 500
ALL_ROLES = ("forward", "back", "left", "right", "fire", "use", "menu", "run")
LOOP_STATUS_COMMAND = ["video", "demo", "doom", "loop-status"]
LOOP_STATUS_ACTIVE_KEY = "video.demo.doom.loop_status.active"

KEY_TOKEN_TO_ROLE = {
    "w": "forward",
    "W": "forward",
    "\x1b[A": "forward",
    "s": "back",
    "S": "back",
    "\x1b[B": "back",
    "a": "left",
    "A": "left",
    "\x1b[D": "left",
    "d": "right",
    "D": "right",
    "\x1b[C": "right",
    " ": "fire",
    "f": "fire",
    "F": "fire",
    "\r": "use",
    "\n": "use",
    "e": "use",
    "E": "use",
    "\x1b": "menu",
    "m": "menu",
    "M": "menu",
    "r": "run",
    "R": "run",
}

EXIT_TOKENS = {"q", "Q", "\x03"}


def role_for_key_token(token: str) -> str | None:
    return KEY_TOKEN_TO_ROLE.get(token)


def decode_key_token(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def doompad_command(role: str, down: bool) -> list[str]:
    if role not in ALL_ROLES:
        raise ValueError(f"unknown doompad role: {role}")
    return ["doompad", "key", role, "1" if down else "0"]


def loop_start_command(frames: int, sha256: str) -> list[str]:
    return [
        "video",
        "demo",
        "doom",
        "loop-start",
        str(frames),
        "--wad",
        "runtime-private",
        "--sha256",
        sha256,
    ]


def is_doompad_key_command(command: list[str]) -> bool:
    return len(command) == 4 and command[0] == "doompad" and command[1] == "key"


def parse_key_value_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


@dataclass
class CommandSender:
    host: str
    port: int
    timeout: float
    print_only: bool = False
    sent: list[list[str]] = field(default_factory=list)

    def send_result(self, command: list[str], *, fast: bool = False) -> a90ctl.ProtocolResult:
        self.sent.append(list(command))
        if self.print_only:
            print(" ".join(command))
            return a90ctl.ProtocolResult(
                begin={},
                end={"rc": "0", "status": "print-only"},
                text="",
            )
        use_fast_path = fast or is_doompad_key_command(command)
        result = a90ctl.run_cmdv1_command(
            self.host,
            self.port,
            self.timeout,
            command,
            retry_unsafe=True,
            require_prompt_after_end=not use_fast_path,
            post_marker_drain_sec=0.0 if use_fast_path else 0.15,
        )
        return result

    def send(self, command: list[str]) -> int:
        result = self.send_result(command)
        return result.rc


@dataclass
class DoomLoopKeeper:
    sender: CommandSender
    loop_frames: int
    frame_ms: int
    sha256: str
    restart_grace_ms: int
    enabled: bool = True
    loop_started_at: float | None = None
    next_check_at: float = 0.0

    def expected_duration_sec(self) -> float:
        if self.loop_frames <= 0 or self.frame_ms <= 0:
            return 0.0
        return (self.loop_frames * self.frame_ms) / 1000.0

    def restart_grace_sec(self) -> float:
        return max(0, self.restart_grace_ms) / 1000.0

    def mark_started(self, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        self.loop_started_at = timestamp
        self.next_check_at = timestamp + self.expected_duration_sec() + self.restart_grace_sec()

    def start(self, now: float | None = None) -> int:
        result = self.sender.send_result(loop_start_command(self.loop_frames, self.sha256), fast=True)
        if result.rc == 0:
            self.mark_started(now)
        elif result.status == "busy" or "status=busy" in result.text:
            timestamp = time.monotonic() if now is None else now
            self.next_check_at = timestamp + 0.5
        return result.rc

    def maybe_restart(self, now: float | None = None) -> int:
        if not self.enabled:
            return 0
        timestamp = time.monotonic() if now is None else now
        if self.loop_started_at is None:
            return self.start(timestamp)
        if timestamp < self.next_check_at:
            return 0

        result = self.sender.send_result(list(LOOP_STATUS_COMMAND), fast=True)
        if result.rc != 0:
            self.next_check_at = timestamp + 1.0
            return result.rc

        values = parse_key_value_lines(result.text)
        active = values.get(LOOP_STATUS_ACTIVE_KEY)
        if active == "0":
            self.loop_started_at = None
            return self.start(timestamp)
        if active == "1":
            self.next_check_at = timestamp + 0.5
        else:
            self.next_check_at = timestamp + 1.0
        return 0


class DoompadKeyboardSession:
    def __init__(self, sender: CommandSender, hold_ms: int) -> None:
        self.sender = sender
        self.hold_sec = hold_ms / 1000.0
        self.active_until: dict[str, float] = {}

    def press(self, role: str, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        if role not in self.active_until:
            self.sender.send(doompad_command(role, True))
        self.active_until[role] = timestamp + self.hold_sec

    def release_expired(self, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        expired = [role for role, deadline in self.active_until.items() if deadline <= timestamp]
        for role in expired:
            self.sender.send(doompad_command(role, False))
            self.active_until.pop(role, None)

    def release_all(self, roles: Iterable[str] = ALL_ROLES) -> None:
        for role in roles:
            if role in self.active_until:
                self.active_until.pop(role, None)
            self.sender.send(doompad_command(role, False))

    def handle_token(self, token: str, now: float | None = None) -> bool:
        if token in EXIT_TOKENS:
            return False
        role = role_for_key_token(token)
        if role is not None:
            self.press(role, now=now)
        return True


class RawTerminal:
    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.original: list[int] | None = None

    def __enter__(self) -> "RawTerminal":
        self.original = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self.original is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.original)


def read_key_token(fd: int, poll_sec: float) -> str | None:
    readable, _, _ = select.select([fd], [], [], poll_sec)
    if not readable:
        return None
    data = os.read(fd, 8)
    if not data:
        return None
    return decode_key_token(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--hold-ms", type=int, default=DEFAULT_HOLD_MS)
    parser.add_argument("--poll-ms", type=int, default=DEFAULT_POLL_MS)
    parser.add_argument("--loop-frames", type=int, default=DEFAULT_LOOP_FRAMES)
    parser.add_argument("--loop-frame-ms", type=int, default=DEFAULT_LOOP_FRAME_MS)
    parser.add_argument("--loop-restart-grace-ms", type=int, default=DEFAULT_LOOP_RESTART_GRACE_MS)
    parser.add_argument("--sha256", default=EXPECTED_WAD_SHA256)
    parser.add_argument("--no-loop-start", action="store_true")
    parser.add_argument("--no-loop-stop", action="store_true")
    parser.add_argument("--no-auto-restart", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sender = CommandSender(args.host, args.port, args.timeout, print_only=args.print_only)
    session = DoompadKeyboardSession(sender, args.hold_ms)
    loop_keeper = DoomLoopKeeper(
        sender,
        args.loop_frames,
        args.loop_frame_ms,
        args.sha256,
        args.loop_restart_grace_ms,
        enabled=not args.no_auto_restart and not args.no_loop_start,
    )
    poll_sec = max(args.poll_ms, 1) / 1000.0

    if not args.no_loop_start:
        rc = loop_keeper.start()
        if rc != 0:
            return rc

    try:
        with RawTerminal(sys.stdin.fileno()):
            while True:
                token = read_key_token(sys.stdin.fileno(), poll_sec)
                if token is not None and not session.handle_token(token):
                    break
                session.release_expired()
                if not session.active_until:
                    loop_keeper.maybe_restart()
    finally:
        session.release_all()
        if not args.no_loop_stop:
            sender.send(["video", "demo", "doom", "loop-stop"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
