/* One disk configuration across two boots. Failure revokes RAM admission only. */
#define CF_SNAPSHOT "/run/s22-debian/cron-config"
#define CF_SUCCESS "/run/s22-debian/cron-success"
static int cf_mount_view(void) {
    struct sw_mount rows[SW_MAX_MOUNTS];unsigned count=0,root=0;
    int error=sw_mounts_parse(rows,&count,NULL,false);if(error)return error;
    char leaf[256];int n=snprintf(leaf,sizeof(leaf),"/%s",cf_path);
    if(n<=0 || n>=(int)sizeof(leaf))return EOVERFLOW;
    for(unsigned i=0;i<count;++i) {
        struct sw_mount *row=rows+i;
        if(!strcmp(row->point,"/")) {
            if(strcmp(row->root,"/") || strcmp(row->type,"ext4") ||
               makedev(row->major,row->minor)!=(dev_t)sw.root_device)return EPROTO;
            ++root;
        } else if(!strcmp(row->point,"/etc") || !strcmp(row->point,"/etc/cron.d") ||
                  !strcmp(row->point,leaf))return EPROTO;
    }
    return root==1 ? 0 : EPROTO;
}
static int cf_root(void) {
    int error=cf_mount_view();if(error){errno=error;return -1;}
    int fd=open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return -1;
    error=cr_directory(fd,(dev_t)sw.root_device);
    if(error){(void)close(fd);errno=error;return -1;}return fd;
}
static int cf_live(struct stat *st) {
    int root=cf_root();if(root<0)return fs1_error();
    int error=cf_read(root,(dev_t)sw.root_device,st,false);
    if(close(root) && !error)error=fs1_error();
    return error;
}
static int cf_snapshot(void) {
    int root=cf_root();if(root<0)return fs1_error();
    int parent=cf_parent(root,(dev_t)sw.root_device),error=parent<0 ? fs1_error() : 0;
    if(close(root) && !error)error=fs1_error();
    struct stat identity;uint8_t bytes[CF_CONFIG_SIZE];
    int fd=error ? -1 : cf_open(parent,(dev_t)sw.root_device,&identity);
    if(!error && fd<0)error=fs1_error();
    if(!error && pread(fd,bytes,sizeof(bytes),0)!=sizeof(bytes))error=EIO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(parent>=0 && close(parent) && !error)error=fs1_error();
    if(error || de_time())return error ? error : ETIMEDOUT;
    mode_t mask=umask(0);fd=open(CF_SNAPSHOT,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);umask(mask);
    error=fd<0 ? fs1_error() : 0;struct statfs fs;
    if(!error && (fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
       write(fd,bytes,sizeof(bytes))!=sizeof(bytes) || fsync(fd)))error=EIO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    return error;
}
static int cf_local_file(int parent,const char *name,uint8_t data[16384],size_t *size) {
    int fd=openat(parent,name,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat before,after;uint8_t extra;
    int error=fstat(fd,&before) || before.st_dev!=(dev_t)sw.root_device || before.st_mode!=(S_IFREG|0600) ||
        before.st_uid || before.st_gid || before.st_nlink!=1 || before.st_size<256 || before.st_size>16384 ? EPROTO : 0;
    if(!error && (read(fd,data,(size_t)before.st_size)!=before.st_size || read(fd,&extra,1) ||
        fstat(fd,&after) || !cf_same(&before,&after)))error=EIO;
    if(close(fd) && !error)error=fs1_error();
    if(!error)*size=(size_t)before.st_size;
    return error;
}
static int cf_prior(struct dh_state *state,struct de_chain *created,uint8_t boot[32],uint8_t nonce[32]) {
    int root=cf_root();if(root<0)return fs1_error();
    int parent=cr_parent(root,(dev_t)sw.root_device),error=parent<0 ? fs1_error() : 0;
    if(close(root) && !error)error=fs1_error();
    uint8_t early[16384],runtime[16384];size_t es=0,rs=0;
    if(!error)error=cf_local_file(parent,rb_leaf(1,0),early,&es);
    if(!error)error=cf_local_file(parent,rb_leaf(1,1),runtime,&rs);
    if(parent>=0 && close(parent) && !error)error=fs1_error();
    if(!error)error=rb_early(early,es,1);
    if(!error)error=cf_prior_chain(runtime,rs,early,(dev_t)sw.root_device,state->hook_sha,created);
    if(!error && !memcmp(early+48,sw.boot,32))error=EPROTO;
    if(!error){memcpy(boot,early+48,32);early_hash(early,256,nonce);}return error;
}
/* A vanished process causes a bounded new read; other proc errors reject the
 * census. Zombies and kernel threads cannot continue cron/PAM execution. */
static int cf_cron_census(bool *active) {
    if(rb_phase==2 && cf_fault(7))return EACCES;
    struct stat expected,root;if(stat("/usr/sbin/cron",&expected) || stat("/",&root))return fs1_error();
    DIR *dir=opendir("/proc");if(!dir)return fs1_error();
    unsigned count=0;int error=0;*active=false;
    for(;;) {
        errno=0;struct dirent *entry=readdir(dir);if(!entry){if(errno)error=errno;break;}
        if(entry->d_name[0]<'0' || entry->d_name[0]>'9')continue;
        char *end;long pid=strtol(entry->d_name,&end,10);
        if(*end || pid<=0 || pid>INT_MAX || ++count>8192){error=EPROTO;break;}
        char path[80],text[4096];snprintf(path,sizeof(path),"/proc/%ld/stat",pid);
        error=fs1_read_text(path,text,sizeof(text));if(error){if(error==ENOENT)error=ESTALE;break;}
        char *tail=strrchr(text,')'),state;long ppid,pgrp,session,tty,tpgid;unsigned long flags;
        if(!tail || sscanf(tail+1," %c %ld %ld %ld %ld %ld %lu",&state,&ppid,&pgrp,&session,&tty,&tpgid,&flags)!=7)
            {error=EPROTO;break;}
        if((flags&0x00200000UL) || state=='Z')continue;
        struct stat executable,task_root;snprintf(path,sizeof(path),"/proc/%ld/exe",pid);
        if(stat(path,&executable)){error=errno==ENOENT ? ESTALE : fs1_error();break;}
        if(executable.st_dev!=expected.st_dev || executable.st_ino!=expected.st_ino)continue;
        snprintf(path,sizeof(path),"/proc/%ld/root",pid);
        if(stat(path,&task_root)){error=errno==ENOENT ? ESTALE : fs1_error();break;}
        if(task_root.st_dev!=root.st_dev || task_root.st_ino!=root.st_ino){error=EPROTO;break;}
        *active=true;
    }
    if(closedir(dir) && !error)error=fs1_error();
    return error;
}
static int cf_settled(uint64_t deadline) {
    unsigned quiet=0;
    for(;;) {
        if(de_time() || sw_now()>=deadline)return ETIMEDOUT;
        bool active=false;int error=cf_cron_census(&active);
        if(error && error!=ESTALE)return error;
        quiet=!error && !active ? quiet+1 : 0;
        if(quiet==2)return de_time() || sw_now()>=deadline ? ETIMEDOUT : 0;
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
    }
}
static int cf_create(void) {
    int root=cf_root();if(root<0)return fs1_error();
    int parent=cf_parent(root,(dev_t)sw.root_device),error=parent<0 ? fs1_error() : 0;
    if(close(root) && !error)error=fs1_error();
    int fd=-1;if(!error)error=de_time();
    if(!error) {
        mode_t mask=umask(0);fd=openat(parent,strrchr(cf_path,'/')+1,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0644);
        error=fd<0 ? fs1_error() : 0;umask(mask);
    }
    size_t amount=cf_fault(1) ? 31 : CF_CONFIG_SIZE;
    if(!error && (de_time() || write(fd,cf_schedule,amount)!=(ssize_t)amount))error=EIO;
    if(!error && (de_time() || fsync(fd)))error=EIO;
    if(!error && (de_time() || fsync(parent)))error=EIO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(parent>=0 && close(parent) && !error)error=fs1_error();
    if(!error && amount!=CF_CONFIG_SIZE) {
        dprintf(2,"CF_CREATE_PARTIAL bytes=%zu\n",amount);error=EIO;
    }
    if(error)return error;
    struct stat st;if((error=cf_live(&st)))return error;
    if((error=de_event(CF_CREATED,1,1,(uint64_t)st.st_ino,(uint64_t)st.st_mtim.tv_sec,(uint64_t)st.st_mtim.tv_nsec)))return error;
    return de_event(CF_CREATED,1,2,(uint64_t)st.st_ctim.tv_sec,(uint64_t)st.st_ctim.tv_nsec,CF_CONFIG_SIZE);
}
static void cf_pack_identity(uint8_t data[CR_SIZE],const struct de_chain *created) {
    cr_put64(data+CR_CONFIG_INODE,created->config_inode);cr_put64(data+CR_CONFIG_SIZE,CF_CONFIG_SIZE);
    cr_put64(data+CR_CONFIG_CREATED_MS,created->config_created_ms);
    cr_put64(data+CR_CONFIG_MTIME_SEC,created->config_mtime_sec);cr_put64(data+CR_CONFIG_MTIME_NSEC,created->config_mtime_nsec);
    cr_put64(data+CR_CONFIG_CTIME_SEC,created->config_ctime_sec);cr_put64(data+CR_CONFIG_CTIME_NSEC,created->config_ctime_nsec);
    memcpy(data+352,cf_config_sha,32);
}
static int cf_job_binding(const uint8_t data[CR_SIZE]) {
    struct stat st;int error=cf_live(&st);if(error)return error;
    return cr_u64(data+CR_CONFIG_INODE)!=(uint64_t)st.st_ino || cr_u64(data+CR_CONFIG_SIZE)!=(uint64_t)st.st_size ||
        cr_u64(data+CR_CONFIG_MTIME_SEC)!=(uint64_t)st.st_mtim.tv_sec || cr_u64(data+CR_CONFIG_MTIME_NSEC)!=(uint64_t)st.st_mtim.tv_nsec ||
        cr_u64(data+CR_CONFIG_CTIME_SEC)!=(uint64_t)st.st_ctim.tv_sec || cr_u64(data+CR_CONFIG_CTIME_NSEC)!=(uint64_t)st.st_ctim.tv_nsec ||
        memcmp(data+352,cf_config_sha,32) ? EPROTO : 0;
}
static int cf_publish_success(void) {
    /* The completion file's write, fsync and close have already succeeded.
     * This final atomic RAM publication opens no descriptor needing close. */
    if(de_time())return ETIMEDOUT;
    struct stat st;struct statfs fs;
    if(lstat("/run/s22-debian",&st) || statfs("/run/s22-debian",&fs) || fs.f_type!=0x01021994L ||
       st.st_mode!=(S_IFDIR|0700) || st.st_uid || st.st_gid)return EPROTO;
    if(de_time())return ETIMEDOUT;
    mode_t mask=umask(0);int rc=mkdir(CF_SUCCESS,0700),saved=errno;umask(mask);
    return rc ? (saved ? saved : EIO) : 0;
}
static int cf_success(void) {
    struct stat st,parent;struct statfs fs;
    int fd=open(CF_SUCCESS,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    int error=fstat(fd,&st) || lstat("/run/s22-debian",&parent) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
        st.st_dev!=parent.st_dev || st.st_mode!=(S_IFDIR|0700) || st.st_uid || st.st_gid || st.st_nlink!=2 ? EPROTO : 0;
    DIR *dir=error ? NULL : fdopendir(fd);
    if(!error && !dir)error=fs1_error();
    if(dir) {
        for(;;) {
            errno=0;struct dirent *entry=readdir(dir);if(!entry){if(errno)error=errno;break;}
            if(strcmp(entry->d_name,".") && strcmp(entry->d_name,"..")){error=EPROTO;break;}
        }
        if(closedir(dir) && !error)error=fs1_error();
    } else if(close(fd) && !error)error=fs1_error();
    return error;
}
static int cr_lifecycle(struct dh_state *state) {
    cr_abort_allowed=true;
    if(de_time() || sw.deadline_ms-sw_now()<175000)return ETIMEDOUT;
    pid_t initial=0,started=0,restarted=0;uint64_t initial_ticks=0,start_ticks=0,restart_ticks=0,deadline=sw_now()+5000;
    int error=cr_wait_daemon(&initial,&initial_ticks,deadline,1);if(error)return error;
    if(rb_phase==1) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
        if(cf_fault(6) && mount("/etc/cron.d","/etc/cron.d",NULL,MS_BIND,NULL))return fs1_error();
#endif
        if((error=cr_service_command("stop",&deadline)) || (error=cr_wait_gone(initial,initial_ticks,deadline)) ||
           (error=cf_settled(deadline)) || (error=cf_create()))return error;
        if((error=cr_service_command("start",&deadline)) || (error=cr_wait_daemon(&started,&start_ticks,deadline,2)) ||
           started==initial)return error ? error : EPROTO;
        if((error=cr_service_command("restart",&deadline)) || (error=cr_wait_gone(started,start_ticks,deadline)) ||
           (error=cr_wait_daemon(&restarted,&restart_ticks,deadline,3)) || restarted==initial || restarted==started)
            return error ? error : EPROTO;
        return cf_snapshot();
    }
    if(rb_phase!=2)return EPROTO;
    struct de_chain created;struct stat config;uint8_t data[CR_SIZE]={0},boot[32],nonce[32];
    if((error=cf_prior(state,&created,boot,nonce)) || (error=cf_live(&config)) ||
       (error=cf_identity(&config,&created)) || (error=cf_snapshot()))return error;
    memcpy(data,"S22CC01\0",8);sw_put32(data+8,1);sw_put32(data+12,CR_SIZE);
    memcpy(data+16,sw.run,16);memcpy(data+32,sw.boot,32);memcpy(data+64,sw.nonce,32);
    cr_put64(data+CR_ROOT_DEVICE,sw.root_device);sw_put32(data+CR_PHASE,2);sw_put32(data+CR_BASELINE,RB_BASE_COUNT);
    sw_put32(data+CR_INSTALLED_COUNT,RB_BASE_COUNT+4);cr_put64(data+CR_ARMED_MS,sw_now());
    cr_put64(data+CR_DAEMON_PID,(uint64_t)initial);cr_put64(data+CR_DAEMON_TICKS,initial_ticks);
    memcpy(data+192,cr_cron_sha,32);memcpy(data+224,cr_sshd_sha,32);memcpy(data+256,state->hook_sha,32);
    cr_put64(data+CR_CRON_SIZE,CR_CRON_BYTES);cr_put64(data+CR_SSHD_SIZE,CR_SSHD_BYTES);
    cf_pack_identity(data,&created);memcpy(data+416,boot,32);memcpy(data+448,nonce,32);
    cr_tag(data+480,2,data,480);error=cr_ram_create(CR_READY,data);
    if(!error && cf_fault(10)) {
        struct stat probe;int rejected=cr_job(state);
        if(rejected!=EPROTO || !lstat(CR_INTENT,&probe) || errno!=ENOENT)return EINVAL;
        dprintf(2,"CF_MANUAL_REJECTED no_intent=1\n");return ECANCELED;
    }
    return error;
}
static int cf_partial_no_retry(struct dh_state *state) {
    int root=cf_root();if(root<0)return fs1_error();
    int parent=cr_parent(root,(dev_t)sw.root_device),error=parent<0 ? fs1_error() : 0;
    if(close(root) && !error)error=fs1_error();
    int fd=error ? -1 : openat(parent,strrchr(cr_path,'/')+1,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(!error && fd<0)error=fs1_error();
    struct stat before,after;uint8_t a[CR_SIZE/2],b[CR_SIZE/2];
    if(!error && (fstat(fd,&before) || before.st_size!=sizeof(a) || pread(fd,a,sizeof(a),0)!=sizeof(a) ||
        cr_job(state) || fstat(fd,&after) || !cf_same(&before,&after) ||
        pread(fd,b,sizeof(b),0)!=sizeof(b) || memcmp(a,b,sizeof(a))))error=EPROTO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(parent>=0 && close(parent) && !error)error=fs1_error();
    if(error)return error;
    dprintf(2,"CF_REPEAT_NO_WRITE partial_bytes=256\n");return ECANCELED;
}
static int cf_retire(struct dh_state *state) {
    /* Wait for the winning worker before checking the final publication and
     * claiming revocation. A worker abort can never be reused as success. */
    if(cf_fault(11))return cf_partial_no_retry(state);
    int error=cr_report_complete(state);
    if(error)return error;
    if((error=cf_success())) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
        dprintf(2,"CF_SUCCESS_REJECTED errno=%d\n",error);
#endif
        return error;
    }
    uint8_t report[CR_SIZE];error=cr_ram_read(CR_DONE,report);
    if(error || (error=cf_job_binding(report)))return error;
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(cf_fault(5))sw.deadline_ms=sw_now();
#endif
    if((error=cr_revoke_once(true)))return error;
    pid_t old=0,current=0;uint64_t ticks=0,current_ticks=0,deadline=0;
    if((error=cr_daemon(&old,&ticks)) || (uint64_t)old!=cr_u64(report+CR_DAEMON_PID) ||
       ticks!=cr_u64(report+CR_DAEMON_TICKS))return error ? error : EPROTO;
    if((error=cr_service_command("stop",&deadline)) || (error=cr_wait_gone(old,ticks,deadline)))return error;
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(cf_fault(8)) {
        pid_t child=fork();if(child<0)return fs1_error();
        if(!child) {
            if(syscall(SYS_close_range,3U,UINT_MAX,0U))_exit(125);
            char *args[]={"/usr/sbin/cron",NULL};execv(args[0],args);_exit(126);
        }
        int status=0;if(waitpid(child,&status,0)!=child || !WIFEXITED(status) || WEXITSTATUS(status))return ECHILD;
        pid_t orphan=0;uint64_t orphan_ticks=0;
        if((error=cr_wait_daemon(&orphan,&orphan_ticks,deadline,5)) || orphan==old)return error ? error : EPROTO;
        dprintf(2,"CF_ORPHAN_CRON_OBSERVED pid=%ld\n",(long)orphan);
    }
#endif
    if((error=cf_settled(deadline)))return error;
    int root=cf_root();if(root<0)return fs1_error();
    int parent=cf_parent(root,(dev_t)sw.root_device);error=parent<0 ? fs1_error() : 0;
    if(close(root) && !error)error=fs1_error();
    struct stat identity,after;int fd=error ? -1 : cf_open(parent,(dev_t)sw.root_device,&identity);
    if(!error && fd<0)error=fs1_error();
    if(!error)error=cf_job_binding(report);
    if(!error && (identity.st_ino!=(ino_t)cr_u64(report+CR_CONFIG_INODE) || de_time()))error=EPROTO;
    const char *name=strrchr(cf_path,'/')+1;
    if(!error) {
        if(unlinkat(parent,name,0))error=fs1_error();
#ifdef S22_ROOT_INSPECT_VIRT_TEST
        dprintf(2,"CF_UNLINK attempts=1 errno=%d\n",error);
#endif
    }
    if(!error && cf_fault(9))error=EIO;
    if(!error && (de_time() || fsync(parent)))error=EIO;
    if(!error && (!fstatat(parent,name,&after,AT_SYMLINK_NOFOLLOW) || errno!=ENOENT))error=EPROTO;
    if(!error && (fstat(fd,&after) || after.st_dev!=identity.st_dev || after.st_ino!=identity.st_ino ||
        after.st_nlink || after.st_size!=identity.st_size))error=EPROTO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(parent>=0 && close(parent) && !error)error=fs1_error();
    if(error)return error;
    if((error=cr_service_command("start",&deadline)) || (error=cr_wait_daemon(&current,&current_ticks,deadline,4)) ||
       current==old)return error ? error : EPROTO;
    return de_event(CF_RETIRED,2,1,(uint64_t)identity.st_ino,(uint64_t)current,current_ticks);
}
static int cr_complete(struct dh_state *state) {
    if(rb_phase==2)return cf_retire(state);
    if(rb_phase!=1)return EPROTO;
    struct stat config,probe;int error=cf_live(&config);
    if(!error)error=cf_identity(&config,&de);
    if(error)return error;
    const char *ram[]={CR_READY,CR_INTENT,CR_DONE,CF_SUCCESS};
    for(unsigned i=0;i<sizeof(ram)/sizeof(ram[0]);++i)
        if(!lstat(ram[i],&probe) || errno!=ENOENT)return EPROTO;
    int root=cf_root();if(root<0)return fs1_error();uint8_t report[CR_SIZE];
    error=cr_read(root,(dev_t)sw.root_device,report,true);
    if(close(root) && !error)error=fs1_error();
    return error;
}
