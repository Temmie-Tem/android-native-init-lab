/* Optional rcS-relative observation owned by its existing parent. No tracefs,
 * proc watchdog sampler, extra process, persistent output or workload gate. */
#ifndef S22_AUTOBOOT_SCRIPT_V1_H
#define S22_AUTOBOOT_SCRIPT_V1_H
#if !defined(S22_AUTOBOOT_RCS_TRACE) || !defined(S22_AUTOBOOT_SINGLECPU)
#error "script channel requires the selected single CPU rcS variant"
#endif
#include <sys/socket.h>
#include <sys/vfs.h>
#include "s22plus_autoboot_script_seal_v1.h"
#include "s22plus_autoboot_script_packet_v1.h"
#ifdef S22_AUTOBOOT_MINIMAL
#define AP_DISPATCHER "/run/s22-debian/rc-minimal"
#else
#define AP_DISPATCHER "/run/s22-debian/rc-observed"
#endif
#define AP_TMPFS 0x01021994L
#define AP_CHILD_STAGE AT_SCRIPT_CHILD_CHANNEL
#define AP_SCRIPT_STAGE AT_SCRIPT_PACKET
enum { AP_IO=8,AP_LOG=16,AP_BUDGET=32,AP_CHANNEL=64 };
static struct {
    unsigned flags,packets,packet_sequence,script_id,script_open,script_done;
    unsigned started,terminal,parent_records;
    uint64_t started_ms,window_end,last_tick,used_ms;
} ap;
static int ap_receive=-1,ap_send=-1;
static uint64_t ap_work_begin,ap_log_begin,ap_end;
static int ap_error(void){return errno ? errno : EIO;}
static int ap_close(int fd,int error){if(close(fd) && !error)error=ap_error();return error;}
static int ap_expired(void){return at_now()>=ap_end ? ETIMEDOUT : 0;}
static void ap_begin(unsigned cleanup) {
    ap_work_begin=at_now();ap_log_begin=at_spent;
    ap_end=ap_work_begin+(ap.used_ms<AP_OBSERVATION_BUDGET_MS ? AP_OBSERVATION_BUDGET_MS-ap.used_ms : 0);
    unsigned actor_limit=2000-AP_ACTOR_RESERVE_MS;
    uint64_t actor_end=ap_work_begin+(at_spent<actor_limit ? actor_limit-at_spent : 0);
    if(ap_end>actor_end)ap_end=actor_end;
    if(ap_end>sw.deadline_ms)ap_end=sw.deadline_ms;
    if(!cleanup && ap_end>ap.window_end)ap_end=ap.window_end;
    at_observation_deadline=ap_end;
}
static void ap_charge(void) {
    uint64_t now=at_now(),elapsed=now<ap_work_begin || now==UINT64_MAX ? AP_OBSERVATION_BUDGET_MS : now-ap_work_begin;
    uint64_t logged=at_spent>=ap_log_begin ? at_spent-ap_log_begin : 0;
    if(elapsed>logged)at_spent+=elapsed-logged;
    if(at_spent>2000)at_spent=2000;
    ap.used_ms+=elapsed;
    if(ap.used_ms>=AP_OBSERVATION_BUDGET_MS || at_spent>=2000-AP_ACTOR_RESERVE_MS)ap.flags|=AP_BUDGET;
    at_observation_deadline=300000;
}
static void ap_record(unsigned stage,int64_t result,unsigned error,unsigned a,unsigned b,unsigned c,unsigned d) {
    unsigned last=at_last,sequence=at_sequence,lost=at_lost;
    at_emit(stage,4,3,result,error,a,b,c,d);at_last=last;
    if(at_sequence==sequence || at_lost!=lost)ap.flags|=AP_LOG;
}
#include "s22plus_autoboot_script_channel_v1.h"
static void ap_finish(void) {
    if(!ap.started || ap.terminal)return;
    ap.terminal=1;ap_begin(1);ap_channel_close();
    ap_record(AT_SCRIPT_SUMMARY,(int64_t)ap.used_ms,0,ap.packets,ap.flags,ap.script_done,ap.parent_records);
    ap_charge();
}
static void ap_abort(void) {
    int saved=errno;ap_finish();errno=saved;
}
static void ap_start(void) {
    int saved=errno;uint64_t now=at_now();
    if(at_actor!=6 || ap.started || now>=sw.deadline_ms)return;
    ap.started=1;ap.started_ms=now;ap.window_end=now+AP_RELATIVE_WINDOW_MS;
    if(ap.window_end>sw.deadline_ms)ap.window_end=sw.deadline_ms;
    ap_begin(0);int error=ap_expired() ? ETIMEDOUT : ap_dispatcher_prepare();
    if(error)ap.flags|=AP_CHANNEL;
    ap_record(AT_SCRIPT_SETUP,(int64_t)ap.started_ms,(unsigned)error,(unsigned)ap.window_end,0,0,0);
    ap_charge();
    if(error || ap.flags&(AP_LOG|AP_BUDGET))ap_finish();
    errno=saved;
}
static void ap_tick(void) {
    int saved=errno;uint64_t now=at_now();
    if(!ap.started || ap.terminal)return;
    if(now>=ap.window_end || ap.flags&(AP_IO|AP_LOG|AP_BUDGET|AP_CHANNEL)) {
        ap_finish();errno=saved;return;
    }
    if(now>=ap.last_tick+100) {
        ap_begin(0);ap.last_tick=now;ap_packets();
        if(!ap_expired() && ap.parent_records<AP_PARENT_RECORD_CAP &&
           now-ap.started_ms>=ap_parent_due[ap.parent_records]) {
            ap_record(AT_SCRIPT_PARENT,(int64_t)(now-ap.started_ms),0,ap.parent_records+1,
                ap.script_id,ap.script_open,ap.packets);++ap.parent_records;
        }
        ap_charge();
    }
    errno=saved;
}
static void ap_reaped(void) {
    int saved=errno;
    if(ap.started && !ap.terminal) {
        ap_begin(0);
        for(unsigned i=0;i<5 && !ap_expired();++i)ap_packets();
        ap_charge();ap_finish();
    }
    errno=saved;
}
/* The channel terminates with rcS. No state or fd crosses into runlevel work. */
#define ap_handover() ((void)0)
#define ap_resume() ((void)0)
#endif
