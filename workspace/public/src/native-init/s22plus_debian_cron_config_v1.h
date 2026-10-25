/* Exact cron.d configuration identity shared with both protected admissions. */
#ifndef S22PLUS_DEBIAN_CRON_CONFIG_V1_H
#define S22PLUS_DEBIAN_CRON_CONFIG_V1_H
static int cf_parent(int root,dev_t device) {
    int fd=fcntl(root,F_DUPFD_CLOEXEC,3);
    if(fd<0)return -1;
    int error=cr_directory(fd,device);const char *parts[]={"etc","cron.d"};
    for(unsigned i=0;i<2 && !error;++i) {
        int next=openat(fd,parts[i],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if(next<0){error=fs1_error();break;}
        error=cr_directory(next,device);
        if(close(fd) && !error)error=fs1_error();
        fd=next;
    }
    if(error){(void)close(fd);errno=error;return -1;}
    return fd;
}
static int cf_stat(const struct stat *st,dev_t device) {
    return st->st_dev!=device || st->st_mode!=(S_IFREG|0644) || st->st_uid || st->st_gid ||
        st->st_nlink!=1 || st->st_size!=CF_CONFIG_SIZE || !st->st_ino || st->st_mtim.tv_sec<=0 ||
        st->st_ctim.tv_sec<=0 || st->st_mtim.tv_nsec<0 || st->st_mtim.tv_nsec>=1000000000L ||
        st->st_ctim.tv_nsec<0 || st->st_ctim.tv_nsec>=1000000000L ? EPROTO : 0;
}
static bool cf_same(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino && a->st_mode==b->st_mode &&
        a->st_uid==b->st_uid && a->st_gid==b->st_gid && a->st_nlink==b->st_nlink && a->st_size==b->st_size &&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec && a->st_mtim.tv_nsec==b->st_mtim.tv_nsec &&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec && a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int cf_open(int parent,dev_t device,struct stat *identity) {
    struct stat before,after;struct statfs fs;uint8_t data[CF_CONFIG_SIZE],extra;
    const char *name=strrchr(cf_path,'/')+1;
    if(fstatat(parent,name,&before,AT_SYMLINK_NOFOLLOW)){return -1;}
    int error=cf_stat(&before,device),fd=-1;
    if(!error && (fd=openat(parent,name,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC))<0)error=fs1_error();
    if(!error && (fstat(fd,&after) || fstatfs(fd,&fs) || fs.f_type!=0xef53 || !cf_same(&before,&after) ||
        read(fd,data,sizeof(data))!=sizeof(data) || read(fd,&extra,1) || memcmp(data,cf_schedule,sizeof(data)) ||
        fstat(fd,&after) || !cf_same(&before,&after)))error=EPROTO;
    if(error){if(fd>=0)(void)close(fd);errno=error;return -1;}
    *identity=after;return fd;
}
static int cf_identity(const struct stat *st,const struct de_chain *chain) {
    return chain->boot_phase!=1 || chain->config_created!=2 || chain->config_inode!=(uint64_t)st->st_ino ||
        chain->config_mtime_sec!=(uint64_t)st->st_mtim.tv_sec || chain->config_mtime_nsec!=(uint64_t)st->st_mtim.tv_nsec ||
        chain->config_ctime_sec!=(uint64_t)st->st_ctim.tv_sec || chain->config_ctime_nsec!=(uint64_t)st->st_ctim.tv_nsec ? EPROTO : 0;
}
static int cf_read(int root,dev_t device,struct stat *identity,bool absent) {
    int parent=cf_parent(root,device);if(parent<0)return fs1_error();
    int error=0,fd=-1;struct stat st;
    if(absent) {
        if(!fstatat(parent,strrchr(cf_path,'/')+1,&st,AT_SYMLINK_NOFOLLOW))error=EEXIST;
        else if(errno!=ENOENT)error=fs1_error();
    } else {
        fd=cf_open(parent,device,identity);if(fd<0)error=fs1_error();
    }
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(close(parent) && !error)error=fs1_error();
    return error;
}
static int cf_prior_chain(const uint8_t *data,size_t size,const uint8_t early[256],dev_t device,
                          const uint8_t hook[32],struct de_chain *chain) {
    if(size<DE_HEADER || size>DE_MAXIMUM || (size-DE_HEADER)%DE_RECORD)return EPROTO;
    uint8_t tag[32],nonce[32];de_tag(tag,data,224);early_hash(early,256,nonce);
    if(memcmp(data,"S22DE01\0",8) || fs1_u32(data+8)!=1 || fs1_u32(data+12)!=DE_HEADER ||
       memcmp(data+16,early_run,16) || memcmp(data+32,early+48,32) || memcmp(data+64,nonce,32) ||
       fs1_u64(data+96) || fs1_u64(data+104)!=300000 || fs1_u32(data+112)!=DE_SELECTED_REVISION ||
       fs1_u32(data+116)!=DE_RECORD || fs1_u32(data+120)!=DE_RECORDS || fs1_u32(data+124)!=DE_MAXIMUM ||
       memcmp(data+128,rb_init_sha256,32) || memcmp(data+160,hook,32) || fs1_u64(data+192)!=(uint64_t)device ||
       fs1_u32(data+200)!=1 || fs1_u32(data+204)!=RB_BASE_COUNT || fs1_u32(data+208)!=RB_BASE_COUNT+2 ||
       !de_tag_equal(data+224,tag))return EPROTO;
    for(unsigned i=212;i<224;++i)if(data[i])return EPROTO;
    memset(chain,0,sizeof(*chain));chain->boot_phase=1;memcpy(chain->tag,data+224,32);
    for(size_t at=DE_HEADER;at<size;at+=DE_RECORD){int error=de_apply(chain,data+at);if(error)return error;}
    return chain->complete && chain->config_created==2 && chain->control==RB_REBOOT_INTENT &&
        !chain->off && !chain->stopped && !chain->released && chain->last_kind==RB_REBOOT_INTENT ? 0 : EPROTO;
}
static int cr_valid(const uint8_t data[CR_SIZE],const uint8_t early[256],dev_t device,const uint8_t hook[32]) {
    uint8_t tag[32],nonce[32];cr_tag(tag,1,data,480);early_hash(early,256,nonce);
    if(memcmp(data,"S22CC01\0",8) || fs1_u32(data+8)!=1 || fs1_u32(data+12)!=CR_SIZE ||
       memcmp(data+16,early_run,16) || memcmp(data+32,early+48,32) || memcmp(data+64,nonce,32) ||
       cr_u64(data+CR_ROOT_DEVICE)!=(uint64_t)device || fs1_u32(data+CR_PHASE)!=2 ||
       fs1_u32(data+CR_BASELINE)!=RB_BASE_COUNT || fs1_u32(data+CR_INSTALLED_COUNT)!=RB_BASE_COUNT+4 ||
       memcmp(data+192,cr_cron_sha,32) || memcmp(data+224,cr_sshd_sha,32) || memcmp(data+256,hook,32) ||
       cr_u64(data+CR_CRON_SIZE)!=CR_CRON_BYTES || cr_u64(data+CR_SSHD_SIZE)!=CR_SSHD_BYTES ||
       cr_u64(data+CR_CONFIG_SIZE)!=CF_CONFIG_SIZE || !cr_u64(data+CR_CONFIG_INODE) ||
       !cr_u64(data+CR_CONFIG_MTIME_SEC) || !cr_u64(data+CR_CONFIG_CTIME_SEC) ||
       cr_u64(data+CR_CONFIG_MTIME_NSEC)>=1000000000ULL || cr_u64(data+CR_CONFIG_CTIME_NSEC)>=1000000000ULL ||
       !cr_u64(data+CR_CONFIG_CREATED_MS) || cr_u64(data+CR_CONFIG_CREATED_MS)>=300000 ||
       memcmp(data+352,cf_config_sha,32) || !memcmp(data+416,data+32,32) ||
       memcmp(data+480,tag,32))return EPROTO;
    const unsigned times[]={CR_ARMED_MS,CR_JOB_MS,CR_HASH_COMPLETED_MS};uint64_t previous=0;
    for(unsigned i=0;i<sizeof(times)/sizeof(times[0]);++i) {
        uint64_t value=cr_u64(data+times[i]);if(!value || value<previous || value>=300000)return EPROTO;previous=value;
    }
    const unsigned pids[]={CR_DAEMON_PID,CR_JOB_PID,CR_PARENT_PID};
    for(unsigned i=0;i<sizeof(pids)/sizeof(pids[0]);++i)
        if(cr_u64(data+pids[i])<=1 || cr_u64(data+pids[i])>INT_MAX)return EPROTO;
    if(cr_u64(data+CR_DAEMON_PID)==cr_u64(data+CR_JOB_PID) || !cr_u64(data+CR_DAEMON_TICKS) ||
       fs1_u32(data+CR_ANCESTOR_COUNT)<1 || fs1_u32(data+CR_ANCESTOR_COUNT)>6)return EPROTO;
    for(unsigned i=116;i<120;++i)if(data[i])return EPROTO;
    for(unsigned i=144;i<160;++i)if(data[i])return EPROTO;
    for(unsigned i=332;i<352;++i)if(data[i])return EPROTO;
    return 0;
}
#endif
