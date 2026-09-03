from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import socket
import sys
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p334_first_read_rc_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(runtime.AUTH_KEY_SIZE))
NONCES = (b"A" * runtime.NONCE_SIZE, b"B" * runtime.NONCE_SIZE)


class P334FirstReadReturnCodeObserverTests(unittest.TestCase):
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
        size = observer.HEADER.unpack(header)[3]
        return observer.decode_frame(header + self._receive_exact(peer, size))

    @staticmethod
    def _send(peer: socket.socket, kind: int, sequence: int, payload: bytes) -> None:
        peer.sendall(observer.encode_frame(kind, sequence, payload))

    def _serve_session(
        self,
        peer: socket.socket,
        nonce: bytes,
        errors: list[BaseException],
        *,
        entry_stage: int = runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
    ) -> None:
        try:
            peer.sendall(runtime.DEVICE_BANNER)
            opened = self._receive_frame(peer)
            self.assertEqual(
                opened, observer.Frame(runtime.FRAME_OPEN, 0, runtime.P334_RUN_ID)
            )
            self._send(
                peer,
                runtime.DIAGNOSTIC_FRAME_TYPE,
                0,
                observer.DIAGNOSTIC.pack(entry_stage, 0),
            )
            if entry_stage != runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER:
                return
            for stage in (
                runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
                runtime.DIAGNOSTIC_STAGE_RNG,
            ):
                self._send(
                    peer,
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(stage, 0),
                )
            self._send(peer, runtime.FRAME_CHALLENGE, 0, nonce)
            auth = self._receive_frame(peer)
            self.assertEqual(
                auth.payload,
                observer.compute_open_tag(TEST_KEY, runtime.P334_RUN_ID, nonce),
            )
            self._send(
                peer,
                runtime.FRAME_READY,
                1,
                observer.compute_ready_tag(TEST_KEY, runtime.P334_RUN_ID, nonce),
            )
            for sequence, command in enumerate(runtime.DEFAULT_COMMANDS, start=2):
                request = self._receive_frame(peer)
                self.assertEqual(request.frame_type, runtime.FRAME_EXEC)
                self.assertEqual(request.sequence, sequence)
                self.assertEqual(request.payload[32:], command)
                if sequence == 2:
                    output = b"uid=0(root) gid=0(root)\n"
                elif sequence == 3:
                    output = b"Linux p334 5.10.198 aarch64 GNU/Linux\n"
                else:
                    output = f"P328-NONCE {runtime.P334_RUN_ID_HEX}\n".encode()
                self._send(peer, runtime.FRAME_DATA, sequence, output)
                self._send(
                    peer,
                    runtime.FRAME_EXIT,
                    sequence,
                    observer.EXIT.pack(0, 0, 0, len(output), 1),
                )
            close_sequence = len(runtime.DEFAULT_COMMANDS) + 2
            closed = self._receive_frame(peer)
            self.assertEqual(closed.frame_type, runtime.FRAME_CLOSE)
            self._send(
                peer,
                runtime.FRAME_DONE,
                close_sequence,
                observer.DONE.pack(len(runtime.DEFAULT_COMMANDS)),
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def test_two_sessions_require_entry_then_existing_diagnostics(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=lambda: [
                self._serve_session(peer, nonce, errors) for nonce in NONCES
            ]
        )
        thread.start()
        try:
            with mock.patch.object(
                observer._P333._P332, "_descriptor", wraps=observer._P333._P332._descriptor
            ) as descriptor:
                result = observer.exchange_resident(
                    host, TEST_KEY, timeout_sec=5
                )
                descriptor.assert_called_once_with(host)
            proof = observer.validate_resident_proof(result)
            self.assertEqual(result.session_count, 2)
            self.assertEqual(result.reconnect_count, 0)
            self.assertEqual(proof["schema"], observer.SCHEMA)
            self.assertEqual(proof["contract_id"], observer.CONTRACT_ID)
            self.assertEqual(
                [item["stage"] for item in proof["sessions"][0]["diagnostics"]],
                [0, 1, 2],
            )
            self.assertEqual(
                observer.validate_proof_value(
                    proof,
                    expected_auth_key_sha256=hashlib.sha256(TEST_KEY).hexdigest(),
                ),
                proof,
            )
            os.fstat(host.fileno())
        finally:
            host.close()
            thread.join(timeout=5)
            peer.close()
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)

    def test_missing_entry_diagnostic_fails_first_session_without_retry(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=self._serve_session,
            args=(peer, NONCES[0], errors),
            kwargs={"entry_stage": runtime.DIAGNOSTIC_STAGE_OPEN_PARSED},
        )
        thread.start()
        try:
            with self.assertRaises(observer.LogicalResidentObserverError) as raised:
                observer.exchange_resident(host, TEST_KEY, timeout_sec=2)
            result = raised.exception.result
            self.assertEqual(result.session_count, 1)
            self.assertEqual(result.successful_sessions, 0)
            self.assertEqual(result.reconnect_count, 0)
            self.assertEqual(result.sessions[0].failure_stage, "open-diagnostic-read")
        finally:
            host.close()
            thread.join(timeout=5)
            peer.close()
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)

    def test_serialized_proof_rejects_missing_or_reordered_entry_stage(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=lambda: [
                self._serve_session(peer, nonce, errors) for nonce in NONCES
            ]
        )
        thread.start()
        try:
            proof = observer.validate_resident_proof(
                observer.exchange_resident(host, TEST_KEY, timeout_sec=5)
            )
            for mutate in (
                lambda value: value["sessions"][0]["diagnostics"].pop(0),
                lambda value: value["sessions"][0]["diagnostics"].__setitem__(
                    0, {"stage": 2, "code": 0}
                ),
            ):
                changed = deepcopy(proof)
                mutate(changed)
                with self.assertRaises(observer.AuthObserverError):
                    observer.validate_proof_value(changed)
        finally:
            host.close()
            thread.join(timeout=5)
            peer.close()
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)

    def test_binding_retains_same_fd_and_fixed_commands(self) -> None:
        self.assertEqual(observer.MAX_SESSIONS, 2)
        self.assertEqual(observer.MAX_RECONNECTS, 0)
        self.assertEqual(observer.PHYSICAL_REOPEN_COUNT, 0)
        self.assertEqual(observer.DEFAULT_COMMANDS, runtime.DEFAULT_COMMANDS)
        self.assertEqual(observer.P334_RUN_ID, runtime.P334_RUN_ID)
        source = Path(observer.__file__).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "SamsungOdinBackend", "adb_client"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
