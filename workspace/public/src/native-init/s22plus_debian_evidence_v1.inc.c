/* Bounded per-run evidence owned by the sequential Debian hooks. Every append
 * revalidates the entire authenticated chain and closes all borrowed fds.
 * The chain itself carries START/report-disabled state across hook execs. */
struct de_chain {
    unsigned count,started,off,complete,released,stopped,progress,last_kind,last_phase;
    unsigned boundary[2],last_event[2],status[2];
    uint64_t elapsed,pid[2],wait_ms[2],progress_ms;
    uint8_t tag[32];
};
static struct de_chain de;
static struct dh_state *de_binding;
static int de_loaded,de_failed;
static ino_t de_inode;
static unsigned de_mode;
static uint64_t de_u64(const uint8_t *p) {
    uint64_t n=0;for(unsigned i=0;i<8;++i)n|=(uint64_t)p[i]<<(8*i);return n;
}
static void de_put64(uint8_t *p,uint64_t n) {for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(n>>(8*i));}
static void de_tag(uint8_t out[32],const uint8_t *p,size_t n) {
#ifdef S22_DEBIAN_AUTOBOOT
    static const char domain[]="S22PLUS-FYG8-DEBIAN-AUTO-DURABLE-v1";
#else
    static const char domain[]="S22PLUS-FYG8-DEBIAN-DURABLE-v1";
#endif
    uint8_t pad[64],inner[32];struct s22plus_max77705_runtime_sha256 h;
    memset(pad,0x36,64);for(unsigned i=0;i<32;++i)pad[i]^=sw_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,(const uint8_t *)domain,sizeof(domain)-1);
    s22plus_max77705_runtime_sha256_update(&h,p,n);
    s22plus_max77705_runtime_sha256_final(&h,inner);
    memset(pad,0x5c,64);for(unsigned i=0;i<32;++i)pad[i]^=sw_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,inner,32);
    s22plus_max77705_runtime_sha256_final(&h,out);
}
static int de_time(void) {
    uint64_t now=sw_now();return now>=sw.deadline_ms || sw.deadline_ms-now>SW_TIMEOUT_MS ? ETIMEDOUT : 0;
}
static int de_transport_error(int error) {
    return error==EIO || error==ENODEV || error==ENXIO || error==EPIPE || error==ECONNRESET || error==ETIMEDOUT;
}
static int de_tag_equal(const uint8_t *a,const uint8_t *b) {
    unsigned different=0;for(unsigned i=0;i<32;++i)different|=a[i]^b[i];return !different;
}
static void de_header(uint8_t h[DE_HEADER]) {
    memset(h,0,DE_HEADER);memcpy(h,"S22DE01\0",8);sw_put32(h+8,1);sw_put32(h+12,DE_HEADER);
    memcpy(h+16,sw.run,16);memcpy(h+32,sw.boot,32);memcpy(h+64,sw.nonce,32);
    de_put64(h+96,sw.deadline_ms-SW_TIMEOUT_MS);de_put64(h+104,sw.deadline_ms);
    sw_put32(h+112,
#ifdef S22_AUTOBOOT_SINGLECPU
        6
#elif defined(S22_DEBIAN_AUTOBOOT)
        5
#else
        4
#endif
        );sw_put32(h+116,DE_RECORD);sw_put32(h+120,DE_RECORDS);sw_put32(h+124,DE_MAXIMUM);
    memcpy(h+128,dh_init_sha256,32);memcpy(h+160,de_binding->hook_sha,32);de_put64(h+192,sw.root_device);
    de_tag(h+224,h,224);
}
static int de_apply(struct de_chain *s,const uint8_t r[DE_RECORD]) {
    unsigned seq=fs1_u32(r+8),kind=fs1_u32(r+12),phase=fs1_u32(r+24),event=fs1_u32(r+28),flags=fs1_u32(r+56);
    uint64_t elapsed=de_u64(r+16),a=de_u64(r+32),b=de_u64(r+40),c=de_u64(r+48);
    uint8_t tag[32];de_tag(tag,r,96);
    if(memcmp(r,"S22DER1\0",8) || seq!=s->count || seq>=DE_RECORDS || fs1_u32(r+60) ||
       elapsed>=SW_TIMEOUT_MS || (seq && elapsed<s->elapsed) || flags!=s->off || s->stopped ||
       !de_tag_equal(r+64,s->tag) || !de_tag_equal(r+96,tag))return EPROTO;
    if(kind==DE_INIT) {
        if(seq || phase || event || a!=1 || b || c)return EPROTO;
    } else if(kind==DE_START) {
        if(seq!=1 || s->started || phase || event || a!=DH_START_SEQUENCE || b || c)return EPROTO;
        s->started=1;
    } else if(kind==DE_REPORT_LOST) {
        if(!s->started || s->off || s->released || phase>2 || event || !a || a>4095)return EPROTO;
        if(!b) {
            if(c || (a!=ENOENT && a!=EIO && a!=ENODEV && a!=ENXIO) ||
               !((phase==1 && ((!s->progress && s->last_kind==DE_START) ||
                 (s->progress==1 && s->last_kind==DE_BOUNDARY && s->last_event[0]==1))) ||
                 (phase==2 && s->progress==2 && s->last_kind==DE_PROGRESS)))return EPROTO;
        } else {
            if(!de_transport_error((int)a))return EPROTO;
            if(b==DH_START_ACK) {if(phase || c!=DH_START_SEQUENCE || s->last_kind!=DE_START)return EPROTO;}
            else if(b==DH_PROGRESS) {
                if(s->last_kind!=DE_PROGRESS || phase!=(s->progress<=2 ? 1U : 2U) || c!=2000+s->progress-1)return EPROTO;
            } else if(b==DH_BOUNDARY) {
                if(s->last_kind!=DE_BOUNDARY || !phase || phase!=s->last_phase ||
                   c!=(phase==1 ? 3000U : 3100U)+s->boundary[phase-1]-1)return EPROTO;
            } else return EPROTO;
        }
        s->off=1;
    } else if(kind==DE_PROGRESS) {
        unsigned ordinal=s->progress,expected=ordinal<3 ? ordinal+1 : 4;
        if(!s->started || s->complete || ordinal>=DH_SAMPLES+3 || phase!=expected ||
           event!=(ordinal<3 ? 0 : ordinal-2) || !sc_valid(c) ||
           (ordinal<2 ? a || b : b!=3 || a<(uint64_t)event*DH_SAMPLE_MS ||
             a>(uint64_t)event*DH_SAMPLE_MS+10000U || a>elapsed || (ordinal>=3 && a<=s->progress_ms)) ||
           (ordinal==1 && (s->last_event[0]!=5 || s->status[0])) ||
           (ordinal==2 && (s->last_event[1]!=5 || s->status[1])))return EPROTO;
        s->progress++;s->progress_ms=a;
    } else if(kind==DE_BOUNDARY) {
        if(!s->started || s->complete || phase<1 || phase>2 || s->progress!=phase)return EPROTO;
        unsigned i=phase-1,last=s->last_event[i];
        if(s->boundary[i]>=DH_BOUNDARY_MAX ||
           (last==0 ? event!=(phase==1 ? 1U : 2U) : last==1 ? event!=2 : last==2 ? event!=3 :
            last==3 || last==4 ? event!=4 && event!=5 : 1) ||
           (event<=2 ? a || b : a<=1 || a>INT_MAX || (event!=5 && b) || b>65535) ||
           (phase==1 && event==2 ? (s->off ? c!=0 : c<s->wait_ms[i] || c>elapsed) : c!=0) ||
           (event>=4 && (a!=s->pid[i] || (event==4 && elapsed-s->wait_ms[i]<DH_SAMPLE_MS))))return EPROTO;
        s->boundary[i]++;s->last_event[i]=event;s->pid[i]=a;s->status[i]=(unsigned)b;s->wait_ms[i]=elapsed;
    } else if(kind==DE_COMPLETE) {
        if(!s->started || s->complete || s->progress!=DH_SAMPLES+3 || phase || event || a || b || c)return EPROTO;
        s->complete=1;
    } else if(kind==DE_RELEASE) {
        if(!s->complete || s->off || s->released || phase || event || a!=DH_RELEASE_SEQUENCE || b || c)return EPROTO;
        s->released=1;
    } else if(kind==DE_STOP) {
        if(!seq || phase || event || !a || a>4095 || b!=SW_WITNESS || c)return EPROTO;
        s->stopped=1;
    } else return EPROTO;
    memcpy(s->tag,r+96,32);s->count++;s->elapsed=elapsed;s->last_kind=kind;s->last_phase=phase;return 0;
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
    for(size_t pos=DE_HEADER;pos<(size_t)before.st_size;pos+=DE_RECORD)
        if((error=de_apply(state,raw+pos)))return error;
    if(!de_inode)de_inode=before.st_ino;
    return 0;
}
static int de_open(int append) {
    int parent=de_parent(0);if(parent<0)return -1;
    int fd=openat(parent,dh_evidence_name,(append ? O_RDWR|O_APPEND : O_RDONLY)|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
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
    de_binding=state;int current=de_time();if(current){de_failed=1;return current;}
    int parent=de_parent(1);if(parent<0){de_failed=1;return fs1_error();}
    current=de_time();if(current){(void)close(parent);de_failed=1;return current;}
    mode_t mask=umask(0);
    int fd=openat(parent,dh_evidence_name,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
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
