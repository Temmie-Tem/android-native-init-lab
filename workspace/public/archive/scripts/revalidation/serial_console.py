#!/usr/bin/env python3

import argparse
import errno
import os
import re
import selectors
import signal
import socket
import sys
import termios
import time
from dataclasses import dataclass


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321

KEY_LINE_RE = re.compile(r"key\s+\d+:\s+([A-Z0-9_]+)\s+\((0x[0-9a-fA-F]+)\)")
BLINDMENU_LINE_RE = re.compile(r"blindmenu:\s+\[(\d+)/(\d+)\]\s+(\S+)\s+-\s+(.*)")
BLINDMENU_SELECT_RE = re.compile(r"blindmenu:\s+selected\s+(\S+)")
WAITKEY_LINE_RE = re.compile(r"waitkey:\s+waiting for (\d+) key press")


@dataclass
class TerminalState:
    fd: int | None = None
    attrs: list | None = None


class ConsoleAnnotator:
    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[str]:
        notes: list[str] = []

        self.buffer.extend(data)
        while True:
            newline = self.buffer.find(b"\n")
            if newline < 0:
                if len(self.buffer) > 65536:
                    del self.buffer[:-4096]
                break

            raw_line = bytes(self.buffer[: newline + 1])
            del self.buffer[: newline + 1]

            line = raw_line.decode("utf-8", errors="replace").replace("\r", "").strip()
            if not line:
                continue

            note = self._annotate(line)
            if note is not None:
                notes.append(note)

        return notes

    def _annotate(self, line: str) -> str | None:
        match = KEY_LINE_RE.search(line)
        if match is not None:
            return f"key {match.group(1)} {match.group(2)}"

        match = BLINDMENU_LINE_RE.search(line)
        if match is not None:
            return f"menu {match.group(1)}/{match.group(2)} -> {match.group(3)}"

        match = BLINDMENU_SELECT_RE.search(line)
        if match is not None:
            return f"menu selected {match.group(1)}"

        match = WAITKEY_LINE_RE.search(line)
        if match is not None:
            return f"waitkey armed for {match.group(1)} press(es)"

        return None


class LocalTerminal:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.state = TerminalState()

    def __enter__(self) -> "LocalTerminal":
        if not self.enabled:
            return self

        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            self.enabled = False
            return self

        attrs = termios.tcgetattr(fd)
        raw_attrs = termios.tcgetattr(fd)
        raw_attrs[3] &= ~(termios.ICANON | termios.ECHO)
        raw_attrs[6][termios.VMIN] = 1
        raw_attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, raw_attrs)

        self.state.fd = fd
        self.state.attrs = attrs
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self.enabled or self.state.fd is None or self.state.attrs is None:
            return
        termios.tcsetattr(self.state.fd, termios.TCSANOW, self.state.attrs)


class ConsoleClient:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.selector = selectors.DefaultSelector()
        self.sock: socket.socket | None = None
        self.stdin_fd: int | None = None
        self.stop_requested = False
        self.next_connect_time = 0.0
        self.connected_once = False
        self.annotator = ConsoleAnnotator()

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[console {timestamp}] {message}", file=sys.stderr, flush=True)

    def emit_note(self, message: str) -> None:
        sys.stdout.flush()
        print(f"\r\n[watch] {message}\r\n", end="", file=sys.stderr, flush=True)

    def maybe_connect(self) -> None:
        if self.sock is not None or time.monotonic() < self.next_connect_time:
            return

        try:
            sock = socket.create_connection(
                (self.args.host, self.args.port),
                timeout=self.args.connect_timeout,
            )
        except OSError as exc:
            if self.args.once:
                raise
            self.log(f"bridge not ready at {self.args.host}:{self.args.port}: {exc}")
            self.next_connect_time = time.monotonic() + self.args.retry_interval
            return

        sock.setblocking(False)
        self.sock = sock
        self.selector.register(sock, selectors.EVENT_READ, "socket")
        self.connected_once = True
        self.log(f"connected to bridge {self.args.host}:{self.args.port}")
        if self.args.watch_only:
            self.emit_note("watch-only mode; local keystrokes stay on the host")
        else:
            self.emit_note("connected; press Ctrl-] to quit locally")

    def close_socket(self) -> None:
        if self.sock is None:
            return

        try:
            self.selector.unregister(self.sock)
        except Exception:
            pass

        try:
            self.sock.close()
        except OSError:
            pass

        self.sock = None
        self.log("bridge disconnected")

        if self.args.once:
            self.stop_requested = True
        else:
            self.next_connect_time = time.monotonic() + self.args.retry_interval

    def register_stdin(self) -> None:
        if self.args.watch_only:
            return
        try:
            fd = sys.stdin.fileno()
        except OSError:
            return
        self.stdin_fd = fd
        self.selector.register(fd, selectors.EVENT_READ, "stdin")

    def unregister_stdin(self) -> None:
        if self.stdin_fd is None:
            return
        try:
            self.selector.unregister(self.stdin_fd)
        except Exception:
            pass
        self.stdin_fd = None

    def handle_socket(self) -> None:
        assert self.sock is not None

        try:
            data = self.sock.recv(8192)
        except OSError as exc:
            if exc.errno in {errno.EAGAIN, errno.EWOULDBLOCK}:
                return
            self.log(f"socket read failed: {exc}")
            self.close_socket()
            return

        if not data:
            self.close_socket()
            return

        os.write(sys.stdout.fileno(), data)
        for note in self.annotator.feed(data):
            self.emit_note(note)

    def handle_stdin(self) -> None:
        if self.stdin_fd is None:
            return

        try:
            data = os.read(self.stdin_fd, 8192)
        except OSError as exc:
            if exc.errno in {errno.EAGAIN, errno.EWOULDBLOCK}:
                return
            raise

        if not data:
            self.stop_requested = True
            return

        if b"\x1d" in data:
            self.emit_note("leaving console")
            self.stop_requested = True
            return

        if self.sock is None:
            self.emit_note("bridge not connected yet")
            return

        try:
            self.sock.sendall(data)
        except OSError as exc:
            self.log(f"socket write failed: {exc}")
            self.close_socket()

    def run(self) -> int:
        with LocalTerminal(enabled=not self.args.watch_only):
            self.register_stdin()
            try:
                while not self.stop_requested:
                    self.maybe_connect()
                    events = self.selector.select(timeout=1.0)
                    for key, _ in events:
                        if key.data == "socket":
                            self.handle_socket()
                        elif key.data == "stdin":
                            self.handle_stdin()
            finally:
                self.unregister_stdin()
                self.close_socket()
                self.selector.close()

        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive console for the serial TCP bridge with key/menu annotations."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="bridge host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bridge port")
    parser.add_argument(
        "--retry-interval",
        type=float,
        default=1.0,
        help="seconds between reconnect attempts",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=3.0,
        help="seconds to wait for each TCP connect attempt",
    )
    parser.add_argument(
        "--watch-only",
        action="store_true",
        help="do not forward local stdin; only observe bridge output",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="connect once and exit when the socket closes",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = ConsoleClient(args)

    def handle_signal(signum: int, _frame) -> None:
        client.log(f"signal {signum} received, stopping")
        client.stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        return client.run()
    except KeyboardInterrupt:
        client.log("keyboard interrupt, stopping")
        return 130
    except OSError as exc:
        client.log(f"fatal error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
