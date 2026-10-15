/* Debian's initial shell execs this once after both supervised children have
 * returned success. No USB observer or host command owns this transition. */
#define _GNU_SOURCE
#include <sys/types.h>
static int ab_stage_early(void);
static int ab_owned_file(int,dev_t);
#define SW_STAGE_ADDITIONAL_RAM ab_stage_early
#define SW_OWNED_ROOT_EXTRA ab_owned_file
#define S22_SWITCH_ROOT_LIBRARY
#define S22_AUTOBOOT_SECOND_ADMISSION
#include "s22plus_switch_root_v1.c"
#include "early-seal.h"
#include "early-protocol.h"

#define AB_EARLY_MAX 16384U
static uint8_t ab_early[AB_EARLY_MAX],ab_hash[32];
static size_t ab_size;

static int ab_receipt(void) {
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;struct statfs fs;
    if(dir<0)return fs1_error();
    int error=fstat(dir,&st) || st.st_mode!=(S_IFDIR|0700) || st.st_uid || st.st_gid ||
        fstatfs(dir,&fs) || fs.f_type!=0x01021994L ? EPROTO : 0;
    int fd=error ? -1 : openat(dir,"autoboot-early",O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0 && !error)error=fs1_error();
    if(close(dir) && !error)error=fs1_error();
    if(!error && (fstat(fd,&st) || st.st_mode!=(S_IFREG|0400) || st.st_uid || st.st_gid ||
        st.st_nlink!=1 || st.st_size<256+14*128 || st.st_size>AB_EARLY_MAX))error=EPROTO;
    if(!error) {
        ab_size=(size_t)st.st_size;uint8_t extra;
        if(read(fd,ab_early,ab_size)!=(ssize_t)ab_size || read(fd,&extra,1)!=0)error=EIO;
    }
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(error)return error;
    const uint8_t *proof=ab_early+32;uint8_t tag[32],boot[32],hash[32];
    unsigned log_size=early_u32(proof+12);
    early_tag(tag,proof+16,0,0,ab_early,224);
    uint64_t origin=fs1_u64(ab_early+208),last=0;
    if(memcmp(ab_early,"S22FL03\0",8) || early_u32(ab_early+8)!=3 || early_u32(ab_early+12)!=256 ||
       memcmp(ab_early+16,early_run,16) || memcmp(ab_early+224,tag,32) ||
       early_u32(proof)!=1 || early_u32(proof+4)<=1 || early_u32(proof+8) ||
       !log_size || log_size>AB_EARLY_MAX-256-14*128 || ab_size!=256+log_size+14*128 ||
       sw_boot(boot) || memcmp(boot,proof+16,32) || origin>=300000 || fs1_u64(ab_early+216) ||
       memcmp(proof+48,early_shell_hash,32) || memcmp(proof+80,early_init_hash,32) ||
       memcmp(proof+144,early_helper_hash,32))return EPROTO;
    early_hash(ab_early+256,log_size,hash);if(memcmp(hash,proof+112,32))return EPROTO;
    const uint8_t *previous=ab_early+224;
    for(unsigned i=0;i<14;++i) {
        const uint8_t *row=ab_early+256+log_size+i*128;
        unsigned kind=i==0 ? 1 : i==13 ? 4 : i%2 ? 2 : 3;
        unsigned phase=i==0 || i==13 ? 0 : (i+1)/2;
        uint64_t elapsed=fs1_u64(row+16);
        early_tag(tag,boot,kind,i,row,96);
        if(memcmp(row,"S22FLR3\0",8) || early_u32(row+8)!=i || early_u32(row+12)!=kind ||
           early_u32(row+24)!=phase || early_u32(row+28) || elapsed<last || elapsed>=300000-origin ||
           memcmp(row+64,previous,32) || memcmp(row+96,tag,32))return EPROTO;
        for(unsigned j=32;j<64;++j)if(row[j])return EPROTO;
        last=elapsed;previous=row+96;
    }
    sw_hash(ab_early,ab_size,ab_hash);memcpy(sw.boot,boot,32);
    /* The nonce denotes this automatic same-boot record, not a host request. */
    sw_hash(ab_early,256,sw.nonce);
    return 0;
}
static int ab_owned_file(int root,dev_t device) {
    char path[128],leaf[NAME_MAX+1];
    int n=snprintf(path,sizeof(path),"var/lib/lab/s22-early-%s",fs1_run_id);
    if(n<=0 || n>=(int)sizeof(path))return EOVERFLOW;
    int parent=ri_parent(root,device,path,leaf);if(parent<0)return fs1_error();
    struct stat st;uint8_t hash[32];
    int error=fstatat(parent,leaf,&st,AT_SYMLINK_NOFOLLOW) || st.st_mode!=(S_IFREG|0600) ||
        st.st_dev!=device || st.st_uid || st.st_gid || st.st_nlink!=1 || st.st_size!=(off_t)ab_size ? EPROTO : 0;
    if(!error)error=ri_hash_file(parent,leaf,device,ab_size,hash);
    if(!error && memcmp(hash,ab_hash,32))error=EPROTO;
    if(close(parent) && !error)error=fs1_error();
    return error;
}
static int ab_stage_early(void) {
    const char *path="/s22-handoff-run/s22-debian/early";
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(fd<0)return fs1_error();
    int error=write(fd,ab_early,ab_size)==(ssize_t)ab_size ? 0 : EIO;
    if(close(fd) && !error)error=fs1_error();
    if(!error) {
        fd=fs1_pin_file(path,ab_size,ab_hash,false);if(fd<0)return fs1_error();
        if(close(fd))error=fs1_error();
    }
    return error;
}
static int ab_initial_fds(void) {
    DIR *dir=opendir("/proc/self/fd");if(!dir)return fs1_error();
    int error=0;unsigned count=0;
    for(;;) {
        errno=0;struct dirent *entry=readdir(dir);
        if(!entry){if(errno)error=errno;break;}
        if(entry->d_name[0]=='.')continue;
        char *end;long fd=strtol(entry->d_name,&end,10);
        if(*end || fd<0 || fd>INT_MAX || ++count>4 || (fd>2 && fd!=dirfd(dir))){error=EPROTO;break;}
    }
    if(closedir(dir) && !error)error=fs1_error();
    return error;
}
int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getpid()!=1 || getuid() || geteuid() || getgid() || getegid())sw_park();
    memset(&sw,0,sizeof(sw));sw.magic=SW_STATE_MAGIC;sw.version=SW_STATE_VERSION;sw.sequence=SW_SEQUENCE;
    memcpy(sw.run,sw_run,16);sw.deadline_ms=300000;
    /* No renewed timer and no inherited helper/console descriptor. */
    int error=sw_now()>=sw.deadline_ms ? ETIMEDOUT : ab_receipt();
    if(!error)error=sw_no_children();
    if(!error)error=sw_userspace();
    if(!error)error=ab_initial_fds();
    if(error)sw_stop(error);
    if(mount(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL) || syscall(SYS_close_range,3U,UINT_MAX,0U))sw_park();
    int nullfd=open("/dev/null",O_RDWR|O_NOFOLLOW|O_CLOEXEC);if(nullfd<0)sw_park();
    for(int i=0;i<3;++i)if(dup2(nullfd,i)!=i)sw_park();
    if(nullfd>2 && close(nullfd))sw_park();
    int trace=memfd_create("s22-autoboot-trace",MFD_ALLOW_SEALING);struct stat st;
    if(trace!=3 || fchmod(trace,0600) || fcntl(trace,F_SETFL,O_RDWR|O_APPEND) || fstat(trace,&st))sw_park();
    sw.tty_device=(uint64_t)st.st_ino;
    static const char entered[]="debian-auto-pid1",settled[]="early-children-settled";
    sw_require(sw_fd_whitelist(0));sw_require(sw_record(SW_ENTER,0,entered,sizeof(entered)-1));
    sw.settled=1;sw_require(sw_record(SW_WORKERS,0,settled,sizeof(settled)-1));
    /* Reuse the empty work mount owned by the successful first phase. The
     * empty configfs mount preserves the checked transition mount ABI; no
     * gadget is created before the installed Debian service runs. */
    struct statfs fs;
    if(lstat("/s22-root-work",&st) || st.st_mode!=(S_IFDIR|0700) || st.st_uid || st.st_gid ||
       statfs("/s22-root-work",&fs) || fs.f_type!=0x01021994L ||
       (fs.f_flags&(ST_NOSUID|ST_NODEV|ST_NOEXEC))!=(ST_NOSUID|ST_NODEV|ST_NOEXEC) ||
       fs1_empty_directory("/s22-root-work"))sw_stop(EPROTO);
    if(mkdir("/config",0755) || mount("configfs","/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))sw_stop(fs1_error());
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    /* The fixed VM kernel has CONFIG_USB_SUPPORT=n. Its real empty configfs
     * mount substitutes only the absent Samsung gadget subsystem. */
    if(fs1_empty_directory("/config"))sw_stop(EPROTO);
#else
    if(fs1_empty_directory("/config/usb_gadget"))sw_stop(EPROTO);
#endif
    int state=open("/dev/null",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(state!=4)sw_stop(EPROTO);
    sw_require(sw_save_state());
    char *args[]={"/s22-switch-root","staged",(char *)fs1_run_id,NULL};
    int result=ri_run(3,args,"staged",sw_next);sw_stop(result ? EIO : EPROTO);
}
