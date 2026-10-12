/* Shared actual-PID1 and bounded RAM-log measurements. No transport or write. */
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
static int measure(unsigned status) {
    char name[128],cmdline[64],boot[38];
    if(getpid()==1 || getppid()!=1 || getuid() || geteuid() || getgid() || getegid())return EACCES;
    ssize_t n=readlink("/proc/1/exe",name,sizeof(name)-1);
    if(n<=0 || (size_t)n>=sizeof(name)-1)return EPROTO;
    name[n]=0;
    if(strcmp(name,"/usr/bin/sh"))return EPROTO;
    int fd=open("/proc/1/cmdline",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return fs1_error();
    n=read(fd,cmdline,sizeof(cmdline));int closed=close(fd);
    static const char wanted[]="/bin/sh\0/init\0";
    if(n!=(ssize_t)sizeof(wanted)-1 || closed || memcmp(cmdline,wanted,sizeof(wanted)-1))return EPROTO;
    uint8_t shell[32],init[32],helper[32];int error=file_hash("/proc/1/exe",4*1024*1024,shell);
    if(!error)error=file_hash("/init",65536,init);
    if(!error)error=file_hash("/sbin/fyg8-prepare",4*1024*1024,helper);
    if(error || memcmp(shell,early_shell_hash,32) || memcmp(init,early_init_hash,32) ||
        memcmp(helper,early_helper_hash,32))return EPROTO;
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
