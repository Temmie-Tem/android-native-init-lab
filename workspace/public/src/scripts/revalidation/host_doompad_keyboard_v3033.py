#!/usr/bin/env python3
"""Drive the A90 serial doompad from a host terminal keyboard.

The default TTY backend uses the existing serial doompad command path with a
short auto-release fallback. The optional evdev backend reads real host key
down/up events and still sends only serial doompad state packets; it does not
use OTG, uinput, or host USB HID injection.
"""

from __future__ import annotations

import argparse
import glob
import os
import select
import struct
import sys
import termios
import time
import tty
from dataclasses import dataclass, field
from typing import Iterable

import a90ctl


EXPECTED_WAD_SHA256 = "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
DEFAULT_HOLD_MS = 110
DEFAULT_POLL_MS = 10
DEFAULT_LOOP_FRAMES = 0
DEFAULT_LOOP_FRAME_MS = 33
DEFAULT_LOOP_RESTART_GRACE_MS = 500
DEFAULT_CONTINUOUS_CHECK_MS = 5000
EVDEV_EVENT_FORMAT = "llHHI"
EVDEV_EVENT_SIZE = struct.calcsize(EVDEV_EVENT_FORMAT)
EV_KEY = 0x01
EVDEV_KEY_UP = 0
EVDEV_KEY_DOWN = 1
EVDEV_KEY_REPEAT = 2
ALL_ROLES = ("forward", "back", "left", "right", "fire", "use", "menu", "run")
ROLE_BITS = {role: 1 << index for index, role in enumerate(ALL_ROLES)}
LOOP_STATUS_COMMAND = ["video", "demo", "doom", "loop-status"]
LOOP_STATUS_ACTIVE_KEY = "video.demo.doom.loop_status.active"
LOOP_STATUS_CONTINUOUS_KEY = "video.demo.doom.loop_status.continuous"

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

LINUX_KEY_CODE_TO_ROLE = {
    17: "forward",  # KEY_W
    103: "forward",  # KEY_UP
    31: "back",  # KEY_S
    108: "back",  # KEY_DOWN
    30: "left",  # KEY_A
    105: "left",  # KEY_LEFT
    32: "right",  # KEY_D
    106: "right",  # KEY_RIGHT
    57: "fire",  # KEY_SPACE
    33: "fire",  # KEY_F
    28: "use",  # KEY_ENTER
    96: "use",  # KEY_KPENTER
    18: "use",  # KEY_E
    1: "menu",  # KEY_ESC
    50: "menu",  # KEY_M
    19: "run",  # KEY_R
    42: "run",  # KEY_LEFTSHIFT
    54: "run",  # KEY_RIGHTSHIFT
}

LINUX_KEY_CODE_LABELS = {
    1: "Esc",
    17: "W",
    18: "E",
    19: "R",
    28: "Enter",
    30: "A",
    31: "S",
    32: "D",
    33: "F",
    42: "LeftShift",
    50: "M",
    54: "RightShift",
    57: "Space",
    96: "KpEnter",
    103: "Up",
    105: "Left",
    106: "Right",
    108: "Down",
}


@dataclass(frozen=True)
class EvdevKeyboardDevice:
    path: str
    name: str
    handlers: tuple[str, ...]

    @property
    def is_keyboard(self) -> bool:
        return "kbd" in self.handlers


def role_for_key_token(token: str) -> str | None:
    return KEY_TOKEN_TO_ROLE.get(token)


def decode_key_token(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def parse_proc_bus_input_devices(text: str) -> list[EvdevKeyboardDevice]:
    devices: list[EvdevKeyboardDevice] = []
    name = "unknown"
    handlers: tuple[str, ...] = ()

    def flush() -> None:
        for handler in handlers:
            if handler.startswith("event"):
                devices.append(
                    EvdevKeyboardDevice(
                        path=f"/dev/input/{handler}",
                        name=name,
                        handlers=handlers,
                    )
                )

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            name = "unknown"
            handlers = ()
            continue
        if line.startswith("N: Name="):
            name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("H: Handlers="):
            handlers = tuple(line.split("=", 1)[1].split())
    flush()
    return devices


def discover_evdev_keyboard_devices(proc_path: str = "/proc/bus/input/devices") -> list[EvdevKeyboardDevice]:
    try:
        with open(proc_path, "r", encoding="utf-8", errors="replace") as handle:
            devices = parse_proc_bus_input_devices(handle.read())
    except OSError:
        devices = []
    keyboard_devices = [device for device in devices if device.is_keyboard and os.path.exists(device.path)]
    if keyboard_devices:
        return keyboard_devices
    return [
        EvdevKeyboardDevice(path=path, name="unknown", handlers=())
        for path in sorted(glob.glob("/dev/input/event*"))
    ]


def format_evdev_device(device: EvdevKeyboardDevice) -> str:
    keyboard = " keyboard" if device.is_keyboard else ""
    return f"{device.path}{keyboard} {device.name}".strip()


def open_evdev_devices(paths: Iterable[str]) -> dict[int, str]:
    fds: dict[int, str] = {}
    try:
        for path in paths:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            fds[fd] = path
    except OSError:
        for fd in fds:
            os.close(fd)
        raise
    return fds


def read_evdev_events(fd: int) -> list[tuple[int, int, int]]:
    events: list[tuple[int, int, int]] = []
    try:
        data = os.read(fd, EVDEV_EVENT_SIZE * 32)
    except BlockingIOError:
        return events
    except InterruptedError:
        return events
    for offset in range(0, len(data) - EVDEV_EVENT_SIZE + 1, EVDEV_EVENT_SIZE):
        _, _, event_type, code, value = struct.unpack(
            EVDEV_EVENT_FORMAT,
            data[offset:offset + EVDEV_EVENT_SIZE],
        )
        events.append((event_type, code, value))
    return events


def role_for_evdev_event(event_type: int, code: int, value: int) -> tuple[str, bool] | None:
    if event_type != EV_KEY or value not in {EVDEV_KEY_UP, EVDEV_KEY_DOWN, EVDEV_KEY_REPEAT}:
        return None
    role = LINUX_KEY_CODE_TO_ROLE.get(code)
    if role is None:
        return None
    if value == EVDEV_KEY_REPEAT:
        return None
    return role, value == EVDEV_KEY_DOWN


def evdev_key_label(code: int) -> str:
    return LINUX_KEY_CODE_LABELS.get(code, f"KEY_{code}")


def doompad_command(role: str, down: bool) -> list[str]:
    if role not in ALL_ROLES:
        raise ValueError(f"unknown doompad role: {role}")
    return ["doompad", "key", role, "1" if down else "0"]


def doompad_mask_for_roles(roles: Iterable[str]) -> int:
    mask = 0
    for role in roles:
        bit = ROLE_BITS.get(role)
        if bit is None:
            raise ValueError(f"unknown doompad role: {role}")
        mask |= bit
    return mask


def doompad_state_command(seq: int, mask: int) -> list[str]:
    if seq < 0:
        raise ValueError("doompad seq must be non-negative")
    if mask < 0 or mask > 0xff:
        raise ValueError("doompad mask must be between 0x00 and 0xff")
    return ["doompad", "state", str(seq), f"0x{mask:02x}"]


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


def is_doompad_state_command(command: list[str]) -> bool:
    return len(command) == 4 and command[0] == "doompad" and command[1] == "state"


def is_doompad_input_command(command: list[str]) -> bool:
    return is_doompad_key_command(command) or is_doompad_state_command(command)


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
        use_fast_path = fast or is_doompad_input_command(command)
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
    continuous_check_ms: int = DEFAULT_CONTINUOUS_CHECK_MS
    enabled: bool = True
    loop_started_at: float | None = None
    next_check_at: float = 0.0

    def expected_duration_sec(self) -> float:
        if self.loop_frames <= 0 or self.frame_ms <= 0:
            return 0.0
        return (self.loop_frames * self.frame_ms) / 1000.0

    def restart_grace_sec(self) -> float:
        return max(0, self.restart_grace_ms) / 1000.0

    def continuous_check_sec(self) -> float:
        return max(1, self.continuous_check_ms) / 1000.0

    def check_delay_sec(self) -> float:
        if self.loop_frames == 0:
            return self.continuous_check_sec()
        return self.expected_duration_sec() + self.restart_grace_sec()

    def mark_started(self, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        self.loop_started_at = timestamp
        self.next_check_at = timestamp + self.check_delay_sec()

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
        continuous = values.get(LOOP_STATUS_CONTINUOUS_KEY) == "1" or self.loop_frames == 0
        if active == "0":
            self.loop_started_at = None
            return self.start(timestamp)
        if active == "1":
            self.next_check_at = timestamp + (self.continuous_check_sec() if continuous else 0.5)
        else:
            self.next_check_at = timestamp + 1.0
        return 0


class DoompadKeyboardSession:
    def __init__(self, sender: CommandSender, hold_ms: int, *, use_state_batch: bool = True) -> None:
        self.sender = sender
        self.hold_sec = hold_ms / 1000.0
        self.use_state_batch = use_state_batch
        self.active_until: dict[str, float] = {}
        self.state_seq = 0

    def active_mask(self) -> int:
        return doompad_mask_for_roles(self.active_until.keys())

    def send_state(self) -> None:
        self.state_seq += 1
        self.sender.send(doompad_state_command(self.state_seq, self.active_mask()))

    def set_role(self, role: str, down: bool) -> bool:
        if role not in ALL_ROLES:
            raise ValueError(f"unknown doompad role: {role}")
        active = role in self.active_until
        if active == down:
            return False
        if down:
            self.active_until[role] = float("inf")
        else:
            self.active_until.pop(role, None)
        if self.use_state_batch:
            self.send_state()
        else:
            self.sender.send(doompad_command(role, down))
        return True

    def press(self, role: str, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        if role not in self.active_until:
            self.active_until[role] = timestamp + self.hold_sec
            if self.use_state_batch:
                self.send_state()
            else:
                self.sender.send(doompad_command(role, True))
            return
        self.active_until[role] = timestamp + self.hold_sec

    def release_expired(self, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        expired = [role for role, deadline in self.active_until.items() if deadline <= timestamp]
        for role in expired:
            self.active_until.pop(role, None)
        if expired:
            if self.use_state_batch:
                self.send_state()
            else:
                for role in expired:
                    self.sender.send(doompad_command(role, False))

    def release_all(self, roles: Iterable[str] = ALL_ROLES) -> None:
        for role in roles:
            if role in self.active_until:
                self.active_until.pop(role, None)
            if not self.use_state_batch:
                self.sender.send(doompad_command(role, False))
        if self.use_state_batch:
            self.send_state()

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


def run_tty_loop(args: argparse.Namespace,
                 sender: CommandSender,
                 session: DoompadKeyboardSession,
                 loop_keeper: DoomLoopKeeper,
                 poll_sec: float) -> int:
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


def resolve_evdev_paths(args: argparse.Namespace) -> list[str]:
    if args.evdev_device:
        return list(args.evdev_device)
    return [device.path for device in discover_evdev_keyboard_devices()]


def run_evdev_loop(args: argparse.Namespace,
                   sender: CommandSender,
                   session: DoompadKeyboardSession,
                   loop_keeper: DoomLoopKeeper,
                   poll_sec: float) -> int:
    paths = resolve_evdev_paths(args)
    if not paths:
        print("no evdev keyboard devices found; pass --evdev-device /dev/input/eventX", file=sys.stderr)
        return 2

    if not args.no_loop_start:
        rc = loop_keeper.start()
        if rc != 0:
            return rc

    fds: dict[int, str] = {}
    try:
        fds = open_evdev_devices(paths)
    except OSError as exc:
        print(f"failed to open evdev input device: {exc}", file=sys.stderr)
        session.release_all()
        if not args.no_loop_stop:
            sender.send(["video", "demo", "doom", "loop-stop"])
        return 2

    try:
        print("evdev input active:", ", ".join(fds.values()), file=sys.stderr)
        print("press Ctrl-C to quit; key-up events release buttons immediately", file=sys.stderr)
        while True:
            readable, _, _ = select.select(list(fds.keys()), [], [], poll_sec)
            for fd in readable:
                for event_type, code, value in read_evdev_events(fd):
                    event = role_for_evdev_event(event_type, code, value)
                    if event is None:
                        continue
                    role, down = event
                    changed = session.set_role(role, down)
                    if changed and not args.quiet:
                        direction = "down" if down else "up"
                        print(f"{evdev_key_label(code)} {direction} -> {role}", file=sys.stderr)
            if not session.active_until:
                loop_keeper.maybe_restart()
    except KeyboardInterrupt:
        return 0
    finally:
        session.release_all()
        for fd in fds:
            os.close(fd)
        if not args.no_loop_stop:
            sender.send(["video", "demo", "doom", "loop-stop"])
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--input-backend", choices=("tty", "evdev"), default="tty")
    parser.add_argument("--evdev-device", action="append", help="host /dev/input/eventX to read; may be repeated")
    parser.add_argument("--list-evdev-devices", action="store_true")
    parser.add_argument("--hold-ms", type=int, default=DEFAULT_HOLD_MS)
    parser.add_argument("--poll-ms", type=int, default=DEFAULT_POLL_MS)
    parser.add_argument("--loop-frames", type=int, default=DEFAULT_LOOP_FRAMES)
    parser.add_argument("--loop-frame-ms", type=int, default=DEFAULT_LOOP_FRAME_MS)
    parser.add_argument("--loop-restart-grace-ms", type=int, default=DEFAULT_LOOP_RESTART_GRACE_MS)
    parser.add_argument("--continuous-check-ms", type=int, default=DEFAULT_CONTINUOUS_CHECK_MS)
    parser.add_argument("--sha256", default=EXPECTED_WAD_SHA256)
    parser.add_argument("--no-loop-start", action="store_true")
    parser.add_argument("--no-loop-stop", action="store_true")
    parser.add_argument("--no-auto-restart", action="store_true")
    parser.add_argument("--legacy-key-events", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_evdev_devices:
        for device in discover_evdev_keyboard_devices():
            print(format_evdev_device(device))
        return 0
    sender = CommandSender(args.host, args.port, args.timeout, print_only=args.print_only)
    session = DoompadKeyboardSession(sender, args.hold_ms, use_state_batch=not args.legacy_key_events)
    loop_keeper = DoomLoopKeeper(
        sender,
        args.loop_frames,
        args.loop_frame_ms,
        args.sha256,
        args.loop_restart_grace_ms,
        continuous_check_ms=args.continuous_check_ms,
        enabled=not args.no_auto_restart and not args.no_loop_start,
    )
    poll_sec = max(args.poll_ms, 1) / 1000.0

    if args.input_backend == "evdev":
        return run_evdev_loop(args, sender, session, loop_keeper, poll_sec)
    return run_tty_loop(args, sender, session, loop_keeper, poll_sec)


if __name__ == "__main__":
    raise SystemExit(main())
