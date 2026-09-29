/* The separate, static post-exec program. Never executes installed code. */
#define FS1_READONLY_BINDING_ONLY
#include "s22plus_native_ext4_v1.c"
#include "s22plus_switch_root_common_v1.inc.c"

static int sw_witness(void) {
    if(!sw.settled || !sw.root_admitted || sw.root_device==sw.old_device || !sw.root_device ||
       !sw.mount_count || sw.mount_count>SW_MAX_MOUNTS)return EPROTO;
    int error=sw_no_children();if(!error)error=sw_userspace();if(error)return error;
    struct stat st;struct statfs fs;
    if(stat("/",&st) || statfs("/",&fs) || (uint64_t)st.st_dev!=sw.root_device || fs.f_type!=0xef53 ||
       fs.f_bsize!=4096 || (fs.f_flags&(ST_RDONLY|ST_NODEV|ST_NOEXEC|ST_NOSUID))!=(ST_RDONLY|ST_NODEV|ST_NOEXEC|ST_NOSUID))return EPROTO;
    int node=open("/dev/.s22-ext4-v1/native",O_RDONLY|O_NOFOLLOW|O_CLOEXEC),ro=0;
    if(node<0)return fs1_error();
    error=fstat(node,&st) || !S_ISBLK(st.st_mode) || (uint64_t)st.st_rdev!=sw.root_device ||
        ioctl(node,BLKROGET,&ro) || ro!=1 ? EPROTO : 0;
    if(close(node) && !error)error=fs1_error();
    if(error)return error;
    if(stat("/run/s22-witness",&st) || st.st_dev==(dev_t)sw.root_device || st.st_dev==(dev_t)sw.old_device ||
       !S_ISREG(st.st_mode) || st.st_mode!=(S_IFREG|0500) || st.st_uid || st.st_gid || st.st_nlink!=1 ||
       statfs("/run",&fs) || fs.f_type!=0x01021994L || (fs.f_flags&ST_NOEXEC) ||
       (fs.f_flags&(ST_NODEV|ST_NOSUID))!=(ST_NODEV|ST_NOSUID))return EPROTO;
    struct stat image;
    if(stat("/proc/self/exe",&image) || image.st_dev!=st.st_dev || image.st_ino!=st.st_ino || image.st_size!=st.st_size)return EPROTO;
    int fd=fs1_pin_file("/run/s22-witness",(uint64_t)st.st_size,sw.witness_digest,true);
    if(fd<0)return fs1_error();
    if(close(fd))return fs1_error();
    struct sw_mount mounts[SW_MAX_MOUNTS]={0};unsigned count=0;uint8_t digest[32];
    if((error=sw_mounts(mounts,&count,NULL)))return error;
    if(count!=sw.mount_count)return EPROTO;
    for(unsigned i=0;i<count;++i)if(sw_mount_allowed(mounts+i,1) || mounts[i].id!=sw.mount_ids[i])return EPROTO;
    sw_mount_hash(mounts,count,digest);if(memcmp(digest,sw.mount_digest,32))return EPROTO;
    if(close(4))return fs1_error();
    return sw_fd_whitelist(0);
}
int main(int argc,char **argv) {
    (void)argv;if(getpid()!=1)return 111;
    sw_require(argc==1 ? sw_load_state() : EINVAL);sw_last_stage=SW_EXEC;
    sw_require(sw_witness());
    uint8_t proof[120]={0};
    sw_put32(proof,1);sw_put32(proof+4,(uint32_t)major((dev_t)sw.root_device));
    sw_put32(proof+8,(uint32_t)minor((dev_t)sw.root_device));sw_put32(proof+12,sw.mount_count);
    memcpy(proof+16,sw.boot,32);memcpy(proof+48,sw.witness_digest,32);memcpy(proof+80,sw.mount_digest,32);
    sw_put32(proof+112,15);sw_put32(proof+116,1); /* root flags; partition RO */
    sw_require(sw_record(SW_WITNESS,0,proof,sizeof(proof)));sw_return();
}
