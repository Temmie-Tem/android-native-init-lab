/* Diskless generic ARM64 component fixture. Uses the actual selected runtime,
 * sockets, descriptor cleanup and logger. Deadline/budget limits are explicit
 * fixture inputs; no Samsung watchdog or physical device behavior is modeled. */
#define _GNU_SOURCE
#include <assert.h>
#include <sys/reboot.h>
#include <sys/mount.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define main script_unused_hook_main
#include "s22plus_debian_handoff_hook_v1.c"
#undef main
static void demand(int yes,const char *why) {
    if(!yes){dprintf(2,"SCRIPT_VM_FAIL %s errno=%d\n",why,errno);_exit(99);}
}
static void directory(const char *path){demand(!mkdir(path,0755) || errno==EEXIST,path);}
static void packet(unsigned sequence,char kind,unsigned id,unsigned status) {
    char text[80];int n=snprintf(text,sizeof(text),"%u %c %u %u\n",sequence,kind,id,status);
    demand(write(3,text,(size_t)n)==n,"packet-send");
}
static void sender(const char *mode) {
    demand(ap_child_channel()==1,"real-nonblocking-channel");
    demand(!syscall(SYS_close_range,4U,UINT_MAX,0U),"close-inherited-endpoints");
    demand(fcntl(4,F_GETFD)==-1 && errno==EBADF,"extra-fd-absent");
    if(!strcmp(mode,"zero")){demand(write(3,"",0)==0,"zero-send");return;}
    if(!strcmp(mode,"truncated")) {
        char text[100];memset(text,'x',sizeof(text));demand(write(3,text,sizeof(text))==sizeof(text),"large-send");return;
    }
    if(!strcmp(mode,"gap")){packet(2,'B',1,0);return;}
    if(!strcmp(mode,"wrong-order")){packet(1,'D',0,0);packet(2,'E',1,0);return;}
    if(!strcmp(mode,"full-queue")) {
        unsigned sent=0;while(write(3,"1 D 0 0\n",8)==8 && ++sent<10000){}
        demand(sent>0 && sent<10000 && errno==EAGAIN,"bounded-nonblocking-full");return;
    }
    packet(1,'D',0,0);
    for(unsigned id=1;id<=16;++id) {
        packet(id*2,'B',id,0);packet(id*2+1,'E',id,id==8?23:0);
    }
    packet(34,'X',0,0);
}
static void owner(const char *mode) {
    at_actor=6;sw.deadline_ms=300000;memcpy(sw.run,sw_run,16);
    memset(sw.nonce,0xa5,sizeof(sw.nonce));demand(!sw_boot(sw.boot),"boot-binding");
    if(!strcmp(mode,"late")) {
        struct timespec delay={16,0};demand(!nanosleep(&delay,NULL),"late-real-clock");
    }
    if(!strcmp(mode,"setup-failure")) {
        int fd=open(AP_DISPATCHER,O_WRONLY|O_CREAT|O_EXCL,0500);demand(fd>=0 && !close(fd),"existing-dispatcher");
    }
    if(!strcmp(mode,"noexec"))demand(!mount(NULL,"/run",NULL,MS_REMOUNT|MS_NOEXEC|MS_NOSUID|MS_NODEV,NULL),"noexec-remount");
    if(!strcmp(mode,"absolute-clip"))sw.deadline_ms=at_now()+500;
    ap_start();
    if(!strcmp(mode,"setup-failure") || !strcmp(mode,"noexec")) {
        demand(ap.terminal && ap_send==-1 && ap_receive==-1,"setup-fallback");return;
    }
    demand(ap.started && !ap.terminal && ap_send>=10 && ap_receive>=10,"started");
    demand(ap.window_end==((ap.started_ms+120000<sw.deadline_ms)?ap.started_ms+120000:sw.deadline_ms),"relative-window-clipped");
    demand(fcntl(3,F_GETFD)==-1 && errno==EBADF,"parent-fd3-absent");
    if(!strcmp(mode,"late"))demand(ap.started_ms>=16000,"after-old-cutoff");
    if(!strcmp(mode,"actor-budget")) {
        at_spent=2000-AP_ACTOR_RESERVE_MS;ap_tick();ap_tick();
        demand(ap.terminal && ap_send==-1 && ap_receive==-1 && at_spent<2000,"budget-reserve-closed");
        unsigned sequence=at_sequence;AT_POINT(AT_RCS_COMPLETE,0,0);
        demand(at_sequence==sequence+1,"reserved-logger-remains-usable");return;
    }
    if(!strcmp(mode,"absolute-clip")) {
        struct timespec delay={0,600000000};demand(!nanosleep(&delay,NULL),"deadline-wait");ap_tick();
        demand(ap.terminal && ap_send==-1 && ap_receive==-1,"absolute-deadline-closed");return;
    }
    if(!strcmp(mode,"parent-progress") || !strcmp(mode,"logger-loss")) {
        if(!strcmp(mode,"logger-loss"))at_disabled=1;
        for(unsigned i=0;i<5;++i){struct timespec delay={0,250000000};demand(!nanosleep(&delay,NULL),"progress-wait");ap_tick();}
        if(!strcmp(mode,"logger-loss")) {
            demand(ap.terminal && ap.flags&AP_LOG && ap_receive==-1 && ap_send==-1,"logger-loss-closed");return;
        }
        demand(ap.parent_records==2 && !ap.terminal,"sparse-parent-progress");
    }
    pid_t child=fork();demand(child>=0,"sender-fork");
    if(!child){sender(mode);_exit(0);}
    ap_parent_fork();demand(ap_send==-1,"parent-send-closed");
    /* Queue capacity is deliberately tested before any receive. */
    int status;demand(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status),"sender-reaped");
    ap_reaped();demand(ap.terminal && ap_receive==-1 && ap_send==-1,"reap-closed");
    if(!strcmp(mode,"normal") || !strcmp(mode,"late") || !strcmp(mode,"parent-progress"))
        demand(ap.packets==34 && ap.script_done && !ap.script_open && !ap.flags,"complete-status-preserved");
    else demand(ap.flags&AP_CHANNEL,"malformed-channel-loss");
    unsigned packets=ap.packets;ap_tick();ap_reaped();ap_start();
    demand(ap.packets==packets && ap_receive==-1 && ap_send==-1,"terminal-not-reopened");
    dprintf(1,"SCRIPT_VM_CHANNEL packets=%u flags=%u started_ms=%llu\n",ap.packets,ap.flags,(unsigned long long)ap.started_ms);
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc==2){owner(argv[1]);return 0;}
    for(const char **p=(const char *[]){"/proc","/sys","/dev","/run",NULL};*p;++p)directory(*p);
    demand(!mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"proc");
    demand(!mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"sysfs");
    demand(!mount("devtmpfs","/dev","devtmpfs",MS_NOSUID,NULL),"devtmpfs");
    demand(!chmod("/dev/kmsg",0600),"logger-mode");
    demand(!mount("tmpfs","/run","tmpfs",MS_NOSUID|MS_NODEV,"mode=0755,size=2m"),"ram-root");
    directory("/run/s22-debian");
    char mode[64]="normal",cmdline[2048];demand(!fs1_read_text("/proc/cmdline",cmdline,sizeof(cmdline)),"cmdline");
    char *selected=strstr(cmdline,"script_case=");if(selected)demand(sscanf(selected,"script_case=%63s",mode)==1,"case");
    pid_t child=fork();demand(child>=0,"owner-fork");
    if(!child){char *args[]={"/init",mode,NULL};execv(args[0],args);_exit(98);}
    int status;demand(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status),"owner-result");
    dprintf(1,"SCRIPT_VM_PASS case=%s scope=GENERIC_ARM64_COMPONENT_ONLY\n",mode);
    sync();reboot(RB_POWER_OFF);return 0;
}
