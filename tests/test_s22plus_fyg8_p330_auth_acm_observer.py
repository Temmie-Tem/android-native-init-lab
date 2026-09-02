from __future__ import annotations

import hashlib
from pathlib import Path
import socket
import sys
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p330_auth_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))
TEST_NONCE = bytes([0xA5]) * runtime.NONCE_SIZE


class Writer:
    def __init__(self) -> None:
        self.payload = bytearray()

    def write_stdout(self, value: bytes) -> None:
        self.payload.extend(value)


class P330AuthObserverTests(unittest.TestCase):
    @staticmethod
    def receive_exact(peer: socket.socket, size: int) -> bytes:
        output = bytearray()
        while len(output) < size:
            chunk = peer.recv(size - len(output))
            if not chunk:
                raise AssertionError("unexpected peer EOF")
            output.extend(chunk)
        return bytes(output)

    def receive_frame(self, peer: socket.socket) -> observer.Frame:
        header = self.receive_exact(peer, observer.HEADER.size)
        length = int.from_bytes(header[6:8], "little")
        return observer.decode_frame(header + self.receive_exact(peer, length))

    @staticmethod
    def send_frame(
        peer: socket.socket, frame_type: int, sequence: int, payload: bytes
    ) -> None:
        value = observer.encode_frame(frame_type, sequence, payload)
        for offset in range(0, len(value), 3):
            peer.sendall(value[offset : offset + 3])

    def send_diagnostic(self, peer: socket.socket, stage: int, code: int) -> None:
        self.send_frame(
            peer,
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            observer.DIAGNOSTIC.pack(stage, code),
        )

    def serve_success(
        self, peer: socket.socket, errors: list[BaseException]
    ) -> None:
        try:
            peer.sendall(runtime.DEVICE_BANNER)
            self.assertEqual(
                self.receive_frame(peer),
                observer.Frame(runtime.FRAME_OPEN, 0, runtime.P330_RUN_ID),
            )
            self.send_diagnostic(peer, runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0)
            self.send_diagnostic(peer, runtime.DIAGNOSTIC_STAGE_RNG, 3)
            self.send_frame(peer, runtime.FRAME_CHALLENGE, 0, TEST_NONCE)
            auth = self.receive_frame(peer)
            self.assertEqual(auth.frame_type, runtime.FRAME_AUTH)
            self.assertEqual(
                auth.payload,
                observer.compute_open_tag(
                    TEST_KEY, runtime.P330_RUN_ID, TEST_NONCE
                ),
            )
            self.send_frame(
                peer,
                runtime.FRAME_READY,
                1,
                observer.compute_ready_tag(
                    TEST_KEY, runtime.P330_RUN_ID, TEST_NONCE
                ),
            )
            outputs = (
                b"uid=0(root) gid=0(root)\n",
                b"Linux s22plus 5.10.198 aarch64 GNU/Linux\n",
                f"P328-NONCE {runtime.P330_RUN_ID_HEX}\n".encode(),
            )
            for sequence, (command, output) in enumerate(
                zip(runtime.DEFAULT_COMMANDS, outputs, strict=True), start=2
            ):
                request = self.receive_frame(peer)
                self.assertEqual(request.frame_type, runtime.FRAME_EXEC)
                self.assertEqual(request.sequence, sequence)
                self.assertEqual(request.payload[32:], command)
                self.send_frame(peer, runtime.FRAME_DATA, sequence, output)
                self.send_frame(
                    peer,
                    runtime.FRAME_EXIT,
                    sequence,
                    observer.EXIT.pack(0, 0, 0, len(output), 1),
                )
            close_sequence = len(runtime.DEFAULT_COMMANDS) + 2
            closed = self.receive_frame(peer)
            self.assertEqual(closed.frame_type, runtime.FRAME_CLOSE)
            self.send_frame(
                peer,
                runtime.FRAME_DONE,
                close_sequence,
                observer.DONE.pack(len(runtime.DEFAULT_COMMANDS)),
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def test_fragmented_success_preserves_diagnostics_and_auth_proof(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(target=self.serve_success, args=(device, errors))
        thread.start()
        writer = Writer()
        try:
            result = observer.exchange_commands(
                host.fileno(), TEST_KEY, timeout_sec=5, writer=writer
            )
        finally:
            host.close()
            thread.join(timeout=5)
            device.close()
        if thread.is_alive():
            self.fail("simulated P330 peer did not terminate")
        if errors:
            raise errors[0]
        receipt = observer.validate_default_proof(result)
        self.assertEqual(receipt["rng_eagain_retries"], 3)
        self.assertEqual(
            receipt["diagnostics"],
            [{"stage": 1, "code": 0}, {"stage": 2, "code": 3}],
        )
        self.assertTrue(receipt["pid1_authenticated_framed_exec_proof"])
        self.assertEqual(bytes(writer.payload), bytes(result.audit.rx))

    def test_terminal_rng_diagnostic_fails_fast_with_actual_partial_audit(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)
        writer = Writer()

        def serve() -> None:
            device.sendall(runtime.DEVICE_BANNER)
            self.receive_frame(device)
            self.send_diagnostic(device, runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0)
            self.send_diagnostic(device, runtime.DIAGNOSTIC_STAGE_RNG, -11)

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            with self.assertRaises(observer.AuthObserverError) as raised:
                observer.exchange_commands(
                    host.fileno(), TEST_KEY, timeout_sec=5, writer=writer
                )
        finally:
            host.close()
            thread.join(timeout=5)
            device.close()
        audit = raised.exception.audit
        self.assertEqual(raised.exception.stage, "rng-diagnostic-read")
        self.assertEqual(raised.exception.code, -11)
        self.assertEqual(len(audit.tx), observer.HEADER.size + len(runtime.P330_RUN_ID))
        self.assertEqual(bytes(audit.rx), bytes(writer.payload))
        self.assertEqual(
            audit.diagnostics,
            [observer.Diagnostic(1, 0), observer.Diagnostic(2, -11)],
        )
        self.assertFalse(audit.challenge_seen)

    def test_missing_open_diagnostic_keeps_banner_and_open_bytes(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)
        original = observer.OPEN_DIAGNOSTIC_TIMEOUT_SEC
        observer.OPEN_DIAGNOSTIC_TIMEOUT_SEC = 0.05

        def serve() -> None:
            device.sendall(runtime.DEVICE_BANNER)
            self.receive_frame(device)

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            with self.assertRaises(observer.AuthObserverError) as raised:
                observer.exchange_commands(host.fileno(), TEST_KEY, timeout_sec=1)
        finally:
            observer.OPEN_DIAGNOSTIC_TIMEOUT_SEC = original
            host.close()
            thread.join(timeout=2)
            device.close()
        audit = raised.exception.audit
        self.assertEqual(raised.exception.stage, "open-diagnostic-read")
        self.assertEqual(audit.exception_type, "TimeoutError")
        self.assertEqual(bytes(audit.rx), runtime.DEVICE_BANNER)
        self.assertEqual(
            hashlib.sha256(bytes(audit.tx)).hexdigest(),
            hashlib.sha256(
                observer.encode_frame(
                    runtime.FRAME_OPEN, 0, runtime.P330_RUN_ID
                )
            ).hexdigest(),
        )

    def test_malformed_or_out_of_order_diagnostic_is_rejected(self) -> None:
        malformed = observer.Frame(runtime.DIAGNOSTIC_FRAME_TYPE, 0, b"short")
        with self.assertRaises(observer.AuthObserverError):
            observer.parse_diagnostic_frame(
                malformed, runtime.DIAGNOSTIC_STAGE_OPEN_PARSED
            )
        wrong = observer.Frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_RNG, 0),
        )
        with self.assertRaises(observer.AuthObserverError):
            observer.parse_diagnostic_frame(
                wrong, runtime.DIAGNOSTIC_STAGE_OPEN_PARSED
            )


if __name__ == "__main__":
    unittest.main()
