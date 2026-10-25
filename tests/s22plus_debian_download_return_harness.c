/* H0 ARM64 syscall fixtures around the actual final helper. No device I/O. */
#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <linux/reboot.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>
#include <stdarg.h>

enum {RB_REBOOT_INTENT=9,RB_SHUTDOWN_INTENT=10};
static struct {uint64_t root_device,deadline_ms;uint8_t nonce[32];} sw;
static struct {int complete,stopped,off,control;} de;
static uint8_t rb_early_nonce[32];
static unsigned rb_phase;
struct dh_state {int unused;};
static jmp_buf parked;
static unsigned calls,modules,claims,records,closed,dir_index,root_checks;
static int fail_module,expire_module,case_id,last_errno;
static uint64_t now=100;
static unsigned long reboot_mode;
static char reboot_argument[16];
static size_t registry_offset;
static const char registry[]="* STAGE : Reboot Notifier\n+ Priority : 250\n[<opaque>] download\n  - func : [<opaque>] ignored\n+ Default :\n[<opaque>] default\n  - func : [<opaque>] ignored\n";
enum {OK,NO_INTENT,BAD_INTENT,INCOMPLETE,CLAIMED,ROOT_RW,BIND_RO,ROOT_DEVICE,EXPIRED,
      BAD_MODE,PIN_FAIL,PROVIDER_MISSING,REGISTRY_BAD,WRITER_UNBOUND,SECOND_ROOT_RW,
      LOG_FAILURE,BAD_NONCE,INIT_MISMATCH,ROOT_MOUNT_WRONG};
static void sw_put32(uint8_t *p,uint32_t n){memcpy(p,&n,4);}
static void de_put64(uint8_t *p,uint64_t n){memcpy(p,&n,8);}
static uint64_t sw_now(void){return now;}
static int fs1_error(void){return errno?errno:EIO;}
static int rb_current_early(void){return 0;}
static int dh_load(struct dh_state *s){(void)s;return 0;}
static int de_load(struct dh_state *s){(void)s;return 0;}
static int dh_actual_init_mode(struct dh_state *s,bool ro){(void)s;assert(ro);return case_id==INIT_MISMATCH?EPROTO:0;}
static int fixture_stat(const char *path,struct stat *s){
    memset(s,0,sizeof(*s));
    if(!strcmp(path,"/")){s->st_dev=case_id==ROOT_DEVICE?makedev(8,3):sw.root_device;return 0;}
    assert(!strcmp(path,"/sys/bus/platform/drivers/samsung,qcom-qcom_reboot_reason/soc:samsung,qcom-qcom_reboot_reason"));
    if(case_id==WRITER_UNBOUND){errno=ENOENT;return -1;}s->st_mode=S_IFDIR|0500;return 0;
}
static int fixture_statfs(const char *path,struct statfs *s){
    memset(s,0,sizeof(*s));
    if(!strcmp(path,"/")){root_checks++;s->f_type=0xef53;s->f_flags=(case_id==ROOT_RW ||
        (case_id==SECOND_ROOT_RW && root_checks>1))?0:ST_RDONLY;return 0;}
    assert(!strcmp(path,"/run/s22-debian"));s->f_type=0x01021994;return 0;
}
static FILE *fixture_fopen(const char *path,const char *mode){
    assert(!strcmp(path,"/proc/self/mountinfo") && !strcmp(mode,"re"));
    const char *text=case_id==BIND_RO?"1 0 8:2 / / ro - ext4 /dev/root rw\n":
        case_id==ROOT_MOUNT_WRONG?"1 0 8:3 / / ro - ext4 /dev/root ro\n":"1 0 8:2 / / ro - ext4 /dev/root ro\n";
    return fmemopen((void *)text,strlen(text),"r");
}
static int fixture_mkdir(const char *path,mode_t mode){
    assert(!strcmp(path,"/run/s22-debian/return-claimed") && mode==0700);claims++;
    if(case_id==CLAIMED){errno=EEXIST;return -1;}return 0;
}
static int fixture_open(const char *path,int flags,...){
    if(!strcmp(path,"/run/s22-debian/return-records")){
        assert(flags==(O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC));return 10;}
    assert(!strcmp(path,"/sys/kernel/debug/sec_reboot_cmd") && flags==(O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC));
    registry_offset=0;return 30;
}
static ssize_t fixture_write(int fd,const void *p,size_t length){
    assert(fd==10 && length==32 && !memcmp(p,"S22DL01",7));const uint8_t *b=p;uint32_t stage,err;
    memcpy(&stage,b+16,4);memcpy(&err,b+20,4);records++;if(stage==255)last_errno=(int)err;
    if(case_id==LOG_FAILURE && stage==50){errno=EIO;return -1;}return (ssize_t)length;
}
static int fixture_fsync(int fd){assert(fd==10);return 0;}
static int fixture_close(int fd){assert(fd==10 || fd==20 || fd==30);closed++;return 0;}
static ssize_t fixture_read(int fd,void *data,size_t size){
    assert(fd==30);const char *text=case_id==REGISTRY_BAD?"* STAGE : Restart Handler\n":registry;
    size_t left=strlen(text)-registry_offset;if(size>left)size=left;
    memcpy(data,text+registry_offset,size);registry_offset+=size;return (ssize_t)size;
}
static int fixture_fstat(int fd,struct stat *s){assert(fd==20);memset(s,0,sizeof(*s));s->st_mode=S_IFREG|(case_id==BAD_MODE?0600:0400);return 0;}
static int fixture_fstatfs(int fd,struct statfs *s){assert(fd==20);memset(s,0,sizeof(*s));s->f_type=0x01021994;return 0;}
static int fs1_pin_file(const char *path,uint64_t size,const uint8_t sha[32],bool optional){
    assert(strstr(path,"/run/s22-debian/return-")==path && size>0 && sha && !optional);
    if(case_id==PIN_FAIL){errno=EINVAL;return -1;}return 20;
}
static DIR *fixture_opendir(const char *path){assert(!strcmp(path,"/sys/bus/nvmem/devices"));dir_index=0;return (DIR *)1;}
static struct dirent *fixture_readdir(DIR *dir){
    static struct dirent entry;assert(dir==(DIR *)1);
    if(dir_index>=(case_id==PROVIDER_MISSING?1U:2U))return NULL;
    memset(&entry,0,sizeof(entry));snprintf(entry.d_name,sizeof(entry.d_name),"spmi_sdam%u",dir_index++);return &entry;
}
static int fixture_dirfd(DIR *dir){assert(dir==(DIR *)1);return 40;}
static int fixture_closedir(DIR *dir){assert(dir==(DIR *)1);return 0;}
static ssize_t fixture_readlinkat(int fd,const char *path,char *data,size_t size){
    assert(fd==40);const char *text=!strcmp(path,"spmi_sdam0/of_node")?
        "/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@7100":"/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@7200";
    assert(strlen(text)<size);memcpy(data,text,strlen(text));return (ssize_t)strlen(text);
}
static int fixture_mount(const char *source,const char *path,const char *type,unsigned long flags,const void *data){
    assert(!strcmp(source,"debugfs") && !strcmp(path,"/sys/kernel/debug") && !strcmp(type,"debugfs") &&
        flags==(MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC) && !data);return 0;
}
static int fixture_nanosleep(const struct timespec *delay,struct timespec *unused){
    assert(!unused);if(delay->tv_sec==1)longjmp(parked,1);now+=100;return 0;
}
static long fixture_syscall(long number,...){
    va_list ap;va_start(ap,number);
    if(number==SYS_finit_module){
        int fd=va_arg(ap,int);const char *params=va_arg(ap,const char *);int flags=va_arg(ap,int);
        assert(fd==20 && flags==0 && !strcmp(params,modules==3?"download_mode=0":""));modules++;
        if((int)modules==expire_module)now=sw.deadline_ms;
        if((int)modules==fail_module){errno=EIO;va_end(ap);return -1;}
    }else{
        assert(number==SYS_reboot);assert(va_arg(ap,int)==(int)LINUX_REBOOT_MAGIC1);
        assert(va_arg(ap,int)==(int)LINUX_REBOOT_MAGIC2);reboot_mode=va_arg(ap,unsigned int);
        const char *arg=va_arg(ap,const char *);if(arg)snprintf(reboot_argument,sizeof(reboot_argument),"%s",arg);
        calls++;errno=EIO;va_end(ap);return -1;
    }
    va_end(ap);return 0;
}
#define stat(...) fixture_stat(__VA_ARGS__)
#define statfs(...) fixture_statfs(__VA_ARGS__)
#define fopen fixture_fopen
#define mkdir fixture_mkdir
#define open fixture_open
#define write fixture_write
#define fsync fixture_fsync
#define close fixture_close
#define read fixture_read
#define fstat fixture_fstat
#define fstatfs fixture_fstatfs
#define opendir fixture_opendir
#define readdir fixture_readdir
#define dirfd fixture_dirfd
#define closedir fixture_closedir
#define readlinkat fixture_readlinkat
#define mount fixture_mount
#define nanosleep fixture_nanosleep
#define syscall fixture_syscall
#include "s22plus_debian_download_return_v1.inc.c"

static void reset(unsigned phase,int selected,int fail,int expire){
    rb_phase=phase;case_id=selected;fail_module=fail;expire_module=expire;
    calls=modules=claims=records=closed=dir_index=root_checks=0;now=100;reboot_mode=0;reboot_argument[0]=0;
    last_errno=0;dl_log=-1;dl_records=0;sw.root_device=makedev(8,2);sw.deadline_ms=10000;
    memset(sw.nonce,0,32);memset(rb_early_nonce,0,32);if(selected==BAD_NONCE)sw.nonce[0]=1;
    de.complete=selected!=INCOMPLETE;de.stopped=de.off=0;de.control=phase==1?9:10;
    if(selected==NO_INTENT)de.control=0;if(selected==BAD_INTENT)de.control=phase==1?10:9;
    if(selected==EXPIRED)now=sw.deadline_ms;
}
static void exercise(unsigned phase,int selected,int fail,int expire,unsigned want_modules,unsigned want_calls){
    reset(phase,selected,fail,expire);if(!setjmp(parked))dl_final();
    assert(modules==want_modules && calls==want_calls && records<=32 && claims<=1);
    if(calls){assert(last_errno==EIO && reboot_mode==(phase==1?LINUX_REBOOT_CMD_RESTART:LINUX_REBOOT_CMD_RESTART2));
        assert(!strcmp(reboot_argument,phase==1?"":"download"));}
    if(records)assert(last_errno!=0);
}
int main(void){
    assert(SYS_finit_module==273 && SYS_reboot==142 && O_NOFOLLOW==0x8000 && O_CLOEXEC==0x80000);
    assert(dl_options_ro("ro,nosuid") && !dl_options_ro("rw") && !dl_options_ro("ro,rw") && !dl_options_ro("ro,ro"));
    assert(dl_registry_valid((const uint8_t *)registry,strlen(registry)));
    const char *bad="* STAGE : Reboot Notifier\n+ Priority : 250\n[<download>] wrong\n  - func : [<download>] ignored\n+ Default :\n[<opaque>] default\n  - func : [<opaque>] ignored\n";
    assert(!dl_registry_valid((const uint8_t *)bad,strlen(bad)));
    exercise(1,OK,0,0,0,1);exercise(2,OK,0,0,5,1);
    for(int id=NO_INTENT;id<=EXPIRED;id++)exercise(2,id,0,0,0,0);
    exercise(2,BAD_MODE,0,0,0,0);exercise(2,PIN_FAIL,0,0,0,0);
    exercise(2,PROVIDER_MISSING,0,0,4,0);exercise(2,REGISTRY_BAD,0,0,4,0);
    exercise(2,WRITER_UNBOUND,0,0,5,0);exercise(2,SECOND_ROOT_RW,0,0,5,0);
    exercise(2,LOG_FAILURE,0,0,5,0);exercise(2,BAD_NONCE,0,0,0,0);
    exercise(2,INIT_MISMATCH,0,0,0,0);exercise(2,ROOT_MOUNT_WRONG,0,0,0,0);
    for(int i=1;i<=5;i++){exercise(2,OK,i,0,(unsigned)i,0);exercise(2,OK,0,i,(unsigned)i,0);}
    puts("PASS ARM64 production Download helper: 30 control/failure fixtures; real target UAPI; no device I/O");return 0;
}
