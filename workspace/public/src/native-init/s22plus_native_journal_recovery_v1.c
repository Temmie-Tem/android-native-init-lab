/* One separately sealed journal replay, followed by protected root admission.
 * No mount is writable and no installed executable or PID1 handoff is used. */
#define _GNU_SOURCE
#include <stdbool.h>
#include <stdint.h>
struct fs1_endpoint;
struct up_stream;
static unsigned rj_kind;
static int rj_admit(struct fs1_endpoint *,uint8_t [1024],int *,bool *);
static int rj_checker(struct fs1_endpoint *),rj_expected(const struct up_stream *);
static void rj_child(int,struct fs1_endpoint *,int [3][2],int,int);
#define S22_NATIVE_JOURNAL_RECOVERY
#define RI_PRE_ADMISSION(endpoint,before,clean,ro) rj_admit(endpoint,before,clean,ro)
#define RI_PRE_MOUNT(endpoint) rj_checker(endpoint)
#define UP_REPEAT_FIXED
#define UP_FIXED_CHILD rj_child
#define UP_FIXED_OUTPUT rj_expected
#define UP_TIMEOUT_MS 150000U
#define S22_USERSPACE_PROBE_LIBRARY
#ifdef S22_JOURNAL_RECOVERY_FAULT
#define S22_USERSPACE_PROBE_FAULT
#endif
#include "s22plus_native_userspace_probe_v1.c"
#include "s22plus_native_journal_recovery_seal_v1.h"

static unsigned rj_attempted,rj_writer_complete,rj_checker_complete,rj_root_match,rj_stopped;
static unsigned rj_valid,rj_stage,rj_complete;
static unsigned long long rj_writes,rj_bytes,rj_errno,rj_io_error;
static int rj_held=-1;

static void rj_child(int root,struct fs1_endpoint *endpoint,int pipes[3][2],int parent,int group) {
    (void)root;(void)endpoint;
    unsigned stage=1;int report=pipes[2][1],error=0;
    if(getppid()!=parent || getpgrp()!=group)up_child_fail(report,stage,EPROTO);
    int held=fcntl(rj_held,F_DUPFD_CLOEXEC,32),saved=fcntl(report,F_DUPFD_CLOEXEC,32),input[2];
    if(held<0 || saved<0 || pipe2(input,O_CLOEXEC) || close(input[1]))up_child_fail(report,stage,fs1_error());
    if(dup2(input[0],0)!=0 || dup2(pipes[0][1],1)!=1 || dup2(pipes[1][1],2)!=2 ||
       dup3(saved,3,O_CLOEXEC)!=3 || dup3(held,4,O_CLOEXEC)!=4 ||
       syscall(SYS_close_range,5U,UINT_MAX,0U))up_child_fail(3,stage,fs1_error());
    report=3;stage=5;
    if((error=up_limit(RLIMIT_CORE,0)) || (error=up_limit(RLIMIT_FSIZE,0)) ||
       (error=up_limit(RLIMIT_CPU,rj_kind==1 ? 120 : 25)) ||
       (error=up_limit(RLIMIT_AS,512U*1024U*1024U)) ||
       (error=up_limit(RLIMIT_NOFILE,64)) || (error=up_limit(RLIMIT_NPROC,16)))up_child_fail(report,stage,error);
    stage=6;
    struct __user_cap_header_struct header={_LINUX_CAPABILITY_VERSION_3,0};
    struct __user_cap_data_struct caps[2]={{0},{0}};
    if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) || prctl(PR_SET_KEEPCAPS,0,0,0,0) ||
       setgroups(0,NULL) || setresgid(0,0,0) || setresuid(0,0,0) ||
       syscall(SYS_capset,&header,caps))up_child_fail(report,stage,fs1_error());
    uid_t ru,eu,su;gid_t rg,eg,sg;stage=7;
    if(getresuid(&ru,&eu,&su) || getresgid(&rg,&eg,&sg) || ru || eu || su || rg || eg || sg ||
       getgroups(0,NULL) || syscall(SYS_capget,&header,caps) ||
       caps[0].effective || caps[0].permitted || caps[0].inheritable ||
       caps[1].effective || caps[1].permitted || caps[1].inheritable ||
       prctl(PR_GET_NO_NEW_PRIVS,0,0,0,0)!=1 || getppid()!=parent || getpgrp()!=group ||
       prctl(PR_SET_PDEATHSIG,SIGKILL,0,0,0) || getppid()!=parent)up_child_fail(report,stage,EPROTO);
#ifdef S22_JOURNAL_RECOVERY_FAULT
    if(rj_kind==rj_fault_kind && rj_fault_mode==1)up_child_fail(report,7,EPERM);
#endif
    up_packet(report,UP_READY,0);
#ifdef S22_JOURNAL_RECOVERY_FAULT
    if(rj_kind==rj_fault_kind) {
        if(rj_fault_mode==2)_exit(0);
        if(rj_fault_mode==3)for(;;)pause();
        if(rj_fault_mode==4){raise(SIGKILL);_exit(127);}
        if(rj_fault_mode==5){pid_t stray=fork();if(stray<0)up_child_fail(report,7,fs1_error());if(!stray)for(;;)pause();}
        if(rj_fault_mode==6){char data[4096];memset(data,'x',sizeof(data));for(unsigned i=0;i<3;++i)if(write(1,data,sizeof(data))!=(ssize_t)sizeof(data))_exit(5);_exit(0);}
        if(rj_fault_mode==7){dprintf(1,"S22_JOURNAL_REPLAY_V1 stage=5 writes=0 bytes=0 error=0 io_error=0 complete=1\n");_exit(0);}
    }
#endif
    char *writer[]={"s22-strict-replay",NULL};
    char *checker[]={"e2fsck","-fn",(char *)fs1_node,NULL};
    char *env[]={"PATH=/usr/sbin:/usr/bin:/sbin:/bin","LC_ALL=C","LANG=C","HOME=/nonexistent",NULL};
    fexecve(4,rj_kind==1 ? writer : checker,env);
    up_child_fail(report,UP_EXEC,fs1_error());
}

static int rj_contains(const struct up_stream *stream,const char *text) {
    size_t n=strlen(text);
    for(size_t i=0;i+n<=stream->used;++i)if(!memcmp(stream->bytes+i,text,n))return 1;
    return 0;
}
static int rj_expected(const struct up_stream *streams) {
    if(rj_kind==2) {
        for(unsigned i=1;i<=5;++i) {char pass[]="Pass 0:";pass[5]=(char)('0'+i);if(!rj_contains(streams,pass))return 0;}
        return rj_contains(streams+1,"e2fsck 1.47.2 (1-Jan-2025)\n");
    }
    if(streams[1].used || streams[0].used>=512)return 0;
    char actual[512],canonical[512];
    memcpy(actual,streams[0].bytes,streams[0].used);actual[streams[0].used]=0;
    if(sscanf(actual,"S22_JOURNAL_REPLAY_V1 stage=%u writes=%llu bytes=%llu error=%llu io_error=%llu complete=%u",
        &rj_stage,&rj_writes,&rj_bytes,&rj_errno,&rj_io_error,&rj_complete)!=6 ||
       rj_stage>5 || rj_writes>262146 || rj_bytes>rj_writes*4096ULL || rj_complete>1 ||
       rj_complete!=(!rj_errno && !rj_io_error && rj_stage==5))return 0;
    if(rj_complete) {
        if(rj_writes<2 || rj_bytes!=(rj_writes-1)*4096ULL+1024)return 0;
    } else if(!rj_errno || (!rj_io_error && (rj_stage>3 || rj_bytes!=rj_writes*4096ULL ||
               (rj_stage<2 && rj_writes))))return 0;
    int length=snprintf(canonical,sizeof(canonical),
        "S22_JOURNAL_REPLAY_V1 stage=%u writes=%llu bytes=%llu error=%llu io_error=%llu complete=%u\n",
        rj_stage,rj_writes,rj_bytes,rj_errno,rj_io_error,rj_complete);
    if(length<0 || (size_t)length!=streams[0].used || memcmp(actual,canonical,(size_t)length))return 0;
    rj_valid=1;return rj_complete;
}

static int rj_execute(unsigned kind,struct fs1_endpoint *endpoint) {
    rj_kind=kind;
    int error=up_execute(-1,endpoint);
    if(close(rj_held) && !error)error=fs1_error();
    rj_held=-1;
    if(error || !up_reaped || !up_settled || up_adopted || up_setup_stage!=UP_READY || up_setup_errno ||
       !WIFEXITED(up_status))return error ? error : EPROTO;
    if(kind==1) {
        if(!rj_valid || WEXITSTATUS(up_status)!=(rj_complete ? 0 : 8))return EPROTO;
        rj_writer_complete=rj_complete;
    } else rj_checker_complete=up_proved;
    return 0;
}

static int rj_clear_ro(struct fs1_endpoint *endpoint) {
    int error=ri_ro(endpoint,false);
    if(error || (error=fs1_not_mounted(endpoint->partition)) || (error=fs1_gpt_exact(endpoint)))return error;
    int fd=fs1_open_block(fs1_node,endpoint->partition,FS1_BYTES);
    if(fd<0)return fs1_error();
    int value=0,actual=-1;
    if(ioctl(fd,BLKROSET,&value))error=fs1_error();
    if(!error && (ioctl(fd,BLKROGET,&actual) || actual))error=EPROTO;
    uint64_t ro=1;
    if(!error && (fs1_number(endpoint->sys_partition,"ro",&ro) || ro))error=EPROTO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}

static int rj_admit(struct fs1_endpoint *e,uint8_t before[1024],int *clean,bool *ro) {
    uint8_t digest[32];char hex[65];
    struct s22plus_max77705_runtime_sha256 hash;s22plus_max77705_runtime_sha256_init(&hash);
    s22plus_max77705_runtime_sha256_update(&hash,before,1024);s22plus_max77705_runtime_sha256_final(&hash,digest);
    ri_digest(digest,hex);ri_print("JR1_BEFORE sha256=%s\n",hex);
    if(*clean) {ri_print("JR1_SKIP clean=1\n");return 0;}
#ifdef S22_JOURNAL_CLEAN_ONLY
    /* The separately compiled file pilot has no replay admission. */
    (void)e;(void)ro;rj_stopped=1;ri_print("JR1_SKIP clean=0\n");return -1;
#else
    if(fs1_u16(before+0x3a)!=1 || !(fs1_u32(before+0x60)&4U) || fs1_u32(before+0xe8)) {
        rj_stopped=1;ri_print("JR1_SKIP clean=0\n");return -1;
    }
    rj_held=fs1_pin_file("/s22-journal-replay",rj_replayer_size,rj_replayer_sha256,true);
    if(rj_held<0)return fs1_error();
    if(fchmodat(e->node_fd,"native",0600,0))return fs1_error();
    /* Declare the one-shot clear before calling it; no retry on uncertain ioctl. */
    *ro=false;
    int error=rj_clear_ro(e);
    if(error)return error;
    ri_print("JR1_BLOCK_RW partition=1\n");rj_attempted=1;
    error=rj_execute(1,e);
    /* Unknown or still-running child state belongs to the outer group owner.
     * Do not claim that a RO ioctl stopped a possibly outstanding writer. */
    if(error)return error;
    if((error=ri_ro(e,true)))return error;
    *ro=true;
    if(fchmodat(e->node_fd,"native",0400,0))return fs1_error();
    ri_print("JR1_BLOCK_RO partition=1 settled=1\n");
    if(rj_io_error)return EIO;
    if((error=fs1_read_super(e,false)) || (error=ri_super_identity(e->superblock)))return error;
    memcpy(before,e->superblock,1024);
    *clean=fs1_superblock(before,1024,fs1_uuid,FS1_BLOCKS);
    ri_print("JR1_AFTER clean=%d state=%u recover=%u orphan=%u\n",*clean,
             fs1_u16(before+0x3a),!!(fs1_u32(before+0x60)&4U),fs1_u32(before+0xe8));
    if(!rj_writer_complete || !*clean) {rj_stopped=1;return -1;}
    return 0;
#endif
}

static int rj_checker(struct fs1_endpoint *e) {
    struct stat config;
    if(!lstat("/etc/e2fsck.conf",&config) || errno!=ENOENT)return EPROTO;
    rj_held=fs1_pin_file(fs1_checker,fs1_checker_size,fs1_checker_sha256,true);
    if(rj_held<0)return fs1_error();
    ri_print("JR1_CHECKER begin=1\n");
    int error=rj_execute(2,e);
    if(error)return error;
    if(!rj_checker_complete){rj_stopped=1;return -1;}
    return 0;
}

static int rj_observe(int root,struct fs1_endpoint *e,const struct ri_counts *counts,
                      const struct ri_compare *comparison,int started,int complete,int witness) {
    struct stat lost;unsigned extra=0;
    int error=dh_root_extras(root,e->partition,&extra);
    if(error)return error;
    rj_root_match=started==1 && complete==1 && witness==1 && comparison->expected==ri_table_count &&
        comparison->matched==ri_table_count && !comparison->missing && !comparison->metadata && !comparison->content &&
        counts->entries==ri_table_count+4+extra && !counts->other &&
        !fstatat(root,"lost+found",&lost,AT_SYMLINK_NOFOLLOW) && lost.st_dev==e->partition &&
        S_ISDIR(lost.st_mode) && (lost.st_mode&07777)==0700 && !lost.st_uid && !lost.st_gid &&
        !fs1_empty_directory("/s22-root-work/root-inspect-v1/root/lost+found");
    if(!rj_root_match)rj_stopped=1;
    ri_print("JR1_ROOT exact=%u extra=%u\n",rj_root_match,extra);
    return 0;
}

int main(int argc,char **argv) {
    int result=ri_run(argc,argv,"recover-journal",rj_observe);
    if(rj_held>=0 && close(rj_held))result=1;
    ri_print("JR1_RESULT complete=%u attempted=%u writer_complete=%u checker_complete=%u root_match=%u stopped=%u io_error=%llu\n",
        !result,rj_attempted,rj_writer_complete,rj_checker_complete,rj_root_match,rj_stopped,rj_io_error);
    return result;
}
