/* Fixed children of initial Debian /init and its temporary PID1 entry.
 * Platform preparation precedes USB; UFS follows the one USB publication.
 * No block read/write, root mount, control command or resident daemon. */
#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-INTEGRATED-v1"
#define FYG8_USB_FIRST
static int logger_bound(void);
#define main di_unused_metadata_main
#include "fyg8-prepare.c"
#undef main
#include "s22plus_fyg8_logger_binding_v1.h"
#include "integrated-providers.h"
#include "integrated-provider-plan.h"
static unsigned di_logger_phase;
static int logger_bound(void) {
#ifdef FYG8_VM_TEST
    di_logger_phase=0;return 0;
#else
    int error=ENOENT;
    for(unsigned i=0;i<200;++i) {
        error=s22_logger_probe(S22_LOGGER_NEED_LAST|S22_LOGGER_NEED_AP,&di_logger_phase);
        if(!error || error!=ENOENT)return error;
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL))return fs1_error();
    }
    return error;
#endif
}
static int di_providers(void) {
    int error=record("PROVIDERS_BEGIN");if(error)return error;
    unsigned mask=0;
#ifdef FYG8_VM_TEST
    char selected[32];
    if(fs1_read_text("/lab/integrated-fault",selected,sizeof(selected)))return EINVAL;
    if(!strcmp(selected,"provider-missing\n"))mask=3;
    else if(!strcmp(selected,"none\n"))mask=7;
    else return EINVAL;
#else
    for(unsigned attempt=0;attempt<50;++attempt) {
        mask=0;
        for(unsigned i=0;i<sizeof(di_providers_plan)/sizeof(di_providers_plan[0]);++i) {
            error=di_provider_scan(di_providers_plan+i);
            if(!error)mask|=1U<<i;
            else if(error!=EAGAIN)return error;
        }
        if(mask==7)break;
        if(attempt+1<50){struct timespec delay={0,100000000};if(nanosleep(&delay,NULL))return fs1_error();}
    }
#endif
    if(mask!=7)return ETIMEDOUT;
    return record("PROVIDERS_READY mask=%u",mask);
}
static int di_modules(unsigned begin,unsigned end) {
    const unsigned count=sizeof(fyg8_modules)/sizeof(fyg8_modules[0]);
    if(begin>=end || end>count)return EINVAL;
    for(unsigned i=begin;i<end;++i) {
        if(module_present(i)!=0)return EEXIST;
        int fd=fs1_pin_file(fyg8_modules[i].path,fyg8_modules[i].size,fyg8_modules[i].hash,false);
        if(fd<0)return fs1_error();
        if(close(fd))return fs1_error();
    }
    for(unsigned i=begin;i<end;++i) {
        const struct fyg8_module *m=fyg8_modules+i;
        int fd=fs1_pin_file(m->path,m->size,m->hash,false);if(fd<0)return fs1_error();
        int error=record("MODULE_BEGIN ordinal=%u name=%s",i+1,m->runtime);
        if(!error && module_present(i)!=0)error=EEXIST;
        if(!error)error=insert(fd,m->parameters);
        if(close(fd) && !error)error=fs1_error();
        if(!error && module_present(i)!=1)error=ENODEV;
        if(!error && !strcmp(m->runtime,"sec_log_buf")) {
            error=logger_bound();
            int logged=record("LOGGER_BIND phase=%u error=%d",di_logger_phase,error);
            if(!error)error=logged;
        }
        if(error)return error;
        if((error=record("MODULE_DONE ordinal=%u name=%s",i+1,m->runtime)))return error;
        if(!strcmp(m->runtime,"qcom_spmi_pmic") && (error=di_providers()))return error;
    }
    return 0;
}
int main(int argc,char **argv) {
    if(argc!=2 || (strcmp(argv[1],"platform") && strcmp(argv[1],"ufs")) ||
       getpid()==1 || getppid()!=1 || getuid() || geteuid() || getgid() || getegid())return 100;
    int ufs=!strcmp(argv[1],"ufs");umask(077);
    int error=target();if(error)return 101;
    if(ufs) {
        struct stat parent,entry;
        if(stat("/proc/1/exe",&parent) || stat("/sbin/integrated-init",&entry) ||
           parent.st_dev!=entry.st_dev || parent.st_ino!=entry.st_ino)return 102;
#ifdef FYG8_VM_TEST
        fake_insertions=DI_PLATFORM_COUNT;
#endif
        for(unsigned i=0;i<DI_PLATFORM_COUNT;++i)if(module_present(i)!=1)return 103;
        sequence=219;
    }
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;struct statfs fs;
    if(dir<0 || fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
       fstatfs(dir,&fs) || fs.f_type!=0x01021994L)return 104;
    events=openat(dir,ufs?"ufs-events":"fyg8-events",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(events<0 || close(dir))return 105;
    char boot[38];error=fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot));
    if(!error && (strlen(boot)!=37 || boot[36]!='\n'))error=EPROTO;
    if(!error){boot[36]=0;error=record("BEGIN run=%s boot=%s parent=1",fs1_run_id,boot);}
    if(!error)error=record("TARGET_GUARD_OK");
    if(!error)error=di_modules(ufs?DI_PLATFORM_COUNT:0,ufs?DI_MODULE_COUNT:DI_PLATFORM_COUNT);
    int logged=record("TERMINAL result=%s error=%d",error?"REJECTED":ufs?"UFS_MODULES_READY":"PLATFORM_READY",error);
    if(close(events) && !error)error=fs1_error();
    return error || logged ? 1 : 0;
}
