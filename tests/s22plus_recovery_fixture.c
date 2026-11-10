/* H0 only. Host/user-QEMU always intercept reboot. System-QEMU uses real
 * RESTART2 only from a standalone PID1 image with explicit VM compilation. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#define CANARY_H0_VM
#define CANARY_DOWNLOAD_RAM
#include "protocol.h"
static const uint8_t canary_key[32]={1}, canary_id[32]={2};
static uint64_t deadline=540000;
static int platform_ok=1;
static pid_t fixture_child;
static int download_ready(void) { return platform_ok; }
static int read_small(const char *p,void *v,size_t n,size_t *s)
{ (void)p;(void)v;(void)n;(void)s;return ENOENT; }
static int transfer(int fd,void *data,size_t size,int write_mode)
{
    (void)fd;(void)write_mode;
    printf("FRAME ");for(size_t i=0;i<size;i++)printf("%02x",((uint8_t*)data)[i]);puts("");
    return 0;
}
#ifdef G0Q_TEST_VM
static uint64_t now_ms(void)
{
    struct timespec t;if(clock_gettime(CLOCK_BOOTTIME,&t))return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;
}
#else
static struct { volatile uint64_t time,called_at; volatile unsigned calls; } *state;
static uint64_t now_ms(void) { return state->time; }
static long fixture_syscall(long number,...)
{
    va_list ap;va_start(ap,number);
    int a=va_arg(ap,int),b=va_arg(ap,int),c=va_arg(ap,int);const char *s=va_arg(ap,const char*);
    va_end(ap);
    if(number!=SYS_reboot || a!=(int)0xfee1dead || b!=672274793 || c!=(int)0xa1b2c3d4 || strcmp(s,"download"))_exit(99);
    state->calls++;state->called_at=now_ms();errno=EPERM;return -1;
}
static int fixture_poll(struct pollfd *p,nfds_t n,int timeout)
{ return poll(p,n,timeout>5?5:timeout); }
static pid_t fixture_fork(void)
{ pid_t p=fork();if(p>0)fixture_child=p;return p; }
#define syscall fixture_syscall
#define poll fixture_poll
#define fork fixture_fork
#endif
#include "recovery.h"
#ifndef G0Q_TEST_VM
#undef syscall
#undef poll
#undef fork
static int wait_child(void)
{
    int status;struct rusage usage;
    for(unsigned i=0;i<400;i++) {
        pid_t p=wait4(fixture_child,&status,WNOHANG,&usage);
        if(p==fixture_child) {
            printf("RESULT %u %llu %ld %ld %d\n",state->calls,(unsigned long long)state->called_at,
                   usage.ru_utime.tv_sec*1000000+usage.ru_utime.tv_usec,
                   usage.ru_stime.tv_sec*1000000+usage.ru_stime.tv_usec,status);
            return 0;
        }
        usleep(5000);
    }
    kill(fixture_child,SIGKILL);waitpid(fixture_child,NULL,0);return 95;
}
#endif

int main(int argc,char **argv)
{
    signal(SIGPIPE,SIG_IGN);
#ifdef G0Q_TEST_VM
    (void)argc;(void)argv;
    if(getpid()!=1)return 90;
    mkdir("/dev",0755);mount("devtmpfs","/dev","devtmpfs",0,NULL);
    int console=open("/dev/ttyAMA0",O_RDWR);if(console<0)return 91;
    for(int i=0;i<3;i++)dup2(console,i);
    if(console>2)close(console);
    pid_t observer=fork();if(observer<0)return 92;
    if(observer) { for(;;)wait(NULL); }
    if(recovery_begin())_exit(93);
    printf("RECOVERY_VM_ARMED %llu\n",(unsigned long long)now_ms());fflush(stdout);
#ifdef G0Q_TEST_VM_COMMIT
    uint8_t nonce[32]={3};if(recovery_probe(nonce,1)||recovery_commit(nonce))_exit(94);
#endif
    /* Observer is hung, while independent child and kernel stay schedulable. */
    for(;;)pause();
#else
    if(argc!=2)return 2;
    state=mmap(NULL,sizeof(*state),PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
    if(state==MAP_FAILED)return 3;
    state->time=1000;
    if(!strcmp(argv[1],"bad-platform"))platform_ok=0;
    if(!strcmp(argv[1],"late-start"))state->time=120000;
    int e=recovery_begin();
    if(!platform_ok||state->time==120000) {printf("REFUSED %d %d\n",e,(int)fixture_child);return e?0:4;}
    if(e)return 5;
    uint8_t nonce[32]={3},base[G0Q_RESPONSE_SIZE]={0};memset(base+40,3,32);memset(base+72,4,16);
    if(recovery_frame(-1,base,base+40,0))return 6;
    if(!strcmp(argv[1],"normal")) {
        if(recovery_frame(-1,base,nonce,1)||recovery_commit(nonce))return 7;
        if(recovery_commit(nonce)==0)return 8;
    } else if(!strcmp(argv[1],"early")) {
        if(recovery_commit(nonce))return 9;
        usleep(20000);if(state->calls)return 10;state->time=555000;
    } else if(!strcmp(argv[1],"killed")) {
        kill(fixture_child,SIGKILL);usleep(20000);
        if(!recovery_probe(nonce,1)||recovery_begin()!=EALREADY)return 11;
        state->time=555000;
    } else if(!strcmp(argv[1],"eof")) {
        close(recovery_fd);recovery_fd=-1;usleep(30000);if(state->calls)return 12;
        state->time=555000;
    } else if(!strcmp(argv[1],"flood")) {
        uint8_t msg[33]={'P'};
        for(unsigned i=0;i<5000;i++)(void)send(recovery_fd,msg,sizeof(msg),MSG_DONTWAIT|MSG_NOSIGNAL);
        state->time=555000;
    } else if(!strcmp(argv[1],"malformed")) {
        uint8_t msg[34]={'C'};(void)send(recovery_fd,msg,sizeof(msg),MSG_DONTWAIT|MSG_NOSIGNAL);
        usleep(20000);if(state->calls)return 13;state->time=555000;
    } else if(!strcmp(argv[1],"expired"))state->time=570000;
    else if(!strcmp(argv[1],"commit-expired")) {
        if(recovery_probe(nonce,1))return 14;
        state->time=540000;
        if(recovery_commit(nonce)!=ETIMEDOUT)return 15;
        state->time=555000;
    } else if(!strcmp(argv[1],"child-late-commit")) {
        if(recovery_probe(nonce,1))return 17;
        state->time=540000;
        uint8_t msg[33]={'C'};(void)send(recovery_fd,msg,sizeof(msg),MSG_DONTWAIT|MSG_NOSIGNAL);
        usleep(20000);if(state->calls)return 18;state->time=555000;
    } else if(!strcmp(argv[1],"timer"))state->time=555000;
    else return 16;
    return wait_child();
#endif
}
