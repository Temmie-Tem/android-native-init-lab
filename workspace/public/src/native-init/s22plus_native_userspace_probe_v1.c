/* One fixed, unprivileged installed-Debian workload. The parent retains the
 * protected noexec mount and the existing ACM supervisor's process group.
 * No install, writable mount, service, network operation or PID 1 handoff.
 */
#define S22_ROOT_INSPECT_LIBRARY
#include "s22plus_native_root_inspect_v1.c"
#include <grp.h>
#include <linux/capability.h>
#include <poll.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <time.h>

_Static_assert(SYS_close_range == 436, "retained ARM64 close_range ABI");
_Static_assert(SYS_capget == 90, "retained ARM64 capget ABI");

#define UP_OUTPUT_MAX 4096U
#define UP_READY 100U
#define UP_EXEC 101U
#define UP_TIMEOUT_MS 30000U

#include "s22plus_native_userspace_probe_seal_v1.h"

/* Fault workloads exist only in explicitly virtual-board H0 builds. Their
 * source and compiler selection are retained separately from shipped bytes.
 */
#ifdef S22_USERSPACE_PROBE_FAULT
#ifndef S22_ROOT_INSPECT_VIRT_TEST
#error "fault injection requires explicit virtual board discovery"
#endif
#include "s22plus_native_userspace_probe_fault_v1.h"
#endif

struct up_stream { int fd; size_t used, maximum; uint8_t bytes[UP_OUTPUT_MAX]; };
struct up_packet { uint32_t stage, error; };
static unsigned up_attempted, up_reaped, up_adopted, up_settled, up_proved, up_setup_stage, up_setup_errno;
static int up_status, up_error;

static int up_time(uint64_t *now) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) return fs1_error();
    *now=(uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U; return 0;
}

static void up_packet(int fd, unsigned stage, int error) {
    struct up_packet packet={stage,(uint32_t)error};
    const uint8_t *p=(const uint8_t *)&packet; size_t left=sizeof(packet);
    while (left) {
        ssize_t n=write(fd,p,left);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) _exit(125);
        p+=n; left-=(size_t)n;
    }
}

static void up_child_fail(int fd, unsigned stage, int error) {
    up_packet(fd,stage,error ? error : EPROTO); _exit(126);
}

static int up_limit(int resource, rlim_t value) {
    struct rlimit limit={value,value}; return setrlimit(resource,&limit) ? fs1_error() : 0;
}

static void up_child(int root, struct fs1_endpoint *endpoint, int pipes[3][2], pid_t parent, pid_t group) {
    unsigned stage=1; int error=0, report=pipes[2][1];
    if (getppid()!=parent || getpgrp()!=group) up_child_fail(report,stage,EPROTO);
    /* Keep the inherited ACM command group; never setsid or setpgid here. */
    if (unshare(CLONE_NEWNS)) up_child_fail(report,stage,fs1_error());
    stage=2;
    /* MS_BIND remount alters only this namespace's vfsmount flags, without
     * asking ext4 to reconfigure the shared superblock or journal options. */
    if (mount(NULL,ri_root,NULL,MS_REMOUNT|MS_BIND|MS_RDONLY|MS_NOSUID|MS_NODEV,NULL))
        up_child_fail(report,stage,fs1_error());
    int selected=open(ri_root,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st; struct statfs fs;
    if (selected<0 || fstat(selected,&st) || fstatfs(selected,&fs) ||
        st.st_dev!=endpoint->partition || fs.f_type!=0xef53 ||
        (fs.f_flags&(ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC))!=(ST_RDONLY|ST_NOSUID|ST_NODEV) ||
        (error=ri_ro(endpoint,false))) up_child_fail(report,stage,error);
    stage=3;
    /* The inherited root fd refers to the parent's noexec mount. Use the
     * freshly opened clone for chroot; no old-root fd survives exec. */
    if (close(root) || fchdir(selected) || chroot(".") || chdir("/")) up_child_fail(report,stage,fs1_error());
    for (unsigned i=0;i<2;++i)
        if (dup2(pipes[i][1],(int)i+1)!=(int)i+1) up_child_fail(report,stage,fs1_error());
    int input[2];
    if (pipe2(input,O_CLOEXEC) || close(input[1]) || dup2(input[0],0)!=0)
        up_child_fail(report,stage,fs1_error()); /* empty read-only pipe, no device fd */
    stage=4;
    if ((report>3 && syscall(SYS_close_range,3U,(unsigned)report-1U,0U)) ||
        syscall(SYS_close_range,(unsigned)report+1U,UINT_MAX,0U)) up_child_fail(report,stage,fs1_error());
    stage=5;
    if ((error=up_limit(RLIMIT_CORE,0)) || (error=up_limit(RLIMIT_FSIZE,0)) ||
        (error=up_limit(RLIMIT_CPU,8)) || (error=up_limit(RLIMIT_AS,128U*1024U*1024U)) ||
        (error=up_limit(RLIMIT_NOFILE,64)) || (error=up_limit(RLIMIT_NPROC,16))) up_child_fail(report,stage,error);
    stage=6;
    if (prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) || prctl(PR_SET_KEEPCAPS,0,0,0,0) ||
        setgroups(0,NULL) || setresgid(65534,65534,65534) || setresuid(65534,65534,65534))
        up_child_fail(report,stage,fs1_error());
    uid_t ru,eu,su; gid_t rg,eg,sg;
    struct __user_cap_header_struct header={_LINUX_CAPABILITY_VERSION_3,0};
    struct __user_cap_data_struct caps[2]={{0},{0}};
    stage=7;
    if (getresuid(&ru,&eu,&su) || getresgid(&rg,&eg,&sg) || ru!=65534 || eu!=65534 || su!=65534 ||
        rg!=65534 || eg!=65534 || sg!=65534 || getgroups(0,NULL)!=0 ||
        syscall(SYS_capget,&header,caps) || caps[0].effective || caps[0].permitted || caps[0].inheritable ||
        caps[1].effective || caps[1].permitted || caps[1].inheritable || prctl(PR_GET_NO_NEW_PRIVS,0,0,0,0)!=1 ||
        getppid()!=parent || getpgrp()!=group) up_child_fail(report,stage,EPROTO);
    /* Reapply after the UID transition, which clears the parent-death signal. */
    if (prctl(PR_SET_PDEATHSIG,SIGKILL,0,0,0) || getppid()!=parent) up_child_fail(report,stage,EPROTO);
    const char *script=up_script;
#ifdef S22_USERSPACE_PROBE_FAULT
    script=up_fault_script;
    if (up_fault_early_zero) _exit(0);
    if (up_fault_setup_error) up_child_fail(report,7,EPERM);
    if (up_fault_orphan) {
        pid_t stray=fork();
        if (stray<0) up_child_fail(report,7,fs1_error());
        if (!stray) { struct timespec pause={60,0}; (void)nanosleep(&pause,NULL); _exit(0); }
    }
#endif
    up_packet(report,UP_READY,0);
    char *args[]={"/bin/sh","-c",(char *)script,NULL};
    char *env[]={"PATH=/usr/bin:/bin","LC_ALL=C","LANG=C","HOME=/nonexistent",NULL};
    execve(args[0],args,env); up_child_fail(report,UP_EXEC,fs1_error());
}

static int up_drain(struct up_stream *stream) {
    while (stream->fd>=0) {
        uint8_t extra; size_t left=stream->maximum-stream->used;
        ssize_t n=read(stream->fd,left ? stream->bytes+stream->used : &extra,left ? left : 1);
        if (n<0 && errno==EINTR) continue;
        if (n<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) return 0;
        if (n<0) return fs1_error();
        if (!n) { int error=close(stream->fd) ? fs1_error() : 0; stream->fd=-1; return error; }
        if (!left) return EOVERFLOW;
        stream->used+=(size_t)n;
    }
    return 0;
}

static void up_output(const char *name, const struct up_stream *stream) {
    static const char hex[]="0123456789abcdef";
    char encoded[2U*UP_OUTPUT_MAX+1];
    for (size_t i=0;i<stream->used;++i) { encoded[i*2]=hex[stream->bytes[i]>>4]; encoded[i*2+1]=hex[stream->bytes[i]&15]; }
    encoded[stream->used*2]=0;
    ri_print("UP1_OUTPUT stream=%s bytes=%zu hex=%s\n",name,stream->used,stream->used?encoded:"-");
}

static int up_execute(int root, struct fs1_endpoint *endpoint) {
    int error=0, pipes[3][2]={{-1,-1},{-1,-1},{-1,-1}};
    struct up_stream streams[3]={{.fd=-1,.maximum=UP_OUTPUT_MAX},{.fd=-1,.maximum=UP_OUTPUT_MAX},
        {.fd=-1,.maximum=2*sizeof(struct up_packet)}};
    uint64_t started,now; pid_t pid=-1;
    if ((error=up_time(&started))) goto done;
    if (prctl(PR_SET_CHILD_SUBREAPER,1,0,0,0)) { error=fs1_error(); goto done; }
    for (unsigned i=0;i<3;++i) {
        if (pipe2(pipes[i],O_CLOEXEC)) { error=fs1_error(); goto done; }
        streams[i].fd=pipes[i][0];
        if (pipes[i][0]<=2 || pipes[i][1]<=2 || fcntl(pipes[i][0],F_SETFL,O_NONBLOCK))
            { error=fs1_error(); goto done; }
    }
    pid_t parent=getpid(),group=getpgrp();
    up_attempted=1;
    pid=fork();
    if (pid<0) { error=fs1_error(); goto done; }
    if (!pid) up_child(root,endpoint,pipes,parent,group);
    for (unsigned i=0;i<3;++i) { (void)close(pipes[i][1]); pipes[i][1]=-1; }
    while (!error) {
        for (unsigned i=0;i<3 && !error;++i) error=up_drain(&streams[i]);
        for (unsigned i=0;i<32 && !error;++i) {
            int status=0; pid_t reaped=waitpid(-1,&status,WNOHANG);
            if (reaped==pid) { if (up_reaped) error=EPROTO; up_status=status; up_reaped=1; }
            else if (reaped>0) { ++up_adopted; continue; }
            else if (reaped==0) break;
            else if (errno==EINTR) continue;
            else if (errno==ECHILD) { up_settled=1; break; }
            else error=fs1_error();
        }
        if (error || (up_reaped && up_settled && streams[0].fd<0 && streams[1].fd<0 && streams[2].fd<0)) break;
        if ((error=up_time(&now))) break;
        unsigned limit=UP_TIMEOUT_MS;
#ifdef S22_USERSPACE_PROBE_FAULT
        limit=up_fault_timeout_ms;
#endif
        if (now-started>=limit) { error=ETIMEDOUT; break; }
        struct pollfd wait[3];
        for (unsigned i=0;i<3;++i) wait[i]=(struct pollfd){streams[i].fd,POLLIN|POLLHUP,0};
        if (poll(wait,3,50)<0 && errno!=EINTR) error=fs1_error();
    }
    if (streams[2].used==sizeof(struct up_packet) || streams[2].used==2*sizeof(struct up_packet)) {
        struct up_packet first,last;
        memcpy(&first,streams[2].bytes,sizeof(first));
        memcpy(&last,streams[2].bytes+streams[2].used-sizeof(last),sizeof(last));
        up_setup_stage=last.stage; up_setup_errno=last.error;
        if (!error && first.stage==UP_READY && !first.error && streams[2].used==sizeof(first) &&
            up_reaped && !up_adopted && up_settled && WIFEXITED(up_status) && WEXITSTATUS(up_status)==0 &&
            streams[0].used==sizeof(up_expected)-1 && !memcmp(streams[0].bytes,up_expected,sizeof(up_expected)-1) &&
            !streams[1].used) up_proved=1;
    } else if (!error) error=EPROTO; /* no READY/failure record: exec state is unknown */
done:
    /* On uncertainty the helper exits nonzero in the ORIGINAL command group.
     * The unchanged outer ACM supervisor kills/reaps the entire group; no
     * separate child group can escape its timeout or cancellation ownership. */
    for (unsigned i=0;i<3;++i) {
        if (streams[i].fd>=0 && close(streams[i].fd) && !error) error=fs1_error();
        if (pipes[i][1]>=0 && close(pipes[i][1]) && !error) error=fs1_error();
    }
    up_output("stdout",&streams[0]); up_output("stderr",&streams[1]);
    up_output("setup",&streams[2]);
    ri_print("UP1_CHILD attempted=%u reaped=%u adopted=%u settled=%u status=%d setup_stage=%u setup_errno=%u error=%d proved=%u\n",
        up_attempted,up_reaped,up_adopted,up_settled,up_status,up_setup_stage,up_setup_errno,error,up_proved&&!error);
    return error;
}

static int up_observe(int root, struct fs1_endpoint *endpoint, const struct ri_counts *counts,
                      const struct ri_compare *comparison, int started, int complete, int witness) {
    struct stat lost; struct statfs fs;
    bool eligible=started==1 && complete==1 && witness==1 && comparison->expected==ri_table_count &&
        comparison->matched==ri_table_count && !comparison->missing && !comparison->metadata && !comparison->content &&
        counts->entries==ri_table_count+4 && !counts->other &&
        !fstatat(root,"lost+found",&lost,AT_SYMLINK_NOFOLLOW) && lost.st_dev==endpoint->partition &&
        S_ISDIR(lost.st_mode) && (lost.st_mode&07777)==0700 && !lost.st_uid && !lost.st_gid;
    ri_print("UP1_ELIGIBLE exact=%u\n",eligible);
    if (!eligible) return 0;
    int error=up_execute(root,endpoint);
    if (!error && (fstatfs(root,&fs) ||
        (fs.f_flags&(ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC))!=(ST_RDONLY|ST_NOSUID|ST_NODEV|ST_NOEXEC) ||
        (error=ri_ro(endpoint,false)))) { if (!error) error=EPROTO; }
    if (!error) ri_print("UP1_PARENT readonly=1 noexec=1 partition_ro=1\n");
    up_error=error; return error;
}

int main(int argc, char **argv) {
    int result=ri_run(argc,argv,"probe",up_observe);
    ri_print("UP1_RESULT complete=%u attempted=%u proved=%u error=%d\n",!result,up_attempted,up_proved&&!result,up_error);
    return result;
}
