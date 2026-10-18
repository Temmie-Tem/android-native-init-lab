/* H0 only: real proc-reader syscalls on synthetic files, real AT serialization
 * and authentication, deterministic clock and kmsg readback. No device access. */
#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/vfs.h>
#include <time.h>
#include <unistd.h>
#include "s22plus_fyg8_max77705_result_parser.inc.c"

static uint64_t now_ms=6000;
static unsigned actor=6,log_live[4],logged,drop,log_delay;
static char last_line[512];
static size_t executable_at;
static const char executable[]="synthetic watchdog H0 executable";
static int fs1_error(void){return errno ? errno : EIO;}
static int fs1_read_text(const char *p,char *out,size_t n) {
    assert(!strcmp(p,"/proc/sys/kernel/random/boot_id"));
    snprintf(out,n,"01234567-89ab-cdef-0123-456789abcdef\n");return 0;
}
static int log_clock(clockid_t c,struct timespec *t) {
    assert(c==CLOCK_BOOTTIME);t->tv_sec=now_ms/1000;t->tv_nsec=(now_ms%1000)*1000000;return 0;
}
static int log_sleep(const struct timespec *t,struct timespec *r) {
    (void)r;now_ms+=(uint64_t)t->tv_sec*1000+t->tv_nsec/1000000;return 0;
}
static int log_open(const char *p,int flags,...) {
    int fd;
    if(!strcmp(p,"/proc/self/exe")){fd=3;executable_at=0;}
    else {assert(!strcmp(p,"/dev/kmsg"));fd=(flags&O_ACCMODE)==O_RDONLY ? 1 : 2;}
    assert(!log_live[fd]);log_live[fd]=1;return 1000+fd;
}
static int log_stat(int fd,struct stat *st) {
    fd-=1000;assert(fd>0 && fd<4 && log_live[fd]);memset(st,0,sizeof(*st));
    st->st_mode=fd==3 ? S_IFREG|0500 : S_IFCHR|0600;
    st->st_rdev=makedev(1,11);st->st_size=sizeof(executable)-1;return 0;
}
static off_t log_seek(int fd,off_t x,int how){assert(fd==1001 && x==0 && how==SEEK_END);return 0;}
static int log_close(int fd){fd-=1000;assert(fd>0 && fd<4 && log_live[fd]);log_live[fd]=0;return 0;}
static ssize_t log_write(int fd,const void *buf,size_t n) {
    assert(fd==1002 && log_live[2] && n<sizeof(last_line));
    memcpy(last_line,buf,n);last_line[n]=0;++logged;now_ms+=log_delay;
    if(!drop)fputs(last_line,stdout);
    return (ssize_t)n;
}
static ssize_t log_read(int fd,void *buf,size_t n) {
    if(fd==1003) {
        size_t left=sizeof(executable)-1-executable_at;if(n>left)n=left;
        memcpy(buf,executable+executable_at,n);executable_at+=n;return (ssize_t)n;
    }
    assert(fd==1001 && log_live[1]);if(drop){errno=EAGAIN;return -1;}
    char text[600];int got=snprintf(text,sizeof(text),"14,1,0,-;%s",last_line+4);
    assert(got>0 && (size_t)got<=n);memcpy(buf,text,(size_t)got);return got;
}
#define clock_gettime log_clock
#define nanosleep log_sleep
#define open log_open
#define fstat log_stat
#define lseek log_seek
#define close log_close
#define write log_write
#define read log_read
#define getpid() (actor==6 ? 21 : 31)
#define getppid() 1
#define S22_AUTOBOOT_TRACE 6
#define S22_AUTOBOOT_RCS_TRACE
static const uint8_t harness_key[32]={7},harness_run[16]={8};
#define AT_KEY harness_key
#define AT_RUN harness_run
#include "s22plus_autoboot_transition_v1.h"
#undef clock_gettime
#undef nanosleep
#undef open
#undef fstat
#undef lseek
#undef close
#undef write
#undef read
#undef getpid
#undef getppid

static const char *root,*scenario;
static char names[512][16];
static unsigned live[512],proc_calls,read_calls,stat_reads,entries,close_fault;
static int own(int fd,const char *name) {
    if(fd<0)return fd;
    assert(fd<512 && !live[fd]);live[fd]=1;snprintf(names[fd],sizeof(names[fd]),"%s",name);return fd;
}
static void fixture_stat(unsigned pid,unsigned start,unsigned ticks) {
    char path[512];snprintf(path,sizeof(path),"%s/%u/stat",root,pid);
    FILE *f=fopen(path,"w");assert(f);fprintf(f,"%u (gh-watchdog) S",pid);
    for(unsigned field=4;field<=52;++field) {
        unsigned value=field==9 ? 0x00200000 : field==14 ? ticks : field==15 ? 2 :
            field==20 ? 1 : field==22 ? start : field==39 ? 7 : field==40 ? 99 : field==41 ? 1 : 0;
        fprintf(f," %u",value);
    }
    fputc('\n',f);assert(!fclose(f));
}
static int proc_open(const char *path,int flags,...) {
    assert(!strcmp(path,"/proc") && flags==(O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));
    ++proc_calls;return own(open(root,flags),"proc");
}
static int proc_openat(int dir,const char *name,int flags) {
    assert(dir>=0 && dir<512 && live[dir] && (flags&O_ACCMODE)==O_RDONLY);
    assert((flags&(O_NOFOLLOW|O_CLOEXEC))==(O_NOFOLLOW|O_CLOEXEC));
    if(strcmp(name,"stat") && strcmp(name,"comm") && strcmp(name,"wchan"))assert(flags&O_DIRECTORY);
    else assert(flags&O_NONBLOCK);
    if(!strcmp(scenario,"reuse-during") && !strcmp(name,"wchan"))fixture_stat(230,124,11);
    return own(openat(dir,name,flags),name);
}
static int proc_fstatfs(int fd,struct statfs *fs) {
    assert(live[fd]);int rc=fstatfs(fd,fs);
    if(!rc && strcmp(scenario,"wrong-fs"))fs->f_type=0x9fa0;
    return rc;
}
static ssize_t proc_read(int fd,void *data,size_t n) {
    assert(live[fd]);++read_calls;
    if(!strcmp(names[fd],"stat")) {
        ++stat_reads;
        if(!strcmp(scenario,"eintr")){errno=EINTR;return -1;}
        if(!strcmp(scenario,"eio")){errno=EIO;return -1;}
    }
    if(!strcmp(names[fd],"wchan") && !strcmp(scenario,"wchan-error")){errno=EACCES;return -1;}
    if(!strcmp(scenario,"slow-read"))now_ms+=110;
    if(!strcmp(scenario,"very-slow-read"))now_ms+=300;
    if(!strcmp(scenario,"short-read") && n>1)n=1;
    return read(fd,data,n);
}
static int proc_close(int fd) {
    assert(live[fd]);live[fd]=0;int rc=close(fd);
    if(!strcmp(scenario,"close-error") && !close_fault++){errno=EIO;return -1;}
    return rc;
}
static int proc_fcntl(int fd,int op,int arg) {
    assert(live[fd] && op==F_DUPFD_CLOEXEC && arg==3);
    return own(fcntl(fd,op,arg),"directory-copy");
}
static struct dirent *proc_readdir(DIR *dir) {
    if(!strcmp(scenario,"too-many-entries")) {
        static struct dirent e;memset(&e,0,sizeof(e));strcpy(e.d_name,"self");++entries;return &e;
    }
    return readdir(dir);
}
static int proc_closedir(DIR *dir){int fd=dirfd(dir);assert(live[fd]);live[fd]=0;return closedir(dir);}
#define open proc_open
#define openat proc_openat
#define fstatfs proc_fstatfs
#define read proc_read
#define close proc_close
#define fcntl proc_fcntl
#define readdir proc_readdir
#define closedir proc_closedir
#define S22_DEBIAN_AUTOBOOT
#define S22_AUTOBOOT_WATCHDOG_TRACE
#include "s22plus_autoboot_watchdog_v1.h"
#undef open
#undef openat
#undef fstatfs
#undef read
#undef close
#undef fcntl
#undef readdir
#undef closedir

static void sample(void) {
    unsigned stopped=aw.disabled,calls=proc_calls;
    errno=EBUSY;at_last=AT_RCS_SLEEP_FIRST;aw_tick();
    assert(errno==EBUSY && at_last==AT_RCS_SLEEP_FIRST);
    if(stopped)assert(proc_calls==calls);
    for(unsigned i=0;i<512;++i)assert(!live[i]);
    for(unsigned i=0;i<4;++i)assert(!log_live[i]);
}
int main(int argc,char **argv) {
    assert(argc==4);root=argv[1];scenario=argv[2];actor=(unsigned)atoi(argv[3]);at_select(actor);
    if(!strcmp(scenario,"late"))now_ms=8600;
    if(!strcmp(scenario,"late-owner"))now_ms=9550;
    if(!strcmp(scenario,"after-window"))now_ms=12500;
    if(!strcmp(scenario,"budget-exhausted"))at_spent=2000;
    if(!strcmp(scenario,"disabled"))at_disabled=1;
    if(!strcmp(scenario,"log-loss"))drop=1;
    if(!strcmp(scenario,"log-delay"))log_delay=200;
    if(!strcmp(scenario,"spend-exhausted"))aw.spent=250;
    sample();
    unsigned first_reads=read_calls;
    if(!strcmp(scenario,"reuse-after"))fixture_stat(230,124,11);
    for(unsigned slot=1;slot<5;++slot) {
        if(aw_due[slot]<now_ms)continue;
        now_ms=aw_due[slot];sample();
        unsigned before=proc_calls;sample();assert(proc_calls==before);
    }
    now_ms=13000;sample();
    if(!strcmp(scenario,"eintr") || !strcmp(scenario,"eio"))assert(stat_reads==1);
    if(!strcmp(scenario,"too-many-entries"))assert(entries==4097);
    if(!strcmp(scenario,"very-slow-read"))assert(at_spent==300 && !at_disabled);
    if(actor!=6 && actor!=8)assert(!proc_calls && !logged);
    if(!strcmp(scenario,"disabled") || !strcmp(scenario,"budget-exhausted") ||
       !strcmp(scenario,"spend-exhausted"))assert(!proc_calls && !logged);
    fprintf(stderr,"H0_OK proc_calls=%u reads=%u first_reads=%u logged=%u disabled=%u spent=%llu flags=%x/%x/%x\n",
        proc_calls,read_calls,first_reads,logged,aw.disabled,(unsigned long long)at_spent,
        O_DIRECTORY,O_NOFOLLOW,O_NONBLOCK);
    return 0;
}
