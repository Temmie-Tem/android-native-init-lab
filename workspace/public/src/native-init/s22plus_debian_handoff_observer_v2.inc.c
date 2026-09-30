/* Fixed, sequential children of installed SysVinit. No daemon, respawn,
 * shell console or native service manager survives this observation. */
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
    int error=sw_send(DH_PROGRESS,2000+ordinal,body,sizeof(body));if(error)dh_hook_fail(error);
}
static void dh_wait_script(const char *path,const char *argument) {
    /* There is no open ACM or state descriptor at fork/exec. The script may
     * start services; none can inherit our diagnostic channel. */
    if(fcntl(3,F_GETFD)!=-1 || errno!=EBADF)dh_hook_fail(EPROTO);
    pid_t child=fork();if(child<0)dh_hook_fail(fs1_error());
    if(!child) {
        if(syscall(SYS_close_range,3U,UINT_MAX,0U))_exit(125);
#if S22_DEBIAN_FAULT == 7
        if(!strcmp(path,"/etc/init.d/rcS"))_exit(23);
#endif
        char *args[]={(char *)path,(char *)argument,NULL};execv(path,args);_exit(126);
    }
    int status;
    for(;;) {
        pid_t got=waitpid(child,&status,WNOHANG);
        if(got==child)break;
        if(got<0 && errno!=EINTR)dh_hook_fail(fs1_error());
        if(sw_now()>=sw.deadline_ms) {
            (void)kill(child,SIGKILL);dh_hook_fail(ETIMEDOUT);
        }
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL) && errno!=EINTR)dh_hook_fail(fs1_error());
    }
    if(!WIFEXITED(status) || WEXITSTATUS(status))dh_hook_fail(ECHILD);
}
static int dh_service(const char *pidfile,const char *executable,uint64_t size,const uint8_t sha[32],pid_t *identity) {
    char text[64],path[128],extra;struct stat file,actual,root;
    int error=fs1_read_text(pidfile,text,sizeof(text));if(error)return error;
    long pid=0;if(sscanf(text,"%ld %c",&pid,&extra)!=1 || pid<=1 || pid>INT_MAX)return EPROTO;
    if(*identity && *identity!=(pid_t)pid)return EPROTO;
    int fd=fs1_pin_file(executable,size,sha,true);if(fd<0)return fs1_error();
    error=fstat(fd,&file) || (uint64_t)file.st_dev!=sw.root_device ? EPROTO : 0;
    if(close(fd) && !error)error=fs1_error();
    if(error)return error;
    snprintf(path,sizeof(path),"/proc/%ld/exe",pid);
    if(stat(path,&actual) || file.st_dev!=actual.st_dev || file.st_ino!=actual.st_ino || kill((pid_t)pid,0))return EPROTO;
    snprintf(path,sizeof(path),"/proc/%ld/root",pid);
    if(stat("/",&root) || stat(path,&actual) || root.st_dev!=actual.st_dev || root.st_ino!=actual.st_ino)return EPROTO;
    snprintf(path,sizeof(path),"/proc/%ld/fd",pid);DIR *fds=opendir(path);if(!fds)return fs1_error();
    unsigned count=0;
    for(;;) {
        errno=0;struct dirent *entry=readdir(fds);
        if(!entry){if(errno)error=errno;break;}
        if(entry->d_name[0]=='.')continue;
        if(++count>128 || fstatat(dirfd(fds),entry->d_name,&actual,0) ||
           (S_ISCHR(actual.st_mode) && (uint64_t)actual.st_rdev==sw.tty_device)) {error=EPROTO;break;}
        char link[256];ssize_t n=readlinkat(dirfd(fds),entry->d_name,link,sizeof(link)-1);
        if(n<0 || n>=(ssize_t)sizeof(link)-1){error=EPROTO;break;}link[n]=0;
        if(strstr(link,"s22-switch-state") || !strcmp(link,DH_STATE_PATH)){error=EPROTO;break;}
    }
    if(closedir(fds) && !error)error=fs1_error();
    if(error)return error;
    *identity=(pid_t)pid;return 0;
}
static __attribute__((noreturn)) void dh_later(struct dh_state *state,const char *mode) {
    int error;
    if(!strcmp(mode,"rcs")) {
        dh_claim("rcs-started","init-started");
        if((error=dh_reopen()) || (error=dh_actual_init(state)))dh_hook_fail(error);
        dh_progress(0,1,0,0,0);
        if(close(3))dh_hook_fail(fs1_error());
        dh_wait_script("/etc/init.d/rcS",NULL);
        if((error=dh_reopen()) || (error=dh_actual_init(state)))dh_hook_fail(error);
        dh_claim("rcs-complete","rcs-started");dh_progress(1,2,0,0,0);
        if(close(3))dh_hook_fail(fs1_error());
        _exit(0);
    }
    dh_claim("runlevel-started","rcs-complete");
    dh_wait_script("/etc/init.d/rc","2");
    if((error=dh_reopen()) || (error=dh_actual_init(state)))dh_hook_fail(error);
    dh_claim("runlevel-complete","runlevel-started");
    pid_t cron=0,ssh=0;uint64_t started=sw_now();
#if S22_DEBIAN_FAULT == 8
    if((error=dh_service("/run/crond.pid","/usr/sbin/cron",dh_cron_size,dh_cron_sha256,&cron)) ||
       kill(cron,SIGKILL))dh_hook_fail(error ? error : fs1_error());
#endif
    if(started>=sw.deadline_ms || sw.deadline_ms-started<DH_SAMPLES*DH_SAMPLE_MS+10000U)dh_hook_fail(ETIMEDOUT);
    for(unsigned sample=0;sample<=DH_SAMPLES;++sample) {
        uint64_t target=started+(uint64_t)sample*DH_SAMPLE_MS;
        while(sw_now()<target) {
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
    /* Recheck the fixed RAM executable after the ordinary service startup. */
#if S22_DEBIAN_FAULT == 9
    int changed=open("/run/s22-debian/usb",O_WRONLY|O_NOFOLLOW|O_CLOEXEC);
    if(changed<0 || write(changed,"!",1)!=1 || close(changed))dh_hook_fail(EIO);
#endif
    int usb=fs1_pin_file("/run/s22-debian/usb",dh_usb_size,dh_usb_sha256,true);
    struct statfs usb_fs;
    if(usb<0 || fstatfs(usb,&usb_fs) || usb_fs.f_type!=0x01021994L)dh_hook_fail(EPROTO);
    if(close(usb))dh_hook_fail(fs1_error());
    dh_request(DH_RELEASE,DH_RELEASE_SEQUENCE,DH_RELEASE_ACK);
    dh_claim("usb-release","runlevel-complete");
    if(close(3) || (error=dh_retire_acm()))dh_hook_fail(error ? error : EIO);
    /* One fixed RAM script adopts the same original gadget after unbind.
     * No extra command or reconnect is accepted after release. */
    char *args[]={"/bin/sh","/run/s22-debian/usb","start",NULL};
    execv(args[0],args);dh_hook_fail(fs1_error());
}
