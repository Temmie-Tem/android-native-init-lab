from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import os
import socket
import sys
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p332_logical_resident_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p332_logical_resident_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(runtime.AUTH_KEY_SIZE))
NONCES = (
    bytes([0xA5]) * runtime.NONCE_SIZE,
    bytes([0x5A]) * runtime.NONCE_SIZE,
)


class _Writer:
    def __init__(self) -> None:
        self.payload = bytearray()

    def write_stdout(self, value: bytes) -> None:
        self.payload.extend(value)


class P332LogicalResidentObserverTests(unittest.TestCase):
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
        length = observer.HEADER.unpack(header)[3]
        payload = self._receive_exact(peer, length)
        return observer.decode_frame(header + payload)

    @staticmethod
    def _send(
        peer: socket.socket, frame_type: int, sequence: int, payload: bytes
    ) -> None:
        peer.sendall(observer.encode_frame(frame_type, sequence, payload))

    def _serve_success(
        self,
        peer: socket.socket,
        nonce: bytes,
        errors: list[BaseException],
        exit_code: int = 0,
    ) -> None:
        try:
            peer.sendall(runtime.DEVICE_BANNER)
            opened = self._receive_frame(peer)
            self.assertEqual(
                opened,
                observer.Frame(runtime.FRAME_OPEN, 0, runtime.P332_RUN_ID),
            )
            self._send(
                peer,
                runtime.DIAGNOSTIC_FRAME_TYPE,
                0,
                observer.DIAGNOSTIC.pack(
                    runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0
                ),
            )
            self._send(
                peer,
                runtime.DIAGNOSTIC_FRAME_TYPE,
                0,
                observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_RNG, 0),
            )
            self._send(peer, runtime.FRAME_CHALLENGE, 0, nonce)
            auth = self._receive_frame(peer)
            self.assertEqual(auth.frame_type, runtime.FRAME_AUTH)
            self.assertEqual(auth.sequence, 1)
            self.assertEqual(
                auth.payload,
                observer.compute_open_tag(TEST_KEY, runtime.P332_RUN_ID, nonce),
            )
            self._send(
                peer,
                runtime.FRAME_READY,
                1,
                observer.compute_ready_tag(TEST_KEY, runtime.P332_RUN_ID, nonce),
            )
            for sequence, command in enumerate(runtime.DEFAULT_COMMANDS, start=2):
                request = self._receive_frame(peer)
                self.assertEqual(request.frame_type, runtime.FRAME_EXEC)
                self.assertEqual(request.sequence, sequence)
                self.assertEqual(request.payload[32:], command)
                self.assertEqual(
                    request.payload[:32],
                    observer.compute_exec_tag(
                        TEST_KEY,
                        runtime.P332_RUN_ID,
                        nonce,
                        sequence,
                        command,
                    ),
                )
                if sequence == 2:
                    output = b"uid=0(root) gid=0(root)\n"
                elif sequence == 3:
                    output = b"Linux p332 5.10.198 aarch64 GNU/Linux\n"
                else:
                    output = (
                        f"P328-NONCE {runtime.P328_RUN_ID_HEX}\n".encode(
                            "ascii"
                        )
                    )
                self._send(peer, runtime.FRAME_DATA, sequence, output)
                self._send(
                    peer,
                    runtime.FRAME_EXIT,
                    sequence,
                    observer.EXIT.pack(0, exit_code, 0, len(output), 1),
                )
            close_sequence = len(runtime.DEFAULT_COMMANDS) + 2
            closed = self._receive_frame(peer)
            self.assertEqual(closed.frame_type, runtime.FRAME_CLOSE)
            self.assertEqual(closed.sequence, close_sequence)
            self.assertEqual(
                closed.payload,
                observer.compute_close_tag(
                    TEST_KEY,
                    runtime.P332_RUN_ID,
                    nonce,
                    close_sequence,
                ),
            )
            self._send(
                peer,
                runtime.FRAME_DONE,
                close_sequence,
                observer.DONE.pack(len(runtime.DEFAULT_COMMANDS)),
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def test_two_sessions_use_one_descriptor_and_validate_strict_proof(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        peer_thread = threading.Thread(
            target=lambda: [
                self._serve_success(peer, nonce, errors) for nonce in NONCES
            ]
        )
        peer_thread.start()
        writer = _Writer()
        try:
            with mock.patch.object(
                observer, "_descriptor", wraps=observer._descriptor
            ) as descriptor:
                result = observer.exchange_resident(
                    host, TEST_KEY, timeout_sec=5, writer=writer
                )
                descriptor.assert_called_once_with(host)
            self.assertTrue(result.complete)
            self.assertEqual(result.session_count, 2)
            self.assertEqual(result.reconnect_count, 0)
            self.assertEqual(
                [item.nonce for item in result.sessions], list(NONCES)
            )
            self.assertEqual(
                [len(item.raw_tx) for item in result.sessions],
                [len(item.audit.tx) for item in result.sessions],
            )
            proof = observer.validate_resident_proof(result)
            self.assertEqual(proof["run_id_hex"], runtime.P332_RUN_ID_HEX)
            self.assertTrue(proof["same_fd"])
            self.assertTrue(proof["same_tty_fd"])
            self.assertEqual(proof["physical_reopen_count"], 0)
            self.assertEqual(observer.validate_proof_value(proof), proof)
            self.assertEqual(
                observer.validate_proof_value(
                    json.loads(json.dumps(proof)),
                    expected_auth_key_sha256=hashlib.sha256(TEST_KEY).hexdigest(),
                ),
                proof,
            )
            self.assertGreaterEqual(len(writer.payload), len(runtime.DEVICE_BANNER) * 2)
            os.fstat(host.fileno())
        finally:
            host.close()
            peer_thread.join(timeout=5)
            peer.close()
        self.assertFalse(peer_thread.is_alive())
        self.assertFalse(errors)

    def test_nonzero_exit_stops_before_second_session_and_retains_failure(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        peer_thread = threading.Thread(
            target=self._serve_success,
            args=(peer, NONCES[0], errors, 7),
        )
        peer_thread.start()
        try:
            with self.assertRaises(observer.LogicalResidentObserverError) as raised:
                observer.exchange_resident(host, TEST_KEY, timeout_sec=5)
            failure = raised.exception
            self.assertEqual(failure.session_index, 0)
            self.assertEqual(failure.result.session_count, 1)
            self.assertFalse(failure.result.complete)
            failed = failure.result.sessions[0]
            self.assertEqual(failed.error_type, "AuthObserverError")
            self.assertTrue(failed.audit.done_seen)
            self.assertTrue(failed.result is not None)
            self.assertFalse(failed.result.commands[0].ok)
            os.fstat(host.fileno())
        finally:
            host.close()
            peer_thread.join(timeout=5)
            peer.close()
        self.assertFalse(peer_thread.is_alive())
        self.assertFalse(errors)

    def test_replayed_nonce_stops_before_second_auth_and_keeps_raw_failure(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []

        def serve() -> None:
            try:
                self._serve_success(peer, NONCES[0], errors)
                peer.sendall(runtime.DEVICE_BANNER)
                opened = self._receive_frame(peer)
                self.assertEqual(opened.frame_type, runtime.FRAME_OPEN)
                self._send(
                    peer,
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(
                        runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0
                    ),
                )
                self._send(
                    peer,
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_RNG, 0),
                )
                self._send(peer, runtime.FRAME_CHALLENGE, 0, NONCES[0])
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        peer_thread = threading.Thread(target=serve)
        peer_thread.start()
        try:
            with self.assertRaises(observer.LogicalResidentObserverError) as raised:
                observer.exchange_resident(host, TEST_KEY, timeout_sec=5)
            failure = raised.exception
            self.assertEqual(failure.session_index, 1)
            self.assertEqual(failure.result.terminal, "session-failed")
            self.assertEqual(failure.result.session_count, 2)
            self.assertEqual(failure.result.sessions[0].nonce, NONCES[0])
            second = failure.result.sessions[1]
            self.assertFalse(second.authenticated)
            self.assertEqual(second.failure_stage, "challenge-read")
            self.assertEqual(
                second.raw_tx,
                observer.encode_frame(runtime.FRAME_OPEN, 0, runtime.P332_RUN_ID),
            )
            os.fstat(host.fileno())
        finally:
            host.close()
            peer_thread.join(timeout=5)
            peer.close()
        self.assertFalse(peer_thread.is_alive())
        self.assertFalse(errors)

    def test_first_session_stall_stops_without_replaying_second_session(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []

        def stall() -> None:
            try:
                peer.sendall(runtime.DEVICE_BANNER)
                opened = self._receive_frame(peer)
                self.assertEqual(opened.frame_type, runtime.FRAME_OPEN)
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        peer_thread = threading.Thread(target=stall)
        peer_thread.start()
        try:
            with self.assertRaises(observer.LogicalResidentObserverError) as raised:
                observer.exchange_resident(host, TEST_KEY, timeout_sec=0.05)
            failure = raised.exception
            self.assertEqual(failure.session_index, 0)
            self.assertEqual(failure.result.session_count, 1)
            self.assertEqual(failure.result.terminal, "session-failed")
            session = failure.result.sessions[0]
            self.assertEqual(session.failure_stage, "open-diagnostic-read")
            self.assertEqual(session.raw_tx, observer.encode_frame(runtime.FRAME_OPEN, 0, runtime.P332_RUN_ID))
            self.assertEqual(session.raw_rx, runtime.DEVICE_BANNER)
            os.fstat(host.fileno())
        finally:
            host.close()
            peer_thread.join(timeout=5)
            peer.close()
        self.assertFalse(peer_thread.is_alive())
        self.assertFalse(errors)

    def test_serialized_validator_rejects_exit_nonce_and_key_drift(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        peer_thread = threading.Thread(
            target=lambda: [
                self._serve_success(peer, nonce, errors) for nonce in NONCES
            ]
        )
        peer_thread.start()
        try:
            result = observer.exchange_resident(host, TEST_KEY, timeout_sec=5)
            proof = observer.validate_resident_proof(result)
            for label, mutate in (
                (
                    "extra-key",
                    lambda item: item.__setitem__("unexpected", True),
                ),
                (
                    "nonzero-exit",
                    lambda item: item["sessions"][0]["commands"][0].__setitem__(
                        "exit_code", 1
                    ),
                ),
                (
                    "nonce-replay",
                    lambda item: item["sessions"][1].__setitem__(
                        "challenge_nonce_sha256",
                        item["sessions"][0]["challenge_nonce_sha256"],
                    ),
                ),
                (
                    "auth-key-drift",
                    lambda item: item["sessions"][1].__setitem__(
                        "auth_key_sha256", "a" * 64
                    ),
                ),
            ):
                changed = deepcopy(proof)
                mutate(changed)
                with self.subTest(label=label), self.assertRaises(
                    observer.AuthObserverError
                ):
                    observer.validate_proof_value(changed)
        finally:
            host.close()
            peer_thread.join(timeout=5)
            peer.close()
        self.assertFalse(peer_thread.is_alive())
        self.assertFalse(errors)


if __name__ == "__main__":
    unittest.main()
