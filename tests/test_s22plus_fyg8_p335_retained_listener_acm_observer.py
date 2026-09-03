from __future__ import annotations

from copy import deepcopy
import hashlib
import socket
import sys
import threading
import unittest

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p335_retained_listener_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p335_retained_listener_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(runtime.AUTH_KEY_SIZE))
BOOT_ID = b"B" * runtime.P335_BOOT_ID_SIZE
NONCES = tuple(bytes([value]) * runtime.NONCE_SIZE for value in (65, 66, 67))


class P335RetainedListenerObserverTests(unittest.TestCase):
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
        return observer.decode_frame(
            header + self._receive_exact(peer, length)
        )

    @staticmethod
    def _send(
        peer: socket.socket, frame_type: int, sequence: int, payload: bytes
    ) -> None:
        peer.sendall(observer.encode_frame(frame_type, sequence, payload))

    def _serve_sessions(
        self,
        peer: socket.socket,
        nonces: tuple[bytes, ...],
        errors: list[BaseException],
        *,
        boot_ids: tuple[bytes, ...] | None = None,
        bad_boot_hmac_index: int | None = None,
    ) -> None:
        boot_values = boot_ids or tuple(BOOT_ID for _ in nonces)
        try:
            for index, nonce in enumerate(nonces):
                peer.sendall(runtime.DEVICE_BANNER)
                opened = self._receive_frame(peer)
                self.assertEqual(
                    opened,
                    observer.Frame(runtime.FRAME_OPEN, 0, runtime.P335_RUN_ID),
                )
                for stage in (
                    runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
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
                    observer.compute_open_tag(
                        TEST_KEY, runtime.P335_RUN_ID, nonce
                    ),
                )
                self._send(
                    peer,
                    runtime.FRAME_READY,
                    1,
                    observer.compute_ready_tag(
                        TEST_KEY, runtime.P335_RUN_ID, nonce
                    ),
                )
                boot_id = boot_values[index]
                tag = observer.compute_boot_id_tag(
                    TEST_KEY, runtime.P335_RUN_ID, nonce, boot_id
                )
                if index == bad_boot_hmac_index:
                    tag = bytes([tag[0] ^ 0x01]) + tag[1:]
                self._send(
                    peer,
                    runtime.P335_FRAME_BOOT_ID,
                    runtime.P335_BOOT_ID_SEQUENCE,
                    boot_id + tag,
                )
                if index == bad_boot_hmac_index:
                    peer.settimeout(1)
                    try:
                        self.assertEqual(peer.recv(1), b"")
                    except (ConnectionResetError, BrokenPipeError):
                        pass
                    return
                if boot_id != BOOT_ID:
                    peer.settimeout(1)
                    try:
                        self.assertEqual(peer.recv(1), b"")
                    except (ConnectionResetError, BrokenPipeError):
                        pass
                    return
                for sequence, command in enumerate(
                    runtime.DEFAULT_COMMANDS, start=3
                ):
                    request = self._receive_frame(peer)
                    self.assertEqual(request.frame_type, runtime.FRAME_EXEC)
                    self.assertEqual(request.sequence, sequence)
                    self.assertEqual(request.payload[32:], command)
                    self.assertEqual(
                        request.payload[:32],
                        observer.compute_exec_tag(
                            TEST_KEY,
                            runtime.P335_RUN_ID,
                            nonce,
                            sequence,
                            command,
                        ),
                    )
                    output = (
                        b"uid=0(root) gid=0(root)\n"
                        if sequence == 3
                        else b"Linux p335 5.10.198 aarch64 GNU/Linux\n"
                        if sequence == 4
                        else f"P328-NONCE {runtime.P335_RUN_ID_HEX}\n".encode()
                    )
                    self._send(peer, runtime.FRAME_DATA, sequence, output)
                    self._send(
                        peer,
                        runtime.FRAME_EXIT,
                        sequence,
                        observer.EXIT.pack(0, 0, 0, len(output), 1),
                    )
                closed = self._receive_frame(peer)
                self.assertEqual(closed.frame_type, runtime.FRAME_CLOSE)
                self.assertEqual(closed.sequence, 6)
                self._send(
                    peer,
                    runtime.FRAME_DONE,
                    6,
                    observer.DONE.pack(len(runtime.DEFAULT_COMMANDS)),
                )
        except (ConnectionResetError, BrokenPipeError):
            if bad_boot_hmac_index is None:
                raise
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def _success_fixture(self) -> tuple[
        socket.socket,
        socket.socket,
        socket.socket,
        socket.socket,
        threading.Thread,
        threading.Thread,
        list[BaseException],
    ]:
        initial_host, initial_peer = socket.socketpair()
        reopened_host, reopened_peer = socket.socketpair()
        initial_host.setblocking(False)
        reopened_host.setblocking(False)
        errors: list[BaseException] = []
        initial_thread = threading.Thread(
            target=self._serve_sessions,
            args=(initial_peer, NONCES[:2], errors),
        )
        reopened_thread = threading.Thread(
            target=self._serve_sessions,
            args=(reopened_peer, NONCES[2:], errors),
        )
        initial_thread.start()
        reopened_thread.start()
        return (
            initial_host,
            reopened_host,
            initial_peer,
            reopened_peer,
            initial_thread,
            reopened_thread,
            errors,
        )

    def test_two_same_fd_sessions_then_one_physical_reopen(self) -> None:
        (
            initial_host,
            reopened_host,
            initial_peer,
            reopened_peer,
            initial_thread,
            reopened_thread,
            errors,
        ) = self._success_fixture()
        calls: list[int] = []
        try:
            result = observer.exchange_retained(
                initial_host,
                TEST_KEY,
                reopen=lambda: calls.append(1) or reopened_host,
                timeout_sec=5,
            )
            proof = observer.validate_retained_proof(result)
            self.assertTrue(result.complete)
            self.assertEqual(result.session_count, 3)
            self.assertEqual(result.reconnect_count, 1)
            self.assertEqual(result.physical_reopen_count, 1)
            self.assertTrue(result.same_initial_fd)
            self.assertTrue(result.same_boot_id)
            self.assertEqual(len(calls), 1)
            self.assertEqual(
                [item.physical_reopen_index for item in result.sessions], [0, 0, 1]
            )
            self.assertEqual(
                [
                    [item.sequence for item in session.result.commands]
                    for session in result.sessions
                ],
                [[3, 4, 5], [3, 4, 5], [3, 4, 5]],
            )
            self.assertEqual(
                [session.boot_id for session in result.sessions],
                [BOOT_ID, BOOT_ID, BOOT_ID],
            )
            self.assertTrue(proof["per_boot_identity_proof"])
            self.assertFalse(proof["listener_replays_commands"])
            self.assertTrue(
                observer.validate_proof_value(
                    proof,
                    expected_auth_key_sha256=hashlib.sha256(TEST_KEY).hexdigest(),
                )
                == proof
            )
            self.assertEqual(initial_host.fileno(), -1)
            self.assertEqual(reopened_host.fileno(), -1)
        finally:
            initial_host.close()
            reopened_host.close()
            initial_thread.join(timeout=5)
            reopened_thread.join(timeout=5)
            initial_peer.close()
            reopened_peer.close()
            self.assertFalse(initial_thread.is_alive())
            self.assertFalse(reopened_thread.is_alive())
        self.assertFalse(errors)

    def test_bad_boot_hmac_stops_before_any_command_and_retains_raw(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=self._serve_sessions,
            args=(peer, (NONCES[0],), errors),
            kwargs={"bad_boot_hmac_index": 0},
        )
        thread.start()
        try:
            with self.assertRaises(observer.RetainedListenerObserverError) as raised:
                observer.exchange_retained(
                    host,
                    TEST_KEY,
                    reopen=lambda: (_ for _ in ()).throw(
                        AssertionError("reopen must not run")
                    ),
                    timeout_sec=2,
                )
            failure = raised.exception
            self.assertEqual(failure.session_index, 0)
            self.assertEqual(failure.result.session_count, 1)
            self.assertFalse(failure.result.sessions[0].ok)
            self.assertTrue(failure.result.sessions[0].raw_rx)
            self.assertIsNone(failure.result.sessions[0].result)
        finally:
            host.close()
            thread.join(timeout=3)
            peer.close()
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)

    def test_changed_boot_identity_on_reopen_fails_before_replay(self) -> None:
        initial_host, initial_peer = socket.socketpair()
        reopened_host, reopened_peer = socket.socketpair()
        initial_host.setblocking(False)
        reopened_host.setblocking(False)
        errors: list[BaseException] = []
        initial_thread = threading.Thread(
            target=self._serve_sessions,
            args=(initial_peer, NONCES[:2], errors),
        )
        reopened_thread = threading.Thread(
            target=self._serve_sessions,
            args=(reopened_peer, (NONCES[2],), errors),
            kwargs={"boot_ids": (b"C" * runtime.P335_BOOT_ID_SIZE,)},
        )
        initial_thread.start()
        reopened_thread.start()
        try:
            with self.assertRaises(observer.RetainedListenerObserverError) as raised:
                observer.exchange_retained(
                    initial_host,
                    TEST_KEY,
                    reopen=lambda: reopened_host,
                    timeout_sec=5,
                )
            failure = raised.exception
            self.assertEqual(failure.session_index, 2)
            self.assertEqual(failure.result.session_count, 3)
            self.assertEqual(failure.result.successful_sessions, 2)
            self.assertEqual(failure.result.sessions[2].failure_stage, "boot-id-read")
            self.assertNotIn(
                observer.encode_frame(runtime.FRAME_EXEC, 3, b"replayed"),
                failure.result.sessions[2].raw_tx,
            )
        finally:
            initial_host.close()
            reopened_host.close()
            initial_thread.join(timeout=5)
            reopened_thread.join(timeout=5)
            initial_peer.close()
            reopened_peer.close()
        self.assertFalse(initial_thread.is_alive())
        self.assertFalse(reopened_thread.is_alive())
        self.assertFalse(errors)

    def test_serialized_proof_rejects_boot_or_command_mutation(self) -> None:
        fixture = self._success_fixture()
        (
            initial_host,
            reopened_host,
            initial_peer,
            reopened_peer,
            initial_thread,
            reopened_thread,
            errors,
        ) = fixture
        try:
            proof = observer.validate_retained_proof(
                observer.exchange_retained(
                    initial_host,
                    TEST_KEY,
                    reopen=lambda: reopened_host,
                    timeout_sec=5,
                )
            )
            changed = deepcopy(proof)
            changed["sessions"][2]["boot_id_sha256"] = "a" * 64
            with self.assertRaises(observer.AuthObserverError):
                observer.validate_proof_value(changed)
            changed = deepcopy(proof)
            changed["sessions"][1]["commands"][0]["sequence"] = 2
            with self.assertRaises(observer.AuthObserverError):
                observer.validate_proof_value(changed)
        finally:
            initial_host.close()
            reopened_host.close()
            initial_thread.join(timeout=5)
            reopened_thread.join(timeout=5)
            initial_peer.close()
            reopened_peer.close()
        self.assertFalse(errors)

    def test_binding_is_host_only_and_exact(self) -> None:
        self.assertEqual(observer.MAX_INITIAL_SESSIONS, 2)
        self.assertEqual(observer.MAX_SESSIONS, 3)
        self.assertEqual(observer.MAX_RECONNECTS, 1)
        self.assertEqual(observer.PHYSICAL_REOPEN_COUNT, 1)
        self.assertEqual(observer.DEFAULT_COMMANDS, runtime.DEFAULT_COMMANDS)
        self.assertEqual(observer.P335_RUN_ID, runtime.P335_RUN_ID)
        source = Path(observer.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "SamsungOdinBackend",
            "adb_client",
            "os.system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
