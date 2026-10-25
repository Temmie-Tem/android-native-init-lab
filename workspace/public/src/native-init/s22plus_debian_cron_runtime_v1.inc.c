/* Fixed packaged-cron lifecycle and one asynchronous report. The asynchronous
 * worker never writes the sequential Debian evidence chain. */
#include "s22plus_debian_cron_v1.h"
#define CR_READY "/run/s22-debian/cron-ready"
#define CR_INTENT "/run/s22-debian/cron-intent"
#define CR_DONE "/run/s22-debian/cron-done"
#ifdef S22_DEBIAN_CRON_CONFIG
/* All virtual helpers contain the same fault-capable binary. A selected H0
 * kernel argument chooses the substitution, so a real first-boot snapshot
 * remains source-bound when exercising a later boot's failure paths. */
static bool cf_fault(unsigned wanted) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    char text[4096],expected[40];
    if(fs1_read_text("/proc/cmdline",text,sizeof(text)))return false;
    snprintf(expected,sizeof(expected),"s22cf_fault=%u",wanted);
    size_t n=strlen(expected);char *at=strstr(text,expected);
    return at && (at==text || at[-1]==' ') && (at[n]==' ' || at[n]=='\n' || !at[n]);
#else
    (void)wanted;return false;
#endif
}
#endif
#if defined(CR_VM_FAULT) && !defined(S22_ROOT_INSPECT_VIRT_TEST)
#error "cron fault injection is H0 only"
#endif
static bool cr_abort_allowed;
static int cr_ram_read(const char *path,uint8_t data[CR_SIZE]);
static int cr_revoke(const char *path,bool schedule) {
    int fd=open(path,O_WRONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return errno==ENOENT && !schedule ? 0 : fs1_error();
    struct stat st,target;struct statfs fs;
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
        st.st_mode!=(S_IFREG|0400) || st.st_uid || st.st_gid || st.st_nlink!=1 ? EPROTO : 0;
    if(!error && schedule && (stat("/etc/crontab",&target) || target.st_dev!=st.st_dev || target.st_ino!=st.st_ino))error=EPROTO;
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 4
    if(schedule)error=EIO;
#endif
    if(!error && ftruncate(fd,0))error=EIO;
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 9
    /* Reproduce truncate within cron's cached active whole second. */
    struct timespec cached[2]={{.tv_nsec=UTIME_OMIT},st.st_mtim};
    if(!error && schedule && futimens(fd,cached))error=EIO;
#endif
    /* Debian cron treats zero mtime as an absent system crontab. This also
     * invalidates its cached active schedule after a same-second failure. */
    struct timespec revoked[2]={{.tv_nsec=UTIME_OMIT},{0,0}};
    if(!error && schedule && futimens(fd,revoked))error=EIO;
    if(!error && (fsync(fd) || fstat(fd,&st) || st.st_size ||
        (schedule && (st.st_mtim.tv_sec || st.st_mtim.tv_nsec))))error=EIO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int cr_revoke_once(bool fresh) {
    if(!cr_abort_allowed)return fresh ? EALREADY : 0;
    cr_abort_allowed=false;
    /* A separate once-only RAM revocation remains allowed on expiry. It is
     * not a retry of the job, schedule arming, retirement or disk write. */
    int parent=open("/run/s22-debian",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;struct statfs fs;int claim_error=parent<0 ? fs1_error() : 0;
    if(!claim_error && (fstat(parent,&st) || fstatfs(parent,&fs) || fs.f_type!=0x01021994L ||
        st.st_uid || st.st_gid || st.st_mode!=(S_IFDIR|0700) || st.st_nlink<2))claim_error=EPROTO;
    int claim=-1;
#ifdef S22_DEBIAN_CRON_CONFIG
    if(!claim_error && cf_fault(12))claim_error=EIO;
#endif
    if(!claim_error) {
        mode_t mask=umask(0);claim=openat(parent,"cron-revocation",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
        if(claim<0)claim_error=fs1_error();
        umask(mask);
    }
    if(parent>=0 && close(parent) && !claim_error)claim_error=fs1_error();
    if(claim_error) {
        if(claim>=0)(void)close(claim);
        uint8_t old[CR_SIZE];int ready=-1,schedule=-1;
        if(claim_error==EEXIST && !cr_ram_read("/run/s22-debian/cron-revocation",old) && !memcmp(old,"S22CRRV1",8)) {
            ready=(int)fs1_u32(old+8);schedule=(int)fs1_u32(old+12);
        }
        dprintf(2,"CRON_RAM_REVOKE claim_errno=%d ready_errno=%d schedule_errno=%d\n",claim_error,ready,schedule);
        return claim_error;
    }
    int ready=cr_revoke(CR_READY,false);
#ifdef S22_DEBIAN_CRON_CONFIG
    int schedule=0; /* Only the RAM admission gate is revoked on this path. */
#else
    int schedule=cr_revoke("/run/s22-debian/crontab",true);
#endif
    uint8_t outcome[CR_SIZE]={0};memcpy(outcome,"S22CRRV1",8);sw_put32(outcome+8,(unsigned)ready);sw_put32(outcome+12,(unsigned)schedule);
    int recorded=write(claim,outcome,sizeof(outcome))==sizeof(outcome) && !fsync(claim) ? 0 : EIO;
    if(close(claim) && !recorded)recorded=fs1_error();
#ifdef S22_DEBIAN_CRON_CONFIG
    if(!recorded && cf_fault(3))recorded=EIO;
#endif
    if(recorded)claim_error=recorded;
    dprintf(2,"CRON_RAM_REVOKE claim_errno=%d ready_errno=%d schedule_errno=%d\n",claim_error,ready,schedule);
    return claim_error ? claim_error : ready ? ready : schedule;
}
static void cr_abort(void) {(void)cr_revoke_once(false);}

static int cr_ram_read(const char *path,uint8_t data[CR_SIZE]) {
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;uint8_t extra;
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
        st.st_mode!=(S_IFREG|0400) || st.st_uid || st.st_gid || st.st_nlink!=1 || st.st_size!=CR_SIZE ||
        read(fd,data,CR_SIZE)!=CR_SIZE || read(fd,&extra,1) ? EPROTO : 0;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int cr_ram_create(const char *path,const uint8_t data[CR_SIZE]) {
    if(de_time())return ETIMEDOUT;
    mode_t mask=umask(0);int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    int error=fd<0 ? fs1_error() : 0;umask(mask);struct statfs fs;
    if(!error && (fstatfs(fd,&fs) || fs.f_type!=0x01021994L || write(fd,data,CR_SIZE)!=CR_SIZE || fsync(fd)))error=EIO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
#ifdef S22_DEBIAN_CRON_CONFIG
    if(!error && !strcmp(path,CR_DONE) && (cf_fault(2) || cf_fault(12)))error=EIO;
#endif
    return error;
}
#ifndef S22_DEBIAN_CRON_CONFIG
static int cr_schedule_change(bool arm) {
    const char *before=arm ? cr_idle : cr_schedule,*after=arm ? cr_schedule : cr_idle;
    size_t old_size=strlen(before),size=strlen(after);uint8_t bytes[256];struct stat st,target,back;struct statfs fs;
    int fd=open("/run/s22-debian/crontab",O_RDWR|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return fs1_error();
    int error=de_time();
    if(!error && (fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
        st.st_mode!=(S_IFREG|0400) || st.st_uid || st.st_gid || st.st_nlink!=1 ||
        st.st_size!=(off_t)old_size || stat("/etc/crontab",&target) || st.st_dev!=target.st_dev || st.st_ino!=target.st_ino ||
        pread(fd,bytes,old_size,0)!=(ssize_t)old_size || memcmp(bytes,before,old_size)))error=EPROTO;
    if(!error && (de_time() || pwrite(fd,after,size,0)!=(ssize_t)size || ftruncate(fd,(off_t)size)))error=EIO;
    /* Debian cron compares whole seconds. Make both transitions observable
     * without changing the wall clock or replacing the mounted inode. */
    struct timespec times[2]={{.tv_nsec=UTIME_OMIT},{0,0}};
    if(!error) {
        if(st.st_mtim.tv_sec<0 || st.st_mtim.tv_sec>=INT64_MAX-1)error=EPROTO;
        else {times[1].tv_sec=st.st_mtim.tv_sec+1;
    if(futimens(fd,times) || fsync(fd))error=fs1_error();}
    }
    if(!error && (fstat(fd,&back) || back.st_dev!=st.st_dev || back.st_ino!=st.st_ino ||
        back.st_mode!=st.st_mode || back.st_nlink!=1 || back.st_size!=(off_t)size ||
        back.st_mtim.tv_sec!=times[1].tv_sec || pread(fd,bytes,size,0)!=(ssize_t)size || memcmp(bytes,after,size)))error=EIO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
#endif
static int cr_process(pid_t pid,pid_t *parent,uint64_t *ticks) {
    char path[64],text[4096];snprintf(path,sizeof(path),"/proc/%ld/stat",(long)pid);
    int error=fs1_read_text(path,text,sizeof(text));
    if(error)return error;
    char *last=strrchr(text,')');
    if(!last || last[1]!=' ')return EPROTO;
    char *save=NULL,*token=strtok_r(last+2," ",&save);*parent=0;*ticks=0;
    for(unsigned field=3;field<=22;++field,token=strtok_r(NULL," ",&save)) {
        if(!token)return EPROTO;
        if(field==4 || field==22) {
            char *end;errno=0;unsigned long long number=strtoull(token,&end,10);
            if(errno || *end || !number || (field==4 && number>INT_MAX))return EPROTO;
            if(field==4)*parent=(pid_t)number;else *ticks=(uint64_t)number;
        }
    }
    return 0;
}
static int cr_gone(pid_t pid,uint64_t ticks,bool *gone) {
    pid_t parent;uint64_t current;int error=cr_process(pid,&parent,&current);
    if(error==ENOENT){*gone=true;
    return 0;}if(error)return error;
    *gone=current!=ticks;
    return 0;
}
static int cr_wait_gone(pid_t pid,uint64_t ticks,uint64_t deadline) {
    for(;;) {
        if(sw_now()>=deadline || de_time())return ETIMEDOUT;
        bool gone=false;int error=cr_gone(pid,ticks,&gone);
        if(error)return error;
        if(gone)return sw_now()>=deadline || de_time() ? ETIMEDOUT : 0;
        struct timespec delay={0,10000000};
    if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
    }
}
static int cr_service_command(const char *command,uint64_t *settle_deadline) {
    uint64_t deadline=sw_now()+10000;
    if(deadline>sw.deadline_ms)deadline=sw.deadline_ms;
    *settle_deadline=deadline;
    if(de_time())return ETIMEDOUT;
    pid_t child=fork();
    if(child<0)return fs1_error();
    if(!child) {
        if(syscall(SYS_close_range,3U,UINT_MAX,0U))_exit(125);
        char *args[]={"/usr/sbin/service","cron",(char *)command,NULL};
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 5
        deadline=sw_now();
#endif
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 7
        args[0]="/bin/true";
#endif
        if(sw_now()>=deadline || de_time())_exit(124);
        execv(args[0],args);_exit(126);
    }
    for(;;) {
        int status;pid_t got=waitpid(child,&status,WNOHANG);
        if(got==child)return WIFEXITED(status) && !WEXITSTATUS(status) ? 0 : ECHILD;
        if(got<0 && errno!=EINTR)return fs1_error();
        if(sw_now()>=deadline){(void)kill(child,SIGKILL);
    return ETIMEDOUT;}
        struct timespec delay={0,10000000};
    if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
    }
}
static int cr_daemon(pid_t *pid,uint64_t *ticks) {
    int error=dh_service("/run/crond.pid","/usr/sbin/cron",dh_cron_size,dh_cron_sha256,pid);
    pid_t parent=0;
    if(!error)error=cr_process(*pid,&parent,ticks);
    return error;
}
static int cr_wait_daemon(pid_t *pid,uint64_t *ticks,uint64_t deadline,unsigned phase) {
    unsigned samples=0,last_retry=0;int last_error=0;
    for(;;) {
        if(de_time() || sw_now()>=deadline) {
            dprintf(2,"CRON_READY_TIMEOUT phase=%u samples=%u reason=%u errno=%d\n",phase,samples,last_retry,last_error);
            return ETIMEDOUT;
        }
        pid_t observed=0,parent=0;uint64_t observed_ticks=0;unsigned retry=0;
        const char *pidfile="/run/crond.pid";const uint8_t *expected_hash=dh_cron_sha256;
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 10
        if(phase==2 && samples<3)pidfile="/run/s22-debian/cron-vm-absent-pid";
#elif defined(CR_VM_FAULT) && CR_VM_FAULT == 11
        if(phase==2)pidfile="/run/s22-debian/cron-vm-absent-pid";
#elif defined(CR_VM_FAULT) && CR_VM_FAULT == 12
        uint8_t changed_hash[32];memcpy(changed_hash,dh_cron_sha256,32);changed_hash[0]^=1;
        if(phase==2)expected_hash=changed_hash;
#endif
        int error=dh_service_probe(pidfile,"/usr/sbin/cron",dh_cron_size,expected_hash,&observed,&retry);
        if(!error) {
            error=cr_process(observed,&parent,&observed_ticks);
            if(error==ENOENT || error==ESRCH)retry=7;
        }
        ++samples;
        if(de_time() || sw_now()>=deadline) {
            dprintf(2,"CRON_READY_TIMEOUT phase=%u samples=%u reason=%u errno=%d\n",phase,samples,retry,error);
            return ETIMEDOUT;
        }
        if(!error) {
            *pid=observed;*ticks=observed_ticks;
            if(samples>1)dprintf(2,"CRON_READY_ACCEPTED phase=%u samples=%u\n",phase,samples);
            return 0;
        }
        if(!retry) {
            dprintf(2,"CRON_READY_REJECTED phase=%u samples=%u errno=%d\n",phase,samples,error);
            return error;
        }
        if(samples==1)dprintf(2,"CRON_READY_PENDING phase=%u reason=%u errno=%d\n",phase,retry,error);
        last_retry=retry;last_error=error;
        struct timespec delay={0,10000000};
        if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
    }
}
static int cr_job(struct dh_state *state);
#ifdef S22_DEBIAN_CRON_CONFIG
static int cf_job_binding(const uint8_t data[CR_SIZE]);
static int cf_publish_success(void);
#else
static int cr_lifecycle(struct dh_state *state) {
    if(rb_phase!=1)return 0;
    cr_abort_allowed=true;
    if(de_time() || sw.deadline_ms-sw_now()<175000)return ETIMEDOUT;
    uint8_t data[CR_SIZE]={0};pid_t initial=0,started=0,restarted=0;uint64_t first_ticks,start_ticks,restart_ticks;
    uint64_t deadline=sw_now()+5000;
    if(deadline>sw.deadline_ms)deadline=sw.deadline_ms;
    int error=cr_wait_daemon(&initial,&first_ticks,deadline,1);
    if(error)return error;
    if((error=cr_service_command("stop",&deadline)) || (error=cr_wait_gone(initial,first_ticks,deadline)))return error;
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 3
    return EIO;
#endif
    cr_put64(data+CR_STOP_MS,sw_now());
    if((error=cr_service_command("start",&deadline)) || (error=cr_wait_daemon(&started,&start_ticks,deadline,2)) || started==initial)return error ? error : EPROTO;
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 10
    return EIO;
#endif
    cr_put64(data+CR_START_MS,sw_now());
    if((error=cr_service_command("restart",&deadline)) || (error=cr_wait_gone(started,start_ticks,deadline)) ||
       (error=cr_wait_daemon(&restarted,&restart_ticks,deadline,3)) || restarted==initial || restarted==started)return error ? error : EPROTO;
    cr_put64(data+CR_RESTART_MS,sw_now());
    memcpy(data,"S22CR01\0",8);sw_put32(data+8,1);sw_put32(data+12,CR_SIZE);
    memcpy(data+16,sw.run,16);memcpy(data+32,sw.boot,32);memcpy(data+64,sw.nonce,32);
    cr_put64(data+CR_ROOT_DEVICE,sw.root_device);sw_put32(data+CR_PHASE,1);sw_put32(data+CR_BASELINE,RB_BASE_COUNT);
    sw_put32(data+CR_INSTALLED_COUNT,RB_BASE_COUNT+2);cr_put64(data+CR_ARMED_MS,sw_now());
    cr_put64(data+CR_INITIAL_PID,(uint64_t)initial);cr_put64(data+CR_STARTED_PID,(uint64_t)started);
    cr_put64(data+CR_RESTARTED_PID,(uint64_t)restarted);cr_put64(data+CR_INITIAL_TICKS,first_ticks);
    cr_put64(data+CR_STARTED_TICKS,start_ticks);cr_put64(data+CR_RESTARTED_TICKS,restart_ticks);
    memcpy(data+192,cr_cron_sha,32);memcpy(data+224,cr_sshd_sha,32);memcpy(data+256,state->hook_sha,32);
    cr_put64(data+CR_CRON_SIZE,CR_CRON_BYTES);cr_put64(data+CR_SSHD_SIZE,CR_SSHD_BYTES);
    cr_tag(data+480,2,data,480);
    if((error=cr_ram_create(CR_READY,data)))return error;
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 8
    error=cr_job(state);struct stat probe;
    if(error!=EPROTO || !lstat(CR_INTENT,&probe) || errno!=ENOENT)return EINVAL;
    dprintf(2,"CRON_MANUAL_REJECTED no_intent=1\n");
    return ECANCELED;
#endif
    error=cr_schedule_change(true);
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 6
    if(!error)sw.deadline_ms=sw_now();
#endif
    return error;
}
#endif
static int cr_ancestors(uint8_t intent[CR_SIZE]) {
    pid_t pid=getpid(),master=(pid_t)cr_u64(intent+CR_RESTARTED_PID);unsigned count=0;
    struct stat root,expected_cron,expected_shell;
    if(stat("/",&root) || stat("/usr/sbin/cron",&expected_cron) || stat("/bin/sh",&expected_shell))return fs1_error();
    for(;;) {
        pid_t parent=0;uint64_t ticks=0;int error=cr_process(pid,&parent,&ticks);
    if(error)return error;
        if(pid==master)return ticks==cr_u64(intent+CR_RESTARTED_TICKS) && count>0 ?
            (sw_put32(intent+CR_ANCESTOR_COUNT,count),0) : EPROTO;
        if(pid<=1 || count>=6)return EPROTO;
        char path[80];struct stat st;
        snprintf(path,sizeof(path),"/proc/%ld/root",(long)pid);
        if(stat(path,&st) || st.st_dev!=root.st_dev || st.st_ino!=root.st_ino)return EPROTO;
        if(count) {
            snprintf(path,sizeof(path),"/proc/%ld/exe",(long)pid);
            if(stat(path,&st) || !((st.st_dev==expected_cron.st_dev && st.st_ino==expected_cron.st_ino) ||
                (st.st_dev==expected_shell.st_dev && st.st_ino==expected_shell.st_ino)))return EPROTO;
        }
        cr_put64(intent+352+count*16,(uint64_t)pid);cr_put64(intent+360+count*16,ticks);
        count++;pid=parent;
    }
}
static int cr_early_prefix(uint8_t early[256]) {
    int fd=open("/run/s22-debian/early",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return fs1_error();
    int error=pread(fd,early,256,0)==256 ? 0 : EIO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int cr_job(struct dh_state *state) {
    /* Already queued invocations may exist after schedule retirement. They
     * cannot retry the schedule change, output creation or an uncertain write. */
    struct stat st;
#ifdef S22_DEBIAN_CRON_CONFIG
    /* Boot 1 may dispatch the installed line, but cannot claim an intent or
     * write a report. RAM readiness exists only on the admitted second boot. */
    if(rb_phase!=2)return 0;
    if(cf_fault(4))return 0;
#endif
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 9
    int count_fd=open("/run/s22-debian/cron-vm-invocations",O_WRONLY|O_CREAT|O_APPEND|O_NOFOLLOW|O_CLOEXEC,0600);
    if(count_fd<0)return fs1_error();
    int count_error=fstat(count_fd,&st) || !S_ISREG(st.st_mode) || st.st_size>=4 || write(count_fd,"X",1)!=1 ? EIO : 0;
    if(close(count_fd) && !count_error)count_error=fs1_error();
    if(count_error)return count_error;
#endif
    if(!lstat(CR_INTENT,&st))return 0;
    if(errno!=ENOENT)return fs1_error();
#if defined(CR_VM_FAULT) && (CR_VM_FAULT == 1 || CR_VM_FAULT == 4)
    return 0;
#endif
    uint8_t data[CR_SIZE],intent[CR_SIZE],tag[32],early[256];int error=cr_ram_read(CR_READY,data);
    if(error==ENOENT)return 0;
    if(error)return error;
    cr_tag(tag,2,data,480);
    if(rb_phase!=
#ifdef S22_DEBIAN_CRON_CONFIG
       2
#else
       1
#endif
       || memcmp(tag,data+480,32) || memcmp(data+16,sw.run,16) ||
       memcmp(data+32,sw.boot,32) || memcmp(data+64,sw.nonce,32) || memcmp(data+256,state->hook_sha,32))return EPROTO;
    pid_t daemon=(pid_t)cr_u64(data+CR_RESTARTED_PID);uint64_t ticks;
    if((error=cr_daemon(&daemon,&ticks)) || ticks!=cr_u64(data+CR_RESTARTED_TICKS))return error ? error : EPROTO;
#ifdef S22_DEBIAN_CRON_CONFIG
    if((uint64_t)daemon!=cr_u64(data+CR_DAEMON_PID))return EPROTO;
    if((error=cf_job_binding(data)))return error;
#endif
    cr_put64(data+CR_JOB_MS,sw_now());cr_put64(data+CR_JOB_PID,(uint64_t)getpid());cr_put64(data+CR_PARENT_PID,(uint64_t)getppid());
    memcpy(intent,data,sizeof(intent));
    if((error=cr_ancestors(intent)))return error;
    memcpy(data+CR_ANCESTOR_COUNT,intent+CR_ANCESTOR_COUNT,4);cr_tag(intent+480,3,intent,480);
    if((error=cr_ram_create(CR_INTENT,intent)))return error==EEXIST ? 0 : error;
    cr_abort_allowed=true;
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 9
    return EIO; /* The real scheduled job loaded the active cron cache. */
#endif
#ifndef S22_DEBIAN_CRON_CONFIG
    if((error=cr_schedule_change(false)))return error;
#endif
    /* The actual scheduled task hashes the two retained installed programs. */
    const char *names[]={"/usr/sbin/cron","/usr/sbin/sshd"};
    const uint8_t *hashes[]={cr_cron_sha,cr_sshd_sha};const uint64_t sizes[]={CR_CRON_BYTES,CR_SSHD_BYTES};
    for(unsigned i=0;i<2;++i) {
        int fd=fs1_pin_file(names[i],sizes[i],hashes[i],true);
    if(fd<0)return fs1_error();
        if(close(fd))return fs1_error();
    if(de_time())return ETIMEDOUT;
    }
    cr_put64(data+CR_HASH_COMPLETED_MS,sw_now());cr_tag(data+480,1,data,480);
    if((error=cr_early_prefix(early)) || (error=cr_valid(data,early,(dev_t)sw.root_device,state->hook_sha)))return error;
    int root=open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(root<0)return fs1_error();
    int parent=cr_parent(root,(dev_t)sw.root_device);error=parent<0 ? fs1_error() : 0;
    if(close(root) && !error)error=fs1_error();
    if(error){if(parent>=0)(void)close(parent);
    return error;}
    if(de_time()){(void)close(parent);
    return ETIMEDOUT;}
    mode_t mask=umask(0);int fd=openat(parent,strrchr(cr_path,'/')+1,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    error=fd<0 ? fs1_error() : 0;umask(mask);
    size_t amount=CR_SIZE;
#ifdef S22_DEBIAN_CRON_CONFIG
    if(cf_fault(11))amount=CR_SIZE/2;
#endif
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 2
    amount=CR_SIZE/2;
#endif
    if(!error && (de_time() || write(fd,data,amount)!=(ssize_t)amount || fsync(fd) || fsync(parent)))error=EIO;
    if(!error && amount!=CR_SIZE)error=EIO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(close(parent) && !error)error=fs1_error();
    if(error)return error;
    error=cr_ram_create(CR_DONE,data);
#ifdef S22_DEBIAN_CRON_CONFIG
    if(!error)error=cf_publish_success();
#endif
    return error;
}
static int cr_report_complete(struct dh_state *state) {
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 9
    uint8_t claimed[CR_SIZE],claimed_tag[32];
    int cached_error=cr_ram_read(CR_INTENT,claimed);
    if(cached_error)return cached_error;
    cr_tag(claimed_tag,3,claimed,480);
    if(memcmp(claimed_tag,claimed+480,32))return EPROTO;
    uint64_t job_ms=cr_u64(claimed+CR_JOB_MS);
    while(sw_now()<job_ms+65000) {
        if(de_time())return ETIMEDOUT;
        struct timespec delay={0,10000000};
        if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
    }
    pid_t master=0;uint64_t ticks=0;struct stat entries,schedule,output;
    if((cached_error=cr_daemon(&master,&ticks)))return cached_error;
    if((uint64_t)master!=cr_u64(claimed+CR_RESTARTED_PID) || ticks!=cr_u64(claimed+CR_RESTARTED_TICKS) ||
       lstat("/run/s22-debian/cron-vm-invocations",&entries) || entries.st_size!=1 ||
       stat("/etc/crontab",&schedule) || schedule.st_size || schedule.st_mtim.tv_sec || schedule.st_mtim.tv_nsec ||
       !lstat(cr_path,&output) || errno!=ENOENT)return EINVAL;
    dprintf(2,"CRON_CACHE_REVOKED elapsed_ms=%llu invocations=1 schedule_size=0 schedule_mtime=0 output_absent=1\n",
        (unsigned long long)(sw_now()-job_ms));
#endif
#if defined(CR_VM_FAULT) && CR_VM_FAULT == 2
    /* Exercise the real consumed-intent branch after a synchronized partial
     * output. This diagnostic exists only in the declared ARM64 VM fault. */
    int probe_root=open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(probe_root<0)return fs1_error();
    int probe_parent=cr_parent(probe_root,(dev_t)sw.root_device);(void)close(probe_root);
    if(probe_parent<0)return fs1_error();
    int probe_fd=openat(probe_parent,strrchr(cr_path,'/')+1,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);(void)close(probe_parent);
    if(probe_fd<0)return fs1_error();
    struct stat probe_before,probe_after;uint8_t before[CR_SIZE/2],after[CR_SIZE/2];
    int probe_error=fstat(probe_fd,&probe_before) || probe_before.st_size!=CR_SIZE/2 ||
        pread(probe_fd,before,sizeof(before),0)!=sizeof(before) || cr_job(state) ||
        fstat(probe_fd,&probe_after) || probe_after.st_size!=probe_before.st_size ||
        probe_after.st_ino!=probe_before.st_ino || probe_after.st_mtim.tv_sec!=probe_before.st_mtim.tv_sec ||
        probe_after.st_mtim.tv_nsec!=probe_before.st_mtim.tv_nsec ||
        pread(probe_fd,after,sizeof(after),0)!=sizeof(after) || memcmp(before,after,sizeof(before));
    if(close(probe_fd))probe_error=1;
    if(probe_error)return EINVAL;
    dprintf(2,"CRON_REPEAT_NO_WRITE partial_bytes=256\n");
#endif
    uint8_t disk[CR_SIZE],done[CR_SIZE],intent[CR_SIZE],tag[32],early[256];
    int error=cr_ram_read(CR_DONE,done);
    if(error)return error;
    if((error=cr_ram_read(CR_INTENT,intent)))return error;
    cr_tag(tag,3,intent,480);
    if(memcmp(tag,intent+480,32))return EPROTO;
    unsigned count=fs1_u32(intent+CR_ANCESTOR_COUNT);
    if(count<1 || count>6)return EPROTO;
    uint64_t deadline=sw_now()+10000;
    if(deadline>sw.deadline_ms)deadline=sw.deadline_ms;
    for(unsigned i=0;i<count;++i)
        if((error=cr_wait_gone((pid_t)cr_u64(intent+352+i*16),cr_u64(intent+360+i*16),deadline)))return error;
    int root=open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(root<0)return fs1_error();
    error=cr_read(root,(dev_t)sw.root_device,disk,false);
    if(close(root) && !error)error=fs1_error();
    if(!error)error=cr_early_prefix(early);
    if(!error)error=cr_valid(disk,early,(dev_t)sw.root_device,state->hook_sha);
    if(!error && memcmp(done,disk,CR_SIZE))error=EPROTO;
    return error;
}
#ifdef S22_DEBIAN_CRON_CONFIG
#include "s22plus_debian_cron_config_runtime_v1.inc.c"
#else
static int cr_complete(struct dh_state *state) {
    return rb_phase==1 ? cr_report_complete(state) : 0;
}
#endif
