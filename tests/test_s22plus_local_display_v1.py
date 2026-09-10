"""Production local lifecycle/publication with real host IPC and fixed hardware.

Numeric credentials, PID1, mounts, modules and DRM are explicit fixtures.
Authentication/command framing, fork/exec/pipes and ownership C remain real.
"""
from contextlib import contextmanager
import ast
import os
from pathlib import Path
import signal
import re
import socket
import struct
import subprocess
import tempfile
import time
import unittest
from unittest import mock
import zlib

import test_s22plus_native_source_v1 as direct_test
import test_s22plus_fyg8_p381_hud_integration as hud
import test_s22plus_fyg8_p376_hud_integration as parent_hud
import test_s22plus_fyg8_p383_native_health_integration as health
import test_s22plus_hud_arm64 as arm64
import s22plus_native_source_v1 as direct
import s22plus_memory_manifest_v1 as memory
import s22plus_root_console_v1 as wire

_HUD_SOURCE = hud.source

def source(runtime=None):
    with direct_test.production_join(profile=direct.LOCAL_PROFILE):
        with mock.patch.object(hud, 'runtime', runtime or hud.runtime):
            value = _HUD_SOURCE()
    if runtime is not None:
        # The inherited host module-table fixture uses its historical name.
        value=value.replace('p381',direct_test.runtime_identity(runtime).namespace)
    value = value.replace('static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){',
        'static pid_t fx_owner_pid;\nstatic int fx_transport=-1;\nstatic unsigned fx_reads;\n'
        'static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){\n'
        ' if(nr==172)return getpid()==fx_owner_pid?1:getpid();')
    # Ownership is set once before fork, inherited unchanged by all children.
    value = value.replace('static long fx_read(int fd,void *p,size_t n){',
        'static int fx_transport;\nstatic unsigned fx_reads;\nstatic uint64_t fx_clock_offset_ms;\nstatic long fx_read(int fd,void *p,size_t n){\n'
        ' if(fd==fx_transport && fx_reads++<8){if(fx_case("peer-eio"))return -EIO;'
        'if(fx_case("peer-zero"))return 0;if(fx_case("peer-enodev"))return -ENODEV;'
        'if(fx_case("peer-epipe"))return -EPIPE;if(fx_case("peer-ebadf"))return -EBADF;}')
    value = value.replace('return neg(read(fd,p,n));',
        'long rc=neg(read(fd,p,n));if(fd==fx_transport && n==32 && rc==32 && '
        'fx_case("auth-deadline-cross"))fx_clock_offset_ms=120001;return rc;')
    value = value.replace('if(fx_at("read",i))return -EIO;',
        'if(len<0||len>=(int)sizeof(b)||fx_pos[i]<0||fx_pos[i]>len)_Exit(128);'
        'if(fx_at("read",i))return -EIO;')
    value = value.replace('if((int)n>len-fx_pos[i])n=(size_t)(len-fx_pos[i]);',
        'size_t left=(size_t)len-(size_t)fx_pos[i];if(n>left)n=left;')
    # Tentative declarations precede fixture wrappers; this is fixture-only.
    value = value.replace('static int fx_transport=-1;\nstatic unsigned fx_reads;\n', '')
    value = value.replace('if(!strcmp(p,"/proc/sys/kernel/random/boot_id")){',
        'if(!strcmp(p,"/proc/sys/kernel/random/boot_id")){fx_mark("boot-id",0);'
        'if(fx_case("boot-id-error"))return -EIO;')
    value = value.replace('out->tv_sec=t.tv_sec;out->tv_nsec=t.tv_nsec;return 0;',
        'unsigned long rate=getenv("LOCAL_CLOCK_RATE")?strtoul(getenv("LOCAL_CLOCK_RATE"),NULL,10):1;'
        'if(!rate)rate=1;uint64_t ms=((uint64_t)t.tv_sec*1000+t.tv_nsec/1000000)*rate+fx_clock_offset_ms;'
        'out->tv_sec=ms/1000;out->tv_nsec=(ms%1000)*1000000;return 0;')
    # Use the exact production publication body, with only its final native
    # parking loop mapped to the existing host fixture exit. No listener retry.
    publisher = (direct.TEMPLATES / 'local_publish.inc.c.in').read_text().replace(
        'for(;;)p282_poll_delay();', 'fx_park();__builtin_unreachable();')
    value = value[:value.index('int main(int argc,char **argv)')]
    return value + publisher + r'''
int main(int argc,char **argv){
 if(argc!=3)return 2;fx_transport=atoi(argv[1]);fx_owner_pid=getpid();
 if(prctl(PR_SET_CHILD_SUBREAPER,1))return 3;
 p319_stock_publish(fx_transport);
}
'''


def compile_c(source_text, binary):
    built = subprocess.run(['cc', '-x', 'c', '-', '-O2', '-Wall', '-Wextra', '-Werror',
        '-Wno-unused-function', '-Wno-unused-const-variable', '-Wno-misleading-indentation',
        '-o', str(binary)], input=source_text, text=True, capture_output=True, timeout=30)
    if built.returncode:
        raise AssertionError(built.stderr)


def frame(kind, sequence, payload):
    header = struct.pack('<4sBBHI', b'S328', 1, kind, len(payload), sequence)
    return header + struct.pack('<I', zlib.crc32(header + payload)) + payload


class LocalLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='s22-local-display-h0-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.binary = cls.folder / 'native'
        cls.source_text = source()
        compile_c(cls.source_text, cls.binary)

    @contextmanager
    def running(self, case='normal', rate=1):
        directory = self.folder / str(time.monotonic_ns());directory.mkdir()
        host, peer = socket.socketpair();host.setblocking(False);peer.setblocking(False)
        process = subprocess.Popen([str(self.binary), str(peer.fileno()), '1'],
            pass_fds=(peer.fileno(),), start_new_session=True, stderr=subprocess.PIPE,
            env=dict(os.environ, P364_CASE=case, P364_MARK=str(directory/'marks'),
                     RC1_WORK=str(directory), LOCAL_CLOCK_RATE=str(rate),
                     HUD_RENDERER='', METRICS_COLLECTOR='/bin/false'))
        peer.close()
        try:
            yield host, process, directory
        finally:
            host.close()
            try:process.wait(timeout=6)
            except subprocess.TimeoutExpired:pass
            # Reap/kill only the fixture process group, including any fixture
            # child still alive after the production nonblocking cleanup.
            try:os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:pass
            process.communicate(timeout=3)

    @staticmethod
    def log(directory):
        path=directory/'hud.log'
        return path.read_bytes() if path.exists() else b''

    @staticmethod
    def marks(directory):
        path=directory/'marks'
        return path.read_text().splitlines() if path.exists() else []

    def until(self, predicate, timeout=3):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.01)
        self.assertTrue(predicate(), 'fixture observation deadline')

    def test_absent_host_displays_wait_then_bounded_expiry_without_tx(self):
        with self.running(rate=20) as (host, process, directory):
            self.until(lambda: b'state=3 ' in self.log(directory))
            with self.assertRaises(BlockingIOError):host.recv(4096)
            self.assertIsNone(process.poll())
            self.assertEqual(process.wait(timeout=4), 0)
            log=self.log(directory);marks=self.marks(directory)
            self.assertIn(b'state=5 ', log)
            self.assertNotIn('download 0', marks)
            self.assertEqual(marks.count('root-dir 0'), 1)
            self.assertEqual(marks.count('root-mount 0'), 1)
            self.assertLess(marks.index('root-mount 0'), marks.index('boot-id 0'))
            self.assertLessEqual(log.count(b'HUD_SIGNAL_ATTEMPT '), 1)
            self.assertLessEqual(log.count(b'METRICS_SIGNAL_ATTEMPT '), 1)

    def test_malformed_open_is_terminal_and_cannot_reenter(self):
        with self.running(rate=20) as (host, process, directory):
            self.until(lambda: b'state=3 ' in self.log(directory))
            host.sendall(b'X'*16)
            self.until(lambda: b'state=4 ' in self.log(directory))
            host.sendall(frame(1, 0, hud.runtime.P345_RUN_ID))
            self.assertEqual(process.wait(timeout=3), 0)
            marks=self.marks(directory)
            self.assertFalse(any(line.startswith('finit ') for line in marks))
            self.assertNotIn('download 0', marks)
            self.assertEqual(marks.count('root-dir 0'), 1)
            self.assertEqual(self.log(directory).count(b'HUD_START '), 1)

    def test_wrong_auth_never_prepares_return_or_accepts_control(self):
        with self.running(rate=20) as (host, process, directory):
            self.until(lambda: b'state=3 ' in self.log(directory))
            host.sendall(frame(1, 0, hud.runtime.P345_RUN_ID) + frame(4, 1, b'x'*32))
            self.assertEqual(process.wait(timeout=3), 0)
            self.assertIn(b'state=4 ', self.log(directory))
            marks=self.marks(directory)
            self.assertFalse(any(line.startswith('finit ') for line in marks))
            self.assertNotIn('download 0', marks)

    def test_boot_id_failure_is_runtime_failure_before_any_auth(self):
        with self.running('boot-id-error', rate=20) as (host, process, directory):
            self.assertEqual(process.wait(timeout=3), 0)
            self.assertEqual(host.recv(4096), b'')
            self.assertIn(b'state=7 ', self.log(directory))
            self.assertNotIn(b'state=4 ', self.log(directory))
            self.assertNotIn('download 0', self.marks(directory))

    def test_pre_open_known_absent_peer_outcomes_wait_but_bad_fd_fails(self):
        for case in ('peer-zero', 'peer-eio', 'peer-enodev', 'peer-epipe', 'peer-ebadf'):
            with self.subTest(case=case), self.running(case, rate=20) as (host, process, directory):
                self.assertEqual(process.wait(timeout=4), 0)
                expected=b'state=4 ' if case=='peer-ebadf' else b'state=5 '
                self.assertIn(expected, self.log(directory))
                self.assertNotIn('download 0', self.marks(directory))

    def test_partial_open_disconnect_is_failure_without_waiting_for_new_peer(self):
        with self.running(rate=20) as (host, process, directory):
            self.until(lambda: b'state=3 ' in self.log(directory))
            host.sendall(b'S');host.shutdown(socket.SHUT_WR)
            self.assertEqual(process.wait(timeout=1), 0)
            self.assertIn(b'state=4 ', self.log(directory))
            self.assertNotIn('download 0', self.marks(directory))

    def test_final_valid_auth_crossing_preauth_deadline_is_rejected(self):
        with self.running('auth-deadline-cross', rate=20) as (host, process, directory):
            codec=parent_hud.live._open_header_initial_observer_module(
                hud.runtime,hud.observer,'local-auth-deadline-h0')
            raw=bytearray();writer=type('Writer',(),{'write_stdout':lambda _,data:raw.extend(data)})()
            io=hud.observer.IO(codec,b'k'*32,fd=host.fileno(),writer=writer,deadline=time.monotonic()+4)
            with self.assertRaises(EOFError):io.handshake()
            self.assertTrue(io.audit.challenge_seen)
            self.assertFalse(io.audit.authenticated)
            self.assertEqual(process.wait(timeout=2),0)
            self.assertIn(b'state=5 ',self.log(directory))
            self.assertNotIn('download 0',self.marks(directory))
            self.assertFalse(any(line.startswith('finit ') for line in self.marks(directory)))


class LocalConsole(parent_hud.HudIntegration):
    """Existing command, cancel, bounded output and CONTROL checks on 1B C."""
    @classmethod
    def setUpClass(cls):
        census=tuple(direct.MemoryModule(*row) for row in memory.manifest())
        identity=direct_test.runtime_identity(hud.runtime)
        with mock.patch.object(hud, 'source', source), mock.patch.object(
                hud.renderer_test.renderer, 'render', side_effect=lambda:
                direct.render_display(identity, census, profile=direct.LOCAL_PROFILE)):
            hud.StatusIntegration.setUpClass.__func__(cls)

    # H0 old observer parses cached stage bytes under an explicitly selected
    # new source profile; it is not a new live owner or syscall-timing proof.
    def run_case(self, case, full=True):
        with mock.patch.object(parent_hud, 'runtime', hud.runtime), mock.patch.object(
                parent_hud, 'observer', hud.observer), mock.patch.dict(os.environ, {
                    'METRICS_COLLECTOR':str(self.collector), 'SNAPSHOT_BINARY':str(self.snapshot)}):
            return super().run_case(case, full)

    def assert_console_control(self, result, error, marks):
        receipt=result.receipt if result is not None else error.partial_receipt
        self.assertTrue(receipt['control_acceptance_observed'])
        self.assertEqual(len(receipt['commands']),6)
        self.assertTrue(all(row['accepted'] and row['terminal'] is not None for row in receipt['commands']))
        self.assertEqual(marks.count('download 0'),1)
        self.assertEqual(marks.count('root-dir 0'),1)
        self.assertEqual(marks.count('root-mount 0'),1)

    def test_hud_updates_while_root_commands_and_cancel_work(self):
        result,error,log,marks=self.run_case('normal')
        self.assert_console_control(result,error,marks)
        self.assertIn(b'state=1 ',log)
        self.assertEqual(marks.count('hud-child 0'),1)
        self.assertLessEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)

    def test_real_renderer_snapshot_decoder_and_console_share_boot(self):
        self.renderer=str(self.real_renderer)
        result,error,log,marks=self.run_case('normal')
        self.assert_console_control(result,error,marks)
        self.assertGreaterEqual(log.count(b'HUD_FRAME '),3)
        self.assertIn(b'HUD_MEM ',log)

    def test_failed_and_parked_hud_preserve_commands_and_control(self):
        for case in ('hud-exit','hud-stall','hud-flood','metrics-blocked','metrics-exit'):
            with self.subTest(case=case):
                result,error,log,marks=self.run_case(case)
                self.assert_console_control(result,error,marks)
                self.assertLessEqual(len(log),1024*1024)
                self.assertLessEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)
                self.assertLessEqual(log.count(b'METRICS_SIGNAL_ATTEMPT '),1)


class LocalHealth(health.IntegrationTests):
    @classmethod
    def setUpClass(cls):
        prepared=source(runtime=health.runtime)
        with mock.patch.object(health.base,'source',return_value=prepared):
            health.IntegrationTests.setUpClass.__func__(cls)

    def exercise(self, case='normal', before_control=None):
        with LocalLifecycle.running(self,case,rate=20) as (host,process,directory):
            raw=bytearray();writer=type('Writer',(),{'write_stdout':lambda _,data:raw.extend(data)})()
            intents=[];result=error=None
            try:
                result=health.observer.qualify(self.codec,host.fileno(),b'k'*32,None,set(),writer,
                    deadline=time.monotonic()+5,before_control=before_control or intents.append,
                    evidence=directory/'console')
            except health.observer.QualificationError as exc:error=exc
            return result,error,intents,bytes(raw)

    def test_delayed_auth_has_local_display_before_healthy_console(self):
        with LocalLifecycle.running(self) as (host,process,directory):
            LocalLifecycle.until(self,lambda:b'state=3 ' in LocalLifecycle.log(directory))
            time.sleep(1.1)
            with self.assertRaises(BlockingIOError):host.recv(4096)
            raw=bytearray();writer=type('Writer',(),{'write_stdout':lambda _,data:raw.extend(data)})()
            intents=[]
            result=health.observer.qualify(self.codec,host.fileno(),b'k'*32,None,set(),writer,
                deadline=time.monotonic()+5,before_control=intents.append,evidence=directory/'console')
            self.assertEqual(result.receipt['qualified_command_count'],1)
            self.assertEqual(len(intents),1)
            self.assertEqual(process.wait(timeout=3),0)
            marks=LocalLifecycle.marks(directory)
            self.assertEqual(marks.count('root-dir 0'),1)
            self.assertEqual(marks.count('download 0'),1)

    def test_cached_ram_preparation_failure_cannot_enter_console(self):
        for case,stage in (('root-dir',61),('root-mount',62)):
            with self.subTest(case=case):
                result,error,intents,raw=self.exercise(case)
                self.assertIsNone(result);self.assertIsNotNone(error)
                self.assertEqual(error.partial_receipt['preparation']['failure']['stage'],stage)
                self.assertEqual(intents,[])
                self.assertTrue(raw)


class LocalAbi(unittest.TestCase):
    def test_getpid_exact_target_uapi_and_real_arm64_syscall(self):
        header=arm64.KERNEL/'include/uapi/asm-generic/unistd.h'
        self.assertIn('#define __NR_getpid 172', header.read_text())
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'getpid'
            code=r'''
#define _GNU_SOURCE
#include <assert.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
_Static_assert(SYS_getpid==172,"target getpid ABI");
int main(void){long owner=syscall(172);assert(owner>1&&owner==getpid());
 pid_t child=fork();assert(child>=0);if(!child){assert(syscall(172)>1&&syscall(172)!=owner);_exit(0);}
 int status;assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);return 0;}
'''
            built=subprocess.run(['aarch64-linux-gnu-gcc','-x','c','-','-static','-O2','-Wall','-Wextra',
                '-Werror','-o',str(binary)],input=code,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stderr)
            self.assertIn('ARM aarch64',subprocess.check_output(['file',binary],text=True))
            result=subprocess.run(['qemu-aarch64',binary],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)


class LocalOwnerBounds(unittest.TestCase):
    def test_child_cannot_service_owner_and_expiry_cannot_restart_or_renew(self):
        text=source();text=text[:text.index('int main(int argc,char **argv)')]
        text=hud.runtime._replace_function(text.encode(),b'static long p241_clock_gettime(',b'''
static uint64_t unit_now=1000000;
static long p241_clock_gettime(struct timespec64 *out){
 out->tv_sec=unit_now/1000;out->tv_nsec=(unit_now%1000)*1000000;return 0;
}
''').decode()
        text+=r'''
#include <assert.h>
int main(void){
 fx_owner_pid=getpid();fx_transport=-1;assert(local_begin()==0);
 long renderer=local_display.hud.pid;assert(renderer>0);
 pid_t probe=fork();assert(probe>=0);
 if(!probe){assert(!local_owner());assert(local_begin()==-P260_EPROTO);
  local_phase(0);local_service();local_close();assert(!local_display.stopped&&local_display.phase==3);_exit(0);}
 int status=0;assert(waitpid(probe,&status,0)==probe&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
 assert(kill(renderer,0)==0);assert(local_begin()==0);
 local_display.attempted=1;assert(local_begin()==-P260_EPROTO);
 local_display.authenticated=1;local_phase(0);local_service();
 uint32_t seq=local_display.hud.sequence;
 for(unsigned i=0;i<10000;i++){local_phase(i%3);local_service();}
 assert(local_display.hud.sequence==seq);
 unit_now=local_display.start+LOCAL_DISPLAY_MS-1;local_service();assert(!local_display.stopped);
 unit_now++;local_service();assert(local_display.stopped&&local_display.phase==5);
 assert(local_pre_auth()==0); /* Display expiry does not renew/terminate console authority. */
 seq=local_display.hud.sequence;local_phase(0);local_service();local_close();
 assert(local_display.hud.sequence==seq&&local_display.phase==5&&local_begin()==-P260_EPROTO);
 puts("PASS owner isolation finite display deadline and no restart");return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='s22-local-owner-h0-') as folder:
            directory=Path(folder);binary=directory/'probe';compile_c(text,binary)
            result=subprocess.run([binary],capture_output=True,text=True,timeout=5,
                env=dict(os.environ,P364_CASE='metrics-blocked',P364_MARK=str(directory/'marks'),
                         RC1_WORK=str(directory),HUD_RENDERER='',METRICS_COLLECTOR='/bin/false'))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PASS owner isolation',result.stdout)
            marks=(directory/'marks').read_text().splitlines();log=(directory/'hud.log').read_bytes()
            self.assertEqual(marks.count('root-dir 0'),1)
            self.assertLessEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)
            self.assertLessEqual(log.count(b'METRICS_SIGNAL_ATTEMPT '),1)


class LocalRenderer(hud.renderer_test.StatusRenderer):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='s22-local-renderer-h0-')
        cls.addClassCleanup(cls.temp.cleanup);folder=Path(cls.temp.name)
        fixture,headers=hud.renderer_test.fixture()
        fixture=fixture.replace('painted[8]','painted[916]').replace('hashes[8]','hashes[916]')
        fixture=fixture.replace('handles<=8','handles<=916').replace('q->handle<=8','q->handle<=916')
        fixture=fixture.replace('if(commits==3){','if(commits==3&&strcmp(scenario,"local-lifetime")){')
        fixture=fixture.replace('if(d->tv_sec==1){',
            'if(d->tv_sec==1){if(!strcmp(scenario,"local-lifetime")){'
            'assert(commits==916&&handles==916&&closed==915&&retired==915&&unmapped==915&&flips==916&&!pending);'
            'puts("PASS 916 immutable frames and final local state");fflush(stdout);_Exit(0);}')
        fixture=fixture.replace('if(!strcmp(scenario,"wrong-run"))value.run[0]^=1;',
            'if(!strncmp(scenario,"local-state-",12))value.state=(unsigned)atoi(scenario+12);\n '
            'if(!strcmp(scenario,"local-lifetime"))value.state=seq==916?8:3;\n '
            'if(!strcmp(scenario,"wrong-run"))value.run[0]^=1;')
        fixture=fixture.replace('  struct status_metrics value={',
            '  if(!strcmp(scenario,"local-lifetime")&&sequence>=601)return 0;\n'
            '  struct status_metrics value={')
        fixture=fixture.replace(' char *args[]={"renderer",',r'''
 if(!strcmp(scenario,"local-gem-bound")){
  char good[]="HUD_MEM seq=916 ms=900000 alloc=916 retired=915 live=1 peak=2 bytes=10183680";
  char bad[]="HUD_MEM seq=917 ms=900000 alloc=917 retired=916 live=1 peak=2 bytes=10183680";
  uint64_t values[7];assert(ms_gem_line(good,values));assert(!ms_gem_line(bad,values));
  puts("PASS profile-specific GEM accounting bound");return 0;
 }
 char *args[]={"renderer",''')
        census=tuple(direct.MemoryModule(*row) for row in memory.manifest())
        (folder/'renderer.c').write_bytes(direct.render_display(
            direct_test.runtime_identity(hud.runtime),census,profile=direct.LOCAL_PROFILE))
        (folder/'fixture.c').write_text(fixture);cls.binary=folder/'renderer'
        built=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE',
            '-I',str(headers),'-I',str(direct.NATIVE),str(folder/'fixture.c'),'-o',str(cls.binary)],
            capture_output=True,text=True,timeout=30)
        if built.returncode:raise AssertionError(built.stderr)

    def test_each_local_state_and_reject_unknown_state(self):
        for state in range(9):
            with self.subTest(state=state):
                result=self.run_case(f'local-state-{state}')
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(f' state={state} '.encode(),result.stderr)
        result=self.run_case('local-state-9')
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertNotIn(b'HUD_FRAME ',result.stderr)

    def test_full_local_capacity_keeps_final_state_and_stale_metrics(self):
        result=subprocess.run([self.binary,'local-lifetime'],capture_output=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr[-2000:])
        rows=[line for line in result.stderr.splitlines() if line.startswith(b'HUD_FRAME ')]
        self.assertEqual(len(rows),916)
        self.assertIn(b'state=8 ',rows[-1]);self.assertIn(b'valid=0 ',rows[-1])
        self.assertIn(b'PASS 916 immutable',result.stdout)
        self.assertLessEqual(result.stderr.count(b'HUD_MEM '),32)

    def test_profile_specific_memory_parser_bound(self):
        result=self.run_case('local-gem-bound')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(b'PASS profile-specific GEM',result.stdout)

    def test_local_log_capacity_includes_existing_failure_outputs(self):
        renderer=(direct.TEMPLATES/'display.c.in').read_text()
        start=renderer.index('fprintf(stderr,"HUD_FRAME')
        line=renderer[start:renderer.index('\n',start)]
        tokens=re.findall(r'"(?:\\.|[^"\\])*"|PRIu64',line)
        format_text=''.join('llu' if token=='PRIu64' else ast.literal_eval(token) for token in tokens)
        maximum=re.sub(r'%(?:llu|s|u|d)',lambda match:'x'*{
            '%llu':20,'%s':32,'%u':10,'%d':11}[match[0]],format_text)
        self.assertNotIn('%',maximum);self.assertLessEqual(len(maximum),1024)
        contract=direct.profile_contract(direct.LOCAL_PROFILE)
        required=916*1024+8*1152+32*128+32768+32768
        self.assertLess(required,contract['local_hud_log_limit'])


class LocalBackpressure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LocalLifecycle.setUpClass.__func__(cls)

    def run_burst(self, control_during_output):
        with LocalLifecycle.running(self) as (host,process,directory):
            codec=parent_hud.live._open_header_initial_observer_module(
                hud.runtime,hud.observer,'local-display-backpressure-h0')
            raw=bytearray();writer=type('Writer',(),{'write_stdout':lambda _,data:raw.extend(data)})()
            io=hud.observer.IO(codec,b'k'*32,fd=host.fileno(),writer=writer,deadline=time.monotonic()+5)
            io.handshake()
            session=wire.Session(host.fileno(),b'k'*32,hud.runtime.P345_RUN_ID,io.audit.nonce,
                directory/'console',on_rx=io.capture,on_tx=io.audit.tx.extend)
            events=[]
            def wait(kind,sequence,timeout=8):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    for k,n,payload in events:
                        if k==kind and n==sequence:return payload
                    events.extend(session.poll());time.sleep(.001)
                self.fail('authenticated console event deadline')
            try:
                wait(wire.READY,2)
                out=bytes(range(256))*256;err=bytes(reversed(range(256)))*256
                (directory/'out.data').write_bytes(out);(directory/'err.data').write_bytes(err)
                sequence=session.send(wire.EXEC,wire.command(
                    b'cat out.data & cat err.data >&2 & wait',cwd=b'/s22-root-work'))
                wait(wire.ACK,sequence);time.sleep(.35)
                if control_during_output:
                    control=session.send(wire.CONTROL);wait(wire.CONTROL_ACK,control)
                else:
                    status=session.send(wire.STATUS);wait(wire.STATUS_REPLY,status)
                terminal=struct.unpack('<7I',wait(wire.EXIT,sequence))
                streams={stream:b''.join(payload[12:] for kind,n,payload in events
                    if kind==wire.OUTPUT and n==sequence and struct.unpack('<I',payload[8:12])[0]==stream)
                    for stream in (1,2)}
                if control_during_output:
                    self.assertTrue(terminal[1]&32);self.assertTrue(terminal[1]&128)
                    self.assertEqual(terminal[4],sum(map(len,streams.values())))
                else:
                    self.assertEqual(terminal[1:4],(0,0,0))
                    self.assertEqual(streams,{1:out,2:err});self.assertEqual(terminal[5],0)
                    control=session.send(wire.CONTROL);wait(wire.CONTROL_ACK,control)
                self.assertEqual(process.wait(timeout=3),0)
                marks=LocalLifecycle.marks(directory)
                self.assertEqual(marks.count('download 0'),1)
                self.assertEqual(marks.count('hud-child 0'),1)
            finally:session.close()

    def test_paused_reader_retains_both_binary_streams(self):
        self.run_burst(False)

    def test_control_during_backpressure_preserves_incomplete_output_flags(self):
        self.run_burst(True)


if __name__=='__main__':unittest.main()
