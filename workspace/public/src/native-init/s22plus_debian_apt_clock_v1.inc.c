/* Authenticated SSH publishes one RAM request. The sequential observer alone
 * sets CLOCK_REALTIME, before cron configuration/arming. No RTC operation. */
#include "s22plus_debian_apt_seal_v1.h"
#define AP_CLOCK_BYTES 160U
static bool ap_fault(unsigned wanted) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    char text[4096],expected[40];
    if(fs1_read_text("/proc/cmdline",text,sizeof(text)))return false;
    snprintf(expected,sizeof(expected),"s22apt_fault=%u",wanted);
    size_t n=strlen(expected);char *at=strstr(text,expected);
    return at && (at==text || at[-1]==' ') && (at[n]==' ' || at[n]=='\n' || !at[n]);
#else
    (void)wanted;return false;
#endif
}
static int ap_ram_stat(int fd,struct stat *st,mode_t mode,uint64_t size) {
    struct statfs fs;
    return fstat(fd,st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L || st->st_mode!=mode ||
        st->st_uid || st->st_gid || st->st_nlink!=1 || st->st_size<0 || (uint64_t)st->st_size!=size ? EPROTO : 0;
}
static int ap_publish(const char *name,const void *data,size_t size) {
    char pending[192],path[160];struct stat st;
    int length=snprintf(path,sizeof(path),"/run/s22-debian/%s",name);
    if(length<0 || (size_t)length>=sizeof(path))return EOVERFLOW;
    snprintf(pending,sizeof(pending),"%s.pending",path);
    mode_t mask=umask(0);int fd=open(pending,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    umask(mask);if(fd<0)return fs1_error();
    int error=ap_ram_stat(fd,&st,S_IFREG|0400,0);
    if(!error && write(fd,data,size)!=(ssize_t)size)error=EIO;
    if(!error && fsync(fd))error=fs1_error();
    if(close(fd) && !error)error=fs1_error();
    if(!error && syscall(SYS_renameat2,AT_FDCWD,pending,AT_FDCWD,path,1U))error=fs1_error();
    return error;
}
static int ap_clock_read(const char *name,uint8_t data[AP_CLOCK_BYTES],bool complete) {
    char path[160];snprintf(path,sizeof(path),"/run/s22-debian/%s",name);
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;uint8_t tag[32],extra;int error=ap_ram_stat(fd,&st,S_IFREG|0400,AP_CLOCK_BYTES);
    if(!error && (read(fd,data,AP_CLOCK_BYTES)!=AP_CLOCK_BYTES || read(fd,&extra,1)!=0))error=EIO;
    if(close(fd) && !error)error=fs1_error();
    if(error)return error;
    de_tag(tag,data,128);
    if(memcmp(data,"S22APT1\0",8) || memcmp(data+8,sw.run,16) || memcmp(data+24,sw.boot,32) ||
       fs1_u32(data+56)!=rb_phase || fs1_u32(data+60) || de_u64(data+64)<1577836800ULL ||
       de_u64(data+64)>=4102444800ULL || de_u64(data+72)>=1000000000ULL ||
       de_u64(data+80)>=sw.deadline_ms || de_u64(data+120) || !de_tag_equal(tag,data+128))return EPROTO;
    uint64_t before=de_u64(data+88),after=de_u64(data+96),sec=de_u64(data+104),ns=de_u64(data+112);
    if(!complete)return before || after || sec || ns ? EPROTO : 0;
    uint64_t wanted=de_u64(data+64)*1000000000ULL+de_u64(data+72);
    uint64_t actual=sec*1000000000ULL+ns;
    return before<de_u64(data+80) || after<before || after>=sw.deadline_ms ||
        after-de_u64(data+80)>20000 || ns>=1000000000ULL || sec>=4102444800ULL ||
        actual<wanted || actual-wanted>1000000000ULL ? EPROTO : 0;
}
static int ap_number(const char *text,uint64_t *out) {
    size_t length=strlen(text);if(!length || length>10 || (length>1 && text[0]=='0'))return EINVAL;
    uint64_t value=0;
    for(size_t i=0;i<length;++i){if(text[i]<'0' || text[i]>'9')return EINVAL;value=value*10+(unsigned)(text[i]-'0');}
    *out=value;return 0;
}
static int ap_marker(const char *name) {
    char path[160];snprintf(path,sizeof(path),"/run/s22-debian/%s",name);
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return fs1_error();
    struct stat st;int error=ap_ram_stat(fd,&st,S_IFREG|0400,0);
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int ap_clock_request(int argc,char **argv,struct dh_state *state) {
    if(argc!=6 || strcmp(argv[1],"apt-time") || strlen(argv[2])!=1 ||
       argv[2][0]!=(char)('0'+rb_phase) || strlen(argv[3])!=64)return EINVAL;
    char boot[65];for(unsigned i=0;i<32;++i)snprintf(boot+2*i,3,"%02x",sw.boot[i]);
    if(strcmp(boot,argv[3]))return EPROTO;
    uint64_t sec,ns;int error=ap_number(argv[4],&sec);
    if(!error)error=ap_number(argv[5],&ns);
    if(error || sec<1577836800ULL || sec>=4102444800ULL || ns>=1000000000ULL)return EINVAL;
    if((error=dh_actual_init(state)) || (error=de_time()))return error;
    /* Exclusive intent precedes publication. A lost response never reissues it. */
    if((error=ap_marker("apt-clock-ready")) || (error=ap_publish("apt-time-intent","",0)))return error;
    uint8_t data[AP_CLOCK_BYTES]={0};memcpy(data,"S22APT1\0",8);memcpy(data+8,sw.run,16);memcpy(data+24,sw.boot,32);
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(ap_fault(2))data[24]^=1;
#endif
    sw_put32(data+56,rb_phase);de_put64(data+64,sec);de_put64(data+72,ns);de_put64(data+80,sw_now());
    de_tag(data+128,data,128);
    if((error=ap_publish("apt-time-request",data,sizeof(data))) || (error=de_time()))return error;
    return printf("S22_APT_CLOCK_REQUESTED\n")<0 || fflush(stdout) ? EIO : 0;
}
static int ap_clock_status(void) {
    uint8_t data[AP_CLOCK_BYTES];int error=ap_clock_read("apt-time-result",data,true);
    if(error==ENOENT) {
        error=ap_marker("apt-clock-ready");
        if(error && error!=ENOENT)return 76;
        const char *value="WAIT";
        if(!error) {
            error=ap_marker("apt-time-intent");
            if(error && error!=ENOENT)return 76;
            value=error==ENOENT ? "READY" : "PENDING";
        }
        return printf("S22_APT_CLOCK_%s\n",value)<0 || fflush(stdout) ? 74 : 75;
    }
    if(error || de_time())return 76;
    char boot[65];for(unsigned i=0;i<32;++i)snprintf(boot+2*i,3,"%02x",sw.boot[i]);
    return printf("S22_APT_CLOCK_V1 %u %s %llu %llu %llu %llu %llu %llu %llu\n",rb_phase,boot,
        (unsigned long long)de_u64(data+64),(unsigned long long)de_u64(data+72),
        (unsigned long long)de_u64(data+80),(unsigned long long)de_u64(data+88),
        (unsigned long long)de_u64(data+96),(unsigned long long)de_u64(data+104),
        (unsigned long long)de_u64(data+112))<0 || fflush(stdout) ? 77 : 0;
}
static int ap_clock_wait(struct dh_state *state) {
    dh_claim("apt-clock-ready","runlevel-complete");
    uint8_t data[AP_CLOCK_BYTES];int error;
    uint64_t deadline=sw.deadline_ms;
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(ap_fault(1)) {
        deadline=sw_now()+5000;
        dprintf(2,"APT_CLOCK_WAIT_MISSING begin_ms=%llu deadline_ms=%llu\n",
            (unsigned long long)(deadline-5000),(unsigned long long)deadline);
    }
#endif
    for(;;) {
        if((error=de_time()))return error;
        if(sw_now()>=deadline) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
            if(ap_fault(1))dprintf(2,"APT_CLOCK_WAIT_MISSING expired_ms=%llu\n",(unsigned long long)sw_now());
#endif
            return ETIMEDOUT;
        }
        aw_tick();ap_tick();
        error=ap_clock_read("apt-time-request",data,false);
        if(!error)break;
        if(error!=ENOENT) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
            if(ap_fault(2))dprintf(2,"APT_CLOCK_WAIT_REQUEST_REJECTED errno=%d\n",error);
#endif
            return error;
        }
        struct timespec delay={0,100000000};if(nanosleep(&delay,NULL) && errno!=EINTR)return fs1_error();
    }
    if((error=dh_actual_init(state)))return error;
    uint64_t before=sw_now();
    if(before<de_u64(data+80) || before-de_u64(data+80)>20000)return ETIMEDOUT;
    dh_claim("apt-time-claimed","apt-time-intent");
    struct timespec set={(time_t)de_u64(data+64),(long)de_u64(data+72)},observed;
    if((error=de_time()))return error;
    if(clock_settime(CLOCK_REALTIME,&set))return fs1_error();
    if(clock_gettime(CLOCK_REALTIME,&observed))return fs1_error();
    de_put64(data+88,before);de_put64(data+96,sw_now());de_put64(data+104,(uint64_t)observed.tv_sec);
    de_put64(data+112,(uint64_t)observed.tv_nsec);de_tag(data+128,data,128);
    if((error=ap_publish("apt-time-result",data,sizeof(data))) ||
       (error=ap_clock_read("apt-time-result",data,true)) || (error=de_time()))return error;
    dprintf(2,"APT_CLOCK phase=%u complete=1\n",rb_phase);
    return de_event(15,rb_phase,1,de_u64(data+64),de_u64(data+72),de_u64(data+96)-de_u64(data+80));
}
