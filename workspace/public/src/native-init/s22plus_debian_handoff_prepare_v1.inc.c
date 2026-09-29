#include "s22plus_debian_handoff_payload_v1.h"
static int dh_stage_assets(void) {
    if(mkdir("/s22-handoff-run/s22-debian",0700))return fs1_error();
    for(unsigned i=0;i<sizeof(dh_assets)/sizeof(dh_assets[0]);++i) {
        const struct dh_asset *a=dh_assets+i;
        int input=fs1_pin_file(a->source,a->size,a->digest,a->mode&0111);
        if(input<0)return fs1_error();
        char path[128];snprintf(path,sizeof(path),"/s22-handoff-run/s22-debian/%s",a->name);
        int output=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,a->mode);
        int error=output<0 ? fs1_error() : 0;uint8_t bytes[65536];uint64_t used=0;
        while(!error && used<a->size) {
            size_t n=a->size-used;if(n>sizeof(bytes))n=sizeof(bytes);
            if(read(input,bytes,n)!=(ssize_t)n || write(output,bytes,n)!=(ssize_t)n)error=EIO;
            used+=n;
        }
        if(close(input) && !error)error=fs1_error();
        if(output>=0 && close(output) && !error)error=fs1_error();
        if(error)return error;
        int checked=fs1_pin_file(path,a->size,a->digest,a->mode&0111);
        if(checked<0)return fs1_error();
        if(close(checked))return fs1_error();
    }
    return 0;
}
static void dh_activate_root(struct fs1_endpoint *e) {
    if(chdir("/") || syscall(SYS_close_range,5U,UINT_MAX,0U) || umount2(ri_root,0))sw_stop(fs1_error());
    sw_require(fs1_not_mounted(e->partition));
    int fd=fs1_open_block(fs1_node,e->partition,FS1_BYTES),value=0,actual=-1;
    if(fd<0)sw_stop(fs1_error());
    /* The compound host intent owns this sole RO-clear and writable mount.
     * Any failure parks; no cleanup branch clears/remounts/retries again. */
    if(ioctl(fd,BLKROSET,&value) || ioctl(fd,BLKROGET,&actual) || actual)sw_stop(fs1_error());
    uint64_t ro=1;sw_require(fs1_number(e->sys_partition,"ro",&ro));if(ro)sw_stop(EPROTO);
    if(close(fd) || mount(fs1_node,ri_root,"ext4",0,"errors=remount-ro,nodiscard"))sw_stop(fs1_error());
    struct stat st;struct statfs fs;
    if(stat(ri_root,&st) || statfs(ri_root,&fs) || st.st_dev!=e->partition || fs.f_type!=0xef53 ||
       (fs.f_flags&(ST_RDONLY|ST_NODEV|ST_NOEXEC|ST_NOSUID)))sw_stop(EPROTO);
}
