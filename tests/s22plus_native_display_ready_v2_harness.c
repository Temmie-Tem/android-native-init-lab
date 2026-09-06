/* Real readiness implementation with a closed fake filesystem/syscall surface. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <linux/capability.h>
#include <linux/magic.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/vfs.h>
#include <time.h>
#include <unistd.h>
static const char *scenario;
static jmp_buf stopped;
static unsigned loads,logs,scans,entry_index,node_creates;
static int64_t elapsed;
static char opened[512];
static size_t offset;
static void p351_failure_diagnostic(void);
static void fail(const char *stage) {
    printf("FAIL %s\n",stage);p351_failure_diagnostic();longjmp(stopped,1);
}
static void require(int ok,const char *stage) {if(!ok)fail(stage);}
static int is(const char *name) {return !strcmp(scenario,name);}
static int64_t now_ms(void) {return elapsed;}
static int fake_open(const char *path,int flags,...) {
    (void)flags;require(strlen(path)<sizeof(opened),"fixture-path");strcpy(opened,path);offset=0;
    if(!strcmp(path,"/sys/class/drm/card0/dev")) {
        if(is("timeout") || (is("delayed") && elapsed<400) || (is("lost") && scans==2)) {
            errno=ENOENT;return -1;
        }
    }
    require(!strcmp(path,"/sys") || !strcmp(path,"/dev") || !strcmp(path,"/proc/cmdline") ||
        !strncmp(path,"/s22-display-modules/",21) || !strcmp(path,"/sys/class/drm/card0/dev") ||
        !strncmp(path,"/sys/class/regulator/regulator.",31),"fixture-unexpected-open");
    return !strcmp(path,"/dev")?20:10;
}
static ssize_t fake_read(int fd,void *out,size_t size) {
    (void)fd;
    const char *value="226:0\n";
    if(!strcmp(opened,"/proc/cmdline"))value="msm_drm.dsi_display0=ss_dsi_panel_S6E3FAC_AMB655AY01_FHD: lcd_id=123abc";
    else if(strstr(opened,"/regulator.")) {
        const char *names[]={"panel_vdd3\n","panel_vci\n","panel_vddr\n","panel_aee_fd\n","panel_vdd3\n"};
        unsigned i=0;require(sscanf(opened,"/sys/class/regulator/regulator.%u/name",&i)==1 && i<5,"fixture-regulator");value=names[i];
    } else if(is("wrong-dev"))value="226:1\n";
    size_t n=strlen(value)-offset;if(n>size)n=size;memcpy(out,value+offset,n);offset+=n;return (ssize_t)n;
}
static int fake_close(int fd) {(void)fd;return 0;}
static int fake_statfs(int fd,struct statfs *fs) {memset(fs,0,sizeof(*fs));fs->f_type=fd==20?TMPFS_MAGIC:SYSFS_MAGIC;if(is("wrong-fs"))fs->f_type=0;return 0;}
static int fake_stat(int fd,struct stat *s) {(void)fd;memset(s,0,sizeof(*s));s->st_mode=S_IFREG|0400;s->st_nlink=1;s->st_size=1;return 0;}
static ssize_t fake_readlink(const char *path,char *out,size_t cap) {
    const char *name;
    if(strstr(path,"i2c@50")) {scans++;name=is("wrong-driver")?"../other":"../i2c-gpio";}
    else if(strstr(path,"50-0060"))name="../s2dos05-regulator";
    else {errno=ENOENT;return -1;}
    require(strlen(name)<cap,"fixture-link");memcpy(out,name,strlen(name));return (ssize_t)strlen(name);
}
static DIR *fake_opendir(const char *path) {require(!strcmp(path,"/sys/class/regulator"),"fixture-directory");entry_index=0;return (DIR *)(uintptr_t)1;}
static int fake_dirfd(DIR *d) {(void)d;return 30;}
static struct dirent *fake_readdir(DIR *d) {
    (void)d;static struct dirent ent;unsigned limit=is("duplicate")?5:4;
    if(entry_index==limit)return NULL;
    snprintf(ent.d_name,sizeof(ent.d_name),"regulator.%u",entry_index++);return &ent;
}
static int fake_closedir(DIR *d) {(void)d;return 0;}
static int fake_sleep(const struct timespec *req,struct timespec *rem) {(void)rem;require(req->tv_sec==0 && req->tv_nsec==200000000,"fixture-delay");elapsed+=200;return 0;}
static long fake_syscall(long call,...) {
    va_list ap;va_start(ap,call);
    if(call==SYS_finit_module) {loads++;va_end(ap);return 0;}
    require(call==SYS_syslog,"fixture-syscall");require(va_arg(ap,int)==3,"fixture-log-type");
    char *out=va_arg(ap,char *);require(va_arg(ap,int)==32768,"fixture-log-limit");va_end(ap);logs++;
    if(is("log-error")) {errno=EPERM;return -1;}
    memcpy(out,"fake tail",9);return 9;
}
static int fake_mkdirat(int fd,const char *p,mode_t mode) {(void)fd;require(!strcmp(p,"dri")&&mode==0700,"fixture-mkdir");return 0;}
static int fake_openat(int fd,const char *p,int flags,...) {(void)fd;(void)flags;require(!strcmp(p,"dri"),"fixture-openat");return 40;}
static int fake_mknodat(int fd,const char *p,mode_t mode,dev_t dev) {(void)fd;require(!strcmp(p,"card0")&&mode==(S_IFCHR|0600)&&dev==makedev(226,0),"fixture-mknod");node_creates++;return 0;}
#define open fake_open
#define read fake_read
#define close fake_close
#define fstatfs fake_statfs
#define fstat fake_stat
#define readlink fake_readlink
#define opendir fake_opendir
#define dirfd fake_dirfd
#define readdir fake_readdir
#define closedir fake_closedir
#define nanosleep fake_sleep
#define syscall fake_syscall
#define mkdirat fake_mkdirat
#define openat fake_openat
#define mknodat fake_mknodat
#define P350_PARAMETERS_ONLY
#include "../workspace/public/src/native-init/s22plus_native_display_ready_v2.inc.c"
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    scenario=argv[1];int failed=setjmp(stopped);
    if(!failed) {
        if(is("log-error")) {p351_diagnostic_armed=1;p351_failure_diagnostic();p351_failure_diagnostic();}
        else p351_prepare_driver();
    }
    printf("COUNTS loads=%u logs=%u scans=%u nodes=%u elapsed=%lld\n",loads,logs,scans,node_creates,(long long)elapsed);
    return failed?1:0;
}
