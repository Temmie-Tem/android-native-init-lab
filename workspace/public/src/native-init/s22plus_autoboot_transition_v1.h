/* Optional bounded observation. No workload decision depends on this channel.
 * BEGIN only says the caller is about to call; absence never proves a stall. */
#ifndef S22_AUTOBOOT_TRANSITION_V1_H
#define S22_AUTOBOOT_TRANSITION_V1_H
#define AT_STAGE(number,name,actors,convention) AT_##name=number,
enum at_stage {
#include "s22plus_autoboot_transition_stages_v1.def"
};
#undef AT_STAGE
#ifdef S22_AUTOBOOT_TRACE
#include "checked-kmsg.h"
static unsigned at_actor=S22_AUTOBOOT_TRACE,at_sequence,at_last,at_lost,at_error,at_ready,at_moved,at_disabled;
static uint64_t at_spent;
static uint8_t at_source[32],at_boot_hash[32];
static char at_boot[38];
static uint64_t at_now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_BOOTTIME,&t) || t.tv_sec<0 || t.tv_nsec<0 || t.tv_nsec>=1000000000L)return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
static void at_u32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
static void at_u64(uint8_t *p,uint64_t n){for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(n>>(8*i));}
static void at_hash(const void *data,size_t n,uint8_t out[32]) {
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,data,n);s22plus_max77705_runtime_sha256_final(&h,out);
}
static int at_measure(uint64_t deadline) {
    if(at_now()>=deadline)return ETIMEDOUT;
    if(fs1_read_text("/proc/sys/kernel/random/boot_id",at_boot,sizeof(at_boot)) ||
       strlen(at_boot)!=37 || at_boot[36]!='\n')return EPROTO;
    for(unsigned i=0;i<36;++i) {
        if(i==8 || i==13 || i==18 || i==23){if(at_boot[i]!='-')return EPROTO;}
        else if(!((at_boot[i]>='0' && at_boot[i]<='9') || (at_boot[i]>='a' && at_boot[i]<='f')))return EPROTO;
    }
    at_boot[36]=0;at_hash(at_boot,36,at_boot_hash);
    /* /proc/self/exe is deliberately followed: measure the running executable,
     * not a path assumed to name it. This fd is closed before every record. */
    if(at_now()>=deadline)return ETIMEDOUT;
    int fd=open("/proc/self/exe",O_RDONLY|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;int error=fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid ||
        st.st_size<=0 || st.st_size>8*1024*1024 ? EPROTO : 0;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    uint8_t bytes[16384];off_t used=0;
    while(!error && used<st.st_size) {
        if(at_now()>=deadline){error=ETIMEDOUT;break;}
        size_t n=(size_t)(st.st_size-used);if(n>sizeof(bytes))n=sizeof(bytes);
        ssize_t got=read(fd,bytes,n);if(got<=0 || got>(ssize_t)n){error=EIO;break;}
        s22plus_max77705_runtime_sha256_update(&h,bytes,(size_t)got);used+=got;
    }
    if(close(fd) && !error)error=fs1_error();
    if(!error && at_now()>=deadline)error=ETIMEDOUT;
    if(!error)s22plus_max77705_runtime_sha256_final(&h,at_source);
    return error;
}
static void at_tag(uint8_t tag[32],const uint8_t raw[128]) {
    static const char domain[]="S22PLUS-FYG8-AUTOBOOT-TRANSITION-v1";
    uint8_t pad[64],inner[32];struct s22plus_max77705_runtime_sha256 h;
    memset(pad,0x36,sizeof(pad));for(unsigned i=0;i<32;++i)pad[i]^=AT_KEY[i];
    s22plus_max77705_runtime_sha256_init(&h);s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,(const uint8_t *)domain,sizeof(domain)-1);
    s22plus_max77705_runtime_sha256_update(&h,AT_RUN,16);
    s22plus_max77705_runtime_sha256_update(&h,at_boot_hash,32);
    s22plus_max77705_runtime_sha256_update(&h,raw,128);s22plus_max77705_runtime_sha256_final(&h,inner);
    memset(pad,0x5c,sizeof(pad));for(unsigned i=0;i<32;++i)pad[i]^=AT_KEY[i];
    s22plus_max77705_runtime_sha256_init(&h);s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,inner,32);s22plus_max77705_runtime_sha256_final(&h,tag);
}
static void at_emit(unsigned stage,unsigned kind,unsigned convention,int64_t result,unsigned error,
        unsigned child,unsigned status,unsigned done,unsigned worker_result) {
    int saved=errno;uint64_t start=at_now();
    if(at_disabled || start==UINT64_MAX || start>=300000 || at_sequence>=96 || at_spent>=2000)goto end;
    if(kind==1 || kind==4)at_last=stage;
    if(!at_ready) {
        uint64_t deadline=start+2000-at_spent;if(deadline>300000)deadline=300000;
        int measured=at_measure(deadline);
        if(measured){at_error=(unsigned)measured;++at_lost;at_disabled=1;goto end;}
        at_ready=1;
    }
    uint8_t raw[128]={0},mac[32];memcpy(raw,"S22AT01\0",8);
    at_u32(raw+8,at_actor);at_u32(raw+12,++at_sequence);at_u32(raw+16,kind);at_u32(raw+20,stage);
    at_u32(raw+24,convention);at_u32(raw+28,error);at_u64(raw+32,(uint64_t)result);at_u64(raw+40,start);
    at_u32(raw+48,(unsigned)getpid());at_u32(raw+52,(unsigned)getppid());
    at_u32(raw+56,at_lost);at_u32(raw+60,at_error);at_u64(raw+64,at_spent);
    at_u32(raw+72,child);at_u32(raw+76,status);at_u32(raw+80,done);at_u32(raw+84,worker_result);
    memcpy(raw+88,at_source,32);at_tag(mac,raw);
    char run[33],tag[65],data[257],line[512];
    for(unsigned i=0;i<16;++i)snprintf(run+2*i,3,"%02x",AT_RUN[i]);
    for(unsigned i=0;i<32;++i)snprintf(tag+2*i,3,"%02x",mac[i]);
    for(unsigned i=0;i<128;++i)snprintf(data+2*i,3,"%02x",raw[i]);
    int n=snprintf(line,sizeof(line),"<14>S22AT1 run=%s boot=%s mac=%s data=%s\n",run,at_boot,tag,data);
    uint64_t now=at_now();unsigned budget=now<start || now-start>=2000-at_spent ? 0 : (unsigned)(2000-at_spent-(now-start));
    if(now>=300000)budget=0;
    else if(budget>300000-now)budget=(unsigned)(300000-now);
    if(budget>500)budget=500;
    int observed=n<=0 || n>=(int)sizeof(line) ? EOVERFLOW : !budget ? ETIMEDOUT :
        checked_kmsg_path(at_moved?"/newroot/dev/kmsg":"/dev/kmsg",line,n,budget);
    if(observed){++at_lost;at_error=(unsigned)observed;}
    now=at_now();at_spent=now<start || now==UINT64_MAX ? 2000 : at_spent+now-start;
end:
    errno=saved;
}
static void at_stop(int error){at_emit(at_last,3,3,0,(unsigned)error,0,0,0,0);}
static void at_select(unsigned actor){at_actor=actor;}
static void at_moved_dev(void){at_moved=1;}
static void at_disable(void){at_disabled=1;}
#define AT_POINT(stage,result,error) at_emit(stage,4,3,result,error,0,0,0,0)
#define AT_BEGIN(stage,convention) at_emit(stage,1,convention,0,0,0,0,0,0)
#define AT_RETURN(stage,convention,result,error) at_emit(stage,2,convention,result,error,0,0,0,0)
/* Keep the call exactly once, and its immediate errno intact after logging. */
#define AT_SYS(stage,call) ({ AT_BEGIN(stage,1); __auto_type at_rc=(call); int at_errno=errno; \
    AT_RETURN(stage,1,(int64_t)at_rc,(unsigned)at_errno); errno=at_errno; at_rc; })
#define AT_CHECK(stage,call) ({ AT_BEGIN(stage,2); int at_rc=(call),at_errno=errno; \
    AT_RETURN(stage,2,at_rc,(unsigned)at_rc); errno=at_errno; at_rc; })
/* Effect guards run after BEGIN as well. A guard stop emits no fake RETURN. */
#define AT_SYS_GUARD(stage,guard,call) ({ AT_BEGIN(stage,1); guard; \
    __auto_type at_rc=(call); int at_errno=errno; \
    AT_RETURN(stage,1,(int64_t)at_rc,(unsigned)at_errno); errno=at_errno; at_rc; })
#else
#define AT_POINT(stage,result,error) ((void)0)
#define AT_BEGIN(stage,convention) ((void)0)
#define AT_RETURN(stage,convention,result,error) ((void)0)
#define AT_SYS(stage,call) (call)
#define AT_CHECK(stage,call) (call)
#define AT_SYS_GUARD(stage,guard,call) (call)
#define at_stop(error) ((void)0)
#define at_select(actor) ((void)0)
#define at_moved_dev() ((void)0)
#define at_disable() ((void)0)
#endif
#endif
