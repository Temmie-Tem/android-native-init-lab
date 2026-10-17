/* One protected mountless read, with the original inspection owner/cleanup.
 * The pre-admission hook always skips the old clean-only mount branch. */
#define _GNU_SOURCE
#include <stdbool.h>
#include <stdint.h>
#include "s22plus_native_evidence_seal_v1.h"
struct fs1_endpoint;
struct up_stream;
static int ne_admit(struct fs1_endpoint *,uint8_t [1024],int *,bool *);
static int ne_expected(const struct up_stream *);
static void ne_child(int,struct fs1_endpoint *,int [3][2],int,int);
#define RI_PRE_ADMISSION(endpoint,before,clean,ro) ne_admit(endpoint,before,clean,ro)
#define UP_FIXED_CHILD ne_child
#define UP_FIXED_OUTPUT ne_expected
#define UP_OUTPUT_MAX NE_LIMIT
#define UP_TIMEOUT_MS 60000U
#define S22_USERSPACE_PROBE_LIBRARY
#include "s22plus_native_userspace_probe_v1.c"
#include "s22plus_native_evidence_reader_v1.inc.c"
static int ne_device=-1;

static void ne_child(int root,struct fs1_endpoint *endpoint,int pipes[3][2],int parent,int group) {
    (void)root;(void)endpoint;int report=pipes[2][1],error=0;
    if(getppid()!=parent || getpgrp()!=group)up_child_fail(report,1,EPROTO);
    int disk=fcntl(ne_device,F_DUPFD_CLOEXEC,32),saved=fcntl(report,F_DUPFD_CLOEXEC,32),input[2];
    if(disk<0 || saved<0 || pipe2(input,O_CLOEXEC) || close(input[1]))up_child_fail(report,2,fs1_error());
    if(dup2(input[0],0)!=0 || dup2(pipes[0][1],1)!=1 || dup2(pipes[1][1],2)!=2 ||
       dup3(disk,3,O_CLOEXEC)!=3 || dup3(saved,4,O_CLOEXEC)!=4 ||
       syscall(SYS_close_range,5U,UINT_MAX,0U))up_child_fail(report,3,fs1_error());
    report=4;
    if((error=up_limit(RLIMIT_CORE,0)) || (error=up_limit(RLIMIT_FSIZE,0)) ||
       (error=up_limit(RLIMIT_CPU,30)) || (error=up_limit(RLIMIT_AS,96U*1024U*1024U)) ||
       (error=up_limit(RLIMIT_NOFILE,16)) || (error=up_limit(RLIMIT_NPROC,0)))up_child_fail(report,5,error);
    if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) || prctl(PR_SET_KEEPCAPS,0,0,0,0) || setgroups(0,NULL) ||
       setresgid(65534,65534,65534) || setresuid(65534,65534,65534))up_child_fail(report,6,fs1_error());
    uid_t ru,eu,su;gid_t rg,eg,sg;
    struct __user_cap_header_struct h={_LINUX_CAPABILITY_VERSION_3,0};
    struct __user_cap_data_struct caps[2]={{0},{0}};
    if(getresuid(&ru,&eu,&su) || getresgid(&rg,&eg,&sg) || ru!=65534 || eu!=65534 || su!=65534 ||
       rg!=65534 || eg!=65534 || sg!=65534 || getgroups(0,NULL) || syscall(SYS_capget,&h,caps) ||
       caps[0].effective || caps[0].permitted || caps[0].inheritable ||
       caps[1].effective || caps[1].permitted || caps[1].inheritable ||
       prctl(PR_GET_NO_NEW_PRIVS,0,0,0,0)!=1 || prctl(PR_SET_PDEATHSIG,SIGKILL,0,0,0) ||
       getppid()!=parent || getpgrp()!=group)up_child_fail(report,7,EPROTO);
    up_packet(report,UP_READY,0);if(close(report))_exit(125);
    _exit(ne_read_files() ? 126 : 0);
}
static int ne_expected(const struct up_stream *s) {
    return !s[1].used && s[0].used>=64 && s[0].used<=NE_LIMIT &&
        !memcmp(s[0].bytes,"S22NE01\0",8) && !memcmp(s[0].bytes+s[0].used-32,"S22NEND\0",8) &&
        fs1_u32(s[0].bytes+s[0].used-8)==s[0].used && !fs1_u32(s[0].bytes+s[0].used-12);
}
static int ne_admit(struct fs1_endpoint *e,uint8_t before[1024],int *clean,bool *ro) {
    (void)before;(void)clean;if(!*ro)return EPROTO;
    int error=ri_ro(e,false);if(error)return error;
    ne_device=fs1_open_block(fs1_node,e->partition,FS1_BYTES);if(ne_device<0)return fs1_error();
    ri_print("NE1_READ mount=0 replay=0 output_max=%u\n",NE_LIMIT);
    error=up_execute(-1,e);
    if(close(ne_device) && !error)error=fs1_error();
    ne_device=-1;
    if(error || !up_proved || !up_reaped || !up_settled || up_adopted)return error ? error : EPROTO;
    return -1; /* Always skip mount, including when the filesystem is clean. */
}
int main(int argc,char **argv) {return ri_run(argc,argv,"evidence",NULL);}
