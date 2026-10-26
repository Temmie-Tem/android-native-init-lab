/* Fixed, sequential children of installed SysVinit. No daemon, respawn,
 * shell console or native service manager survives this observation. */
#include "s22plus_autoboot_watchdog_v1.h"
#include "s22plus_autoboot_phase_v1.h"
static void dh_claim(const char *name,const char *previous) {
    char path[128];struct stat st;
    if(previous) {
        snprintf(path,sizeof(path),"/run/s22-debian/%s",previous);
        if(lstat(path,&st) || st.st_mode!=(S_IFREG|0400) || st.st_uid || st.st_gid ||
           st.st_nlink!=1 || st.st_size)dh_hook_fail(EPROTO);
    }
    snprintf(path,sizeof(path),"/run/s22-debian/%s",name);
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(fd<0 || close(fd))dh_hook_fail(fs1_error());
}
static void dh_progress(unsigned ordinal,unsigned stage,unsigned sample,uint64_t elapsed,unsigned services) {
    uint8_t body[56]={0};sw_put32(body,stage);sw_put32(body+4,sample);
    sw_put32(body+8,1);sw_put32(body+12,services);
    for(unsigned i=0;i<8;++i)body[16+i]=(uint8_t)(elapsed>>(8*i));
    memcpy(body+24,sw.boot,32);
    uint64_t platform=0;int error;
#ifdef S22_AUTOBOOT_SINGLECPU
    if((error=sc_observe(&platform)))dh_hook_fail(error);
#endif
    error=de_event(DE_PROGRESS,stage,sample,elapsed,services,platform);if(error)dh_hook_fail(error);
    error=dh_report(DH_PROGRESS,2000+ordinal,body,sizeof(body));if(error)dh_hook_fail(error);
}
/* Revision 4 retains the revision-3 wire boundaries; local records also bind
 * disabled reporting. Revision 3: phase 1 is rcS, phase 2 is rc2. Events are before-close,
 * reopened/verified, child-forked (not exec proof), waiting, child-exited.
 * All elapsed values use the original deadline, never a renewed timer. */
static unsigned dh_boundary_ordinal;
static void dh_boundary(unsigned phase,unsigned event,pid_t child,unsigned status,uint64_t auxiliary) {
    uint64_t now=sw_now();uint8_t body[64]={0};
    if(dh_boundary_ordinal>=DH_BOUNDARY_MAX || now>=sw.deadline_ms ||
       sw.deadline_ms-now>SW_TIMEOUT_MS)dh_hook_fail(ETIMEDOUT);
    sw_put32(body,phase);sw_put32(body+4,event);sw_put32(body+8,(unsigned)child);sw_put32(body+12,status);
    uint64_t elapsed=now-(sw.deadline_ms-SW_TIMEOUT_MS);
    for(unsigned i=0;i<8;++i){body[16+i]=(uint8_t)(elapsed>>(8*i));body[24+i]=(uint8_t)(auxiliary>>(8*i));}
    memcpy(body+32,sw.boot,32);
    int error=de_event(DE_BOUNDARY,phase,event,(unsigned)child,status,auxiliary);if(error)dh_hook_fail(error);
    error=dh_report(DH_BOUNDARY,(phase==1 ? 3000 : 3100)+dh_boundary_ordinal++,body,sizeof(body));
    if(error)dh_hook_fail(error);
}
static void dh_wait_script(struct dh_state *state,unsigned phase,const char *path,const char *argument) {
    /* The finite parent owns reporting while it waits. The phase dispatcher
     * alone may retain its nonblocking fd3; each service closes it on entry. */
    int error=0;
#ifdef S22_AUTOBOOT_RCS_TRACE
    bool traced=phase==1;
#else
    bool traced=false;
#endif
#ifdef S22_DEBIAN_AUTOBOOT
    if((error=dh_reporting_open()))dh_hook_fail(error);
#else
    if(de.off) {if(fcntl(3,F_GETFD)!=-1 || errno!=EBADF)dh_hook_fail(EPROTO);}
    else if((error=sw_fd_type()))dh_hook_fail(error);
#endif
    if((error=de_time()))dh_hook_fail(error);
#ifdef S22_AUTOBOOT_MINIMAL
    if(phase==1 && (error=ap_required_program()))dh_hook_fail(error);
#endif
    if(traced)ap_start();
    if(traced) {
        AT_BEGIN(AT_RCS_FORK,1);
        if((error=de_time()))dh_hook_fail(error);
    }
    pid_t child=fork();int fork_errno=errno;
    if(!child) {
#ifdef S22_AUTOBOOT_RCS_TRACE
        if(traced){at_fork_child(7);AT_POINT(AT_RCS_CHILD_ENTRY,0,0);}
#endif
#if defined(S22_AUTOBOOT_PHASE_TRACE) || defined(S22_AUTOBOOT_SCRIPT_CHANNEL)
        int channel=traced ? ap_child_channel() : 0;
        if(channel<0){AT_POINT(AP_CHILD_STAGE,0,(unsigned)-channel);channel=0;}
        unsigned first=channel ? 4U : 3U;
#else
        unsigned first=3U;
#endif
#if S22_DEBIAN_FAULT != 14
        if(traced ? AT_SYS(AT_RCS_CHILD_CLOSE_FDS,syscall(SYS_close_range,first,UINT_MAX,0U)) :
            syscall(SYS_close_range,first,UINT_MAX,0U))_exit(125);
#endif
#if defined(S22_AUTOBOOT_PHASE_TRACE) || defined(S22_AUTOBOOT_SCRIPT_CHANNEL)
        if(channel) {
            if(fcntl(4,F_GETFD)!=-1 || errno!=EBADF)_exit(125);
            AT_POINT(AP_CHILD_STAGE,0,0);
            path=AP_DISPATCHER;argument="S";
        } else
#endif
        {
        int probe=traced ? AT_SYS(AT_RCS_CHILD_FD_PROBE,fcntl(3,F_GETFD)) : fcntl(3,F_GETFD);
        if(probe!=-1 || errno!=EBADF)_exit(125);
        }
#if S22_DEBIAN_FAULT == 7
        if(phase==1)_exit(23);
#endif
#ifdef S22_AUTOBOOT_MINIMAL
        /* Never fall back to the full rcS when optional observation fails. */
        if(phase==1){path=AP_DISPATCHER;argument="S";}
#endif
#if S22_DEBIAN_FAULT == 11
        for(;;)pause();
#elif S22_DEBIAN_FAULT == 12
        path="/run/s22-debian/absent-executable";
#elif S22_DEBIAN_FAULT == 13
        signal(SIGTERM,SIG_DFL);kill(getpid(),SIGTERM);_exit(127);
#endif
        if(sw_now()>=sw.deadline_ms)_exit(124);
        char *args[]={(char *)path,(char *)argument,NULL};
        if(traced) {
            (void)AT_SYS_GUARD(AT_RCS_CHILD_EXEC,if(sw_now()>=sw.deadline_ms)_exit(124);,execv(path,args));
        } else execv(path,args);
        _exit(126);
    }
    ap_parent_fork();
    if(traced)AT_RETURN(AT_RCS_FORK,1,child,(unsigned)fork_errno);
    errno=fork_errno;if(child<0)dh_hook_fail(fs1_error());
    if(traced)AT_BEGIN(AT_RCS_FORK_RECORD,2);
    dh_boundary(phase,3,child,0,0);
    if(traced)AT_RETURN(AT_RCS_FORK_RECORD,2,0,0);
    int status;uint64_t heartbeat=sw_now();bool first_wait=true,first_sleep=true,first_heartbeat=true;
    for(;;) {
        aw_tick();
        ap_tick();
        pid_t got=traced && first_wait ? AT_SYS(AT_RCS_WAIT_FIRST,waitpid(child,&status,WNOHANG)) :
            waitpid(child,&status,WNOHANG);
        first_wait=false;
        if(got==child){ap_reaped();break;}
        if(got<0 && errno!=EINTR)dh_hook_fail(fs1_error());
        if(sw_now()>=sw.deadline_ms) {
            (void)kill(child,SIGKILL);dh_hook_fail(ETIMEDOUT);
        }
        if(sw_now()-heartbeat>=DH_SAMPLE_MS) {
            if(traced && first_heartbeat)AT_BEGIN(AT_RCS_HEARTBEAT,2);
            if((error=dh_actual_init(state)))dh_hook_fail(error);
            dh_boundary(phase,4,child,0,0);heartbeat=sw_now();
            if(traced && first_heartbeat)AT_RETURN(AT_RCS_HEARTBEAT,2,0,0);
            first_heartbeat=false;
        }
        struct timespec delay={0,10000000};
        int slept=traced && first_sleep ? AT_SYS(AT_RCS_SLEEP_FIRST,nanosleep(&delay,NULL)) : nanosleep(&delay,NULL);
        first_sleep=false;
        if(slept && errno!=EINTR)dh_hook_fail(fs1_error());
    }
#ifdef S22_AUTOBOOT_RCS_TRACE
    if(traced)at_emit(AT_RCS_CHILD_REAPED,4,3,0,0,(unsigned)child,(unsigned)status,1,0);
#endif
    dh_boundary(phase,5,child,(unsigned)status,0);
    if(!WIFEXITED(status) || WEXITSTATUS(status))dh_hook_fail(ECHILD);
}
/* A missing startup object may be reobserved by the cron lifecycle caller.
 * Identity/content/forbidden-FD mismatches retain their original hard errors. */
static int dh_service_absent(unsigned *retry,unsigned stage,int cause,int error) {
    if(retry && (cause==ENOENT || cause==ESRCH))*retry=stage;
    return error;
}
static int dh_service_probe(const char *pidfile,const char *executable,uint64_t size,const uint8_t sha[32],
                            pid_t *identity,unsigned *retry) {
    char text[64]={0},path[128],extra;struct stat file,actual,root;
    if(retry)*retry=0;
    int error=fs1_read_text(pidfile,text,sizeof(text));
    if(error) {
        if(retry && error==EPROTO && !text[0] && !lstat(pidfile,&actual) &&
            S_ISREG(actual.st_mode) && !actual.st_uid && !actual.st_size)*retry=1;
        return dh_service_absent(retry,1,error,error);
    }
    long pid=0;if(sscanf(text,"%ld %c",&pid,&extra)!=1 || pid<=1 || pid>INT_MAX)return EPROTO;
    if(*identity && *identity!=(pid_t)pid)return EPROTO;
    int fd=fs1_pin_file(executable,size,sha,true);if(fd<0)return fs1_error();
    error=fstat(fd,&file) || (uint64_t)file.st_dev!=sw.root_device ? EPROTO : 0;
    if(close(fd) && !error)error=fs1_error();
    if(error)return error;
    snprintf(path,sizeof(path),"/proc/%ld/exe",pid);
    if(stat(path,&actual))return dh_service_absent(retry,2,errno,EPROTO);
    if(file.st_dev!=actual.st_dev || file.st_ino!=actual.st_ino)return EPROTO;
    if(kill((pid_t)pid,0))return dh_service_absent(retry,2,errno,EPROTO);
    snprintf(path,sizeof(path),"/proc/%ld/root",pid);
    if(stat("/",&root))return EPROTO;
    if(stat(path,&actual))return dh_service_absent(retry,3,errno,EPROTO);
    if(root.st_dev!=actual.st_dev || root.st_ino!=actual.st_ino)return EPROTO;
    snprintf(path,sizeof(path),"/proc/%ld/fd",pid);DIR *fds=opendir(path);
    if(!fds){error=fs1_error();return dh_service_absent(retry,4,error,error);}
    unsigned count=0;
    for(;;) {
        errno=0;struct dirent *entry=readdir(fds);
        if(!entry){if(errno)error=errno;break;}
        if(entry->d_name[0]=='.')continue;
        if(++count>128){error=EPROTO;break;}
        if(fstatat(dirfd(fds),entry->d_name,&actual,0)) {
            error=dh_service_absent(retry,5,errno,EPROTO);break;
        }
#ifndef S22_DEBIAN_AUTOBOOT
        if(S_ISCHR(actual.st_mode) && (uint64_t)actual.st_rdev==sw.tty_device){error=EPROTO;break;}
#endif
        char link[256];ssize_t n=readlinkat(dirfd(fds),entry->d_name,link,sizeof(link)-1);
        if(n<0){error=dh_service_absent(retry,6,errno,EPROTO);break;}
        if(n>=(ssize_t)sizeof(link)-1){error=EPROTO;break;}link[n]=0;
        if(strstr(link,"s22-switch-state") ||
#ifdef S22_DEBIAN_AUTOBOOT
           strstr(link,"s22-autoboot-trace") ||
#endif
           !strcmp(link,DH_STATE_PATH)){error=EPROTO;break;}
    }
    if(closedir(fds) && !error)error=fs1_error();
    if(error)return error;
    *identity=(pid_t)pid;return 0;
}
static int dh_service(const char *pidfile,const char *executable,uint64_t size,const uint8_t sha[32],pid_t *identity) {
    return dh_service_probe(pidfile,executable,size,sha,identity,NULL);
}
#ifdef S22_DEBIAN_APT
#include "s22plus_debian_apt_clock_v1.inc.c"
#endif
#ifdef S22_DEBIAN_CRON
#include "s22plus_debian_cron_runtime_v1.inc.c"
#endif
#ifdef S22_DEBIAN_PACKAGE
#include "s22plus_debian_package_runtime_v1.inc.c"
#endif
static __attribute__((noreturn)) void dh_later(struct dh_state *state,const char *mode) {
    int error;
    if(!strcmp(mode,"rcs")) {
        dh_claim("rcs-started","init-started");
        if((error=
#ifdef S22_AUTOBOOT_RCS_TRACE
            AT_CHECK(AT_RCS_ACTUAL_INIT,dh_actual_init(state))
#else
            dh_actual_init(state)
#endif
            ) || (error=dh_reporting_open()))dh_hook_fail(error);
        dh_progress(0,1,0,0,0);
        dh_boundary(1,1,0,0,0);
        if((error=dh_reporting_close()))dh_hook_fail(error);
        uint64_t closed=de.off ? 0 : sw_now()-(sw.deadline_ms-SW_TIMEOUT_MS);
#if S22_DEBIAN_FAULT == 10
        dh_hook_fail(EIO);
#endif
        if((error=dh_actual_init(state)) || (error=dh_reporting_open()))dh_hook_fail(error);
        dh_boundary(1,2,0,0,de.off ? 0 : closed);
        dh_wait_script(state,1,"/etc/init.d/rcS",NULL);
        if((error=dh_actual_init(state)))dh_hook_fail(error);
        dh_claim("rcs-complete","rcs-started");dh_progress(1,2,0,0,0);
#ifdef S22_AUTOBOOT_RCS_TRACE
        AT_POINT(AT_RCS_COMPLETE,0,0);
#endif
        if((error=dh_reporting_close()))dh_hook_fail(error);
        ap_handover();
        _exit(0);
    }
    dh_claim("runlevel-started","rcs-complete");
    ap_resume();
    if((error=dh_actual_init(state)) || (error=dh_reporting_open()))dh_hook_fail(error);
    dh_boundary(2,2,0,0,0);
    dh_wait_script(state,2,"/etc/init.d/rc","2");
    if((error=dh_actual_init(state)))dh_hook_fail(error);
    dh_claim("runlevel-complete","runlevel-started");
#ifdef S22_DEBIAN_APT
    if((error=ap_clock_wait(state)))dh_hook_fail(error);
#endif
#ifdef S22_DEBIAN_CRON
    if((error=cr_lifecycle(state)))dh_hook_fail(error);
#endif
    pid_t cron=0,ssh=0;uint64_t started=sw_now();
#if S22_DEBIAN_FAULT == 8
    if((error=dh_service("/run/crond.pid","/usr/sbin/cron",dh_cron_size,dh_cron_sha256,&cron)) ||
       kill(cron,SIGKILL))dh_hook_fail(error ? error : fs1_error());
#endif
    if(started>=sw.deadline_ms || sw.deadline_ms-started<DH_SAMPLES*DH_SAMPLE_MS+10000U)dh_hook_fail(ETIMEDOUT);
    for(unsigned sample=0;sample<=DH_SAMPLES;++sample) {
        uint64_t target=started+(uint64_t)sample*DH_SAMPLE_MS;
        while(sw_now()<target) {
            aw_tick();
            ap_tick();
            struct timespec delay={0,100000000};
            if(nanosleep(&delay,NULL) && errno!=EINTR)dh_hook_fail(fs1_error());
        }
        uint8_t boot[32];
        if(sw_now()>=sw.deadline_ms || sw_boot(boot) || memcmp(boot,sw.boot,32) ||
           (error=dh_actual_init(state)) ||
           (error=dh_service("/run/crond.pid","/usr/sbin/cron",dh_cron_size,dh_cron_sha256,&cron)) ||
           (error=dh_service("/run/sshd.pid","/usr/sbin/sshd",dh_sshd_size,dh_sshd_sha256,&ssh)))
            dh_hook_fail(error ? error : EPROTO);
        dh_progress(2+sample,sample ? 4 : 3,sample,sw_now()-started,3);
    }
#ifdef S22_DEBIAN_CRON
    if((error=cr_complete(state)))dh_hook_fail(error);
#endif
#ifdef S22_DEBIAN_PACKAGE
    if((error=pk_complete(state)))dh_hook_fail(error);
#endif
    if((error=de_event(DE_COMPLETE,0,0,0,0,0)))dh_hook_fail(error);
#ifdef S22_DEBIAN_AUTOBOOT
    dh_claim("autoboot-complete","runlevel-complete");
    if((error=dh_reporting_close()))dh_hook_fail(error);
    _exit(0);
#else
    if(de.off) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
        dprintf(2,"DHVM_LOCAL_COMPLETE reporting=0\n");
#endif
        /* No RELEASE read, reopen, gadget operation or additional local work. */
        for(;;){struct timespec delay={1,0};(void)nanosleep(&delay,NULL);}
    }
    /* Recheck the fixed RAM executable after the ordinary service startup. */
#if S22_DEBIAN_FAULT == 9
    int changed=open("/run/s22-debian/usb",O_WRONLY|O_NOFOLLOW|O_CLOEXEC);
    if(changed<0 || write(changed,"!",1)!=1 || close(changed))dh_hook_fail(EIO);
#endif
    int usb=fs1_pin_file("/run/s22-debian/usb",dh_usb_size,dh_usb_sha256,true);
    struct statfs usb_fs;
    if(usb<0 || fstatfs(usb,&usb_fs) || usb_fs.f_type!=0x01021994L)dh_hook_fail(EPROTO);
    if(close(usb))dh_hook_fail(fs1_error());
    if((error=dh_auth_request(DH_RELEASE,DH_RELEASE_SEQUENCE)) ||
       (error=de_event(DE_RELEASE,0,0,DH_RELEASE_SEQUENCE,0,0)))dh_hook_fail(error);
    uint32_t accepted=1;uint64_t end=sw_now()+DE_REPORT_MS;if(end>sw.deadline_ms)end=sw.deadline_ms;
    /* RELEASE acknowledgement remains mandatory; loss cannot retire ACM. */
    if((error=sw_send_until(DH_RELEASE_ACK,DH_RELEASE_SEQUENCE,&accepted,sizeof(accepted),end)))dh_hook_fail(error);
    dh_claim("usb-release","runlevel-complete");
    if(close(3) || (error=dh_retire_acm()))dh_hook_fail(error ? error : EIO);
    /* One fixed RAM script adopts the same original gadget after unbind.
     * No extra command or reconnect is accepted after release. */
    char *args[]={"/bin/sh","/run/s22-debian/usb","start",NULL};
    execv(args[0],args);dh_hook_fail(fs1_error());
#endif
}
