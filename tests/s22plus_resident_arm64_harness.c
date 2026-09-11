/* Exact raw syscall operands from resident PID1, executed as real AArch64. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include "s22plus_resident_v1/wire.h"
static long raw(long n,long a,long b,long c,long d,long e,long f) {
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");
    return x0;
}
_Static_assert(SYS_clock_gettime==113 && CLOCK_BOOTTIME==7 && SYS_ftruncate==46 && SYS_lseek==62,"clock/file UAPI");
_Static_assert(SYS_socketpair==199 && SYS_sendto==206 && SYS_recvfrom==207 && SYS_close_range==436,"IPC UAPI");
_Static_assert(O_NOFOLLOW==0100000 && O_NONBLOCK==04000 && O_CLOEXEC==02000000,"ARM64 flag overrides");
int main(void) {
    struct timespec stamp;assert(raw(113,7,(long)&stamp,0,0,0,0)==0 && stamp.tv_sec>=0);
    char directory[]="/tmp/s22-resident-arm64-XXXXXX";assert(mkdtemp(directory));
    char path[128],link[128];snprintf(path,sizeof(path),"%s/log",directory);snprintf(link,sizeof(link),"%s/link",directory);
    int file=(int)raw(56,-100,(long)path,00000001|00000100|00000200|0100000|02000000,0400,0,0);assert(file>2);
    assert(fcntl(file,F_GETFD)==FD_CLOEXEC);assert(write(file,"old trailing bytes",18)==18);
    assert(raw(46,file,0,0,0,0,0)==0 && raw(62,file,0,0,0,0,0)==0);
    assert(write(file,"complete\n",9)==9);struct stat st;assert(!fstat(file,&st) && st.st_size==9);assert(!close(file));
    assert(!symlink(path,link));assert(raw(56,-100,(long)link,0100000,0,0,0)==-ELOOP);
    assert(!unlink(link) && !unlink(path) && !rmdir(directory));
    int pair[2];assert(raw(199,1,5|04000|02000000,0,(long)pair,0,0)==0);
    assert(fcntl(pair[0],F_GETFL)&O_NONBLOCK);assert(fcntl(pair[1],F_GETFD)==FD_CLOEXEC);
    struct status_metrics sample={.magic=RESIDENT_SAMPLE_MAGIC,.sequence=0x100000001ULL};
    assert(raw(206,pair[0],(long)&sample,128,0x4000|0x40,0,0)==128);
    struct status_metrics got;assert(raw(207,pair[1],(long)&got,128,0x20|0x40,0,0)==128);assert(got.sequence==sample.sequence);
    struct hud_snapshot view={.magic=RESIDENT_VIEW_MAGIC,.sequence=~0ULL};
    assert(raw(206,pair[0],(long)&view,304,0x4000|0x40,0,0)==304);
    assert(raw(207,pair[1],(long)&got,128,0x20|0x40,0,0)==304); /* oversized frame detected */
    assert(raw(207,pair[1],(long)&view,304,0x20|0x40,0,0)==-EAGAIN);
    unsigned sent=0;long rc;
    while((rc=raw(206,pair[0],(long)&view,304,0x4000|0x40,0,0))==304)assert(++sent<10000);
    assert(rc==-EAGAIN && sent>0);
    for(unsigned i=0;i<sent;i++)assert(raw(207,pair[1],(long)&view,304,0x20|0x40,0,0)==304);
    assert(!close(pair[1]));assert(raw(206,pair[0],(long)&view,304,0x4000|0x40,0,0)==-EPIPE);assert(!close(pair[0]));
    int extra=open("/dev/null",O_RDONLY|O_CLOEXEC);assert(extra>=3);
    assert(raw(436,3,0xffffffffU,0,0,0,0)==0);assert(fcntl(extra,F_GETFD)==-1 && errno==EBADF);
    puts("PASS ARM64 resident raw clock export flags 128/304-byte IPC backpressure truncation and close_range");return 0;
}
