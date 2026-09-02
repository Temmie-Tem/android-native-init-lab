from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
import socket
import sys
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p328_auth_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p328_auth_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))
TEST_NONCE = bytes([0xA5]) * runtime.NONCE_SIZE


class Writer:
    def __init__(self) -> None:
        self.payload = bytearray()

    def write_stdout(self, value: bytes) -> None:
        self.payload.extend(value)


class P328AuthObserverTests(unittest.TestCase):
    @staticmethod
    def _receive_exact(peer: socket.socket, size: int) -> bytes:
        output = bytearray()
        while len(output) < size:
            chunk = peer.recv(size - len(output))
            if not chunk:
                raise AssertionError("unexpected peer EOF")
            output.extend(chunk)
        return bytes(output)

    def _receive_frame(self, peer: socket.socket) -> observer.Frame:
        header = self._receive_exact(peer, observer.HEADER.size)
        length = int.from_bytes(header[6:8], "little")
        return observer.decode_frame(
            header + self._receive_exact(peer, length)
        )

    @staticmethod
    def _send_fragmented(peer: socket.socket, value: bytes) -> None:
        cursor = 0
        widths = (1, 3, 7, 13)
        index = 0
        while cursor < len(value):
            width = widths[index % len(widths)]
            peer.sendall(value[cursor : cursor + width])
            cursor += width
            index += 1

    def test_hmac_vectors_bind_domain_run_nonce_sequence_and_command(self) -> None:
        self.assertEqual(
            runtime.P328_RUN_ID_HEX,
            "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b",
        )
        self.assertEqual(
            runtime.DEVICE_BANNER,
            b"S22PLUS-FYG8-E3:c328f1e0a90b5e6d7c8a9b0c1d2e3f2b\n",
        )
        open_expected = hmac.new(
            TEST_KEY,
            runtime.AUTH_DOMAIN_OPEN + runtime.P328_RUN_ID + TEST_NONCE,
            hashlib.sha256,
        ).digest()
        self.assertEqual(
            observer.compute_open_tag(TEST_KEY, runtime.P328_RUN_ID, TEST_NONCE),
            open_expected,
        )
        sequence = 23
        command = b"echo printable"
        expected = hmac.new(
            TEST_KEY,
            runtime.AUTH_DOMAIN_EXEC
            + runtime.P328_RUN_ID
            + TEST_NONCE
            + sequence.to_bytes(4, "little")
            + command,
            hashlib.sha256,
        ).digest()
        self.assertEqual(
            observer.compute_exec_tag(
                TEST_KEY, runtime.P328_RUN_ID, TEST_NONCE, sequence, command
            ),
            expected,
        )

    def test_wrong_key_tag_nonce_and_sequence_never_verify(self) -> None:
        tag = observer.compute_exec_tag(
            TEST_KEY, runtime.P328_RUN_ID, TEST_NONCE, 2, b"echo ok"
        )
        self.assertFalse(
            observer.constant_time_equal(
                tag,
                observer.compute_exec_tag(
                    b"K" * 32,
                    runtime.P328_RUN_ID,
                    TEST_NONCE,
                    2,
                    b"echo ok",
                ),
            )
        )
        self.assertFalse(
            observer.constant_time_equal(
                tag,
                observer.compute_exec_tag(
                    TEST_KEY,
                    runtime.P328_RUN_ID,
                    bytes([0x5A]) * 32,
                    2,
                    b"echo ok",
                ),
            )
        )
        self.assertFalse(
            observer.constant_time_equal(
                tag,
                observer.compute_exec_tag(
                    TEST_KEY,
                    runtime.P328_RUN_ID,
                    TEST_NONCE,
                    3,
                    b"echo ok",
                ),
            )
        )
        self.assertFalse(observer.constant_time_equal(tag, tag[:-1] + b"X"))

    def test_printable_command_codec_and_count_bounds(self) -> None:
        self.assertEqual(observer.validate_command(b"A" * 1023), b"A" * 1023)
        for command in (
            b"",
            b"A" * 1024,
            b"contains\nnewline",
            b"contains\rreturn",
            b"contains\x00nul",
            b"contains\x1fcontrol",
            "unicode-\u2603".encode("utf-8"),
        ):
            with self.assertRaises(observer.AuthObserverError):
                observer.validate_command(command)
        self.assertEqual(
            observer.validate_commands((b"echo one", b"echo two")),
            (b"echo one", b"echo two"),
        )
        with self.assertRaises(observer.AuthObserverError):
            observer.validate_commands(())
        with self.assertRaises(observer.AuthObserverError):
            observer.validate_commands(tuple(b"echo %d" % index for index in range(17)))

    def test_codec_rejects_crc_and_predecessor_magic(self) -> None:
        encoded = observer.encode_frame(runtime.FRAME_EXEC, 2, b"echo ok")
        self.assertEqual(encoded[:4], b"S328")
        self.assertEqual(encoded[4], 1)
        self.assertEqual(
            observer.decode_frame(encoded),
            observer.Frame(runtime.FRAME_EXEC, 2, b"echo ok"),
        )
        with self.assertRaises(observer.AuthObserverError):
            observer.decode_frame(encoded[:-1] + bytes([encoded[-1] ^ 1]))
        predecessor = b"S327" + encoded[4:]
        with self.assertRaises(observer.AuthObserverError):
            observer.decode_frame(predecessor)

    def _serve(
        self,
        peer: socket.socket,
        commands: tuple[bytes, ...],
        outputs: tuple[bytes, ...],
        errors: list[BaseException],
    ) -> None:
        try:
            self._send_fragmented(peer, runtime.DEVICE_BANNER)
            opened = self._receive_frame(peer)
            self.assertEqual(
                opened,
                observer.Frame(runtime.FRAME_OPEN, 0, runtime.P328_RUN_ID),
            )
            self._send_fragmented(
                peer,
                observer.encode_frame(runtime.FRAME_CHALLENGE, 0, TEST_NONCE),
            )
            auth = self._receive_frame(peer)
            self.assertEqual(
                auth,
                observer.Frame(
                    runtime.FRAME_AUTH,
                    1,
                    observer.compute_open_tag(
                        TEST_KEY, runtime.P328_RUN_ID, TEST_NONCE
                    ),
                ),
            )
            self._send_fragmented(
                peer,
                observer.encode_frame(
                    runtime.FRAME_READY,
                    1,
                    observer.compute_ready_tag(
                        TEST_KEY, runtime.P328_RUN_ID, TEST_NONCE
                    ),
                ),
            )
            for sequence, (command, output) in enumerate(
                zip(commands, outputs, strict=True), start=2
            ):
                request = self._receive_frame(peer)
                self.assertEqual(request.frame_type, runtime.FRAME_EXEC)
                self.assertEqual(request.sequence, sequence)
                self.assertEqual(request.payload[32:], command)
                self.assertEqual(
                    request.payload[:32],
                    observer.compute_exec_tag(
                        TEST_KEY,
                        runtime.P328_RUN_ID,
                        TEST_NONCE,
                        sequence,
                        command,
                    ),
                )
                for offset in range(0, len(output), runtime.MAX_FRAME_PAYLOAD):
                    self._send_fragmented(
                        peer,
                        observer.encode_frame(
                            runtime.FRAME_DATA,
                            sequence,
                            output[offset : offset + runtime.MAX_FRAME_PAYLOAD],
                        ),
                    )
                self._send_fragmented(
                    peer,
                    observer.encode_frame(
                        runtime.FRAME_EXIT,
                        sequence,
                        observer.EXIT.pack(0, 0, 0, len(output), 2),
                    ),
                )
            close_sequence = len(commands) + 2
            closed = self._receive_frame(peer)
            self.assertEqual(closed.frame_type, runtime.FRAME_CLOSE)
            self.assertEqual(closed.sequence, close_sequence)
            self.assertEqual(
                closed.payload,
                observer.compute_close_tag(
                    TEST_KEY, runtime.P328_RUN_ID, TEST_NONCE, close_sequence
                ),
            )
            self._send_fragmented(
                peer,
                observer.encode_frame(
                    runtime.FRAME_DONE,
                    close_sequence,
                    observer.DONE.pack(len(commands)),
                ),
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def test_fragmented_authenticated_exchange_and_default_proof(self) -> None:
        commands = (b"echo hello", b"/bin/busybox id")
        outputs = (b"hello\n", b"uid=0(root) gid=0(root)\n")
        host, device = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=self._serve, args=(device, commands, outputs, errors)
        )
        thread.start()
        writer = Writer()
        try:
            result = observer.exchange_commands(
                host.fileno(), TEST_KEY, commands, timeout_sec=5, writer=writer
            )
        finally:
            host.close()
            thread.join(timeout=5)
            device.close()
        if thread.is_alive():
            self.fail("simulated P328 peer did not terminate")
        if errors:
            raise errors[0]
        self.assertEqual([item.output for item in result.commands], list(outputs))
        self.assertTrue(result.audit.authenticated)
        self.assertEqual(result.audit.nonce, TEST_NONCE)
        self.assertEqual(bytes(writer.payload), bytes(result.audit.rx))

    def test_default_fixed_proof_is_an_observer_projection_only(self) -> None:
        commands = observer.DEFAULT_COMMANDS
        outputs = (
            b"uid=0(root) gid=0(root) groups=0(root)\n",
            b"Linux s22plus 5.10.198 aarch64 GNU/Linux\n",
            f"P328-NONCE {runtime.P328_RUN_ID_HEX}\n".encode("ascii"),
        )
        host, device = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=self._serve, args=(device, commands, outputs, errors)
        )
        thread.start()
        try:
            result = observer.exchange_commands(
                host.fileno(), TEST_KEY, commands, timeout_sec=5
            )
        finally:
            host.close()
            thread.join(timeout=5)
            device.close()
        if thread.is_alive():
            self.fail("simulated P328 proof peer did not terminate")
        if errors:
            raise errors[0]
        receipt = observer.validate_default_proof(result)
        self.assertTrue(receipt["pid1_authenticated_framed_exec_proof"])
        self.assertEqual(
            receipt["auth_key_sha256"], hashlib.sha256(TEST_KEY).hexdigest()
        )
        self.assertNotIn(TEST_KEY.hex(), str(receipt))

    def test_bad_ready_tag_stops_before_any_exec(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        saw_exec = False

        def run() -> None:
            nonlocal saw_exec
            try:
                device.sendall(runtime.DEVICE_BANNER)
                self.assertEqual(self._receive_frame(device).frame_type, runtime.FRAME_OPEN)
                device.sendall(observer.encode_frame(runtime.FRAME_CHALLENGE, 0, TEST_NONCE))
                self._receive_frame(device)
                device.sendall(observer.encode_frame(runtime.FRAME_READY, 1, b"X" * 32))
                device.settimeout(0.5)
                try:
                    frame = self._receive_frame(device)
                    saw_exec = frame.frame_type == runtime.FRAME_EXEC
                except (socket.timeout, AssertionError):
                    pass
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        thread = threading.Thread(target=run)
        thread.start()
        try:
            with self.assertRaises(observer.AuthObserverError):
                observer.exchange_commands(host.fileno(), TEST_KEY, (b"echo",), timeout_sec=2)
        finally:
            host.close()
            thread.join(timeout=2)
            device.close()
        self.assertFalse(saw_exec)
        if errors:
            raise errors[0]


if __name__ == "__main__":
    unittest.main()
