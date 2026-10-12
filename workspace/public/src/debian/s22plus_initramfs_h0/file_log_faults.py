"""Compile-time ARM64 VM fault wrappers; never a physical candidate input."""
import json
from pathlib import Path

NAMES=('short-write','file-sync-error','parent-sync-error','unmount-error','late-ro-clear','checker-timeout')


def source(out,original,fault):
    if fault not in NAMES:raise ValueError('unknown file fault')
    out=Path(out)
    if fault=='checker-timeout':
        (out/'s22plus_native_userspace_probe_fault_v1.h').write_text(
            'static const char up_fault_script[]="";\n'
            'static const int up_fault_early_zero=0,up_fault_setup_error=0,up_fault_orphan=0;\n'
            'static const unsigned rj_fault_kind=2,rj_fault_mode=3;\n'
            '#define up_fault_timeout_ms (rj_kind==rj_fault_kind ? 2000U : 150000U)\n')
        return original,['-DS22_JOURNAL_RECOVERY_FAULT']
    prefix='''#define _GNU_SOURCE
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#include <sys/mount.h>
#include <sys/ioctl.h>
#include <linux/fs.h>
#include <time.h>
#ifndef S22_ROOT_INSPECT_VIRT_TEST
#error "file fault requires virtual binding"
#endif
static int fixture_path(int fd,int directory) {
    char name[64],path[256];snprintf(name,sizeof(name),"/proc/self/fd/%d",fd);
    ssize_t n=readlink(name,path,sizeof(path)-1);if(n<0)return 0;path[n]=0;
    return directory ? !strcmp(path,"/s22-root-work/file-root/var/lib/lab") :
        !strncmp(path,"/s22-root-work/file-root/var/lib/lab/s22-evidence-",
            sizeof("/s22-root-work/file-root/var/lib/lab/s22-evidence-")-1);
}
'''
    bodies={
        'short-write':'''static unsigned fixture_writes;
static ssize_t fixture_write(int fd,const void *p,size_t n) {
    if(fixture_path(fd,0) && ++fixture_writes==4)return write(fd,p,n-1);
    return write(fd,p,n);
}
#define write fixture_write
''',
        'file-sync-error':'''static unsigned fixture_syncs;
static int fixture_fsync(int fd) {
    if(fixture_path(fd,0) && ++fixture_syncs==4){errno=EIO;return -1;}
    return fsync(fd);
}
#define fsync fixture_fsync
''',
        'parent-sync-error':'''static int fixture_fsync(int fd) {
    if(fixture_path(fd,1)){errno=EIO;return -1;}
    return fsync(fd);
}
#define fsync fixture_fsync
''',
        'unmount-error':'''static int fixture_umount(const char *path,int flags) {
    if(!strcmp(path,"/s22-root-work/file-root")){errno=EBUSY;return -1;}
    return umount2(path,flags);
}
#define umount2 fixture_umount
''',
        'late-ro-clear':'''static int fixture_late;
static int fixture_ioctl(int fd,unsigned long request,void *value) {
    int result=ioctl(fd,request,value);
    if(!result && request==BLKROSET && *(int *)value==0)fixture_late=1;
    return result;
}
static int fixture_clock(clockid_t kind,struct timespec *value) {
    int result=clock_gettime(kind,value);
    if(!result && fixture_late && kind==CLOCK_BOOTTIME){value->tv_sec=301;value->tv_nsec=0;}
    return result;
}
#define ioctl fixture_ioctl
#define clock_gettime fixture_clock
'''}
    path=out/'file-fault.c';path.write_text(prefix+bodies[fault]+'#include '+json.dumps(str(original))+'\n')
    return path,[]
