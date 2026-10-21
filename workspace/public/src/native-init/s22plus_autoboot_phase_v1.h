/* Optional finite observation in the two existing installed-init children.
 * All files here are tmpfs/tracefs. No service or watchdog control is added.
 * Budgets limit admitted work; they cannot cancel a blocked kernel syscall. */
#ifndef S22_AUTOBOOT_PHASE_V1_H
#define S22_AUTOBOOT_PHASE_V1_H
#if defined(S22_AUTOBOOT_SCRIPT_CHANNEL) && defined(S22_AUTOBOOT_PHASE_TRACE)
#error "select one optional observer"
#endif
#ifdef S22_AUTOBOOT_SCRIPT_CHANNEL
#include "s22plus_autoboot_script_v1.h"
#elif defined(S22_AUTOBOOT_PHASE_TRACE)
#include <sys/socket.h>
#include <sys/vfs.h>
#include "s22plus_autoboot_phase_seal_v1.h"
#include "s22plus_autoboot_phase_parse_v1.h"
#define AP_ROOT "/run/s22-debian/phase-trace"
#define AP_INSTANCE AP_ROOT "/instances/s22phase"
#define AP_STATE "/run/s22-debian/phase-state"
#define AP_DISPATCHER "/run/s22-debian/rc-observed"
#define AP_MAGIC 0x41504831U
#define AP_TRACEFS 0x74726163L
#define AP_TMPFS 0x01021994L
#define AP_ALL ((1U<<AP_PROBE_COUNT)-1U)
enum { AP_TAIL=1,AP_PARSE=2,AP_CAP=4,AP_IO=8,AP_LOG=16,AP_BUDGET=32,AP_CHANNEL=64,AP_GAP=128 };
struct ap_state {
    uint32_t magic,version,owner,handover,terminal,attempted,confirmed,mount_intent,mounted,instance;
    uint32_t enabled,flags,records,packets,packet_sequence,script_id,script_open,script_done;
    uint32_t decoded[AP_PROBE_COUNT],read_calls,read_bytes;
    uint64_t used_ms,started_ms,handover_ms,last_tick;
    uint8_t boot[32],tag[32];
};
_Static_assert(offsetof(struct ap_state,tag)+32==sizeof(struct ap_state),"phase state tag must be last");
static struct ap_state ap;
static int ap_receive=-1,ap_send=-1;
static unsigned ap_claimed,ap_local_done,ap_cleanup_disarm;
static uint64_t ap_work_begin,ap_log_begin,ap_end;
static int ap_error(void){return errno ? errno : EIO;}
static int ap_close(int fd,int error) {if(close(fd) && !error)error=ap_error();return error;}
static int ap_expired(void){return !ap_cleanup_disarm && at_now()>=ap_end ? ETIMEDOUT : 0;}
static void ap_begin(unsigned cleanup) {
    ap_work_begin=at_now();ap_log_begin=at_spent;
    unsigned limit=AP_PHASE_BUDGET_MS-(cleanup ? 0 : AP_CLEANUP_RESERVE_MS);
    ap_end=ap_work_begin+(ap.used_ms<limit ? limit-ap.used_ms : 0);
    uint64_t actor_end=ap_work_begin+(at_spent<2000 ? 2000-at_spent : 0);
    if(ap_end>actor_end)ap_end=actor_end;
    if(ap_end>sw.deadline_ms)ap_end=sw.deadline_ms;
    if(!cleanup && ap_end>AP_ABSOLUTE_WINDOW_MS)ap_end=AP_ABSOLUTE_WINDOW_MS;
    at_observation_deadline=ap_end;
}
static void ap_charge(void) {
    uint64_t now=at_now(),elapsed=now<ap_work_begin || now==UINT64_MAX ? AP_PHASE_BUDGET_MS : now-ap_work_begin;
    uint64_t logged=at_spent>=ap_log_begin ? at_spent-ap_log_begin : 0;
    if(elapsed>logged)at_spent+=elapsed-logged;
    if(at_spent>2000)at_spent=2000;
    ap.used_ms+=elapsed;if(ap.used_ms>=AP_PHASE_BUDGET_MS)ap.flags|=AP_BUDGET;
    at_observation_deadline=300000;
}
static void ap_record(unsigned stage,int64_t result,unsigned error,unsigned a,unsigned b,unsigned c,unsigned d) {
    unsigned last=at_last,sequence=at_sequence,lost=at_lost;
    at_emit(stage,4,3,result,error,a,b,c,d);at_last=last;
    if(at_sequence==sequence || at_lost!=lost)ap.flags|=AP_LOG;
}
static int ap_state_write(int create) {
    if(ap_expired())return ETIMEDOUT;
    int fd=open(AP_STATE,O_RDWR|O_CLOEXEC|O_NOFOLLOW|(create ? O_CREAT|O_EXCL : 0),0400);
    if(fd<0)return ap_error();
    struct stat st;struct statfs fs;
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || st.st_mode!=(S_IFREG|0400) ||
        st.st_uid || st.st_gid || st.st_nlink!=1 || fs.f_type!=AP_TMPFS ||
        st.st_size!=(create ? 0 : (off_t)sizeof(ap)) ? EPROTO : 0;
    if(!error) {
        sw_tag(ap.tag,175,0,(const uint8_t *)&ap,sizeof(ap)-32);
        if(pwrite(fd,&ap,sizeof(ap),0)!=(ssize_t)sizeof(ap))error=EIO;
        struct ap_state check;
        if(!error && (pread(fd,&check,sizeof(check),0)!=(ssize_t)sizeof(check) || memcmp(&check,&ap,sizeof(ap))))error=EIO;
    }
    return ap_close(fd,error);
}
static int ap_state_read(void) {
    int fd=open(AP_STATE,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return ap_error();
    struct stat st;struct statfs fs;struct ap_state state;uint8_t tag[32];
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || st.st_mode!=(S_IFREG|0400) ||
        st.st_uid || st.st_gid || st.st_nlink!=1 || st.st_size!=sizeof(state) || fs.f_type!=AP_TMPFS ||
        pread(fd,&state,sizeof(state),0)!=(ssize_t)sizeof(state) ? EPROTO : 0;
    error=ap_close(fd,error);if(error)return error;
    sw_tag(tag,175,0,(const uint8_t *)&state,sizeof(state)-32);
    if(memcmp(tag,state.tag,32) || memcmp(state.boot,sw.boot,32) || state.magic!=AP_MAGIC || state.version!=1 ||
       state.owner!=6 || state.handover!=1 || state.terminal || state.confirmed&~state.attempted ||
       state.attempted&~AP_ALL || state.records>AP_KERNEL_RECORD_CAP || state.packets>AP_SCRIPT_RECORD_CAP ||
       state.started_ms>=AP_ABSOLUTE_WINDOW_MS || state.handover_ms<state.started_ms)return EPROTO;
    ap=state;return 0;
}
static int ap_trace_open(const char *path,int flags) {
    if(ap_expired()){errno=ETIMEDOUT;return -1;}
    int fd=open(path,flags|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);if(fd<0)return -1;
    struct statfs fs;struct stat st;
    if(fstatfs(fd,&fs) || fs.f_type!=AP_TRACEFS || fstat(fd,&st) || !S_ISREG(st.st_mode)) {
        (void)close(fd);errno=EPROTO;return -1;
    }
    return fd;
}
static int ap_read(const char *path,char *text,size_t capacity) {
    int fd=ap_trace_open(path,O_RDONLY);if(fd<0)return ap_error();
    size_t used=0;int error=0;unsigned calls=0;
    while(!error) {
        if(ap_expired()){error=ETIMEDOUT;break;}
        if(++calls>6){error=EOVERFLOW;break;}
        char extra;size_t room=capacity-1-used;
        ssize_t n=read(fd,room ? text+used : &extra,room ? room : 1);
        if(n<0){error=ap_error();break;}if(!n)break;
        if(!room || (size_t)n>room){error=EOVERFLOW;break;}used+=(size_t)n;
    }
    if(!error && (memchr(text,0,used) || (used && text[used-1]!='\n')))error=EPROTO;
    text[used]=0;return ap_close(fd,error);
}
static int ap_write(const char *path,const char *text) {
    int fd=ap_trace_open(path,O_WRONLY);if(fd<0)return ap_error();
    size_t size=strlen(text);int error=write(fd,text,size)==(ssize_t)size ? 0 : ap_error();
    return ap_close(fd,error);
}
static int ap_setting(const char *name,const char *value,const char *expected) {
    char path[256],text[1024];snprintf(path,sizeof(path),AP_INSTANCE "/%s",name);
    int error=ap_write(path,value);if(!error)error=ap_read(path,text,sizeof(text));
    if(!error && strcmp(text,expected))error=EPROTO;
    return error;
}
static int ap_registry(unsigned *mask) {
    char text[16384];*mask=0;int error=ap_read(AP_ROOT "/kprobe_events",text,sizeof(text));if(error)return error;
    for(char *p=text;*p;) {
        char *end=strchr(p,'\n');if(!end)return EPROTO;size_t n=(size_t)(end-p)+1;
        const char *slash=memchr(p,'/',n),*colon=memchr(p,':',n),*space=memchr(p,' ',n);
        if(slash && colon && space && colon<slash && slash<space &&
           slash-colon==9 && !memcmp(colon+1,"s22phase",8)) {
            int found=-1;for(unsigned i=0;i<AP_PROBE_COUNT;++i)
                if(strlen(ap_probes[i].readback)==n && !memcmp(p,ap_probes[i].readback,n))found=(int)i;
            if(found<0 || (*mask&(1U<<found)))return EPROTO;
            *mask|=1U<<found;
        } else {
            if(slash && space && slash<space)for(unsigned i=0;i<AP_PROBE_COUNT;++i)
                if((size_t)(space-slash-1)==strlen(ap_probes[i].name) &&
                   !memcmp(slash+1,ap_probes[i].name,(size_t)(space-slash-1)))return EEXIST;
        }
        p=end+1;
    }
    return 0;
}
static int ap_buffer_size(void) {
    /* A 16 KiB request is rounded to payload pages. Exact FYG8 4 KiB pages
     * expose 19 KiB (five 4080-byte payload pages), never literal 16 KiB.
     * The fixed eight-CPU allocation is bounded by 20 KiB per CPU. */
    char value[64],request[32];snprintf(request,sizeof(request),"%u\n",AP_RING_REQUEST_KIB);
    int error=ap_write(AP_INSTANCE "/buffer_size_kb",request);
    if(!error)error=ap_read(AP_INSTANCE "/buffer_size_kb",value,sizeof(value));
    if(error)return error;
    const char *p=value;uint64_t size;
    if(ap_unsigned(&p,&size) || strcmp(p,"\n") || size<AP_RING_REQUEST_KIB || size>AP_RING_MAXIMUM_KIB)return EPROTO;
    return 0;
}
static int ap_trace_setup(void) {
    if(ap_expired())return ETIMEDOUT;
    char possible[64];
    if(fs1_read_text("/sys/devices/system/cpu/possible",possible,sizeof(possible)) ||
       strcmp(possible,"0-7\n"))return EPROTO;
    /* This path must be newly created on the already verified /run tmpfs. */
    if(mkdir(AP_ROOT,0700))return ap_error();
    struct statfs fs;if(statfs(AP_ROOT,&fs) || fs.f_type!=AP_TMPFS)return EPROTO;
    ap.mount_intent=1;int error=ap_state_write(0);if(error)return error;
    if(mount("tracefs",AP_ROOT,"tracefs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))return ap_error();
    ap.mounted=1;if(statfs(AP_ROOT,&fs) || fs.f_type!=AP_TRACEFS)return EPROTO;
    unsigned mask;if((error=ap_registry(&mask)) || mask)return error ? error : EEXIST;
    if(ap_expired() || mkdir(AP_INSTANCE,0700))return ap_expired() ? ETIMEDOUT : ap_error();
    ap.instance=1;if((error=ap_state_write(0)))return error;
    struct stat group;
    if(!lstat(AP_INSTANCE "/events/s22phase",&group) || errno!=ENOENT)return EEXIST;
    if((error=ap_setting("tracing_on","0\n","0\n")) ||
       (error=ap_setting("current_tracer","nop\n","nop\n")) ||
       (error=ap_buffer_size()) ||
       (error=ap_setting("tracing_cpumask","ff\n","ff\n")) ||
       (error=ap_setting("options/context-info","1\n","1\n")) ||
       (error=ap_setting("options/irq-info","1\n","1\n")) ||
       (error=ap_setting("options/record-tgid","0\n","0\n")) ||
       (error=ap_setting("options/raw","0\n","0\n")) ||
       (error=ap_setting("options/hex","0\n","0\n")) ||
       (error=ap_setting("options/bin","0\n","0\n")) ||
       (error=ap_setting("options/sym-addr","0\n","0\n")) ||
       (error=ap_setting("options/latency-format","0\n","0\n")))return error;
    char text[2048];
    if((error=ap_write(AP_INSTANCE "/trace_clock","boot\n")) ||
       (error=ap_read(AP_INSTANCE "/trace_clock",text,sizeof(text))))return error;
    if(!strstr(text,"[boot]"))return EPROTO;
    if((error=ap_read(AP_INSTANCE "/events/enable",text,sizeof(text))) || strcmp(text,"0\n"))return error ? error : EPROTO;
    /* No truncation/global clearing: only the fixed, initially absent group. */
    for(unsigned i=0;i<AP_PROBE_COUNT;++i) {
        ap.attempted|=1U<<i;if((error=ap_state_write(0)))return error;
        error=ap_write(AP_ROOT "/kprobe_events",ap_probes[i].definition);
        int observed=ap_registry(&mask);
        if(!observed && !(mask&~ap.attempted))ap.confirmed=mask;
        if(error || observed || mask!=ap.attempted)return error ? error : observed ? observed : EPROTO;
    }
    if((error=ap_state_write(0)) ||
       (error=ap_setting("events/s22phase/enable","1\n","1\n")) ||
       (error=ap_setting("tracing_on","1\n","1\n")))return error;
    ap.enabled=1;return 0;
}
static void ap_kernel_line(char *line) {
    struct ap_event event;
    if(ap_trace_line(line,&event)){ap.flags|=AP_PARSE;return;}
    if(ap.decoded[event.id-1]==UINT32_MAX){ap.flags|=AP_CAP;return;}
    ++ap.decoded[event.id-1];
    /* ns2usecs rounds by 500ns; the last microsecond is conservatively excluded. */
    if(event.usec>=AP_ABSOLUTE_WINDOW_MS*1000ULL-1 || event.usec+1000<ap.started_ms*1000ULL)return;
    if(ap.records>=AP_KERNEL_RECORD_CAP){ap.flags|=AP_CAP;return;}
    ++ap.records;
    ap_record(AT_PHASE_KERNEL,(int64_t)event.usec,0,event.pid,event.id|(event.cpu<<8),
        (unsigned)event.target,(unsigned)event.rc);
}
static void ap_drain(void) {
    int fd=ap_trace_open(AP_INSTANCE "/trace_pipe",O_RDONLY);if(fd<0){ap.flags|=AP_IO;return;}
    char bytes[4096],line[1024];size_t used=0;unsigned calls=0;int settled=0;
    while(calls++<4 && !ap_expired() && ap.read_calls<384 && ap.read_bytes<65536) {
        size_t allowance=65536-ap.read_bytes;if(allowance>sizeof(bytes))allowance=sizeof(bytes);
        ++ap.read_calls;ssize_t n=read(fd,bytes,allowance);
        if(n<0) {if(errno==EAGAIN){settled=1;break;}ap.flags|=AP_IO;break;}
        if(!n){settled=1;break;}ap.read_bytes+=(unsigned)n;
        for(ssize_t i=0;i<n;++i) {
            if(used>=sizeof(line)-1){ap.flags|=AP_PARSE;goto done;}
            line[used++]=bytes[i];
            if(bytes[i]=='\n'){line[used]=0;ap_kernel_line(line);used=0;}
        }
        /* A read can stop one byte short of trace_seq's final newline.
         * Keep this fd until the partial line is settled, within this bound. */
        settled=!used;
    }
done:
    if(used || !settled)ap.flags|=AP_TAIL;
    if(ap.read_calls>=384 || ap.read_bytes>=65536)ap.flags|=AP_CAP;
    if(close(fd))ap.flags|=AP_IO;
}
static void ap_metadata(void) {
    char text[16384];unsigned mask=0;uint64_t hits=0,missed=0;
    int error=ap_read(AP_ROOT "/kprobe_profile",text,sizeof(text));
    if(!error)error=ap_profile_parse(text,ap.decoded,&mask,&hits,&missed);
    unsigned decoded=0;for(unsigned i=0;i<AP_PROBE_COUNT;++i)decoded+=ap.decoded[i];
    ap_record(AT_PHASE_PROFILE,(int64_t)hits,(unsigned)error,mask,decoded,ap.records,(unsigned)missed);
    uint64_t overruns=0,commits=0,dropped=0;mask=0;error=0;
    for(unsigned cpu=0;cpu<8 && !error;++cpu) {
        char path[256];snprintf(path,sizeof(path),AP_INSTANCE "/per_cpu/cpu%u/stats",cpu);
        uint64_t a=0,b=0,c=0,remaining=0;
        int fd=ap_trace_open(path,O_RDONLY);
        if(fd<0)error=ap_error();
        else {
            /* Unlike seq_file, stats regenerates its text on every read.
             * Require one complete eight-row snapshot, never concatenate. */
            ssize_t n=read(fd,text,2047);
            if(n<=0 || n>=2047 || memchr(text,0,(size_t)n))error=EPROTO;
            else text[n]=0;
            error=ap_close(fd,error);
        }
        if(!error)error=ap_stats_parse(text,&a,&b,&c,&remaining);
        if(!error && remaining)ap.flags|=AP_CAP;
        if(!error && (a>UINT32_MAX-overruns || b>UINT32_MAX-commits || c>UINT32_MAX-dropped))error=EOVERFLOW;
        if(!error){mask|=1U<<cpu;overruns+=a;commits+=b;dropped+=c;}
    }
    ap_record(AT_PHASE_RING,(int64_t)overruns,(unsigned)error,mask,(unsigned)commits,(unsigned)dropped,
        ap.flags|(ap.packets<<8));
}
#define AP_CHILD_STAGE AT_PHASE_CHILD_CHANNEL
#define AP_SCRIPT_STAGE AT_PHASE_SCRIPT
#include "s22plus_autoboot_script_channel_v1.h"
static void ap_cleanup(void) {
    if(ap_local_done)return;
    ap_local_done=1;ap_begin(1);ap_channel_close();
    unsigned last=at_last;AT_BEGIN(AT_PHASE_CLEANUP,2);int error=0;
    /* The first-opportunity disarm is a finite already-owned cleanup, even
     * after a kernel/scheduling overrun. It grants no new observation budget.
     * Both fixed controls are attempted once; a failed registry/metadata read
     * cannot prevent stopping the positively owned instance. */
    if(ap.instance) {
        ap_cleanup_disarm=1;
        error=ap_setting("tracing_on","0\n","0\n");
        if(ap.confirmed) {
            int disabled=ap_setting("events/s22phase/enable","0\n","0\n");
            if(!error)error=disabled;
        }
        ap_cleanup_disarm=0;
    }
    unsigned mask=0;int registry=ap.mounted ? ap_registry(&mask) : 0;
    if(registry || mask&~ap.attempted)error=registry ? registry : EPROTO;
    if(ap.instance && !error) {
        if(!error && ap.enabled){ap_drain();ap_metadata();}
    }
    if(!error)for(unsigned i=0;i<AP_PROBE_COUNT;++i)if(mask&(1U<<i)) {
        char command[128];snprintf(command,sizeof(command),"-:s22phase/%s\n",ap_probes[i].name);
        if((error=ap_write(AP_ROOT "/kprobe_events",command)))break;
    }
    if(!error && ap.mounted) {
        error=ap_registry(&mask);if(!error && mask)error=EPROTO;
    }
    if(!error && ap.instance && (ap_expired() || rmdir(AP_INSTANCE)))error=ap_expired() ? ETIMEDOUT : ap_error();
    if(!error && ap.mounted && (ap_expired() || umount(AP_ROOT)))error=ap_expired() ? ETIMEDOUT : ap_error();
    if(!error && ap.mount_intent) {
        struct statfs fs;if(statfs(AP_ROOT,&fs) || fs.f_type!=AP_TMPFS)error=EPROTO;
        else if(rmdir(AP_ROOT))error=ap_error();
    }
    ap.terminal=error ? 2 : 1;ap_charge();
    /* The tombstone is never removed or reused; failure is explicit. */
    ap_begin(1);ap_cleanup_disarm=1;
    if(ap_claimed) {int saved=ap_state_write(0);if(!error)error=saved;}
    ap_cleanup_disarm=0;
    AT_RETURN(AT_PHASE_CLEANUP,2,error,(unsigned)error);at_last=last;ap_charge();
}
static void ap_abort(void) {
    int saved=errno;
    if(ap_claimed && ap.owner==at_actor)ap_cleanup();
    errno=saved;
}
static void ap_start(void) {
    if(at_actor!=6 || at_now()>=AP_START_BEFORE_MS)return;
    int saved=errno;unsigned last=at_last;ap_begin(0);
    memset(&ap,0,sizeof(ap));ap.magic=AP_MAGIC;ap.version=1;ap.owner=6;ap.started_ms=ap_work_begin;
    memcpy(ap.boot,sw.boot,32);AT_BEGIN(AT_PHASE_SETUP,2);
    int error=ap_state_write(1);
    if(!error)ap_claimed=1;
    if(!error) {
        int channel=ap_dispatcher_prepare();if(channel)ap.flags|=AP_CHANNEL;
        error=ap_trace_setup();
    }
    AT_RETURN(AT_PHASE_SETUP,2,error,(unsigned)error);
    at_last=last;ap_charge();
    /* A trace setup failure does not remove the separately working rc channel.
     * Cleanup its owned partial kernel state now, then still run the dispatcher. */
    if(error && ap_claimed) {
        int receive=ap_receive,send=ap_send;ap_receive=ap_send=-1;
        ap_cleanup();ap_receive=receive;ap_send=send;
    }
    errno=saved;
}
static void ap_tick(void) {
    int saved=errno;uint64_t now=at_now();
    if(!ap_claimed){errno=saved;return;}
    if(now>=AP_ABSOLUTE_WINDOW_MS || ap.used_ms>=AP_PHASE_BUDGET_MS-AP_CLEANUP_RESERVE_MS ||
       ap.flags&(AP_CAP|AP_PARSE|AP_TAIL|AP_IO|AP_LOG)) {
        ap_cleanup();ap_channel_close();errno=saved;return;
    }
    if(now>=ap.last_tick+100) {
        ap_begin(0);ap.last_tick=now;ap_packets();
        if(ap.enabled && !ap_local_done)ap_drain();
        ap_charge();
    }
    errno=saved;
}
static void ap_reaped(void) {
    if(!ap_claimed)return;
    ap_begin(0);
    /* Datagram channels have no EOF; one final bounded pass follows waitpid. */
    for(unsigned i=0;i<5 && !ap_expired();++i)ap_packets();
    ap_channel_close();ap_charge();
}
static void ap_handover(void) {
    if(!ap_claimed || ap_local_done)return;
    ap_tick();if(ap_local_done)return;ap_begin(0);
    ap.handover=1;ap.handover_ms=ap_work_begin;
    ap_record(AT_PHASE_HANDOVER,1,0,0,0,0,0);
    int error=ap_state_write(0);ap_charge();
    if(error)ap_cleanup();
}
static void ap_resume(void) {
    int saved=errno;uint64_t read_started=at_now();int loaded=ap_state_read();
    uint64_t read_end=at_now(),read_elapsed=read_end<read_started || read_end==UINT64_MAX ? 2000 : read_end-read_started;
    at_spent+=read_elapsed;if(at_spent>2000)at_spent=2000;
    if(loaded){ap_record(AT_PHASE_HANDOVER,2,(unsigned)loaded,0,0,0,0);errno=saved;return;}
    ap_claimed=1;ap.owner=8;uint64_t now=at_now();
    uint64_t gap=now<ap.handover_ms ? AP_PHASE_BUDGET_MS : now-ap.handover_ms;
    ap.used_ms+=gap;ap.flags|=AP_GAP;
    ap_begin(1);int error=ap_state_write(0);
    ap_record(AT_PHASE_HANDOVER,2,(unsigned)error,0,0,0,0);ap_charge();
    if(error){ap_cleanup();errno=saved;return;}
    ap_tick();errno=saved;
}
#else
#define ap_start() ((void)0)
#define ap_tick() ((void)0)
#define ap_reaped() ((void)0)
#define ap_handover() ((void)0)
#define ap_resume() ((void)0)
#define ap_parent_fork() ((void)0)
#endif
#endif
