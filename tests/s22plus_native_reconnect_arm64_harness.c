/* Compile as AArch64 and use actual inherited host PTYs through qemu-user.
 * Only /dev/ttyGS0's path is mapped to the explicit test PTY. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/syscall.h>

#define S22PLUS_P318_ERRNO_EPIPE 32
#define UR1_IDLE_LINK_LOST (-4096L)
struct timespec64 {int64_t tv_sec,tv_nsec;};
static const char *route;
static long negative(long n){return n<0?-errno:n;}
static long sys_close(int fd){return negative(syscall(57,fd));}
static long sys_openat(const char *path,int flags,int mode){
    assert(!strcmp(path,"/dev/ttyGS0")&&flags==(00000002|00000400|00004000|02000000)&&mode==0);
    return negative(syscall(56,-100,route,flags,mode));
}
static long p260_ioctl(int fd,unsigned long op,void *arg){return negative(syscall(29,fd,op,arg));}
static long local_pre_auth(void){return 0;}
static long baseline_check(void){return 0;}
static long p282_deadline_after(long seconds,struct timespec64 *out){
    struct timespec t;assert(clock_gettime(CLOCK_BOOTTIME,&t)==0);
    out->tv_sec=t.tv_sec+seconds;out->tv_nsec=t.tv_nsec;return 0;
}
static int p282_deadline_expired(struct timespec64 *end){
    struct timespec t;assert(clock_gettime(CLOCK_BOOTTIME,&t)==0);
    return t.tv_sec>end->tv_sec||(t.tv_sec==end->tv_sec&&t.tv_nsec>=end->tv_nsec);
}
static void p282_poll_delay(void){usleep(1000);}

#include "owned-tty.h"

int main(int argc,char **argv){
    assert(argc==3);int fd=atoi(argv[1]);route=argv[2];char byte;
    _Static_assert(sizeof(struct p260_termios)==36,"target termios size");
    /* Host supplied raw VMIN=0/VTIME=0: real empty read is zero. */
    assert(syscall(63,fd,&byte,1)==0);
    assert(ur1_raw(fd)==0);
    assert(syscall(63,fd,&byte,1)==-1&&errno==EAGAIN);
    puts("READY normalized empty EAGAIN");fflush(stdout);
    assert(getchar()=='H');
    assert(syscall(63,fd,&byte,1)==0);
    assert(ur1_raw(fd)==UR1_IDLE_LINK_LOST);
    assert(ur1_close(&fd)==0&&fd==-1);
    assert(ur1_open(&fd)==0&&fd>=0);
    assert(syscall(63,fd,&byte,1)==-1&&errno==EAGAIN);
    assert(ur1_close(&fd)==0&&fd==-1);
    puts("PASS ARM64 real raw ioctl, empty read, hangup, close and fixed-path reopen");
    return 0;
}
