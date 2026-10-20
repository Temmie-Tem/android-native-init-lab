/* Diskless generic ARM64 H0 fixture. The generated adapter uses only the
 * retained dummy_hcd entry/post-BL sites, never a physical watchdog module. */
#define _GNU_SOURCE
#include <assert.h>
#include <sys/reboot.h>
#include <sys/mount.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static unsigned vm_control_writes,vm_fail_write;
static unsigned vm_apply_failure,vm_applied_failures;
static unsigned vm_frame_mode,vm_frame_offset,vm_frame_fd,vm_frame_reads;
static unsigned vm_registry_failure;
static char vm_frame[4096];
static ssize_t vm_write(int fd,const void *bytes,size_t size);
static ssize_t vm_read(int fd,void *bytes,size_t size);
#define write vm_write
#define read vm_read
#define main phase_unused_hook_main
#include "s22plus_debian_handoff_hook_v1.c"
#undef main
#undef write
#undef read
static ssize_t vm_read(int fd,void *bytes,size_t size) {
    if(vm_frame_mode || vm_registry_failure) {
        char path[64],target[256];snprintf(path,sizeof(path),"/proc/self/fd/%d",fd);
        ssize_t n=readlink(path,target,sizeof(target)-1);
        if(n>0) {
            target[n]=0;
            if(vm_registry_failure && !strcmp(target,AP_ROOT "/kprobe_events")) {
                errno=EIO;return -1;
            }
            if(vm_frame_mode && !strcmp(target,AP_INSTANCE "/trace_pipe")) {
                if(vm_frame_reads && vm_frame_fd!=(unsigned)fd){errno=EIO;return -1;}
                vm_frame_fd=(unsigned)fd;++vm_frame_reads;
                if(vm_frame_offset==sizeof(vm_frame)){errno=EAGAIN;return -1;}
                size_t count=vm_frame_offset ? 1 : 4095;
                if(count>size)count=size;
                memcpy(bytes,vm_frame+vm_frame_offset,count);vm_frame_offset+=(unsigned)count;
                return (ssize_t)count;
            }
        }
    }
    return read(fd,bytes,size);
}
static ssize_t vm_write(int fd,const void *bytes,size_t size) {
    struct statfs fs;
    if(!fstatfs(fd,&fs) && fs.f_type==AP_TRACEFS) {
        ++vm_control_writes;
        if(vm_fail_write && vm_control_writes==vm_fail_write) {
            if(vm_apply_failure) {
                ssize_t applied=write(fd,bytes,size);
                if(applied!=(ssize_t)size)return applied;
                ++vm_applied_failures;
            }
            errno=EIO;return -1;
        }
    }
    return write(fd,bytes,size);
}
static void vm_fail(const char *message) {
    dprintf(2,"PHASE_VM_FAIL %s errno=%d\n",message,errno);_exit(99);
}
static void vm_require(int condition,const char *message){if(!condition)vm_fail(message);}
static void vm_directory(const char *path) {
    if(mkdir(path,0755) && errno!=EEXIST)vm_fail(path);
}
static void vm_filesystems(void) {
    vm_directory("/proc");vm_directory("/sys");vm_directory("/dev");vm_directory("/run");
    vm_require(!mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"proc");
    vm_require(!mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"sys");
    vm_require(!mount("devtmpfs","/dev","devtmpfs",MS_NOSUID,NULL),"dev");
    vm_require(!chmod("/dev/kmsg",0600),"logger-node-mode");
    vm_require(!mount("tmpfs","/run","tmpfs",MS_NOSUID|MS_NODEV,"mode=0755,size=2m"),"run");
    vm_directory("/run/s22-debian");
}
static void vm_module(const char *name) {
    char path[128];snprintf(path,sizeof(path),"/modules/%s.ko",name);
    int fd=open(path,O_RDONLY|O_CLOEXEC);vm_require(fd>=0,path);
    vm_require(!syscall(SYS_finit_module,fd,"",0),name);vm_require(!close(fd),"module-close");
}
static void vm_binding(unsigned actor) {
    at_actor=actor;sw.deadline_ms=300000;memcpy(sw.run,sw_run,16);
    memset(sw.nonce,0xa5,sizeof(sw.nonce));vm_require(!sw_boot(sw.boot),"boot-id");
}
static void vm_no_trace_descriptors(void) {
    DIR *dir=opendir("/proc/self/fd");vm_require(dir!=NULL,"fd-directory");
    struct dirent *entry;
    while((entry=readdir(dir))) {
        if(entry->d_name[0]=='.')continue;
        int fd=atoi(entry->d_name);if(fd==dirfd(dir) || fd<=2)continue;
        char path[80],target[256];snprintf(path,sizeof(path),"/proc/self/fd/%d",fd);
        ssize_t size=readlink(path,target,sizeof(target)-1);vm_require(size>=0,"fd-link");target[size]=0;
        vm_require(!strstr(target,"phase-trace") && !strstr(target,"phase-state"),"observation-fd-leak");
    }
    vm_require(!closedir(dir),"fd-directory-close");
}
static void vm_original_scripts(void) {
    /* The actual dispatcher bytes are pinned and installed only on RAM here.
     * This fixture isolates kernel lifecycle; full Debian VM qualifies rcS. */
    ap.script_done=1;ap_channel_close();
}
static void vm_framing(const char *mode) {
    /* Exact target trace_seq boundary, supplied through the real drain's fd.
     * The producer emits 4095 bytes then the final newline on the same open. */
    unsigned used=0;
    for(unsigned i=0;i<26;++i) {
        char row[256];uint64_t now=at_now()*1000;
        int n=snprintf(row,sizeof(row),"worker-23 [000] d..2. %llu.%06llu: %s: (%s100%s)\n",
            (unsigned long long)(now/1000000),(unsigned long long)(now%1000000),
            ap_probes[0].name,ap_probes[0].symbol,ap_module_suffix);
        unsigned length=i<24 ? 158 : 152;
        vm_require(n>0 && (unsigned)n<=length && length-(unsigned)n<80,"frame-shape");
        memset(vm_frame+used,' ',length-(unsigned)n);
        memcpy(vm_frame+used+length-(unsigned)n,row,(size_t)n);used+=length;
    }
    vm_require(used==4096 && vm_frame[4095]=='\n',"frame-boundary");
    vm_frame_mode=1;if(!strcmp(mode,"framing-cap"))ap.read_calls=383;
    ap_begin(0);ap_drain();ap_charge();vm_frame_mode=0;
    if(!strcmp(mode,"framing-cap")) {
        vm_require(ap.records==25 && vm_frame_reads==1 && vm_frame_offset==4095 &&
            (ap.flags&(AP_CAP|AP_TAIL))==(AP_CAP|AP_TAIL),"bounded-tail-not-invented");
    } else {
        vm_require(ap.records==26 && vm_frame_reads==3 && vm_frame_offset==4096 &&
            !(ap.flags&(AP_TAIL|AP_PARSE|AP_CAP|AP_IO|AP_LOG)),"same-fd-final-newline");
    }
    ap_cleanup();vm_require(ap.terminal==1,"framing-cleanup");
    dprintf(1,"PHASE_VM_FRAMING_PASS records=%u reads=%u offset=%u flags=%u\n",
        ap.records,vm_frame_reads,vm_frame_offset,ap.flags);
}
static int vm_rcs(const char *mode,unsigned fail) {
    vm_binding(6);vm_fail_write=fail;vm_apply_failure=!strncmp(mode,"applied-",8);
    if(!strcmp(mode,"foreign-group")) {
        vm_directory("/fixturetrace");
        vm_require(!mount("tracefs","/fixturetrace","tracefs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),
            "fixture-tracefs");
        int fd=open("/fixturetrace/kprobe_events",O_WRONLY);
        const char *foreign="r16:s22phase/foreign dummy_hcd:dummy_hcd_probe\n";
        vm_require(fd>=0 && write(fd,foreign,strlen(foreign))==(ssize_t)strlen(foreign) &&
            !close(fd),"fixture-foreign-register");
        vm_control_writes=0;ap_start();
        vm_require(ap_claimed && ap_local_done && ap.terminal==2 && !ap.attempted &&
            vm_control_writes==0,"foreign-event-not-enabled-or-deleted");
        char value[256];fd=open("/fixturetrace/kprobe_events",O_RDONLY);
        ssize_t n=read(fd,value,sizeof(value)-1);vm_require(n>0 && !close(fd),"foreign-readback");
        value[n]=0;vm_require(strstr(value,"s22phase/foreign")!=NULL,"foreign-preserved");
        return 0;
    }
    ap_start();
    if(fail) {
        vm_require(ap_claimed && ap_local_done && ap.terminal==1,"partial-setup-cleanup");
        vm_require(access(AP_ROOT,F_OK)<0 && errno==ENOENT,"partial-mount-removed");
        vm_require(vm_applied_failures==vm_apply_failure,"applied-error-occurrence");
        vm_no_trace_descriptors();
        dprintf(1,"PHASE_VM_PARTIAL_PASS control=%u writes=%u used_ms=%llu\n",fail,vm_control_writes,(unsigned long long)ap.used_ms);
        return 0;
    }
    vm_require(ap_claimed && ap.enabled && !ap_local_done,"phase-setup");
    vm_original_scripts();
    if(!strncmp(mode,"framing-",8)) {
        vm_framing(mode);vm_no_trace_descriptors();return 0;
    }
    if(!strcmp(mode,"cleanup-fail")) {
        vm_fail_write=vm_control_writes+1;ap_cleanup();
        vm_require(ap_local_done && ap.terminal==2 && ap_state_read()!=0,"cleanup-failure-consumed");
        char value[64];ap_cleanup_disarm=1;
        vm_require(!ap_read(AP_INSTANCE "/events/s22phase/enable",value,sizeof(value)) &&
            !strcmp(value,"0\n"),"failed-instance-disable-still-disables-owned-events");
        ap_cleanup_disarm=0;
        unsigned writes=vm_control_writes;ap_cleanup();
        vm_require(vm_control_writes==writes,"cleanup-not-retried");return 0;
    }
    if(!strcmp(mode,"logger-loss")) {
        vm_require(!unlink("/dev/kmsg"),"remove-fixture-logger");
        ap_record(AT_PHASE_KERNEL,1000000,0,0,1,UINT_MAX,0);
        vm_require(ap.flags&AP_LOG,"logger-loss-explicit");ap_tick();
        vm_require(ap_local_done && ap.terminal==1 && at_lost,"logger-loss-owned-cleanup");
        return 0;
    }
    if(!strcmp(mode,"registry-fail")) {
        vm_registry_failure=1;ap_cleanup();vm_registry_failure=0;
        vm_require(ap_local_done && ap.terminal==2,"registry-failure-incomplete");
        char value[64];ap_cleanup_disarm=1;
        vm_require(!ap_read(AP_INSTANCE "/tracing_on",value,sizeof(value)) &&
            !strcmp(value,"0\n"),"registry-failure-instance-disarmed");
        vm_require(!ap_read(AP_INSTANCE "/events/s22phase/enable",value,sizeof(value)) &&
            !strcmp(value,"0\n"),"registry-failure-events-disarmed");
        ap_cleanup_disarm=0;return 0;
    }
    ap_begin(0);
    vm_require(!ap_setting("tracing_on","0\n","0\n"),"off-before-unrecorded-trigger");
    vm_module("dummy_hcd");
    vm_require(!syscall(SYS_delete_module,"dummy_hcd",O_NONBLOCK),"unload-first-trigger");
    vm_require(!ap_setting("tracing_on","1\n","1\n"),"on-before-handover");
    ap_charge();
    if(!strcmp(mode,"actor-budget")) {
        at_spent=1999;ap_begin(0);vm_require(ap_end<=ap_work_begin+1,"actor-budget-clip");ap_charge();
        ap_abort();vm_require(ap_local_done,"budget-cleanup-once");
        dprintf(1,"PHASE_VM_BUDGET_PASS used_ms=%llu terminal=%u writes=%u\n",
            (unsigned long long)ap.used_ms,ap.terminal,vm_control_writes);
        return 0;
    }
    ap_handover();vm_require(ap.handover==1 && !ap_local_done,"handover-save");
    vm_no_trace_descriptors();
    dprintf(1,"PHASE_VM_HANDOVER used_ms=%llu writes=%u flags=%u log_lost=%u log_error=%u\n",
        (unsigned long long)ap.used_ms,vm_control_writes,ap.flags,at_lost,at_error);
    return 0;
}
static int vm_runlevel(const char *mode) {
    vm_binding(8);
    if(!strcmp(mode,"handover-stale"))sw.boot[0]^=1;
    ap_resume();
    if(!strncmp(mode,"handover-",9)) {
        vm_require(!ap_claimed && !vm_control_writes,"invalid-handover-no-effects");
        vm_no_trace_descriptors();return 0;
    }
    dprintf(1,"PHASE_VM_RESUME used_ms=%llu flags=%u terminal=%u log_lost=%u log_error=%u\n",
        (unsigned long long)ap.used_ms,ap.flags,ap.terminal,at_lost,at_error);
    vm_require(ap_claimed && ap.handover==1 && ap.owner==8,"handover-consumed");
    if(!strcmp(mode,"late")) {
        vm_require(ap_local_done && ap.terminal==2 && ap.records==0,"late-cleanup-unconfirmed");
        char value[64];ap_cleanup_disarm=1;
        vm_require(!ap_read(AP_INSTANCE "/tracing_on",value,sizeof(value)) && !strcmp(value,"0\n"),"late-instance-off");
        vm_require(!ap_read(AP_INSTANCE "/events/s22phase/enable",value,sizeof(value)) && !strcmp(value,"0\n"),"late-events-off");
        ap_cleanup_disarm=0;
    } else {
        vm_require(!ap_local_done,"handover-budget");
        vm_module("dummy_hcd");
        ap_begin(0);ap_drain();ap_charge();
        vm_require(ap.records>0 && !(ap.flags&(AP_PARSE|AP_TAIL|AP_IO|AP_CAP)),"actual-trace-decode");
        ap_cleanup();vm_require(ap.terminal==1,"final-cleanup");
    }
    vm_no_trace_descriptors();
    if(strcmp(mode,"late"))vm_require(access(AP_ROOT,F_OK)<0 && errno==ENOENT,"mount-removed");
    vm_require(ap_state_read()!=0,"handover-cannot-replay");
    dprintf(1,"PHASE_VM_FINAL_PASS mode=%s records=%u calls=%u bytes=%u flags=%u used_ms=%llu writes=%u\n",
        mode,ap.records,ap.read_calls,ap.read_bytes,ap.flags,(unsigned long long)ap.used_ms,vm_control_writes);
    return 0;
}
static void vm_child(const char *mode,const char *role,unsigned fail) {
    pid_t child=fork();vm_require(child>=0,"fork-owner");
    if(!child) {
        char number[16];snprintf(number,sizeof(number),"%u",fail);
        char *args[]={"/init",(char *)mode,(char *)role,number,NULL};
        execv(args[0],args);vm_fail("exec-owner");
    }
    int status;vm_require(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status),"owner-result");
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc==4) {
        if(!strcmp(argv[2],"rcs"))return vm_rcs(argv[1],(unsigned)strtoul(argv[3],NULL,10));
        return vm_runlevel(argv[1]);
    }
    vm_filesystems();
    char mode[64]="normal",cmdline[2048];unsigned fail=0;
    vm_require(!fs1_read_text("/proc/cmdline",cmdline,sizeof(cmdline)),"cmdline");
    char *selected=strstr(cmdline,"phase_case=");
    if(selected)vm_require(sscanf(selected,"phase_case=%63s",mode)==1,"case");
    if(!strncmp(mode,"partial-",8))fail=(unsigned)strtoul(mode+8,NULL,10);
    if(!strncmp(mode,"applied-",8))fail=(unsigned)strtoul(mode+8,NULL,10);
    vm_module("usb-common");vm_module("usbcore");vm_module("udc-core");
    vm_child(mode,"rcs",fail);
    if(!fail && strcmp(mode,"actor-budget") && strncmp(mode,"framing-",8) &&
        strcmp(mode,"cleanup-fail") && strcmp(mode,"logger-loss") &&
        strcmp(mode,"registry-fail") && strcmp(mode,"foreign-group")) {
        if(!strcmp(mode,"handover-missing"))vm_require(!unlink(AP_STATE),"fixture-missing-state");
        if(!strcmp(mode,"handover-torn")) {
            int fd=open(AP_STATE,O_WRONLY);char byte=0;
            vm_require(fd>=0 && pwrite(fd,&byte,1,0)==1 && !close(fd),"fixture-torn-state");
        }
        if(!strcmp(mode,"late")) {
            struct timespec delay={16,0};vm_require(!nanosleep(&delay,NULL),"late-gap");
        }
        vm_child(mode,"runlevel",0);
    }
    dprintf(1,"PHASE_VM_PASS case=%s scope=GENERIC_ARM64_COMPONENT_ONLY\n",mode);
    sync();reboot(RB_POWER_OFF);return 0;
}
