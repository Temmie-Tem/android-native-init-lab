/* Only phase 1 acquires one signed HTTPS package and runs one APT transaction.
 * All frontend state is RAM. Failure leaves the consumed transaction untouched. */
static int ap_dir(const char *path,uid_t uid,gid_t gid) {
    mode_t mask=umask(0);int rc=mkdir(path,0755),saved=errno;umask(mask);
    if(rc)return saved;
    int fd=open(path,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
        st.st_mode!=(S_IFDIR|0755) || st.st_uid || st.st_gid || fchown(fd,uid,gid) ? EPROTO : 0;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int ap_file(const char *path,const char *text) {
    mode_t mask=umask(0);int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0444);umask(mask);
    if(fd<0)return fs1_error();
    struct stat st;
    int error=ap_ram_stat(fd,&st,S_IFREG|0444,0);size_t size=strlen(text);
    if(!error && (write(fd,text,size)!=(ssize_t)size || fsync(fd)))error=EIO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int ap_workspace(void) {
    const char *dirs[]={"/run/s22-apt","/run/s22-apt/etc","/run/s22-apt/etc/empty",
        "/run/s22-apt/state","/run/s22-apt/lists","/run/s22-apt/lists/partial",
        "/run/s22-apt/cache","/run/s22-apt/cache/archives","/run/s22-apt/cache/archives/partial",
        "/run/s22-apt/log","/run/s22-apt/tmp","/run/s22-apt/function","/run/s22-apt/function/branch"};
    for(unsigned i=0;i<sizeof(dirs)/sizeof(dirs[0]);++i) {
        bool apt=i>=3 && i<=10;int error=ap_dir(dirs[i],apt ? 42 : 0,apt ? 65534 : 0);if(error)return error;
    }
    int error=ap_file("/run/s22-apt/apt.conf",ap_config);
    if(!error)error=ap_file("/run/s22-apt/etc/empty-main","");
    if(!error)error=ap_file("/run/s22-apt/etc/sources.list",ap_sources);
    if(!error)error=ap_file("/run/s22-apt/function/branch/leaf","fixed\n");
    return error;
}
static int ap_seal_directory(const char *path) {
    int fd=open(path,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L || st.st_mode!=(S_IFDIR|0755) ||
        st.st_uid!=42 || st.st_gid!=65534 ? EPROTO : 0;
    if(!error && (fchown(fd,0,0) || fchmod(fd,0555) || fsync(fd)))error=fs1_error();
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int ap_pin_acquired(const char *path,uint64_t size,const uint8_t sha[32]) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if((ap_fault(3) && size==ap_release_size) || (ap_fault(4) && size==ap_archive_size)) {
        int changed=open(path,O_RDWR|O_NOFOLLOW|O_CLOEXEC);uint8_t byte;
        if(changed<0 || pread(changed,&byte,1,0)!=1)return EIO;
        byte^=1;if(pwrite(changed,&byte,1,0)!=1 || fsync(changed) || close(changed))return EIO;
        dprintf(2,"APT_FAULT_CORRUPTED kind=%s bytes=1\n",size==ap_release_size ? "metadata" : "archive");
    }
#endif
    int fd=open(path,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L || st.st_mode!=(S_IFREG|0644) ||
        st.st_uid!=42 || st.st_gid!=65534 || st.st_nlink!=1 || st.st_size<0 || (uint64_t)st.st_size!=size ? EPROTO : 0;
    /* The process group is settled and the parent directory sealed. Keep
     * metadata readable by the next unprivileged download, but not writable. */
    if(!error && (fchown(fd,0,0) || fchmod(fd,0444) || fsync(fd)))error=fs1_error();
    if(close(fd) && !error)error=fs1_error();
    if(error)return error;
    fd=fs1_pin_file(path,size,sha,false);if(fd<0)return fs1_error();
    if(fstatfs(fd,&fs) || fs.f_type!=0x01021994L)error=EPROTO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int ap_network(uint64_t deadline,pid_t *child) {
    char *route[]={"/usr/bin/ip","route","add","default","via",(char *)ap_gateway,"dev",(char *)ap_interface,NULL};
    int error=pk_command(6,pk_programs+7,route,"",deadline,child);
    if(!error)error=ap_file("/run/s22-apt/resolv.conf",ap_resolver);
    uint8_t empty[32];sw_hash("",0,empty);
    int fd=error ? -1 : fs1_pin_file("/etc/resolv.conf",0,empty,false);struct stat st;
    if(!error && fd<0)error=fs1_error();
    if(!error && (fstat(fd,&st) || (uint64_t)st.st_dev!=sw.root_device))error=EPROTO;
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(!error && mount("/run/s22-apt/resolv.conf","/etc/resolv.conf",NULL,MS_BIND,NULL))error=fs1_error();
    if(!error && mount(NULL,"/etc/resolv.conf",NULL,MS_BIND|MS_REMOUNT|MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))error=fs1_error();
    return error;
}
static int pk_complete(struct dh_state *state) {
    if(!rb_valid_phase(rb_phase) || de.package_intent || de.package_complete || !de.apt_clock)return EPROTO;
    uint64_t deadline=sw_now()+PK_BUDGET_MS;if(deadline>sw.deadline_ms)deadline=sw.deadline_ms;
    int root=open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(root<0)return fs1_error();
    dev_t device=(dev_t)sw.root_device;int error=dh_actual_init(state);pid_t child=0;
    if(!error)error=pk_check_files(root,device,rb_phase==2);
    if(!error)error=pk_db_clean(root,device);
    if(!error)error=ap_workspace();
    char *audit[]={"/usr/bin/dpkg","--audit",NULL};
    char *update[]={"/usr/bin/apt-get","--error-on=any","update",NULL};
    char *download[]={"/usr/bin/apt-get","download","tree=2.2.1-1",NULL};
    char *plan[]={"/usr/bin/apt-get","--simulate","--no-remove","--no-install-recommends","install","tree=2.2.1-1",NULL,NULL};
    char *install[]={"/usr/bin/apt-get","--no-download","--no-remove","--no-install-recommends","install","tree=2.2.1-1",NULL};
    char *verify[]={"/usr/bin/dpkg","--verify","tree",NULL};
    char *function[]={"/usr/bin/tree","-n","--charset=ASCII","--noreport","/run/s22-apt/function",NULL};
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(ap_fault(5))plan[6]="ed";
    if(ap_fault(6))install[5]="tree=0";
#endif
    if(!error)error=pk_command(1,pk_programs,audit,"",deadline,&child);
    for(unsigned i=1;!error && i<8;++i) {
        int fd=fs1_pin_file(pk_programs[i].path,pk_programs[i].size,pk_programs[i].sha,i!=6);struct stat st;
        if(fd<0)error=fs1_error();
        else {
            if(fstat(fd,&st) || (uint64_t)st.st_dev!=sw.root_device)error=EPROTO;
            if(close(fd) && !error)error=fs1_error();
        }
    }
    if(!error && rb_phase==1) {
        if((error=ap_network(deadline,&child)))goto done;
        if((error=pk_command(10,pk_programs+3,update,NULL,deadline,&child)))goto done;
        if((error=ap_seal_directory("/run/s22-apt/lists")))goto done;
        if((error=ap_pin_acquired("/run/s22-apt/lists/deb.debian.org_debian_dists_trixie_InRelease",ap_release_size,ap_release_sha)) ||
           (error=ap_pin_acquired("/run/s22-apt/lists/deb.debian.org_debian_dists_trixie_main_binary-arm64_Packages.lz4",ap_index_size,ap_index_sha)))goto done;
        if((error=pk_command(11,pk_programs+3,download,NULL,deadline,&child)))goto done;
        if((error=ap_seal_directory("/run/s22-apt/cache/archives")))goto done;
        if((error=ap_seal_directory("/run/s22-apt/cache")))goto done;
        if((error=ap_pin_acquired("/run/s22-apt/cache/archives/tree_2.2.1-1_arm64.deb",ap_archive_size,ap_archive_sha)))goto done;
        if((error=pk_command(12,pk_programs+3,plan,ap_plan,deadline,&child)))goto done;
        if((error=pk_check_files(root,device,false)) || (error=pk_db_clean(root,device)))goto done;
        if((error=de_event(16,1,1,ap_release_size,ap_index_size,ap_archive_size)))goto done;
    }
    if(!error)error=de_event(13,rb_phase,rb_phase,PK_ADDED,PK_ROWS,0);
    if(!error && rb_phase==1)error=pk_command(2,pk_programs+3,install,NULL,deadline,&child);
    if(!error && rb_phase==1)error=pk_command(3,pk_programs,audit,"",deadline,&child);
    if(!error)error=pk_command(4,pk_programs,verify,"",deadline,&child);
    if(!error)error=pk_check_files(root,device,true);
    if(!error)error=pk_db_clean(root,device);
    if(!error)error=pk_command(5,&pk_hello,function,ap_function_output,deadline,&child);
    if(!error && rb_phase==1 && syncfs(root))error=fs1_error();
    if(!error && rb_phase==1 && umount("/etc/resolv.conf"))error=fs1_error();
    if(!error)error=pk_check_files(root,device,true);
    if(!error)error=dh_actual_init(state);
    if(!error && (de_time() || sw_now()>=deadline))error=ETIMEDOUT;
    if(!error)error=de_event(14,rb_phase,rb_phase,(uint64_t)child,0,PK_ROWS);
 done:
    if(close(root) && !error)error=fs1_error();
    dprintf(2,"APT_RESULT phase=%u intent=%u complete=%u errno=%d\n",rb_phase,de.package_intent,de.package_complete,error);
    return error;
}
