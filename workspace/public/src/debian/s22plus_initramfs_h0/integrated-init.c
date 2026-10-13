/* Temporary initial-namespace PID1 entry, exec'd by Debian /init. The native
 * manager is absent. Reuse the exact protected admission and root transition. */
static int di_stage_parent(void);
#define SW_STAGE_ADDITIONAL_RAM di_stage_parent
#define S22_SWITCH_ROOT_LIBRARY
#include "s22plus_switch_root_v1.c"
#define EARLY_OBSERVER_LIBRARY
#define EARLY_USB_FIRST
#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-INTEGRATED-v1"
#include "early-observer.c"

#define DI_UFS_LOG 179U
#define DI_UFS_END 180U
static uint8_t di_parent[208],di_ufs[8192];
static size_t di_ufs_size;

static int di_read_ram(const char *name,void *data,size_t maximum,size_t *size) {
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;struct statfs fs;
    if(dir<0)return fs1_error();
    int error=fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
        fstatfs(dir,&fs) || fs.f_type!=0x01021994L ? EPROTO : 0;
    int fd=error ? -1 : openat(dir,name,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0 && !error)error=fs1_error();
    if(close(dir) && !error)error=fs1_error();
    if(!error && (fstat(fd,&st) || st.st_uid || st.st_gid || st.st_nlink!=1 ||
       st.st_mode!=(S_IFREG|0400) || st.st_size<=0 || (uint64_t)st.st_size>maximum))error=EPROTO;
    if(!error) {
        *size=(size_t)st.st_size;uint8_t extra;
        if(read(fd,data,*size)!=(ssize_t)*size || read(fd,&extra,1)!=0)error=EIO;
    }
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    return error;
}
static int di_parent_proof(void) {
    size_t size=0;uint8_t tag[32],boot[32],hash[32];
    int error=di_read_ram("initial-parent",di_parent,sizeof(di_parent),&size);
    if(error || size!=sizeof(di_parent))return error ? error : EPROTO;
    early_tag(tag,di_parent+16,243,1,di_parent,176);
    if(memcmp(tag,di_parent+176,32) || sw_boot(boot) || memcmp(boot,di_parent+16,32) ||
       early_u32(di_parent)!=1 || early_u32(di_parent+4)<=1 || early_u32(di_parent+8)!=0 ||
       memcmp(di_parent+48,early_shell_hash,32) || memcmp(di_parent+80,early_init_hash,32) ||
       memcmp(di_parent+144,early_helper_hash,32))return EPROTO;
    error=di_read_ram("fyg8-events",log_bytes,sizeof(log_bytes),&log_size);if(error)return error;
    early_hash(log_bytes,log_size,hash);
    if(log_size!=early_u32(di_parent+12) || memcmp(hash,di_parent+112,32))return EPROTO;
    memcpy(proof,di_parent,176);
    return 0;
}
static int di_ufs_child(void) {
    int fd=fs1_pin_file("/sbin/fyg8-prepare",early_helper_size,early_helper_hash,true);
    if(fd<0)return fs1_error();
    if(close(fd))return fs1_error();
    if(now()>=deadline)return ETIMEDOUT;
    pid_t child=fork();if(child<0)return fs1_error();
    if(!child) {
        if(syscall(SYS_close_range,3U,UINT_MAX,0U))_exit(125);
        if(now()>=deadline)_exit(124);
        char *args[]={"/sbin/fyg8-prepare","ufs",NULL};
        char *env[]={"PATH=/usr/sbin:/usr/bin:/sbin:/bin","LC_ALL=C",NULL};
        execve(args[0],args,env);_exit(126);
    }
    int status=0;uint64_t end=now()+30000;int error=0;
    if(end>deadline)end=deadline;
    for(;;) {
        pid_t got=waitpid(child,&status,WNOHANG);
        if(got==child)break;
        if(got<0){error=fs1_error();break;}
        if(now()>=end){error=ETIMEDOUT;break;}
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL)){error=fs1_error();break;}
    }
    if(error) {
        if(kill(child,SIGKILL) && errno!=ESRCH)return fs1_error();
        uint64_t settle=now()+SW_SETTLE_MS;
        for(;;) {
            pid_t got=waitpid(child,&status,WNOHANG);
            if(got==child)break;
            if(got<0)return fs1_error();
            if(now()>=settle || now()>=deadline)return ETIMEDOUT;
            struct timespec delay={0,10000000};if(nanosleep(&delay,NULL))return fs1_error();
        }
        return error;
    }
    if(!WIFEXITED(status) || WEXITSTATUS(status))return ECHILD;
    return sw_no_children();
}
static int di_copy_ram(const char *name,const void *data,size_t size) {
    char path[128];int n=snprintf(path,sizeof(path),"/s22-handoff-run/s22-debian/early-%s",name);
    if(n<=0 || (size_t)n>=sizeof(path))return EOVERFLOW;
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(fd<0)return fs1_error();
    int error=write(fd,data,size)==(ssize_t)size ? 0 : EIO;
    if(close(fd) && !error)error=fs1_error();
    uint8_t digest[32];early_hash(data,size,digest);
    if(!error) {
        fd=fs1_pin_file(path,size,digest,false);if(fd<0)return fs1_error();
        struct statfs fs;if(fstatfs(fd,&fs) || fs.f_type!=0x01021994L)error=EPROTO;
        if(close(fd) && !error)error=fs1_error();
    }
    return error;
}
static int di_stage_parent(void) {
    int error=di_copy_ram("parent",di_parent,sizeof(di_parent));
    if(!error)error=di_copy_ram("platform",log_bytes,log_size);
    if(!error)error=di_copy_ram("ufs",di_ufs,di_ufs_size);
    return error;
}
static __attribute__((noreturn)) void di_fail(int error) {
#ifdef EARLY_VM_TEST
    dprintf(2,"INTEGRATED_VM_STOP errno=%d\n",error);
#endif
    (void)error;sw_park();
}
int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getpid()!=1 || getuid() || geteuid() || getgid() || getegid())di_fail(EACCES);
    uint64_t began=now();if(began==UINT64_MAX)di_fail(EIO);deadline=began+EARLY_TIMEOUT;
    int error=di_parent_proof();if(error)di_fail(error);
    if((error=sw_no_children()) || (error=sw_userspace()))di_fail(error);
    if(mount(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL))di_fail(fs1_error());
    if((error=gadget()))di_fail(error);
#ifdef EARLY_VM_TEST
    if(mkdir("/config",0755) || mount("configfs","/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))di_fail(fs1_error());
#endif
    int fd=serial_open();if(fd<0)di_fail(EIO);
    if(fd!=3){if(dup2(fd,3)!=3 || close(fd))di_fail(fs1_error());}
    if(fcntl(3,F_SETFD,0))di_fail(fs1_error());
    struct termios tty,checked;
    if(tcgetattr(3,&tty))di_fail(fs1_error());
    cfmakeraw(&tty);tty.c_cflag|=CLOCAL|CREAD;tty.c_cc[VMIN]=1;tty.c_cc[VTIME]=0;
    if(tcsetattr(3,TCSANOW,&tty) || tcgetattr(3,&checked) ||
       tty.c_iflag!=checked.c_iflag || tty.c_oflag!=checked.c_oflag || tty.c_cflag!=checked.c_cflag ||
       tty.c_lflag!=checked.c_lflag || checked.c_cc[VMIN]!=1 || checked.c_cc[VTIME])di_fail(EPROTO);
    if((error=gadget_bind()))di_fail(error);
#ifdef EARLY_VM_TEST
    struct stat device;if(fstat(3,&device) || mknod("/dev/sw-tty",S_IFCHR|0600,device.st_rdev))di_fail(EIO);
    dprintf(2,"INTEGRATED_VM_WIRE_READY\n");
#endif
    if((error=request(3)))di_fail(error);
    if((error=emit(3,EARLY_PROOF,2,proof,sizeof(proof))))di_fail(error);
    unsigned seq=3;
    for(size_t at=0;at<log_size;at+=EARLY_CHUNK) {
        size_t size=log_size-at;if(size>EARLY_CHUNK)size=EARLY_CHUNK;
        if((error=emit(3,EARLY_LOG,seq++,log_bytes+at,size)))di_fail(error);
    }
    if((error=emit(3,EARLY_END,seq++,proof+112,32)))di_fail(error);
    /* USB is already published; this exact child owns the one UFS insertion. */
    if((error=di_ufs_child()))di_fail(error);
    if((error=di_read_ram("ufs-events",di_ufs,sizeof(di_ufs),&di_ufs_size)))di_fail(error);
    for(size_t at=0;at<di_ufs_size;at+=EARLY_CHUNK) {
        size_t size=di_ufs_size-at;if(size>EARLY_CHUNK)size=EARLY_CHUNK;
        if((error=emit(3,DI_UFS_LOG,seq++,di_ufs+at,size)))di_fail(error);
    }
    uint8_t digest[32];early_hash(di_ufs,di_ufs_size,digest);
    if((error=emit(3,DI_UFS_END,seq,digest,32)))di_fail(error);
    /* From here reuse admission and transition with accurate early ownership. */
    memset(&sw,0,sizeof(sw));sw.magic=SW_STATE_MAGIC;sw.version=SW_STATE_VERSION;sw.sequence=SW_SEQUENCE;
    memcpy(sw.run,early_run,16);memcpy(sw.nonce,nonce,32);memcpy(sw.boot,proof+16,32);
    sw.deadline_ms=deadline;
    struct stat tty_st;if(fstat(3,&tty_st))di_fail(fs1_error());sw.tty_device=(uint64_t)tty_st.st_rdev;
    int nullfd=open("/dev/null",O_RDWR|O_NOFOLLOW|O_CLOEXEC);if(nullfd<0)di_fail(fs1_error());
    for(int i=0;i<3;++i)if(dup2(nullfd,i)!=i)di_fail(fs1_error());
    if(nullfd>3 && close(nullfd))di_fail(fs1_error());
    sw_require(sw_fd_whitelist(0));sw_require(sw_record(SW_ENTER,0,"actual-pid1",11));
    sw_require(sw_no_children());sw_require(sw_userspace());sw.settled=1;
    static const char settled[]="early-children-settled";
    sw_require(sw_record(SW_WORKERS,0,settled,sizeof(settled)-1));
    /* Keep the existing prepare/witness ABI: admission fds start above the
     * sealed state in fd 4, so the unchanged close/mount boundaries apply. */
    int statefd=open("/dev/null",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(statefd!=4)sw_stop(EPROTO);
    sw_require(sw_save_state());
    if(sw_now()>=sw.deadline_ms)sw_stop(ETIMEDOUT);
    if(mkdir("/s22-root-work",0700) ||
       mount("tmpfs","/s22-root-work","tmpfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,"mode=0700"))sw_stop(fs1_error());
    char *args[]={"/s22-switch-root","staged",(char *)fs1_run_id,NULL};
    int result=ri_run(3,args,"staged",sw_next);
    sw_stop(result ? EIO : EPROTO);
}
