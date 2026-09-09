"""Real AArch64 status parsers and fixed-interface collection, H0 only."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
SOURCE = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include "s22plus_status_metrics_v1.inc.c"
int main(int argc,char **argv) {
 if(argc==2&&!strcmp(argv[1],"fd3")) {
  assert(fcntl(3,F_GETFD)==0&&(fcntl(3,F_GETFL)&O_NONBLOCK));
  assert(fcntl(512,F_GETFD)==-1&&errno==EBADF);
  struct status_metrics wire;
  for(unsigned i=0;i<1000;i++){ssize_t n=recv(3,&wire,sizeof(wire),MSG_TRUNC);if(n==72){assert(wire.magic==0x31545353U);return 0;}assert(n<0&&errno==EAGAIN);usleep(1000);}return 99;
 }
 assert(argc==2);
 int inherited[2];assert(!socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_NONBLOCK|SOCK_CLOEXEC,0,inherited));
 int extra=open("/dev/null",O_RDONLY);assert(extra>=0&&dup2(extra,512)==512);
 pid_t receiver=fork();assert(receiver>=0);
 if(!receiver){assert(dup2(inherited[1],3)==3);assert(!syscall(SYS_close_range,4,0xffffffffU,0));execl(argv[1],argv[1],argv[0],"fd3",NULL);_exit(98);}
 struct status_metrics packet={.magic=0x31545353U};assert(send(inherited[0],&packet,72,MSG_NOSIGNAL)==72);
 int receiver_status;assert(waitpid(receiver,&receiver_status,0)==receiver&&WIFEXITED(receiver_status)&&!WEXITSTATUS(receiver_status));
 close(inherited[0]);close(inherited[1]);close(extra);close(512);
 struct status_metrics m={0};
 assert(status_memory("MemTotal: 100 kB\nMemAvailable: 40 kB\n",&m));
 assert(m.mem_total_kib==100&&m.mem_available_kib==40&&m.valid==STATUS_MEM);
 assert(!status_memory("MemTotal: 100 kB\nMemAvailable: 101 kB\n",&m));
 assert(!status_memory("MemTotal: 100 kB\nMemTotal: 100 kB\nMemAvailable: 1 kB\n",&m));
 assert(!status_memory("MemTotal: 100 kB\nMemAvailable: 40 MB\n",&m));
 assert(!status_memory("MemTotal: 18446744073709551616 kB\nMemAvailable: 1 kB\n",&m));
 int64_t n;assert(status_scalar("-12\n",&n)&&n==-12);assert(!status_scalar("12x\n",&n));
 struct status_cpu prior={0};m=(struct status_metrics){0};
 status_cpu_sample("cpu  100 0 100 800 0 0 0 0 50 0\n",&prior,&m);assert(!m.valid);
 status_cpu_sample("cpu  150 0 100 950 0 0 0 0 75 0\n",&prior,&m);assert(m.valid==STATUS_CPU&&m.cpu_permille==250);
 m.valid=0;status_cpu_sample("cpu  150 0 100 950 0 0 0 0\n",&prior,&m);assert(!m.valid);
 status_cpu_sample("cpu  149 0 100 960 0 0 0 0\n",&prior,&m);assert(!m.valid);
 status_cpu_sample("cpu broken\n",&prior,&m);assert(!prior.valid);
 status_cpu_sample("cpu  150 0 100 970 0 0 0 0\n",&prior,&m);assert(!m.valid);
 char text[8192];assert(status_read("/proc/meminfo",text,sizeof(text),0x9fa0L));
 assert(status_memory(text,&m));assert(!status_read("/proc/meminfo",text,4,0x9fa0L));
 assert(!status_read("/proc/meminfo",text,sizeof(text),0x62656572L));
 int pair[2];assert(!socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_NONBLOCK,0,pair));
 pid_t child=fork();assert(child>=0);
 if(!child){close(pair[0]);assert(dup2(pair[1],1)==1);close(pair[1]);_exit(status_collect("c377f1e0a90b5e6d7c8a9b0c1d2e3f0b"));}
 close(pair[1]);unsigned samples=0;
 for(unsigned attempt=0;attempt<400&&samples<2;attempt++) {
  struct status_metrics wire;ssize_t got=recv(pair[0],&wire,sizeof(wire),MSG_TRUNC);
  if(got<0){assert(errno==EAGAIN);usleep(10000);continue;}
  assert(got==72&&wire.magic==0x31545353U&&wire.sequence==samples+1&&wire.reserved==0);
  assert(wire.valid&STATUS_MEM);if(samples)assert(wire.valid&STATUS_CPU);else assert(!(wire.valid&STATUS_CPU));++samples;
 }
 assert(samples==2);assert(!kill(child,SIGKILL));int status;assert(waitpid(child,&status,0)==child);close(pair[0]);
 puts("PASS ARM64 fixed collector and missing malformed counter boundaries");return 0;
}
'''


class StatusMetrics(unittest.TestCase):
    def test_real_arm64(self):
        compiler = shutil.which('aarch64-linux-gnu-gcc')
        qemu = shutil.which('qemu-aarch64')
        self.assertTrue(compiler and qemu)
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / 'probe'
            build = subprocess.run([compiler, '-x', 'c', '-', '-I', str(ROOT / 'workspace/public/src/native-init'), '-static', '-O2', '-Wall', '-Wextra', '-Werror', '-o', str(binary)], input=SOURCE, text=True, capture_output=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertIn('ARM aarch64', subprocess.check_output(['file', binary], text=True))
            run = subprocess.run([qemu, binary, qemu], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('PASS ARM64', run.stdout)


if __name__ == '__main__':
    unittest.main()
