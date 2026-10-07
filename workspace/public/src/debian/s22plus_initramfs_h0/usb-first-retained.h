/* Fixed bounded printk records through the stock sec_log_buf owner. No
 * reserved-memory mapping, disk writer, panic, console reader or replay. */
#ifndef USB_RETAINED_PROTOCOL_EXTERNAL
#include "usb-first-key.h"
#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-USB-FIRST-v1"
#include "early-protocol.h"
#endif
static int usb_retained(unsigned sequence,const char *event,size_t size) {
    if(!sequence || sequence>256 || !size || size>384 || event[size-1]!='\n')return EINVAL;
    char boot[38],line[768],hex[65],run[33];uint8_t boot_hash[32],mac[32];
    int error=fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot));
    if(error || strlen(boot)!=37 || boot[36]!='\n')return EPROTO;
    boot[36]=0;early_hash(boot,36,boot_hash);
    early_tag(mac,boot_hash,240,sequence,event,size-1);
    for(unsigned i=0;i<16;++i)snprintf(run+2*i,3,"%02x",early_run[i]);
    for(unsigned i=0;i<32;++i)snprintf(hex+2*i,3,"%02x",mac[i]);
    int n=snprintf(line,sizeof(line),"<14>S22USB1 run=%s boot=%s seq=%u mac=%s %.*s\n",
        run,boot,sequence,hex,(int)size-1,event);
    if(n<0 || (size_t)n>=sizeof(line))return EOVERFLOW;
    int reader=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(reader<0)return fs1_error();
    struct stat st;
    if(fstat(reader,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=makedev(1,11) ||
        st.st_uid || st.st_gid || (st.st_mode&07777)!=0600 || lseek(reader,0,SEEK_END)<0) {
        close(reader);return EPROTO;
    }
    int fd=open("/dev/kmsg",O_WRONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0){close(reader);return fs1_error();}
    if(fstat(fd,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=makedev(1,11) ||
        st.st_uid || st.st_gid || (st.st_mode&07777)!=0600)error=EPROTO;
    /* This kernel may return full length when dropping a write. Require exact
     * bounded ring readback; it still is not post-reboot retention proof. */
    if(!error && write(fd,line,(size_t)n)!=n)error=EIO;
    if(close(fd)&&!error)error=fs1_error();
    size_t total=0;bool found=false;struct timespec start,current;
    if(clock_gettime(CLOCK_BOOTTIME,&start))error=EIO;
    while(!error && !found && total<65536) {
        if(clock_gettime(CLOCK_BOOTTIME,&current)){error=EIO;break;}
        int64_t elapsed=(int64_t)(current.tv_sec-start.tv_sec)*1000000000LL+current.tv_nsec-start.tv_nsec;
        if(elapsed<0 || elapsed>=500000000LL){error=ETIMEDOUT;break;}
        char raw[2048];size_t available=65536-total;
        if(available>sizeof(raw))available=sizeof(raw);
        ssize_t amount=read(reader,raw,available);
        if(amount>0) {
            total+=(size_t)amount;
            char *body=memchr(raw,';',(size_t)amount);
            if(body && (size_t)(raw+amount-body-1)==(size_t)n-4 && !memcmp(body+1,line+4,(size_t)n-4))found=true;
        }else if(amount<0 && errno!=EAGAIN && errno!=EINTR){error=fs1_error();break;}
        else if(amount==0){error=EIO;break;}
        if(clock_gettime(CLOCK_BOOTTIME,&current)){error=EIO;break;}
        elapsed=(int64_t)(current.tv_sec-start.tv_sec)*1000000000LL+current.tv_nsec-start.tv_nsec;
        if(elapsed<0 || elapsed>=500000000LL){error=ETIMEDOUT;break;}
        if(!found) {struct timespec delay={0,1000000};if(nanosleep(&delay,NULL))error=fs1_error();}
    }
    if(!error && !found)error=ENOMSG;
    if(close(reader)&&!error)error=fs1_error();
    return error;
}
