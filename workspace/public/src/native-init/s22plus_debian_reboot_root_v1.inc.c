/* Current-run extras are authenticated exact files, never wildcard history. */
#include "s22plus_switch_root_v1.h"
#include "s22plus_debian_handoff_v1.h"
#include "s22plus_autoboot_singlecpu_v1.h"
#define DE_CHAIN_KEY early_key
#include "s22plus_debian_evidence_chain_v1.h"
#undef DE_CHAIN_KEY
#ifdef S22_DEBIAN_CRON
#include "s22plus_debian_cron_v1.h"
#endif

static int rb_file(int root,dev_t device,unsigned phase,unsigned runtime,
                   uint8_t data[16384],size_t *size,bool absent) {
    char leaf[NAME_MAX+1];int parent=ri_parent(root,device,rb_paths[phase-1][runtime],leaf);
    if(parent<0)return absent && errno==ENOENT ? 0 : fs1_error();
    struct stat st;int error=0;
    if(fstatat(parent,leaf,&st,AT_SYMLINK_NOFOLLOW))error=errno==ENOENT && absent ? 0 : fs1_error();
    else if(absent)error=EEXIST;
    else {
        if(st.st_dev!=device || st.st_mode!=(S_IFREG|0600) || st.st_uid || st.st_gid ||
           st.st_nlink!=1 || st.st_size<256 || st.st_size>(runtime ? DE_MAXIMUM : 16384))error=EPROTO;
        int fd=error ? -1 : openat(parent,leaf,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
        if(!error && fd<0)error=fs1_error();
        struct stat after;uint8_t extra;
        if(!error && (fstat(fd,&after) || after.st_dev!=st.st_dev || after.st_ino!=st.st_ino ||
            after.st_mode!=st.st_mode || after.st_size!=st.st_size || after.st_nlink!=1 ||
            read(fd,data,(size_t)st.st_size)!=st.st_size || read(fd,&extra,1)))error=EIO;
        if(fd>=0 && close(fd) && !error)error=fs1_error();
        if(!error)*size=(size_t)st.st_size;
    }
    if(close(parent) && !error)error=fs1_error();
    return error;
}
static int rb_hook_digest(uint8_t digest[32]) {
    /* Both boots execute the same immutable RAM asset from this boot image. */
    int fd=open("/s22-debian-hook",O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;int error=fstat(fd,&st) || fstatfs(fd,&fs) ||
        (fs.f_type!=0x01021994L && fs.f_type!=0x858458f6L) ||
        st.st_mode!=(S_IFREG|0500) || st.st_uid || st.st_gid || st.st_nlink!=1 ||
        st.st_size<1 || st.st_size>8*1024*1024 ? EPROTO : 0;
    struct s22plus_max77705_runtime_sha256 hash;s22plus_max77705_runtime_sha256_init(&hash);
    uint8_t data[65536],extra;size_t used=0;
    while(!error && used<(size_t)st.st_size) {
        size_t amount=(size_t)st.st_size-used;if(amount>sizeof(data))amount=sizeof(data);
        if(read(fd,data,amount)!=(ssize_t)amount)error=EIO;
        else {s22plus_max77705_runtime_sha256_update(&hash,data,amount);used+=amount;}
    }
    if(!error && read(fd,&extra,1))error=EIO;
    if(close(fd) && !error)error=fs1_error();
    if(!error)s22plus_max77705_runtime_sha256_final(&hash,digest);
    return error;
}
#ifdef S22_DEBIAN_CRON_CONFIG
static struct de_chain rb_config_created;
#endif
static int rb_prior_runtime(const uint8_t *data,size_t size,const uint8_t *early,dev_t device) {
#ifdef S22_DEBIAN_CRON_CONFIG
    uint8_t hook[32];int error=rb_hook_digest(hook);
    return error ? error : cf_prior_chain(data,size,early,device,hook,&rb_config_created);
#else
    if(size<DE_HEADER || size>DE_MAXIMUM || (size-DE_HEADER)%DE_RECORD)return EPROTO;
    uint8_t tag[32],nonce[32],hook[32];de_tag(tag,data,224);early_hash(early,256,nonce);
    int error=rb_hook_digest(hook);if(error)return error;
    if(memcmp(data,"S22DE01\0",8) || fs1_u32(data+8)!=1 || fs1_u32(data+12)!=DE_HEADER ||
       memcmp(data+16,early_run,16) || memcmp(data+32,early+48,32) || memcmp(data+64,nonce,32) ||
       fs1_u64(data+96) || fs1_u64(data+104)!=300000 || fs1_u32(data+112)!=7 ||
       fs1_u32(data+116)!=DE_RECORD || fs1_u32(data+120)!=DE_RECORDS || fs1_u32(data+124)!=DE_MAXIMUM ||
       memcmp(data+128,rb_init_sha256,32) || memcmp(data+160,hook,32) || fs1_u64(data+192)!=(uint64_t)device ||
       fs1_u32(data+200)!=1 || fs1_u32(data+204)!=RB_BASE_COUNT || fs1_u32(data+208)!=RB_BASE_COUNT+2 ||
       !de_tag_equal(data+224,tag))return EPROTO;
    for(unsigned i=212;i<224;++i)if(data[i])return EPROTO;
    struct de_chain chain={0};memcpy(chain.tag,data+224,32);
    for(size_t at=DE_HEADER;at<size;at+=DE_RECORD)if((error=de_apply(&chain,data+at)))return error;
    return chain.complete && chain.control==RB_REBOOT_INTENT && !chain.off && !chain.stopped &&
        !chain.released && chain.last_kind==RB_REBOOT_INTENT ? 0 : EPROTO;
#endif
}
static int rb_root_extras(int root,dev_t device,unsigned *extra) {
    if(!rb_valid_phase(rb_phase))return EPROTO;
    uint8_t first[16384],runtime[16384],boot[32];size_t first_size=0,runtime_size=0;
    int error=0;
    /* Exact optional old shutdown output; it is not P457-retrieved history. */
    char leaf[NAME_MAX+1];int parent=ri_parent(root,device,"var/lib/lab/shutdown-start",leaf);
    if(parent<0 && errno!=ENOENT)return fs1_error();
    if(parent>=0) {
        struct stat marker;uint8_t digest[32];
        if(fstatat(parent,leaf,&marker,AT_SYMLINK_NOFOLLOW)) {if(errno!=ENOENT)error=fs1_error();}
        else {
            if(marker.st_dev!=device || marker.st_mode!=(S_IFREG|0644) || marker.st_uid || marker.st_gid ||
               marker.st_nlink!=1 || marker.st_size!=37)error=EPROTO;
            if(!error)error=ri_hash_file(parent,leaf,device,37,digest);
            if(!error && memcmp(digest,rb_shutdown_sha256,32))error=EPROTO;
            if(!error)++*extra;
        }
        if(close(parent) && !error)error=fs1_error();
        if(error)return error;
    }
    if(rb_phase==2) {
        if((error=rb_file(root,device,1,0,first,&first_size,false)) ||
           (error=rb_file(root,device,1,1,runtime,&runtime_size,false)) ||
           (error=rb_early(first,first_size,1)) || (error=rb_prior_runtime(runtime,runtime_size,first,device)) ||
           (error=rb_boot(boot)))return error;
        if(!memcmp(boot,first+48,32))return EPROTO;
        *extra+=2;
    }
#ifdef S22_DEBIAN_CRON_CONFIG
    uint8_t cron[CR_SIZE];struct stat config={0};
    if((error=cr_read(root,device,cron,true)) || (error=cf_read(root,device,&config,rb_phase==1)))return error;
    if(rb_phase==2) {
        if((error=cf_identity(&config,&rb_config_created)))return error;
        ++*extra;
    }
#elif defined(S22_DEBIAN_CRON)
    uint8_t cron[CR_SIZE],hook[32];
    if((error=cr_read(root,device,cron,rb_phase==1)))return error;
    if(rb_phase==2) {
        if((error=rb_hook_digest(hook)) || (error=cr_valid(cron,first,device,hook)))return error;
        ++*extra;
    }
#endif
    for(unsigned p=rb_phase;p<=2;++p)for(unsigned kind=0;kind<2;++kind) {
#ifdef S22_AUTOBOOT_SECOND_ADMISSION
        /* Its exact same-boot early file is checked by ab_owned_file. */
        if(p==rb_phase && kind==0)continue;
#endif
        if((error=rb_file(root,device,p,kind,first,&first_size,true)))return error;
    }
    return 0;
}
