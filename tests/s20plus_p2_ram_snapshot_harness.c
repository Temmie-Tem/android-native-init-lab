// SPDX-License-Identifier: MIT
/* Production control-flow test. File I/O runs on a caller-owned tmpfs fixture.
 * Only PID1/proc/kmsg, uid=0 and the Magisk handoff are simulated. No device,
 * mount or real /init path is touched. The relocation is an explicit model. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <unistd.h>
enum { H0_RDONLY = O_RDONLY, H0_WRONLY = O_WRONLY, H0_RDWR = O_RDWR,
       H0_CREAT = O_CREAT, H0_EXCL = O_EXCL, H0_DIRECTORY = O_DIRECTORY,
       H0_NOFOLLOW = O_NOFOLLOW, H0_NONBLOCK = O_NONBLOCK, H0_CLOEXEC = O_CLOEXEC };
#undef O_RDONLY
#undef O_WRONLY
#undef O_CLOEXEC
#undef AT_FDCWD
#undef S_IFCHR
#define S20PLUS_P2_WITNESS_FAULT_HARNESS 1
#include "s20plus_p2_pid1_ram_snapshot.c"

#ifdef __aarch64__
_Static_assert(H0_DIRECTORY == P2_O_DIRECTORY && H0_NOFOLLOW == P2_O_NOFOLLOW,
               "real ARM64 open flags");
_Static_assert(SYS_fstat == P2_NR_FSTAT && SYS_fstatfs == P2_NR_FSTATFS &&
               SYS_renameat2 == P2_NR_RENAMEAT2, "real ARM64 syscall numbers");
_Static_assert(sizeof(struct stat) == sizeof(struct p2_stat) &&
               offsetof(struct stat, st_rdev) == offsetof(struct p2_stat, rdev) &&
               offsetof(struct stat, st_size) == offsetof(struct p2_stat, size) &&
               offsetof(struct stat, st_mtim) == offsetof(struct p2_stat, mtime),
               "real ARM64 stat offsets");
_Static_assert(sizeof(struct statfs) == sizeof(struct p2_statfs), "real ARM64 statfs size");
#endif

enum { PROC_FD = 9000, BOOT_FD = 9001, KMSG_WRITE = 9002, KMSG_READ = 9003 };
static const char *scenario, *fixture;
static jmp_buf terminal;
static int first_call = -1, calls, handoff, vectors_ok, reading, read_status;
static int part_fd = -1, snapshot_fd = -1, root_fd = -1;
static size_t write_total, readback_total, reader_total, kmsg_index, stream_size;
static unsigned char stream[P2_READER_HEADER + P2_SNAPSHOT_HEADER + P2_MAX_CAPTURE_BYTES];
static char emitted[512];
static size_t emitted_size;
static int interrupted, boot_reads, deadline_jumped;
static uint64_t clock_ns = 1000000;
static unsigned long *original_stack;

static int is(const char *name) { return strcmp(scenario, name) == 0; }
static long hresult(long n) { return n < 0 ? -errno : n; }
static int host_flags(long f) {
    int result = (int)(f & 3);
    if (f & P2_O_CREAT) result |= H0_CREAT;
    if (f & P2_O_EXCL) result |= H0_EXCL;
    if (f & P2_O_DIRECTORY) result |= H0_DIRECTORY;
    if (f & P2_O_NOFOLLOW) result |= H0_NOFOLLOW;
    if (f & P2_O_NONBLOCK) result |= H0_NONBLOCK;
    if (f & O_CLOEXEC) result |= H0_CLOEXEC;
    return result;
}
static void path(char *out, size_t n, const char *suffix) {
    if (snprintf(out, n, "%s/%s", fixture, suffix) >= (int)n) abort();
}
static long hstat(long fd, struct p2_stat *out) {
#ifdef __aarch64__
    /* Let the real ARM64 syscall fill the production structure directly. */
    if(syscall(SYS_fstat,(int)fd,out)) return -errno;
    out->uid=0; out->gid=0; /* explicit privilege fixture, as in the host mode */
#else
    struct stat s;
    if (fstat((int)fd, &s)) return -errno;
    p2_zero(out, sizeof(*out));
    out->dev=s.st_dev; out->ino=s.st_ino; out->mode=s.st_mode;
    out->nlink=s.st_nlink; out->uid=0; out->gid=0; /* explicit privilege fixture */
    out->rdev=s.st_rdev; out->size=s.st_size;
    out->mtime=s.st_mtim.tv_sec; out->mtime_ns=s.st_mtim.tv_nsec;
    out->ctime=s.st_ctim.tv_sec; out->ctime_ns=s.st_ctim.tv_nsec;
#endif
    if (reading && is("reader-metadata")) out->uid=2000;
    if (reading && is("reader-changed") && reader_total) out->mtime++;
    return 0;
}

long p2w_harness_syscall(long nr, long a, long b, long c, long d, long e) {
    if (first_call == -1) first_call = (int)nr;
    calls++;
    switch (nr) {
    case NR_GETPID: return is("not-pid1") ? 42 : 1;
    case P2_NR_GETUID: case P2_NR_GETEUID: return 0;
    case P2_NR_FCNTL: return 0;
    case P2_NR_CLOCK_GETTIME: {
        if (is("clock-fail")) return -5;
        if (is("capture-deadline") && kmsg_index == 1 && !deadline_jumped) {
            clock_ns += P2_MAX_ELAPSED_NS; deadline_jumped = 1;
        }
        struct p2w_timespec *t=(void *)b;
        t->tv_sec=(int64_t)(clock_ns/1000000000); t->tv_nsec=(int64_t)(clock_ns%1000000000);
        clock_ns += 1000; return 0;
    }
    case NR_MKDIRAT: case NR_MOUNT: case NR_UMOUNT2: case NR_MKNODAT: case NR_UNLINKAT: return 0;
    case NR_READLINKAT: {
        const char *name=(void *)b, *value;
        if (!strcmp(name,"/proc/self")) value="1";
        else if (!strcmp(name,"/proc/self/ns/pid")) value="pid:[4026531836]";
        else if (!strcmp(name,"/proc/self/exe")) value="/debug_ramdisk/" P2_READER_NAME;
        else abort();
        size_t n=strlen(value); if(n>(size_t)d) abort(); memcpy((void *)c,value,n); return (long)n;
    }
    case NR_OPENAT: {
        const char *name=(void *)b;
        if (!strcmp(name,"/proc")) return PROC_FD;
        if (!strcmp(name,P2W_BOOT_ID_PATH)) return BOOT_FD;
        if (!strcmp(name,P2W_KMSG_PATH)) {
            if (is("kmsg-open")) return -13;
            return (c&3)==O_WRONLY ? KMSG_WRITE : KMSG_READ;
        }
        if (is("overlay-symlink") && !strcmp(name,"overlay.d")) return -40;
        if (!reading && is("part-open") && !strcmp(name,P2_PARTIAL_NAME)) return -13;
        char mapped[4096];
        if (!strcmp(name,"/")) { path(mapped,sizeof(mapped),""); name=mapped; }
        else if (!strcmp(name,"/debug_ramdisk")) { path(mapped,sizeof(mapped),"debug_ramdisk"); name=mapped; }
        long fd=hresult(openat((int)a,name,host_flags(c),(mode_t)d));
        if (!strcmp((char *)b,"/") && fd>=0) root_fd=(int)fd;
        if (!reading && !strcmp((char *)b,P2_PARTIAL_NAME) && fd>=0) part_fd=(int)fd;
        if (reading && (!strcmp((char *)b,P2_SNAPSHOT_NAME)||!strcmp((char *)b,P2_PARTIAL_NAME)) && fd>=0)
            snapshot_fd=(int)fd;
        return fd;
    }
    case P2_NR_FSTATFS: {
        struct p2_statfs *out=(void *)b; p2_zero(out,sizeof(*out));
        if (a==PROC_FD) { out->type=P2_PROC_MAGIC; return 0; }
        struct statfs s; if(fstatfs((int)a,&s)) return -errno;
        out->type=s.f_type;
        if ((!reading && is("root-not-ram") && a==root_fd) || (reading && is("reader-not-ram"))) out->type=0xef53;
        return 0;
    }
    case P2_NR_FSTAT:
        if (a==KMSG_WRITE || a==KMSG_READ) {
            struct p2_stat *out=(void *)b; p2_zero(out,sizeof(*out)); out->mode=S_IFCHR|0600;
            out->rdev=p2w_make_dev(1,11); return 0;
        }
        return hstat(a,(void *)b);
    case NR_WRITE:
        if (a==KMSG_WRITE) {
            if (is("emit-short")) return c-1;
            if ((size_t)c>=sizeof(emitted)) abort();
            memcpy(emitted,(void *)b,(size_t)c);
            emitted_size=(size_t)c; return c;
        }
        if (reading && a==1) {
            size_t n=(size_t)c;
            if (is("stdout-zero")) return 0;
            if (n>17) n=17; /* actual reader's full-write loop */
            if(stream_size+n>sizeof(stream)) abort();
            memcpy(stream+stream_size,(void *)b,n); stream_size+=n;
            return (long)n;
        }
        if (a==part_fd) {
            if (is("write-eintr") && !interrupted) { interrupted=1; return -4; }
            if (is("write-zero") && write_total) return 0;
            if (is("write-error") && write_total) return -5;
            size_t n=(size_t)c;
            if ((is("write-short") || is("write-zero") || is("write-error")) && n>7) n=7;
            long rc=hresult(write((int)a,(void *)b,n)); if(rc>0) write_total+=(size_t)rc; return rc;
        }
        abort();
    case NR_READ:
        if (a==BOOT_FD) {
            const char *id="11111111-2222-4333-8444-555555555555\n";
            if(reading && is("reader-boot") && boot_reads++) id="99999999-2222-4333-8444-555555555555\n";
            memcpy((void *)b,id,37); return 37;
        }
        if (a==KMSG_READ) {
            if (is("kmsg-epipe") && kmsg_index==1) return -32;
            if (is("kmsg-eagain") && kmsg_index==1) return -11;
            if (is("kmsg-eio") && kmsg_index==1) return -5;
            char line[1024];
            if(kmsg_index==0) snprintf(line,sizeof(line),"6,%d,1,-;Linux version fixture\n",is("prefix-lost")?8:0);
            else if(kmsg_index==1) snprintf(line,sizeof(line),"6,%d,2,-;Run /init as init process\n",is("prefix-lost")?9:is("prefix-gap")?2:1);
            else if(kmsg_index==2) snprintf(line,sizeof(line),"14,%d,3,-;%.*s",is("prefix-lost")?10:is("prefix-gap")?3:2,(int)emitted_size,emitted);
            else return -11;
            size_t n=strlen(line); if(n>(size_t)c) return -22;
            memcpy((void *)b,line,n); kmsg_index++; return (long)n;
        }
        if(reading && a==snapshot_fd && is("reader-short-io") && reader_total) return -5;
        { size_t n=(size_t)c;
          if(reading && is("reader-short-io") && n>40) n=40;
          long rc=hresult(read((int)a,(void *)b,n));
          if(rc>0 && reading) reader_total+=(size_t)rc;
          if(rc>0 && !reading) {
              if(is("readback-bad") && !readback_total) ((unsigned char *)b)[0]^=1;
              readback_total+=(size_t)rc;
          }
          return rc; }
    case P2_NR_LSEEK: return hresult(lseek((int)a,(off_t)b,(int)c));
    case P2_NR_FSYNC: return is("fsync-fail") ? -5 : hresult(fsync((int)a));
    case NR_CLOSE:
        if(a>=PROC_FD) return 0;
        { int fd=(int)a; long rc=hresult(close(fd));
          if(!reading && fd==part_fd && is("close-fail")) return -5;
          return rc; }
    case P2_NR_RENAMEAT2:
        if(is("rename-file")) return -5;
        return hresult(syscall(SYS_renameat2,(int)a,(char *)b,(int)c,(char *)d,(unsigned)e));
    case NR_RENAMEAT:
        if(strcmp((char *)b,"/init.magisk")||strcmp((char *)d,"/init")) abort();
        return is("rename-init") ? -5 : 0;
    case NR_EXECVE:
        handoff=1;
        vectors_ok=(char **)b==(char **)&original_stack[1] && (char **)c==(char **)&original_stack[4];
        if(is("exec-fail")) return -8;
        longjmp(terminal,1);
    case NR_NANOSLEEP:
        if(((struct p2w_timespec *)a)->tv_sec>=60) longjmp(terminal,2);
        return 0;
    default: fprintf(stderr,"unexpected syscall %ld\n",nr); abort();
    }
}

static void save(const char *name,const unsigned char *data,size_t n) {
    char target[4096]; path(target,sizeof(target),name); FILE *out=fopen(target,"wb");
    if(!out || fwrite(data,1,n,out)!=n || fclose(out)) abort();
}
int main(int argc,char **argv) {
    if(argc!=3) return 2;
    scenario=argv[1]; fixture=argv[2];
    unsigned long stack[]={2,(unsigned long)"/init",(unsigned long)"fixture-arg",0,(unsigned long)"PATH=/sbin",0};
    original_stack=stack;
    int ending=setjmp(terminal);
    if(!ending) p2w_main(stack);
    /* Model only the documented file relocation; this is not execution of
     * magiskinit or evidence that the actual S20+ handoff works. */
    const char *names[]={P2_SNAPSHOT_NAME,P2_PARTIAL_NAME};
    for(unsigned i=0;i<2;i++) {
        char from[4096],to[4096],suffix[512];
        snprintf(suffix,sizeof(suffix),"overlay.d/sbin/%s",names[i]); path(from,sizeof(from),suffix);
        snprintf(suffix,sizeof(suffix),"debug_ramdisk/%s",names[i]); path(to,sizeof(to),suffix);
        if(rename(from,to) && errno!=ENOENT) abort();
    }
    int producer_calls=calls;
    reading=1; clock_ns=1000000;
    read_status=p2_read_snapshot();
    save("reader.raw",stream,stream_size);
    printf("{\"ending\":\"%s\",\"first_syscall\":%d,\"handoff\":%d,\"vectors_ok\":%d,\"reader_returncode\":%d,\"raw_size\":%zu,\"calls\":%d,\"producer_calls\":%d}\n",
        ending==1?"exec":"park",first_call,handoff,vectors_ok,read_status,stream_size,calls,producer_calls);
    return 0;
}
