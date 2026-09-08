"""Exact target UAPI and real AArch64 eventfd fork/dup/exec behavior (H0)."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
KERNEL=ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel'
SOURCE=r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/eventfd.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
_Static_assert(SYS_eventfd2==19,"exact ARM64 syscall");
_Static_assert(EFD_CLOEXEC==02000000 && EFD_NONBLOCK==04000,"exact ARM64 flags");
static uint64_t receive(int fd){uint64_t value=0;for(int i=0;i<1000;i++){ssize_t n=read(fd,&value,8);if(n==8)return value;assert(n==-1&&errno==EAGAIN);usleep(1000);}abort();}
int main(int argc,char **argv){
 if(argc==2&&!strcmp(argv[1],"child")){
  assert((fcntl(0,F_GETFL)&O_NONBLOCK)!=0);assert(fcntl(0,F_GETFD)==0);
  assert(receive(0)==1);assert(receive(0)==2);_exit(7);
 }
 assert(argc==2);int fd=(int)syscall(19,0,02000000|04000);assert(fd>2);
 uint64_t v=0;assert(read(fd,&v,8)==-1&&errno==EAGAIN);
 assert(fcntl(fd,F_GETFD)==FD_CLOEXEC);assert(fcntl(fd,F_GETFL)&O_NONBLOCK);
 pid_t child=fork();assert(child>=0);
 if(!child){assert(dup2(fd,0)==0);assert(close(fd)==0);execl(argv[1],argv[1],argv[0],"child",NULL);_exit(99);}
 v=1;assert(write(fd,&v,8)==8);usleep(200000);v=2;assert(write(fd,&v,8)==8);
 int status=0;assert(waitpid(child,&status,0)==child);assert(WIFEXITED(status)&&WEXITSTATUS(status)==7);
 assert(fcntl(fd,F_GETFL)&O_NONBLOCK);assert(fcntl(fd,F_GETFD)==FD_CLOEXEC);
 /* Child exit does not make eventfd writes fail: ACK is queueing only. */
 v=1;assert(write(fd,&v,8)==8);v=2;assert(write(fd,&v,8)==8);assert(read(fd,&v,8)==8&&v==3);
 v=UINT64_MAX-1;assert(write(fd,&v,8)==8);v=1;assert(write(fd,&v,8)==-1&&errno==EAGAIN);
 assert(read(fd,&v,8)==8&&v==UINT64_MAX-1);assert(close(fd)==0);
 puts("PASS ARM64 eventfd fork dup exec nonblocking queue-only coalescing backpressure");return 0;
}
'''

class Arm64EventfdTests(unittest.TestCase):
    def test_exact_target_uapi(self):
        paths={
            'include/uapi/asm-generic/unistd.h':['#define __NR_eventfd2 19'],
            'include/linux/eventfd.h':['#define EFD_CLOEXEC O_CLOEXEC','#define EFD_NONBLOCK O_NONBLOCK'],
            'include/uapi/asm-generic/fcntl.h':['#define O_NONBLOCK\t00004000','#define O_CLOEXEC\t02000000'],
            'arch/arm64/include/uapi/asm/unistd.h':['#include <asm-generic/unistd.h>'],
            'arch/arm64/include/uapi/asm/fcntl.h':['#include <asm-generic/fcntl.h>'],
        }
        for relative,needles in paths.items():
            text=(KERNEL/relative).read_text()
            for needle in needles:self.assertIn(needle,text,relative)

        arm=(KERNEL/'arch/arm64/include/uapi/asm/fcntl.h').read_text()
        self.assertNotIn('#define O_NONBLOCK',arm);self.assertNotIn('#define O_CLOEXEC',arm)

    def test_real_aarch64_fork_dup_exec_and_eventfd_semantics(self):
        compiler=shutil.which('aarch64-linux-gnu-gcc');qemu=shutil.which('qemu-aarch64')
        self.assertIsNotNone(compiler);self.assertIsNotNone(qemu)
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'probe'
            p=subprocess.run([compiler,'-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-o',str(binary)],input=SOURCE,text=True,capture_output=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr)
            result=subprocess.run(['file',str(binary)],capture_output=True,text=True,check=True)
            self.assertIn('ARM aarch64',result.stdout)
            p=subprocess.run([qemu,str(binary),qemu],capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('PASS ARM64 eventfd fork dup exec',p.stdout)

if __name__=='__main__':unittest.main()
