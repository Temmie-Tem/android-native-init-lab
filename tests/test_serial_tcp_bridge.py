from __future__ import annotations

import errno
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


serial_bridge = load_script("workspace/public/src/scripts/revalidation/serial_tcp_bridge.py")


class FakeSelector:
    def __init__(self) -> None:
        self.registered: list[tuple[object, int, str]] = []
        self.modified: list[tuple[object, int, str]] = []
        self.unregistered: list[object] = []

    def register(self, fileobj: object, events: int, data: str) -> None:
        self.registered.append((fileobj, events, data))

    def modify(self, fileobj: object, events: int, data: str) -> None:
        self.modified.append((fileobj, events, data))

    def unregister(self, fileobj: object) -> None:
        self.unregistered.append(fileobj)


class FakeClient:
    def __init__(self, recv_chunks: list[bytes] | None = None) -> None:
        self.recv_chunks = list(recv_chunks or [])
        self.sent = bytearray()
        self.closed = False
        self.blocking: list[bool] = []

    def setblocking(self, value: bool) -> None:
        self.blocking.append(value)

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, _size: int) -> bytes:
        if self.recv_chunks:
            item = self.recv_chunks.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        return b""

    def close(self) -> None:
        self.closed = True


class FakeServer:
    def __init__(self, client: FakeClient, addr: tuple[str, int] = ("127.0.0.1", 12345)) -> None:
        self.client = client
        self.addr = addr

    def accept(self) -> tuple[FakeClient, tuple[str, int]]:
        return self.client, self.addr


class FakeCapture:
    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, data: bytes) -> None:
        self.data.extend(data)


def make_bridge(**overrides: object):
    args = SimpleNamespace(
        device="auto",
        device_glob="/dev/serial/*",
        allow_multiple_auto_matches=False,
        expect_realpath=None,
        no_pin_device=False,
        allow_device_change=False,
        allow_client_without_serial=False,
        retry_interval=1.0,
    )
    for key, value in overrides.pop("arg_overrides", {}).items():
        setattr(args, key, value)
    bridge = object.__new__(serial_bridge.Bridge)
    bridge.args = args
    bridge.selector = FakeSelector()
    bridge.server = overrides.pop("server", FakeServer(FakeClient()))
    bridge.serial_fd = overrides.pop("serial_fd", None)
    bridge.serial_device = overrides.pop("serial_device", None)
    bridge.serial_stat = overrides.pop("serial_stat", None)
    bridge.expected_serial_realpath = overrides.pop("expected_serial_realpath", None)
    bridge.pinned_serial_realpath = overrides.pop("pinned_serial_realpath", None)
    bridge.client = overrides.pop("client", None)
    bridge.client_addr = overrides.pop("client_addr", None)
    bridge.capture_fp = overrides.pop("capture_fp", None)
    bridge.stop_requested = False
    bridge.next_serial_retry = 0.0
    bridge.next_serial_identity_check = 0.0
    bridge.serial_tx_buffer = bytearray(overrides.pop("serial_tx_buffer", b""))
    bridge.log = mock.Mock()
    return bridge


class DeviceSelectionAndPinning(unittest.TestCase):
    def test_resolve_device_returns_explicit_path_and_handles_auto_absent_or_ambiguous(self) -> None:
        bridge = make_bridge(arg_overrides={"device": "/dev/ttyACM0"})
        self.assertEqual(bridge.resolve_device(), "/dev/ttyACM0")

        bridge = make_bridge()
        with mock.patch.object(serial_bridge.glob, "glob", return_value=[]):
            self.assertIsNone(bridge.resolve_device())

        with mock.patch.object(serial_bridge.glob, "glob", return_value=["/dev/b", "/dev/a"]):
            self.assertIsNone(bridge.resolve_device())
            bridge.log.assert_called()

        bridge = make_bridge(arg_overrides={"allow_multiple_auto_matches": True})
        with mock.patch.object(serial_bridge.glob, "glob", return_value=["/dev/b", "/dev/a"]):
            self.assertEqual(bridge.resolve_device(), "/dev/a")

    def test_resolve_device_accepts_ordered_multi_glob_for_current_and_legacy_identity(self) -> None:
        bridge = make_bridge(arg_overrides={
            "device_glob": "/dev/serial/by-id/usb-A90-LNX_*,/dev/serial/by-id/usb-SAMSUNG_*",
        })

        def fake_glob(pattern: str) -> list[str]:
            return {
                "/dev/serial/by-id/usb-A90-LNX_*": ["/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"],
                "/dev/serial/by-id/usb-SAMSUNG_*": [],
            }.get(pattern, [])

        with mock.patch.object(serial_bridge.glob, "glob", side_effect=fake_glob):
            self.assertEqual(
                bridge.resolve_device(),
                "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00",
            )

    def test_serial_realpath_allowed_pins_expected_refuses_or_allows_change(self) -> None:
        bridge = make_bridge()
        with mock.patch.object(serial_bridge.os.path, "realpath", return_value="/real/one"):
            self.assertTrue(bridge.serial_realpath_allowed("/dev/tty"))
        self.assertEqual(bridge.pinned_serial_realpath, "/real/one")

        with mock.patch.object(serial_bridge.os.path, "realpath", return_value="/real/two"):
            self.assertFalse(bridge.serial_realpath_allowed("/dev/tty"))

        bridge = make_bridge(expected_serial_realpath="/real/expected", pinned_serial_realpath="/real/expected")
        with mock.patch.object(serial_bridge.os.path, "realpath", return_value="/real/other"):
            self.assertFalse(bridge.serial_realpath_allowed("/dev/tty"))

        bridge = make_bridge(
            pinned_serial_realpath="/real/old",
            arg_overrides={"allow_device_change": True},
        )
        with mock.patch.object(serial_bridge.os.path, "realpath", return_value="/real/new"):
            self.assertTrue(bridge.serial_realpath_allowed("/dev/tty"))
        self.assertEqual(bridge.pinned_serial_realpath, "/real/new")


class ManagedCapture(unittest.TestCase):
    def test_capture_is_private_direct_regular_owner_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private = root / "workspace/private"
            private.mkdir(parents=True, mode=0o700)
            with mock.patch.object(serial_bridge, "REPO_ROOT", root), mock.patch.object(
                serial_bridge, "PRIVATE_ROOT", private
            ):
                path, stream = serial_bridge._open_managed_capture(
                    str(private / "logs" / "capture.raw")
                )
                stream.write(b"raw")
                stream.close()
                self.assertEqual(path.read_bytes(), b"raw")
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                for bad in (Path("/tmp/a90.raw"), Path("/dev/null")):
                    with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                        serial_bridge._open_managed_capture(str(bad))

                symlink_parent = private / "symlink-parent"
                outside = root / "outside"
                outside.mkdir(mode=0o700)
                symlink_parent.symlink_to(outside, target_is_directory=True)
                with self.assertRaises(RuntimeError):
                    serial_bridge._open_managed_capture(
                        str(symlink_parent / "capture.raw")
                    )
                insecure_parent = private / "insecure-parent"
                insecure_parent.mkdir(mode=0o700)
                insecure_parent.chmod(0o777)
                with self.assertRaises(RuntimeError):
                    serial_bridge._open_managed_capture(
                        str(insecure_parent / "capture.raw")
                    )
                direct_link = private / "direct-link"
                direct_link.symlink_to(path)
                with self.assertRaises(RuntimeError):
                    serial_bridge._open_managed_capture(str(direct_link))


class ClientHandling(unittest.TestCase):
    def test_accept_client_rejects_when_serial_missing_unless_override_enabled(self) -> None:
        client = FakeClient()
        bridge = make_bridge(server=FakeServer(client), serial_fd=None)

        bridge.accept_client()

        self.assertIn(b"serial device is not connected", client.sent)
        self.assertTrue(client.closed)
        self.assertIsNone(bridge.client)

        client = FakeClient()
        bridge = make_bridge(
            server=FakeServer(client),
            serial_fd=None,
            arg_overrides={"allow_client_without_serial": True},
        )
        bridge.accept_client()
        self.assertIs(bridge.client, client)
        self.assertEqual(client.blocking, [False])
        self.assertEqual(bridge.selector.registered[-1][2], "client")

    def test_accept_client_rejects_second_client_with_busy_message(self) -> None:
        existing = FakeClient()
        extra = FakeClient()
        bridge = make_bridge(server=FakeServer(extra), serial_fd=10, client=existing)

        bridge.accept_client()

        self.assertEqual(extra.sent, serial_bridge.BRIDGE_BUSY_TEXT)
        self.assertTrue(extra.closed)
        self.assertIs(bridge.client, existing)

    def test_close_client_unregisters_closes_and_clears_state(self) -> None:
        client = FakeClient()
        bridge = make_bridge(client=client, client_addr=("host", 1000))

        bridge.close_client()

        self.assertEqual(bridge.selector.unregistered, [client])
        self.assertTrue(client.closed)
        self.assertIsNone(bridge.client)
        self.assertIsNone(bridge.client_addr)


class ForwardingAndSerialTx(unittest.TestCase):
    def test_forward_client_buffers_data_for_serial_and_flushes(self) -> None:
        client = FakeClient([b"cmd\n"])
        capture = FakeCapture()
        bridge = make_bridge(client=client, serial_fd=5, capture_fp=capture)

        with mock.patch.object(bridge, "flush_serial_tx") as flush:
            bridge.forward_client()

        self.assertEqual(bridge.serial_tx_buffer, b"cmd\n")
        self.assertIn(b"--- tcp->serial ---", capture.data)
        flush.assert_called_once_with()

    def test_forward_client_closes_on_empty_read_or_os_error(self) -> None:
        client = FakeClient([b""])
        bridge = make_bridge(client=client)
        with mock.patch.object(bridge, "close_client") as close:
            bridge.forward_client()
        close.assert_called_once_with()

        client = FakeClient([OSError("read failed")])
        bridge = make_bridge(client=client)
        with mock.patch.object(bridge, "close_client") as close:
            bridge.forward_client()
        close.assert_called_once_with()

    def test_forward_serial_captures_and_sends_to_client(self) -> None:
        client = FakeClient()
        capture = FakeCapture()
        bridge = make_bridge(client=client, serial_fd=7, capture_fp=capture)

        with mock.patch.object(serial_bridge.os, "read", return_value=b"serial out"):
            bridge.forward_serial()

        self.assertEqual(client.sent, b"serial out")
        self.assertIn(b"--- serial->tcp ---", capture.data)
        self.assertIn(b"serial out", capture.data)

    def test_forward_serial_closes_on_empty_read_or_nonblocking_errors(self) -> None:
        bridge = make_bridge(serial_fd=7)
        with mock.patch.object(serial_bridge.os, "read", side_effect=OSError(errno.EAGAIN, "again")), \
                mock.patch.object(bridge, "close_serial") as close:
            bridge.forward_serial()
        close.assert_not_called()

        bridge = make_bridge(serial_fd=7)
        with mock.patch.object(serial_bridge.os, "read", return_value=b""), \
                mock.patch.object(bridge, "close_serial") as close:
            bridge.forward_serial()
        close.assert_called_once_with()

    def test_flush_serial_tx_handles_partial_writes_and_nonblocking_backpressure(self) -> None:
        bridge = make_bridge(serial_fd=8, serial_tx_buffer=b"abcdef")
        with mock.patch.object(serial_bridge.os, "write", side_effect=[3, OSError(errno.EAGAIN, "again")]):
            bridge.flush_serial_tx()

        self.assertEqual(bridge.serial_tx_buffer, b"def")
        self.assertTrue(bridge.selector.modified)

    def test_flush_serial_tx_clears_buffer_when_serial_is_absent(self) -> None:
        bridge = make_bridge(serial_fd=None, serial_tx_buffer=b"pending")

        bridge.flush_serial_tx()

        self.assertEqual(bridge.serial_tx_buffer, b"")


if __name__ == "__main__":
    unittest.main()
