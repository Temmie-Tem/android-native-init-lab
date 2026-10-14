/* Shared exact initial Debian PID1 measurement, including supervised workers. */
#ifndef S22_PID1_MEASURE_H
#define S22_PID1_MEASURE_H
static int pid1_cmdline_matches(const char *cmdline,ssize_t length) {
    static const char minimal[]="/bin/sh\0/init\0";
    /* FYG8 passes these two operands to /init; binfmt_script preserves them.
     * Compare the entire NUL-separated tuple, never an arbitrary suffix. */
    static const char fyg8[]="/bin/sh\0/init\0bootconfig\0nohyp_uart\0";
    return (length==(ssize_t)sizeof(minimal)-1 && !memcmp(cmdline,minimal,sizeof(minimal)-1)) ||
        (length==(ssize_t)sizeof(fyg8)-1 && !memcmp(cmdline,fyg8,sizeof(fyg8)-1));
}
static int file_hash(const char *path,uint64_t maximum,uint8_t hash[32]) {
    int fd=open(path,O_RDONLY|O_CLOEXEC); /* /proc/1/exe is an intended proc link. */
    if(fd<0)return fs1_error();
    struct stat before,after;int error=0;
    if(fstat(fd,&before) || !S_ISREG(before.st_mode) || before.st_uid || before.st_gid ||
        before.st_size<=0 || (uint64_t)before.st_size>maximum)error=EPROTO;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    uint8_t data[4096];uint64_t total=0;
    while(!error) {
        ssize_t n=read(fd,data,sizeof(data));
        if(n<0){error=fs1_error();break;}if(!n)break;
        total+=(uint64_t)n;if(total>maximum){error=EOVERFLOW;break;}
        s22plus_max77705_runtime_sha256_update(&h,data,(size_t)n);
    }
    if(!error && (fstat(fd,&after) || before.st_dev!=after.st_dev || before.st_ino!=after.st_ino ||
        before.st_size!=after.st_size || total!=(uint64_t)before.st_size))error=ESTALE;
    s22plus_max77705_runtime_sha256_final(&h,hash);
    if(close(fd)&&!error)error=fs1_error();
    return error;
}
static int measure_pid1(uint8_t shell[32],uint8_t init[32]) {
    char name[128],cmdline[64];
    ssize_t n=readlink("/proc/1/exe",name,sizeof(name)-1);
    if(n<=0 || (size_t)n>=sizeof(name)-1)return EPROTO;
    name[n]=0;
    if(strcmp(name,"/usr/bin/sh"))return EPROTO;
    int fd=open("/proc/1/cmdline",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return fs1_error();
    n=read(fd,cmdline,sizeof(cmdline));int closed=close(fd);
    if(closed || !pid1_cmdline_matches(cmdline,n))return EPROTO;
    int error=file_hash("/proc/1/exe",4*1024*1024,shell);
    if(!error)error=file_hash("/init",65536,init);
    return error?error:memcmp(shell,early_shell_hash,32) || memcmp(init,early_init_hash,32)?EPROTO:0;
}
#endif
