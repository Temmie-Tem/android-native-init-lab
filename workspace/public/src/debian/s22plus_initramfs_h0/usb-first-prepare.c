/* A fixed child of Debian shell PID1. No UFS insertion, block access, mount,
 * installed init or reboot. The old metadata main is unreferenced and removed
 * by section GC; the build checks the resulting executable's symbols. */
#define FYG8_USB_FIRST
static int logger_bound(void);
#define main unused_metadata_main
#include "fyg8-prepare.c"
#undef main

static int logger_bound(void) {
#ifdef FYG8_VM_TEST
    return 0;
#else
    struct stat st;
    if(lstat("/sys/bus/platform/drivers/samsung,kernel_log_buf/soc:samsung,kernel_log_buf",&st) ||
        !S_ISLNK(st.st_mode) || st.st_uid)return ENODEV;
    if(lstat("/proc/last_kmsg",&st) || !S_ISREG(st.st_mode) || st.st_uid)return ENODEV;
    return 0;
#endif
}

int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getuid() || geteuid() || getgid() || getegid() || getppid()!=1)return 100;
    umask(077);int error=target();if(error)return 101;
    struct stat st;struct statfs fs;
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(dir<0 || fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
        fstatfs(dir,&fs) || (unsigned long)fs.f_type!=0x01021994UL)return 102;
    events=openat(dir,"fyg8-events",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(events<0 || close(dir))return 103;
    char boot[38];error=fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot));
    if(!error && (strlen(boot)!=37 || boot[36]!='\n'))error=EPROTO;
    if(!error){boot[36]=0;error=record("BEGIN run=%s boot=%s parent=1",fs1_run_id,boot);}
    if(!error)error=record("TARGET_GUARD_OK");
    if(!error)error=modules();
#ifdef FYG8_USB_RAM_ONLY
    if(!error)error=record("LOGGING_RAM_ONLY retention_after_reboot=not_available");
#else
    if(!error)error=logger_bound();
    if(!error)error=record("LOGGER_BOUND retention_after_reboot=unproved");
#endif
    int logged=record("TERMINAL result=%s error=%d",error?"REJECTED":"PLATFORM_READY",error);
    if(close(events)&&!error)error=EIO;
    return error || logged ? 1 : 0;
}
