#!/usr/bin/env python3
"""Host-side DOOM input dashboard for the V3033 visible loop candidate.

The dashboard keeps the existing serial doompad path:
`a90ctl.py doompad key <role> <0|1>`. It adds live visibility for host
keyboard input, serial command results, DOOM loop lifetime, and device status.
It does not use OTG, evdev, uinput, or host USB HID injection.
"""

from __future__ import annotations

import argparse
import curses
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

import a90ctl
import host_doompad_keyboard_v3033 as keyboard


EXPECTED_WAD_SHA256 = keyboard.EXPECTED_WAD_SHA256
DEFAULT_LOOP_FRAMES = keyboard.DEFAULT_LOOP_FRAMES
DEFAULT_LOOP_FRAME_MS = 50
DEFAULT_HOLD_MS = 250
DEFAULT_POLL_MS = 30
DEFAULT_STATUS_INTERVAL_SEC = 1.0
DEFAULT_DEVICE_TIMEOUT_SEC = 3.0
MAX_LOG_LINES = 200
KEY_VALUE_RE = re.compile(r"^([A-Za-z0-9_. -]+?)=(.*)$")

CURSES_KEY_TOKENS: dict[int, str] = {
    curses.KEY_UP: "\x1b[A",
    curses.KEY_DOWN: "\x1b[B",
    curses.KEY_LEFT: "\x1b[D",
    curses.KEY_RIGHT: "\x1b[C",
}


@dataclass
class DashboardLogEntry:
    timestamp: float
    channel: str
    message: str
    ok: bool = True

    def render(self, now: float) -> str:
        age = max(0.0, now - self.timestamp)
        mark = "ok" if self.ok else "!!"
        return f"{age:5.1f}s {self.channel:<7} {mark} {self.message}"


@dataclass
class DashboardState:
    logs: deque[DashboardLogEntry] = field(default_factory=lambda: deque(maxlen=MAX_LOG_LINES))
    status_lines: list[str] = field(default_factory=list)
    doom_lines: list[str] = field(default_factory=list)
    doompad_lines: list[str] = field(default_factory=list)
    loop_lines: list[str] = field(default_factory=list)
    status_kv: dict[str, str] = field(default_factory=dict)
    doom_kv: dict[str, str] = field(default_factory=dict)
    doompad_kv: dict[str, str] = field(default_factory=dict)
    loop_kv: dict[str, str] = field(default_factory=dict)
    started_at: float = field(default_factory=time.monotonic)
    loop_started_at: float | None = None
    loop_frames: int = DEFAULT_LOOP_FRAMES
    loop_frame_ms: int = DEFAULT_LOOP_FRAME_MS
    loop_generation: int = 0
    loop_active: bool | None = None
    auto_restart: bool = True
    key_events: int = 0
    command_count: int = 0
    command_failures: int = 0
    last_key: str = "-"
    last_command: str = "-"
    last_rc: int | None = None
    last_status: str = "-"

    def add_log(self, channel: str, message: str, *, ok: bool = True) -> None:
        self.logs.append(DashboardLogEntry(time.monotonic(), channel, message, ok))


class DashboardCommandSender:
    def __init__(self,
                 state: DashboardState,
                 host: str,
                 port: int,
                 timeout: float,
                 *,
                 print_only: bool = False) -> None:
        self.state = state
        self.host = host
        self.port = port
        self.timeout = timeout
        self.print_only = print_only
        self.sent: list[list[str]] = []

    def send(self, command: list[str]) -> int:
        result = self.send_result(command)
        return result.rc if result is not None else 1

    def send_result(self, command: list[str]) -> a90ctl.ProtocolResult | None:
        command_text = " ".join(command)
        self.sent.append(list(command))
        self.state.command_count += 1
        self.state.last_command = command_text
        if self.print_only:
            self.state.last_rc = 0
            self.state.last_status = "print-only"
            self.state.add_log("send", command_text)
            return a90ctl.ProtocolResult(
                begin={},
                end={"rc": "0", "status": "print-only"},
                text="",
            )
        try:
            result = a90ctl.run_cmdv1_command(
                self.host,
                self.port,
                self.timeout,
                command,
                retry_unsafe=True,
            )
        except Exception as exc:  # pragma: no cover - exercised only against live serial bridge.
            self.state.command_failures += 1
            self.state.last_rc = 1
            self.state.last_status = "exception"
            self.state.add_log("send", f"{command_text} -> {exc}", ok=False)
            return None

        ok = result.rc == 0
        if not ok:
            self.state.command_failures += 1
        self.state.last_rc = result.rc
        self.state.last_status = result.status
        self.state.add_log("send", f"{command_text} -> rc={result.rc} status={result.status}", ok=ok)
        return result


def parse_key_value_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        match = KEY_VALUE_RE.match(line)
        if match is None:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key:
            values[key] = value
    return values


def interesting_lines(text: str, prefixes: Iterable[str]) -> list[str]:
    result: list[str] = []
    prefix_tuple = tuple(prefixes)
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix_tuple):
            result.append(line)
    return result


def token_for_curses_key(code: int) -> str | None:
    if code < 0:
        return None
    token = CURSES_KEY_TOKENS.get(code)
    if token is not None:
        return token
    if 0 <= code <= 255:
        return chr(code)
    return None


def token_label(token: str) -> str:
    if token == " ":
        return "Space"
    if token == "\r" or token == "\n":
        return "Enter"
    if token == "\x1b":
        return "Esc"
    if token == "\x03":
        return "Ctrl-C"
    if token == "\x1b[A":
        return "Up"
    if token == "\x1b[B":
        return "Down"
    if token == "\x1b[C":
        return "Right"
    if token == "\x1b[D":
        return "Left"
    if token.isprintable():
        return token
    return repr(token)


def estimated_loop_frame(state: DashboardState, now: float | None = None) -> int:
    if state.loop_started_at is None or state.loop_frame_ms <= 0:
        return 0
    timestamp = time.monotonic() if now is None else now
    elapsed_ms = max(0.0, (timestamp - state.loop_started_at) * 1000.0)
    frame = int(elapsed_ms / float(state.loop_frame_ms))
    if state.loop_frames > 0:
        frame %= state.loop_frames
    return frame


def target_fps(loop_frame_ms: int) -> float:
    if loop_frame_ms <= 0:
        return 0.0
    return 1000.0 / float(loop_frame_ms)


def start_loop(sender: DashboardCommandSender, state: DashboardState, sha256: str) -> int:
    result = sender.send_result(keyboard.loop_start_command(state.loop_frames, sha256))
    if result is None:
        return 1
    if result.rc == 0:
        state.loop_generation += 1
        state.loop_started_at = time.monotonic()
        state.loop_active = True
    elif "status=busy" in result.text or result.status == "busy":
        state.loop_active = True
    return result.rc


def stop_loop(sender: DashboardCommandSender, state: DashboardState) -> int:
    result = sender.send_result(["video", "demo", "doom", "loop-stop"])
    state.loop_active = False
    state.loop_started_at = None
    return result.rc if result is not None else 1


def refresh_device_state(sender: DashboardCommandSender, state: DashboardState) -> None:
    status = sender.send_result(["status"])
    if status is not None:
        state.status_lines = interesting_lines(
            status.text,
            ("init:", "selftest:", "uptime:", "battery:", "power:", "thermal:",
             "memory:", "display:", "runtime:", "transport.bridge_endpoint=",
             "storage: backend="),
        )
        state.status_kv = parse_key_value_lines(status.text)

    doom = sender.send_result(["video", "demo", "doom", "status"])
    if doom is not None:
        state.doom_kv = parse_key_value_lines(doom.text)
        state.doom_lines = interesting_lines(
            doom.text,
            ("video.demo.engine.", "video.demo.asset.wad.", "video.demo.doom.",
             "video.demo.input.", "video.demo.sound."),
        )
        frame_ms = state.doom_kv.get("video.demo.doom.loop.frame_ms")
        if frame_ms is not None and frame_ms.isdigit():
            state.loop_frame_ms = int(frame_ms)

    loop = sender.send_result(["video", "demo", "doom", "loop-status"])
    if loop is not None:
        state.loop_kv = parse_key_value_lines(loop.text)
        state.loop_lines = interesting_lines(loop.text, ("video.demo.doom.loop_status.",))
        active = state.loop_kv.get("video.demo.doom.loop_status.active")
        if active in {"0", "1"}:
            state.loop_active = active == "1"
            if active == "0":
                state.loop_started_at = None

    pad = sender.send_result(["doompad", "status"])
    if pad is not None:
        state.doompad_kv = parse_key_value_lines(pad.text)
        state.doompad_lines = interesting_lines(pad.text, ("doompad.",))


def maybe_auto_restart_loop(sender: DashboardCommandSender, state: DashboardState, sha256: str) -> None:
    if not state.auto_restart:
        return
    if state.loop_active is False:
        state.add_log("loop", "auto restart after inactive loop")
        start_loop(sender, state, sha256)
        return
    if state.loop_started_at is None or state.loop_frames <= 0 or state.loop_frame_ms <= 0:
        return
    duration = (state.loop_frames * state.loop_frame_ms) / 1000.0
    if time.monotonic() - state.loop_started_at > duration + 0.5:
        state.add_log("loop", "loop lifetime elapsed; checking status")
        result = sender.send_result(["video", "demo", "doom", "loop-status"])
        if result is not None:
            state.loop_kv = parse_key_value_lines(result.text)
            active = state.loop_kv.get("video.demo.doom.loop_status.active")
            if active == "0":
                state.loop_active = False
                state.loop_started_at = None
                start_loop(sender, state, sha256)


def addstr_clipped(window: curses.window, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
    if width <= 0:
        return
    try:
        window.addnstr(y, x, text.ljust(width), width, attr)
    except curses.error:
        pass


def draw_box(window: curses.window, y: int, x: int, height: int, width: int, title: str) -> None:
    if height <= 1 or width <= 2:
        return
    try:
        window.addstr(y, x, "+" + "-" * (width - 2) + "+")
        for row in range(y + 1, y + height - 1):
            window.addstr(row, x, "|")
            window.addstr(row, x + width - 1, "|")
        window.addstr(y + height - 1, x, "+" + "-" * (width - 2) + "+")
        addstr_clipped(window, y, x + 2, f" {title} ", max(0, width - 4), curses.A_BOLD)
    except curses.error:
        pass


def draw_lines(window: curses.window,
               y: int,
               x: int,
               height: int,
               width: int,
               lines: Iterable[str],
               attr: int = 0) -> None:
    for offset, line in enumerate(lines):
        if offset >= height:
            break
        addstr_clipped(window, y + offset, x, line, width, attr)


def draw_dashboard(stdscr: curses.window,
                   state: DashboardState,
                   session: keyboard.DoompadKeyboardSession) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    now = time.monotonic()
    min_height = 22
    min_width = 72
    if max_y < min_height or max_x < min_width:
        addstr_clipped(stdscr, 0, 0, f"terminal too small: need {min_width}x{min_height}", max_x)
        stdscr.refresh()
        return

    top_h = 8
    bottom_h = max(7, min(12, max_y // 3))
    mid_h = max_y - top_h - bottom_h
    left_w = max_x // 2
    right_w = max_x - left_w

    draw_box(stdscr, 0, 0, top_h, max_x, "DOOM DISPLAY / LOOP")
    active_roles = ",".join(sorted(session.active_until.keys())) or "-"
    loop_elapsed = 0.0 if state.loop_started_at is None else max(0.0, now - state.loop_started_at)
    loop_state = "unknown" if state.loop_active is None else ("active" if state.loop_active else "inactive")
    frame = estimated_loop_frame(state, now)
    top_lines = [
        f"loop={loop_state} gen={state.loop_generation} frame_est={frame}/{state.loop_frames} "
        f"elapsed={loop_elapsed:0.1f}s target_fps={target_fps(state.loop_frame_ms):0.1f} "
        f"auto_restart={'on' if state.auto_restart else 'off'}",
        f"wad={state.doom_kv.get('video.demo.asset.wad.present', '?')} "
        f"bytes={state.doom_kv.get('video.demo.asset.wad.bytes', '?')} "
        f"helper={state.doom_kv.get('video.demo.engine.helper.executable', '?')} "
        f"frame={state.doom_kv.get('video.demo.doom.frame.width', '?')}x"
        f"{state.doom_kv.get('video.demo.doom.frame.height', '?')}",
        f"input_active_roles={active_roles} doompad={state.doompad_kv.get('doompad.state seq', '-')}",
        f"last_key={state.last_key} commands={state.command_count} failures={state.command_failures} "
        f"last_rc={state.last_rc} last_status={state.last_status}",
        "keys: WASD/arrows move  Space/F fire  Enter/E use  R run  Esc/M menu  L restart  P auto  X stop  Q quit",
    ]
    draw_lines(stdscr, 2, 2, top_h - 3, max_x - 4, top_lines)

    draw_box(stdscr, top_h, 0, mid_h, left_w, "SYSTEM / DOOM INFO")
    system_lines = list(state.status_lines[:8])
    system_lines.extend(state.loop_lines[:3])
    system_lines.extend(state.doom_lines[:max(0, mid_h - 4 - len(system_lines))])
    draw_lines(stdscr, top_h + 2, 2, mid_h - 3, left_w - 4, system_lines)

    draw_box(stdscr, top_h, left_w, mid_h, right_w, "DEVICE OUTPUT")
    device_lines = []
    device_lines.extend(state.doompad_lines[-4:])
    device_lines.extend(state.doom_lines[-8:])
    device_lines.extend(state.status_lines[-5:])
    draw_lines(stdscr, top_h + 2, left_w + 2, mid_h - 3, right_w - 4, device_lines)

    draw_box(stdscr, max_y - bottom_h, 0, bottom_h, max_x, "KEYBOARD / SERIAL INPUT LOG")
    log_lines = [entry.render(now) for entry in list(state.logs)[-(bottom_h - 3):]]
    draw_lines(stdscr, max_y - bottom_h + 2, 2, bottom_h - 3, max_x - 4, log_lines)
    stdscr.refresh()


def render_snapshot_lines(state: DashboardState) -> list[str]:
    now = time.monotonic()
    loop_elapsed = 0.0 if state.loop_started_at is None else max(0.0, now - state.loop_started_at)
    loop_state = "unknown" if state.loop_active is None else ("active" if state.loop_active else "inactive")
    lines = [
        "A90 DOOMPAD DASHBOARD SNAPSHOT",
        f"loop={loop_state} frame_est={estimated_loop_frame(state, now)}/{state.loop_frames} "
        f"elapsed={loop_elapsed:0.1f}s target_fps={target_fps(state.loop_frame_ms):0.1f} "
        f"auto_restart={'on' if state.auto_restart else 'off'}",
        f"commands={state.command_count} failures={state.command_failures} "
        f"last_rc={state.last_rc} last_status={state.last_status}",
    ]
    lines.extend(state.status_lines[:8])
    lines.extend(state.loop_lines[:4])
    lines.extend(state.doompad_lines[:4])
    lines.extend(state.doom_lines[:8])
    return lines


def run_once(args: argparse.Namespace) -> int:
    state = DashboardState(
        loop_frames=args.loop_frames,
        loop_frame_ms=args.loop_frame_ms,
        auto_restart=not args.no_auto_restart,
    )
    sender = DashboardCommandSender(
        state,
        args.host,
        args.port,
        args.timeout,
        print_only=args.print_only,
    )
    if not args.no_loop_start:
        start_loop(sender, state, args.sha256)
    refresh_device_state(sender, state)
    for line in render_snapshot_lines(state):
        print(line)
    if not args.no_loop_stop:
        stop_loop(sender, state)
    return 0 if state.command_failures == 0 else 1


def handle_dashboard_token(token: str,
                           sender: DashboardCommandSender,
                           state: DashboardState,
                           session: keyboard.DoompadKeyboardSession,
                           sha256: str) -> bool:
    label = token_label(token)
    state.last_key = label
    state.key_events += 1

    if token in keyboard.EXIT_TOKENS:
        state.add_log("key", f"{label} quit")
        return False
    if token in {"p", "P"}:
        state.auto_restart = not state.auto_restart
        state.add_log("key", f"{label} auto_restart={'on' if state.auto_restart else 'off'}")
        return True
    if token in {"l", "L"}:
        state.add_log("key", f"{label} manual loop restart")
        stop_loop(sender, state)
        start_loop(sender, state, sha256)
        return True
    if token in {"x", "X"}:
        state.add_log("key", f"{label} stop loop and reset doompad")
        stop_loop(sender, state)
        sender.send(["doompad", "reset"])
        return True

    role = keyboard.role_for_key_token(token)
    if role is None:
        state.add_log("key", f"{label} unmapped", ok=False)
        return True
    state.add_log("key", f"{label} -> {role}")
    session.press(role)
    return True


def run_curses(stdscr: curses.window, args: argparse.Namespace) -> int:
    state = DashboardState(
        loop_frames=args.loop_frames,
        loop_frame_ms=args.loop_frame_ms,
        auto_restart=not args.no_auto_restart,
    )
    sender = DashboardCommandSender(
        state,
        args.host,
        args.port,
        args.timeout,
        print_only=args.print_only,
    )
    session = keyboard.DoompadKeyboardSession(sender, args.hold_ms)
    poll_sec = max(args.poll_ms, 1) / 1000.0
    last_refresh = 0.0

    stdscr.nodelay(True)
    stdscr.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    if not args.no_loop_start:
        start_loop(sender, state, args.sha256)
    refresh_device_state(sender, state)

    try:
        while True:
            now = time.monotonic()
            code = stdscr.getch()
            if code != -1:
                token = token_for_curses_key(code)
                if token is not None and not handle_dashboard_token(token, sender, state, session, args.sha256):
                    break

            session.release_expired()
            maybe_auto_restart_loop(sender, state, args.sha256)
            if now - last_refresh >= args.status_interval:
                refresh_device_state(sender, state)
                last_refresh = time.monotonic()
            draw_dashboard(stdscr, state, session)
            time.sleep(poll_sec)
    finally:
        session.release_all()
        if not args.no_loop_stop:
            stop_loop(sender, state)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_DEVICE_TIMEOUT_SEC)
    parser.add_argument("--hold-ms", type=int, default=DEFAULT_HOLD_MS)
    parser.add_argument("--poll-ms", type=int, default=DEFAULT_POLL_MS)
    parser.add_argument("--loop-frames", type=int, default=DEFAULT_LOOP_FRAMES)
    parser.add_argument("--loop-frame-ms", type=int, default=DEFAULT_LOOP_FRAME_MS)
    parser.add_argument("--status-interval", type=float, default=DEFAULT_STATUS_INTERVAL_SEC)
    parser.add_argument("--sha256", default=EXPECTED_WAD_SHA256)
    parser.add_argument("--no-loop-start", action="store_true")
    parser.add_argument("--no-loop-stop", action="store_true")
    parser.add_argument("--no-auto-restart", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument("--once", action="store_true", help="print one non-curses snapshot and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.loop_frames <= 0:
        print("--loop-frames must be positive", file=sys.stderr)
        return 2
    if args.loop_frame_ms <= 0:
        print("--loop-frame-ms must be positive", file=sys.stderr)
        return 2
    if args.once:
        return run_once(args)
    return curses.wrapper(run_curses, args)


if __name__ == "__main__":
    raise SystemExit(main())
