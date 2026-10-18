/* Optional, inactive-by-default procfs observation of the existing watchdog.
 * No timer, scheduler, signal, affinity, watchdog or workload control operation.
 * Clock/byte/call bounds cannot cancel a kernel read that does not return. */
#ifndef S22_AUTOBOOT_WATCHDOG_V1_H
#define S22_AUTOBOOT_WATCHDOG_V1_H
#ifdef S22_AUTOBOOT_WATCHDOG_TRACE
#if !defined(S22_AUTOBOOT_RCS_TRACE) || !defined(S22_DEBIAN_AUTOBOOT)
#error "watchdog observation requires automatic rcS observation"
#endif
#include <dirent.h>
#include <limits.h>
#include <sys/vfs.h>

#define AW_PROC_MAGIC 0x9fa0
#define AW_KTHREAD 0x00200000ULL
#define AW_SLOTS 5U
#define AW_TOTAL_MS 250U
static const unsigned aw_due[AW_SLOTS]={0,9000,10000,11000,12000};
struct aw_task { unsigned pid,start,cpu,policy,priority; char state; uint64_t ticks; };
static struct { unsigned next,pid,start,disabled; uint64_t spent; } aw;

static int aw_number(const char *p,size_t n,uint64_t *value) {
    uint64_t v=0;if(!n || n>20)return EPROTO;
    for(size_t i=0;i<n;++i) {
        if(p[i]<'0' || p[i]>'9' || v>(UINT64_MAX-(unsigned)(p[i]-'0'))/10)return EPROTO;
        v=v*10+(unsigned)(p[i]-'0');
    }
    *value=v;return 0;
}
static int aw_parse_stat(const char *text,unsigned pid,struct aw_task *out) {
    const char *p=strchr(text,' ');uint64_t number;
    if(!p || aw_number(text,(size_t)(p-text),&number) || number!=pid ||
       strncmp(p," (gh-watchdog) ",15))return EPROTO;
    p+=15;if(!*p || !strchr("RSDTtXZPI",*p) || p[1]!=' ')return EPROTO;
    struct aw_task t={.pid=pid,.state=*p};p+=2;
    uint64_t flags=0,user=0,system=0,threads=0,start=0,cpu=0,priority=0,policy=0;
    /* Field 3 was state. Selected unsigned fields are from Linux proc stat.
     * Other fields may be signed; no addresses or unrelated values are kept. */
    for(unsigned field=4;field<=52;++field) {
        const char *end=p;while(*end && *end!=' ' && *end!='\n')++end;
        if(end==p)return EPROTO;
        bool selected=field==9 || field==14 || field==15 || field==20 || field==22 ||
            field==39 || field==40 || field==41;
        if(selected) {
            if(aw_number(p,(size_t)(end-p),&number))return EPROTO;
            if(field==9)flags=number;else if(field==14)user=number;else if(field==15)system=number;
            else if(field==20)threads=number;else if(field==22)start=number;
            else if(field==39)cpu=number;else if(field==40)priority=number;else policy=number;
        } else {
            const char *digits=p;if(*digits=='-')++digits;
            if(aw_number(digits,(size_t)(end-digits),&number))return EPROTO;
        }
        if(field==52) {if(*end=='\n')++end;if(*end)return EPROTO;}
        else {if(*end!=' ')return EPROTO;p=end+1;}
    }
    if(!(flags&AW_KTHREAD) || threads!=1 || start>UINT32_MAX || cpu>=32 ||
       priority>99 || policy>6 || user>INT64_MAX || system>(uint64_t)INT64_MAX-user)return EPROTO;
    t.start=(unsigned)start;t.cpu=(unsigned)cpu;t.priority=(unsigned)priority;
    t.policy=(unsigned)policy;t.ticks=user+system;*out=t;return 0;
}
static int aw_expired(uint64_t end){return at_now()>=end ? ETIMEDOUT : 0;}
static int aw_close(int fd,int error) {
    if(close(fd) && !error)error=errno ? errno : EIO;
    return error;
}
static int aw_read(int dir,const char *name,char *out,size_t capacity,uint64_t end) {
    if(aw_expired(end))return ETIMEDOUT;
    int fd=openat(dir,name,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);if(fd<0)return errno ? errno : EIO;
    struct stat st;struct statfs fs;size_t used=0;int error=0;unsigned calls=0;
    if(fstat(fd,&st) || fstatfs(fd,&fs) || !S_ISREG(st.st_mode) || fs.f_type!=AW_PROC_MAGIC)error=EPROTO;
    while(!error) {
        if(aw_expired(end)){error=ETIMEDOUT;break;}
        if(++calls>3){error=EOVERFLOW;break;}
        char extra;size_t room=capacity-1-used;
        ssize_t n=read(fd,room ? out+used : &extra,room ? room : 1);
        if(n<0){error=errno ? errno : EIO;break;}
        if(!n)break;
        if(!room || (size_t)n>room){error=EOVERFLOW;break;}
        used+=(size_t)n;
    }
    error=aw_close(fd,error);if(!error && aw_expired(end))error=ETIMEDOUT;
    if(!error && (!used || memchr(out,0,used)))error=EPROTO;
    if(!error)out[used]=0;
    return error;
}
static int aw_pid_dir(int proc,unsigned pid,uint64_t end) {
    if(aw_expired(end)){errno=ETIMEDOUT;return -1;}
    char name[16];snprintf(name,sizeof(name),"%u",pid);
    return openat(proc,name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
}
static int aw_stat(int dir,unsigned pid,struct aw_task *out,uint64_t end) {
    char text[2048];int error=aw_read(dir,"stat",text,sizeof(text),end);
    return error ? error : aw_parse_stat(text,pid,out);
}
static int aw_discover(int proc,struct aw_task *found,uint64_t end) {
    int copy=fcntl(proc,F_DUPFD_CLOEXEC,3);if(copy<0)return errno ? errno : EIO;
    DIR *dir=fdopendir(copy);if(!dir)return aw_close(copy,errno ? errno : EIO);
    int error=0;unsigned entries=0,matches=0;
    for(;;) {
        if(aw_expired(end)){error=ETIMEDOUT;break;}
        errno=0;struct dirent *entry=readdir(dir);
        if(!entry){if(errno)error=errno;break;}
        if(++entries>4096){error=EOVERFLOW;break;}
        uint64_t number;if(aw_number(entry->d_name,strlen(entry->d_name),&number) ||
            number<=2 || number>INT_MAX)continue;
        char canonical[16];snprintf(canonical,sizeof(canonical),"%u",(unsigned)number);
        if(strcmp(canonical,entry->d_name))continue;
        int task=aw_pid_dir(proc,(unsigned)number,end);
        if(task<0) {if(errno==ENOENT || errno==ESRCH)continue;error=errno ? errno : EIO;break;}
        char comm[32];int e=aw_read(task,"comm",comm,sizeof(comm),end);
        if(e && e!=ENOENT && e!=ESRCH)error=e;
        if(!e && !strcmp(comm,"gh-watchdog\n")) {
            struct aw_task candidate;
            e=aw_stat(task,(unsigned)number,&candidate,end);
            if(!e){*found=candidate;++matches;}
            else error=e;
        }
        int closed=aw_close(task,0);if(closed)error=closed;
        if(e==ETIMEDOUT)error=e;
        if(error || matches>1){if(!error)error=EEXIST;break;}
    }
    if(closedir(dir) && !error)error=errno ? errno : EIO;
    return error ? error : matches==1 ? 0 : ENOENT;
}
/* Symbol classes only. Zero also means running/unavailable/permission-hidden;
 * neither zero nor a class proves a particular live watchdog phase. */
static unsigned aw_wchan(const char *text) {
    if(!strcmp(text,"0") || !strcmp(text,"0\n"))return 0;
    static const char *names[]={"qcom_wdt_kthread","smp_call_function_single", "csd_lock_wait",
        "wait_for_completion","schedule_timeout"};
    for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i) {
        size_t n=strlen(names[i]);if(!strncmp(text,names[i],n) &&
            (!text[n] || (text[n]=='\n' && !text[n+1])))return i+1;
    }
    return 6;
}
static int aw_collect(struct aw_task *out,unsigned *channel,int *channel_error,uint64_t end) {
    int proc=open("/proc",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(proc<0)return errno ? errno : EIO;
    struct statfs fs;int error=0;
    if(fstatfs(proc,&fs) || fs.f_type!=AW_PROC_MAGIC)error=EPROTO;
    if(!error && !aw.pid) {
        struct aw_task first={0};error=aw_discover(proc,&first,end);
        if(!error){aw.pid=first.pid;aw.start=first.start;}
    }
    int task=error ? -1 : aw_pid_dir(proc,aw.pid,end);
    if(task<0 && !error)error=errno ? errno : EIO;
    struct aw_task before,after;
    if(!error)error=aw_stat(task,aw.pid,&before,end);
    if(!error && before.start!=aw.start)error=ESTALE;
    if(!error) {
        char wait[128];*channel_error=aw_read(task,"wchan",wait,sizeof(wait),end);
        if(!*channel_error)*channel=aw_wchan(wait);
        error=aw_stat(task,aw.pid,&after,end);
        if(!error && (after.start!=before.start || after.ticks<before.ticks))error=ESTALE;
        if(!error)*out=after;
    }
    if(task>=0)error=aw_close(task,error);
    error=aw_close(proc,error);if(!error && aw_expired(end))error=ETIMEDOUT;
    return error;
}
static void aw_tick(void) {
    if(aw.disabled || at_disabled || (at_actor!=6 && at_actor!=8) || aw.next>=AW_SLOTS ||
       at_spent>=2000 || aw.spent>=AW_TOTAL_MS)return;
    int saved=errno;uint64_t begin=at_now();unsigned lost=at_lost,last=at_last;
    if(begin==UINT64_MAX || begin>=12500){aw.disabled=1;goto done;}
    /* A later owner may start after an earlier opportunity. Skip expired
     * slots without reading, waiting, or inventing a missed observation. */
    while(aw.next<AW_SLOTS && begin>=(aw.next ? aw_due[aw.next]+250 : 8500))++aw.next;
    if(aw.next>=AW_SLOTS)goto done;
    unsigned slot=aw.next;if(begin<aw_due[slot])goto done;
    ++aw.next;uint64_t latest=slot ? aw_due[slot]+250 : 8500;
    struct aw_task task={0};unsigned channel=0;int channel_error=0,error=0;
    uint64_t budget=aw.pid ? 25 : 100;
    if(budget>AW_TOTAL_MS-aw.spent)budget=AW_TOTAL_MS-aw.spent;
    if(budget>2000-at_spent)budget=2000-at_spent;
    uint64_t end=begin+budget;if(end>latest)end=latest;
    if(begin>=end)error=ETIMEDOUT;else error=aw_collect(&task,&channel,&channel_error,end);
    uint64_t acquired=at_now(),elapsed=acquired<begin ? UINT64_MAX : acquired-begin;
    if(elapsed>2000-at_spent){aw.disabled=1;at_spent=2000;goto done;}
    aw.spent+=elapsed;at_spent+=elapsed;
    if(acquired>=12500){aw.disabled=1;goto done;}
    unsigned sample=(unsigned)acquired*8+slot;
    unsigned properties=(unsigned)(unsigned char)task.state|(task.cpu<<8)|(task.policy<<16)|(task.priority<<24);
    at_emit(AT_WATCHDOG_TASK,4,3,error ? 0 : (int64_t)task.ticks,(unsigned)error,
        error ? 0 : task.pid,error ? 0 : task.start,error ? 0 : properties,sample);
    if(!error && at_lost==lost)at_emit(AT_WATCHDOG_WCHAN,4,3,channel_error ? 0 : channel,(unsigned)channel_error,
        channel_error ? 0 : task.pid,channel_error ? 0 : task.start,0,sample);
    if(error || channel_error || at_lost!=lost)aw.disabled=1;
done:
    at_last=last;errno=saved;
}
#else
#define aw_tick() ((void)0)
#endif
#endif
