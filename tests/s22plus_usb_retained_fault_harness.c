/* Execute the real bounded printk writer/readback with syscall fault fixtures. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>
static unsigned scenario,writes,reads,clocks,total_read;
static char emitted[768];static size_t emitted_size;
static const uint8_t early_run[16]={0};
static int fs1_error(void){return errno?errno:EIO;}
static int fs1_read_text(const char *p,char *out,size_t n) {
    assert(!strcmp(p,"/proc/sys/kernel/random/boot_id") && n>=38);
    strcpy(out,"12345678-1234-1234-1234-123456789abc\n");return 0;
}
static void early_hash(const void *p,size_t n,uint8_t out[32]){(void)p;(void)n;memset(out,0,32);}
static void early_tag(uint8_t out[32],const uint8_t *p,unsigned k,unsigned s,const void *b,size_t n) {
    (void)p;(void)k;(void)s;(void)b;(void)n;memset(out,0,32);
}
static int fake_open(const char *p,int flags) {
    assert(!strcmp(p,"/dev/kmsg"));return (flags&O_ACCMODE)==O_RDONLY?11:12;
}
static int fake_fstat(int fd,struct stat *st) {
    assert(fd==11 || fd==12);memset(st,0,sizeof(*st));st->st_mode=S_IFCHR|0600;
    st->st_rdev=makedev(1,scenario==6?3:11);return 0;
}
static off_t fake_lseek(int fd,off_t off,int mode){assert(fd==11 && off==0 && mode==SEEK_END);return 0;}
static int fake_close(int fd){assert(fd==11 || fd==12);return 0;}
static ssize_t fake_write(int fd,const void *p,size_t n) {
    assert(fd==12 && ++writes==1 && n<sizeof(emitted));memcpy(emitted,p,n);emitted_size=n;
    return scenario==2?(ssize_t)n-1:(ssize_t)n;
}
static ssize_t fake_read(int fd,void *p,size_t n) {
    assert(fd==11 && n<=65536-total_read);++reads;
    if(scenario==1){errno=EAGAIN;return -1;}
    if(scenario==4){size_t amount=reads==1?1000:n;memset(p,'x',amount);total_read+=amount;return amount;}
    const char prefix[]="14,5,100,-;";size_t size=sizeof(prefix)-1+emitted_size-4;
    assert(n>=size);memcpy(p,prefix,sizeof(prefix)-1);memcpy((char *)p+sizeof(prefix)-1,emitted+4,emitted_size-4);
    total_read+=size;return size;
}
static int fake_clock(clockid_t id,struct timespec *t) {
    assert(id==CLOCK_BOOTTIME);++clocks;t->tv_sec=10;t->tv_nsec=0;
    if(scenario==1)t->tv_nsec=(long)(clocks-1)*100000000L;
    if(scenario==3 && reads)t->tv_nsec=500000000L;
    if(scenario==5 && clocks>1)t->tv_sec=9;
    return 0;
}
static int fake_sleep(const struct timespec *a,struct timespec *b){(void)a;(void)b;return 0;}
#define USB_RETAINED_PROTOCOL_EXTERNAL
#define open fake_open
#define fstat fake_fstat
#define lseek fake_lseek
#define close fake_close
#define write fake_write
#define read fake_read
#define clock_gettime fake_clock
#define nanosleep fake_sleep
#include "../workspace/public/src/debian/s22plus_initramfs_h0/usb-first-retained.h"
int main(void) {
    static const int wanted[]={0,ETIMEDOUT,EIO,ETIMEDOUT,ENOMSG,ETIMEDOUT,EPROTO};
    for(scenario=0;scenario<sizeof(wanted)/sizeof(wanted[0]);++scenario) {
        writes=reads=clocks=total_read=0;emitted_size=0;
        const char line[]="USBSTAGE TEST\n";int result=usb_retained(200,line,sizeof(line)-1);
        assert(result==wanted[scenario]);assert(writes==(scenario==6?0U:1U));assert(total_read<=65536);
    }
    puts("PASS: 7 real writer/readback failure boundaries");return 0;
}
