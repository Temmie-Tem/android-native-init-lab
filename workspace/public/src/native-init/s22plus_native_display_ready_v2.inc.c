/* P351 fixed provider readiness. No insertion retry or arbitrary sysfs access. */
#define p350_prepare_driver __attribute__((unused)) p350_previous_prepare_driver
#include "s22plus_native_display_load.inc.c"
#undef p350_prepare_driver
#include <dirent.h>

#define P351_READY_MS 15000
#define P351_KMSG_LIMIT 32768
struct p351_readiness { int complete,bus,pmic,rails,drm,mdp,dsi; };
static struct p351_readiness p351_last={0,-1,-1,-1,-1,-1,-1};
static int p351_diagnostic_armed;
static int64_t p351_elapsed;
static unsigned p351_scans;
static int p351_ready(struct p351_readiness s) {
    return s.complete==1 && s.bus==1 && s.pmic==1 && s.rails==15 && s.drm==1;
}
static void p351_emit_snapshot(void) {
    printf("DISPLAY_READY ready=%d complete=%d bus=%d pmic=%d rails=%d drm=%d mdp=%d dsi=%d elapsed_ms=%lld scans=%u\n",
        p351_ready(p351_last),p351_last.complete,p351_last.bus,p351_last.pmic,
        p351_last.rails,p351_last.drm,p351_last.mdp,p351_last.dsi,
        (long long)p351_elapsed,p351_scans);
    fflush(stdout);
}
static void p351_failure_diagnostic(void) {
    if (!p351_diagnostic_armed) return;
    p351_diagnostic_armed=0; /* One attempt, including syscall failure. */
    p351_emit_snapshot();
    char log[P351_KMSG_LIMIT];
    errno=0;
    long n=syscall(SYS_syslog,3,log,(int)sizeof(log)); /* READ_ALL; never READ_CLEAR. */
    int error=n<0?errno:0;
    if (n>(long)sizeof(log)) { n=-1;error=EOVERFLOW; }
    printf("DISPLAY_KMSG_BEGIN limit=%u bytes=%ld errno=%d coverage=bounded-tail\n",
        (unsigned)sizeof(log),n<0?0:n,error);
    if (n>0) (void)fwrite(log,1,(size_t)n,stdout);
    printf("\nDISPLAY_KMSG_END\n");fflush(stdout);
}
static int p351_read_sysfs(const char *path,char *buffer,size_t capacity) {
    int node=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if (node<0) {
        if(errno==ENOENT || errno==ENODEV)return -1;
        fail("ready-open");
    }
    struct statfs fs;if(fstatfs(node,&fs))fail("ready-statfs");
    require(fs.f_type==SYSFS_MAGIC,"ready-not-sysfs");
    size_t used=0;
    for(;;) {
        require(used<capacity,"ready-value-bound");
        ssize_t n=read(node,buffer+used,capacity-used);
        if(n<0)fail("ready-read");
        if(!n)break;
        used+=(size_t)n;
    }
    if(close(node))fail("ready-close");
    require(used && !memchr(buffer,0,used),"ready-value-format");
    buffer[used]=0;return (int)used;
}
static int p351_driver(const char *path,const char *expected,int strict) {
    char target[512];ssize_t n=readlink(path,target,sizeof(target)-1);
    if(n<0) {
        if(errno==ENOENT || errno==ENODEV)return 0;
        if(!strict)return -1;
        fail("ready-driver-link");
    }
    if(n<=0 || (size_t)n>=sizeof(target)-1) {
        if(!strict)return -1;
        require(0,"ready-driver-bound");
    }
    target[n]=0;char *name=strrchr(target,'/');
    int matched=name && !strcmp(name+1,expected);
    if(strict)require(matched,"ready-driver-binding");
    return matched;
}
static int p351_regulators(void) {
    DIR *dir=opendir("/sys/class/regulator");
    if(!dir) {if(errno==ENOENT)return 0;fail("ready-regulator-dir");}
    struct statfs fs;if(fstatfs(dirfd(dir),&fs))fail("ready-regulator-statfs");
    require(fs.f_type==SYSFS_MAGIC,"ready-regulator-not-sysfs");
    const char *names[]={"panel_vdd3\n","panel_vci\n","panel_vddr\n","panel_aee_fd\n"};
    int mask=0;unsigned count=0;struct dirent *entry;
    for(;;) {
        errno=0;entry=readdir(dir);if(!entry) {if(errno)fail("ready-regulator-readdir");break;}
        if(!strcmp(entry->d_name,".") || !strcmp(entry->d_name,".."))continue;
        require(++count<=256,"ready-regulator-count");
        if(strncmp(entry->d_name,"regulator.",10))continue;
        const char *suffix=entry->d_name+10;
        require(*suffix,"ready-regulator-name");
        for(const char *p=suffix;*p;p++)require(*p>='0'&&*p<='9',"ready-regulator-name");
        char path[320],value[65];int n=snprintf(path,sizeof(path),"/sys/class/regulator/%s/name",entry->d_name);
        require(n>0 && (size_t)n<sizeof(path),"ready-regulator-path");
        if(p351_read_sysfs(path,value,sizeof(value)-1)<0)continue;
        for(unsigned i=0;i<4;i++)if(!strcmp(value,names[i])) {
            require(!(mask&(1<<i)),"ready-regulator-duplicate");mask|=1<<i;
        }
    }
    if(closedir(dir))fail("ready-regulator-close");
    return mask;
}
static void p351_snapshot(void) {
    p351_last=(struct p351_readiness){0,-1,-1,-1,-1,-1,-1};++p351_scans;
    p351_last.bus=p351_driver("/sys/bus/platform/devices/i2c@50/driver","i2c-gpio",1);
    p351_last.pmic=p351_driver("/sys/bus/i2c/devices/50-0060/driver","s2dos05-regulator",1);
    p351_last.rails=p351_regulators();
    char number[17];int n=p351_read_sysfs("/sys/class/drm/card0/dev",number,sizeof(number)-1);
    if(n>=0)require(n==6&&!memcmp(number,"226:0\n",6),"ready-drm-number");
    p351_last.drm=n>=0;
    p351_last.mdp=p351_driver("/sys/bus/platform/devices/ae00000.qcom,mdss_mdp/driver","msm_drm",0);
    p351_last.dsi=p351_driver("/sys/bus/platform/devices/soc:qcom,dsi-display-primary/driver","msm-dsi-display",0);
    p351_last.complete=1;
}
static void p351_prepare_driver(void) {
    int sys=open("/sys",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(sys<0)fail("sysfs-open");
    struct statfs fs;if(fstatfs(sys,&fs))fail("sysfs-statfs");require(fs.f_type==SYSFS_MAGIC,"sysfs-binding");
    if(close(sys))fail("sysfs-close");
    char cmdline[8192],params[192];size_t used=0;
    int source=open("/proc/cmdline",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(source<0)fail("cmdline-open");
    for(;;) {
        require(used<sizeof(cmdline)-1,"cmdline-bound");
        ssize_t n=read(source,cmdline+used,sizeof(cmdline)-1-used);
        if(n<0)fail("cmdline-read");
        if(!n)break;
        used+=(size_t)n;
    }
    if(close(source))fail("cmdline-close");
    require(used>0 && !memchr(cmdline,0,used),"cmdline-format");cmdline[used]=0;
    p350_parameters(params,cmdline);
    for(unsigned i=0;i<P350_DISPLAY_MODULE_COUNT;i++) {
        const struct p350_display_module *m=&p350_display_modules[i];
        int mod=open(m->path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(mod<0)fail("module-open");
        struct stat st;if(fstat(mod,&st))fail("module-stat");
        require(S_ISREG(st.st_mode)&&st.st_nlink==1&&st.st_uid==0&&
            (st.st_mode&0777)==0400&&(uint64_t)st.st_size==m->size,"module-file-binding");
        printf("DISPLAY_LOAD_BEGIN index=%u\n",i);fflush(stdout);
        if(syscall(SYS_finit_module,mod,m->display?params:"",0))fail("module-insertion");
        if(close(mod))fail("module-close");
        printf("DISPLAY_LOAD_DONE index=%u\n",i);fflush(stdout);
    }
    int64_t start=now_ms();p351_diagnostic_armed=1;
    for(;;) {
        p351_snapshot();p351_elapsed=now_ms()-start;
        if(p351_ready(p351_last) && p351_elapsed<=P351_READY_MS) {
            p351_snapshot();p351_elapsed=now_ms()-start;
            if(p351_ready(p351_last) && p351_elapsed<=P351_READY_MS)break;
        }
        if(p351_elapsed>=P351_READY_MS) {errno=ETIMEDOUT;fail("drm-readiness");}
        struct timespec delay={.tv_nsec=200000000};if(nanosleep(&delay,NULL))fail("ready-delay");
    }
    p351_emit_snapshot();p351_diagnostic_armed=0;
    int dev=open("/dev",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(dev<0)fail("dev-open");
    if(fstatfs(dev,&fs))fail("dev-statfs");
    require(fs.f_type==TMPFS_MAGIC,"dev-not-ram");
    if(mkdirat(dev,"dri",0700) && errno!=EEXIST)fail("dri-mkdir");
    int dri=openat(dev,"dri",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(dri<0)fail("dri-open");
    struct stat ds;if(fstat(dri,&ds))fail("dri-stat");require(ds.st_uid==0&&!(ds.st_mode&0022),"dri-permissions");
    if(mknodat(dri,"card0",S_IFCHR|0600,makedev(226,0)))fail("drm-node-create");
    if(close(dri)||close(dev))fail("dev-close");
}
