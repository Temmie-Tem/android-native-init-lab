/* Child of Debian /init: fixed ACM evidence exporter. No CONTROL, shell,
 * filesystem mount or installed-code execution. Configfs is its only mount. */
#define FS1_READONLY_BINDING_ONLY
#include "s22plus_native_ext4_v1.c"
#include <poll.h>
#include <termios.h>
#include <time.h>
#include <sys/utsname.h>
#include "early-seal.h"
#include "early-protocol.h"
static uint8_t log_bytes[EARLY_LIMIT],proof[176],nonce[32];
static size_t log_size;
static uint64_t deadline;

static uint64_t now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_BOOTTIME,&t) || t.tv_sec<0) return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
static int transfer(int fd,void *data,size_t size,bool output) {
    uint8_t *p=data;
    while(size) {
        if(now()>=deadline)return ETIMEDOUT;
        ssize_t n=output?write(fd,p,size):read(fd,p,size);
        if(n>0) {p+=n;size-=(size_t)n;continue;}
        if(n<0 && (errno==EAGAIN || errno==EINTR)) {
            struct pollfd item={fd,output?POLLOUT:POLLIN,0};
            if(poll(&item,1,20)<0 && errno!=EINTR)return fs1_error();
            continue;
        }
        return n?fs1_error():EIO;
    }
    return 0;
}
static int emit(int fd,unsigned kind,unsigned seq,const void *data,size_t size) {
    if(size>EARLY_CHUNK)return EOVERFLOW;
    uint8_t frame[16+EARLY_CHUNK+32]={'S','3','2','8',1,(uint8_t)kind};
    frame[6]=(uint8_t)(size+32);frame[7]=(uint8_t)((size+32)>>8);
    early_put32(frame+8,seq);memcpy(frame+16,data,size);
    early_tag(frame+16+size,nonce,kind,seq,data,size);
    early_put32(frame+12,~early_crc(frame+16,size+32,early_crc(frame,12,~0U)));
    return transfer(fd,frame,size+48,true);
}
static int request(int fd) {
    uint8_t frame[80],tag[32];int error=transfer(fd,frame,sizeof(frame),false);
    if(error)return error;
    if(memcmp(frame,"S328",4) || frame[4]!=1 || frame[5]!=EARLY_REQUEST ||
        frame[6]!=64 || frame[7] || early_u32(frame+8)!=1 ||
        early_u32(frame+12)!=~early_crc(frame+16,64,early_crc(frame,12,~0U)))return EPROTO;
    memcpy(nonce,frame+16,32);early_tag(tag,nonce,EARLY_REQUEST,1,NULL,0);
    unsigned different=0,nonzero=0;
    for(unsigned i=0;i<32;++i) {different|=tag[i]^frame[48+i];nonzero|=nonce[i];}
    return different || !nonzero ? EACCES:0;
}
static int file_hash(const char *path,uint64_t maximum,uint8_t hash[32]) {
    int fd=open(path,O_RDONLY|O_CLOEXEC); /* /proc/1/exe is an intended proc link. */
    if(fd<0)return fs1_error();
    struct stat before,after;int error=0;
    if(fstat(fd,&before) || !S_ISREG(before.st_mode) || before.st_uid || before.st_gid ||
        before.st_size<=0 || (uint64_t)before.st_size>maximum)error=EPROTO;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    uint8_t data[4096];uint64_t total=0;
    while(!error) {
        ssize_t n=read(fd,data,sizeof(data));
        if(n<0){error=fs1_error();break;}if(!n)break;
        total+=(uint64_t)n;if(total>maximum){error=EOVERFLOW;break;}
        s22plus_max77705_runtime_sha256_update(&h,data,(size_t)n);
    }
    if(!error && (fstat(fd,&after) || before.st_dev!=after.st_dev || before.st_ino!=after.st_ino ||
        before.st_size!=after.st_size || total!=(uint64_t)before.st_size))error=ESTALE;
    s22plus_max77705_runtime_sha256_final(&h,hash);
    if(close(fd)&&!error)error=fs1_error();
    return error;
}
static int measure(unsigned status) {
    char name[128],cmdline[64],boot[38];
    if(getpid()==1 || getppid()!=1 || getuid() || geteuid() || getgid() || getegid())return EACCES;
    ssize_t n=readlink("/proc/1/exe",name,sizeof(name)-1);
    if(n<=0 || (size_t)n>=sizeof(name)-1)return EPROTO;
    name[n]=0;
    if(strcmp(name,"/usr/bin/sh"))return EPROTO;
    int fd=open("/proc/1/cmdline",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return fs1_error();
    n=read(fd,cmdline,sizeof(cmdline));int closed=close(fd);
    static const char wanted[]="/bin/sh\0/init\0";
    if(n!=(ssize_t)sizeof(wanted)-1 || closed || memcmp(cmdline,wanted,sizeof(wanted)-1))return EPROTO;
    uint8_t shell[32],init[32],helper[32];int error=file_hash("/proc/1/exe",4*1024*1024,shell);
    if(!error)error=file_hash("/init",65536,init);
    if(!error)error=file_hash("/sbin/fyg8-prepare",4*1024*1024,helper);
    if(error || memcmp(shell,early_shell_hash,32) || memcmp(init,early_init_hash,32) ||
        memcmp(helper,early_helper_hash,32))return EPROTO;
    if(fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot)) ||
        strlen(boot)!=37 || boot[36]!='\n')return EPROTO;
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;struct statfs fs;
    if(dir<0 || fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
        fstatfs(dir,&fs) || (unsigned long)fs.f_type!=0x01021994UL)return EPROTO;
    fd=openat(dir,"fyg8-events",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(close(dir) || fd<0)return EIO;
    if(fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid || st.st_nlink!=1 ||
        (st.st_mode&07777)!=0400 || st.st_size<=0 || st.st_size>EARLY_LIMIT)error=EPROTO;
    if(!error){log_size=(size_t)st.st_size;if(read(fd,log_bytes,log_size)!=(ssize_t)log_size)error=EIO;}
    uint8_t extra;if(!error && read(fd,&extra,1)!=0)error=EPROTO;
    if(close(fd)&&!error)error=EIO;
    if(error)return error;
    /* The host validates the complete structured log including original boot.
     * This proof independently binds the currently observed parent and bytes. */
    early_put32(proof,1);early_put32(proof+4,(uint32_t)getpid());
    early_put32(proof+8,status);early_put32(proof+12,(uint32_t)log_size);
    early_hash(boot,36,proof+16);memcpy(proof+48,shell,32);memcpy(proof+80,init,32);
    early_hash(log_bytes,log_size,proof+112);memcpy(proof+144,helper,32);
    return 0;
}
static int write_fixed(const char *path,const char *value) {
    int fd=open(path,O_WRONLY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return fs1_error();
    size_t size=strlen(value);int error=write(fd,value,size)==(ssize_t)size?0:EIO;
    if(close(fd)&&!error)error=fs1_error();
    return error;
}
static int gadget(void) {
#ifdef EARLY_VM_TEST
    return 0;
#else
    struct utsname u;char model[128];
    if(uname(&u) || strcmp(u.release,early_release) ||
        fs1_read_text("/sys/firmware/devicetree/base/model",model,sizeof(model)) ||
        strcmp(model,early_model))return EXDEV;
    for(unsigned i=0;i<sizeof(early_module_names)/sizeof(early_module_names[0]);++i) {
        char path[128];struct stat st;
        snprintf(path,sizeof(path),"/sys/module/%s",early_module_names[i]);
        if(lstat(path,&st) || !S_ISDIR(st.st_mode) || st.st_uid)return ENODEV;
    }
    if(mount("configfs","/sys/kernel/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))return fs1_error();
    if(fs1_empty_directory("/sys/kernel/config/usb_gadget"))return EBUSY;
    static const char *dirs[]={"g1","g1/strings/0x409","g1/configs/c.1","g1/functions/acm.usb0"};
    char path[PATH_MAX];
    for(unsigned i=0;i<sizeof(dirs)/sizeof(dirs[0]);++i) {
        snprintf(path,sizeof(path),"/sys/kernel/config/usb_gadget/%s",dirs[i]);
        if(mkdir(path,0755))return fs1_error();
    }
    static const char *paths[]={"g1/idVendor","g1/idProduct","g1/strings/0x409/serialnumber",
        "g1/strings/0x409/product","g1/strings/0x409/manufacturer"};
    const char *values[]={"0x04e8","0x6861",early_serial,"S22 Debian early evidence","Linux"};
    for(unsigned i=0;i<sizeof(paths)/sizeof(paths[0]);++i) {
        snprintf(path,sizeof(path),"/sys/kernel/config/usb_gadget/%s",paths[i]);
        int error=write_fixed(path,values[i]);if(error)return error;
    }
    if(symlink("../../functions/acm.usb0","/sys/kernel/config/usb_gadget/g1/configs/c.1/acm.usb0"))return fs1_error();
    return write_fixed("/sys/devices/platform/soc/a600000.ssusb/mode","peripheral");
#endif
}
static int gadget_bind(void) {
#ifdef EARLY_VM_TEST
    return 0;
#else
    int error=write_fixed("/sys/kernel/config/usb_gadget/g1/UDC","a600000.dwc3");
    if(error)return error;
    char text[128];
    if(fs1_read_text("/sys/kernel/config/usb_gadget/g1/UDC",text,sizeof(text)) ||
        strcmp(text,"a600000.dwc3\n"))return EPROTO;
    return 0;
#endif
}
static int serial_open(void) {
#ifdef EARLY_VM_TEST
    const char *sys="/sys/class/tty/hvc0",*path="/dev/early-virt";
#else
    const char *sys="/sys/class/tty/ttyGS0",*path="/dev/ttyGS0";
#endif
    dev_t number;int error=ENOENT;
    for(unsigned attempt=0;attempt<50 && now()<deadline;++attempt) {
        error=fs1_device_number(sys,&number);
        if(error!=ENOENT)break;
        struct timespec delay={0,100000000};
        if(nanosleep(&delay,NULL))break;
    }
    if(error)return -1;
    if(mknod(path,S_IFCHR|0600,number))return -1;
    int fd=open(path,O_RDWR|O_NOCTTY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return -1;
    struct stat st;
    if(fstat(fd,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=number || st.st_uid || st.st_gid){close(fd);return -1;}
    struct termios tty;
    if(tcgetattr(fd,&tty)){close(fd);return -1;}
    cfmakeraw(&tty);tty.c_cflag|=CLOCAL|CREAD;
    if(tcsetattr(fd,TCSANOW,&tty)){close(fd);return -1;}
    return fd;
}
int main(int argc,char **argv) {
    if(argc!=2 || (strcmp(argv[1],"0") && strcmp(argv[1],"1") && strcmp(argv[1],"2")))return 100;
    uint64_t start=now();if(start==UINT64_MAX)return 101;deadline=start+EARLY_TIMEOUT;
    int error=measure((unsigned)(argv[1][0]-'0'));
    if(!error)error=gadget();
    int fd=-1;if(!error){fd=serial_open();if(fd<0)error=EIO;}
    /* Prepare the tty before publishing UDC: no host request can enter a
     * default canonical line discipline during initial enumeration. */
    if(!error)error=gadget_bind();
#ifdef EARLY_VM_TEST
    if(!error && dprintf(1,"EARLY_VM_WIRE_READY\n")<0)error=EIO;
#endif
    if(!error)error=request(fd);
    if(!error)error=emit(fd,EARLY_PROOF,2,proof,sizeof(proof));
    unsigned seq=3;
    for(size_t off=0;!error && off<log_size;off+=EARLY_CHUNK) {
        size_t size=log_size-off<EARLY_CHUNK?log_size-off:EARLY_CHUNK;
        error=emit(fd,EARLY_LOG,seq++,log_bytes+off,size);
    }
    if(!error)error=emit(fd,EARLY_END,seq,proof+112,32);
    if(fd>=0 && close(fd)&&!error)error=EIO;
    return error?1:0;
}
