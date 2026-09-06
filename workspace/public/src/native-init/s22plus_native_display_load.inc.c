/* Included only by the separately built P350 fixed renderer variant.
 * The parent has already authenticated the one-shot command, consumed its
 * boot-local slot, closed inherited fds, and retained the USB/deadline owner.
 * No shell, module discovery, unload, fallback or replay is implemented here.
 */
#include <grp.h>
#include <linux/capability.h>
#include <linux/magic.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/vfs.h>
#include "s22plus_native_display_plan.h"

static void p350_parameters(char output[192], char *cmdline) {
    const char *display=NULL,*panel=NULL;
    char *save=NULL;
    for(char *t=strtok_r(cmdline," \t\r\n",&save);t;t=strtok_r(NULL," \t\r\n",&save)) {
        if(!strncmp(t,"msm_drm.dsi_display0=",21)) {
            require(!display,"duplicate-primary-display");display=t+21;
        } else if(!strncmp(t,"msm_drm.lcd_id=",15)) {
            require(!panel,"duplicate-primary-id");panel=t+15;
        } else if(!strncmp(t,"lcd_id=",7)) {
            require(!panel,"duplicate-primary-id");panel=t+7;
        } else if(!strncmp(t,"msm_drm.dsi_display1=",21) ||
                  !strncmp(t,"msm_drm.lcd_id1=",16) || !strncmp(t,"lcd_id1=",8)) {
            require(0,"secondary-display-not-in-scope");
        } else if(!strncmp(t,"androidboot.boot_recovery=",26)) {
            require(!strcmp(t+26,"0"),"recovery-not-in-scope");
        } else if(!strcmp(t,"androidboot.mode=recovery") || !strcmp(t,"androidboot.mode=charger")) {
            require(0,"nonordinary-boot");
        }
    }
    require(display && panel,"missing-primary-parameters");
    require(!strcmp(display,"ss_dsi_panel_S6E3FAC_AMB655AY01_FHD:"),"primary-panel-selection");
    if(!strncmp(panel,"0x",2) || !strncmp(panel,"0X",2))panel+=2;
    require(strlen(panel)==6,"primary-id-length");
    char normalized[7]={0};
    for(unsigned i=0;i<6;i++) {
        char c=panel[i];if(c>='A'&&c<='F')c=(char)(c-'A'+'a');
        require((c>='0'&&c<='9')||(c>='a'&&c<='f'),"primary-id-hex");normalized[i]=c;
    }
    require(strcmp(normalized,"000000") && strcmp(normalized,"ffffff"),"primary-id-detached");
    int n=snprintf(output,192,"dsi_display0=%s lcd_id=%s",display,normalized);
    require(n>0&&n<192,"module-parameter-bound");
}
#ifndef P350_PARAMETERS_ONLY
static void p350_prepare_driver(void) {
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
    /* Native PID1 has a tmpfs /dev, not udev/devtmpfs. Create only the exact
     * primary DRM character node, and verify the kernel's published dev_t. */
    char number[16]={0};int node=open("/sys/class/drm/card0/dev",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(node<0)fail("drm-readiness");
    ssize_t n=read(node,number,sizeof(number));
    require(n==6&&!memcmp(number,"226:0\n",6),"drm-dev-number");
    if(close(node))fail("drm-number-close");
    int dev=open("/dev",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(dev<0)fail("dev-open");
    struct statfs fs;if(fstatfs(dev,&fs))fail("dev-statfs");require(fs.f_type==TMPFS_MAGIC,"dev-not-ram");
    if(mkdirat(dev,"dri",0700) && errno!=EEXIST)fail("dri-mkdir");
    int dri=openat(dev,"dri",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(dri<0)fail("dri-open");
    struct stat ds;if(fstat(dri,&ds))fail("dri-stat");require(ds.st_uid==0&&!(ds.st_mode&0022),"dri-permissions");
    if(mknodat(dri,"card0",S_IFCHR|0600,makedev(226,0)))fail("drm-node-create");
    if(close(dri)||close(dev))fail("dev-close");
}
static void p350_drop_privileges(void) {
    if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0) || setgroups(0,NULL) ||
       setresgid(65534,65534,65534) || setresuid(65534,65534,65534))fail("display-drop-identity");
    struct __user_cap_header_struct h={.version=_LINUX_CAPABILITY_VERSION_3,.pid=0};
    struct __user_cap_data_struct d[2]={{0},{0}};
    if(syscall(SYS_capset,&h,d) || syscall(SYS_capget,&h,d))fail("display-drop-caps");
    require(getuid()==65534&&geteuid()==65534&&getgid()==65534&&getegid()==65534&&
        !(d[0].effective|d[0].permitted|d[0].inheritable|d[1].effective|d[1].permitted|d[1].inheritable),"display-caps-remain");
}

#endif
