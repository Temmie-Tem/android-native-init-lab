"""Compile actual inherited C command/cleanup functions; no device contact."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p344_open_read_branch_runtime as runtime
import s22plus_fyg8_research_shell_child as child


def function(source, name):
    start = source.index('static long '+name+'(')
    end = source.index('\n}', start)+2
    return source[start:end]


PREFIX = r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#define EAGAIN 11
#define EIO 5
#define ETIMEDOUT 110
#define SIGKILL 9
#define WNOHANG 1
#define O_CLOEXEC 0
#define O_NONBLOCK 0
#define O_RDONLY 0
#define P260_EPROTO 71
#define P260_EINTR 4
#define P328_ECHILD 10
#define P328_MAX_COMMAND 1023
#define P328_MAX_PAYLOAD 1055
#define P328_MAX_OUTPUT 131072
#define P328_COMMAND_TIMEOUT_SEC 15LL
#define P328_FRAME_DATA 130
#define P328_FRAME_EXIT 131
#define P328_FLAG_TRUNCATED 2
#define P328_FLAG_TIMEOUT 1
#define P328_FLAG_EXEC_FAILURE 4
struct timespec64 { int64_t tv_sec, tv_nsec; };
static int mode, ticks, reads, kills, exit_flags, direct_killed;
static long p282_deadline_after(long seconds, struct timespec64 *d) { d->tv_sec=ticks+seconds; return 0; }
static int p282_deadline_expired(const struct timespec64 *d) { return ticks>=d->tv_sec; }
static void p282_poll_delay(void) {}
static long p241_clock_gettime(struct timespec64 *d) { d->tv_sec=ticks; d->tv_nsec=0; return 0; }
static long sys_kill(long pid,int sig) { (void)sig; if(pid<0)kills++;else direct_killed=1; return 0; }
static long sys_wait4(long pid,int *status,int options) {
 (void)options; *status=direct_killed?9:0;
 if(pid<0){if(mode==3){ticks++;return 42;}return -P328_ECHILD;}
 return mode==2&&!direct_killed?0:pid;
}
static long sys_read(int fd,void *buf,size_t size) {
 (void)fd;(void)size; reads++; ticks++; *(char*)buf='x';
 if(reads>100)exit(90); /* deterministic assertion, not an unbounded fixture */
 return mode==0&&reads>1?0:mode==2?-EAGAIN:1;
}
static long sys_close(int fd) { (void)fd;return 0; }
static long sys_pipe2(int *fds,int flags) { (void)flags;fds[0]=3;fds[1]=4;return 0; }
static long sys_clone(void) { return 42; }
static long p328_setsid(void) { return 42; }
static long p328_dup_to(int source,int target) { (void)source;return target; }
static long sys_openat(const char *p,int flags,int mode_) { (void)p;(void)flags;(void)mode_;return 0; }
static void sys_exit(int code) { exit(code); }
static long sys_execve(const char *p,char *const *a,char *const *e) { (void)p;(void)a;(void)e;return 0; }
static int p335_command_valid(uint32_t s,const uint8_t *p,uint16_t n) { (void)s;(void)p;(void)n;return 1; }
static long p328_reap_after_kill(long pid,int *status) { (void)pid;*status=9;return 0; }
static uint64_t p328_elapsed_ms(const struct timespec64 *a,const struct timespec64 *b) { return (uint64_t)(b->tv_sec-a->tv_sec)*1000; }
static void p328_store_le32(uint8_t *p,uint32_t v) { memcpy(p,&v,4); }
static void p328_store_le64(uint8_t *p,uint64_t v) { memcpy(p,&v,8); }
static long p328_write_frame(int fd,int type,uint32_t seq,const void *p,uint16_t n) {
 (void)fd;(void)seq;(void)n;if(type==P328_FRAME_EXIT)memcpy(&exit_flags,p,4);return 0;
}
'''
MAIN = r'''
int main(int argc,char **argv) {
 mode=argc>1?atoi(argv[1]):0;
 long rc=p328_exec_command(5,4,(const uint8_t*)"true",4);
 if(kills!=1)return 10;
 if(mode==3)return rc==-ETIMEDOUT?0:11;
 if(rc!=0)return 12;
 if(mode==1&&!(exit_flags&P328_FLAG_TRUNCATED))return 13;
 if(mode==2&&!(exit_flags&P328_FLAG_TIMEOUT))return 14;
 if(mode==0&&exit_flags)return 15;
 return 0;
}
'''


class ShellChildTests(unittest.TestCase):
    def test_actual_c_normal_timeout_descendant_and_cleanup_bounds(self):
        original=runtime.P344_HELPER
        transformed=child.bound_child_drain(original)
        with self.assertRaises(ValueError):child.bound_child_drain(transformed)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for label, helper in [('old',original),('new',transformed)]:
                text=helper.decode()
                source=PREFIX+'\n'+function(text,'p328_cleanup_process_group')+'\n'+function(text,'p328_exec_command')+MAIN
                path=root/(label+'.c');path.write_text(source)
                exe=root/label
                build=subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2',str(path),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(build.returncode,0,build.stderr)
                if label=='new':
                    subprocess.run(['aarch64-linux-gnu-gcc','-std=c11','-Wall','-Wextra','-Werror','-O2','-c',str(path),'-o',str(root/'new-aarch64.o')],check=True,capture_output=True)
                    description=subprocess.check_output(['file',str(root/'new-aarch64.o')],text=True)
                    self.assertIn('ARM aarch64',description)
                    for mode in (0,1,2,3):
                        self.assertEqual(subprocess.run([str(exe),str(mode)],timeout=2).returncode,0)
                else:
                    self.assertEqual(subprocess.run([str(exe),'1'],timeout=2).returncode,90)


if __name__=='__main__':unittest.main()
