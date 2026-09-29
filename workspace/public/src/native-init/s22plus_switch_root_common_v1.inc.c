/* Shared by the preparation PID1 and the post-switch executable. No fork,
 * mount, caller-selected command or storage write lives in this transport. */
#include <linux/reboot.h>
#include <poll.h>
#include <stdarg.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <termios.h>
#include <time.h>
#include "s22plus_switch_root_v1.h"
#include "s22plus_switch_root_seal_v1.h"

static struct sw_state sw;
static int sw_broken;
static unsigned sw_last_stage;

static uint64_t sw_now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_BOOTTIME,&t) || t.tv_sec<0 || t.tv_nsec<0 || t.tv_nsec>=1000000000L)
        return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U;
}
static void sw_hash(const void *data,size_t size,uint8_t out[32]) {
    struct s22plus_max77705_runtime_sha256 hash;
    s22plus_max77705_runtime_sha256_init(&hash);
    s22plus_max77705_runtime_sha256_update(&hash,data,size);
    s22plus_max77705_runtime_sha256_final(&hash,out);
}
static int sw_boot(uint8_t out[32]) {
    char value[38]; int error=fs1_read_text("/proc/sys/kernel/random/boot_id",value,sizeof(value));
    if (error) return error;
    if (strlen(value)!=37 || value[36]!='\n') return EPROTO;
    for (unsigned i=0;i<36;++i) {
        if (i==8 || i==13 || i==18 || i==23) { if (value[i]!='-') return EPROTO; }
        else if (!((value[i]>='0' && value[i]<='9') || (value[i]>='a' && value[i]<='f'))) return EPROTO;
    }
    sw_hash(value,36,out); return 0;
}
static int sw_bytes(int fd,void *buffer,size_t count,int output) {
    uint8_t *p=buffer;
    while (count) {
        if (sw_now()>=sw.deadline_ms) return ETIMEDOUT;
        ssize_t n=output ? write(fd,p,count) : read(fd,p,count);
        if (n>0) { p+=n;count-=(size_t)n;continue; }
        if (n<0 && (errno==EINTR || errno==EAGAIN)) {
            struct pollfd f={fd,output ? POLLOUT : POLLIN,0};
            if (poll(&f,1,20)<0 && errno!=EINTR) return fs1_error();
            continue;
        }
        return n ? fs1_error() : EIO;
    }
    return 0;
}
static uint32_t sw_crc(const uint8_t *p,size_t length,uint32_t crc) {
    for (size_t i=0;i<length;++i) {
        crc^=p[i]; for (unsigned j=0;j<8;++j) crc=(crc>>1)^(0xedb88320U&-(crc&1U));
    }
    return crc;
}
static void sw_put32(uint8_t *out,uint32_t v) { for(unsigned i=0;i<4;++i)out[i]=(uint8_t)(v>>(8*i)); }
static void sw_tag(uint8_t out[32],unsigned kind,uint32_t sequence,const uint8_t *body,size_t size) {
    static const char domain[]="S22PLUS-FYG8-SWITCH-ROOT-v1";
    uint8_t pad[64],inner[32],tail[5]; struct s22plus_max77705_runtime_sha256 hash;
    memset(pad,0x36,sizeof(pad)); for(unsigned i=0;i<32;++i)pad[i]^=sw_key[i];
    s22plus_max77705_runtime_sha256_init(&hash);
    s22plus_max77705_runtime_sha256_update(&hash,pad,sizeof(pad));
    s22plus_max77705_runtime_sha256_update(&hash,(const uint8_t *)domain,sizeof(domain)-1);
    s22plus_max77705_runtime_sha256_update(&hash,sw.run,sizeof(sw.run));
    s22plus_max77705_runtime_sha256_update(&hash,sw.nonce,sizeof(sw.nonce));
    sw_put32(tail,sequence);tail[4]=(uint8_t)kind;
    s22plus_max77705_runtime_sha256_update(&hash,tail,sizeof(tail));
    s22plus_max77705_runtime_sha256_update(&hash,body,size);
    s22plus_max77705_runtime_sha256_final(&hash,inner);
    memset(pad,0x5c,sizeof(pad));for(unsigned i=0;i<32;++i)pad[i]^=sw_key[i];
    s22plus_max77705_runtime_sha256_init(&hash);
    s22plus_max77705_runtime_sha256_update(&hash,pad,sizeof(pad));
    s22plus_max77705_runtime_sha256_update(&hash,inner,sizeof(inner));
    s22plus_max77705_runtime_sha256_final(&hash,out);
}
static int sw_send(unsigned kind,uint32_t sequence,const void *data,size_t size) {
    if (sw_broken || size>991) return EPROTO;
    uint8_t frame[1039]={ 'S','3','2','8',1,(uint8_t)kind };
    frame[6]=(uint8_t)(size+32);frame[7]=(uint8_t)((size+32)>>8);sw_put32(frame+8,sequence);
    memcpy(frame+16,data,size);sw_tag(frame+16+size,kind,sequence,data,size);
    sw_put32(frame+12,~sw_crc(frame+16,size+32,sw_crc(frame,12,~0U)));
    int error=sw_bytes(3,frame,size+48,1);if(error)sw_broken=1;return error;
}
static int sw_record(unsigned stage,unsigned error,const void *data,size_t size) {
    if (sw.next_record>=SW_MAX_RECORDS || size>983 || error>4095) return EOVERFLOW;
    uint8_t body[991];sw_put32(body,stage);sw_put32(body+4,error);memcpy(body+8,data,size);
    int rc=sw_send(SW_RECORD,1024+sw.next_record,body,size+8);
    ++sw.next_record;if(stage!=SW_LOG)sw_last_stage=stage;return rc;
}
static __attribute__((noreturn)) void sw_park(void) {
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && !defined(S22_DEBIAN_HOOK)
    /* H0 harness termination only. The Samsung build always parks. */
    (void)syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_POWER_OFF,0);
#endif
    for (;;) {struct timespec delay={1,0};(void)nanosleep(&delay,NULL);}
}
static __attribute__((noreturn)) void sw_stop(int error) {
    uint32_t failed=sw_last_stage;
    if (error<=0 || error>4095) error=EPROTO;
    (void)sw_record(SW_STOP,(unsigned)error,&failed,sizeof(failed));sw_park();
}
static void sw_require(int error) { if(error)sw_stop(error); }
static void sw_log(const char *format,va_list args) {
    char bytes[16384];int n=vsnprintf(bytes,sizeof(bytes),format,args);
    if(n<0 || n>=(int)sizeof(bytes))sw_stop(EOVERFLOW);
    for(size_t used=0;used<(size_t)n;) {
        size_t amount=(size_t)n-used;if(amount>768)amount=768;
        sw_require(sw_record(SW_LOG,0,bytes+used,amount));used+=amount;
    }
}
static int sw_fd_type(void) {
    struct stat st;struct termios tty;
    if(fstat(3,&st) || !S_ISCHR(st.st_mode) || tcgetattr(3,&tty) ||
       fcntl(3,F_GETFD)!=0 || !(fcntl(3,F_GETFL)&O_NONBLOCK))return EPROTO;
    return sw.tty_device && sw.tty_device!=(uint64_t)st.st_rdev ? EPROTO : 0;
}
static int sw_load_state(void) {
    struct stat st;uint8_t boot[32];uint8_t extra;
    if(getpid()!=1 || getuid() || geteuid() || getgid() || getegid() ||
       fstat(4,&st) || !S_ISREG(st.st_mode) || st.st_size!=(off_t)sizeof(sw) ||
       fcntl(4,F_GET_SEALS)!=SW_MEMFD_SEALS || pread(4,&sw,sizeof(sw),0)!=(ssize_t)sizeof(sw) ||
       pread(4,&extra,1,sizeof(sw))!=0 || sw.magic!=SW_STATE_MAGIC || sw.version!=SW_STATE_VERSION ||
       sw.sequence!=SW_SEQUENCE || memcmp(sw.run,sw_run,16) || sw.reserved ||
       !sw.deadline_ms || sw_now()>=sw.deadline_ms || sw.deadline_ms-sw_now()>SW_TIMEOUT_MS ||
       sw.next_record>=SW_MAX_RECORDS || sw_boot(boot) || memcmp(sw.boot,boot,32))return EPROTO;
    int nonzero=0;for(unsigned i=0;i<32;++i)nonzero|=sw.nonce[i];
    return nonzero ? sw_fd_type() : EPROTO;
}
static int sw_save_state(void) {
    int fd=memfd_create("s22-switch-state",MFD_ALLOW_SEALING|MFD_CLOEXEC);
    if(fd<0)return fs1_error();
    int error=write(fd,&sw,sizeof(sw))==(ssize_t)sizeof(sw) ? 0 : EIO;
    if(!error && fcntl(fd,F_ADD_SEALS,SW_MEMFD_SEALS))error=fs1_error();
    if(!error && dup2(fd,4)!=4)error=fs1_error();
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int sw_no_children(void) {
    int status;pid_t p;
    do{p=waitpid(-1,&status,WNOHANG);}while(p<0 && errno==EINTR);
    return p==-1 && errno==ECHILD ? 0 : ECHILD;
}
/* Kernel threads have PF_KTHREAD set in /proc/pid/stat. Every other task must
 * be this initial-namespace PID1; vanished/ambiguous rows reject the claim. */
static int sw_userspace(void) {
    DIR *d=opendir("/proc");if(!d)return fs1_error();
    int error=0;unsigned count=0,self=0;
    for(;;) {
        errno=0;struct dirent *entry=readdir(d);
        if(!entry){if(errno)error=errno;break;}
        if(entry->d_name[0]<'0' || entry->d_name[0]>'9')continue;
        if(++count>8192){error=EOVERFLOW;break;}
        char *end;long pid=strtol(entry->d_name,&end,10);
        if(*end || pid<=0 || pid>INT_MAX){error=EPROTO;break;}
        char path[128],text[4096];snprintf(path,sizeof(path),"/proc/%ld/stat",pid);
        error=fs1_read_text(path,text,sizeof(text));if(error)break;
        char *tail=strrchr(text,')');char state;long ppid,pgrp,session,tty,tpgid;unsigned long flags;
        if(!tail || sscanf(tail+1," %c %ld %ld %ld %ld %ld %lu",&state,&ppid,&pgrp,&session,&tty,&tpgid,&flags)!=7)
            {error=EPROTO;break;}
        if(pid==1){if(flags&0x00200000UL || ppid!=0){error=EPROTO;break;}++self;}
        else if(!(flags&0x00200000UL)){error=EBUSY;break;}
    }
    if(closedir(d) && !error)error=fs1_error();
    return error ? error : self==1 ? 0 : EPROTO;
}
static int sw_fd_whitelist(int state) {
    for(int i=0;i<3;++i){struct stat st;if(fstat(i,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=makedev(1,3))return EPROTO;}
    int error=sw_fd_type();if(error)return error;
    DIR *d=opendir("/proc/self/fd");if(!d)return fs1_error();unsigned count=0;
    for(;;) {
        errno=0;struct dirent *entry=readdir(d);
        if(!entry){if(errno)error=errno;break;}
        if(entry->d_name[0]=='.')continue;
        char *end;long fd=strtol(entry->d_name,&end,10);
        if(*end || fd<0 || fd>INT_MAX || ++count>7){error=EPROTO;break;}
        if(fd>3 && !(state && fd==4) && fd!=dirfd(d)){error=EBUSY;break;}
    }
    if(closedir(d) && !error)error=fs1_error();
    return error;
}
struct sw_mount {unsigned id,major,minor;char point[256],root[256],type[32],options[256],super[256];};
static const char *sw_mountinfo="/proc/self/mountinfo";
/* No escapes are accepted: every admitted mount has a fixed ASCII path. */
static int sw_mounts(struct sw_mount out[SW_MAX_MOUNTS],unsigned *count,const char *prefix) {
    char data[32768];int error=fs1_read_text(sw_mountinfo,data,sizeof(data));if(error)return error;
    unsigned used=0;char *save=NULL;
    for(char *line=strtok_r(data,"\n",&save);line;line=strtok_r(NULL,"\n",&save)) {
        if(used==SW_MAX_MOUNTS || strchr(line,'\\'))return EOVERFLOW;
        struct sw_mount row={0};unsigned parent;int end=0;
        if(sscanf(line,"%u %u %u:%u %255s %255s %255s%n",&row.id,&parent,&row.major,&row.minor,
                  row.root,row.point,row.options,&end)!=7)return EPROTO;
        char *separator=strstr(line+end," - ");char source[256];
        /* All shared/slave/unbindable propagation is forbidden after MS_PRIVATE. */
        if(!separator || separator!=line+end ||
           sscanf(separator," - %31s %255s %255s%n",row.type,source,row.super,&end)!=3 || separator[end])return EPROTO;
        if(prefix) {
            size_t n=strlen(prefix);
            if(strncmp(row.point,prefix,n) || (row.point[n] && row.point[n]!='/'))continue;
            memmove(row.point,row.point+n,strlen(row.point+n)+1);if(!row.point[0])strcpy(row.point,"/");
        }
        if(strcmp(row.root,"/"))return EPROTO;
        for(unsigned i=0;i<used;++i)if(out[i].id==row.id || !strcmp(out[i].point,row.point))return EPROTO;
        out[used++]=row;
    }
    for(unsigned i=0;i<used;++i)for(unsigned j=i+1;j<used;++j)if(strcmp(out[i].point,out[j].point)>0)
        {struct sw_mount temp=out[i];out[i]=out[j];out[j]=temp;}
    *count=used;return used ? 0 : EPROTO;
}
static int sw_mount_allowed(const struct sw_mount *m,int final) {
    const char *expected=NULL;
    if(!strcmp(m->point,"/"))expected=final ? "ext4" : NULL;
    else if(!strcmp(m->point,"/dev"))expected="tmpfs";
    else if(!strcmp(m->point,"/proc"))expected="proc";
    else if(!strcmp(m->point,"/sys"))expected="sysfs";
    else if(!strcmp(m->point,"/sys/kernel/debug"))expected="debugfs";
    else if(!strcmp(m->point,final ? "/run/config" : "/config"))expected="configfs";
    else if(!strcmp(m->point,final ? "/run" : "/s22-root-work"))expected="tmpfs";
    else if(!final && !strcmp(m->point,"/run"))expected="tmpfs";
    else if(!final && !strcmp(m->point,"/s22-root-work/root-inspect-v1/root"))expected="ext4";
    else return EPROTO;
    if(!expected)return !strcmp(m->type,"rootfs") || !strcmp(m->type,"tmpfs") ? 0 : EPROTO;
    return strcmp(m->type,expected) ? EPROTO : 0;
}
static void sw_mount_hash(struct sw_mount *rows,unsigned count,uint8_t digest[32]) {
    struct s22plus_max77705_runtime_sha256 hash;s22plus_max77705_runtime_sha256_init(&hash);
    for(unsigned i=0;i<count;++i) {
        char line[1200];int n=snprintf(line,sizeof(line),"%u %u:%u %s %s %s %s %s\n",rows[i].id,rows[i].major,rows[i].minor,
            rows[i].root,rows[i].point,rows[i].type,rows[i].options,rows[i].super);
        if(n<=0 || n>=(int)sizeof(line))sw_stop(EOVERFLOW);
        s22plus_max77705_runtime_sha256_update(&hash,(const uint8_t *)line,(size_t)n);
    }
    s22plus_max77705_runtime_sha256_final(&hash,digest);
}
static __attribute__((noreturn)) void sw_return(void) {
    uint8_t frame[48],tag[32];sw_require(sw_bytes(3,frame,sizeof(frame),0));
    if(memcmp(frame,"S328",4) || frame[4]!=1 || frame[5]!=SW_RETURN || frame[6]!=32 || frame[7] ||
       fs1_u32(frame+8)!=SW_RETURN_SEQUENCE || fs1_u32(frame+12)!=~sw_crc(frame+16,32,sw_crc(frame,12,~0U)))sw_stop(EPROTO);
    sw_tag(tag,SW_RETURN,SW_RETURN_SEQUENCE,NULL,0);
    unsigned difference=0;for(unsigned i=0;i<32;++i)difference|=tag[i]^frame[16+i];
    if(difference)sw_stop(EPROTO);
    /* Acceptance is not Download arrival. This sole effect is consumed before
     * its ACK; an incomplete ACK never reaches reboot and never reads again. */
    uint32_t body=1;sw_require(sw_send(SW_RETURN_ACK,SW_RETURN_SEQUENCE,&body,sizeof(body)));
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    (void)syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_POWER_OFF,0);
#else
    (void)syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,LINUX_REBOOT_CMD_RESTART2,"download");
#endif
    sw_park();
}
