/* One Debian-PID1 child, one stock logger insertion, bounded printk stages.
 * No platform, USB, UFS, block, mount, installed execution or reboot path. */
#define FS1_READONLY_BINDING_ONLY
#include "s22plus_native_ext4_v1.c"
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <time.h>
#include "stage-seal.h"
#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-STAGE-v1"
#include "early-protocol.h"
#include "s22plus_fyg8_logger_binding_v1.h"

_Static_assert(SYS_finit_module==273,"ARM64 module syscall");
static uint8_t stage_boot[16];
static unsigned sequence;
#ifdef STAGE_VM_TEST
static int fault;
#endif

static int deadline(void) {
    struct timespec now;
    return clock_gettime(CLOCK_BOOTTIME,&now) || now.tv_sec<0 || now.tv_sec>=60 ? ETIMEDOUT : 0;
}

static int ring_write(const char *line,size_t length) {
    int reader=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(reader<0)return fs1_error();
    struct stat st;int error=0;
    if(fstat(reader,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=makedev(1,11) ||
        st.st_uid || st.st_gid || (st.st_mode&07777)!=0600 || lseek(reader,0,SEEK_END)<0)error=EPROTO;
    int writer=-1;
    if(!error) {writer=open("/dev/kmsg",O_WRONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);if(writer<0)error=fs1_error();}
    if(!error && (fstat(writer,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=makedev(1,11) ||
        st.st_uid || st.st_gid || (st.st_mode&07777)!=0600))error=EPROTO;
    if(!error && write(writer,line,length)!=(ssize_t)length)error=EIO;
    if(writer>=0 && close(writer) && !error)error=fs1_error();
    struct timespec start,now;if(clock_gettime(CLOCK_BOOTTIME,&start))error=EIO;
    size_t total=0;bool found=false;
    while(!error && !found && total<65536) {
        if(clock_gettime(CLOCK_BOOTTIME,&now)){error=EIO;break;}
        int64_t elapsed=(int64_t)(now.tv_sec-start.tv_sec)*1000000000LL+now.tv_nsec-start.tv_nsec;
        if(elapsed<0 || elapsed>=500000000LL){error=ETIMEDOUT;break;}
        char raw[2048];size_t available=65536-total;if(available>sizeof(raw))available=sizeof(raw);
        ssize_t n=read(reader,raw,available);
        if(n>0) {
            total+=(size_t)n;char *body=memchr(raw,';',(size_t)n);
            if(body && (size_t)(raw+n-body-1)==length-4 && !memcmp(body+1,line+4,length-4))found=true;
        }else if(n<0 && errno!=EAGAIN && errno!=EINTR){error=fs1_error();break;}
        else if(n==0){error=EIO;break;}
        if(clock_gettime(CLOCK_BOOTTIME,&now)){error=EIO;break;}
        elapsed=(int64_t)(now.tv_sec-start.tv_sec)*1000000000LL+now.tv_nsec-start.tv_nsec;
        if(elapsed<0 || elapsed>=500000000LL){error=ETIMEDOUT;break;}
        if(!found){struct timespec delay={0,1000000};if(nanosleep(&delay,NULL))error=fs1_error();}
    }
    if(!error && !found)error=ENOMSG;
    if(close(reader)&&!error)error=fs1_error();
    return error;
}

static int emit(unsigned kind,unsigned value,const uint8_t *detail) {
    int error=deadline();if(error)return error;
    if(++sequence>9)return EOVERFLOW;
    uint8_t data[108]={0},nonce[32];char line[160];
    memcpy(data,early_run,16);memcpy(data+16,stage_boot,16);
    early_put32(data+32,sequence);early_put32(data+36,kind);early_put32(data+40,value);
    if(detail)memcpy(data+44,detail,32);
    early_hash(stage_boot,16,nonce);early_tag(data+76,nonce,241,sequence,data,76);
    static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    memcpy(line,"<14>S22STG1[",12);size_t at=12;
    for(size_t i=0;i<sizeof(data);i+=3) {
        unsigned x=(unsigned)data[i]<<16|(unsigned)data[i+1]<<8|data[i+2];
        line[at++]=alphabet[x>>18];line[at++]=alphabet[x>>12&63];
        line[at++]=alphabet[x>>6&63];line[at++]=alphabet[x&63];
    }
    line[at++]=']';line[at++]='\n';
    return ring_write(line,at);
}

static int hash_file(const char *path,uint64_t maximum,uint8_t digest[32]) {
    int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat before,after;int error=0;
    if(fstat(fd,&before) || !S_ISREG(before.st_mode) || before.st_uid || before.st_gid ||
        before.st_size<=0 || (uint64_t)before.st_size>maximum)error=EPROTO;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    uint8_t bytes[4096];uint64_t total=0;
    while(!error) {
        ssize_t n=read(fd,bytes,sizeof(bytes));if(n<0){error=fs1_error();break;}if(!n)break;
        total+=(uint64_t)n;if(total>maximum){error=EOVERFLOW;break;}
        s22plus_max77705_runtime_sha256_update(&h,bytes,(size_t)n);
    }
    if(!error && (fstat(fd,&after) || before.st_dev!=after.st_dev || before.st_ino!=after.st_ino ||
        before.st_size!=after.st_size || total!=(uint64_t)before.st_size))error=ESTALE;
    s22plus_max77705_runtime_sha256_final(&h,digest);
    if(close(fd)&&!error)error=fs1_error();
    return error;
}

static int identity(void) {
    struct utsname name;char text[128];
#ifdef STAGE_VM_TEST
    if(fs1_read_text("/sys/firmware/devicetree/base/compatible",text,sizeof(text)) || strcmp(text,"linux,dummy-virt"))return EXDEV;
    if(fs1_read_text("/lab/fault",text,sizeof(text)))return EINVAL;
    if(!strcmp(text,"none\n"))fault=0;
    else if(!strcmp(text,"insert-error\n"))fault=2;
    else if(!strcmp(text,"binding-missing\n"))fault=3;
    else if(!strcmp(text,"late\n"))fault=4;
    else return EINVAL;
    (void)name;
#else
    if(uname(&name) || strcmp(name.release,stage_release) ||
        fs1_read_text("/sys/firmware/devicetree/base/model",text,sizeof(text)) || strcmp(text,stage_model))return EXDEV;
#endif
    if(fs1_read_text("/proc/sys/kernel/random/boot_id",text,sizeof(text)) || strlen(text)!=37 || text[36]!='\n')return EPROTO;
    unsigned at=0;
    for(unsigned i=0;i<36;) {
        if(i==8 || i==13 || i==18 || i==23){if(text[i++]!='-')return EPROTO;continue;}
        unsigned value=0;
        for(unsigned j=0;j<2;++j) {
            unsigned c=(unsigned char)text[i++];
            if(c>='0' && c<='9')c-='0';else if(c>='a' && c<='f')c=c-'a'+10;else return EPROTO;
            value=value*16+c;
        }
        if(at>=16)return EPROTO;
        stage_boot[at++]=(uint8_t)value;
    }
    return at==16 ? 0 : EPROTO;
}

static int parent(uint8_t shell[32],uint8_t init[32],uint8_t helper[32]) {
    char name[128],cmdline[64];ssize_t n=readlink("/proc/1/exe",name,sizeof(name)-1);
    if(n<=0 || (size_t)n>=sizeof(name)-1)return EPROTO;
    name[n]=0;
    if(strcmp(name,"/usr/bin/sh"))return EPROTO;
    int fd=open("/proc/1/cmdline",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    n=read(fd,cmdline,sizeof(cmdline));int closed=close(fd);static const char wanted[]="/bin/sh\0/init\0";
    if(n!=(ssize_t)sizeof(wanted)-1 || closed || memcmp(cmdline,wanted,sizeof(wanted)-1))return EPROTO;
    int error=hash_file("/proc/1/exe",4*1024*1024,shell);
    if(!error)error=hash_file("/init",65536,init);
    if(!error)error=hash_file("/proc/self/exe",4*1024*1024,helper);
    if(!error && (memcmp(shell,early_shell_hash,32) || memcmp(init,early_init_hash,32)))error=EPROTO;
    return error;
}

static int module_present(void) {
#ifdef STAGE_VM_TEST
    return 0;
#else
    struct stat st;if(!lstat("/sys/module/sec_log_buf",&st))return EEXIST;
    return errno==ENOENT ? 0 : fs1_error();
#endif
}

static int insert(int fd) {
#ifdef STAGE_VM_TEST
    (void)fd;
    static const char marker[]="STAGE_VM_INSERT_ONCE\n";
    if(write(1,marker,sizeof(marker)-1)!=(ssize_t)sizeof(marker)-1)return EIO;
    return fault==2 ? EIO : 0;
#else
    return syscall(SYS_finit_module,fd,"",0) ? fs1_error() : 0;
#endif
}

static int binding(void) {
#ifdef STAGE_VM_TEST
    return fault==3 ? ENODEV : 0;
#else
    /* Read-only probe settlement only. No reinsertion, ioctl or repair. */
    for(unsigned i=0;i<200;++i) {
        int error=deadline();if(error)return error;
        unsigned phase;error=s22_logger_probe(S22_LOGGER_NEED_LAST,&phase);
        if(!error)return 0;
        if(error!=ENOENT)return error;
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL))return fs1_error();
    }
    return ENODEV;
#endif
}

int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getpid()==1 || getppid()!=1 || getuid() || geteuid() || getgid() || getegid())return 100;
    struct stat st;struct statfs fs;int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(dir<0 || fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
        fstatfs(dir,&fs) || (unsigned long)fs.f_type!=0x01021994UL)return 101;
    if(close(dir) || identity())return 102;
#ifdef STAGE_VM_TEST
    if(fault==4){struct timespec delay={61,0};if(nanosleep(&delay,NULL))return 103;}
#endif
    int error=emit(1,(unsigned)getpid(),NULL);if(error)return 1;
    uint8_t shell[32],init[32],helper[32];error=parent(shell,init,helper);
    if(error){(void)emit(9,(unsigned)error,NULL);return 1;}
    if(emit(2,0,shell) || emit(3,0,init) || emit(4,0,helper))return 1;
    error=module_present();int fd=-1;
    if(!error){fd=fs1_pin_file("/lab/modules/sec_log_buf.ko",STAGE_LOGGER_SIZE,stage_logger_hash,false);if(fd<0)error=fs1_error();}
    if(error){(void)emit(9,(unsigned)error,NULL);return 1;}
    error=emit(5,0,stage_logger_hash);
    if(error){close(fd);return 1;}
    error=deadline();if(!error)error=module_present();
    if(error){close(fd);(void)emit(9,(unsigned)error,NULL);return 1;}
    error=insert(fd);if(close(fd)&&!error)error=fs1_error();
    if(emit(6,(unsigned)error,NULL) || error)return 1;
    error=binding();if(error){(void)emit(9,(unsigned)error,NULL);return 1;}
    if(emit(7,0,NULL) || emit(8,0,NULL))return 1;
    return 0;
}
