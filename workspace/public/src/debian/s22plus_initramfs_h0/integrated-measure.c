/* Measure the still-running Debian shell parent before its PID1 exec. */
#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-INTEGRATED-v1"
#define main di_unused_observer_main
#include "early-observer.c"
#undef main
int main(int argc,char **argv) {
    if(argc!=2 || strcmp(argv[1],"0"))return 100;
    int error=measure(0);if(error)return 101;
    uint8_t value[208];memcpy(value,proof,sizeof(proof));
    early_tag(value+176,proof+16,243,1,proof,176);
    int fd=open("/run/initramfs/initial-parent",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(fd<0)return 102;
    error=write(fd,value,sizeof(value))==(ssize_t)sizeof(value) ? 0 : EIO;
    if(close(fd) && !error)error=fs1_error();
    return error ? 103 : 0;
}
