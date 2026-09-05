"""H0 real PTY/authenticated codec; virtual time, never USB or a live key."""
import copy
import inspect
import os
from pathlib import Path
import sys
import textwrap
import threading
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'workspace/public/src/scripts/revalidation'), str(ROOT / 'tests')]
import device_action_f1_live_v2 as live
import s22plus_fyg8_idle_reuse_probe as probe
import test_s22plus_fyg8_host_first_open as pty
import test_s22plus_fyg8_p335_retained_listener_acm_observer as fixture


class VirtualClock:
    def __init__(self):
        self.now = 0.0
        self.hook = None

    def clock(self):
        return self.now

    def pause(self, seconds):
        self.now += seconds
        if self.hook:
            hook, self.hook = self.hook, None
            hook()


class IdleReuseTests(unittest.TestCase):
    def exercise(self, *, idle_noise=False, idle_cut=False, bad_hmac=False, reopen_failure=False,
                 real_time=False, writer_failure=False):
        module = live._p341_initial_observer_module()
        clock = VirtualClock()
        receipts = probe.install(module) if real_time else probe.install(
            module, clock=clock.clock, pause=clock.pause)
        helper = fixture.P335RetainedListenerObserverTests()
        source = textwrap.dedent(inspect.getsource(helper._serve_sessions))
        old = '            peer.sendall(runtime.DEVICE_BANNER)\n            opened = self._receive_frame(peer)'
        self.assertEqual(source.count(old), 1)
        source = source.replace(old, '            opened = self._receive_frame(peer)\n            peer.sendall(runtime.DEVICE_BANNER)')
        scope = dict(fixture.__dict__, observer=module, runtime=module.runtime)
        exec(compile(source, '<idle-h0-peer>', 'exec'), scope)
        def receive_frame(peer):
            header = helper._receive_exact(peer, module.HEADER.size)
            length = module.HEADER.unpack(header)[3]
            return module.decode_frame(header + helper._receive_exact(peer, length))
        helper._receive_frame = receive_frame
        serve = types.MethodType(scope['_serve_sessions'], helper)
        pairs = [os.openpty(), os.openpty()]
        errors, threads, reopens = [], [], []
        peers = [pty.Peer(pair[0]) for pair in pairs]
        if real_time:
            for peer in peers:
                peer.timeout = probe.IDLE_SECONDS + 30
        if idle_noise:
            clock.hook = lambda: os.write(pairs[0][0], b'unexpected-idle-bytes')
        if idle_cut:
            def cut():
                raise OSError('synthetic idle observation interruption')
            clock.hook = cut
        initial_count = 2 if idle_noise or idle_cut else 3
        nonces = fixture.NONCES + (b'D' * module.runtime.NONCE_SIZE,)
        captured = bytearray()
        def write(value):
            if writer_failure and value == b'unexpected-idle-bytes':
                raise OSError('synthetic raw writer failure')
            captured.extend(value)
        writer = types.SimpleNamespace(write_stdout=write)
        try:
            for _, slave in pairs:
                live.cdc_acm_observer.ObserverSession._raw_tty(None, slave)
                os.set_blocking(slave, False)
            for index, batch in enumerate((nonces[:initial_count], nonces[3:])):
                if index == 1 and (idle_noise or idle_cut or bad_hmac or reopen_failure):
                    continue
                thread = threading.Thread(target=serve, args=(peers[index], batch, errors),
                    kwargs={'bad_boot_hmac_index': 2 if bad_hmac and index == 0 else None})
                thread.start(); threads.append(thread)
            def reopen():
                reopens.append(True)
                if reopen_failure:
                    raise OSError('synthetic reopen failure')
                return pairs[1][1]
            if idle_noise or idle_cut or bad_hmac or reopen_failure:
                with self.assertRaises(module.RetainedListenerObserverError) as caught:
                    module.exchange_retained(pairs[0][1], fixture.TEST_KEY,
                                             reopen=reopen, timeout_sec=2, writer=writer)
                result = caught.exception.result
                with self.assertRaisesRegex(ValueError, 'already used'):
                    module.exchange_retained(pairs[0][1], fixture.TEST_KEY, reopen=reopen)
                for alias in ('exchange_resident', 'exchange_resident_sessions', 'exchange_commands'):
                    with self.assertRaisesRegex(ValueError, 'already used'):
                        getattr(module, alias)(pairs[0][1], fixture.TEST_KEY, reopen=reopen)
                self.assertEqual(len(reopens), 1 if reopen_failure else 0)
                self.assertEqual(result.successful_sessions, 3 if reopen_failure else 2)
                if idle_noise or idle_cut:
                    self.assertEqual(result.sessions[-1].raw_tx, b'')
                    self.assertEqual(result.sessions[-1].failure_stage, 'same-fd-idle')
                    self.assertFalse(receipts[0]['completed'])
                if idle_noise:
                    self.assertEqual(result.sessions[-1].raw_rx, b'unexpected-idle-bytes')
                    if not writer_failure:
                        self.assertTrue(captured.endswith(b'unexpected-idle-bytes'))
                return
            result = module.exchange_retained(pairs[0][1], fixture.TEST_KEY,
                                             reopen=reopen, timeout_sec=2, writer=writer)
            self.assertTrue(result.complete)
            proof = module.validate_retained_proof(result)
            self.assertEqual(module.validate_default_proof(result), proof)
            self.assertEqual(module.validate_resident_proof(result), proof)
            with self.assertRaisesRegex(ValueError, 'already used'):
                module.exchange_retained(pairs[0][1], fixture.TEST_KEY, reopen=reopen)
            module.validate_proof_value(proof)
            self.assertEqual(len(reopens), 1)
            self.assertEqual(proof['session_count'], 4)
            self.assertEqual(sum(len(s['commands']) for s in proof['sessions']), 12)
            self.assertEqual([s['physical_reopen_index'] for s in proof['sessions']], [0,0,0,1])
            elapsed = probe.validate_idle(receipts)['elapsed_seconds']
            self.assertGreaterEqual(elapsed, 120)
            if not real_time:
                self.assertEqual(elapsed, 120)
            for session in result.sessions:
                opened = module.encode_frame(module.runtime.FRAME_OPEN, 0, module.runtime.P335_RUN_ID)
                self.assertEqual(session.raw_tx.count(opened), 1)
            for index in (2, 3):
                changed = copy.deepcopy(proof)
                changed['sessions'][index]['physical_reopen_index'] ^= 1
                with self.assertRaises(module.AuthObserverError):
                    module.validate_proof_value(changed)
            # The consumed three-session P341 grammar is not silently widened.
            with self.assertRaises(live._P341_INITIAL_OBSERVER.AuthObserverError):
                live._P341_INITIAL_OBSERVER.validate_proof_value(proof)
        finally:
            for _, slave in pairs:
                pty.close(slave)
            for thread in threads:
                thread.join(3)
            for master, _ in pairs:
                pty.close(master)
            self.assertFalse(any(t.is_alive() for t in threads))
            self.assertFalse(errors)

    def test_four_sessions_idle_and_serialized_proof(self):
        self.exercise()

    def test_idle_noise_retained_without_next_open(self):
        self.exercise(idle_noise=True)

    def test_idle_interruption_no_replay(self):
        self.exercise(idle_cut=True)

    def test_idle_writer_failure_keeps_partial_rx_in_result(self):
        self.exercise(idle_noise=True, writer_failure=True)

    def test_post_idle_bad_auth_stops_before_reopen(self):
        self.exercise(bad_hmac=True)

    def test_reopen_failure_is_not_retried(self):
        self.exercise(reopen_failure=True)

    def test_short_idle_cannot_claim_success(self):
        with self.assertRaises(ValueError):
            probe.validate_idle([dict(phase='same-fd-idle', before_session_index=2,
                requested_seconds=120, elapsed_seconds=119.9, same_descriptor=True,
                completed=True, received_bytes=0)])

    def test_private_install_does_not_mutate_live_codec(self):
        before = (live._P341_INITIAL_OBSERVER.MAX_INITIAL_SESSIONS,
                  live._P341_INITIAL_OBSERVER.MAX_SESSIONS)
        private = live._p341_initial_observer_module()
        probe.install(private)
        with self.assertRaises(ValueError):
            probe.install(private)
        self.assertEqual(before, (2,3))
        self.assertEqual((live._P341_INITIAL_OBSERVER.MAX_INITIAL_SESSIONS,
                          live._P341_INITIAL_OBSERVER.MAX_SESSIONS), before)

    def test_changed_exchange_budget_rejected_before_install(self):
        module = live._p341_initial_observer_module()
        module.SESSION_TIMEOUT_SEC = 31
        with self.assertRaisesRegex(ValueError, 'budget'):
            probe.install(module)
        self.assertEqual((module.MAX_INITIAL_SESSIONS, module.MAX_SESSIONS), (2,3))
