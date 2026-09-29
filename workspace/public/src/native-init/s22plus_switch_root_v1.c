/* One fixed readonly root transition, entered by exec of actual native PID1.
 * Its only executable destinations are the pinned BusyBox and RAM witness.
 */
#define _GNU_SOURCE
#include <stdarg.h>
#include <sys/types.h>
static void sw_log(const char *,va_list);
static void sw_register_child(pid_t);
static int sw_finish_child(pid_t,unsigned);
#define RI_PRINT_SINK sw_log
#define UP_REGISTER_CHILD sw_register_child
#define UP_FINISH_CHILD sw_finish_child
#define main sw_unused_staged_main
#include "s22plus_native_staged_preflight_v1.c"
#undef main
#include "s22plus_switch_root_common_v1.inc.c"
#include "s22plus_switch_root_payload_v1.h"
#ifndef S22_SWITCH_ROOT_FAULT
#define S22_SWITCH_ROOT_FAULT 0
#elif !defined(S22_ROOT_INSPECT_VIRT_TEST)
#error "Switch-root fault injection requires virtual discovery"
#endif

static pid_t sw_checker_pid;
static void sw_register_child(pid_t pid) { if(sw_checker_pid || pid<=1)sw_stop(EPROTO);sw_checker_pid=pid; }
static int sw_finish_child(pid_t pid,unsigned reaped) {
    if(pid!=sw_checker_pid)return EPROTO;
    sw_checker_pid=0;
    if(!reaped) {
        /* The old generic child runner had an outer supervisor. Here PID1
         * owns exact-child failure settlement before it can assert any proof. */
        if(kill(pid,SIGKILL) && errno!=ESRCH)return fs1_error();
        uint64_t end=sw_now()+SW_SETTLE_MS;int status;
        for(;;) {
            pid_t got=waitpid(pid,&status,WNOHANG);
            if(got==pid)break;
            if(got<0 && errno!=EINTR)return fs1_error();
            if(sw_now()>=end || sw_now()>=sw.deadline_ms)return ETIMEDOUT;
            struct timespec delay={0,10000000};if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
        }
    }
    return sw_no_children();
}
static int sw_workers(void) {
    unsigned pending=0;
    for(unsigned i=0;i<3;++i) {
        struct sw_child_state *child=&sw.child[i];
        if(child->pid<=1 || child->unknown || (child->reaped!=0 && child->reaped!=1))return EPROTO;
        for(unsigned j=0;j<i;++j)if(child->pid==sw.child[j].pid)return EPROTO;
        if(child->reaped)continue;
        pid_t got=waitpid(child->pid,&child->status,WNOHANG);
        if(got==child->pid){child->reaped=1;continue;}
        if(got<0)return fs1_error();
        if(kill(child->pid,SIGKILL) && errno!=ESRCH)return fs1_error();
        ++pending;
    }
    uint64_t end=sw_now()+SW_SETTLE_MS;
    while(pending) {
        for(unsigned i=0;i<3;++i) {
            struct sw_child_state *child=&sw.child[i];if(child->reaped)continue;
            pid_t got=waitpid(child->pid,&child->status,WNOHANG);
            if(got==child->pid){child->reaped=1;--pending;}
            else if(got<0 && errno!=EINTR)return fs1_error();
        }
        if(!pending)break;
        if(sw_now()>=end || sw_now()>=sw.deadline_ms)return ETIMEDOUT;
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
    }
    int error=sw_no_children();if(!error)error=sw_userspace();return error;
}
static int sw_copy_witness(void) {
    int input=fs1_pin_file("/s22-switch-witness",sw_witness_size,sw_witness_sha256,true);
    if(input<0)return fs1_error();
    int output=open("/s22-handoff-run/s22-witness",O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0500);
    int error=output<0 ? fs1_error() : 0;
    uint8_t bytes[65536];uint64_t copied=0;
    while(!error && copied<sw_witness_size) {
        size_t count=sw_witness_size-copied;if(count>sizeof(bytes))count=sizeof(bytes);
        ssize_t n=read(input,bytes,count);
        if(n!=(ssize_t)count){error=EIO;break;}
        if(write(output,bytes,count)!=(ssize_t)count){error=EIO;break;}
        copied+=count;
    }
    if(output>=0 && close(output) && !error)error=fs1_error();
    if(close(input) && !error)error=fs1_error();
    if(!error) {
        int fd=fs1_pin_file("/s22-handoff-run/s22-witness",sw_witness_size,sw_witness_sha256,true);
        struct statfs fs;
        if(fd<0)error=fs1_error();
        else {
            if(fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
               (fs.f_flags&(ST_NOEXEC|ST_NODEV|ST_NOSUID))!=(ST_NODEV|ST_NOSUID))error=EPROTO;
            if(close(fd) && !error)error=fs1_error();
        }
    }
    return error;
}
static int sw_root_eligible(int root,struct fs1_endpoint *e,const struct ri_counts *counts,
                            const struct ri_compare *comparison,int started,int complete,int witness) {
    struct stat st;
    if(started!=1 || complete!=1 || witness!=1 || comparison->expected!=ri_table_count ||
       comparison->matched!=ri_table_count || comparison->missing || comparison->metadata || comparison->content ||
       counts->entries!=ri_table_count+4 || counts->other ||
       fstatat(root,"lost+found",&st,AT_SYMLINK_NOFOLLOW) || st.st_dev!=e->partition ||
       !S_ISDIR(st.st_mode) || (st.st_mode&07777)!=0700 || st.st_uid || st.st_gid ||
       fs1_empty_directory("/s22-root-work/root-inspect-v1/root/lost+found"))return EPROTO;
    const char *directories[]={"dev","proc","sys","run"};
    for(unsigned i=0;i<4;++i) {
        if(fstatat(root,directories[i],&st,AT_SYMLINK_NOFOLLOW) || !S_ISDIR(st.st_mode) ||
           st.st_dev!=e->partition || st.st_uid || st.st_gid || (st.st_mode&022))return EPROTO;
    }
    return 0;
}
static void sw_move(const char *from,const char *to) {
#if S22_SWITCH_ROOT_FAULT == 2
    to="/missing-move-destination";
#endif
    if(mount(from,to,NULL,MS_MOVE,NULL))sw_stop(fs1_error());
}
static int sw_next(int root,struct fs1_endpoint *e,const struct ri_counts *counts,
                   const struct ri_compare *comparison,int started,int complete,int witness) {
    int error=sw_root_eligible(root,e,counts,comparison,started,complete,witness);if(error)return error;
    sw.root_admitted=1;sw.root_device=(uint64_t)e->partition;
    sw_require(sw_record(SW_ROOT,0,"exact-root-checker",18));
    sw_require(sw_userspace());sw_require(sw_no_children());sw_require(ri_ro(e,false));
    uint8_t before[1024];memcpy(before,e->superblock,sizeof(before));
    sw_require(fs1_read_super(e,true));
    if(memcmp(before,e->superblock,sizeof(before)))sw_stop(EPROTO);
    sw_require(fs1_gpt_exact(e));
    sw_require(sw_record(SW_STORAGE,0,"protected-after-retirement",26));
    struct stat old;struct statfs oldfs;
    if(stat("/",&old) || statfs("/",&oldfs) || old.st_dev==e->partition ||
       (oldfs.f_type!=0x858458f6L && oldfs.f_type!=0x01021994L) ||
       lstat("/init",&old) || !S_ISREG(old.st_mode))sw_stop(EPROTO);
    if(stat("/",&old))sw_stop(fs1_error());
    sw.old_device=(uint64_t)old.st_dev;
    struct sw_mount mounts[SW_MAX_MOUNTS]={0};unsigned count=0;
    sw_require(sw_mounts(mounts,&count,NULL));
    for(unsigned i=0;i<count;++i)sw_require(sw_mount_allowed(mounts+i,0));
    if(mkdir("/newroot",0700) || mkdir("/s22-handoff-run",0700) ||
       mount("tmpfs","/s22-handoff-run","tmpfs",MS_NOSUID|MS_NODEV|
           (S22_SWITCH_ROOT_FAULT==1 ? MS_NOEXEC : 0),"size=8m,nr_inodes=64,mode=0700") ||
       mkdir("/s22-handoff-run/config",0700))sw_stop(fs1_error());
    sw_require(sw_copy_witness());memcpy(sw.witness_digest,sw_witness_sha256,32);
    int busybox=fs1_pin_file("/s22-switch-busybox",sw_busybox_size,sw_busybox_sha256,true);
    if(busybox<0)sw_stop(fs1_error());
    if(close(busybox))sw_stop(fs1_error());
    sw_require(sw_record(SW_MOUNTS,0,"fixed-ram-witness",17));
    /* From this point a failure parks. It never falls through ri_run's old
     * cleanup paths after the namespace or descriptor set has changed. */
    sw_move(ri_root,"/newroot");
    sw_move("/s22-handoff-run","/newroot/run");
    sw_move("/config","/newroot/run/config");
    sw_move("/dev","/newroot/dev");
    sw_move("/sys","/newroot/sys");
    sw_move("/proc","/newroot/proc");
    if(chdir("/") || syscall(SYS_close_range,5U,UINT_MAX,0U) ||
       umount2("/run",0) || umount2("/s22-root-work",0))sw_stop(fs1_error());
    sw_mountinfo="/newroot/proc/self/mountinfo";
    memset(mounts,0,sizeof(mounts));sw_require(sw_mounts(mounts,&count,"/newroot"));
    if(count<6)sw_stop(EPROTO);
    for(unsigned i=0;i<count;++i){sw_require(sw_mount_allowed(mounts+i,1));sw.mount_ids[i]=mounts[i].id;}
    sw.mount_count=count;sw_mount_hash(mounts,count,sw.mount_digest);
    sw_require(sw_record(SW_MOVE,0,"mounts-moved-work-unmounted",27));
    sw_require(sw_record(SW_EXEC,0,"busybox-switch-root",19));
    sw_require(sw_save_state());
#if S22_SWITCH_ROOT_FAULT == 3
    if(unlink("/newroot/run/s22-witness"))sw_stop(fs1_error());
#endif
    char *args[]={"busybox","switch_root","/newroot","/run/s22-witness",NULL};
    char *env[]={"PATH=/usr/sbin:/usr/bin:/sbin:/bin","LC_ALL=C",NULL};
    execve("/s22-switch-busybox",args,env);sw_stop(fs1_error());
}
int main(int argc,char **argv) {
    (void)argv;
    if(getpid()!=1)return 111;
    sw_require(argc==1 ? sw_load_state() : EINVAL);
    struct stat tty;if(fstat(3,&tty))sw_stop(fs1_error());sw.tty_device=(uint64_t)tty.st_rdev;
    sw_require(sw_fd_whitelist(1));sw_require(sw_record(SW_ENTER,0,"actual-pid1",11));
    sw_require(sw_workers());sw.settled=1;
    sw_require(sw_record(SW_WORKERS,0,"three-workers-reaped",20));
    char *args[]={"/s22-switch-root","staged",(char *)fs1_run_id,NULL};
    int result=ri_run(3,args,"staged",sw_next);
    /* A dirty/mismatched root and every failed preparation remain no-proof.
     * An empty successful inspector result cannot imply a root transition. */
    sw_stop(result ? EIO : EPROTO);
}
