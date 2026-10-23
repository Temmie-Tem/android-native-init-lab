/* H0 only: ext4 mount-consumption probe inside an ARM64 QEMU virt guest.
 * Not linked into a physical image or any device-action runner. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

static unsigned u16(const uint8_t *p) { return p[0] | (unsigned)p[1] << 8; }
static unsigned u32(const uint8_t *p) {
    return p[0] | (unsigned)p[1] << 8 | (unsigned)p[2] << 16 | (unsigned)p[3] << 24;
}
static void fail(const char *stage) {
    printf("P458_ERROR stage=%s errno=%d\n", stage, errno);
    fflush(stdout); exit(1);
}
static void point(const char *stage) {
    printf("P458_POINT %s\n", stage); fflush(stdout);
}
static void hold(const char *selected, const char *stage) {
    point(stage);
    if (!strcmp(selected, stage)) for (;;) pause();
}
static unsigned inspect(const char *stage, bool *clean) {
    uint8_t sb[1024]; int fd=open("/dev/vda",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if (fd<0) fail("open-super");
    struct stat st;
    if (fstat(fd,&st) || !S_ISBLK(st.st_mode)) fail("block-type");
    if (pread(fd,sb,sizeof(sb),1024)!=(ssize_t)sizeof(sb)) fail("read-super");
    if (close(fd)) fail("close-super");
    if (u16(sb+56)!=0xef53 || !(u32(sb+92)&4)) { errno=EPROTO; fail("ext4-journal"); }
    unsigned state=u16(sb+58), recover=!!(u32(sb+96)&4), orphan=u32(sb+232);
    *clean=state==1 && !recover && !orphan;
    printf("P458_SUPER stage=%s count=%u state=%u recover=%u orphan=%u clean=%u\n",
        stage,u16(sb+52),state,recover,orphan,*clean);
    fflush(stdout); return u16(sb+52);
}
static bool absent(void) {
    struct stat st;
    if (!lstat("/mnt/consume",&st)) return false;
    if (errno!=ENOENT) fail("consume-stat");
    return true;
}
int main(int argc, char **argv) {
    char model[128]={0}; int fd=open("/proc/device-tree/model",O_RDONLY|O_CLOEXEC);
    if (fd<0 || read(fd,model,sizeof(model)-1)<=0 || close(fd)) fail("virt-model");
    if (!strstr(model,"linux,dummy-virt") || geteuid()) { errno=EPERM; fail("virt-only"); }
    if (argc!=3) { errno=EINVAL; fail("arguments"); }
    const char *cases[]={"inspect","before-mount","after-mount","after-consume","clean-error","normal"};
    bool selected=false;
    for (unsigned i=0;i<sizeof(cases)/sizeof(*cases);i++) selected|=!strcmp(argv[1],cases[i]);
    char *end=NULL; unsigned long expected=strtoul(argv[2],&end,10);
    if (!selected || !*argv[2] || *end || expected>65534) { errno=EINVAL; fail("selection"); }
    bool clean=false; unsigned before=inspect("before",&clean);
    if (!clean || before!=expected) {
        printf("P458_REJECT reason=%s\n",!clean?"dirty":"mount-count"); return 0;
    }
    fd=open("/dev/vda",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    int ro=1;
    if (fd<0 || ioctl(fd,BLKROSET,&ro)) fail("protect-ro");
    if (mount("/dev/vda","/mnt","ext4",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,"noload,nodiscard")) fail("read-mount");
    bool available=absent();
    if (umount2("/mnt",0)) fail("read-unmount");
    if (!available) { puts("P458_REJECT reason=consume-exists"); close(fd); return 0; }
    puts("P458_ADMIT"); fflush(stdout);
    if (!strcmp(argv[1],"inspect")) { close(fd); return 0; }
    hold(argv[1],"before-mount");
    ro=0; if (ioctl(fd,BLKROSET,&ro) || close(fd)) fail("clear-ro");
    if (mount("/dev/vda","/mnt","ext4",MS_NOSUID|MS_NODEV|MS_NOEXEC,"nodiscard,barrier=1")) fail("write-mount");
    unsigned mounted=inspect("mounted",&clean);
    if (mounted!=before+1 || clean) { errno=EPROTO; fail("mounted-consumption"); }
    hold(argv[1],"after-mount");
    if (!strcmp(argv[1],"clean-error")) {
        /* Simulate a userspace error before any application file exists. */
        if (!absent()) { errno=EEXIST; fail("pre-error-file"); }
        if (umount2("/mnt",0)) fail("error-unmount");
        unsigned after=inspect("clean-error",&clean);
        if (!clean || after!=before+1) { errno=EPROTO; fail("error-consumption"); }
        point("clean-error"); return 0;
    }
    int dir=open("/mnt",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (dir<0) fail("parent");
    fd=openat(dir,"consume",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    static const char body[]="P458_H0_CONSUMED\n";
    if (fd<0 || write(fd,body,sizeof(body)-1)!=(ssize_t)sizeof(body)-1 || fsync(fd) || fsync(dir)) fail("consume");
    if (close(fd) || close(dir)) fail("consume-close");
    hold(argv[1],"after-consume");
    if (umount2("/mnt",0)) fail("normal-unmount");
    unsigned after=inspect("normal",&clean);
    if (!clean || after!=before+1) { errno=EPROTO; fail("normal-consumption"); }
    point("normal"); return 0;
}
