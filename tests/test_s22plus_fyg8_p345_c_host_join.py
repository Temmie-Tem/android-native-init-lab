"""Actual C framing/HMAC/command supervisor joined to Python over a local FD.

Only platform syscall wrappers, banner and fixed parent witnesses are adapted.
Child isolation is deliberately a stub here and has separate tests. This is
not an on-device sandbox or USB test.
"""
from pathlib import Path
import hashlib
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import device_action_f1_live_v2 as live
import device_action_raw_capture_v1 as raw
import s22plus_fyg8_p345_research_shell_runtime as runtime
import s22plus_fyg8_research_shell_exchange as exchange

PREFIX = r'''
#define _GNU_SOURCE
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <time.h>
#include <sys/wait.h>
#include <sys/random.h>
#include <sys/prctl.h>
#define P260_EINTR EINTR
#define P260_EPROTO EPROTO
#define S22PLUS_P318_ERRNO_EPIPE EPIPE
#define S22PLUS_P318_BANNER_WRITTEN 1
struct timespec64 { int64_t tv_sec, tv_nsec; };
struct s22plus_p318_banner_result { int outcome; };
static long neg(long n) { return n < 0 ? -errno : n; }
static long sys_read(int fd,void *p,size_t n){ return neg(read(fd,p,n)); }
static long sys_write(int fd,const void *p,size_t n){ return neg(write(fd,p,n)); }
static long sys_close(int fd){ return neg(close(fd)); }
static long sys_pipe2(int *fds,int flags){ return neg(pipe2(fds,flags)); }
static long sys_clone(void){ return neg(fork()); }
static long sys_kill(long pid,int sig){ return neg(kill(pid,sig)); }
static long sys_wait4(long pid,int *status,int options){ return neg(waitpid(pid,status,options)); }
static long sys_openat(const char *p,int flags,int mode){ return neg(open(p,flags,mode)); }
static long sys_execve(const char *p,char *const *a,char *const *e){ return neg(execve(p,a,e)); }
static long sys_dup3(int a,int b,int flags){ return neg(dup3(a,b,flags)); }
static void sys_exit(int code){ _exit(code); }
static long syscall6(long nr,long a,long b,long c,long d,long e,long f){
 (void)d;(void)e;(void)f;
 if(nr==157)return neg(setsid());
 if(nr==278)return neg(getrandom((void*)a,b,c));
 return -ENOSYS;
}
static long p241_clock_gettime(struct timespec64 *out){
 struct timespec t; if(clock_gettime(CLOCK_MONOTONIC,&t))return -errno;
 out->tv_sec=t.tv_sec;out->tv_nsec=t.tv_nsec;return 0;
}
static long p282_deadline_after(long seconds,struct timespec64 *out){
 long rc=p241_clock_gettime(out);out->tv_sec+=seconds;return rc;
}
static int p282_deadline_expired(const struct timespec64 *d){
 struct timespec64 n;p241_clock_gettime(&n);
 return n.tv_sec>d->tv_sec || (n.tv_sec==d->tv_sec && n.tv_nsec>=d->tv_nsec);
}
static void p282_poll_delay(void){usleep(1000);}
static long p260_write_all(int fd,const char *p,size_t n,long seconds){
 struct timespec64 d;p282_deadline_after(seconds,&d);
 while(n){long a=sys_write(fd,p,n);if(a>0){p+=a;n-=a;continue;}
  if(a!=-EAGAIN && a!=-EINTR)return a?a:-EIO;
  if(p282_deadline_expired(&d))return -ETIMEDOUT;p282_poll_delay();}
 return 0;
}
static int p260_bytes_equal(const char *a,const char *b,size_t n){return memcmp(a,b,n)==0;}
static const uint8_t k_run_id[16]={RUN_BYTES};
static struct s22plus_p318_banner_result s22plus_p318_banner_attempt(int fd){
 const char *b="S22PLUS-FYG8-E3:RUN_HEX\n";
 return (struct s22plus_p318_banner_result){p260_write_all(fd,b,49,2)==0};
}
'''

WITNESS = r'''
static long p345_exec_command(int fd,uint32_t seq,const uint8_t *cmd,
 uint16_t size,const uint8_t nonce[32],uint8_t *cancel){
 if(seq==4)return native_exec(fd,seq,cmd,size,nonce,cancel);
 const char *value=seq==3?"uid=0 gid=0\n":"P328-NONCE RUN_HEX\n";
 long rc=p328_write_frame(fd,P328_FRAME_DATA,seq,(const uint8_t*)value,strlen(value));
 if(rc)return rc;
 uint8_t out[24]={0};p328_store_le32(out+12,strlen(value));
 return p328_write_frame(fd,P328_FRAME_EXIT,seq,out,24);
}
'''


def source(selected_runtime=runtime):
    runtime = selected_runtime
    parser = (ROOT/'workspace/public/src/native-init/s22plus_fyg8_p318_max77705_result_parser.inc.c').read_text()
    sha = parser[parser.index('struct s22plus_max77705_runtime_sha256 {'):
                 parser.index('static int s22plus_max77705_runtime_expect(')]
    sha += parser[parser.index('static uint32_t s22plus_max77705_runtime_rotr('):
                  parser.index('static int s22plus_max77705_runtime_active_timeout_slot(')]
    helper = runtime.build_helper(runtime.fixture_child_source()).decode()
    helper = helper.replace('P328_AUTH_KEY_BYTES', ','.join(['107'] * 32))
    helper = helper.replace('static long p345_exec_command(', 'static long native_exec(', 1)
    anchor = 'static long p345_framed_console('
    helper = helper.replace(anchor, WITNESS + '\n' + anchor, 1)
    main = r'''
int main(int argc,char **argv){
 if(argc!=3)return 2;int fd=atoi(argv[1]),count=atoi(argv[2]);
 if(prctl(PR_SET_CHILD_SUBREAPER,1))return 3;
 uint8_t boot[32];memset(boot,'b',32);
 for(int i=0;i<count;i++){uint8_t seen=0;long rc=p345_framed_console(fd,boot,&seen);
  if(rc){fprintf(stderr,"console rc=%ld session=%d\n",rc,i);return 4;}}
 return 0;
}
'''
    return (PREFIX + sha + helper + main).replace('RUN_HEX', runtime.P345_RUN_ID_HEX).replace(
        'RUN_BYTES', ','.join(str(x) for x in runtime.P345_RUN_ID))


class CJoinTests(unittest.TestCase):
    runtime = runtime
    def test_real_c_normal_nonzero_cancel_timeout_and_next_same_fd(self):
        runtime = self.runtime
        # Actual 15-second timeout is intentionally retained, not accelerated.
        cases = [('printf hello', 'ok', False), ('exit 7', 'command-failed', False),
                 ('printf started; /bin/busybox sleep 30', 'cancelled', True),
                 ('/bin/busybox sleep 30', 'timeout', False),
                 ('x=$(printf next); printf "%s" "$x"', 'ok', False)]
        observer = live._open_header_initial_observer_module(
            runtime, live.p344_open_read_observer, 'p345-local-c-join')
        with tempfile.TemporaryDirectory(prefix='p345-c-join-') as directory:
            root = Path(directory); binary = root/'peer'
            build = subprocess.run(['cc','-x','c','-','-o',str(binary),
                '-O2','-Wall','-Wextra','-Wno-deprecated-declarations',
                '-Wno-unused-function','-Wno-misleading-indentation'],
                input=source(runtime).encode(), capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr.decode())
            host, peer = socket.socketpair()
            host.setblocking(False); peer.setblocking(False)
            process = subprocess.Popen([str(binary),str(peer.fileno()),str(len(cases))],
                pass_fds=(peer.fileno(),),stderr=subprocess.PIPE)
            peer.close()
            try:
                seen = set()
                for ordinal,(cmd,wanted,cancel) in enumerate(cases):
                    writer = raw.RawCaptureWriter(root,f'rx-{ordinal}',
                        stdout_maximum=512*1024,stderr_maximum=4096)
                    started = time.monotonic()
                    result = exchange.exchange(observer,host.fileno(),b'k'*32,cmd,
                        hashlib.sha256(b'b'*32).hexdigest(),seen,writer,
                        deadline=started+22,
                        cancel_requested=lambda: cancel and time.monotonic()-started>.15)
                    self.assertEqual(result.outcome,wanted)
                    self.assertTrue(result.session.audit.done_seen)
                    receipt = writer.finalize(returncode=0)
                    self.assertEqual(raw.read_stdout(receipt,maximum=512*1024),
                                     bytes(result.session.audit.rx))
                self.assertEqual(process.wait(timeout=3),0,process.stderr.read().decode())
            finally:
                host.close()
                if process.poll() is None: process.kill()
                process.wait(timeout=3); process.stderr.close()


if __name__ == '__main__': unittest.main()
