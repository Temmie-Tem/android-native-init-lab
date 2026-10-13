/* Fixed storage preparation before the separately measured file writer. */
#define DI_PREPARE_LIBRARY
#include "integrated-prepare.c"
#include "file-first-plan.h"

int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getpid()==1 || getppid()!=1 || getuid() || geteuid() || getgid() || getegid())return 100;
    umask(077);int error=target();if(error)return 104;
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;struct statfs fs;
    if(dir<0 || fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
        fstatfs(dir,&fs) || fs.f_type!=0x01021994L)return 107;
    events=openat(dir,"fyg8-events",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(events<0 || close(dir))return 108;
    char boot[38];error=fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot));
    if(!error && (strlen(boot)!=37 || boot[36]!='\n'))error=EPROTO;
    if(!error){boot[36]=0;error=record("BEGIN run=%s boot=%s parent=1",fs1_run_id,boot);}
    if(!error)error=record("TARGET_GUARD_OK");
    if(!error)error=di_modules(0,FF_STORAGE_COUNT);
    int logged=record("TERMINAL result=%s error=%d",error?"REJECTED":"STORAGE_READY",error);
    if(close(events) && !error)error=fs1_error();
    return error || logged ? 1 : 0;
}
