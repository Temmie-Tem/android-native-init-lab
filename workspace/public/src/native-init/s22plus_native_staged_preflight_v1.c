/* Fixed protected preparation after native ACM is already authenticated.
 * Every stage is streamed before/after its work. No PID 1 replacement,
 * writable root, module insertion, mdev scan or service startup is reachable.
 */
struct fs1_endpoint;
struct up_stream;
static void sp_begin(const char *), sp_pass(const char *), sp_error(int), sp_cleanup(int);
static int sp_checker(struct fs1_endpoint *), sp_expected(const struct up_stream *);
static void sp_child(int,struct fs1_endpoint *,int [3][2],int,int);
#define RI_PROGRESS_BEGIN(name) sp_begin(name)
#define RI_PROGRESS_END(name) sp_pass(name)
#define RI_PROGRESS_ERROR(error) sp_error(error)
#define RI_PROGRESS_CLEANUP(error) sp_cleanup(error)
#define RI_PRE_MOUNT(endpoint) sp_checker(endpoint)
#define UP_REPEAT_FIXED
#define UP_FIXED_CHILD sp_child
#define UP_FIXED_OUTPUT sp_expected
#define S22_USERSPACE_PROBE_LIBRARY
#ifdef S22_STAGED_PREFLIGHT_FAULT
/* The included child engine rejects fault builds without virtual discovery. */
#define S22_USERSPACE_PROBE_FAULT
#endif
#include "s22plus_native_userspace_probe_v1.c"
#include "s22plus_native_staged_preflight_seal_v1.h"

enum { SP_CHECKER=1, SP_VERIFY=2, SP_LIST=3 };
static unsigned sp_sequence, sp_kind, sp_attempts, sp_passes, sp_stopped;
static const char *sp_active;
static int sp_checker_fd=-1;

static int sp_known(const char *name) {
    for (unsigned i=0;i<sizeof(sp_steps)/sizeof(sp_steps[0]);++i)
        if (!strcmp(name,sp_steps[i])) return 1;
    return 0;
}
static void sp_emit(const char *name,const char *phase,int error) {
    if (!sp_known(name) || sp_sequence>=64 || error<0 || error>4095) _exit(119);
    ri_print("SP1_STAGE seq=%u step=%s phase=%s errno=%d\n",++sp_sequence,name,phase,error);
}
static void sp_begin(const char *name) {
    if (sp_active) _exit(119);
    sp_active=name; sp_emit(name,"begin",0);
}
static void sp_end(const char *phase,int error) {
    if (!sp_active) _exit(119);
    sp_emit(sp_active,phase,error); sp_active=NULL;
}
static void sp_pass(const char *name) {
    if (!sp_active || strcmp(sp_active,name)) _exit(119);
    sp_end("pass",0);
}
static void sp_error(int error) {
    if (sp_active) sp_end("error",error ? error : EPROTO);
}
static void sp_cleanup(int error) { if (error) sp_error(error); else sp_pass("cleanup"); }

/* The checker is the pinned, image-owned static binary, under partition RO.
 * Both variants close borrowed fds, clear groups/caps and set NNP. Only the
 * loader variant gains an executable private mount and enters the chroot. */
static void sp_child(int root,struct fs1_endpoint *endpoint,int pipes[3][2],int parent,int group) {
    unsigned stage=1; int report=pipes[2][1],error=0;
    if (getppid()!=parent || getpgrp()!=group) up_child_fail(report,stage,EPROTO);
    if (sp_kind!=SP_CHECKER) {
        if (unshare(CLONE_NEWNS)) up_child_fail(report,stage,fs1_error());
        stage=2;
        if (mount(NULL,ri_root,NULL,MS_REMOUNT|MS_BIND|MS_RDONLY|MS_NOSUID|MS_NODEV,NULL))
            up_child_fail(report,stage,fs1_error());
        int selected=open(ri_root,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        struct stat st; struct statfs fs;
        if (selected<0 || fstat(selected,&st) || fstatfs(selected,&fs) ||
            st.st_dev!=endpoint->partition || fs.f_type!=0xef53 ||
            (fs.f_flags&(ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC))!=(ST_RDONLY|ST_NOSUID|ST_NODEV) ||
            (error=ri_ro(endpoint,false))) up_child_fail(report,stage,error);
        stage=3;
        if (close(root) || fchdir(selected) || chroot(".") || chdir("/"))
            up_child_fail(report,stage,fs1_error());
    }
    int held=sp_kind==SP_CHECKER ? fcntl(sp_checker_fd,F_DUPFD_CLOEXEC,32) : -1;
    int saved=fcntl(report,F_DUPFD_CLOEXEC,32),input[2];
    if ((sp_kind==SP_CHECKER && held<0) || saved<0 || pipe2(input,O_CLOEXEC) || close(input[1]))
        up_child_fail(report,stage,fs1_error());
    if (dup2(input[0],0)!=0 || dup2(pipes[0][1],1)!=1 || dup2(pipes[1][1],2)!=2 ||
        dup3(saved,3,O_CLOEXEC)!=3) up_child_fail(report,stage,fs1_error());
    report=3; stage=4;
    if ((held>=0 && dup3(held,4,O_CLOEXEC)!=4) ||
        syscall(SYS_close_range,held>=0 ? 5U : 4U,UINT_MAX,0U)) up_child_fail(report,stage,fs1_error());
    stage=5;
    if ((error=up_limit(RLIMIT_CORE,0)) || (error=up_limit(RLIMIT_FSIZE,0)) ||
        (error=up_limit(RLIMIT_CPU,sp_kind==SP_CHECKER ? 25 : 8)) ||
        (error=up_limit(RLIMIT_AS,(sp_kind==SP_CHECKER ? 512U : 128U)*1024U*1024U)) ||
        (error=up_limit(RLIMIT_NOFILE,64)) || (error=up_limit(RLIMIT_NPROC,16))) up_child_fail(report,stage,error);
    stage=6;
    unsigned identity=sp_kind==SP_CHECKER ? 0 : 65534;
    struct __user_cap_header_struct header={_LINUX_CAPABILITY_VERSION_3,0};
    struct __user_cap_data_struct caps[2]={{0},{0}};
    if (prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) || prctl(PR_SET_KEEPCAPS,0,0,0,0) ||
        setgroups(0,NULL) || setresgid(identity,identity,identity) || setresuid(identity,identity,identity) ||
        syscall(SYS_capset,&header,caps)) up_child_fail(report,stage,fs1_error());
    uid_t ru,eu,su; gid_t rg,eg,sg;
    stage=7;
    if (getresuid(&ru,&eu,&su) || getresgid(&rg,&eg,&sg) ||
        ru!=identity || eu!=identity || su!=identity || rg!=identity || eg!=identity || sg!=identity ||
        getgroups(0,NULL) || syscall(SYS_capget,&header,caps) ||
        caps[0].effective || caps[0].permitted || caps[0].inheritable ||
        caps[1].effective || caps[1].permitted || caps[1].inheritable ||
        prctl(PR_GET_NO_NEW_PRIVS,0,0,0,0)!=1 || getppid()!=parent || getpgrp()!=group ||
        prctl(PR_SET_PDEATHSIG,SIGKILL,0,0,0) || getppid()!=parent) up_child_fail(report,stage,EPROTO);
#ifdef S22_STAGED_PREFLIGHT_FAULT
    if (sp_kind==sp_fault_kind && sp_fault_mode==1) up_child_fail(report,7,EPERM);
    if (sp_kind==sp_fault_kind && sp_fault_mode==2) _exit(0);
#endif
    up_packet(report,UP_READY,0);
#ifdef S22_STAGED_PREFLIGHT_FAULT
    if (sp_kind==sp_fault_kind) {
        if (sp_fault_mode==3) _exit(17);
        if (sp_fault_mode==4) {raise(SIGKILL);_exit(127);}
        if (sp_fault_mode==5) for (;;) pause();
        if (sp_fault_mode==6) {char out[4096];memset(out,'x',sizeof(out));for (unsigned i=0;i<8;++i)if(write(1,out,sizeof(out))!=(ssize_t)sizeof(out))_exit(5);_exit(0);}
        if (sp_fault_mode==7) {
            pid_t stray=fork();if (stray<0) up_child_fail(report,7,fs1_error());
            if (!stray) for (;;) pause();
        }
        if (sp_fault_mode==8) {char *bad[]={"/missing",NULL};execve(bad[0],bad,NULL);up_child_fail(report,UP_EXEC,fs1_error());}
        if (sp_fault_mode==9) {if(write(1,"wrong\n",6)!=6)_exit(5);_exit(0);}
    }
#endif
    char *env[]={"PATH=/usr/sbin:/usr/bin:/sbin:/bin","LC_ALL=C","LANG=C","HOME=/nonexistent",NULL};
    if (sp_kind==SP_CHECKER) {
        char *args[]={"e2fsck","-fn",(char *)fs1_node,NULL};
        fexecve(4,args,env);
    } else {
        char *args[]={"/lib/ld-linux-aarch64.so.1",sp_kind==SP_VERIFY ? "--verify" : "--list","/sbin/init",NULL};
        execve(args[0],args,env);
    }
    up_child_fail(report,UP_EXEC,fs1_error());
}

static int sp_contains(const struct up_stream *stream,const char *needle) {
    size_t length=strlen(needle);
    for (size_t i=0;i+length<=stream->used;++i)
        if (!memcmp(stream->bytes+i,needle,length)) return 1;
    return 0;
}
static int sp_expected(const struct up_stream *streams) {
    if (sp_kind==SP_CHECKER) {
        for (unsigned i=1;i<=5;++i) {
            char expected[]="Pass 0:";expected[5]=(char)('0'+i);
            if (!sp_contains(streams,expected)) return 0;
        }
        return sp_contains(streams+1,"e2fsck ");
    }
    if (streams[1].used) return 0;
    if (sp_kind==SP_VERIFY) return streams[0].used==0;
    unsigned found[sizeof(sp_loader_lines)/sizeof(sp_loader_lines[0])]={0},count=0;
    size_t pos=0;
    while (pos<streams[0].used) {
        while (pos<streams[0].used && (streams[0].bytes[pos]==' ' || streams[0].bytes[pos]=='\t')) ++pos;
        unsigned match=(unsigned)(sizeof(found)/sizeof(found[0]));
        for (unsigned i=0;i<sizeof(found)/sizeof(found[0]);++i) {
            size_t n=strlen(sp_loader_lines[i]);
            if (pos+n+4<streams[0].used && !memcmp(streams[0].bytes+pos,sp_loader_lines[i],n) &&
                !memcmp(streams[0].bytes+pos+n," (0x",4)) {match=i;pos+=n+4;break;}
        }
        if (match==sizeof(found)/sizeof(found[0]) || found[match]++) return 0;
        unsigned digits=0;
        while (pos<streams[0].used && ((streams[0].bytes[pos]>='0' && streams[0].bytes[pos]<='9') ||
            (streams[0].bytes[pos]>='a' && streams[0].bytes[pos]<='f'))) {++digits;++pos;}
        if (!digits || digits>16 || pos+2>streams[0].used || streams[0].bytes[pos++]!=')' ||
            streams[0].bytes[pos++]!='\n') return 0;
        ++count;
    }
    return count==sizeof(found)/sizeof(found[0]);
}
static int sp_execute(unsigned kind,int root,struct fs1_endpoint *endpoint) {
    sp_kind=kind; ++sp_attempts;
    int error=up_execute(root,endpoint);
    if (kind==SP_CHECKER) {
        if (close(sp_checker_fd) && !error) error=fs1_error();
        sp_checker_fd=-1;
    }
    if (error) { sp_error(error); return error; }
    if (!up_proved) { sp_stopped=1; sp_end("stop",0); return -1; }
    ++sp_passes;sp_end("pass",0);return 0;
}
static int sp_checker(struct fs1_endpoint *endpoint) {
    sp_begin("checker");
    struct stat config;
    if (!lstat("/etc/e2fsck.conf",&config) || errno!=ENOENT) return EPROTO;
    sp_checker_fd=fs1_pin_file(fs1_checker,fs1_checker_size,fs1_checker_sha256,true);
    if (sp_checker_fd<0) return fs1_error();
    return sp_execute(SP_CHECKER,-1,endpoint);
}

static int sp_observe(int root,struct fs1_endpoint *endpoint,const struct ri_counts *counts,
                      const struct ri_compare *comparison,int started,int complete,int witness) {
    sp_begin("eligibility");
    struct stat lost; struct statfs fs;
    bool eligible=started==1 && complete==1 && witness==1 && comparison->expected==ri_table_count &&
        comparison->matched==ri_table_count && !comparison->missing && !comparison->metadata && !comparison->content &&
        counts->entries==ri_table_count+4 && !counts->other &&
        !fstatat(root,"lost+found",&lost,AT_SYMLINK_NOFOLLOW) && lost.st_dev==endpoint->partition &&
        S_ISDIR(lost.st_mode) && (lost.st_mode&07777)==0700 && !lost.st_uid && !lost.st_gid &&
        !fs1_empty_directory("/s22-root-work/root-inspect-v1/root/lost+found");
    ri_print("SP1_ELIGIBLE exact=%u\n",eligible);
    if (!eligible) {sp_stopped=1;sp_end("stop",0);return 0;}
    sp_pass("eligibility");
    sp_begin("loader-inputs");
    struct stat st;
    if (!fstatat(root,"etc/ld.so.preload",&st,AT_SYMLINK_NOFOLLOW) || errno!=ENOENT) return EPROTO;
    int fd=fs1_pin_file("/s22-root-work/root-inspect-v1/root/etc/ld.so.cache",sp_cache_size,sp_cache_sha256,false);
    if (fd<0) return fs1_error();
    if (close(fd)) return fs1_error();
    sp_pass("loader-inputs");
    for (unsigned kind=SP_VERIFY;kind<=SP_LIST;++kind) {
        sp_begin(kind==SP_VERIFY ? "loader-verify" : "loader-list");
        int error=sp_execute(kind,root,endpoint);
        if (error>0) return error;
        if (error<0) break;
    }
    sp_begin("parent-protection");
    int error=ri_ro(endpoint,false);
    if (error) return error;
    if (fstatfs(root,&fs) ||
        (fs.f_flags&(ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC))!=(ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC)) return EPROTO;
    sp_pass("parent-protection");return 0;
}

int main(int argc,char **argv) {
    int result=ri_run(argc,argv,"staged",sp_observe);
    ri_print("SP1_RESULT complete=%u children=%u passed=%u stopped=%u\n",!result,sp_attempts,sp_passes,sp_stopped);
    return result;
}
