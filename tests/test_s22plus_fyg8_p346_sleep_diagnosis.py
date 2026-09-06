"""H0 reproduction of P346 sleep's false-success applet outcome.

The real C supervisor uses the real filter (host syscall numbers only), while
mount/UID setup and USB remain outside this host test. The optional exact-binary
case runs retained AArch64 BusyBox in user-mode QEMU with explicit EPERM fault
injection; it does not claim that QEMU user mode enforces guest seccomp.
"""
from pathlib import Path
import hashlib
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

import test_s22plus_fyg8_p345_c_host_join as join
import s22plus_fyg8_p346_research_shell_runtime as runtime


def host_definitions(fragment):
    macros = subprocess.run(
        ['cc', '-dM', '-E', '-x', 'c', '-include', 'sys/syscall.h', '-'],
        input='', text=True, capture_output=True, check=True).stdout
    numbers = dict(re.findall(r'^#define __NR_([a-z0-9_]+) (\d+)$', macros, re.M))
    result = ['-DP345_HOST_TEST_EXTRA_SYSCALLS', '-DP345_AUDIT_ARCH=0xc000003eU',
              '-DP345_NR_ARCH_PRCTL=158', '-DP345_NR_DUP2=33']
    for name in re.findall(r'^#define P345_NR_([A-Z0-9_]+) \d+$', fragment, re.M):
        result.append(f'-DP345_NR_{name}={numbers[name.lower()]}')
    return result


def filtered_source(fragment, selected_runtime=runtime):
    # Only the boundary syscall adapter uses host numbers. The existing join
    # adapter still implements the target-numbered supervisor syscalls.
    boundary = fragment.replace('syscall6(', 'filter_syscall6(').replace(
        'p345_enter_readonly_child(void)', 'unused_full_child_setup(void)')
    prelude = r'''
#include <sys/syscall.h>
static long filter_syscall6(long n,long a,long b,long c,long d,long e,long f) {
    return neg(syscall(n,a,b,c,d,e,f));
}
static long sys_mount(const char *s,const char *t,const char *f,
                      unsigned long flags,const char *data) {
    (void)s;(void)t;(void)f;(void)flags;(void)data;return -EPERM;
}
'''
    hook = '''
static long p345_enter_readonly_child(void) {
    if (p345_prctl(P345_PR_SET_NO_NEW_PRIVS,1,0,0,0)) return -1;
    return p345_install_filter();
}
'''
    source = join.source(selected_runtime)
    source = source.replace(" if(nr==157)", " if(nr==25)return neg(fcntl(a,b,c));\n if(nr==157)")
    stub = selected_runtime.fixture_child_source().decode()
    assert source.count(stub) == 1
    return source.replace(stub, prelude + boundary + hook).replace(
        'usleep(1000);', 'usleep(100000);')


class SleepDiagnosisTests(unittest.TestCase):
    @unittest.skipUnless(os.uname().machine == 'x86_64' and shutil.which('cc')
                         and Path('/bin/busybox').exists(), 'native x86 BusyBox fixture')
    def test_real_filter_and_supervisor_report_actual_early_zero_exit(self):
        fragment = (Path(__file__).parent / 'fixtures/p346/readonly_child.inc.c').read_text()
        # P346's consumed filter is a historical input, not current activation.
        self.assertEqual(hashlib.sha256(fragment.encode()).hexdigest(),
                         'a053e6796a83767e5de97ed714080a10888e2c9a9ef99dbb06e3aabf1633ae29')
        observer = join.live._open_header_initial_observer_module(
            runtime, join.live.p344_open_read_observer, 'p346-filter-sleep-h0')
        with tempfile.TemporaryDirectory(prefix='p346-filter-sleep-') as directory:
            root = Path(directory)
            binary = root / 'peer'
            build = subprocess.run(
                ['cc', '-x', 'c', '-', '-o', str(binary), '-O2', '-Wall', '-Wextra',
                 '-Wno-unused-function', '-Wno-misleading-indentation',
                 *host_definitions(fragment)], input=filtered_source(fragment),
                text=True, capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            host, peer = socket.socketpair()
            host.setblocking(False)
            peer.setblocking(False)
            process = subprocess.Popen([str(binary), str(peer.fileno()), '2'],
                                       pass_fds=(peer.fileno(),), stderr=subprocess.PIPE)
            peer.close()
            try:
                seen = set()
                for index, command in enumerate(('/bin/busybox sleep 30', 'printf after')):
                    writer = join.raw.RawCaptureWriter(root, f'rx-{index}',
                        stdout_maximum=512*1024, stderr_maximum=4096)
                    result = join.exchange.exchange(observer, host.fileno(), b'k'*32,
                        command, hashlib.sha256(b'b'*32).hexdigest(), seen, writer,
                        deadline=time.monotonic()+5)
                    self.assertEqual(result.outcome, 'ok')
                    self.assertTrue(result.session.audit.done_seen)
                    command_result = result.session.commands[1]
                    self.assertEqual(command_result.exit_code, 0)
                    self.assertLess(command_result.duration_ms, 2000)
                    self.assertEqual(command_result.output, b'' if index == 0 else b'after')
                    receipt = writer.finalize(returncode=0)
                    self.assertEqual(join.raw.read_stdout(receipt, maximum=512*1024),
                                     bytes(result.session.audit.rx))
                self.assertEqual(process.wait(timeout=3), 0, process.stderr.read().decode())
            finally:
                host.close()
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=3)
                process.stderr.close()

    @unittest.skipUnless(os.environ.get('P346_BUSYBOX_H0'),
                         'set P346_BUSYBOX_H0 to extracted retained binary')
    def test_exact_candidate_busybox_clock_nanosleep_eperm_exits_zero(self):
        binary = Path(os.environ['P346_BUSYBOX_H0']).resolve()
        self.assertEqual(hashlib.sha256(binary.read_bytes()).hexdigest(),
                         'd4e1ca8235fd5c47a7dfca5c9c60ad2243f5d17d3c43d58a7c42355f10fa2cba')
        with tempfile.TemporaryDirectory(prefix='p346-qemu-sleep-') as directory:
            started = time.monotonic()
            normal = subprocess.run(['qemu-aarch64', '-strace', str(binary), 'sleep', '0.2'],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(normal.returncode, 0, normal.stderr)
            self.assertGreaterEqual(time.monotonic()-started, 0.18)
            self.assertRegex(normal.stderr, r'clock_nanosleep\(CLOCK_REALTIME,0,.* = 0')
            trace = Path(directory)/'host.strace'
            started = time.monotonic()
            denied = subprocess.run(['strace', '-f', '-e', 'trace=clock_nanosleep',
                '-e', 'inject=clock_nanosleep:error=EPERM', '-o', str(trace),
                'qemu-aarch64', '-strace', str(binary), 'sleep', '30'],
                capture_output=True, text=True, timeout=5)
            self.assertEqual(denied.returncode, 0, denied.stderr)
            self.assertLess(time.monotonic()-started, 2)
            self.assertEqual(denied.stdout, '')
            self.assertIn('(INJECTED)', trace.read_text())
            self.assertRegex(denied.stderr,
                r'clock_nanosleep\(CLOCK_REALTIME,0,.*tv_sec = 30.* = -1 errno=1 ')
            self.assertIn('exit_group(0)', denied.stderr)


if __name__ == '__main__':
    unittest.main()
