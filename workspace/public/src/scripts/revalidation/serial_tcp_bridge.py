#!/usr/bin/env python3

import argparse
import errno
import fcntl
import glob
import os
import selectors
import signal
import socket
import struct
import sys
import termios
import time
from pathlib import Path


DEFAULT_DEVICE_GLOB = "/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_BAUD = 115200

BAUD_MAP = {
    9600: termios.B9600,
    19200: termios.B19200,
    38400: termios.B38400,
    57600: termios.B57600,
    115200: termios.B115200,
    230400: termios.B230400,
    460800: termios.B460800,
    921600: termios.B921600,
}

CRTSCTS = getattr(termios, "CRTSCTS", 0)


class Bridge:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.selector = selectors.DefaultSelector()
        self.server = self._open_server()
        self.selector.register(self.server, selectors.EVENT_READ, "server")
        self.serial_fd = None
        self.serial_device = None
        self.serial_stat = None
        self.expected_serial_realpath = (
            os.path.realpath(self.args.expect_realpath)
            if self.args.expect_realpath else None
        )
        self.pinned_serial_realpath = self.expected_serial_realpath
        self.client = None
        self.client_addr = None
        self.capture_fp = None
        self.stop_requested = False
        self.next_serial_retry = 0.0
        self.next_serial_identity_check = 0.0
        self.serial_tx_buffer = bytearray()

        if self.args.capture:
            capture_path = Path(self.args.capture)
            capture_path.parent.mkdir(parents=True, exist_ok=True)
            self.capture_fp = capture_path.open("ab", buffering=0)

    def _open_server(self) -> socket.socket:
        attempts = max(1, self.args.bind_retries + 1)

        for attempt in range(1, attempts + 1):
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server.bind((self.args.host, self.args.port))
                server.listen(1)
                server.setblocking(False)
                self.log(f"tcp listener ready on {self.args.host}:{self.args.port}")
                return server
            except OSError as exc:
                server.close()
                if exc.errno != errno.EADDRINUSE or attempt == attempts:
                    raise
                self.log(
                    f"tcp port {self.args.host}:{self.args.port} is busy; "
                    f"retrying bind ({attempt}/{attempts - 1})"
                )
                time.sleep(self.args.bind_retry_interval)

        raise RuntimeError("unreachable bind retry state")

    def log(self, message: str) -> None:
        print(f"[bridge] {message}", file=sys.stderr, flush=True)

    def resolve_device(self) -> str | None:
        if self.args.device != "auto":
            return self.args.device

        matches = sorted(glob.glob(self.args.device_glob))
        if not matches:
            return None
        if len(matches) > 1 and not self.args.allow_multiple_auto_matches:
            self.log(
                "refusing ambiguous auto serial match; pass --device explicitly "
                "or --allow-multiple-auto-matches"
            )
            for match in matches:
                self.log(f"  match: {match} -> {os.path.realpath(match)}")
            return None
        return matches[0]

    def serial_realpath_allowed(self, device: str) -> bool:
        realpath = os.path.realpath(device)
        if self.expected_serial_realpath and realpath != self.expected_serial_realpath:
            self.log(
                f"refusing serial device {device} -> {realpath}; "
                f"expected {self.expected_serial_realpath}"
            )
            return False

        if self.pinned_serial_realpath is None:
            if not self.args.no_pin_device:
                self.pinned_serial_realpath = realpath
                self.log(f"pinned serial realpath: {realpath}")
            return True

        if realpath == self.pinned_serial_realpath:
            return True

        if self.args.allow_device_change and not self.expected_serial_realpath:
            self.log(
                f"serial realpath changed: {self.pinned_serial_realpath} -> {realpath}"
            )
            self.pinned_serial_realpath = realpath
            return True

        self.log(
            f"refusing serial device change: {device} -> {realpath}; "
            f"pinned {self.pinned_serial_realpath}"
        )
        return False

    def configure_serial(self, fd: int) -> None:
        attrs = termios.tcgetattr(fd)
        baud = BAUD_MAP[self.args.baud]

        attrs[0] = termios.IGNBRK
        attrs[1] = 0
        attrs[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB | termios.HUPCL | CRTSCTS)
        attrs[2] |= termios.CLOCAL | termios.CREAD | termios.CS8
        attrs[3] = 0
        attrs[4] = baud
        attrs[5] = baud
        attrs[6][termios.VMIN] = 1
        attrs[6][termios.VTIME] = 0

        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        termios.tcflush(fd, termios.TCIOFLUSH)
        if self.args.assert_dtr_rts:
            self.assert_dtr_rts(fd)

    def assert_dtr_rts(self, fd: int) -> None:
        mask = termios.TIOCM_DTR | termios.TIOCM_RTS
        try:
            fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack("I", mask))
        except OSError as exc:
            self.log(f"warning: failed to assert DTR/RTS: {exc}")

    def open_serial(self) -> None:
        device = self.resolve_device()
        if device is None:
            return
        if not self.serial_realpath_allowed(device):
            return

        try:
            fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            if not self.args.no_exclusive_tty:
                self.set_exclusive_tty(fd)
            self.configure_serial(fd)
            serial_stat = os.fstat(fd)
        except OSError as exc:
            if exc.errno in {errno.ENOENT, errno.ENODEV, errno.EACCES, errno.EBUSY}:
                self.log(f"serial not ready at {device}: {exc.strerror}")
                return
            raise

        self.serial_fd = fd
        self.serial_device = device
        self.serial_stat = (
            serial_stat.st_dev,
            serial_stat.st_ino,
            serial_stat.st_rdev,
        )
        self.next_serial_identity_check = time.monotonic() + 0.5
        self.selector.register(fd, selectors.EVENT_READ, "serial")
        self.log(f"serial connected: {device}")

    def update_serial_events(self) -> None:
        if self.serial_fd is None:
            return

        events = selectors.EVENT_READ
        if self.serial_tx_buffer:
            events |= selectors.EVENT_WRITE
        try:
            self.selector.modify(self.serial_fd, events, "serial")
        except KeyError:
            self.selector.register(self.serial_fd, events, "serial")

    def set_exclusive_tty(self, fd: int) -> None:
        try:
            fcntl.ioctl(fd, termios.TIOCEXCL)
        except OSError as exc:
            self.log(f"warning: failed to set TIOCEXCL: {exc}")

    def close_serial(self) -> None:
        if self.serial_fd is None:
            return

        try:
            self.selector.unregister(self.serial_fd)
        except Exception:
            pass

        try:
            os.close(self.serial_fd)
        except OSError:
            pass

        self.serial_fd = None
        self.serial_device = None
        self.serial_stat = None
        self.serial_tx_buffer.clear()
        self.next_serial_retry = time.monotonic() + self.args.retry_interval
        self.log("serial disconnected")
        self.close_client()

    def check_serial_identity(self) -> None:
        if self.serial_fd is None:
            return

        now = time.monotonic()
        if now < self.next_serial_identity_check:
            return

        self.next_serial_identity_check = now + 0.5
        device = self.resolve_device()
        if device is None:
            self.log("serial device path disappeared")
            self.close_serial()
            return
        if not self.serial_realpath_allowed(device):
            self.close_serial()
            return

        try:
            current_stat = os.stat(device)
        except OSError as exc:
            if exc.errno in {errno.ENOENT, errno.ENODEV, errno.EACCES}:
                self.log(f"serial device path is no longer valid: {exc.strerror}")
                self.close_serial()
                return
            raise

        current_identity = (
            current_stat.st_dev,
            current_stat.st_ino,
            current_stat.st_rdev,
        )
        if current_identity != self.serial_stat:
            self.log(f"serial device was re-enumerated: {device}")
            self.close_serial()

    def accept_client(self) -> None:
        conn, addr = self.server.accept()
        conn.setblocking(False)

        if self.serial_fd is None and not self.args.allow_client_without_serial:
            self.log(f"rejecting client from {addr[0]}:{addr[1]}: serial not connected")
            try:
                conn.sendall(b"[bridge] serial device is not connected; retry later\r\n")
            except OSError:
                pass
            conn.close()
            return

        if self.client is not None:
            self.log(f"rejecting extra client from {addr[0]}:{addr[1]}")
            conn.close()
            return

        self.client = conn
        self.client_addr = addr
        self.selector.register(conn, selectors.EVENT_READ, "client")
        self.log(f"client connected: {addr[0]}:{addr[1]}")

    def close_client(self) -> None:
        if self.client is None:
            return

        try:
            self.selector.unregister(self.client)
        except Exception:
            pass

        try:
            self.client.close()
        except OSError:
            pass

        if self.client_addr is not None:
            self.log(f"client disconnected: {self.client_addr[0]}:{self.client_addr[1]}")

        self.client = None
        self.client_addr = None

    def forward_serial(self) -> None:
        if self.serial_fd is None:
            return

        try:
            data = os.read(self.serial_fd, 8192)
        except OSError as exc:
            if exc.errno in {errno.EAGAIN, errno.EWOULDBLOCK}:
                return
            self.log(f"serial read failed: {exc}")
            self.close_serial()
            return

        if not data:
            self.close_serial()
            return

        if self.capture_fp is not None:
            self.capture_fp.write(b"\n--- serial->tcp ---\n")
            self.capture_fp.write(data)

        if self.client is not None:
            try:
                self.client.sendall(data)
            except OSError as exc:
                self.log(f"client write failed: {exc}")
                self.close_client()

    def flush_serial_tx(self) -> None:
        if self.serial_fd is None:
            self.serial_tx_buffer.clear()
            return

        while self.serial_tx_buffer:
            try:
                written = os.write(self.serial_fd, self.serial_tx_buffer)
            except OSError as exc:
                if exc.errno in {errno.EAGAIN, errno.EWOULDBLOCK}:
                    break
                self.log(f"serial write failed: {exc}")
                self.close_serial()
                return

            if written <= 0:
                break
            del self.serial_tx_buffer[:written]

        self.update_serial_events()

    def forward_client(self) -> None:
        if self.client is None:
            return

        try:
            data = self.client.recv(8192)
        except OSError as exc:
            self.log(f"client read failed: {exc}")
            self.close_client()
            return

        if not data:
            self.close_client()
            return

        if self.capture_fp is not None:
            self.capture_fp.write(b"\n--- tcp->serial ---\n")
            self.capture_fp.write(data)

        if self.serial_fd is None:
            return

        self.serial_tx_buffer.extend(data)
        self.flush_serial_tx()

    def tick(self) -> None:
        self.check_serial_identity()

        if self.serial_fd is None and time.monotonic() >= self.next_serial_retry:
            self.open_serial()
            if self.serial_fd is None:
                self.next_serial_retry = time.monotonic() + self.args.retry_interval

        events = self.selector.select(timeout=1.0)
        for key, mask in events:
            if key.data == "server":
                self.accept_client()
            elif key.data == "serial":
                if self.serial_fd is not None and key.fileobj == self.serial_fd:
                    if mask & selectors.EVENT_READ:
                        self.forward_serial()
                    if mask & selectors.EVENT_WRITE:
                        self.flush_serial_tx()
            elif key.data == "client":
                if self.client is not None and key.fileobj is self.client:
                    self.forward_client()

    def run(self) -> int:
        self.log("press Ctrl-C to stop")
        while not self.stop_requested:
            self.tick()
        return 0

    def close(self) -> None:
        self.close_client()
        self.close_serial()

        try:
            self.selector.unregister(self.server)
        except Exception:
            pass

        try:
            self.server.close()
        except OSError:
            pass

        self.selector.close()

        if self.capture_fp is not None:
            self.capture_fp.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose the A90 USB ACM shell over a local TCP port."
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="serial device path, or 'auto' to use the Samsung by-id symlink",
    )
    parser.add_argument(
        "--device-glob",
        default=DEFAULT_DEVICE_GLOB,
        help="glob used when --device=auto",
    )
    parser.add_argument(
        "--expect-realpath",
        help="require the resolved serial device path to match this path",
    )
    parser.add_argument(
        "--allow-device-change",
        action="store_true",
        help="allow the resolved serial device path to change after first connect",
    )
    parser.add_argument(
        "--no-pin-device",
        action="store_true",
        help="do not pin the first resolved serial device path",
    )
    parser.add_argument(
        "--allow-multiple-auto-matches",
        action="store_true",
        help="allow --device=auto when the Samsung by-id glob matches multiple devices",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="listen host")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="listen TCP port",
    )
    parser.add_argument(
        "--baud",
        type=int,
        choices=sorted(BAUD_MAP),
        default=DEFAULT_BAUD,
        help="serial baud rate",
    )
    parser.add_argument(
        "--retry-interval",
        type=float,
        default=1.0,
        help="seconds between serial reconnect attempts",
    )
    parser.add_argument(
        "--bind-retries",
        type=int,
        default=5,
        help="number of retries when the TCP listen port is still busy",
    )
    parser.add_argument(
        "--bind-retry-interval",
        type=float,
        default=0.5,
        help="seconds between TCP listen port bind retries",
    )
    parser.add_argument(
        "--capture",
        help="optional path to append raw bridge traffic",
    )
    parser.add_argument(
        "--assert-dtr-rts",
        action="store_true",
        help="explicitly assert DTR/RTS after opening the CDC ACM tty",
    )
    parser.add_argument(
        "--no-exclusive-tty",
        action="store_true",
        help="do not set TIOCEXCL on the serial tty after opening it",
    )
    parser.add_argument(
        "--allow-client-without-serial",
        action="store_true",
        help=(
            "accept a TCP client even when the serial device is absent; "
            "without this, clients are rejected so probe scripts can retry "
            "instead of sending commands into a missing serial device"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bridge = Bridge(args)

    def handle_signal(signum: int, _frame) -> None:
        bridge.log(f"signal {signum} received, stopping")
        bridge.stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        return bridge.run()
    finally:
        bridge.close()


if __name__ == "__main__":
    raise SystemExit(main())
