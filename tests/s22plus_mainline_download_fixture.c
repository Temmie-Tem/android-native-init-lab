/* Actual physical readiness and control implementation, fixed H0 syscalls.
 * No device paths can be opened; reset is replaced by a counted EIO return. */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdarg.h>
#include <time.h>
#include <stdlib.h>
#include <unistd.h>
static int fixture_open(const char *,int,...);
static char *fixture_realpath(const char *,char *);
static int fixture_clock(clockid_t,struct timespec *);
static long fixture_syscall(long,...);
#define open fixture_open
#define realpath fixture_realpath
#define clock_gettime fixture_clock
#define syscall fixture_syscall
#define main unused_canary_main
#define CANARY_DEBIAN_RAM
#define CANARY_DOWNLOAD_RAM
#include "../workspace/public/src/mainline/s22plus_canary_h0/init.c"
#undef open
#undef realpath
#undef clock_gettime
#undef syscall
#undef main

static const char *mode_file,*test_case;
static unsigned clocks,reads,resets;
static int delayed_binding;
static int fixture_open(const char *path,int flags,...) {
    if(strcmp(path,"/sys/class/reboot-mode/nvmem-reboot-mode/reboot_modes")||flags!=(O_RDONLY|O_CLOEXEC)) {
        errno=EPERM;return -1;
    }
    reads++;
    if(!strcmp(test_case,"expired-during-binding")&&reads>1)delayed_binding=1;
    if(!strcmp(test_case,"missing-modes")||(!strcmp(test_case,"binding-lost")&&reads>1)) {errno=ENOENT;return -1;}
    return open(mode_file,O_RDONLY|O_CLOEXEC);
}
static char *fixture_realpath(const char *path,char *resolved) {
    if(resolved)abort();
    if(!strcmp(test_case,"missing-link")) {errno=ENOENT;return NULL;}
    if(!strcmp(path,"/sys/bus/platform/devices/reboot-mode/driver"))
        return strdup(!strcmp(test_case,"wrong-driver")?"/sys/bus/platform/drivers/other":"/sys/bus/platform/drivers/nvmem-reboot-mode");
    if(!strcmp(path,"/sys/bus/platform/devices/reboot-mode/of_node"))
        return strdup(!strcmp(test_case,"wrong-node")?"/sys/firmware/devicetree/base/other":"/sys/firmware/devicetree/base/reboot-mode");
    errno=EPERM;return NULL;
}
static int fixture_clock(clockid_t which,struct timespec *t) {
    if(which!=CLOCK_BOOTTIME)abort();
    clocks++;
    t->tv_sec=1;t->tv_nsec=0;
    if(!strcmp(test_case,"expired")||(!strcmp(test_case,"expired-after-eof")&&clocks>=5)||delayed_binding)t->tv_sec=2;
    return 0;
}
static long fixture_syscall(long number,...) {
    va_list args;va_start(args,number);
    unsigned magic1=va_arg(args,unsigned),magic2=va_arg(args,unsigned),command=va_arg(args,unsigned);
    const char *text=va_arg(args,const char *);va_end(args);
    if(number!=SYS_reboot||magic1!=LINUX_REBOOT_MAGIC1||magic2!=LINUX_REBOOT_MAGIC2||
       command!=LINUX_REBOOT_CMD_RESTART2||strcmp(text,"download"))abort();
    resets++;errno=EIO;return -1;
}
int main(int argc,char **argv) {
    if(argc!=3)return 90;
    test_case=argv[1];mode_file=argv[2];
    if(!strncmp(test_case,"ready-",6)) {
        test_case+=6;printf("ready=%d\n",download_ready());return 0;
    }
    uint8_t response[G0Q_RESPONSE_SIZE]={0},command[89]={0},ack[121]={0};
    for(unsigned i=0;i<32;i++)response[40+i]=(uint8_t)i;
    for(unsigned i=0;i<16;i++)response[72+i]=(uint8_t)(i+1);
    memcpy(command,"G0QDCQ1\0",8);memcpy(command+8,response+40,32);memcpy(command+40,response+72,16);
    if(!strcmp(test_case,"wrong-boot"))command[40]^=1;
    if(!strcmp(test_case,"wrong-nonce"))command[8]^=1;
    if(!strcmp(test_case,"legacy-command"))command[3]='S';
    g_tag(command+56,canary_key,canary_id,2,command,56);
    if(!strcmp(test_case,"wrong-auth"))command[56]^=1;
    int fd[2];if(socketpair(AF_UNIX,SOCK_STREAM,0,fd))return 91;
    size_t size=!strcmp(test_case,"partial-control")?1:!strcmp(test_case,"extra-tail")?89:88;
    if(write(fd[0],command,size)!=(ssize_t)size)return 92;
    if(strcmp(test_case,"missing-eof")&&shutdown(fd[0],SHUT_WR))return 93;
    deadline=!strcmp(test_case,"missing-eof")?1001:1500;
    int result=download_finish(fd[1],response);close(fd[1]);
    ssize_t length=read(fd[0],ack,sizeof(ack));close(fd[0]);
    if(length==120) {
        uint8_t auth[32];g_tag(auth,canary_key,canary_id,3,ack,88);
        if(memcmp(ack,"G0QDCA1\0",8)||memcmp(ack+8,canary_id,32)||memcmp(ack+40,response+40,48)||
           memcmp(ack+88,auth,32))return 94;
    }
    printf("error=%d resets=%u ack=%zd reads=%u\n",result,resets,length,reads);
    return 0;
}
