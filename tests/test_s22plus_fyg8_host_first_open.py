"""Dormant H0: real PTY line discipline, real three-session codec, C build.

No ADB, USB device, Odin, private authentication key or live registration.
"""
from pathlib import Path
import errno
import inspect
import os
import select
import shutil
import subprocess
import sys
import tempfile
import termios
import threading
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'workspace/public/src/scripts/revalidation'), str(ROOT / 'tests')]
import device_action_f1_live_v2 as live
import s22plus_fyg8_host_first_open as change
import test_s22plus_fyg8_p335_retained_listener_acm_observer as fixture


class Peer:
    def __init__(self, fd):
        self.fd = fd
        self.received = bytearray()
        self.timeout = 2

    def settimeout(self, timeout):
        self.timeout = timeout

    def recv(self, size):
        if not select.select([self.fd], [], [], self.timeout)[0]:
            raise TimeoutError('local PTY peer')
        try:
            value = os.read(self.fd, size)
        except OSError as exc:
            if exc.errno != errno.EIO: raise
            value = b''  # PTY peer closed, equivalent to socket EOF.
        self.received.extend(value)
        return value

    def sendall(self, value):
        while value:
            value = value[os.write(self.fd, value):]


def close(fd):
    try:
        os.close(fd)
    except OSError as exc:
        if exc.errno != errno.EBADF:
            raise


def c_function(source, name):
    start = source.rfind('\nstatic ', 0, source.index(name + '(')) + 1
    brace = source.index('{', source.index(name, start))
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


class HostFirstTests(unittest.TestCase):
    def codec(self):
        module = live._p340_initial_observer_module()
        change.install_observer(module)
        return module

    def test_real_pty_reproduces_old_echo_but_prepared_start_has_none(self):
        banner = live._P340_INITIAL_OBSERVER.DEVICE_BANNER
        for prepared in (False, True):
            m, s = os.openpty()
            try:
                if prepared:
                    live.cdc_acm_observer.ObserverSession._raw_tty(None, s)
                os.write(m, banner)
                readable = select.select([m], [], [], 0.1)[0]
                echo = os.read(m, 256) if readable else b''
                self.assertEqual(echo[:16], b'' if prepared else b'S22PLUS-FYG8-E3:')
            finally:
                close(s); close(m)

    def test_nonraw_tty_rejects_before_any_open_tx(self):
        module = self.codec()
        m, s = os.openpty()
        try:
            with self.assertRaises(module.RetainedListenerObserverError) as caught:
                module.exchange_retained(s, fixture.TEST_KEY, reopen=lambda: self.fail('reopen'), timeout_sec=1)
            self.assertEqual(caught.exception.result.sessions[0].raw_tx, b'')
        finally:
            close(s); close(m)

    def test_three_real_pty_sessions_and_bad_hmac(self):
        # Reuse the full existing authenticated device fixture, moving only
        # its banner to after the single OPEN. This is not device C execution.
        for bad_hmac in (False, True):
            module = self.codec()
            text = inspect.getsource(fixture.P335RetainedListenerObserverTests._serve_sessions)
            import textwrap
            text = textwrap.dedent(text)
            old = '            peer.sendall(runtime.DEVICE_BANNER)\n            opened = self._receive_frame(peer)'
            self.assertEqual(text.count(old), 1)
            text = text.replace(old, '            opened = self._receive_frame(peer)\n            peer.sendall(runtime.DEVICE_BANNER)', 1)
            scope = dict(fixture.__dict__, observer=module, runtime=module.runtime)
            exec(compile(text, '<host-first-peer>', 'exec'), scope)
            helper = fixture.P335RetainedListenerObserverTests()
            def receive_frame(peer):
                header = helper._receive_exact(peer, module.HEADER.size)
                length = module.HEADER.unpack(header)[3]
                return module.decode_frame(header + helper._receive_exact(peer, length))
            helper._receive_frame = receive_frame
            serve = types.MethodType(scope['_serve_sessions'], helper)
            pairs = [os.openpty(), os.openpty()]
            errors = []
            threads = []
            try:
                for _, slave in pairs:
                    live.cdc_acm_observer.ObserverSession._raw_tty(None, slave)
                    os.set_blocking(slave, False)
                for index, nonces in enumerate((fixture.NONCES[:2], fixture.NONCES[2:])):
                    if bad_hmac and index == 1:
                        continue
                    thread = threading.Thread(target=serve, args=(Peer(pairs[index][0]), nonces, errors),
                        kwargs={'bad_boot_hmac_index': 0 if bad_hmac else None})
                    thread.start(); threads.append(thread)
                if bad_hmac:
                    with self.assertRaises(module.RetainedListenerObserverError):
                        module.exchange_retained(pairs[0][1], fixture.TEST_KEY,
                            reopen=lambda: self.fail('bad HMAC cannot reopen'), timeout_sec=5)
                else:
                    reopens = []
                    result = module.exchange_retained(pairs[0][1], fixture.TEST_KEY,
                        reopen=lambda: reopens.append(1) or pairs[1][1], timeout_sec=5)
                    self.assertTrue(result.complete)
                    self.assertEqual(len(result.sessions), 3)
                    self.assertEqual(reopens, [1])
                    for session in result.sessions:
                        expected = module.encode_frame(module.runtime.FRAME_OPEN, 0, module.runtime.P335_RUN_ID)
                        self.assertTrue(session.raw_tx.startswith(expected))
                        self.assertEqual(session.raw_tx.count(expected), 1)
            finally:
                for _, slave in pairs: close(slave)
                for thread in threads: thread.join(3)
                for master, _ in pairs: close(master)
            self.assertFalse(any(t.is_alive() for t in threads))
            self.assertFalse(errors)

    def test_c_runtime_compiles_aarch64_without_packaging(self):
        source = ROOT / 'workspace/private/outputs/s22plus_fyg8_p340/stock-candidate-build-v1-20260905-01/stock-sources'
        with tempfile.TemporaryDirectory(prefix='s22-host-first-h0-') as directory:
            out = Path(directory)
            for path in source.iterdir():
                if path.is_file(): shutil.copyfile(path, out / path.name)
            runtime = out / 's22plus_fyg8_p290_e3_runtime.inc.c'
            # Use only a public synthetic key in this test artifact.
            value = runtime.read_bytes()
            old_key = change.base.predecessor._materialized_key(value)
            original = change.base.materialize_helper(old_key)
            value = value.replace(original, change.base.materialize_helper(fixture.TEST_KEY), 1)
            value = change.transform_runtime_include(value, fixture.TEST_KEY)
            runtime.write_bytes(value)
            self.assertEqual(value.count(b's22plus_p318_banner_attempt(tty_fd);'),
                (source / runtime.name).read_bytes().count(b's22plus_p318_banner_attempt(tty_fd);') - 2)
            command = ['/usr/bin/aarch64-linux-gnu-gcc', '-c', '-ffreestanding', '-fno-builtin',
                '-Os', '-Wall', '-Wextra', '-Werror',
                '-DS22PLUS_FYG8_P233_PROFILE=3', '-I', directory,
                '-DS22PLUS_FYG8_P233_RUN_ID_BYTES={' + ','.join(str(x) for x in range(16)) + '}',
                '-I', str(ROOT / 'workspace/public/src/native-init'),
                str(out / 's22plus_fyg8_p290_e3_runtime.c'), '-o', str(out / 'runtime.o')]
            compiled = subprocess.run(command, capture_output=True, timeout=60)
            self.assertEqual(compiled.returncode, 0, compiled.stderr.decode())
            result = subprocess.check_output(['file', str(out / 'runtime.o')], text=True)
            self.assertIn('ARM aarch64', result)

    def test_actual_c_open_reader_silent_idle_partial_stop_and_valid_order(self):
        # Compile the actual changed C read/validation/preamble prefix on the
        # host. Only I/O/deadline/preamble sinks are fixtures; not the parser.
        text = change.helper(change.base.materialize_helper(fixture.TEST_KEY)).decode()
        names = ('p328_load_le16', 'p328_load_le32', 'p328_crc32_update',
            'p328_frame_crc', 'p341_read_exact', 'p328_read_exact', 'p328_read_frame',
            'p328_constant_time_equal')
        functions = '\n'.join(c_function(text, name) for name in names)
        console = c_function(text, 'p335_framed_console')
        console = console[:console.index('    uint32_t rng_retries =')] + '    return rc;\n}\n'
        module = live._P340_INITIAL_OBSERVER
        opened = module.encode_frame(module.runtime.FRAME_OPEN, 0, module.runtime.P335_RUN_ID)
        numbers = lambda data: ','.join(str(x) for x in data)
        definitions = '\n'.join(line for line in text.splitlines() if line.startswith('#define '))
        harness = r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#define P260_EINTR EINTR
#define P260_EPROTO EPROTO
#define S22PLUS_P318_BANNER_WRITTEN 1
struct timespec64 { long tv_sec, tv_nsec; };
struct s22plus_p318_banner_result { int outcome; };
static const uint8_t *input;
static size_t remaining;
static int writes, events[16];
static long p282_deadline_after(long seconds, struct timespec64 *deadline) { return 0; }
static int p282_deadline_expired(struct timespec64 *deadline) { return 1; }
static void p282_poll_delay(void) {}
static long sys_read(int fd, void *out, size_t n) {
    if (!remaining) return -EAGAIN;
    if (n > remaining) n = remaining;
    memcpy(out, input, n); input += n; remaining -= n; return n;
}
static struct s22plus_p318_banner_result s22plus_p318_banner_attempt(int fd) {
    events[writes++] = 100; return (struct s22plus_p318_banner_result){1};
}
static long p330_write_diagnostic(int fd, uint32_t stage, int32_t code) {
    events[writes++] = stage; return 0;
}
'''
        harness += definitions + '\nstatic const uint8_t p328_run_id[] = {' + numbers(module.runtime.P335_RUN_ID) + '};\n'
        harness += functions + '\n' + console
        harness += '\nstatic const uint8_t valid[] = {' + numbers(opened) + '};\n'
        harness += r'''
static void reset(const uint8_t *data, size_t n) { input=data;remaining=n;writes=0; }
int main(void) {
    uint8_t seen=0, bad[sizeof(valid)]; long rc;
    reset(valid, 0); rc=p335_framed_console(0, NULL, &seen);
    assert(rc==-ETIMEDOUT && seen==0 && writes==0);
    reset(valid, 8); rc=p335_framed_console(0, NULL, &seen);
    assert(rc==-ETIMEDOUT && seen==1 && writes==1);
    reset(valid, 24); rc=p335_framed_console(0, NULL, &seen);
    assert(rc==-ETIMEDOUT && seen==1 && writes==1);
    memcpy(bad,valid,sizeof(valid)); bad[0]='X';
    reset(bad,sizeof(bad));rc=p335_framed_console(0,NULL,&seen);
    assert(rc==-EPROTO && seen==1 && writes==5 && events[0]==3);
    reset(valid,sizeof(valid));rc=p335_framed_console(0,NULL,&seen);
    assert(rc==0 && seen==1 && writes==3);
    assert(events[0]==100 && events[1]==0 && events[2]==1);
    assert(remaining==0);
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='s22-open-parser-h0-') as directory:
            binary = str(Path(directory) / 'parser')
            result = subprocess.run(['/usr/bin/cc', '-x', 'c', '-', '-o', binary],
                input=harness.encode(), capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            subprocess.run([binary], check=True, timeout=5)


if __name__ == '__main__':
    unittest.main()
