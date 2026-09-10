"""Real generated auth/console C, fork/pipes and raw replay with fixture hardware.

UUID and root/mount command facts are explicit fixtures, not target ABI or live
health proof. The unchanged C producer supplies the authenticated wire bytes.
"""
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest

import test_s22plus_fyg8_p375_console_integration as base
import device_action_f1_live_v2 as live
import s22plus_fyg8_p375_research_shell_observer as observer
import s22plus_fyg8_p375_research_shell_runtime as runtime
import s22plus_native_baseline_health_v1 as health
import s22plus_root_console_v1 as wire

KEY = b'k'*32
UUID1 = '01234567-89ab-4cde-8fab-0123456789ab\n'
UUID2 = '11234567-89ab-4cde-8fab-0123456789ab\n'


class HealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.binary = cls.folder/'native'
        source = base.source().replace(
            'const char*u="01234567-89ab-4cde-8fab-0123456789ab\\n";',
            'const char*u=getenv("NB1_UUID");')
        source = source.replace('const char *command=text;', r'''const char *command=text;
 if(strstr(command,"NB1"))command=fx_case("bad-health")?"printf BAD":
 "printf 'NB1\\n0\\n0\\n1\\nMOUNTS\\nCOMPLETE\\000OUT\\n'; printf 'COMPLETE\\000ERR\\n' >&2";''')
        result = subprocess.run(['cc', '-x', 'c', '-', '-O2', '-Wall', '-Wextra',
            '-Werror', '-Wno-unused-function', '-Wno-unused-const-variable',
            '-Wno-misleading-indentation', '-o', str(cls.binary)],
            input=source, text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.codec = live._open_header_initial_observer_module(runtime, observer, 'nb1-h0')

    def capture(self, uuid=UUID1, case='normal'):
        directory = self.folder/str(time.monotonic_ns())
        directory.mkdir()
        host, peer = socket.socketpair()
        host.setblocking(False); peer.setblocking(False)
        process = subprocess.Popen([str(self.binary), str(peer.fileno()), '1'],
            pass_fds=(peer.fileno(),), env=dict(os.environ, NB1_UUID=uuid,
            P364_CASE=case, P364_MARK=str(directory/'marks'), RC1_WORK=str(directory)),
            stderr=subprocess.PIPE, start_new_session=True)
        peer.close()
        raw = bytearray()
        writer = type('Writer', (), {'write_stdout': lambda _, data: raw.extend(data)})()
        io = observer.IO(self.codec, KEY, fd=host.fileno(), writer=writer,
                         deadline=time.monotonic()+10)
        session = None
        try:
            io.handshake()
            session = wire.Session(host.fileno(), KEY, observer.RUN_ID, io.audit.nonce,
                directory/'console', on_rx=io.capture, on_tx=io.audit.tx.extend)
            events = []
            health.run_console_checks(session, events, deadline=time.monotonic()+10)
            sequence = session.send(wire.CONTROL)
            until = time.monotonic()+5
            while not any((k, n) == (wire.CONTROL_ACK, sequence) for k, n, _ in events):
                if time.monotonic() > until:
                    self.fail('fixture CONTROL timeout')
                events.extend(session.poll()); time.sleep(.001)
            self.assertEqual(process.wait(timeout=3), 0)
            self.assertEqual(raw, io.audit.rx)
            return bytes(io.audit.rx), bytes(io.audit.tx)
        finally:
            if session is not None:
                session.close()
            host.close()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=3)

    def replay(self, raw, arrival=1, previous=None):
        return health.replay(observer, self.codec, *raw, KEY,
                             arrival=arrival, previous=previous)

    def test_two_fresh_authenticated_arrivals(self):
        first = self.replay(self.capture())
        second = self.replay(self.capture(UUID2), 2, first)
        self.assertTrue(second['console_healthy'])
        self.assertFalse(second['download_arrival_proved'])
        self.assertNotEqual(first['kernel_boot_identity_sha256'], second['kernel_boot_identity_sha256'])

    def test_new_challenge_on_same_kernel_boot_is_not_new_arrival(self):
        first = self.replay(self.capture())
        raw = self.capture()
        self.assertNotEqual(first['nonce_sha256'], self.replay(raw)['nonce_sha256'])
        with self.assertRaisesRegex(ValueError, 'freshness'):
            self.replay(raw, 2, first)

    def test_authenticated_wrong_health_stops_without_control(self):
        with self.assertRaisesRegex(ValueError, 'unproved'):
            self.capture(case='bad-health')

    def test_tampered_truncated_and_replayed_session_rejected(self):
        rx, tx = self.capture()
        first = self.replay((rx, tx))
        with self.assertRaises(ValueError):
            self.replay((rx, tx), 2, first)
        for bad_rx, bad_tx in ((rx[:-1], tx), (rx, tx[:-1]), (rx[:-1]+bytes([rx[-1]^1]), tx)):
            with self.subTest(rx_size=len(bad_rx), tx_size=len(bad_tx)):
                with self.assertRaises(ValueError):
                    self.replay((bad_rx, bad_tx))

    def test_status_before_terminal_is_not_post_command_health(self):
        raw = self.capture()
        io = observer.IO(self.codec, KEY, rx=raw[0], tx=raw[1]); io.handshake()
        state, events = wire.replay(KEY, observer.RUN_ID, io.audit.nonce,
                                    raw[0][io.rpos:], raw[1][io.tpos:])
        status = next(event for event in events if event[0] == wire.STATUS_REPLY)
        events.remove(status); events.insert(0, status)
        with self.assertRaisesRegex(ValueError, 'precedes'):
            health.validate_console(state, events)


if __name__ == '__main__':
    unittest.main()
