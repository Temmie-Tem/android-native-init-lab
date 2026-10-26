/* First synchronous SysVinit child. Failure must park: SysVinit deliberately
 * ignores a failed sysinit child's exit status and would otherwise start rcS. */
#define FS1_READONLY_BINDING_ONLY
#define S22_DEBIAN_HOOK
#include "s22plus_native_ext4_v1.c"
#include "s22plus_switch_root_common_v1.inc.c"
#include "s22plus_debian_handoff_common_v1.inc.c"
#include "s22plus_autoboot_singlecpu_v1.h"
#ifdef S22_DEBIAN_REBOOT
#include "s22plus_debian_reboot_common_v1.h"
#endif
#include "s22plus_debian_evidence_v1.inc.c"
#if defined(S22_AUTOBOOT_PHASE_TRACE) || defined(S22_AUTOBOOT_SCRIPT_CHANNEL)
static void ap_abort(void);
#endif
#ifdef S22_DEBIAN_CRON
static void cr_abort(void);
#endif
static __attribute__((noreturn)) void dh_hook_fail(int error) {
#ifdef S22_DEBIAN_CRON
    cr_abort();
#endif
#if defined(S22_AUTOBOOT_PHASE_TRACE) || defined(S22_AUTOBOOT_SCRIPT_CHANNEL)
    ap_abort();
#endif
    at_stop(error);
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dprintf(2,"DHVM_HOOK_PARK errno=%d\n",error);
#endif
    unsigned reason=error>0 && error<4096 ? (unsigned)error : EPROTO;
    if(de_loaded && !de_failed && !de.stopped && !de.control)(void)de_event(DE_STOP,0,0,reason,SW_WITNESS,0);
#ifndef S22_DEBIAN_AUTOBOOT
    if(sw.deadline_ms && !sw_broken && !de.off && !sw_fd_type()) {
        uint8_t body[12];sw_put32(body,SW_STOP);sw_put32(body+4,reason);sw_put32(body+8,sw_last_stage);
        uint64_t end=sw_now()+DE_REPORT_MS;if(end>sw.deadline_ms)end=sw.deadline_ms;
        (void)sw_send_until(SW_RECORD,1024+sw.next_record,body,sizeof(body),end);
    }
#endif
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
#ifndef S22_DEBIAN_AUTOBOOT
static int dh_open_failed;
static int dh_reopen(void) {
    dh_open_failed=0;
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dprintf(2,"DHVM_REPORT_OPEN phase=%u\n",de_mode);
    if((S22_DEBIAN_FAULT==25 && de_mode==2) || (S22_DEBIAN_FAULT==29 && de_mode==1 && de.progress==1))
        {dh_open_failed=1;return ENOENT;}
    if(S22_DEBIAN_FAULT==30 && de_mode==1)return EPROTO;
    const char *path="/dev/sw-tty";
#else
    const char *path="/dev/ttyGS0";
#endif
    int fd=open(path,O_RDWR|O_NONBLOCK|O_NOCTTY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0){dh_open_failed=1;return fs1_error();}
    struct stat st;struct termios tty,readback;
    if(fstat(fd,&st) || !S_ISCHR(st.st_mode) || (uint64_t)st.st_rdev!=sw.tty_device || tcgetattr(fd,&tty))
        {(void)close(fd);return EPROTO;}
    cfmakeraw(&tty);tty.c_cc[VMIN]=1;tty.c_cc[VTIME]=0;
    if(tcsetattr(fd,TCSANOW,&tty) || tcgetattr(fd,&readback) ||
       tty.c_iflag!=readback.c_iflag || tty.c_oflag!=readback.c_oflag || tty.c_cflag!=readback.c_cflag ||
       tty.c_lflag!=readback.c_lflag || readback.c_cc[VMIN]!=1 || readback.c_cc[VTIME])
        {(void)close(fd);return EPROTO;}
    if(fd!=3){
        if(dup2(fd,3)!=3){int error=fs1_error();(void)close(fd);return error;}
        if(close(fd))return fs1_error();
    }
    if(fcntl(3,F_SETFD,0))return fs1_error();
    return sw_fd_type();
}
/* Only known reporting I/O loss after durable START may disable reporting.
 * Descriptor identity, termios and close failures are never optional. */
static int dh_reporting_open(void) {
    if(de.off)return 0;
    int error=de_time();if(error)return error;
    error=dh_reopen();
    if(error)sw_broken=1; /* A failed open/identity check cannot report on fd 3. */
    if(error && dh_open_failed && de.started) {
        return de_report_lost(error,0,0);
    }
    return error;
}
static int dh_reporting_close(void) {
    if(de.off)return 0;
    int error=close(3) ? fs1_error() : 0;
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 27
    if(!error)error=EIO;
#endif
    if(error)sw_broken=1;
    return error;
}
static int dh_report(unsigned kind,unsigned sequence,const void *body,size_t size) {
    if(de.off)return 0;
    int error=sw_fd_type();if(error)return error;
    uint64_t end=sw_now()+DE_REPORT_MS;if(end>sw.deadline_ms)end=sw.deadline_ms;
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dprintf(2,"DHVM_REPORT_SEND phase=%u kind=%u sequence=%u\n",de_mode,kind,sequence);
    int lost=(S22_DEBIAN_FAULT==20 && kind==DH_INIT_PROOF) ||
        (S22_DEBIAN_FAULT==21 && kind==DH_START_ACK) ||
        (S22_DEBIAN_FAULT==22 && kind==DH_PROGRESS && sequence==2000) ||
        (S22_DEBIAN_FAULT==23 && kind==DH_BOUNDARY && sequence==3000) ||
        (S22_DEBIAN_FAULT==24 && kind==DH_PROGRESS && sequence==2001) ||
        (S22_DEBIAN_FAULT==26 && kind==DH_PROGRESS && sequence==2003);
    error=lost ? EPIPE : sw_send_until(kind,sequence,body,size,end);
#else
    error=sw_send_until(kind,sequence,body,size,end);
#endif
    if(!error)return 0;
    if(!de.started || !de_transport_error(error))return error;
    int stored=de_report_lost(error,kind,sequence);
    /* This descriptor is retired exactly once. No future hook reopens it. */
    int closed=close(3) ? fs1_error() : 0;
    return stored ? stored : closed;
}
#else
/* Automatic startup has no transport descriptor, open, close or host request.
 * Absence is checked explicitly; local de_event remains mandatory. */
static int dh_reporting_open(void) {
    int error=de_time();if(error)return error;
    return fcntl(3,F_GETFD)==-1 && errno==EBADF ? 0 : EPROTO;
}
static int dh_reporting_close(void) {return dh_reporting_open();}
static int dh_report(unsigned kind,unsigned sequence,const void *body,size_t size) {
    (void)kind;(void)sequence;(void)body;(void)size;return dh_reporting_open();
}
#endif
static int dh_actual_init_mode(struct dh_state *state,bool readonly) {
    struct stat st,root,exe;struct statfs fs;
    if(getpid()<=1 || getuid() || geteuid() || getgid() || getegid() ||
       access("/proc/1/ns/pid",F_OK)==0 || stat("/",&root) || (uint64_t)root.st_dev!=sw.root_device ||
       stat("/proc/1/root",&st) || st.st_dev!=root.st_dev || st.st_ino!=root.st_ino ||
       statfs("/",&fs) || fs.f_type!=0xef53 || ((bool)(fs.f_flags&ST_RDONLY)!=readonly) || (fs.f_flags&(ST_NODEV|ST_NOEXEC|ST_NOSUID)) ||
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
        if(fstatat(dirfd(d),entry->d_name,&st,0)
#ifndef S22_DEBIAN_AUTOBOOT
           || (S_ISCHR(st.st_mode) && (uint64_t)st.st_rdev==sw.tty_device)
#endif
           )
            {error=EPROTO;break;}
        char path[256];ssize_t n=readlinkat(dirfd(d),entry->d_name,path,sizeof(path)-1);
        if(n<0 || n>=(ssize_t)sizeof(path)-1){error=EPROTO;break;}path[n]=0;
        if(strstr(path,"s22-switch-state") ||
#ifdef S22_DEBIAN_AUTOBOOT
           strstr(path,"s22-autoboot-trace") ||
#endif
           !strcmp(path,DH_STATE_PATH)){error=EPROTO;break;}
    }
    if(closedir(d) && !error)error=fs1_error();
    return error;
}
static int dh_actual_init(struct dh_state *state) {return dh_actual_init_mode(state,false);}
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
#include "s22plus_debian_handoff_observer_v2.inc.c"
#ifdef S22_DEBIAN_DOWNLOAD
#include "s22plus_debian_download_return_v1.inc.c"
#endif
int main(int argc,char **argv) {
    struct dh_state state={0};int error;
#ifdef S22_DEBIAN_DOWNLOAD
    if(argc==2 && !strcmp(argv[1],"return-park"))dl_park(EIO);
    if(argc==2 && !strcmp(argv[1],"return-final"))dl_final();
#endif
#ifdef S22_DEBIAN_REBOOT
    if((error=rb_current_early()))return 110;
#ifdef S22_DEBIAN_APT
    if((argc==6 && !strcmp(argv[1],"apt-time")) || (argc==2 && !strcmp(argv[1],"apt-time-status"))) {
        at_disable();
        if((error=dh_load(&state)) || memcmp(rb_early_nonce,sw.nonce,32) ||
           (error=dh_actual_init(&state)))return 118;
        return argc==2 ? ap_clock_status() : ap_clock_request(argc,argv,&state);
    }
#endif
#ifdef S22_DEBIAN_CRON
    if(argc==2 && !strcmp(argv[1],"cron-job")) {
        at_disable();
        if((error=dh_load(&state)) || memcmp(rb_early_nonce,sw.nonce,32) ||
           (error=dh_actual_init(&state)))return 115;
        error=cr_job(&state);
        if(error)cr_abort();
        return error ? 116 : 0;
    }
#endif
    if(argc==2 && (!strcmp(argv[1],"phase") || !strcmp(argv[1],"reboot-intent") || !strcmp(argv[1],
#ifdef S22_DEBIAN_DOWNLOAD
        "download-intent"
#else
        "shutdown-intent"
#endif
        ))) {
        at_disable();pid_t cron=0,sshd=0;
        if((error=dh_load(&state)) || memcmp(rb_early_nonce,sw.nonce,32) || (error=dh_actual_init(&state)))return 111;
        if(!strcmp(argv[1],"phase"))return printf("%u\n",rb_phase)<0 || fflush(stdout) ? 112 : 0;
        unsigned kind=!strcmp(argv[1],"reboot-intent") ? RB_REBOOT_INTENT : RB_SHUTDOWN_INTENT;
        if((kind==RB_REBOOT_INTENT ? rb_phase!=1 : rb_phase!=2) ||
           (error=de_load(&state)) || !de.complete || de.control || de.off || de.stopped ||
           (error=dh_service("/run/crond.pid","/usr/sbin/cron",dh_cron_size,dh_cron_sha256,&cron)) ||
           (error=dh_service("/run/sshd.pid","/usr/sbin/sshd",dh_sshd_size,dh_sshd_sha256,&sshd)) || cron==sshd)return 113;
        return de_event(kind,rb_phase,0,RB_BASE_COUNT,rb_installed(rb_phase),0) ? 114 : 0;
    }
#endif
    /* The separately selected rcS invocation has a distinct bounded actor. */
    if(argc==2 && !strcmp(argv[1],"init"))AT_POINT(AT_HOOK_ENTRY,0,0);
#ifdef S22_AUTOBOOT_RCS_TRACE
    else if(argc==2 && !strcmp(argv[1],"rcs")){at_select(6);AT_POINT(AT_RCS_ENTRY,0,0);}
#endif
#ifdef S22_AUTOBOOT_WATCHDOG_TRACE
    else if(argc==2 && !strcmp(argv[1],"runlevel")){at_select(8);AT_POINT(AT_WATCHDOG_OWNER,0,0);}
#endif
    else at_disable();
    if(argc!=2 || getpid()<=1 || (strcmp(argv[1],"init") && strcmp(argv[1],"rcs") &&
       strcmp(argv[1],"runlevel") && strcmp(argv[1],"park")))dh_hook_fail(EINVAL);
    unsigned state_stage=AT_HOOK_STATE;
#ifdef S22_AUTOBOOT_RCS_TRACE
    if(!strcmp(argv[1],"rcs"))state_stage=AT_RCS_STATE;
#endif
#ifdef S22_AUTOBOOT_WATCHDOG_TRACE
    if(!strcmp(argv[1],"runlevel"))state_stage=AT_WATCHDOG_STATE;
#endif
    (void)state_stage;
    if((error=AT_CHECK(state_stage,dh_load(&state))))dh_hook_fail(error);
#ifdef S22_DEBIAN_REBOOT
    if(memcmp(rb_early_nonce,sw.nonce,32))dh_hook_fail(EPROTO);
#endif
    sw_last_stage=SW_WITNESS;
    if(!strcmp(argv[1],"park"))dh_hook_fail(EIO);
    if(strcmp(argv[1],"init")) {
        de_mode=!strcmp(argv[1],"rcs") ? 1 : 2;
        if((error=
#ifdef S22_AUTOBOOT_RCS_TRACE
            de_mode==1 ? AT_CHECK(AT_RCS_RUNTIME_LOAD,de_load(&state)) :
#endif
            de_load(&state)) || !de.started || de.stopped || de.complete)dh_hook_fail(error ? error : EPROTO);
        dh_later(&state,argv[1]);
    }
    if(S22_DEBIAN_FAULT==1)dh_hook_fail(EPROTO);
    if((error=AT_CHECK(AT_ACTUAL_INIT_CHECK,dh_actual_init(&state))))dh_hook_fail(error);
    if((error=AT_CHECK(AT_RUNTIME_FILE_BEGIN,de_begin(&state))) || (error=de_event(DE_INIT,0,0,1,0,0)))dh_hook_fail(error);
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 31
    if((error=de_begin(&state)))dh_hook_fail(error);
#endif
    if((error=dh_reporting_open()))dh_hook_fail(error);
    uint8_t proof[116]={0};sw_put32(proof,1);sw_put32(proof+4,(uint32_t)major((dev_t)sw.root_device));
    sw_put32(proof+8,(uint32_t)minor((dev_t)sw.root_device));
    memcpy(proof+12,sw.boot,32);memcpy(proof+44,dh_init_sha256,32);memcpy(proof+76,state.hook_sha,32);
    /* Last two fields are inherited ACM and state fd counts, both proved 0. */
    if((error=dh_report(DH_INIT_PROOF,7,proof,sizeof(proof))))dh_hook_fail(error);
    /* Release the synchronous init barrier without retiring the gadget.
     * Later Debian wait entries are its sole successive descriptor owners. */
#ifndef S22_DEBIAN_AUTOBOOT
    if((error=dh_auth_request(DH_START,DH_START_SEQUENCE)))dh_hook_fail(error);
#endif
    if((error=de_event(DE_START,0,0,DH_START_SEQUENCE,0,0)))dh_hook_fail(error);
    uint32_t accepted=1;
    if((error=dh_report(DH_START_ACK,DH_START_SEQUENCE,&accepted,sizeof(accepted))))dh_hook_fail(error);
    dh_claim("init-started",NULL);
    if((error=dh_reporting_close()))dh_hook_fail(error);
    return 0;
}
