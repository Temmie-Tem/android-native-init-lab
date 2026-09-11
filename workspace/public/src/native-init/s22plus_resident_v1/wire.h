/* Private boot-local IPC. Native little-endian AArch64; no external ABI or grant.
 * Included by freestanding PID1 and the libc workers/renderer. */
#ifndef S22_RESIDENT_WIRE_H
#define S22_RESIDENT_WIRE_H
#define STATUS_MEM 1U
#define STATUS_CPU 2U
#define STATUS_CAP 4U
#define STATUS_CHARGE 8U
#define STATUS_TEMP 16U
#define STATUS_GAUGE_SOC 32U
#define STATUS_GAUGE_VOLTAGE 64U
#define STATUS_GAUGE_CURRENT 128U
#define STATUS_CPU_TEMP 256U
#define RESIDENT_SAMPLE_MAGIC 0x31525353U
#define RESIDENT_VIEW_MAGIC 0x31565253U
#define RESIDENT_FRESH_MS 5000U
#define RESIDENT_U64_MAX ((uint64_t)-1)
enum resident_source_state {RS_ABSENT,RS_RUNNING,RS_EOF,RS_FAULT,RS_WAIT_UNKNOWN};
struct status_metrics {
    uint32_t magic,valid,source,reserved;
    uint64_t sequence,collected_ms,mem_total_kib,mem_available_kib;
    uint32_t cpu_permille;
    int32_t battery_temp_deci;
    uint32_t battery_pct,charge;
    uint8_t run[16];
    uint64_t gauge_sequence,gauge_ms;
    uint32_t gauge_soc_permille,gauge_voltage_uv;
    int32_t gauge_current_ua,cpu_temp_mc;
    uint32_t cpu_mask,cpu_expected,reserved2[2];
};
struct hud_snapshot {
    uint32_t magic,state;
    uint64_t sequence,uptime_ms;
    uint8_t run[16];
    uint32_t source_state[2];
    struct status_metrics sample[2];
};
_Static_assert(sizeof(struct status_metrics)==128,"resident sample layout");
_Static_assert(sizeof(struct hud_snapshot)==304,"resident view layout");
static inline uint64_t resident_age(uint64_t now,uint64_t stamp,uint64_t sequence) {
    return sequence && stamp<=now?now-stamp:RESIDENT_U64_MAX;
}
static inline unsigned resident_valid(const struct status_metrics *m,unsigned state,uint64_t now) {
    unsigned valid=state==RS_RUNNING && resident_age(now,m->collected_ms,m->sequence)<=RESIDENT_FRESH_MS?m->valid:0;
    if(resident_age(now,m->gauge_ms,m->gauge_sequence)>RESIDENT_FRESH_MS)valid&=~224U;
    return valid;
}
static inline int resident_sample_valid(const struct status_metrics *m,const struct status_metrics *old,
                                        unsigned source,uint64_t now,const uint8_t run[16]) {
    if(m->magic!=RESIDENT_SAMPLE_MAGIC || m->source!=source || m->reserved ||
       m->reserved2[0] || m->reserved2[1] || !m->sequence ||
       m->sequence<=old->sequence || m->collected_ms<old->collected_ms || m->collected_ms>now ||
       (m->valid&~(source?508U:3U)))return 0;
    for(unsigned i=0;i<16;i++)if(m->run[i]!=run[i])return 0;
    if((m->valid&STATUS_MEM) && (!m->mem_total_kib || m->mem_total_kib>(1ULL<<30) || m->mem_available_kib>m->mem_total_kib))return 0;
    if((m->valid&STATUS_CPU) && m->cpu_permille>1000)return 0;
    if((m->valid&STATUS_CAP) && m->battery_pct>100)return 0;
    if((m->valid&STATUS_TEMP) && (m->battery_temp_deci< -500 || m->battery_temp_deci>1500))return 0;
    if((m->valid&STATUS_CHARGE) && m->charge>4)return 0;
    if(m->valid&224U) {
        if(!m->gauge_sequence || m->gauge_ms>now || m->gauge_sequence<old->gauge_sequence || m->gauge_ms<old->gauge_ms)return 0;
        if(m->gauge_sequence==old->gauge_sequence &&
           (m->gauge_ms!=old->gauge_ms || m->gauge_soc_permille!=old->gauge_soc_permille ||
            m->gauge_voltage_uv!=old->gauge_voltage_uv || m->gauge_current_ua!=old->gauge_current_ua))return 0;
    }
    if((m->valid&STATUS_GAUGE_SOC) && m->gauge_soc_permille>1000)return 0;
    if((m->valid&STATUS_GAUGE_VOLTAGE) && (m->gauge_voltage_uv<2000000 || m->gauge_voltage_uv>5000000))return 0;
    if((m->valid&STATUS_GAUGE_CURRENT) && (m->gauge_current_ua< -25600000 || m->gauge_current_ua>25599218))return 0;
    if(m->cpu_expected!= (source?13U:0U) || (m->cpu_mask&~8191U))return 0;
    if((m->valid&STATUS_CPU_TEMP) && (!m->cpu_mask || m->cpu_temp_mc< -40000 || m->cpu_temp_mc>150000))return 0;
    return 1;
}
#define RESIDENT_LOG_SLOTS 64U
#define RESIDENT_LOG_RECORD 768U
struct resident_log {
    char row[RESIDENT_LOG_SLOTS][RESIDENT_LOG_RECORD],partial[RESIDENT_LOG_RECORD];
    unsigned size[RESIDENT_LOG_SLOTS],head,count,used,discard,exhausted;
    uint64_t last,evicted,dropped;
};
static inline void resident_log_drop(struct resident_log *r) {
    if(r->dropped!=RESIDENT_U64_MAX)++r->dropped;
    else r->exhausted=1;
}
static inline void resident_log_feed(struct resident_log *r,const char *p,unsigned n) {
    for(unsigned i=0;i<n;i++) {
        unsigned char c=(unsigned char)p[i];
        if(r->exhausted)return;
        if(c=='\n') {
            if(r->discard){resident_log_drop(r);r->discard=r->used=0;continue;}
            if(r->last==RESIDENT_U64_MAX){r->exhausted=1;return;}
            if(r->count==RESIDENT_LOG_SLOTS) {
                if(r->evicted==RESIDENT_U64_MAX){r->exhausted=1;return;}
                ++r->evicted;r->head=(r->head+1)%RESIDENT_LOG_SLOTS;--r->count;
            }
            unsigned slot=(r->head+r->count)%RESIDENT_LOG_SLOTS;
            for(unsigned j=0;j<r->used;j++)r->row[slot][j]=r->partial[j];
            r->row[slot][r->used]='\n';r->size[slot]=r->used+1;
            ++r->count;++r->last;r->used=0;
        }else if(!r->discard) {
            if(c<32 || c>126 || r->used==RESIDENT_LOG_RECORD-1)r->discard=1;
            else r->partial[r->used++]=(char)c;
        }
    }
}
static inline void resident_log_eof(struct resident_log *r) {
    if(r->used || r->discard)resident_log_drop(r);
    r->used=r->discard=0;
}
#endif
