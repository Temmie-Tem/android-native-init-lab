"""Actual resident C, PTY command reentry and fixed-size real service IPC.

Credentials, target mounts/USB and DRM are explicit fixtures. Time acceleration
and sensor fixtures do not establish a live soak, thermal accuracy or recovery.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import pty
import signal
import socket
import struct
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_native_baseline_protocol_v1 as baseline_test
import test_s22plus_fyg8_p376_hud_renderer as drm_test
import s22plus_native_source_v1 as common
import s22plus_native_resident_source_v1 as source
import s22plus_native_resident_protocol_v1 as protocol
import s22plus_root_console_v1 as wire

IDENTITY = baseline_test.candidate.IDENTITY  # fixture identity only; no active source changes
HEADERS = common.ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'
CENSUS = (common.MemoryModule('fixture.ko', 123, 0o400),)


def swap(text, before, after):
    return source.replace(text.encode(), before.encode(), after.encode()).decode()


def native_fixture():
    with mock.patch.object(common, 'helper_template', side_effect=lambda identity, **kw: source.helper_template(identity)):
        text = baseline_test.source()
    old = common._read(common.TEMPLATES/'local_publish.inc.c.in').decode().replace(
        'for(;;)p282_poll_delay();', 'fx_park();__builtin_unreachable();')
    text = swap(text, old, source.publish_source().decode())
    text = swap(text, 'static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){', '''
static long p241_clock_gettime(struct timespec64 *out);
static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){
 if(nr==113){if(a!=CLOCK_BOOTTIME||c||d||e||f)_Exit(130);return p241_clock_gettime((void*)b);}
 if(nr==207){if(d!=(MSG_DONTWAIT|MSG_TRUNC)||e||f)_Exit(131);return neg(recv(a,(void*)b,c,d));}
 if(nr==46){if(b||c||d||e||f)_Exit(132);return neg(ftruncate(a,b));}
 if(nr==62 && a<2000){if(b||c||d||e||f)_Exit(133);return neg(lseek(a,b,c));}
''')
    text = swap(text, 'if(d!=MSG_NOSIGNAL||e||f)_Exit(122);',
                'if(d!=(MSG_NOSIGNAL|MSG_DONTWAIT)||e||f)_Exit(122);')
    text = swap(text, 'if(!strcmp(a[1],"--collect-status")) {',
                'if(!strcmp(a[1],"--collect-system") || !strcmp(a[1],"--collect-hardware")) {')
    text = swap(text, 'if(fx_case("metrics-blocked"))for(;;)usleep(10000);',
                'if(fx_case("metrics-blocked") && !strcmp(a[1],"--collect-hardware"))for(;;)usleep(10000);')
    text = swap(text, 'if(fx_case("metrics-exit"))_Exit(7);',
                'if(fx_case("metrics-exit") && !strcmp(a[1],"--collect-hardware"))_Exit(7);')
    text = swap(text, 'char *args[]={getenv("METRICS_COLLECTOR"),a[2],NULL};',
                'char *args[]={getenv("METRICS_COLLECTOR"),a[1],a[2],NULL};')
    # BOOTTIME in every real participant; old monotonic deadline wrapper is
    # test-only and uses the same accelerated BOOTTIME value.
    text = text.replace('clock_gettime(CLOCK_MONOTONIC,&t)', 'clock_gettime(CLOCK_BOOTTIME,&t)')
    # Bounded test-only observation of PID1 state after the actual service tick.
    # This does not issue a command, change the latch, or replace its behavior.
    text = swap(text, 'static void local_service(void) {',
                'static void fx_resident_observe(void);\nstatic void local_service(void) {')
    text = swap(text, 'if(!local_display.stopped)hud1_tick(&local_display.hud,now,local_display.phase);',
                'if(!local_display.stopped){hud1_tick(&local_display.hud,now,local_display.phase);fx_resident_observe();}')
    before='int main(int argc,char **argv){'
    text=swap(text,before,r'''
static void fx_resident_observe(void){
 static unsigned turn;if(++turn%25)return;
 char path[4096];snprintf(path,sizeof(path),"%s/service.txt",getenv("RC1_WORK"));
 int f=open(path,O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC,0600);if(f<0)_Exit(139);
 dprintf(f,"seq=%llu system=%llu hardware=%llu hardware_state=%u terminal=%u stopped=%u sessions=%llu\n",
  (unsigned long long)local_display.hud.sequence,(unsigned long long)local_display.hud.sample[0].sequence,
  (unsigned long long)local_display.hud.sample[1].sequence,local_display.hud.state[1],local_display.terminal,
  local_display.stopped,(unsigned long long)baseline_sessions);close(f);
}
'''+before)
    return text


def renderer_fixture():
    text, _ = drm_test.fixture()
    text = text.replace('painted[8]', 'painted[1004]').replace('hashes[8]', 'hashes[1004]')
    text = text.replace('handles<=8', 'handles<=1004').replace('q->handle<=8', 'q->handle<=1004')
    text = swap(text, 'int fake_clock_gettime(clockid_t id,struct timespec *value){',
                'static uint64_t fixture_ms=1;\nint fake_clock_gettime(clockid_t id,struct timespec *value){')
    text = swap(text, 'static uint64_t ticks;assert(id==CLOCK_MONOTONIC);', 'assert(id==CLOCK_BOOTTIME);')
    text = swap(text, 'ticks+=100;value->tv_sec=ticks/1000;value->tv_nsec=(ticks%1000)*1000000;',
                'fixture_ms+=10;value->tv_sec=fixture_ms/1000;value->tv_nsec=(fixture_ms%1000)*1000000;')
    a, b = text.index('ssize_t fake_recv('), text.index('ssize_t fake_read(')
    text = text[:a] + r'''
ssize_t fake_recv(int f,void *out,size_t size,int flags){
 static uint64_t seq;static unsigned empty;assert(f==0&&size==304&&flags==(MSG_DONTWAIT|MSG_TRUNC));
 if(!strcmp(scenario,"ipc-live"))return syscall(SYS_recvfrom,f,out,size,flags,NULL,NULL);
 if(empty){empty=0;errno=EAGAIN;return -1;}
 unsigned limit=!strcmp(scenario,"resident-long")?1001:3;
 if(commits==limit){assert(handles==limit&&closed==limit-1&&retired==closed&&unmapped==closed&&flips==limit&&!pending);immutable();puts("PASS resident immutable frames and bounded GEM ownership");fflush(stdout);_Exit(0);}
 ++seq;fixture_ms+=1000;
 if(!strcmp(scenario,"resident-days"))fixture_ms+=86400000ULL;
 struct hud_snapshot value={.magic=RESIDENT_VIEW_MAGIC,.sequence=seq,.state=3,.uptime_ms=fixture_ms};
 const unsigned char id[16]={0xc3,0x85,0xf1,0xe0,0xa9,0x0b,0x5e,0x6d,0x7c,0x8a,0x9b,0x0c,0x0f,0x2e,0x3f,0x0b};
 /* Identity comes from generated renderer's exact run string. */
 (void)id;for(unsigned i=0;i<16;i++){unsigned v;assert(sscanf(run_id+2*i,"%2x",&v)==1);value.run[i]=(uint8_t)v;}
 for(unsigned i=0;i<2;i++){
  value.source_state[i]=RS_RUNNING;
  struct status_metrics *m=&value.sample[i];m->magic=RESIDENT_SAMPLE_MAGIC;m->source=i;
  m->sequence=seq;m->collected_ms=fixture_ms;memcpy(m->run,value.run,16);
  if(!i){m->valid=3;m->mem_total_kib=8192000;m->mem_available_kib=4096000;m->cpu_permille=300;}
  else{m->valid=508;m->cpu_expected=13;m->cpu_mask=8191;m->cpu_temp_mc=48300;
   m->battery_temp_deci=260;m->battery_pct=75;m->charge=2;m->gauge_sequence=seq;
   m->gauge_ms=fixture_ms;m->gauge_soc_permille=750;m->gauge_voltage_uv=4000000;m->gauge_current_ua=-100000;}
 }
 if(!strcmp(scenario,"wrong-run"))value.run[0]^=1;
 if(!strcmp(scenario,"stale-sequence")&&commits)value.sequence--;
 if(!strcmp(scenario,"stale-parent")){errno=EAGAIN;return -1;}
 if(!strcmp(scenario,"oversized-packet"))return 305;
 if(!strcmp(scenario,"snapshot-eof"))return 0;
 if(!strcmp(scenario,"hardware-eof"))value.source_state[1]=RS_EOF;
 if(!strcmp(scenario,"hardware-stale"))value.sample[1].collected_ms=1;
 memcpy(out,&value,sizeof(value));empty=1;return sizeof(value);
}
''' + text[b:]
    text = text.replace('"NNN");', '"NNN",6);').replace('"OVERFLOW");', '"OVERFLOW",6);')
    text = text.replace('c376f1e0a90b5e6d7c8a9b0c1d2e3f0b', IDENTITY.run_id_hex)
    return text


def compile_c(path, binary, *flags):
    subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(common.NATIVE),
                    '-I', str(HEADERS), *flags, str(path), '-o', str(binary)],
                   check=True, capture_output=True, text=True, timeout=40)


class Resident(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='s22-resident-h0-')
        cls.addClassCleanup(cls.temp.cleanup); cls.folder = Path(cls.temp.name)
        (cls.folder/'native.c').write_text(native_fixture())
        cls.binary = cls.folder/'native'
        compile_c(cls.folder/'native.c', cls.binary, '-Wno-unused-function', '-Wno-unused-const-variable', '-Wno-misleading-indentation')
        (cls.folder/'renderer.c').write_bytes(source.render_display(IDENTITY, CENSUS))
        (cls.folder/'drm.c').write_text(renderer_fixture()); cls.renderer = cls.folder/'renderer'
        compile_c(cls.folder/'drm.c', cls.renderer, '-D_DEFAULT_SOURCE')
        cls.collector = cls.folder/'collector'
        compile_c(cls.folder/'renderer.c', cls.collector)
        cls.codec = baseline_test.local.parent_hud.live._open_header_initial_observer_module(
            baseline_test.fixture_runtime(), baseline_test.candidate.observer, 'resident-protocol-h0')

    @contextmanager
    def running(self, case='normal'):
        folder = self.folder/str(time.monotonic_ns()); folder.mkdir()
        master, fd = pty.openpty(); import tty; tty.setraw(fd)
        os.set_blocking(master, False); os.set_blocking(fd, False); name = os.ttyname(fd)
        proc = subprocess.Popen([self.binary, str(master), '1'], pass_fds=(master,), start_new_session=True,
            stderr=subprocess.PIPE, env=dict(os.environ, P364_CASE=case, P364_MARK=str(folder/'marks'),
            RC1_WORK=str(folder), HUD_RENDERER=str(self.renderer), METRICS_COLLECTOR=str(self.collector), LOCAL_CLOCK_RATE='1'))
        os.close(master); ctx = SimpleNamespace(folder=folder, fd=fd, proc=proc, name=name)
        try: yield ctx
        finally:
            if ctx.fd is not None: os.close(ctx.fd)
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            _, err = proc.communicate(timeout=3)
            if proc.returncode not in (-signal.SIGKILL, 0):
                raise AssertionError((proc.returncode, err, (folder/'marks').read_text() if (folder/'marks').exists() else ''))

    def session(self, ctx, ending='detach', command=b'printf RESIDENT_OK'):
        io = protocol.IO(self.codec, b'k'*32, IDENTITY, fd=ctx.fd, deadline=time.monotonic()+5,
                         writer=SimpleNamespace(write_stdout=lambda data:None))
        io.handshake()
        session = protocol.Session(ctx.fd, b'k'*32, bytes.fromhex(IDENTITY.run_id_hex), io.audit.nonce,
            ctx.folder/str(time.monotonic_ns()), on_rx=io.capture, on_tx=io.audit.tx.extend)
        events = []
        def wait(predicate):
            end = time.monotonic()+5
            while not predicate():
                self.assertLess(time.monotonic(), end, events)
                events.extend(session.poll());time.sleep(.001)
        try:
            wait(lambda:session.ready is not None)
            seq = session.send(wire.EXEC, wire.command(command, cwd=b'/s22-root-work', timeout_ms=1000))
            wait(lambda:seq in session.terminals)
            kind, ack = (protocol.DETACH, protocol.DETACH_ACK) if ending=='detach' else (wire.CONTROL, wire.CONTROL_ACK)
            terminal = session.send(kind)
            wait(lambda:any(k==ack and n==terminal for k,n,_ in events))
            raw, tx = bytes(io.audit.rx), bytes(io.audit.tx)
            proof = protocol.replay_one(self.codec, IDENTITY, b'k'*32, raw, tx)
            return proof, raw, tx
        finally: session.close()

    def reopen(self, ctx):
        import tty
        os.close(ctx.fd);ctx.fd=os.open(ctx.name, os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC);tty.setraw(ctx.fd)

    def observe(self, ctx, predicate=lambda row:True):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:row={k:int(v) for field in (ctx.folder/'service.txt').read_text().split() for k,v in [field.split('=')]}
            except (OSError,ValueError):row={}
            if len(row)==7 and predicate(row):return row
            time.sleep(.01)
        self.fail('resident observation did not reach expected state: '+repr(row))

    def test_more_than_eight_sessions_with_repeated_rng_still_have_unique_nonces(self):
        with self.running('same-nonce') as ctx:
            previous=None
            for ordinal in range(1,13):
                proof,raw,tx=self.session(ctx, 'detach' if ordinal<12 else 'download')
                self.assertEqual(proof['resident_info']['authentication_ordinal'],ordinal)
                if previous:protocol.fresh_same_boot(previous,proof)
                previous=proof
                if ordinal<12:self.reopen(ctx)
            marks=(ctx.folder/'marks').read_text()
            self.assertEqual(marks.count('baseline-boot-prepare'),1)
            self.assertEqual(marks.count('metrics-child'),2)
            self.assertEqual(marks.count('hud-child'),1)
            with self.assertRaises(ValueError):protocol.replay_one(self.codec, IDENTITY, b'k'*32, raw[:-1],tx)

    def test_production_renderer_crosses_old_frame_and_day_boundaries(self):
        for case,count in [('resident-long',1001),('resident-days',3),('hardware-eof',3)]:
            with self.subTest(case=case):
                result=subprocess.run([self.renderer,case],capture_output=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stderr[-1500:])
                rows=[r for r in result.stderr.splitlines() if r.startswith(b'RESIDENT_FRAME ')]
                self.assertEqual(len(rows),count)
                self.assertIn(b'system_valid=3 ',rows[-1])
                self.assertIn(b'hardware_valid=0 ' if case=='hardware-eof' else b'hardware_valid=508 ', rows[-1])

    def test_drm_uncertainty_parks_without_replay_or_retirement(self):
        for case in ('wrong-token','commit-error','wrong-crtc','partial-event','event-timeout','rmfb-error','unmap-error','gem-close-error'):
            result=subprocess.run([self.renderer,case],capture_output=True,timeout=4)
            self.assertEqual(result.returncode,1,result.stderr[-1000:])
            self.assertIn(b'closed=0 ',result.stderr)

    def test_hardware_worker_fault_does_not_expire_system_or_commands(self):
        for case in ('metrics-blocked','metrics-exit'):
            with self.subTest(case=case),self.running(case) as ctx:
                first=self.observe(ctx,lambda row:row['system']>=2)
                proof,_,_=self.session(ctx);self.reopen(ctx)
                later=self.observe(ctx,lambda row:row['system']>=first['system']+2)
                self.assertEqual(later['hardware'],0)
                self.assertEqual(later['hardware_state'],1 if case=='metrics-blocked' else 3)
                self.assertFalse(later['terminal']);self.assertGreater(later['seq'],first['seq'])
                second,_,_=self.session(ctx,'download');protocol.fresh_same_boot(proof,second)
                log=protocol.decode_log((ctx.folder/'hud.log').read_bytes())
                self.assertTrue(any(b'system_valid=3 ' in row for row in log['records']))
                marks=(ctx.folder/'marks').read_text();self.assertEqual(marks.count('metrics-child'),2)

    def test_uncertain_session_and_boot_identity_failure_latch_commands_only(self):
        for case in ('malformed-open','authenticated-disconnect','boot-id-error'):
            with self.subTest(case=case),self.running('boot-id-error' if case=='boot-id-error' else 'normal') as ctx:
                if case=='malformed-open':
                    bad=bytearray(baseline_test.local.frame(1,0,bytes.fromhex(IDENTITY.run_id_hex)));bad[0]^=1
                    os.write(ctx.fd,bad)
                elif case=='authenticated-disconnect':
                    io=protocol.IO(self.codec,b'k'*32,IDENTITY,fd=ctx.fd,deadline=time.monotonic()+5,
                        writer=SimpleNamespace(write_stdout=lambda data:None));io.handshake()
                    os.close(ctx.fd);ctx.fd=None
                first=self.observe(ctx,lambda row:row['terminal']==1 and row['system']>=1)
                if ctx.fd is None:
                    import tty
                    ctx.fd=os.open(ctx.name,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC);tty.setraw(ctx.fd)
                while True:
                    try:
                        if not os.read(ctx.fd,4096):break
                    except BlockingIOError:break
                io=protocol.IO(self.codec,b'k'*32,IDENTITY,fd=ctx.fd,deadline=time.monotonic()+.2,
                    writer=SimpleNamespace(write_stdout=lambda data:None))
                with self.assertRaises((TimeoutError,EOFError,ValueError)):io.handshake()
                after=self.observe(ctx,lambda row:row['system']>=first['system']+1)
                self.assertEqual(after['sessions'],first['sessions']);self.assertFalse(after['stopped'])
                self.assertTrue(after['terminal']);self.assertGreater(after['seq'],first['seq'])


if __name__=='__main__':unittest.main()
