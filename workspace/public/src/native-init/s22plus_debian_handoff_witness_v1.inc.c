#include "s22plus_debian_handoff_common_v1.inc.c"
#include "s22plus_debian_handoff_payload_v1.h"
static int dh_write(const char *path,const void *data,size_t size,mode_t mode) {
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,mode);
    if(fd<0)return fs1_error();
    int error=write(fd,data,size)==(ssize_t)size ? 0 : EIO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
/* Only inherited RAM /dev aliases are removed. Never follow a symlink or
 * recurse into another filesystem, and retain the one exact native node. */
static int dh_prune(int fd,dev_t ram,unsigned depth,unsigned *count,int native_parent) {
    if(depth>8)return EOVERFLOW;
    int copy=dup(fd);if(copy<0)return fs1_error();DIR *d=fdopendir(copy);
    if(!d){close(copy);return fs1_error();}int error=0;
    for(;;) {
        errno=0;struct dirent *entry=readdir(d);
        if(!entry){if(errno)error=errno;break;}
        if(!strcmp(entry->d_name,".") || !strcmp(entry->d_name,".."))continue;
        if(++*count>4096){error=EOVERFLOW;break;}
        struct stat st;
        if(fstatat(fd,entry->d_name,&st,AT_SYMLINK_NOFOLLOW) || st.st_dev!=ram){error=EPROTO;break;}
        if(S_ISBLK(st.st_mode)) {
            if(st.st_rdev==(dev_t)sw.root_device && !strcmp(entry->d_name,"native") && native_parent)continue;
            if(unlinkat(fd,entry->d_name,0)){error=fs1_error();break;}
        } else if(S_ISDIR(st.st_mode)) {
            int child=openat(fd,entry->d_name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
            if(child<0){error=fs1_error();break;}
            error=dh_prune(child,ram,depth+1,count,depth==0 && !strcmp(entry->d_name,".s22-ext4-v1"));
            if(close(child) && !error)error=fs1_error();
            if(error)break;
        }
    }
    if(closedir(d) && !error)error=fs1_error();
    return error;
}
static void dh_overlay(const char *source,const char *target) {
    struct stat a,b;
    if(lstat(source,&a) || lstat(target,&b) || !S_ISREG(a.st_mode) || !S_ISREG(b.st_mode) ||
       a.st_dev==(dev_t)sw.root_device || b.st_dev!=(dev_t)sw.root_device || a.st_uid || b.st_uid ||
       mount(source,target,NULL,MS_BIND,NULL) ||
       mount(NULL,target,NULL,MS_REMOUNT|MS_BIND|MS_RDONLY|MS_NOSUID|MS_NODEV,NULL))sw_stop(EPROTO);
}
static __attribute__((noreturn)) void dh_exec_init(void) {
    dh_request(DH_CONTINUE,6,DH_CONTINUE_ACK);
    sw_require(dh_pin_init());sw_require(sw_no_children());sw_require(sw_userspace());
    if(mount(NULL,"/run",NULL,MS_REMOUNT|MS_NOSUID|MS_NODEV,"size=32m,nr_inodes=4096,mode=0755") ||
       chmod("/run",0755))sw_stop(fs1_error());
    sw_require(dh_write("/run/.tmpfs","",0,0600));
    int dev=open("/dev",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);struct stat st;unsigned count=0;
    if(dev<0 || fstat(dev,&st))sw_stop(fs1_error());
    sw_require(dh_prune(dev,st.st_dev,0,&count,0));if(close(dev))sw_stop(fs1_error());
    if(mkdir("/dev/pts",0755) || mkdir("/dev/shm",01777) ||
       mount("devpts","/dev/pts","devpts",MS_NOSUID|MS_NOEXEC,"newinstance,ptmxmode=0666,mode=0620,gid=5") ||
       mount("tmpfs","/dev/shm","tmpfs",MS_NOSUID|MS_NODEV,"size=16m,nr_inodes=1024,mode=1777"))sw_stop(fs1_error());
    if(lstat("/dev/ptmx",&st)==0) {if(!S_ISCHR(st.st_mode) || unlink("/dev/ptmx"))sw_stop(EPROTO);}
    else if(errno!=ENOENT)sw_stop(fs1_error());
    const char *links[][2]={{"pts/ptmx","/dev/ptmx"},{"/proc/self/fd","/dev/fd"},
        {"/proc/self/fd/0","/dev/stdin"},{"/proc/self/fd/1","/dev/stdout"},{"/proc/self/fd/2","/dev/stderr"}};
    for(unsigned i=0;i<sizeof(links)/sizeof(links[0]);++i)if(symlink(links[i][0],links[i][1]))sw_stop(fs1_error());
    dh_overlay("/run/s22-debian/inittab","/etc/inittab");
    dh_overlay("/run/s22-debian/qualify","/usr/local/sbin/lab-qualify");
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dh_overlay("/run/s22-debian/usb","/etc/init.d/lab-usb");
#endif
    char log[256];int n=snprintf(log,sizeof(log),"%sBOOTSTRAP_HANDOFF pid=1 children=0 backend=s22plus-fyg8\n",dh_boot_identity);
    if(n<=0 || n>=(int)sizeof(log))sw_stop(EOVERFLOW);
    sw_require(dh_write("/run/lab-bootstrap.log",log,(size_t)n,0400));
    struct dh_state state={.native=sw};memcpy(state.hook_sha,dh_assets[0].digest,32);
#if S22_DEBIAN_FAULT == 4
    state.native.boot[0]^=1;
#endif
    sw_tag(state.tag,DH_STATE_TAG,0,(const uint8_t *)&state,sizeof(state)-32);
#if S22_DEBIAN_FAULT == 3
    state.tag[0]^=1;
#endif
    sw_require(dh_write(DH_STATE_PATH,&state,sizeof(state),0400));
    int fd=open(DH_STATE_PATH,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);struct dh_state check;
    if(fd<0 || read(fd,&check,sizeof(check))!=sizeof(check) || memcmp(&check,&state,sizeof(check)) || close(fd))sw_stop(EIO);
    /* SysVinit closes only stdio itself. These flags and the explicit close
     * prevent the installed PID1 from retaining native ACM or sealed state. */
#if S22_DEBIAN_FAULT != 5
    if(fcntl(3,F_SETFD,FD_CLOEXEC))sw_stop(fs1_error());
#endif
    if(syscall(SYS_close_range,4U,UINT_MAX,0U))sw_stop(fs1_error());
#if S22_DEBIAN_FAULT == 6
    int leaked=open(DH_STATE_PATH,O_RDONLY|O_NOFOLLOW);
    if(leaked!=4)sw_stop(EPROTO);
#endif
    char *args[]={"/sbin/init",NULL};char *env[]={"PATH=/usr/sbin:/usr/bin:/sbin:/bin","LC_ALL=C",NULL};
    execve("/sbin/init",args,env);sw_stop(fs1_error());
}
