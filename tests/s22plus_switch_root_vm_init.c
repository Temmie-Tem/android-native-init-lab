/* H0-only ARM64 init: virtual board setup, then the actual production parent
 * exec boundary. Physical UFS/USB discovery and return are explicit substitutes.
 */
#define FS1_READONLY_BINDING_ONLY
#include "s22plus_native_ext4_v1.c"
#include "s22plus_switch_root_common_v1.inc.c"
#include "s22plus_switch_root_vm_seal.h"

struct rc1_state {
    int fd,active,pid,blocked,control;unsigned control_seq,next,qcount,flags,overload,fault_sent;
    uint64_t start,control_start;uint8_t nonce[32];
};
struct resident_child {long pid;int reaped,status,signalled,unknown;};
static struct {
    int stopped,terminal;struct resident_child abandoned_command;
    struct {struct resident_child child[3];} hud;
} local_display;
static const uint8_t *p328_run_id_bytes=sw_run;
#define P260_EPROTO EPROTO
static int local_owner(void){return getpid()==1;}
static long rc1_now(uint64_t *now){*now=sw_now();return *now==UINT64_MAX ? -EIO : 0;}
static long swvm_kernel_boot_id(uint8_t *out){return -sw_boot(out);}
static long syscall6(long nr,long a,long b,long c,long d,long e,long f){long rc=syscall(nr,a,b,c,d,e,f);return rc<0 ? -errno : rc;}
static long sys_write(int fd,const void *p,size_t n){ssize_t rc=write(fd,p,n);return rc<0 ? -errno : rc;}
static long sys_close(int fd){return close(fd) ? -errno : 0;}
static long sys_openat(const char *p,int flags,int mode){int rc=open(p,flags,mode);return rc<0 ? -errno : rc;}
static long p328_dup_to(int fd,int to){int rc=fd==to ? to : dup3(fd,to,0);return rc<0 ? -errno : rc;}
static long sys_execve(const char *p,char *const a[],char *const e[]){execve(p,a,e);return -errno;}
static void p282_poll_delay(void){sw_park();}
#include "s22plus_switch_root_parent_expanded.h"

static void init_require(int condition,const char *where){if(!condition){dprintf(2,"SWVM_SETUP_FAIL %s errno=%d\n",where,errno);sw_park();}}
static void worker(void){if(setsid()<0)_exit(90);for(;;)pause();}
int main(void) {
    init_require(getpid()==1,"pid1");
    init_require(!mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"proc");
    init_require(!mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"sys");
    init_require(!mount("tmpfs","/dev","tmpfs",MS_NOSUID,"mode=0755"),"dev");
    init_require(!mknod("/dev/null",S_IFCHR|0600,makedev(1,3)),"null");
    init_require(!mount("tmpfs","/run","tmpfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,"mode=0755"),"old-run");
    init_require(!mount("tmpfs","/s22-root-work","tmpfs",MS_NOSUID|MS_NODEV,"size=64m,mode=0700"),"work");
    init_require(!mount("configfs","/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"config");
    init_require(!mount("debugfs","/sys/kernel/debug","debugfs",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL),"debugfs");
    dev_t tty;int error=0;
    for(unsigned i=0;i<200;++i) {
        error=fs1_device_number("/sys/class/tty/hvc0",&tty);
        if(!error && access("/sys/class/block/vda41/dev",F_OK)==0)break;
        struct timespec delay={0,50000000};nanosleep(&delay,NULL);
    }
    init_require(!error,"virtual-tty-discovery");
    init_require(!mknod("/dev/sw-tty",S_IFCHR|0600,tty),"virtual-tty-node");
    int fd=open("/dev/sw-tty",O_RDWR|O_NOCTTY|O_NONBLOCK|O_CLOEXEC);
    init_require(fd>=0,"virtual-tty-open");
    struct termios term;init_require(!tcgetattr(fd,&term),"virtual-tty-termios");cfmakeraw(&term);
    init_require(!tcsetattr(fd,TCSANOW,&term),"virtual-tty-raw");
    uint8_t boot[32];char boot_hex[65];init_require(!sw_boot(boot),"kernel-boot-id");
    for(unsigned i=0;i<32;++i)snprintf(boot_hex+2*i,3,"%02x",boot[i]);
    dprintf(2,"SWVM_BOOT %s\n",boot_hex);
    /* A high fixture descriptor also exposes the parent's low-FD-hole case. */
    int high=fcntl(fd,F_DUPFD_CLOEXEC,64);init_require(high>=64,"high-tty");close(fd);fd=high;
    for(unsigned i=0;i<3;++i){pid_t p=fork();init_require(p>=0,"worker-fork");if(!p)worker();local_display.hud.child[i].pid=p;}
    if(swvm_fault==1){pid_t p=fork();init_require(p>=0,"unknown-child");if(!p)worker();}
    if(swvm_fault==2){local_display.hud.child[0].unknown=1;}
    if(swvm_fault==3){
        for(int i=0;i<5;++i)close(i); /* actual memfd collision regression */
    }
    if(swvm_fault==4){
        pid_t p=local_display.hud.child[0].pid;kill(p,SIGKILL);
        init_require(waitpid(p,&local_display.hud.child[0].status,0)==p,"early-reap");
        local_display.hud.child[0].reaped=1;
    }
    struct rc1_state state={.fd=fd,.blocked=1,.control=4,.control_seq=5,.next=6};
    state.start=state.control_start=sw_now();memcpy(state.nonce,swvm_nonce,32);
    sw_parent_exec(&state);
}
