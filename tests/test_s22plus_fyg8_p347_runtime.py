"""P347 real-filter/C-supervisor regression; host-only, no namespace/USB claim."""
from pathlib import Path
import hashlib
import socket
import subprocess
import tempfile
import time
import unittest
from unittest import mock

import test_s22plus_fyg8_p346_sleep_diagnosis as fixture
import test_s22plus_fyg8_p345_readonly_child as child_tests
from test_s22plus_fyg8_p346_sleep_diagnosis import join
import s22plus_fyg8_p347_research_shell_runtime as runtime
import s22plus_fyg8_readonly_child_v2 as child


class P347RuntimeTests(unittest.TestCase):
    def test_child_actual_filter_and_arm64_compile(self):
        with mock.patch.object(child_tests, 'child', child):
            case = child_tests.P345ReadonlyChildTests()
            case.test_native_seccomp_filter_runs_busybox_and_rejects_write_open_flags()
            case.test_arm64_object_compiles_when_toolchain_is_available()
            case.test_all_declared_syscalls_match_aarch64_header()

    def test_real_filter_output_sleep_failure_cancel_timeout_and_next(self):
        fragment = child.child_source().decode()
        observer = join.live._open_header_initial_observer_module(
            runtime, join.live.p344_open_read_observer, 'p347-local-c-filter')
        cases = [
            ('/bin/busybox awk \'BEGIN {for(i=0;i<60000;i++) print "x"}\'', 'ok', b'x\n'*60000, False),
            ('/bin/busybox sleep 0.2; printf slept', 'ok', b'slept', False),
            ('/bin/busybox cat /nonexistent/p347-test | /bin/busybox wc -c', 'command-failed', None, False),
            ('v=$(/bin/busybox cat /nonexistent/p347-test) || exit 74; printf bad', 'command-failed', None, False),
            ('/bin/busybox awk \'BEGIN {for(i=0;i<80000;i++) print "x"}\'', 'truncated', b'x\n'*65536, False),
            ('exit 7', 'command-failed', b'', False),
            ('printf started; /bin/busybox sleep 30', 'cancelled', b'started', True),
            ('/bin/busybox sleep 30', 'timeout', b'', False),
            ('printf "%s" "$(printf next)" | /bin/busybox tr a-z A-Z', 'ok', b'NEXT', False),
        ]
        with tempfile.TemporaryDirectory(prefix='p347-runtime-') as directory:
            root = Path(directory); binary = root/'peer'
            build = subprocess.run(['cc', '-x', 'c', '-', '-O2', '-Wall', '-Wextra',
                '-Wno-unused-function', '-Wno-misleading-indentation',
                *fixture.host_definitions(fragment), '-o', str(binary)],
                input=fixture.filtered_source(fragment, runtime), text=True,
                capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            host, peer = socket.socketpair(); host.setblocking(False); peer.setblocking(False)
            process = subprocess.Popen([str(binary), str(peer.fileno()), str(len(cases))],
                pass_fds=(peer.fileno(),), stderr=subprocess.PIPE)
            peer.close()
            try:
                seen = set()
                for index, (command, wanted, expected, cancel) in enumerate(cases):
                    writer = join.raw.RawCaptureWriter(root, f'rx-{index}',
                        stdout_maximum=512*1024, stderr_maximum=4096)
                    started = time.monotonic()
                    result = join.exchange.exchange(observer, host.fileno(), b'k'*32,
                        command, hashlib.sha256(b'b'*32).hexdigest(), seen, writer,
                        deadline=started+22,
                        cancel_requested=lambda: cancel and time.monotonic()-started>.4)
                    self.assertEqual(result.outcome, wanted, (index, result.session.commands[1]))
                    self.assertTrue(result.session.audit.done_seen)
                    query = result.session.commands[1]
                    if expected is not None:
                        self.assertEqual(query.output, expected)
                    if index == 1:
                        self.assertGreaterEqual(query.duration_ms, 200)
                    if wanted == 'timeout':
                        self.assertGreaterEqual(query.duration_ms, 15000)
                    if index == 3:
                        self.assertEqual(query.exit_code, 74)
                        self.assertNotIn(b'bad', query.output)
                    receipt = writer.finalize(returncode=0)
                    self.assertEqual(join.raw.read_stdout(receipt, maximum=512*1024),
                                     bytes(result.session.audit.rx))
                self.assertEqual(process.wait(timeout=3), 0, process.stderr.read().decode())
            finally:
                host.close()
                if process.poll() is None: process.kill()
                process.wait(timeout=3); process.stderr.close()


    def test_real_five_session_qualification_and_raw_reopening(self):
        import s22plus_fyg8_p347_research_shell_observer as qualification
        fragment = child.child_source().decode()
        codec = join.live._open_header_initial_observer_module(
            runtime, join.live.p344_open_read_observer, 'p347-five-session-h0')
        with tempfile.TemporaryDirectory(prefix='p347-qualification-') as directory:
            root = Path(directory); binary = root/'peer'
            build = subprocess.run(['cc', '-x', 'c', '-', '-O2',
                *fixture.host_definitions(fragment), '-o', str(binary)],
                input=fixture.filtered_source(fragment, runtime), text=True,
                capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            host, peer = socket.socketpair(); host.setblocking(False); peer.setblocking(False)
            # Map only the host fixture's UID/GID. The real canary runs unchanged;
            # this tests neither the target mount setup nor target UID-drop code.
            process = subprocess.Popen(['unshare', '--user', '--map-user=65534',
                '--map-group=65534', str(binary), str(peer.fileno()), '5'],
                pass_fds=(peer.fileno(),), stderr=subprocess.PIPE)
            peer.close()
            try:
                writer = join.raw.RawCaptureWriter(root, 'qualification',
                    stdout_maximum=512*1024, stderr_maximum=4096)
                result = qualification.qualify(codec, host.fileno(), b'k'*32,
                    None, set(), writer, deadline=time.monotonic()+60)
                self.assertTrue(result.receipt['proved'])
                self.assertEqual(result.receipt['session_count'], 5)
                self.assertEqual(result.sessions[4].session.commands[1].output, qualification.PIPELINE_MARKER)
                receipt = writer.finalize(returncode=0)
                raw_bytes = join.raw.read_stdout(receipt, maximum=512*1024)
                self.assertEqual(raw_bytes, b''.join(bytes(s.session.audit.rx) for s in result.sessions))
                qualification.validate_qualification(result.receipt)
                for step, exchange_result in zip(qualification.QUALIFICATION_COMMANDS, result.sessions):
                    session = exchange_result.session
                    reopened = qualification.parse_captured_session(codec,
                        bytes(session.audit.rx), bytes(session.audit.tx), b'k'*32)
                    qualification.validate_session_result(reopened, step)
                self.assertEqual(process.wait(timeout=3), 0, process.stderr.read().decode())
            finally:
                host.close()
                if process.poll() is None: process.kill()
                process.wait(timeout=3); process.stderr.close()


if __name__ == '__main__': unittest.main()
