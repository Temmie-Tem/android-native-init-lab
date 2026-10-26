/* One fixed dpkg transaction in the existing installed-root lifetime.
 * Failed/uncertain writes are retained, never retried, repaired or removed. */
#include "s22plus_debian_package_files_v1.h"
static bool pk_fault(unsigned wanted) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    char text[4096],expected[40];
    if(fs1_read_text("/proc/cmdline",text,sizeof(text)))return false;
    snprintf(expected,sizeof(expected),"s22pk_fault=%u",wanted);
    size_t n=strlen(expected);char *at=strstr(text,expected);
    return at && (at==text || at[-1]==' ') && (at[n]==' ' || at[n]=='\n' || !at[n]);
#else
    (void)wanted;return false;
#endif
}
static int pk_program(const struct pk_program *program) {
    int fd=fs1_pin_file(program->path,program->size,program->sha,true);
    if(fd<0)return fs1_error();
    struct stat st;int error=fstat(fd,&st) || (uint64_t)st.st_dev!=sw.root_device ? EPROTO : 0;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int pk_db_clean(int root,dev_t device) {
    char leaf[NAME_MAX+1];int parent=pk_parent(root,device,"var/lib/dpkg/updates",leaf);
    if(parent<0)return fs1_error();
    int fd=openat(parent,leaf,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    int error=fd<0 ? fs1_error() : pk_directory(fd,device);
    if(!error)error=pk_transients_absent(root,device);
    if(close(parent) && !error)error=fs1_error();
    if(fd<0)return error;
    DIR *directory=fdopendir(fd);
    if(!directory){(void)close(fd);return fs1_error();}
    while(!error) {
        errno=0;struct dirent *entry=readdir(directory);
        if(!entry){if(errno)error=errno;break;}
        if(strcmp(entry->d_name,".") && strcmp(entry->d_name,"..")){error=EEXIST;break;}
    }
    if(closedir(directory) && !error)error=fs1_error();
    return error;
}
static int pk_command(unsigned step,const struct pk_program *program,char *const argv[],
                      const char *expected,uint64_t deadline,pid_t *identity) {
    int error=de_time();if(error || sw_now()>=deadline)return error ? error : ETIMEDOUT;
    if((error=pk_program(program)))return error;
    char path[128];snprintf(path,sizeof(path),"/run/s22-debian/package-output-%u",step);
    mode_t mask=umask(0);int log=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    umask(mask);if(log<0)return fs1_error();
    struct statfs fs;int pipefd[2]={-1,-1};
    if(fstatfs(log,&fs) || fs.f_type!=0x01021994L)error=EPROTO;
    if(!error && pipe2(pipefd,O_CLOEXEC|O_NONBLOCK))error=fs1_error();
    if(error){(void)close(log);return error;}
    pid_t child=fork();
    if(!child) {
        if(setpgid(0,0) || dup2(pipefd[1],1)!=1 || dup2(pipefd[1],2)!=2 ||
           fcntl(1,F_SETFL,0) || fcntl(2,F_SETFL,0))_exit(125);
        int input=open("/dev/null",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
        if(input<0 || dup2(input,0)!=0 || syscall(SYS_close_range,3U,UINT_MAX,0U))_exit(125);
        if(sw_now()>=deadline || de_time())_exit(124);
#ifdef S22_ROOT_INSPECT_VIRT_TEST
        if(step==2 && pk_fault(2))for(;;)pause();
        if(step==5 && pk_fault(6)) {
            pid_t orphan=fork();if(orphan<0)_exit(125);
            if(!orphan){(void)syscall(SYS_close_range,0U,UINT_MAX,0U);for(;;)pause();}
        }
#endif
        umask(022);
        char *env[]={"PATH=/usr/sbin:/usr/bin:/sbin:/bin","LC_ALL=C","LANG=C","TZ=UTC","HOME=/root",NULL};
        execve(program->path,argv,env);_exit(126);
    }
    if(child<0)error=fs1_error();
    if(close(pipefd[1]) && !error)error=fs1_error();
    if(!error && setpgid(child,child) && !(errno==EACCES && getpgid(child)==child))error=fs1_error();
    uint8_t output[65536];size_t used=0;bool reaped=false,eof=false;int status=0;
    bool group_gone=false;
    while(!error && (!reaped || !eof || !group_gone)) {
        if(de_time() || sw_now()>=deadline){error=ETIMEDOUT;break;}
        uint8_t bytes[4096];ssize_t got=read(pipefd[0],bytes,sizeof(bytes));
        if(got>0) {
            if((size_t)got>sizeof(output)-used){error=EFBIG;break;}
            memcpy(output+used,bytes,(size_t)got);used+=(size_t)got;
            if(write(log,bytes,(size_t)got)!=got){error=EIO;break;}
        } else if(!got)eof=true;
        else if(errno!=EAGAIN && errno!=EINTR){error=fs1_error();break;}
        if(!reaped) {
            pid_t waited=waitpid(child,&status,WNOHANG);
            if(waited==child)reaped=true;
            else if(waited<0 && errno!=EINTR){error=fs1_error();break;}
        }
        if(reaped && eof) {
            if(kill(-child,0)) {
                if(errno==ESRCH)group_gone=true;
                else {error=fs1_error();break;}
            }
        }
        if(!reaped || !eof || !group_gone) {
            struct timespec delay={0,10000000};
            if(nanosleep(&delay,NULL) && errno!=EINTR)error=fs1_error();
        }
    }
    if(error && child>1){(void)kill(-child,SIGKILL);(void)kill(child,SIGKILL);}
    if(close(pipefd[0]) && !error)error=fs1_error();
    if(fsync(log) && !error)error=fs1_error();
    if(close(log) && !error)error=fs1_error();
    if(!error && (!WIFEXITED(status) || WEXITSTATUS(status)))error=ECHILD;
    if(!error && expected && (used!=strlen(expected) || memcmp(output,expected,used)))error=EPROTO;
    if(!error && (de_time() || sw_now()>=deadline))error=ETIMEDOUT;
    dprintf(2,"PACKAGE_COMMAND phase=%u step=%u pid=%ld status=%d bytes=%zu errno=%d\n",
        rb_phase,step,(long)child,status,used,error);
    if(!error)*identity=child;
    return error;
}
static int pk_complete(struct dh_state *state) {
    if(!rb_valid_phase(rb_phase) || de.package_intent || de.package_complete)return EPROTO;
    uint64_t deadline=sw_now()+PK_BUDGET_MS;if(deadline>sw.deadline_ms)deadline=sw.deadline_ms;
    int root=open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(root<0)return fs1_error();
    dev_t device=(dev_t)sw.root_device;
    int error=dh_actual_init(state);pid_t child=0;
    if(!error)error=pk_check_files(root,device,rb_phase==2);
    if(!error)error=pk_db_clean(root,device);
    char *audit[]={"/usr/bin/dpkg","--audit",NULL};
    char *install[]={"/usr/bin/dpkg","--log=/run/s22-debian/package-dpkg.log","--install",
        "/usr/local/lib/lab-offline/hello.deb",NULL};
    char *verify[]={"/usr/bin/dpkg","--verify","hello",NULL};
    char *hello[]={"/usr/bin/hello","--greeting=S22_PACKAGE_FUNCTION",NULL};
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(pk_fault(1))install[3]="/run/s22-debian/package-absent.deb";
    if(pk_fault(3))hello[1]="--greeting=UNEXPECTED_PACKAGE_OUTPUT";
#endif
    if(!error)error=pk_command(1,pk_programs,audit,"",deadline,&child);
    for(unsigned i=1;!error && i<4;++i) {
        int fd=fs1_pin_file(pk_programs[i].path,pk_programs[i].size,pk_programs[i].sha,i<3);
        struct stat st;
        if(fd<0)error=fs1_error();
        else {
            if(fstat(fd,&st) || (uint64_t)st.st_dev!=sw.root_device)error=EPROTO;
            if(close(fd) && !error)error=fs1_error();
        }
    }
    if(!error && rb_phase==1) {
        mode_t mask=umask(0);int log=open("/run/s22-debian/package-dpkg.log",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
        umask(mask);struct statfs fs;
        if(log<0)error=fs1_error();
        else {
            if(fstatfs(log,&fs) || fs.f_type!=0x01021994L)error=EPROTO;
            if(close(log) && !error)error=fs1_error();
        }
    }
    if(!error)error=de_event(13,rb_phase,rb_phase,PK_ADDED,PK_ROWS,0);
    if(!error && pk_fault(5))error=de_event(13,rb_phase,rb_phase,PK_ADDED,PK_ROWS,0);
    if(!error && rb_phase==1)error=pk_command(2,pk_programs,install,NULL,deadline,&child);
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(!error && pk_fault(7)) {
        int fd=open("/usr/bin/hello.dpkg-new",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0644);
        if(fd<0 || write(fd,"X",1)!=1)error=EIO;
        if(fd>=0 && close(fd) && !error)error=fs1_error();
    }
#endif
    if(!error && rb_phase==1)error=pk_command(3,pk_programs,audit,"",deadline,&child);
    if(!error)error=pk_command(4,pk_programs,verify,"",deadline,&child);
    if(!error)error=pk_check_files(root,device,true);
    if(!error)error=pk_db_clean(root,device);
    if(!error)error=pk_command(5,&pk_hello,hello,"S22_PACKAGE_FUNCTION\n",deadline,&child);
    if(!error && (de_time() || sw_now()>=deadline))error=ETIMEDOUT;
    if(!error && pk_fault(4))error=EIO;
    if(!error && rb_phase==1 && syncfs(root))error=fs1_error();
    if(!error)error=pk_check_files(root,device,true);
    if(!error)error=dh_actual_init(state);
    if(close(root) && !error)error=fs1_error();
    if(!error && (de_time() || sw_now()>=deadline))error=ETIMEDOUT;
    if(!error)error=de_event(14,rb_phase,rb_phase,(uint64_t)child,0,PK_ROWS);
    dprintf(2,"PACKAGE_RESULT phase=%u intent=%u complete=%u errno=%d\n",
        rb_phase,de.package_intent,de.package_complete,error);
    return error;
}
