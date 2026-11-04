#define _GNU_SOURCE
#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <net/if.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#ifdef CANARY_DEBIAN_RAM
#include <sys/vfs.h>
#include <linux/magic.h>
#endif
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include "seal.h"
#include "protocol.h"

/* One bounded authenticated observation, then this observer parks. Physical
 * Download/original-A is the recovery route; no automatic reset is claimed.
 * No child, shell, executable loader, module loader or block-device API.
 */
static uint64_t deadline;
static uint8_t fdt[G0Q_FDT_LIMIT];
static size_t fdt_size;

static uint64_t now_ms(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_BOOTTIME,&t))return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
static _Noreturn void park(int error) {
    dprintf(2,"G0Q_RAM_PARK error=%d\n",error);
    for(;;) { while(waitpid(-1,NULL,WNOHANG)>0){}; struct timespec t={1,0};nanosleep(&t,NULL); }
}
static int folder(const char *path,mode_t mode) {
    if(mkdir(path,mode) && errno!=EEXIST)return errno;
    struct stat s;if(lstat(path,&s)||!S_ISDIR(s.st_mode))return EINVAL;
    return 0;
}
static int put(const char *path,const char *value) {
    int fd=open(path,O_WRONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)return errno;
    size_t n=strlen(value);ssize_t wrote=write(fd,value,n);
    int e=wrote==(ssize_t)n?0:(wrote<0?errno:EIO);
    if(close(fd)&&!e)e=errno;
    return e;
}
static int read_small(const char *path,void *buffer,size_t limit,size_t *length) {
    int fd=open(path,O_RDONLY|O_CLOEXEC);
    if(fd<0)return errno;
    size_t used=0;int error=0;
    while(used<limit) {
        ssize_t n=read(fd,(uint8_t*)buffer+used,limit-used);
        if(n<0) { if(errno==EINTR)continue;error=errno;break; }
        if(!n)break;
        used+=(size_t)n;
    }
    if(!error && used==limit) { uint8_t extra;ssize_t n=read(fd,&extra,1);if(n)error=n<0?errno:EOVERFLOW; }
    if(close(fd)&&!error)error=errno;
    if(!error)*length=used;
    return error;
}
static int network(const char *name) {
    int fd=socket(AF_INET,SOCK_DGRAM|SOCK_CLOEXEC,0);if(fd<0)return errno;
    struct ifreq r;memset(&r,0,sizeof(r));snprintf(r.ifr_name,sizeof(r.ifr_name),"%s",name);
    struct sockaddr_in *address=(struct sockaddr_in*)&r.ifr_addr;
    address->sin_family=AF_INET;
    int error=inet_pton(AF_INET,canary_device_ip,&address->sin_addr)==1?0:EINVAL;
    if(!error&&ioctl(fd,SIOCSIFADDR,&r))error=errno;
    if(!error&&inet_pton(AF_INET,canary_netmask,&address->sin_addr)!=1)error=EINVAL;
    if(!error&&ioctl(fd,SIOCSIFNETMASK,&r))error=errno;
    if(!error&&ioctl(fd,SIOCGIFFLAGS,&r))error=errno;
    r.ifr_flags|=IFF_UP;
    if(!error&&ioctl(fd,SIOCSIFFLAGS,&r))error=errno;
    if(close(fd)&&!error)error=errno;
    return error;
}
static int one_entry(const char *path,char out[NAME_MAX+1]) {
    DIR *d=opendir(path);if(!d)return errno;
    struct dirent *ent;unsigned count=0;int error=0;
    errno=0;
    while((ent=readdir(d))) {
        if(ent->d_name[0]=='.')continue;
        if(++count!=1) {error=EEXIST;break;}
        if(strlen(ent->d_name)>NAME_MAX) {error=EOVERFLOW;break;}
        strcpy(out,ent->d_name);
    }
    if(!error&&errno)error=errno;
    if(closedir(d)&&!error)error=errno;
    return error?error:(count==1?0:ENOENT);
}
static int usb(void) {
    int e;char udc[NAME_MAX+1];
    while((e=one_entry("/sys/class/udc",udc))==ENOENT && now_ms()<deadline) {
        struct timespec t={0,10000000};nanosleep(&t,NULL);
    }
    if(e)return e;
    if(strcmp(udc,canary_udc))return ENODEV;
    if(mount("configfs","/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))return errno;
    if(chdir("/config/usb_gadget"))return errno;
    /* Exclusive creation: no second gadget or adoption/rebind path. */
    if(mkdir("g0q-canary",0700))return errno;
    if(chdir("g0q-canary"))return errno;
    const struct {const char *name,*value;} attrs[]={
        {"idVendor","0x1d6b"},{"idProduct","0x0104"},{"bcdDevice","0x0100"},
        {"bcdUSB","0x0200"},{"bDeviceClass","0xef"},{"bDeviceSubClass","0x02"},
        {"bDeviceProtocol","0x01"},{"max_speed","high-speed"}};
    for(size_t i=0;i<sizeof(attrs)/sizeof(attrs[0]);i++)if((e=put(attrs[i].name,attrs[i].value)))return e;
    if((e=folder("strings/0x409",0700)))return e;
    if((e=put("strings/0x409/serialnumber",canary_serial)))return e;
    if((e=put("strings/0x409/manufacturer","Native Init Lab")))return e;
    if((e=put("strings/0x409/product","G0Q RAM Canary")))return e;
    if((e=folder("configs/c.1",0700)))return e;
    if((e=put("configs/c.1/MaxPower","250")))return e;
    if((e=put("configs/c.1/bmAttributes","0x80")))return e;
    if((e=folder("functions/ncm.usb0",0700)))return e;
    if((e=put("functions/ncm.usb0/dev_addr",canary_device_mac)))return e;
    if((e=put("functions/ncm.usb0/host_addr",canary_host_mac)))return e;
    if(symlink("functions/ncm.usb0","configs/c.1/ncm.usb0"))return errno;
    /* f_ncm registers its netdev during bind, not during configfs linking. */
    if((e=put("UDC",udc)))return e;
    if((e=network("usb0")))return e;
    return chdir("/")?errno:0;
}
static int transfer(int fd,void *buffer,size_t length,int writing) {
    size_t done=0;
    while(done<length) {
        uint64_t now=now_ms();if(now>=deadline)return ETIMEDOUT;
        struct pollfd p={fd,writing?POLLOUT:POLLIN,0};
        int rc=poll(&p,1,(int)(deadline-now));
        if(rc<0) {if(errno==EINTR)continue;return errno;}
        if(!rc)return ETIMEDOUT;
        if(p.revents&(POLLERR|POLLNVAL))return EIO;
        ssize_t n=writing?send(fd,(uint8_t*)buffer+done,length-done,MSG_NOSIGNAL):
                          recv(fd,(uint8_t*)buffer+done,length-done,0);
        if(n<0) {if(errno==EINTR||errno==EAGAIN)continue;return errno;}
        if(!n)return EPIPE;
        done+=(size_t)n;
    }
    return 0;
}
static int hash_file(const char *path,uint8_t out[32]) {
    int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return errno;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    uint8_t b[4096];size_t total=0;int error=0;
    for(;;) {
        ssize_t n=read(fd,b,sizeof(b));
        if(n<0) {if(errno==EINTR)continue;error=errno;break;}
        if(!n)break;
        total+=(size_t)n;if(total>4*1024*1024) {error=EOVERFLOW;break;}
        s22plus_max77705_runtime_sha256_update(&h,b,(size_t)n);
    }
    if(close(fd)&&!error)error=errno;
    if(!error&&!total)error=EINVAL;
    if(!error)s22plus_max77705_runtime_sha256_final(&h,out);
    return error;
}
#ifdef CANARY_DEBIAN_RAM
/* Only scalar claims leave the observer. Namespace inode numbers and process
 * status text stay local. This consistency check is joined with the reviewed
 * initial boot path; namespace equality alone cannot establish initial PID1. */
static int one_nspid(const char *path,pid_t expected) {
    char data[8192];size_t size;int e=read_small(path,data,sizeof(data)-1,&size);
    if(e)return e;
    data[size]=0;unsigned found=0;
    for(char *p=data;*p;) {
        char *end=strchr(p,'\n');if(!end)return EINVAL;
        if(!strncmp(p,"NSpid:",6)) {
            char *last;errno=0;long value=strtol(p+6,&last,10);
            if(errno||last==p+6||value!=expected)return EINVAL;
            while(last<end&&(*last==' '||*last=='\t'))last++;
            if(last!=end||++found!=1)return EINVAL;
        }
        p=end+1;
    }
    return found==1?0:EINVAL;
}
static int debian_proof(uint8_t response[G0Q_RESPONSE_SIZE]) {
    pid_t self=getpid(),parent=getppid();
    if(self<=1||parent!=1)return EINVAL;
    const char *level=getenv("RUNLEVEL"),*previous=getenv("PREVLEVEL");
    if(!level||strcmp(level,"2")||!previous||strcmp(previous,"N"))return EINVAL;
    int e=one_nspid("/proc/1/status",1);if(e)return e;
    if((e=one_nspid("/proc/self/status",self)))return e;
    struct stat own,init;
    if(stat("/proc/self/ns/pid",&own)||stat("/proc/1/ns/pid",&init))return errno;
    if(own.st_dev!=init.st_dev||own.st_ino!=init.st_ino)return EINVAL;
    if((e=hash_file("/proc/self/exe",response+288)))return e;
    if((e=hash_file("/etc/inittab",response+320)))return e;
    /* Parent must still be PID1 after all measured reads. */
    if(getppid()!=1)return EINVAL;
    g_put32(response+224,1);g_put32(response+256,(uint32_t)self);
    g_put32(response+260,(uint32_t)parent);g_put32(response+264,1);
    g_put32(response+268,'2');g_put32(response+272,'N');
    return 0;
}
#endif
static int proof(const uint8_t nonce[32],uint8_t response[G0Q_RESPONSE_SIZE]) {
    uint8_t memory[65536];
    for(size_t i=0;i<sizeof(memory);i++)memory[i]=(uint8_t)(i^(i>>8)^0xa7);
    /* Volatile read prevents the compiler replacing the check with a constant. */
    volatile const uint8_t *observed=memory;
    for(size_t i=0;i<sizeof(memory);i++)if(observed[i]!=(uint8_t)(i^(i>>8)^0xa7))return EIO;
    uint64_t before=now_ms();struct timespec delay={0,20000000};
    if(nanosleep(&delay,NULL))return errno;
    uint64_t after=now_ms();if(after<before||after-before<20||after-before>5000)return ERANGE;
    long cpus=sysconf(_SC_NPROCESSORS_ONLN);if(cpus!=1)return EINVAL;
    DIR *block=opendir("/sys/class/block");if(!block)return errno;
    struct dirent *ent;unsigned blocks=0;errno=0;
    while((ent=readdir(block)))if(ent->d_name[0]!='.')blocks++;
    int e=errno;if(closedir(block)&&!e)e=errno;
    if(e||blocks)return e?e:ENOTEMPTY;
    if((e=read_small("/sys/firmware/fdt",fdt,sizeof(fdt),&fdt_size)))return e;
    if(fdt_size<40||memcmp(fdt,"\xd0\x0d\xfe\xed",4))return EINVAL;
    uint32_t declared=(uint32_t)fdt[4]<<24|(uint32_t)fdt[5]<<16|(uint32_t)fdt[6]<<8|fdt[7];
    if(declared!=fdt_size)return EINVAL;
    char boot[40];size_t size;
    if((e=read_small("/proc/sys/kernel/random/boot_id",boot,sizeof(boot),&size)))return e;
    if(size!=37||boot[36]!='\n')return EINVAL;
    memset(response,0,G0Q_RESPONSE_SIZE);memcpy(response,G0Q_RESPONSE_MAGIC,8);
    memcpy(response+8,canary_id,32);memcpy(response+40,nonce,32);
    size_t at=72;int high=-1;
    for(size_t i=0;i<36;i++) {
        if(i==8||i==13||i==18||i==23) {if(boot[i]!='-')return EINVAL;continue;}
        int nibble=boot[i]>='0'&&boot[i]<='9'?boot[i]-'0':boot[i]>='a'&&boot[i]<='f'?boot[i]-'a'+10:-1;
        if(nibble<0)return EINVAL;
        if(high<0)high=nibble;else {response[at++]=(uint8_t)(high*16+nibble);high=-1;}
    }
    if(at!=88||high!=-1)return EINVAL;
    g_hash(fdt,fdt_size,response+88);
    if((e=hash_file("/proc/1/exe",response+120)))return e;
    struct utsname u;if(uname(&u))return errno;
    if(strlen(u.release)>=64)return EOVERFLOW;
    memcpy(response+152,u.release,strlen(u.release));
    g_put64(response+216,after);g_put32(response+224,(uint32_t)getpid());
    g_put32(response+228,(uint32_t)cpus);g_put32(response+232,blocks);
    g_put32(response+236,1);g_put64(response+240,after-before);
    g_put32(response+248,(uint32_t)fdt_size);
#ifdef CANARY_H0_VM
    g_put32(response+252,1);
#endif
#ifdef CANARY_DEBIAN_RAM
    if((e=debian_proof(response)))return e;
#endif
    g_tag(response+G0Q_BODY_SIZE,canary_key,canary_id,1,response,G0Q_BODY_SIZE);
    return 0;
}
static int serve(void) {
    int fd=socket(AF_INET,SOCK_STREAM|SOCK_CLOEXEC|SOCK_NONBLOCK,0);if(fd<0)return errno;
    struct sockaddr_in a={.sin_family=AF_INET,.sin_port=htons(CANARY_PORT)};
    int error=0,client=-1;
    if(inet_pton(AF_INET,canary_device_ip,&a.sin_addr)!=1)error=EINVAL;
    if(!error&&bind(fd,(struct sockaddr*)&a,sizeof(a)))error=errno;
    if(!error&&listen(fd,1))error=errno;
    if(!error)dprintf(2,"G0Q_RAM_OBSERVER_READY\n");
    while(!error&&client<0) {
        uint64_t now=now_ms();if(now>=deadline) {error=ETIMEDOUT;break;}
        struct pollfd p={fd,POLLIN,0};int rc=poll(&p,1,(int)(deadline-now));
        if(rc<0) {if(errno==EINTR)continue;error=errno;break;}
        if(!rc) {error=ETIMEDOUT;break;}
        struct sockaddr_in peer;socklen_t length=sizeof(peer);
        client=accept4(fd,(struct sockaddr*)&peer,&length,SOCK_CLOEXEC|SOCK_NONBLOCK);
        if(client<0) {if(errno==EAGAIN||errno==EINTR)continue;error=errno;break;}
        struct in_addr expected;
        if(length!=sizeof(peer)||peer.sin_family!=AF_INET||
           inet_pton(AF_INET,canary_host_ip,&expected)!=1||peer.sin_addr.s_addr!=expected.s_addr)error=EACCES;
    }
    if(close(fd)&&!error)error=errno;
    uint8_t request[G0Q_REQUEST_SIZE],response[G0Q_RESPONSE_SIZE];
    if(!error)error=transfer(client,request,sizeof(request),0);
    if(!error&&!g_request(request,canary_key,canary_id))error=EACCES;
    if(!error)error=proof(request+8,response);
    if(!error)error=transfer(client,response,sizeof(response),1);
    if(!error)error=transfer(client,fdt,fdt_size,1);
    if(client>=0&&close(client)&&!error)error=errno;
    return error;
}
int main(void) {
#ifdef CANARY_DEBIAN_RAM
    if(getpid()<=1||getppid()!=1)return 100;
#else
    if(getpid()!=1)return 100;
#endif
    signal(SIGPIPE,SIG_IGN);signal(SIGCHLD,SIG_DFL);
    uint64_t start=now_ms();if(start==UINT64_MAX)park(EIO);
    deadline=120000; /* Absolute boot-time limit, shared with host verification. */
    if(start>=deadline)park(ETIMEDOUT);
    const char *dirs[]={"/dev","/proc","/sys","/config"};
    for(size_t i=0;i<sizeof(dirs)/sizeof(dirs[0]);i++) {int e=folder(dirs[i],0755);if(e)park(e);}
    if(mount("devtmpfs","/dev","devtmpfs",MS_NOSUID|MS_NOEXEC,NULL))park(errno);
#ifdef CANARY_H0_VM
    const char *console="/dev/ttyAMA0";
#else
    const char *console="/dev/console";
#endif
    int fd=open(console,O_RDWR|O_CLOEXEC);
    if(fd<0)fd=open("/dev/null",O_RDWR|O_CLOEXEC);
    if(fd<0)park(errno);
    for(int n=0;n<3;n++)if(dup2(fd,n)<0)park(errno);
    if(fd>2)close(fd);
    if(mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL)) {
        int error=errno;dprintf(2,"G0Q_RAM_MOUNT_FAIL proc\n");park(error);
    }
    int sysfs_ready=0;
#ifdef CANARY_DEBIAN_RAM
    /* Packaged libselinux may leave this mounted before init starts us.
     * Accept the measured filesystem, never an EBUSY error by itself. */
    struct statfs inherited;
    if(statfs("/sys",&inherited))park(errno);
    sysfs_ready=inherited.f_type==SYSFS_MAGIC;
#endif
    if(!sysfs_ready&&mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL)) {
        int error=errno;dprintf(2,"G0Q_RAM_MOUNT_FAIL sysfs\n");park(error);
    }
    dprintf(2,"G0Q_RAM_PID1_BEGIN\n");
#ifdef CANARY_H0_VM
    int e=network("eth0");
#else
    int e=usb();
#endif
    if(e)park(e);
    park(serve());
}
