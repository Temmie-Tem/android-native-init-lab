"""P383 generated C plus fixed-health observer; hardware facts are fixtures."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from unittest import mock

import test_s22plus_fyg8_p375_console_integration as base
import device_action_f1_live_v2 as live
import s22plus_fyg8_p383_research_shell_runtime as runtime
import s22plus_fyg8_p383_research_shell_observer as observer
import s22plus_fyg8_p383_console_owner as plan_owner


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.binary = cls.folder/'native'
        with mock.patch.object(base, 'runtime', runtime):
            source = base.source().replace('p375', 'p383')
        source = source.replace('const char*u="01234567-89ab-4cde-8fab-0123456789ab\\n";', 'const char*u=getenv("NB1_UUID");if(!u)u="01234567-89ab-4cde-8fab-0123456789ab\\n";')
        source = source.replace('const char *command=text;', r'''const char *command=text;
 if(strstr(command,"NB1"))command=fx_case("bad-health")?"printf BAD":
 "printf 'NB1\\n0\\n0\\n1\\nMOUNTS\\nCOMPLETE\\000OUT\\n'; printf 'COMPLETE\\000ERR\\n' >&2";''')
        result = subprocess.run(['cc', '-x', 'c', '-', '-O2', '-Wall', '-Wextra',
            '-Werror', '-Wno-unused-function', '-Wno-unused-const-variable',
            '-Wno-misleading-indentation', '-o', str(cls.binary)],
            input=source, text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.codec = live._open_header_initial_observer_module(runtime, observer, 'p383-health-h0')

    def exercise(self, case='normal', before_control=None):
        directory = self.folder/str(time.monotonic_ns())
        directory.mkdir()
        host, peer = socket.socketpair()
        host.setblocking(False); peer.setblocking(False)
        process = subprocess.Popen([str(self.binary), str(peer.fileno()), '1'],
            pass_fds=(peer.fileno(),), env=dict(os.environ, P364_CASE=case,
            P364_MARK=str(directory/'marks'), RC1_WORK=str(directory)),
            stderr=subprocess.PIPE, start_new_session=True)
        peer.close()
        raw = bytearray()
        writer = type('Writer', (), {'write_stdout': lambda _, data: raw.extend(data)})()
        intents = []
        result = error = None
        try:
            try:
                result = observer.qualify(self.codec, host.fileno(), b'k'*32, None,
                    set(), writer, deadline=time.monotonic()+5,
                    before_control=before_control or intents.append,
                    evidence=directory/'console')
            except observer.QualificationError as exc:
                error = exc
            return result, error, intents, bytes(raw)
        finally:
            host.close()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=3)

    def test_fixed_health_and_raw_consumer(self):
        result, error, intents, raw = self.exercise()
        if error:
            raise AssertionError(repr(error.__cause__))
        self.assertEqual(result.receipt['qualified_command_count'], 1)
        self.assertEqual(len(intents), 1)
        audit = result.sessions[0].session.audit
        self.assertEqual(raw, audit.rx)
        self.assertEqual(observer.replay_session(self.codec, raw, bytes(audit.tx), b'k'*32),
                         result.receipt)

    def test_failed_health_never_requests_control(self):
        result, error, intents, raw = self.exercise('bad-health')
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertEqual(intents, [])
        self.assertFalse(error.partial_receipt['proved'])
        self.assertTrue(raw)

    def test_freshness_rejection_preserves_raw_without_control(self):
        def reject(request):
            raise ValueError('same kernel boot')
        result, error, _, raw = self.exercise(before_control=reject)
        self.assertIsNone(result)
        self.assertIn('same kernel boot', str(error.__cause__))
        self.assertFalse(error.partial_receipt['control_acceptance_observed'])
        self.assertTrue(raw)

    def test_nonempty_plan_rejected_before_owner_open(self):
        with self.assertRaises(plan_owner.ConsolePlanError):
            plan_owner.validate(dict(schema=plan_owner.SCHEMA, commands=[{}]))


if __name__ == '__main__':
    unittest.main()
