/* One fixed native-origin calibration of early import and live retained logging.
 * A bounded root child owns the one module syscall; PID1 never calls it here. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>
#include "s22plus_fyg8_max77705_result_parser.inc.c"
#include "log-calibration-seal.h"
#define EARLY_DOMAIN "S22PLUS-FYG8-NATIVE-LOG-CAL-v1"
#include "early-protocol.h"
#include "s22plus_fyg8_logger_binding_v1.h"

_Static_assert(SYS_finit_module==273 && O_DIRECTORY==040000 && O_NOFOLLOW==0100000,
               "exact ARM64 syscall/path ABI");
_Static_assert(O_NONBLOCK==04000 && O_CLOEXEC==02000000,"exact ARM64 descriptor ABI");
#define LC_LIMIT (4U*1024U*1024U)
#define LC_FRAME 153U
static const char node[]="log-calibration-kmsg";
static uint8_t boot[16],self_hash[32];
static char boot_text[38],frames[2][LC_FRAME];
static uint64_t started;
static unsigned stage,attempted,returned,bound,ring[2],written[2],backend_eof;
static unsigned counts[2],offsets[2],module_errno;
static size_t backend_bytes;
static uint8_t backend_sha[32];
static char backend_frames[2][LC_FRAME];
#ifdef LC_VM
static int fault;
#endif

static int err(void){return errno>0 && errno<=4095?errno:EIO;}
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_BOOTTIME,&t))return 0;
    return (uint64_t)t.tv_sec*1000000000ULL+(unsigned long)t.tv_nsec;}
static int deadline(void){uint64_t n=now();return !n || n<started || n-started>=15000000000ULL?ETIMEDOUT:0;}
static int output(const char *fmt,...){char b[2048];va_list a;va_start(a,fmt);int n=vsnprintf(b,sizeof(b),fmt,a);va_end(a);
    if(n<0 || (size_t)n>=sizeof(b))return EOVERFLOW;
    return write(1,b,(size_t)n)==n?0:EIO;}
static int step(unsigned n){stage=n;return deadline()?ETIMEDOUT:output("LC1_STEP stage=%u\n",n);}
static void hex(const uint8_t *p,size_t n,char *s){static const char h[]="0123456789abcdef";
    for(size_t i=0;i<n;++i){s[i*2]=h[p[i]>>4];s[i*2+1]=h[p[i]&15];}s[n*2]=0;}
static int text(const char *path,char *b,size_t size){int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return err();
    ssize_t n=read(fd,b,size);int e=n<=0 || (size_t)n>=size?EIO:0;
    if(n>=0 && (size_t)n<size)b[n]=0;
    if(close(fd)&&!e)e=err();
    return e;}
static int hash_fd(int fd,uint64_t limit,uint8_t hash[32]){
    struct stat a,z;if(fstat(fd,&a)||!S_ISREG(a.st_mode)||a.st_uid||a.st_gid||a.st_size<=0||(uint64_t)a.st_size>limit)return EPROTO;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    uint8_t b[4096];uint64_t total=0;int error=0;
    for(;;){ssize_t n=read(fd,b,sizeof(b));if(n<0){error=err();break;}if(!n)break;
        total+=(uint64_t)n;if(total>limit){error=EOVERFLOW;break;}s22plus_max77705_runtime_sha256_update(&h,b,(size_t)n);}
    if(!error&&(fstat(fd,&z)||a.st_dev!=z.st_dev||a.st_ino!=z.st_ino||a.st_size!=z.st_size||total!=(uint64_t)a.st_size))error=ESTALE;
    s22plus_max77705_runtime_sha256_final(&h,hash);return error;
}
static int identity(void){struct utsname u;char b[128];
#ifdef LC_VM
    (void)u;if(text("/lab/fault",b,sizeof(b)))return EINVAL;
    const char *cases[]={"normal\n","insert-error\n","binding-missing\n","logger-off\n","backend-absent\n","backend-missing\n","existing\n","bad-module\n","alias-exists\n"};
    fault=-1;for(unsigned i=0;i<9;++i)if(!strcmp(b,cases[i]))fault=(int)i;if(fault<0)return EINVAL;
#else
    if(uname(&u)||strcmp(u.release,lc_release)||text("/sys/firmware/devicetree/base/model",b,sizeof(b))||strcmp(b,lc_model))return EXDEV;
#endif
    if(text("/proc/sys/kernel/random/boot_id",boot_text,sizeof(boot_text))||strlen(boot_text)!=37||boot_text[36]!='\n')return EPROTO;
    boot_text[36]=0;unsigned at=0;
    for(unsigned i=0;i<36;){if(i==8||i==13||i==18||i==23){if(boot_text[i++]!='-')return EPROTO;continue;}
        unsigned v=0;for(unsigned j=0;j<2;++j){unsigned c=(unsigned char)boot_text[i++];
            if(c>='0'&&c<='9')c-='0';else if(c>='a'&&c<='f')c=c-'a'+10;else return EPROTO;v=v*16+c;}boot[at++]=(uint8_t)v;}
    int fd=open("/proc/self/exe",O_RDONLY|O_CLOEXEC);if(fd<0)return err();int e=hash_fd(fd,4*1024*1024,self_hash);
    if(close(fd)&&!e)e=err();
    return at==16?e:EPROTO;
}
static int module_absent(void){
#ifdef LC_VM
    return fault==6?EEXIST:0;
#else
    struct stat s;if(!lstat("/sys/module/sec_log_buf",&s))return EEXIST;return errno==ENOENT?0:err();
#endif
}
static int logger_bind(void){
#ifdef LC_VM
    return fault==2?ENODEV:0;
#else
    for(unsigned i=0;i<200;++i){unsigned phase;int e=deadline();if(e)return e;
        e=s22_logger_probe(S22_LOGGER_NEED_AP,&phase);
        if(!e)return 0;
        if(e!=ENOENT)return e;
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL))return err();}return ENODEV;
#endif
}
static void frame(unsigned sequence){uint8_t data[108]={0},nonce[32];char *s=frames[sequence-1];
    memcpy(data,early_run,16);memcpy(data+16,boot,16);early_put32(data+32,sequence);early_put32(data+36,sequence);
    early_put32(data+40,(unsigned)getpid());memcpy(data+44,self_hash,32);early_hash(boot,16,nonce);
    early_tag(data+76,nonce,242,sequence,data,76);memcpy(s,"S22CAL1[",8);size_t at=8;
    static const char a[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    for(size_t i=0;i<sizeof(data);i+=3){unsigned x=(unsigned)data[i]<<16|(unsigned)data[i+1]<<8|data[i+2];
        s[at++]=a[x>>18];s[at++]=a[x>>12&63];s[at++]=a[x>>6&63];s[at++]=a[x&63];}s[at]=']';
}
static int ring_emit(int dir,unsigned sequence){frame(sequence);char line[158];memcpy(line,"<14>",4);
    memcpy(line+4,frames[sequence-1],LC_FRAME);line[157]='\n';
    int rd=openat(dir,node,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);if(rd<0)return err();
    struct stat s;int e=0,wr=-1;if(fstat(rd,&s)||!S_ISCHR(s.st_mode)||s.st_rdev!=makedev(1,11)||s.st_uid||s.st_gid||(s.st_mode&07777)!=0600||lseek(rd,0,SEEK_END)<0)e=EPROTO;
    if(!e){wr=openat(dir,node,O_WRONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);if(wr<0)e=err();}
    if(!e&&(fstat(wr,&s)||!S_ISCHR(s.st_mode)||s.st_rdev!=makedev(1,11)||s.st_uid||s.st_gid||(s.st_mode&07777)!=0600))e=EPROTO;
    if(!e){if(write(wr,line,sizeof(line))!=(ssize_t)sizeof(line))e=EIO;else written[sequence-1]=1;}
    if(wr>=0&&close(wr)&&!e)e=err();
    uint64_t start=now();size_t total=0;
    while(!e&&!ring[sequence-1]&&total<65536){uint64_t n=now();if(!n||n<start||n-start>=500000000ULL){e=ETIMEDOUT;break;}
        char raw[2048];size_t cap=65536-total;if(cap>sizeof(raw))cap=sizeof(raw);ssize_t len=read(rd,raw,cap);
        if(len>0){total+=(size_t)len;char *body=memchr(raw,';',(size_t)len);
            if(body&&(size_t)(raw+len-body-1)==sizeof(line)-4&&!memcmp(body+1,line+4,sizeof(line)-4))ring[sequence-1]=1;
        }else if(!len){e=EIO;break;}else if(errno!=EAGAIN&&errno!=EINTR){e=err();break;}
        if(!ring[sequence-1]){struct timespec delay={0,1000000};if(nanosleep(&delay,NULL))e=err();}}
    if(!e&&!ring[sequence-1])e=ENOMSG;
    if(close(rd)&&!e)e=err();
    return e;
}
static int backend(void){const char *path="/proc/ap_klog";
#ifdef LC_VM
    path="/run/lc-backend";if(fault==4)return ENOENT;
    int writer=open(path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0400);if(writer<0)return err();
    int e=0;if(fault!=5){if(write(writer,frames[0],LC_FRAME)!=LC_FRAME||write(writer,frames[1],LC_FRAME)!=LC_FRAME)e=EIO;}
    else if(write(writer,"unrelated\n",10)!=10)e=EIO;
    if(close(writer)&&!e)e=err();
    if(e)return e;
#endif
    /* Opening only now avoids the stock descriptor-cached pre-emission snapshot. */
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return err();struct stat s;struct statfs fs;
    int error=0;if(fstat(fd,&s)||!S_ISREG(s.st_mode)||s.st_uid||s.st_gid||fstatfs(fd,&fs))error=EPROTO;
#ifndef LC_VM
    if(!error&&(unsigned long)fs.f_type!=0x9fa0UL)error=EPROTO;
#else
    if(!error&&(unsigned long)fs.f_type!=0x01021994UL)error=EPROTO;
#endif
    uint8_t *buf=malloc(LC_LIMIT+1U);if(!buf&&!error)error=ENOMEM;
    while(!error){if(deadline()){error=ETIMEDOUT;break;}size_t cap=LC_LIMIT+1U-backend_bytes;
        if(!cap){error=EOVERFLOW;break;}ssize_t n=read(fd,buf+backend_bytes,cap>65536?65536:cap);
        if(n<0){error=err();break;}if(!n){backend_eof=1;break;}backend_bytes+=(size_t)n;
        if(backend_bytes>LC_LIMIT){error=EOVERFLOW;break;}}
    if(close(fd)&&!error)error=err();
    if(buf){early_hash(buf,backend_bytes,backend_sha);
        if(!error)for(unsigned j=0;j<2;++j)for(size_t i=0;i+LC_FRAME<=backend_bytes;++i)
            if(!memcmp(buf+i,frames[j],LC_FRAME)){if(!counts[j]){offsets[j]=(unsigned)i;memcpy(backend_frames[j],buf+i,LC_FRAME);}++counts[j];}
        free(buf);}
    if(!error&&(counts[0]!=1||counts[1]!=1||offsets[0]+LC_FRAME>offsets[1]))error=ENOMSG;
    return error;
}
static int finish(int error,int cleanup){char a[LC_FRAME*2+1],b[LC_FRAME*2+1],c[LC_FRAME*2+1],d[LC_FRAME*2+1],hash[65];
    hex((uint8_t *)frames[0],LC_FRAME,a);hex((uint8_t *)frames[1],LC_FRAME,b);
    hex((uint8_t *)backend_frames[0],LC_FRAME,c);hex((uint8_t *)backend_frames[1],LC_FRAME,d);hex(backend_sha,32,hash);
    return output("LC1_RESULT stage=%u errno=%d attempted=%u returned=%u module_errno=%u bound=%u pre_written=%u pre_ring=%u post_written=%u post_ring=%u backend_bytes=%zu backend_eof=%u pre_count=%u post_count=%u pre_offset=%u post_offset=%u cleanup_errno=%d\nLC1_PRE frame=%s\nLC1_POST frame=%s\nLC1_BACKEND_PRE frame=%s\nLC1_BACKEND_POST frame=%s\nLC1_BACKEND sha256=%s\n",stage,error,attempted,returned,module_errno,bound,written[0],ring[0],written[1],ring[1],backend_bytes,backend_eof,counts[0],counts[1],offsets[0],offsets[1],cleanup,a,b,c,d,hash)?1:0;
}
int main(int argc,char **argv){started=now();
    if(argc!=3||strcmp(argv[1],"calibrate")||strcmp(argv[2],lc_run)||getpid()<=1||getuid()||geteuid()||getgid()||getegid())return 100;
    int error=identity();if(error)return 101;char sha[65];hex(self_hash,32,sha);
    if(output("LC1_BEGIN version=1 run=%s boot=%s pid=%u helper=%s\n",lc_run,boot_text,(unsigned)getpid(),sha))return 102;
    int dir=-1,fd=-1,cleanup=0;bool owned=false;
    if((error=step(1)))goto done;
    dir=open("/dev",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(dir<0){error=err();goto done;}
    struct stat s;struct statfs fs;
    if(fstat(dir,&s)||!S_ISDIR(s.st_mode)||s.st_uid||s.st_gid||(s.st_mode&0022)||fstatfs(dir,&fs)||((unsigned long)fs.f_type!=0x01021994UL&&(unsigned long)fs.f_type!=0x858458f6UL)){error=EPROTO;goto done;}
    if((error=module_absent()))goto done;
    fd=open("/s22-log-module.ko",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0){error=err();goto done;}
    uint8_t hash[32];if(fstat(fd,&s)||s.st_nlink!=1||(s.st_mode&07777)!=0400||(uint64_t)s.st_size!=LC_MODULE_SIZE){error=EPROTO;goto done;}
    error=hash_fd(fd,LC_MODULE_SIZE,hash);if(!error&&memcmp(hash,lc_module_hash,32))error=EPROTO;if(error)goto done;
    if(lseek(fd,0,SEEK_SET)<0){error=err();goto done;}
    if(mknodat(dir,node,S_IFCHR|0600,makedev(1,11))){error=err();goto done;}owned=true;
    if((error=step(2))||(error=ring_emit(dir,1)))goto done;
    if((error=step(3))||(error=module_absent())||(error=deadline()))goto done;
    attempted=1;
#ifdef LC_VM
    error=fault==1?EIO:0;
#else
    error=syscall(SYS_finit_module,fd,"",0)?err():0;
#endif
    returned=1;module_errno=(unsigned)error;
    if(output("LC1_RETURN errno=%u\n",module_errno)){error=EIO;goto done;}if(error)goto done;
    if(close(fd)){fd=-1;error=err();goto done;}fd=-1;
    if((error=step(4))||(error=logger_bind()))goto done;
    bound=1;
    if((error=step(5))||(error=ring_emit(dir,2)))goto done;
    if((error=step(6))||(error=backend()))goto done;
    error=step(7);
 done:
    if(fd>=0&&close(fd)&&!error)error=err();
    if(owned&&unlinkat(dir,node,0))cleanup=err();
    if(dir>=0&&close(dir)&&!cleanup)cleanup=err();
    return finish(error,cleanup);
}
