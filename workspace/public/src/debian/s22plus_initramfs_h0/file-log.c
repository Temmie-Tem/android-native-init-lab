/* One automatic, clean-root-only file pilot under Debian shell PID1.
 * No gadget, console command, installed code, repair, replay or reboot. */
#define _GNU_SOURCE
#include <sys/types.h>
static void fl_register_child(pid_t);
static int fl_finish_child(pid_t,unsigned);
#define UP_REGISTER_CHILD fl_register_child
#define UP_FINISH_CHILD fl_finish_child
#define S22_JOURNAL_CLEAN_ONLY
#define main unused_recovery_main
#include "s22plus_native_journal_recovery_v1.c"
#undef main
#include "early-seal.h"
#include "early-protocol.h"
static uint8_t log_bytes[EARLY_LIMIT],proof[176];
static size_t log_size;
#include "early-measure.h"

#define FL_MAXIMUM 16384U
#define FL_HEADER 256U
#define FL_RECORD 128U
#ifdef FL_STORAGE_FIRST
#include "file-first-plan.h"
#define FL_RECORDS (2U+FF_CLIENT_COUNT*2U)
#define FL_PHASES FF_CLIENT_COUNT
#define FL_MAGIC "S22FL02\0"
#define FL_RECORD_MAGIC "S22FLR2\0"
#define FL_VERSION 2U
#define FL_ACCESS O_RDWR
#else
#define FL_RECORDS 8U
#define FL_PHASES 3U
#define FL_MAGIC "S22FL01\0"
#define FL_RECORD_MAGIC "S22FLR1\0"
#define FL_VERSION 1U
#define FL_ACCESS O_WRONLY
#endif
static const char fl_root[]="/s22-root-work/file-root";
static struct fs1_endpoint fl_endpoint;
static int fl_admitted;
static uint8_t fl_previous[32];
static unsigned fl_sequence,fl_bytes;
static uint64_t fl_origin;
static pid_t fl_checker_pid;
static int fl_unsettled;

static uint64_t fl_now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_BOOTTIME,&t) || t.tv_sec<0)return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
static void fl_register_child(pid_t pid) {
    if(fl_checker_pid || pid<=1)_exit(120);
    fl_checker_pid=pid;
}
static int fl_finish_child(pid_t pid,unsigned reaped) {
    fl_unsettled=1;
    if(pid!=fl_checker_pid)return EPROTO;
    if(!reaped) {
        /* The shell PID1 shares our group. Only the registered checker may
         * be killed; never send a signal to that inherited process group. */
        if(kill(pid,SIGKILL) && errno!=ESRCH)return fs1_error();
        uint64_t start=fl_now();if(start==UINT64_MAX)return EIO;
        for(;;) {
            int status;pid_t got=waitpid(pid,&status,WNOHANG);
            if(got==pid)break;
            if(got<0 && errno!=EINTR)return fs1_error();
            uint64_t n=fl_now();if(n<start || n-start>=2000)return ETIMEDOUT;
            struct timespec delay={0,10000000};
            if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
        }
    }
    int status;pid_t remaining=waitpid(-1,&status,WNOHANG);
    if(remaining!=-1 || errno!=ECHILD)return ECHILD;
    ri_print("FILE_CHECKER_SETTLED owner_reaped=%u children=0\n",!reaped);
    fl_checker_pid=0;fl_unsettled=0;return 0;
}
static int fl_time(void) {
    uint64_t n=fl_now();return n<fl_origin || n>=300000 ? ETIMEDOUT:0;
}
static void fl_u64(uint8_t *p,uint64_t n) {for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(n>>(i*8));}
static int fl_admission(int root,struct fs1_endpoint *e,const struct ri_counts *counts,
        const struct ri_compare *comparison,int started,int complete,int witness) {
    int error=rj_observe(root,e,counts,comparison,started,complete,witness);
    if(error || !rj_root_match)return error?error:EPROTO;
    fl_endpoint=*e;fl_admitted=1;return 0;
}
static int fl_directory(int fd,dev_t device) {
    struct stat st;struct statfs fs;
    return fstat(fd,&st) || fstatfs(fd,&fs) || st.st_dev!=device ||
        st.st_mode!=(S_IFDIR|0755) || st.st_uid || st.st_gid || st.st_nlink<2 ||
        fs.f_type!=0xef53 || fs.f_bsize!=4096 || (fs.f_flags&ST_RDONLY) ||
        (fs.f_flags&(ST_NOSUID|ST_NODEV|ST_NOEXEC))!=(ST_NOSUID|ST_NODEV|ST_NOEXEC) ? EPROTO:0;
}
static int fl_parent(int root,dev_t device) {
    int fd=fcntl(root,F_DUPFD_CLOEXEC,3);if(fd<0)return -1;
    const char *parts[]={"var","lib","lab"};
    for(unsigned i=0;i<3;++i) {
        int error=fl_time(),made=0;
        if(!error && i==2) {
            mode_t old=umask(0);int rc=mkdirat(fd,parts[i],0755),saved=errno;umask(old);
            if(rc && saved!=EEXIST)error=saved;
            made=!rc;
        }
        int next=error?-1:openat(fd,parts[i],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if(!error)error=next<0?fs1_error():fl_directory(next,device);
        if(!error && made && (fsync(fd) || fsync(next)))error=fs1_error();
        if(close(fd) && !error)error=fs1_error();
        if(error){if(next>=0)(void)close(next);errno=error;return -1;}
        fd=next;
    }
    return fd;
}
/* One write and one checked sync per record. Short writes are consumed errors. */
static int fl_write(int fd,const void *data,size_t length) {
    int error=fl_time();if(error)return error;
    if(length>FL_MAXIMUM-fl_bytes)return EOVERFLOW;
    if(write(fd,data,length)!=(ssize_t)length || fsync(fd))return EIO;
#ifdef FL_STORAGE_FIRST
    uint8_t checked[1024];size_t at=0;
    while(at<length) {
        size_t n=length-at;if(n>sizeof(checked))n=sizeof(checked);
        if(pread(fd,checked,n,(off_t)fl_bytes+(off_t)at)!=(ssize_t)n ||
            memcmp(checked,(const uint8_t *)data+at,n))return EIO;
        at+=n;
    }
#endif
    fl_bytes+=(unsigned)length;return fl_time();
}
static int fl_record(int fd,unsigned kind,unsigned phase,int error_code) {
    if(fl_sequence>=FL_RECORDS)return EOVERFLOW;
    uint64_t n=fl_now();if(n<fl_origin || n-fl_origin>=300000)return ETIMEDOUT;
    uint8_t raw[FL_RECORD]={0};memcpy(raw,FL_RECORD_MAGIC,8);
    early_put32(raw+8,fl_sequence);early_put32(raw+12,kind);fl_u64(raw+16,n-fl_origin);
    early_put32(raw+24,phase);early_put32(raw+28,(uint32_t)error_code);
    memcpy(raw+64,fl_previous,32);early_tag(raw+96,proof+16,kind,fl_sequence,raw,96);
    int error=fl_write(fd,raw,sizeof(raw));if(error)return error;
    memcpy(fl_previous,raw+96,32);++fl_sequence;return 0;
}
#ifdef FL_STORAGE_FIRST
#include "file-first-clients.h"
#endif
static int fl_file(int root,dev_t device) {
    int parent=fl_parent(root,device);if(parent<0)return fs1_error();
    char name[64];snprintf(name,sizeof(name),"s22-evidence-%s",fs1_run_id);
    int late=fl_time();if(late){(void)close(parent);return late;}
    int fd=openat(parent,name,FL_ACCESS|O_CREAT|O_EXCL|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC,0600);
    int error=fd<0?fs1_error():0;struct stat st;
    if(!error && (fstat(fd,&st) || st.st_dev!=device || st.st_mode!=(S_IFREG|0600) ||
        st.st_uid || st.st_gid || st.st_nlink!=1 || st.st_size))error=EPROTO;
    if(!error && fsync(parent))error=fs1_error();
    uint8_t header[FL_HEADER]={0};memcpy(header,FL_MAGIC,8);
    early_put32(header+8,FL_VERSION);early_put32(header+12,FL_HEADER);memcpy(header+16,early_run,16);
    memcpy(header+32,proof,sizeof(proof));fl_u64(header+208,fl_origin);
    early_tag(header+224,proof+16,0,0,header,224);
    if(!error)error=fl_write(fd,header,sizeof(header));
    if(!error)error=fl_write(fd,log_bytes,log_size);
    memcpy(fl_previous,header+224,32);
    if(!error)error=fl_record(fd,1,0,0); /* Header and imported preparation synced. */
#ifdef FL_STORAGE_FIRST
    if(!error)error=fl_clients_check();
#endif
    for(unsigned phase=1;phase<=FL_PHASES && !error;++phase) {
        error=fl_record(fd,2,phase,0);
#ifdef FL_STORAGE_FIRST
        int observed=error ? error : fl_client(phase);
#else
        /* Fixed probe, no installed code and no USB prerequisite. */
        int observed=getppid()==1?0:EPROTO;
#endif
        if(!error)error=fl_record(fd,3,phase,observed);
        if(!error && observed)error=observed;
    }
    if(!error)error=fl_record(fd,4,0,0); /* Last in-file fact precedes unmount. */
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(close(parent) && !error)error=fs1_error();
    return error;
}
static int fl_write_mount(void) {
    struct fs1_endpoint e=fl_endpoint;e.node_fd=-1;e.node_created=e.disk_created=0;
    int error=0,root=-1;bool nodes=false,directory=false,mounted=false;
    if(fl_time() || mkdir("/dev/.s22-ext4-v1",0700))return EIO;
    nodes=true;e.node_fd=open("/dev/.s22-ext4-v1",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(e.node_fd<0){error=fs1_error();goto done;}
    if((error=fs1_make_node(&e,"native",e.partition,0600)) ||
       (error=fs1_make_node(&e,"lu0",e.disk,0400)) || (error=fs1_not_mounted(e.partition)) ||
       (error=ri_ro(&e,false)) || (error=fs1_gpt_exact(&e)) || (error=fs1_read_super(&e,false)))goto done;
    if(!fs1_superblock(e.superblock,1024,fs1_uuid,FS1_BLOCKS)){error=EPROTO;goto done;}
    if(mkdir(fl_root,0700)){error=fs1_error();goto done;}directory=true;
    if((error=fl_time()) || (error=rj_clear_ro(&e)))goto done;
    if((error=fl_time()))goto done;
    if(mount(fs1_node,fl_root,"ext4",MS_NOSUID|MS_NODEV|MS_NOEXEC,"nodiscard")){error=fs1_error();goto done;}
    mounted=true;root=open(fl_root,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(root<0){error=fs1_error();goto done;}
    if(!(error=fl_directory(root,e.partition)))error=fl_file(root,e.partition);
    if(close(root) && !error)error=fs1_error();
    root=-1;
done:
    if(root>=0 && close(root) && !error)error=fs1_error();
    /* Attempt each owned unmount once; never restore RO over an uncertain mount. */
    if(mounted) {
        if(umount2(fl_root,0)){if(!error)error=fs1_error();goto leave;}
        mounted=false;
    }
    if(e.node_fd>=0 && e.node_created) {
        int cleanup=ri_ro(&e,true);
        if(!cleanup)cleanup=fs1_not_mounted(e.partition);
        if(!cleanup)cleanup=fs1_read_super(&e,false);
        if(!cleanup && !fs1_superblock(e.superblock,1024,fs1_uuid,FS1_BLOCKS))cleanup=EPROTO;
        if(!cleanup)cleanup=fs1_gpt_exact(&e);
        if(!error)error=cleanup;
    }
leave:
    if(e.node_created && unlinkat(e.node_fd,"native",0) && !error)error=fs1_error();
    if(e.disk_created && unlinkat(e.node_fd,"lu0",0) && !error)error=fs1_error();
    if(e.node_fd>=0 && close(e.node_fd) && !error)error=fs1_error();
    if(nodes && rmdir("/dev/.s22-ext4-v1") && !error)error=fs1_error();
    if(directory && !mounted && rmdir(fl_root) && !error)error=fs1_error();
    return error;
}
int main(int argc,char **argv) {
    (void)argv;if(argc!=1)return 100;
    fl_origin=fl_now();if(fl_origin==UINT64_MAX || fl_time())return 101;
    int error=measure(0);
    if(error || log_size>FL_MAXIMUM-FL_HEADER-FL_RECORDS*FL_RECORD)return 102;
    if(fl_time())return 102;
    char *arguments[]={"file-admission","recover-journal",(char *)fs1_run_id,NULL};
    int result=ri_run(3,arguments,"recover-journal",fl_admission);
    if(rj_held>=0 && close(rj_held))result=1;
    rj_held=-1;
    /* Unknown child state remains owned here until physical recovery. It
     * never advances to a writable mount or gets reported as settled. */
    if(fl_unsettled)for(;;)pause();
    if(result || !fl_admitted || !rj_checker_complete || rj_attempted || rj_stopped)return 103;
    error=fl_write_mount();
#if defined(FL_STORAGE_FIRST) && defined(S22_ROOT_INSPECT_VIRT_TEST)
    dprintf(1,"FILE_VM_CLIENTS inserted=%u\n",fl_test_inserted);
#endif
    dprintf(1,"FILE_PILOT result=%s error=%d records=%u bytes=%u\n",error?"REJECTED":"CLOSED",error,fl_sequence,fl_bytes);
    return error?1:0;
}
