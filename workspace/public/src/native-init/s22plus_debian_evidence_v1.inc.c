/* Bounded per-run evidence owned by the sequential Debian hooks. Every append
 * revalidates the entire authenticated chain and closes all borrowed fds.
 * The chain itself carries START/report-disabled state across hook execs. */
#include "s22plus_debian_evidence_chain_v1.h"
static struct de_chain de;
static struct dh_state *de_binding;
static int de_loaded,de_failed;
static ino_t de_inode;
static unsigned de_mode;
static int de_time(void) {
    uint64_t now=sw_now();return now>=sw.deadline_ms || sw.deadline_ms-now>SW_TIMEOUT_MS ? ETIMEDOUT : 0;
}
static void de_header(uint8_t h[DE_HEADER]) {
    memset(h,0,DE_HEADER);memcpy(h,"S22DE01\0",8);sw_put32(h+8,1);sw_put32(h+12,DE_HEADER);
    memcpy(h+16,sw.run,16);memcpy(h+32,sw.boot,32);memcpy(h+64,sw.nonce,32);
    de_put64(h+96,sw.deadline_ms-SW_TIMEOUT_MS);de_put64(h+104,sw.deadline_ms);
    sw_put32(h+112,
#ifdef S22_DEBIAN_CRON_CONFIG
        8
#elif defined(S22_DEBIAN_REBOOT)
        7
#elif defined(S22_AUTOBOOT_SINGLECPU)
        6
#elif defined(S22_DEBIAN_AUTOBOOT)
        5
#else
        4
#endif
        );sw_put32(h+116,DE_RECORD);sw_put32(h+120,DE_RECORDS);sw_put32(h+124,DE_MAXIMUM);
    memcpy(h+128,dh_init_sha256,32);memcpy(h+160,de_binding->hook_sha,32);de_put64(h+192,sw.root_device);
#ifdef S22_DEBIAN_REBOOT
    sw_put32(h+200,rb_phase);sw_put32(h+204,RB_BASE_COUNT);sw_put32(h+208,rb_installed(rb_phase));
#endif
    de_tag(h+224,h,224);
}
static int de_directory(int fd) {
    struct stat st;struct statfs fs;
    return fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0xef53 ||
        (uint64_t)st.st_dev!=sw.root_device || st.st_mode!=(S_IFDIR|0755) || st.st_uid || st.st_gid ||
        st.st_nlink<2 ? EPROTO : 0;
}
static int de_parent(int create) {
    int root=open("/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(root<0)return -1;
    int error=de_directory(root),fd=root;
    const char *parts[]={"var","lib","lab"};
    for(unsigned i=0;i<3 && !error;++i) {
        int made=0;
        if(i==2 && create) {
            if((error=de_time()))break;
            mode_t mask=umask(0);int rc=mkdirat(fd,parts[i],0755);int saved=errno;umask(mask);
            if(rc && saved!=EEXIST){error=saved;break;}made=!rc;
        }
        int next=openat(fd,parts[i],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if(next<0){error=fs1_error();break;}
        error=de_directory(next);
        if(!error && made && (fsync(fd) || fsync(next)))error=fs1_error();
        if(close(fd) && !error)error=fs1_error();
        fd=next;
    }
    if(error){(void)close(fd);errno=error;return -1;}return fd;
}
static int de_file_stat(int fd,struct stat *st) {
    return fstat(fd,st) || (uint64_t)st->st_dev!=sw.root_device || st->st_mode!=(S_IFREG|0600) ||
        st->st_uid || st->st_gid || st->st_nlink!=1 || st->st_size<DE_HEADER ||
        st->st_size>DE_MAXIMUM || (st->st_size-DE_HEADER)%DE_RECORD ? EPROTO : 0;
}
static int de_scan(int fd,struct de_chain *state) {
    struct stat before,after;uint8_t raw[DE_MAXIMUM],expected[DE_HEADER];
    int error=de_file_stat(fd,&before);if(error)return error;
    if(de_inode && de_inode!=before.st_ino)return EPROTO;
    if(pread(fd,raw,(size_t)before.st_size,0)!=before.st_size || fstat(fd,&after) ||
       before.st_dev!=after.st_dev || before.st_ino!=after.st_ino || before.st_size!=after.st_size ||
       before.st_mtim.tv_sec!=after.st_mtim.tv_sec || before.st_mtim.tv_nsec!=after.st_mtim.tv_nsec ||
       before.st_ctim.tv_sec!=after.st_ctim.tv_sec || before.st_ctim.tv_nsec!=after.st_ctim.tv_nsec)return EIO;
    de_header(expected);if(memcmp(raw,expected,DE_HEADER))return EPROTO;
    memset(state,0,sizeof(*state));memcpy(state->tag,raw+224,32);
#ifdef S22_DEBIAN_CRON_CONFIG
    state->boot_phase=fs1_u32(raw+200);
#endif
    for(size_t pos=DE_HEADER;pos<(size_t)before.st_size;pos+=DE_RECORD)
        if((error=de_apply(state,raw+pos)))return error;
    if(!de_inode)de_inode=before.st_ino;
    return 0;
}
static int de_open(int append) {
#ifdef S22_DEBIAN_REBOOT
    if(!rb_valid_phase(rb_phase)){errno=EPROTO;return -1;}
    const char *name=rb_leaf(rb_phase,1);
#else
    const char *name=dh_evidence_name;
#endif
    int parent=de_parent(0);if(parent<0)return -1;
    int fd=openat(parent,name,(append ? O_RDWR|O_APPEND : O_RDONLY)|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    int error=fd<0 ? fs1_error() : 0;
    if(close(parent) && !error)error=fs1_error();
    if(error){if(fd>=0)(void)close(fd);errno=error;return -1;}return fd;
}
static int de_load(struct dh_state *state) {
    de_binding=state;int fd=de_open(0),error=fd<0 ? fs1_error() : 0;
    if(!error)error=de_scan(fd,&de);
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(error){de_failed=1;return error;}de_loaded=1;return 0;
}
static int de_begin(struct dh_state *state) {
#ifdef S22_DEBIAN_REBOOT
    if(!rb_valid_phase(rb_phase))return EPROTO;
    const char *name=rb_leaf(rb_phase,1);
#else
    const char *name=dh_evidence_name;
#endif
    de_binding=state;int current=de_time();if(current){de_failed=1;return current;}
    int parent=de_parent(1);if(parent<0){de_failed=1;return fs1_error();}
    current=de_time();if(current){(void)close(parent);de_failed=1;return current;}
    mode_t mask=umask(0);
    int fd=openat(parent,name,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    int error=fd<0 ? fs1_error() : 0;umask(mask);
    uint8_t header[DE_HEADER];de_header(header);
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 28
    sw.deadline_ms=sw_now();
#endif
    if(!error)error=de_time();
    size_t header_size=DE_HEADER;
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 15
    header_size--;
#endif
    if(!error && write(fd,header,header_size)!=DE_HEADER)error=EIO;
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 16
    if(!error)error=EIO;
#endif
    if(!error && fsync(fd))error=fs1_error();
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 17
    if(!error)error=EIO;
#endif
    if(!error && fsync(parent))error=fs1_error();
    if(!error)error=de_scan(fd,&de);
    if(fd>=0 && close(fd) && !error)error=fs1_error();
    if(close(parent) && !error)error=fs1_error();
    if(error){de_failed=1;return error;}de_loaded=1;return 0;
}
static int de_event(unsigned kind,unsigned phase,unsigned event,uint64_t a,uint64_t b,uint64_t c) {
    uint64_t now=sw_now();int error=0,fd=-1;
#ifdef S22_AUTOBOOT_RCS_TRACE
    bool traced=kind==DE_BOUNDARY && phase==1 && event==3;
#else
    bool traced=false;
#endif
    if(!de_loaded || de_failed || now>=sw.deadline_ms || sw.deadline_ms-now>SW_TIMEOUT_MS || de.count>=DE_RECORDS)
        {de_failed=1;return EPROTO;}
    uint8_t record[DE_RECORD]={0};memcpy(record,"S22DER1\0",8);sw_put32(record+8,de.count);sw_put32(record+12,kind);
    de_put64(record+16,now-(sw.deadline_ms-SW_TIMEOUT_MS));sw_put32(record+24,phase);sw_put32(record+28,event);
    de_put64(record+32,a);de_put64(record+40,b);de_put64(record+48,c);sw_put32(record+56,de.off);
    memcpy(record+64,de.tag,32);de_tag(record+96,record,96);
    struct de_chain next=de,actual;
    if((error=de_apply(&next,record)))goto done;
    fd=de_open(1);if(fd<0){error=fs1_error();goto done;}
    if((error=de_scan(fd,&actual)))goto done;
    if(actual.count!=de.count || !de_tag_equal(actual.tag,de.tag)){error=EPROTO;goto done;}
    if((error=de_time()))goto done;
    size_t record_size=DE_RECORD;
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 18
    if(kind==DE_START)record_size--;
#endif
    ssize_t written=traced ? AT_SYS_GUARD(AT_RCS_RECORD_WRITE,
        if((error=de_time()))goto done;,write(fd,record,record_size)) : write(fd,record,record_size);
    if(written!=DE_RECORD){error=EIO;goto done;}
#if defined(S22_ROOT_INSPECT_VIRT_TEST) && S22_DEBIAN_FAULT == 19
    if(kind==DE_START){error=EIO;goto done;}
#endif
    if(traced ? AT_SYS(AT_RCS_RECORD_FSYNC,fsync(fd)) : fsync(fd)){error=fs1_error();goto done;}
    uint8_t back[DE_RECORD];struct stat st;
    if(traced)AT_BEGIN(AT_RCS_RECORD_VERIFY,2);
    if(de_file_stat(fd,&st) || st.st_size!=(off_t)(DE_HEADER+next.count*DE_RECORD) ||
       pread(fd,back,DE_RECORD,DE_HEADER+de.count*DE_RECORD)!=DE_RECORD || memcmp(back,record,DE_RECORD))error=EIO;
    if(traced)AT_RETURN(AT_RCS_RECORD_VERIFY,2,error,(unsigned)error);
 done:
    if(fd>=0 && (traced ? AT_SYS(AT_RCS_RECORD_CLOSE,close(fd)) : close(fd)) && !error)error=fs1_error();
    if(error || sw_now()>=sw.deadline_ms){de_failed=1;return error ? error : ETIMEDOUT;}
    de=next;return 0;
}
static int de_report_lost(int error,unsigned kind,unsigned sequence) {
    if(!de.started || de.off || !(de_transport_error(error) || (kind==0 && error==ENOENT)))return error ? error : EPROTO;
    int result=de_event(DE_REPORT_LOST,de_mode,0,(unsigned)error,kind,sequence);
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    if(!result)dprintf(2,"DHVM_REPORT_DISABLED phase=%u kind=%u sequence=%u\n",de_mode,kind,sequence);
#endif
    return result;
}
