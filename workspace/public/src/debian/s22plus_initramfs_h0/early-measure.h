#ifndef fo_parent_ok
#ifndef S22_FAILURE_OBSERVER
#define fo_parent_ok() (getppid()==1)
#endif
#endif
/* Shared actual-PID1 and bounded RAM-log measurements. No transport or write. */
#include "pid1-measure.h"
static int measure(unsigned status) {
    char boot[38];
    if(getpid()==1 || !fo_parent_ok() || getuid() || geteuid() || getgid() || getegid())return EACCES;
    uint8_t shell[32],init[32],helper[32];int error=measure_pid1(shell,init);
    if(!error)error=file_hash("/sbin/fyg8-prepare",4*1024*1024,helper);
    if(error || memcmp(helper,early_helper_hash,32))return EPROTO;
    int fd;
    if(fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot)) ||
        strlen(boot)!=37 || boot[36]!='\n')return EPROTO;
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;struct statfs fs;
    if(dir<0 || fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
        fstatfs(dir,&fs) || (unsigned long)fs.f_type!=0x01021994UL)return EPROTO;
    fd=openat(dir,"fyg8-events",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(close(dir) || fd<0)return EIO;
    if(fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid || st.st_nlink!=1 ||
        (st.st_mode&07777)!=0400 || st.st_size<=0 || st.st_size>EARLY_LIMIT)error=EPROTO;
    if(!error){log_size=(size_t)st.st_size;if(read(fd,log_bytes,log_size)!=(ssize_t)log_size)error=EIO;}
    uint8_t extra;if(!error && read(fd,&extra,1)!=0)error=EPROTO;
    if(close(fd)&&!error)error=EIO;
    if(error)return error;
    /* The host validates the complete structured log including original boot.
     * This proof independently binds the currently observed parent and bytes. */
    early_put32(proof,1);early_put32(proof+4,(uint32_t)getpid());
    early_put32(proof+8,status);early_put32(proof+12,(uint32_t)log_size);
    early_hash(boot,36,proof+16);memcpy(proof+48,shell,32);memcpy(proof+80,init,32);
    early_hash(log_bytes,log_size,proof+112);memcpy(proof+144,helper,32);
    return 0;
}
