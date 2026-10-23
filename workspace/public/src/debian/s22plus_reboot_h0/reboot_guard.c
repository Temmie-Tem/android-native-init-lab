/* Isolated QEMU-virt feasibility component, never a physical entry point.
 * Tests two real ext4 lifetimes per boot and an authenticated phase boundary.
 * It deliberately does NOT replace the product's complete root admission. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <time.h>
#include <unistd.h>
#include "s22plus_fyg8_max77705_result_parser.inc.c"
#include "p458-seal.h"

#define RECORD 256U
#define MAXIMUM (RECORD*3U)
static unsigned phase,base;
static uint8_t boot[32],early[RECORD],runtime[MAXIMUM];
static size_t runtime_size;
static char selected_case[48];
static const char magic[8]="S22RBH0";

static void fail(const char *stage) {
    printf("P458_GUARD_ERROR stage=%s errno=%d\n",stage,errno);
    fflush(stdout); exit(1);
}
static void check(bool good,const char *stage) {
    if (!good) { errno=EPROTO; fail(stage); }
}
static unsigned u32(const uint8_t *p) {
    return p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;
}
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static uint64_t u64(const uint8_t *p) {
    uint64_t n=0; for(unsigned i=0;i<8;i++) n|=(uint64_t)p[i]<<(i*8); return n;
}
static void put32(uint8_t *p,unsigned n) { for(unsigned i=0;i<4;i++) p[i]=(uint8_t)(n>>(i*8)); }
static void put64(uint8_t *p,uint64_t n) { for(unsigned i=0;i<8;i++) p[i]=(uint8_t)(n>>(i*8)); }
static uint64_t now(void) {
    struct timespec t; if(clock_gettime(CLOCK_BOOTTIME,&t)) fail("clock");
    return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
static void timely(void) { check(now()<300000,"absolute-deadline"); }
static void hash(const void *p,size_t n,uint8_t out[32]) {
    struct s22plus_max77705_runtime_sha256 h;
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,p,n);
    s22plus_max77705_runtime_sha256_final(&h,out);
}
static void tag(const uint8_t *p,uint8_t out[32]) {
    static const char domain[]="S22-P458-H0-PHASE-v1";
    uint8_t pad[64],inner[32]; struct s22plus_max77705_runtime_sha256 h;
    memset(pad,0x36,64); for(unsigned i=0;i<32;i++) pad[i]^=p458_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,(const uint8_t *)domain,sizeof(domain)-1);
    s22plus_max77705_runtime_sha256_update(&h,p,224);
    s22plus_max77705_runtime_sha256_final(&h,inner);
    memset(pad,0x5c,64); for(unsigned i=0;i<32;i++) pad[i]^=p458_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,inner,32);
    s22plus_max77705_runtime_sha256_final(&h,out);
}
static bool equal(const uint8_t *a,const uint8_t *b,size_t n) {
    unsigned d=0; for(size_t i=0;i<n;i++) d|=a[i]^b[i]; return !d;
}
static void hex(const uint8_t *p,size_t n) { for(size_t i=0;i<n;i++) printf("%02x",p[i]); }
static void boot_identity(void) {
    char text[38]; int fd=open("/proc/sys/kernel/random/boot_id",O_RDONLY|O_CLOEXEC);
    if(fd<0 || read(fd,text,sizeof(text))!=37 || close(fd)) fail("boot-id");
    check(text[36]=='\n',"boot-id-format"); hash(text,37,boot);
}
static void virt_only(void) {
    char model[128]={0}; int fd=open("/proc/device-tree/model",O_RDONLY|O_CLOEXEC);
    if(fd<0 || read(fd,model,sizeof(model)-1)<=0 || close(fd)) fail("virt-model");
    check(strstr(model,"linux,dummy-virt") && !geteuid(),"virt-only");
    fd=open("/run/p458/case",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0) fail("case");
    ssize_t n=read(fd,selected_case,sizeof(selected_case)-1);
    if(n<1 || close(fd)) fail("case-read");
    check(selected_case[n-1]=='\n',"case-format"); selected_case[n-1]=0;
    boot_identity(); timely();
}
static void point(const char *name) { printf("P458_POINT %s\n",name); fflush(stdout); }
static void cut(const char *name) {
    point(name); if(!strcmp(selected_case,name)) for(;;) pause();
}
static unsigned super(bool require_clean) {
    uint8_t sb[1024]; int fd=open("/dev/vda",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    struct stat st;
    if(fd<0 || fstat(fd,&st) || !S_ISBLK(st.st_mode) ||
       pread(fd,sb,sizeof(sb),1024)!=(ssize_t)sizeof(sb) || close(fd)) fail("super-read");
    check(u16(sb+56)==0xef53 && (u32(sb+92)&4) && equal(sb+104,p458_uuid,16),"filesystem-identity");
    bool clean=u16(sb+58)==1 && !(u32(sb+96)&4) && !u32(sb+232);
    printf("P458_SUPER count=%u state=%u recover=%u orphan=%u\n",
        u16(sb+52),u16(sb+58),!!(u32(sb+96)&4),u32(sb+232)); fflush(stdout);
    if(require_clean) check(clean,"clean-superblock");
    return u16(sb+52);
}
static void protect(int ro) {
    int fd=open("/dev/vda",O_RDONLY|O_NOFOLLOW|O_CLOEXEC),actual=-1;
    if(fd<0 || ioctl(fd,BLKROSET,&ro) || ioctl(fd,BLKROGET,&actual) || close(fd)) fail("block-protect");
    check(actual==ro,"block-protect-readback");
}
static int directory(const char *root) {
    int fd=open(root,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0) fail("root-dir");
    struct stat st,first;
    if(fstat(fd,&first)) fail("root-stat");
    const char *parts[]={"var","lib","lab"};
    for(unsigned i=0;i<3;i++) {
        int next=openat(fd,parts[i],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if(next<0 || fstat(next,&st) || close(fd)) fail("parent-dir");
        check(st.st_dev==first.st_dev && S_ISDIR(st.st_mode) && !st.st_uid && !st.st_gid,"parent-metadata");
        fd=next;
    }
    return fd;
}
static void leaf(char out[96],unsigned p,bool is_early) {
    snprintf(out,96,"p458-%s-%s-b%u",p458_run_text,is_early?"early":"runtime",p);
}
static size_t load(int dir,unsigned p,bool is_early,uint8_t *data) {
    char name[96]; leaf(name,p,is_early);
    int fd=openat(dir,name,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0 && errno==ENOENT) return 0;
    if(fd<0) fail("record-open");
    struct stat st,ds;
    if(fstat(fd,&st) || fstat(dir,&ds)) fail("record-stat");
    check(st.st_dev==ds.st_dev && st.st_mode==(S_IFREG|0600) && !st.st_uid && !st.st_gid && st.st_nlink==1 &&
        st.st_size>=RECORD && st.st_size<=(is_early?RECORD:MAXIMUM) && st.st_size%RECORD==0,"record-metadata");
    uint8_t extra; size_t n=(size_t)st.st_size;
    if(read(fd,data,n)!=(ssize_t)n || read(fd,&extra,1)!=0 || close(fd)) fail("record-read");
    return n;
}
static void validate_record(const uint8_t *r,unsigned p,unsigned role,const uint8_t *previous,const uint8_t *e) {
    uint8_t expected[32],zero[32]={0},prior[32]={0}; tag(r,expected);
    if(previous) hash(previous,RECORD,prior);
    check(equal(r, (const uint8_t *)magic,8) && u32(r+8)==1 && u32(r+12)==role && u32(r+16)==p &&
        u32(r+20)<=65531 && u32(r+24)==(role==1 ? u32(r+20)+2*p-1 : u32(r+20)+2*p) &&
        !u32(r+28) && u64(r+32)<300000 && equal(r+160,p458_run,16) &&
        equal(r+176,zero,32) && equal(r+208,zero,16) && equal(r+224,expected,32) && equal(r+104,prior,32),"record-auth");
    if(role==1) check(equal(r+72,zero,32),"early-chain");
    else { hash(e,RECORD,expected); check(equal(r+72,expected,32) && u32(r+20)==u32(e+20) && equal(r+40,e+40,32),"runtime-early-join"); }
    if(previous) check(u64(r+32)>=u64(previous+32),"record-time-order");
    if(role==1 || role==2) check(equal(r+136,zero,24),"initial-process-fields");
    else check(u64(r+136)==1 && u64(r+144)>1 && u64(r+152)>1 && u64(r+144)!=u64(r+152),"process-fields");
}
static void validate_pair(int dir,unsigned p,bool intent) {
    check(load(dir,p,true,early)==RECORD,"early-absent");
    runtime_size=load(dir,p,false,runtime);
    check(runtime_size>=RECORD && (!intent || runtime_size==MAXIMUM),"runtime-length");
    validate_record(early,p,1,NULL,NULL);
    for(size_t n=0;n<runtime_size/RECORD;n++) validate_record(runtime+n*RECORD,p,
        n==0?2:n==1?3:p==1?4:5,n?runtime+(n-1)*RECORD:NULL,early);
    if(runtime_size>=2*RECORD) check(u64(runtime+RECORD+32)>=u64(runtime+32)+120000,"service-span");
    base=u32(early+20);
}
static void write_record(int dir,unsigned p,bool is_early,bool append,const uint8_t *r) {
    char name[96]; leaf(name,p,is_early);
    int fd=openat(dir,name,O_WRONLY|O_NOFOLLOW|O_CLOEXEC|(append?O_APPEND:O_CREAT|O_EXCL),0600);
    if(fd<0 || write(fd,r,RECORD)!=RECORD || fsync(fd) || fsync(dir) || close(fd)) fail("record-write");
}
static void make_record(uint8_t r[RECORD],unsigned p,unsigned role,const uint8_t *previous,const uint8_t *e,
                        unsigned cron,unsigned ssh) {
    memset(r,0,RECORD); memcpy(r,magic,8); put32(r+8,1); put32(r+12,role); put32(r+16,p);
    put32(r+20,base); put32(r+24,base+2*p-(role==1)); put64(r+32,now()); memcpy(r+40,boot,32);
    if(e) hash(e,RECORD,r+72);
    if(previous) hash(previous,RECORD,r+104);
    if(role>=3) { put64(r+136,1); put64(r+144,cron); put64(r+152,ssh); }
    memcpy(r+160,p458_run,16); tag(r,r+224);
}
static void count(unsigned expected,bool clean) { check(super(clean)==expected,"mount-count"); }
static void boot_root(void) {
    protect(1); unsigned before=super(true);
    if(mount("/dev/vda","/newroot","ext4",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,"noload,nodiscard")) fail("admission-mount");
    int dir=directory("/newroot"); uint8_t scratch[MAXIMUM];
    check(!load(dir,2,true,scratch) && !load(dir,2,false,scratch),"second-phase-consumed");
    size_t e=load(dir,1,true,early),r=load(dir,1,false,runtime);
    if(!e && !r) { phase=1; base=before; check(base<=65531,"mount-count-overflow"); }
    else {
        phase=2; validate_pair(dir,1,true);
        check(!equal(boot,early+40,32),"new-boot-required");
        check(before==base+2,"mount-count");
    }
    if(close(dir) || umount2("/newroot",0)) fail("admission-unmount");
    count(base+2*(phase-1),true);
    printf("P458_PHASE phase=%u base=%u\n",phase,base); fflush(stdout);
    if(phase==2) {
        cut("b2-before-mount");
        if(!strcmp(selected_case,"normal")) {
            /* H0-only quiescent disk snapshot; not a product release gate. */
            point("snapshot-ready"); char permit;
            check(read(STDIN_FILENO,&permit,1)==1 && permit=='G',"fixture-snapshot-resume");
        }
    }
    protect(0); timely();
    if(mount("/dev/vda","/newroot","ext4",MS_NOSUID|MS_NODEV|MS_NOEXEC,"nodiscard,barrier=1")) fail("early-rw-mount");
    count(base+2*phase-1,false);
    if(phase==2) {
        cut("b2-after-mount");
        if(!strcmp(selected_case,"b2-clean-error")) {
            if(umount2("/newroot",0)) fail("clean-error-unmount");
            count(base+3,true); point("b2-clean-error"); exit(2);
        }
    }
    dir=directory("/newroot"); make_record(early,phase,1,NULL,NULL,0,0);
    write_record(dir,phase,true,false,early); if(close(dir)) fail("early-close");
    if(phase==2) cut("b2-after-early");
    if(umount2("/newroot",0)) fail("early-unmount");
    protect(1); count(base+2*phase-1,true);
    if(mount("/dev/vda","/newroot","ext4",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,"noload,nodiscard")) fail("second-admission-mount");
    dir=directory("/newroot");
    check(load(dir,phase,true,scratch)==RECORD && equal(scratch,early,RECORD),"same-boot-early-file");
    check(!load(dir,phase,false,scratch),"runtime-already-present");
    if(close(dir) || umount2("/newroot",0)) fail("second-admission-unmount");
    count(base+2*phase-1,true); protect(0); timely();
    if(mount("/dev/vda","/newroot","ext4",0,"errors=remount-ro,nodiscard,barrier=1")) fail("installed-rw-mount");
    if(!strcmp(selected_case,"unexpected-remount") && phase==1) {
        if(mount(NULL,"/newroot",NULL,MS_REMOUNT|MS_RDONLY,NULL) ||
           mount(NULL,"/newroot",NULL,MS_REMOUNT,"barrier=1,nodiscard")) fail("injected-remount");
    }
    count(base+2*phase,false);
    struct statvfs vf; if(statvfs("/newroot",&vf)) fail("root-vfs");
    check(!(vf.f_flag&ST_RDONLY),"root-writable");
    dir=directory("/newroot"); make_record(runtime,phase,2,NULL,early,0,0);
    write_record(dir,phase,false,false,runtime); if(close(dir)) fail("runtime-close");
    int fd=open("/run/p458/phase",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    char p=(char)('0'+phase); if(fd<0 || write(fd,&p,1)!=1 || close(fd)) fail("ram-phase");
    point("installed-root-ready");
}
static unsigned pidfile(const char *path) {
    char text[32]={0}; int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0) fail("pidfile");
    ssize_t n=read(fd,text,sizeof(text)-1);
    if(n<1 || close(fd)) fail("pidfile-read");
    char *end=NULL; unsigned long p=strtoul(text,&end,10);
    check(p>1 && p<INT32_MAX && (*end=='\n' || !*end) && !kill((pid_t)p,0),"live-pid"); return (unsigned)p;
}
static void executable(unsigned pid,const uint8_t digest[32]) {
    char path[64]; snprintf(path,sizeof(path),"/proc/%u/exe",pid);
    int fd=open(path,O_RDONLY|O_CLOEXEC); if(fd<0) fail("executable");
    struct stat st; if(fstat(fd,&st)) fail("executable-stat");
    check(S_ISREG(st.st_mode) && st.st_size>0 && st.st_size<4*1024*1024,"executable-bound");
    struct s22plus_max77705_runtime_sha256 h; s22plus_max77705_runtime_sha256_init(&h);
    uint8_t bytes[65536],got[32]; ssize_t n;
    while((n=read(fd,bytes,sizeof(bytes)))>0) s22plus_max77705_runtime_sha256_update(&h,bytes,(size_t)n);
    if(n<0 || close(fd)) fail("executable-read");
    s22plus_max77705_runtime_sha256_final(&h,got); check(equal(got,digest,32),"executable-digest");
}
static int current(unsigned *cron,unsigned *ssh) {
    int fd=open("/run/p458/phase",O_RDONLY|O_NOFOLLOW|O_CLOEXEC); char p[2];
    if(fd<0 || read(fd,p,2)!=1 || close(fd)) fail("phase-read");
    check(p[0]=='1' || p[0]=='2',"phase-value"); phase=(unsigned)(p[0]-'0');
    int dir=directory("/"); validate_pair(dir,phase,false);
    check(equal(boot,early+40,32),"same-boot-records"); count(base+2*phase,false);
    executable(1,p458_init_sha); *cron=pidfile("/run/crond.pid"); *ssh=pidfile("/run/sshd.pid");
    executable(*cron,p458_cron_sha); executable(*ssh,p458_sshd_sha);
    check(*cron!=*ssh,"distinct-services"); timely(); return dir;
}
static void status(void) {
    unsigned cron,ssh; int dir=current(&cron,&ssh);
    printf("P458_HEALTH phase=%u base=%u boot=",phase,base); hex(boot,32);
    printf(" uptime_ms=%llu init_pid=1 cron_pid=%u sshd_pid=%u\n",(unsigned long long)now(),cron,ssh);
    for(unsigned p=1;p<=phase;p++) {
        uint8_t bytes[MAXIMUM];
        for(unsigned kind=0;kind<2;kind++) {
            size_t size=load(dir,p,!kind,bytes);
            printf("P458_FILE phase=%u kind=%s data=",p,kind?"runtime":"early"); hex(bytes,size); putchar('\n');
        }
    }
    if(close(dir)) fail("status-close");
}
static void append(unsigned role) {
    unsigned cron,ssh; int dir=current(&cron,&ssh);
    check(runtime_size==(role==3?RECORD:2*RECORD),"command-consumed");
    check(role==3 || (role==4 && phase==1) || (role==5 && phase==2),"command-phase");
    if(role==3) check(now()>=u64(runtime+32)+120000,"service-span");
    uint8_t record[RECORD]; make_record(record,phase,role,runtime+runtime_size-RECORD,early,cron,ssh);
    write_record(dir,phase,false,true,record); if(close(dir)) fail("append-close");
    printf("P458_APPEND role=%u phase=%u\n",role,phase); fflush(stdout);
}
int main(int argc,char **argv) {
    virt_only(); check(argc==2,"arguments");
    if(!strcmp(argv[1],"boot")) boot_root();
    else if(!strcmp(argv[1],"health")) status();
    else if(!strcmp(argv[1],"complete")) append(3);
    else if(!strcmp(argv[1],"intent")) append(4);
    else if(!strcmp(argv[1],"shutdown")) append(5);
    else { errno=EINVAL; fail("command"); }
    return 0;
}
