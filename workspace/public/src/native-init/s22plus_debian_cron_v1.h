/* One fixed cron report, shared by its producer and protected-root reader. */
#ifndef S22PLUS_DEBIAN_CRON_V1_H
#define S22PLUS_DEBIAN_CRON_V1_H
#include "s22plus_debian_cron_seal_v1.h"
static uint64_t cr_u64(const uint8_t *p) {
    uint64_t value=0;for(unsigned i=0;i<8;++i)value|=(uint64_t)p[i]<<(8*i);
    return value;
}
static void cr_put64(uint8_t *p,uint64_t value) {for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(value>>(8*i));}
static void cr_tag(uint8_t tag[32],unsigned role,const uint8_t *data,size_t size) {
#ifdef S22_DEBIAN_CRON_CONFIG
    static const char domain[]="S22PLUS-FYG8-DEBIAN-CRON-CONFIG-v1";
#else
    static const char domain[]="S22PLUS-FYG8-DEBIAN-CRON-v1";
#endif
    uint8_t pad[64],inner[32],kind=(uint8_t)role;struct s22plus_max77705_runtime_sha256 h;
    memset(pad,0x36,64);for(unsigned i=0;i<32;++i)pad[i]^=early_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,(const uint8_t *)domain,sizeof(domain)-1);
    s22plus_max77705_runtime_sha256_update(&h,&kind,1);
    s22plus_max77705_runtime_sha256_update(&h,data,size);
    s22plus_max77705_runtime_sha256_final(&h,inner);
    memset(pad,0x5c,64);for(unsigned i=0;i<32;++i)pad[i]^=early_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,inner,32);
    s22plus_max77705_runtime_sha256_final(&h,tag);
}
#ifndef S22_DEBIAN_CRON_CONFIG
static int cr_valid(const uint8_t data[CR_SIZE],const uint8_t early[256],dev_t device,const uint8_t hook[32]) {
    uint8_t tag[32],nonce[32];cr_tag(tag,1,data,480);early_hash(early,256,nonce);
    if(memcmp(data,"S22CR01\0",8) || fs1_u32(data+8)!=1 || fs1_u32(data+12)!=CR_SIZE ||
       memcmp(data+16,early_run,16) || memcmp(data+32,early+48,32) || memcmp(data+64,nonce,32) ||
       cr_u64(data+CR_ROOT_DEVICE)!=(uint64_t)device || fs1_u32(data+CR_PHASE)!=1 ||
       fs1_u32(data+CR_BASELINE)!=RB_BASE_COUNT || fs1_u32(data+CR_INSTALLED_COUNT)!=RB_BASE_COUNT+2 ||
       memcmp(data+192,cr_cron_sha,32) || memcmp(data+224,cr_sshd_sha,32) || memcmp(data+256,hook,32) ||
       cr_u64(data+CR_CRON_SIZE)!=CR_CRON_BYTES || cr_u64(data+CR_SSHD_SIZE)!=CR_SSHD_BYTES ||
       memcmp(data+480,tag,32))return EPROTO;
    const unsigned times[]={CR_STOP_MS,CR_START_MS,CR_RESTART_MS,CR_ARMED_MS,CR_JOB_MS,CR_HASH_COMPLETED_MS};
    uint64_t previous=0;
    for(unsigned i=0;i<sizeof(times)/sizeof(times[0]);++i) {
        uint64_t value=cr_u64(data+times[i]);
        if(!value || value<previous || value>=300000)return EPROTO;
        previous=value;
    }
    const unsigned pids[]={CR_INITIAL_PID,CR_STARTED_PID,CR_RESTARTED_PID,CR_JOB_PID,CR_PARENT_PID};
    for(unsigned i=0;i<sizeof(pids)/sizeof(pids[0]);++i)
        if(cr_u64(data+pids[i])<=1 || cr_u64(data+pids[i])>INT_MAX)return EPROTO;
    if(cr_u64(data+CR_INITIAL_PID)==cr_u64(data+CR_STARTED_PID) ||
       cr_u64(data+CR_INITIAL_PID)==cr_u64(data+CR_RESTARTED_PID) ||
       cr_u64(data+CR_STARTED_PID)==cr_u64(data+CR_RESTARTED_PID) ||
       cr_u64(data+CR_JOB_PID)==cr_u64(data+CR_RESTARTED_PID) ||
       !cr_u64(data+CR_INITIAL_TICKS) || !cr_u64(data+CR_STARTED_TICKS) || !cr_u64(data+CR_RESTARTED_TICKS) ||
       fs1_u32(data+CR_ANCESTOR_COUNT)<1 || fs1_u32(data+CR_ANCESTOR_COUNT)>6)return EPROTO;
    for(unsigned i=116;i<120;++i)if(data[i])return EPROTO;
    for(unsigned i=332;i<336;++i)if(data[i])return EPROTO;
    for(unsigned i=352;i<480;++i)if(data[i])return EPROTO;
    return 0;
}
#endif
static int cr_directory(int fd,dev_t device) {
    struct stat st;struct statfs fs;
    return fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0xef53 || st.st_dev!=device ||
        st.st_mode!=(S_IFDIR|0755) || st.st_uid || st.st_gid || st.st_nlink<2 ? EPROTO : 0;
}
static int cr_parent(int root,dev_t device) {
    int fd=fcntl(root,F_DUPFD_CLOEXEC,3);
    if(fd<0)return -1;
    int error=cr_directory(fd,device);const char *parts[]={"var","lib","lab"};
    for(unsigned i=0;i<3 && !error;++i) {
        int next=openat(fd,parts[i],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if(next<0){error=fs1_error();break;}
        error=cr_directory(next,device);
        if(close(fd) && !error)error=fs1_error();
        fd=next;
    }
    if(error){(void)close(fd);errno=error;return -1;}
    return fd;
}
static int cr_read(int root,dev_t device,uint8_t data[CR_SIZE],bool absent) {
    int parent=cr_parent(root,device);
    if(parent<0)return absent && errno==ENOENT ? 0 : fs1_error();
    const char *name=strrchr(cr_path,'/')+1;struct stat before,after;int error=0,fd=-1;
    if(fstatat(parent,name,&before,AT_SYMLINK_NOFOLLOW))error=absent && errno==ENOENT ? 0 : fs1_error();
    else if(absent)error=EEXIST;
    else {
        if(before.st_dev!=device || before.st_mode!=(S_IFREG|0600) || before.st_uid || before.st_gid ||
           before.st_nlink!=1 || before.st_size!=CR_SIZE)error=EPROTO;
        if(!error && (fd=openat(parent,name,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC))<0)error=fs1_error();
        uint8_t extra;
        if(!error && (fstat(fd,&after) || before.st_dev!=after.st_dev || before.st_ino!=after.st_ino ||
           before.st_mode!=after.st_mode || before.st_nlink!=after.st_nlink || before.st_size!=after.st_size ||
           read(fd,data,CR_SIZE)!=CR_SIZE || read(fd,&extra,1) || fstat(fd,&after) ||
           before.st_mtim.tv_sec!=after.st_mtim.tv_sec || before.st_mtim.tv_nsec!=after.st_mtim.tv_nsec ||
           before.st_ctim.tv_sec!=after.st_ctim.tv_sec || before.st_ctim.tv_nsec!=after.st_ctim.tv_nsec))error=EIO;
    }
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(close(parent) && !error)error=fs1_error();
    return error;
}
#ifdef S22_DEBIAN_CRON_CONFIG
#include "s22plus_debian_cron_config_v1.h"
#endif
#endif
