/* Shared authenticated wire reader used by live hooks and protected admission. */
#ifndef S22PLUS_DEBIAN_EVIDENCE_CHAIN_V1_H
#define S22PLUS_DEBIAN_EVIDENCE_CHAIN_V1_H
#ifndef DE_CHAIN_KEY
#define DE_CHAIN_KEY sw_key
#endif
#ifdef S22_DEBIAN_CRON_CONFIG
#include "s22plus_debian_cron_seal_v1.h"
#endif
struct de_chain {
    unsigned count,started,off,complete,released,stopped,progress,last_kind,last_phase,control;
    unsigned boundary[2],last_event[2],status[2];
    uint64_t elapsed,pid[2],wait_ms[2],progress_ms;
    uint8_t tag[32];
#ifdef S22_DEBIAN_CRON_CONFIG
    unsigned boot_phase,config_created,config_retired;
    uint64_t config_inode,config_mtime_sec,config_mtime_nsec,config_ctime_sec,config_ctime_nsec,config_created_ms;
#endif
};
static uint64_t de_u64(const uint8_t *p) {
    uint64_t n=0;for(unsigned i=0;i<8;++i)n|=(uint64_t)p[i]<<(8*i);return n;
}
static void de_put64(uint8_t *p,uint64_t n) {for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(n>>(8*i));}
static void de_tag(uint8_t out[32],const uint8_t *p,size_t n) {
#ifdef S22_DEBIAN_CRON_CONFIG
    static const char domain[]="S22PLUS-FYG8-DEBIAN-CRON-CONFIG-DURABLE-v1";
#elif defined(S22_DEBIAN_REBOOT)
    static const char domain[]="S22PLUS-FYG8-DEBIAN-REBOOT-DURABLE-v1";
#elif defined(S22_DEBIAN_AUTOBOOT)
    static const char domain[]="S22PLUS-FYG8-DEBIAN-AUTO-DURABLE-v1";
#else
    static const char domain[]="S22PLUS-FYG8-DEBIAN-DURABLE-v1";
#endif
    uint8_t pad[64],inner[32];struct s22plus_max77705_runtime_sha256 h;
    memset(pad,0x36,64);for(unsigned i=0;i<32;++i)pad[i]^=DE_CHAIN_KEY[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,(const uint8_t *)domain,sizeof(domain)-1);
    s22plus_max77705_runtime_sha256_update(&h,p,n);
    s22plus_max77705_runtime_sha256_final(&h,inner);
    memset(pad,0x5c,64);for(unsigned i=0;i<32;++i)pad[i]^=DE_CHAIN_KEY[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,inner,32);
    s22plus_max77705_runtime_sha256_final(&h,out);
}
static int de_transport_error(int error) {
    return error==EIO || error==ENODEV || error==ENXIO || error==EPIPE || error==ECONNRESET || error==ETIMEDOUT;
}
static int de_tag_equal(const uint8_t *a,const uint8_t *b) {
    unsigned different=0;for(unsigned i=0;i<32;++i)different|=a[i]^b[i];return !different;
}
static int de_apply(struct de_chain *s,const uint8_t r[DE_RECORD]) {
    unsigned seq=fs1_u32(r+8),kind=fs1_u32(r+12),phase=fs1_u32(r+24),event=fs1_u32(r+28),flags=fs1_u32(r+56);
    uint64_t elapsed=de_u64(r+16),a=de_u64(r+32),b=de_u64(r+40),c=de_u64(r+48);
    uint8_t tag[32];de_tag(tag,r,96);
    if(memcmp(r,"S22DER1\0",8) || seq!=s->count || seq>=DE_RECORDS || fs1_u32(r+60) ||
       elapsed>=SW_TIMEOUT_MS || (seq && elapsed<s->elapsed) || flags!=s->off || s->stopped || s->control ||
       !de_tag_equal(r+64,s->tag) || !de_tag_equal(r+96,tag))return EPROTO;
    if(kind==DE_INIT) {
        if(seq || phase || event || a!=1 || b || c)return EPROTO;
    } else if(kind==DE_START) {
        if(seq!=1 || s->started || phase || event || a!=DH_START_SEQUENCE || b || c)return EPROTO;
        s->started=1;
    } else if(kind==DE_REPORT_LOST) {
#ifdef S22_DEBIAN_AUTOBOOT
        return EPROTO;
#endif
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
#ifdef S22_DEBIAN_CRON_CONFIG
        if(s->boot_phase==1 ? s->config_created!=2 || s->config_retired :
           s->boot_phase!=2 || s->config_created || !s->config_retired)return EPROTO;
#endif
        s->complete=1;
#ifdef S22_DEBIAN_CRON_CONFIG
    } else if(kind==11U) {
        if(s->boot_phase!=1 || !s->started || s->complete || s->progress!=2 ||
           s->last_event[1]!=5 || s->status[1] || phase!=1 || event!=s->config_created+1 || event>2)return EPROTO;
        if(event==1) {
            if(!a || !b || c>=1000000000ULL)return EPROTO;
            s->config_inode=a;s->config_mtime_sec=b;s->config_mtime_nsec=c;
        } else {
            if(!a || b>=1000000000ULL || c!=CF_CONFIG_SIZE || s->last_kind!=11U)return EPROTO;
            s->config_ctime_sec=a;s->config_ctime_nsec=b;s->config_created_ms=elapsed;
        }
        s->config_created++;
    } else if(kind==12U) {
        if(s->boot_phase!=2 || !s->started || s->complete || s->progress!=DH_SAMPLES+3 ||
           s->config_created || s->config_retired || phase!=2 || event!=1 || !a || b<=1 || b>INT_MAX || !c)return EPROTO;
        s->config_inode=a;s->config_retired=1;
#endif
    } else if(kind==DE_RELEASE) {
#ifdef S22_DEBIAN_AUTOBOOT
        return EPROTO;
#endif
        if(!s->complete || s->off || s->released || phase || event || a!=DH_RELEASE_SEQUENCE || b || c)return EPROTO;
        s->released=1;
#ifdef S22_DEBIAN_REBOOT
    } else if(kind==RB_REBOOT_INTENT || kind==RB_SHUTDOWN_INTENT) {
        unsigned wanted=kind==RB_REBOOT_INTENT ? 1U : 2U;
        if(!s->complete || s->off || s->released || phase!=wanted || event ||
           a!=RB_BASE_COUNT || b!=RB_BASE_COUNT+2*wanted || c)return EPROTO;
        s->control=kind;
#endif
    } else if(kind==DE_STOP) {
        if(!seq || phase || event || !a || a>4095 || b!=SW_WITNESS || c)return EPROTO;
        s->stopped=1;
    } else return EPROTO;
    memcpy(s->tag,r+96,32);s->count++;s->elapsed=elapsed;s->last_kind=kind;s->last_phase=phase;return 0;
}

#endif
