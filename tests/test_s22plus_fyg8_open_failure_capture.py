"""Exercise the actual initial exchange, including the P339 receive cut.

Only the device is simulated by a local socket peer. The session reader,
raw sink, parser, exception path and connection close are real host code.
No connected device, firmware execution or private authentication key is used.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
sys.path.insert(0, str(ROOT / "tests"))

import device_action_f1_live_v2 as live
import s22plus_fyg8_open_failure_capture as capture
import s22plus_fyg8_p339_open_read_branch_acm_observer as parser
import test_s22plus_fyg8_p335_retained_listener_acm_observer as success_fixture


class RawSink:
    def __init__(self):
        self.payload = bytearray()

    def write_stdout(self, chunk):
        self.payload.extend(chunk)


class OpenFailureCaptureTests(unittest.TestCase):
    def _module(self):
        return live._p339_initial_observer_module()

    @staticmethod
    def _diag(module, stage, code):
        return module.encode_frame(
            module.runtime.DIAGNOSTIC_FRAME_TYPE, 0,
            module.DIAGNOSTIC.pack(stage, code),
        )

    def _suffix(self, module, header):
        return b"".join(
            self._diag(module, stage, int.from_bytes(header[i:i+4], "little", signed=True))
            for stage, i in zip((4, 5, 6, 7), range(0, 16, 4))
        )

    def _run(self, suffix=b"", *, branch=1, patched=True, silent=False):
        module = self._module()
        original_codec = module._CODEC
        if patched:
            capture.install(module)
            self.assertIsNot(module._CODEC, original_codec)
            self.assertFalse(getattr(original_codec, "_open_failure_capture_installed", False))
        prefix = module.DEVICE_BANNER + self._diag(module, 0, 0) + self._diag(module, 3, branch)
        host, peer = socket.socketpair()
        host.setblocking(False)
        peer.settimeout(1)
        released = threading.Event()
        sent = []
        errors = []

        def serve():
            try:
                peer.sendall(prefix + suffix)
                request = bytearray()
                while len(request) < 32:
                    chunk = peer.recv(32 - len(request))
                    if not chunk:
                        break
                    request.extend(chunk)
                sent.append(bytes(request))
                if silent:
                    released.wait(2)
                else:
                    peer.close()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=serve)
        sink = RawSink()
        thread.start()
        start = time.monotonic()
        try:
            with self.assertRaises(module.RetainedListenerObserverError) as raised:
                module.exchange_retained(
                    host, bytes(range(32)),
                    reopen=lambda: self.fail("failure must not reconnect"),
                    timeout_sec=0.15, writer=sink,
                )
            elapsed = time.monotonic() - start
        finally:
            released.set()
            host.close()
            thread.join(2)
            peer.close()
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        result = raised.exception.result
        self.assertFalse(result.complete)
        self.assertEqual(len(result.sessions), 1)
        session = result.sessions[0]
        self.assertFalse(session.authenticated)
        self.assertEqual(session.failure_stage, "open-diagnostic-read")
        self.assertEqual(bytes(sink.payload), session.raw_rx)
        expected_open = module.encode_frame(module.runtime.FRAME_OPEN, 0, module.runtime.P335_RUN_ID)
        self.assertEqual(session.raw_tx, expected_open)
        self.assertEqual(sent, [expected_open])
        return session, elapsed

    def test_original_initial_path_stops_at_exact_retained_p339_97_bytes(self):
        module = self._module()
        suffix = self._suffix(module, b"BAD!" + bytes(range(12)))
        session, _ = self._run(suffix, patched=False)
        self.assertEqual(len(session.raw_rx), 97)
        self.assertEqual(hashlib.sha256(session.raw_rx).hexdigest(),
                         "4724b51f7d04cd2bcfa0efe03c8ee78a3304cc68def41fa44f32c56694739d8c")

    def test_complete_grammar_and_semantic_headers_survive_real_exchange(self):
        module = self._module()
        rejected = b"BAD!" + bytes(range(12))
        for branch in (1, 4):
            with self.subTest(branch=branch):
                session, _ = self._run(self._suffix(module, rejected), branch=branch)
                self.assertEqual(len(session.raw_rx), 193)
                value = parser.parse_retained_open_read_branch(session.raw_rx)
                self.assertTrue(value["header_snapshot_complete"])
                self.assertEqual(value["header_snapshot_hex"], rejected.hex())

    def test_partial_header_is_retained_on_eof(self):
        module = self._module()
        suffix = self._suffix(module, b"BAD!" + bytes(range(12)))
        for cut in (0, 24, 48, 72, 85):
            with self.subTest(cut=cut):
                session, _ = self._run(suffix[:cut])
                self.assertEqual(session.raw_rx[97:], suffix[:cut])

    def test_silent_tail_uses_original_deadline(self):
        session, elapsed = self._run(silent=True)
        self.assertEqual(len(session.raw_rx), 97)
        self.assertLess(elapsed, 0.8)

    def test_oversized_or_bad_crc_or_out_of_order_tail_is_bounded(self):
        module = self._module()
        oversized = module.HEADER.pack(module.runtime.FRAME_MAGIC, 1, 0x86, 1024, 0, 0)
        bad_crc = bytearray(self._diag(module, 4, 0))
        bad_crc[-1] ^= 1
        for suffix, amount in ((oversized + b"x" * 200, 16),
                               (bytes(bad_crc) + self._diag(module, 5, 0), 24),
                               (self._diag(module, 5, 0), 24)):
            with self.subTest(amount=amount):
                session, _ = self._run(suffix)
                self.assertEqual(len(session.raw_rx), 97 + amount)

    def test_other_branches_do_not_read_a_suffix_and_no_fifth_word_is_read(self):
        module = self._module()
        suffix = self._suffix(module, b"BAD!" + bytes(range(12)))
        for branch in (0, 2, 3):
            session, _ = self._run(suffix, branch=branch)
            self.assertEqual(len(session.raw_rx), 97)
        session, _ = self._run(suffix + self._diag(module, 8, 0))
        self.assertEqual(len(session.raw_rx), 193)

    def test_three_authenticated_success_sessions_still_pass(self):
        module = self._module()
        capture.install(module)
        fixture = success_fixture.P335RetainedListenerObserverTests()
        with mock.patch.object(success_fixture, "observer", module), \
             mock.patch.object(success_fixture, "runtime", module.runtime):
            fixture.test_two_same_fd_sessions_then_one_physical_reopen()


if __name__ == "__main__":
    unittest.main()
