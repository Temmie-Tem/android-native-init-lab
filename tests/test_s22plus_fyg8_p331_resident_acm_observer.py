from __future__ import annotations

from pathlib import Path
import socket
import sys
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p331_resident_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p331_resident_exec_runtime as runtime  # noqa: E402


TEST_KEY = bytes(range(32))
NONCES = (bytes([0xA5]) * runtime.NONCE_SIZE, bytes([0x5A]) * runtime.NONCE_SIZE)


class P331ResidentObserverTests(unittest.TestCase):
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
    def _send(peer: socket.socket, frame_type: int, sequence: int, payload: bytes) -> None:
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
            self.assertEqual(
                self._receive_frame(peer),
                observer.Frame(runtime.FRAME_OPEN, 0, runtime.P331_RUN_ID),
            )
            self._send(
                peer,
                runtime.DIAGNOSTIC_FRAME_TYPE,
                0,
                observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0),
            )
            self._send(
                peer,
                runtime.DIAGNOSTIC_FRAME_TYPE,
                0,
                observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_RNG, 0),
            )
            self._send(peer, runtime.FRAME_CHALLENGE, 0, nonce)
            auth = self._receive_frame(peer)
            self.assertEqual(
                auth.payload,
                observer.compute_open_tag(TEST_KEY, runtime.P331_RUN_ID, nonce),
            )
            self._send(
                peer,
                runtime.FRAME_READY,
                1,
                observer.compute_ready_tag(TEST_KEY, runtime.P331_RUN_ID, nonce),
            )
            request = self._receive_frame(peer)
            self.assertEqual(request.frame_type, runtime.FRAME_EXEC)
            self.assertEqual(request.sequence, 2)
            self.assertEqual(request.payload[32:], runtime.HEARTBEAT_COMMAND)
            self.assertEqual(
                request.payload[:32],
                observer.compute_exec_tag(
                    TEST_KEY,
                    runtime.P331_RUN_ID,
                    nonce,
                    2,
                    runtime.HEARTBEAT_COMMAND,
                ),
            )
            self._send(peer, runtime.FRAME_DATA, 2, runtime.HEARTBEAT_OUTPUT)
            self._send(
                peer,
                runtime.FRAME_EXIT,
                2,
                observer.EXIT.pack(0, exit_code, 0, len(runtime.HEARTBEAT_OUTPUT), 1),
            )
            closed = self._receive_frame(peer)
            self.assertEqual(closed.frame_type, runtime.FRAME_CLOSE)
            self._send(peer, runtime.FRAME_DONE, closed.sequence, observer.DONE.pack(1))
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def test_two_authenticated_sessions_reconnect_after_clean_close(self) -> None:
        hosts: list[socket.socket] = []
        peers: list[socket.socket] = []
        threads: list[threading.Thread] = []
        errors: list[BaseException] = []
        for nonce in NONCES:
            host, peer = socket.socketpair()
            host.setblocking(False)
            hosts.append(host)
            peers.append(peer)
            thread = threading.Thread(
                target=self._serve_success,
                args=(peer, nonce, errors),
            )
            thread.start()
            threads.append(thread)
        try:
            result = observer.exchange_resident(hosts, TEST_KEY, timeout_sec=5)
        finally:
            for host in hosts:
                host.close()
            for thread in threads:
                thread.join(timeout=5)
            for peer in peers:
                peer.close()
        self.assertFalse(errors)
        self.assertTrue(result.complete)
        self.assertEqual(result.session_count, 2)
        self.assertEqual(result.reconnect_count, 1)
        self.assertEqual(
            [session.nonce for session in result.sessions], list(NONCES)
        )
        self.assertTrue(all(session.raw_tx and session.raw_rx for session in result.sessions))
        proof = observer.validate_resident_proof(result)
        self.assertTrue(proof["resident_loop_proof"])
        self.assertFalse(proof["caller_selected_command"])
        self.assertEqual(proof["banner_attempts"], 2)
        self.assertEqual(proof["banner_scope"], "resident_loop_per_session")
        self.assertTrue(all(session.audit.banner_seen for session in result.sessions))

    def test_nonzero_exit_cannot_satisfy_resident_proof(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=self._serve_success,
            args=(peer, NONCES[0], errors, 7),
        )
        thread.start()
        try:
            result = observer.exchange_resident(
                [host], TEST_KEY, timeout_sec=5, max_sessions=1
            )
        finally:
            host.close()
            thread.join(timeout=5)
            peer.close()
        self.assertFalse(errors)
        self.assertEqual(result.session_count, 1)
        self.assertTrue(result.sessions[0].authenticated)
        self.assertTrue(result.sessions[0].clean_close)
        with self.assertRaises(observer.ResidentObserverError) as raised:
            observer.validate_resident_proof(result)
        self.assertEqual(raised.exception.session_index, 0)

    def test_replayed_challenge_is_rejected_before_second_auth_and_raw_is_kept(self) -> None:
        first_host, first_peer = socket.socketpair()
        second_host, second_peer = socket.socketpair()
        first_host.setblocking(False)
        second_host.setblocking(False)
        errors: list[BaseException] = []
        first_thread = threading.Thread(
            target=self._serve_success,
            args=(first_peer, NONCES[0], errors),
        )
        first_thread.start()

        def replay_peer() -> None:
            try:
                second_peer.sendall(runtime.DEVICE_BANNER)
                opened = self._receive_frame(second_peer)
                self.assertEqual(opened.frame_type, runtime.FRAME_OPEN)
                self._send(
                    second_peer,
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, 0),
                )
                self._send(
                    second_peer,
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(runtime.DIAGNOSTIC_STAGE_RNG, 0),
                )
                self._send(second_peer, runtime.FRAME_CHALLENGE, 0, NONCES[0])
                second_peer.settimeout(1)
                self.assertEqual(second_peer.recv(1), b"")
            except (OSError, AssertionError) as exc:
                if isinstance(exc, AssertionError):
                    errors.append(exc)

        second_thread = threading.Thread(target=replay_peer)
        second_thread.start()
        try:
            with self.assertRaises(observer.ResidentObserverError) as raised:
                observer.exchange_resident(
                    [first_host, second_host], TEST_KEY, timeout_sec=5
                )
        finally:
            first_host.close()
            second_host.close()
            first_thread.join(timeout=5)
            second_thread.join(timeout=5)
            first_peer.close()
            second_peer.close()
        self.assertFalse(errors)
        failure = raised.exception
        self.assertEqual(failure.session_index, 1)
        self.assertEqual(failure.result.sessions[1].error_type, "AuthObserverError")
        self.assertIn(runtime.DEVICE_BANNER, failure.result.sessions[1].raw_rx)
        self.assertIn(observer.encode_frame(runtime.FRAME_OPEN, 0, runtime.P331_RUN_ID), failure.result.sessions[1].raw_tx)

    def test_reconnect_cap_and_timeout_stop_without_replay(self) -> None:
        host, peer = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []
        thread = threading.Thread(
            target=self._serve_success,
            args=(peer, NONCES[0], errors),
        )
        thread.start()
        try:
            result = observer.exchange_resident(
                [host],
                TEST_KEY,
                timeout_sec=5,
                max_reconnects=0,
            )
        finally:
            host.close()
            thread.join(timeout=5)
            peer.close()
        self.assertFalse(errors)
        self.assertEqual(result.terminal, "reconnect-cap")
        self.assertEqual(result.session_count, 1)
        self.assertEqual(result.reconnect_count, 0)

        timeout_host, timeout_peer = socket.socketpair()
        timeout_host.setblocking(False)

        def stall() -> None:
            try:
                timeout_peer.sendall(runtime.DEVICE_BANNER)
                self._receive_frame(timeout_peer)
                timeout_peer.settimeout(1)
                self.assertEqual(timeout_peer.recv(1), b"")
            except (OSError, AssertionError) as exc:
                if isinstance(exc, AssertionError):
                    errors.append(exc)

        timeout_thread = threading.Thread(target=stall)
        timeout_thread.start()
        try:
            with self.assertRaises(observer.ResidentObserverError) as raised:
                observer.exchange_resident(
                    [timeout_host], TEST_KEY, timeout_sec=0.05, max_sessions=1
                )
        finally:
            timeout_host.close()
            timeout_thread.join(timeout=2)
            timeout_peer.close()
        self.assertFalse(errors)
        session = raised.exception.result.sessions[0]
        self.assertEqual(session.error_type, "AuthObserverError")
        self.assertIn(runtime.DEVICE_BANNER, session.raw_rx)
        self.assertIn(
            observer.encode_frame(runtime.FRAME_OPEN, 0, runtime.P331_RUN_ID),
            session.raw_tx,
        )


if __name__ == "__main__":
    unittest.main()
