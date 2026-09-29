/* First synchronous SysVinit child. Failure must park: SysVinit deliberately
 * ignores a failed sysinit child's exit status and would otherwise start rcS. */
#define FS1_READONLY_BINDING_ONLY
#define S22_DEBIAN_HOOK
#include "s22plus_native_ext4_v1.c"
#include "s22plus_switch_root_common_v1.inc.c"
#include "s22plus_debian_handoff_common_v1.inc.c"
static __attribute__((noreturn)) void dh_hook_fail(int error) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dprintf(2,"DHVM_HOOK_PARK errno=%d\n",error);
#endif
    if(sw.deadline_ms && !sw_broken)(void)sw_record(SW_STOP,error>0 && error<4096 ? error : EPROTO,&sw_last_stage,sizeof(sw_last_stage));
    for(;;){struct timespec pause={1,0};(void)nanosleep(&pause,NULL);}
}
static int dh_load(struct dh_state *state) {
    int fd=open(DH_STATE_PATH,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;uint8_t boot[32],tag[32];
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
        st.st_mode!=(S_IFREG|0400) || st.st_uid || st.st_gid || st.st_nlink!=1 || st.st_size!=sizeof(*state) ||
        read(fd,state,sizeof(*state))!=sizeof(*state) ? EPROTO : 0;
    if(close(fd) && !error)error=fs1_error();
    if(error)return error;
    sw=state->native;
    if(sw.magic!=SW_STATE_MAGIC || sw.version!=SW_STATE_VERSION || sw.sequence!=SW_SEQUENCE ||
       memcmp(sw.run,sw_run,16) || sw.reserved || !sw.settled || !sw.root_admitted ||
       sw.next_record>=SW_MAX_RECORDS || sw_now()>=sw.deadline_ms || sw.deadline_ms-sw_now()>SW_TIMEOUT_MS ||
       sw_boot(boot) || memcmp(boot,sw.boot,32))return EPROTO;
    sw_tag(tag,DH_STATE_TAG,0,(const uint8_t *)state,sizeof(*state)-32);
    unsigned difference=0;for(unsigned i=0;i<32;++i)difference|=tag[i]^state->tag[i];
    return difference ? EPROTO : 0;
}
static int dh_reopen(void) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    const char *path="/dev/sw-tty";
#else
    const char *path="/dev/ttyGS0";
#endif
    int fd=open(path,O_RDWR|O_NONBLOCK|O_NOCTTY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;struct termios tty,readback;
    if(fstat(fd,&st) || !S_ISCHR(st.st_mode) || (uint64_t)st.st_rdev!=sw.tty_device || tcgetattr(fd,&tty))return EPROTO;
    cfmakeraw(&tty);tty.c_cc[VMIN]=1;tty.c_cc[VTIME]=0;
    if(tcsetattr(fd,TCSANOW,&tty) || tcgetattr(fd,&readback) ||
       tty.c_iflag!=readback.c_iflag || tty.c_oflag!=readback.c_oflag || tty.c_cflag!=readback.c_cflag ||
       tty.c_lflag!=readback.c_lflag || readback.c_cc[VMIN]!=1 || readback.c_cc[VTIME])return EPROTO;
    if(fd!=3){if(dup2(fd,3)!=3 || close(fd))return fs1_error();}
    if(fcntl(3,F_SETFD,0))return fs1_error();
    return sw_fd_type();
}
static int dh_actual_init(struct dh_state *state) {
    struct stat st,root,exe;struct statfs fs;
    if(getpid()<=1 || getuid() || geteuid() || getgid() || getegid() ||
       access("/proc/1/ns/pid",F_OK)==0 || stat("/",&root) || (uint64_t)root.st_dev!=sw.root_device ||
       stat("/proc/1/root",&st) || st.st_dev!=root.st_dev || st.st_ino!=root.st_ino ||
       statfs("/",&fs) || fs.f_type!=0xef53 || (fs.f_flags&(ST_RDONLY|ST_NODEV|ST_NOEXEC|ST_NOSUID)) ||
       stat("/usr/sbin/init",&exe) || stat("/proc/1/exe",&st) || exe.st_dev!=st.st_dev || exe.st_ino!=st.st_ino)return EPROTO;
    int error=dh_pin_init();if(error)return error;
    if(stat(DH_HOOK_PATH,&st) || stat("/proc/self/exe",&exe) || st.st_dev!=exe.st_dev || st.st_ino!=exe.st_ino)return EPROTO;
    int hook=fs1_pin_file(DH_HOOK_PATH,(uint64_t)st.st_size,state->hook_sha,true);
    if(hook<0)return fs1_error();
    if(close(hook))return fs1_error();
    DIR *d=opendir("/proc/1/fd");if(!d)return fs1_error();unsigned count=0;
    for(;;) {
        errno=0;struct dirent *entry=readdir(d);if(!entry){if(errno)error=errno;break;}
        if(entry->d_name[0]=='.')continue;
        if(++count>64){error=EOVERFLOW;break;}
        if(fstatat(dirfd(d),entry->d_name,&st,0) || (S_ISCHR(st.st_mode) && (uint64_t)st.st_rdev==sw.tty_device))
            {error=EPROTO;break;}
        char path[256];ssize_t n=readlinkat(dirfd(d),entry->d_name,path,sizeof(path)-1);
        if(n<0 || n>=(ssize_t)sizeof(path)-1){error=EPROTO;break;}path[n]=0;
        if(strstr(path,"s22-switch-state") || !strcmp(path,DH_STATE_PATH)){error=EPROTO;break;}
    }
    if(closedir(d) && !error)error=fs1_error();
    return error;
}
static int dh_retire_acm(void) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    return S22_DEBIAN_FAULT==2 ? EIO : 0;
#else
    static const char udc[]="/run/config/usb_gadget/g1/UDC";char text[64];
    int error=fs1_read_text(udc,text,sizeof(text));if(error)return error;
    if(strcmp(text,"a600000.dwc3\n"))return EPROTO;
    int fd=open(udc,O_WRONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    error=write(fd,"\n",1)==1 ? 0 : EIO;if(close(fd) && !error)error=fs1_error();
    if(!error)error=fs1_read_text(udc,text,sizeof(text));
    return error ? error : !strcmp(text,"\n") ? 0 : EPROTO;
#endif
}
int main(int argc,char **argv) {
    (void)argv;struct dh_state state={0};int error;
    if(argc!=1 || getpid()<=1)dh_hook_fail(EINVAL);
    if((error=dh_load(&state)))dh_hook_fail(error);
    sw_last_stage=SW_WITNESS;
    if((error=dh_reopen()))dh_hook_fail(error);
    if(S22_DEBIAN_FAULT==1)dh_hook_fail(EPROTO);
    if((error=dh_actual_init(&state)))dh_hook_fail(error);
    uint8_t proof[116]={0};sw_put32(proof,1);sw_put32(proof+4,(uint32_t)major((dev_t)sw.root_device));
    sw_put32(proof+8,(uint32_t)minor((dev_t)sw.root_device));
    memcpy(proof+12,sw.boot,32);memcpy(proof+44,dh_init_sha256,32);memcpy(proof+76,state.hook_sha,32);
    /* Last two fields are inherited ACM and state fd counts, both proved 0. */
    if((error=sw_send(DH_INIT_PROOF,7,proof,sizeof(proof))))dh_hook_fail(error);
    /* Invalid release parks even in the VM: failed sysinit must block rcS. */
    dh_request(DH_RELEASE,7,DH_RELEASE_ACK);
    if(close(3) || (error=dh_retire_acm()))dh_hook_fail(error ? error : EIO);
    return 0;
}
