"""Exact target UAPI and real AArch64 HUD IPC/process-group behavior, H0."""
from pathlib import Path
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
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
_Static_assert(O_WRONLY==1 && O_CREAT==0100 && O_EXCL==0200 && O_NOFOLLOW==0100000,"target log flags");
_Static_assert(SYS_socketpair==199 && SYS_sendto==206 && SYS_close_range==436,"target syscalls");
_Static_assert(AF_UNIX==1 && SOCK_SEQPACKET==5 && MSG_NOSIGNAL==0x4000,"target socket constants");
_Static_assert(SOCK_NONBLOCK==04000 && SOCK_CLOEXEC==02000000,"target socket flags");
int main(int argc,char **argv){
 if(argc==2&&!strcmp(argv[1],"child")){
  assert(fcntl(0,F_GETFL)&O_NONBLOCK);assert(fcntl(0,F_GETFD)==0);
  assert(fcntl(512,F_GETFD)==-1&&errno==EBADF);char bytes[40];
  for(int i=0;i<1000;i++){ssize_t n=recv(0,bytes,sizeof(bytes),MSG_TRUNC);if(n==40){assert(bytes[0]==42);_exit(7);}assert(n<0&&errno==EAGAIN);usleep(1000);}_exit(99);
 }
 assert(argc==2);char directory[]="/tmp/s22-hud-arm64-XXXXXX";assert(mkdtemp(directory));char target[128],link[128];snprintf(target,sizeof(target),"%s/log",directory);snprintf(link,sizeof(link),"%s/link",directory);
 int log=open(target,00000001|00000100|00000200|0100000|02000000,0400);assert(log>=0);assert(write(log,"HUD\n",4)==4);assert(close(log)==0);assert(symlink(target,link)==0);assert(open(link,O_RDONLY|0100000)==-1&&errno==ELOOP);assert(unlink(link)==0&&unlink(target)==0&&rmdir(directory)==0);
 int pair[2];assert(syscall(199,1,5|04000|02000000,0,pair)==0);
 assert(fcntl(pair[0],F_GETFD)==FD_CLOEXEC);char bytes[40]={42};unsigned sent=0;
 while(send(pair[0],bytes,sizeof(bytes),MSG_NOSIGNAL)==40){assert(++sent<100000);}
 assert(errno==EAGAIN&&sent>0);
 for(unsigned i=0;i<sent;i++)assert(recv(pair[1],bytes,sizeof(bytes),MSG_TRUNC)==40);
 assert(recv(pair[1],bytes,sizeof(bytes),MSG_TRUNC)==-1&&errno==EAGAIN);
 assert(close(pair[1])==0);assert(send(pair[0],bytes,sizeof(bytes),MSG_NOSIGNAL)==-1&&errno==EPIPE);assert(close(pair[0])==0);
 assert(socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_NONBLOCK|SOCK_CLOEXEC,0,pair)==0);
 int extra=open("/dev/null",O_RDONLY);assert(extra>=0&&dup2(extra,512)==512);
 pid_t hud=fork();assert(hud>=0);
 if(!hud){assert(setsid()>0);assert(dup2(pair[1],0)==0);assert(syscall(436,3,0xffffffffU,0)==0);execl(argv[1],argv[1],argv[0],"child",NULL);_exit(98);}
 assert(close(pair[1])==0);assert(close(extra)==0);assert(close(512)==0);
 assert(send(pair[0],bytes,sizeof(bytes),MSG_NOSIGNAL)==40);int status=0;assert(waitpid(hud,&status,0)==hud&&WIFEXITED(status)&&WEXITSTATUS(status)==7);assert(close(pair[0])==0);
 /* Separate ownership: cancelling a command process group cannot reap/kill HUD. */
 hud=fork();assert(hud>=0);if(!hud){assert(setsid()>0);for(;;)pause();}
 pid_t command=fork();assert(command>=0);if(!command){assert(setsid()>0);for(;;)pause();}
 usleep(100000);assert(kill(-command,SIGTERM)==0);assert(waitpid(command,&status,0)==command&&WIFSIGNALED(status));assert(waitpid(hud,&status,WNOHANG)==0);
 assert(kill(hud,SIGKILL)==0);assert(waitpid(hud,&status,0)==hud&&WIFSIGNALED(status));
 puts("PASS ARM64 snapshots full broken channel CLOEXEC close_range and group isolation");return 0;
}
'''

class HudArm64(unittest.TestCase):
    def test_exact_target_uapi(self):
        mapping={
            'include/uapi/asm-generic/unistd.h':['#define __NR_socketpair 199','#define __NR_sendto 206','#define __NR_close_range 436'],
            'include/linux/net.h':['SOCK_SEQPACKET\t= 5'],
            'arch/arm64/include/uapi/asm/fcntl.h':['#define O_NOFOLLOW\t0100000'],
            'include/linux/socket.h':['#define MSG_NOSIGNAL\t0x4000','#define AF_UNIX\t\t1'],
            'include/uapi/asm-generic/fcntl.h':['#define O_NONBLOCK\t00004000','#define O_CLOEXEC\t02000000'],
        }
        for path,needles in mapping.items():
            text=(KERNEL/path).read_text()
            for needle in needles:self.assertIn(needle,text,path)

    def test_real_aarch64_ipc_and_owned_process_groups(self):
        compiler=shutil.which('aarch64-linux-gnu-gcc');qemu=shutil.which('qemu-aarch64')
        self.assertTrue(compiler and qemu)
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'probe'
            p=subprocess.run([compiler,'-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-o',str(binary)],input=SOURCE,text=True,capture_output=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('ARM aarch64',subprocess.check_output(['file',binary],text=True))
            p=subprocess.run([qemu,binary,qemu],capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('PASS ARM64',p.stdout)

if __name__=='__main__':unittest.main()
