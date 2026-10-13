/* Fixed single-worker diagnostics. No device effect or recovery authority. */
#ifndef S22_FAILURE_STATE_H
#define S22_FAILURE_STATE_H
enum fo_field {FO_PHASE,FO_ORD,FO_RETURNED,FO_RC,FO_ERRNO,FO_CLOSED,FO_CLOSE_ERR,
    FO_PRESENTED,FO_PRESENCE,FO_PRESENCE_ERR,FO_LOG_STAGE,FO_LOG_ERROR,
    FO_FAIL_PHASE,FO_FAIL_ERR,FO_DONE,FO_RESULT,FO_CALLS,FO_LOG_FAIL_STAGE,
    FO_LOG_FAIL_ERR,FO_GUARD_ERR,FO_LOG_RETURNED,FO_PID1_VALID,FO_FIELDS};
enum fo_phase {FO_START=1,FO_MODULE=2,FO_CALL_ARMED=3,FO_CALL_RETURN=4,
    FO_CLOSE=5,FO_PRESENCE_CHECK=6,FO_EVIDENCE=7,FO_MEASURE=8,
    FO_ADMISSION=9,FO_WRITABLE=10,FO_CLEANUP=11,FO_FINISHED=12};
enum fo_log {FO_RAM_WRITE=1,FO_RAM_SYNC=2,FO_KERNEL=3,FO_FILE_WRITE=4,
    FO_FILE_SYNC=5,FO_FILE_READ=6,FO_PARENT_SYNC=7,FO_EVENT_CLOSE=8,FO_FILE_CLOSE=9};
#ifdef S22_FAILURE_OBSERVER
#include <stdatomic.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <signal.h>
_Static_assert(ATOMIC_INT_LOCK_FREE==2 && sizeof(unsigned)==4,"lock-free 32-bit state");
struct fo_shared {atomic_uint generation,stop;atomic_uint field[FO_FIELDS];};
static struct fo_shared *fo_state;
static pid_t fo_parent;
static uint64_t fo_deadline=300000;
static uint64_t fo_now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_BOOTTIME,&t) || t.tv_sec<0)return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
/* All fields atomic, including during an interrupted writer's odd generation.
 * Readers try finitely; they never reinterpret a torn snapshot as stable. */
static void fo_set(unsigned field,unsigned value) {
    if(!fo_state)return;
    atomic_fetch_add(&fo_state->generation,1);
    atomic_store(&fo_state->field[field],value);
    atomic_fetch_add(&fo_state->generation,1);
}
static void fo_failure(unsigned phase,int error) {
    if(!error || !fo_state || atomic_load(&fo_state->field[FO_FAIL_ERR]))return;
    atomic_fetch_add(&fo_state->generation,1);
    atomic_store(&fo_state->field[FO_FAIL_PHASE],phase);
    atomic_store(&fo_state->field[FO_FAIL_ERR],(unsigned)error);
    atomic_fetch_add(&fo_state->generation,1);
}
static void fo_phase(unsigned phase) {fo_set(FO_PHASE,phase);}
static int fo_guard(void) {
    uint64_t now=fo_now();
    int error=(!fo_state || getppid()!=fo_parent)?ECHILD:now==UINT64_MAX?EIO:
        (atomic_load(&fo_state->stop) || now>=fo_deadline)?ETIMEDOUT:0;
    if(error){fo_set(FO_GUARD_ERR,(unsigned)error);fo_failure(FO_START,error);}
    return error;
}
static int fo_parent_ok(void) {return fo_state && fo_parent>1 && getppid()==fo_parent;}
static void fo_module(unsigned ordinal) {
    if(!fo_state)return;
    atomic_fetch_add(&fo_state->generation,1);
    for(unsigned i=FO_RETURNED;i<=FO_PRESENCE_ERR;++i)atomic_store(&fo_state->field[i],0);
    atomic_store(&fo_state->field[FO_ORD],ordinal);
    atomic_store(&fo_state->field[FO_PHASE],FO_MODULE);
    atomic_fetch_add(&fo_state->generation,1);
}
static void fo_call(long rc,int error) {
    if(!fo_state)return;
    atomic_fetch_add(&fo_state->generation,1);
    atomic_store(&fo_state->field[FO_RETURNED],1);
    atomic_store(&fo_state->field[FO_RC],(unsigned)rc);
    atomic_store(&fo_state->field[FO_ERRNO],(unsigned)error);
    atomic_fetch_add(&fo_state->field[FO_CALLS],1);
    atomic_store(&fo_state->field[FO_PHASE],FO_CALL_RETURN);
    atomic_fetch_add(&fo_state->generation,1);
    fo_failure(FO_CALL_RETURN,error);
}
static void fo_close(int error) {
    if(!fo_state)return;
    atomic_fetch_add(&fo_state->generation,1);
    atomic_store(&fo_state->field[FO_CLOSE_ERR],(unsigned)error);
    atomic_store(&fo_state->field[FO_CLOSED],1);
    atomic_fetch_add(&fo_state->generation,1);fo_failure(FO_CLOSE,error);
}
static void fo_presence(int present,int error) {
    if(!fo_state)return;
    atomic_fetch_add(&fo_state->generation,1);
    atomic_store(&fo_state->field[FO_PRESENCE],(unsigned)present);
    atomic_store(&fo_state->field[FO_PRESENCE_ERR],(unsigned)error);
    atomic_store(&fo_state->field[FO_PRESENTED],1);
    atomic_fetch_add(&fo_state->generation,1);fo_failure(FO_PRESENCE_CHECK,error);
}
static void fo_log_begin(unsigned stage) {
    if(!fo_state)return;
    atomic_fetch_add(&fo_state->generation,1);
    atomic_store(&fo_state->field[FO_LOG_STAGE],stage);
    atomic_store(&fo_state->field[FO_LOG_ERROR],0);
    atomic_store(&fo_state->field[FO_LOG_RETURNED],0);
    atomic_fetch_add(&fo_state->generation,1);
}
static void fo_log_result(unsigned stage,int error) {
    if(!fo_state)return;
    atomic_fetch_add(&fo_state->generation,1);
    atomic_store(&fo_state->field[FO_LOG_STAGE],stage);
    atomic_store(&fo_state->field[FO_LOG_ERROR],(unsigned)error);
    atomic_store(&fo_state->field[FO_LOG_RETURNED],1);
    if(error && !atomic_load(&fo_state->field[FO_LOG_FAIL_ERR])) {
        atomic_store(&fo_state->field[FO_LOG_FAIL_STAGE],stage);
        atomic_store(&fo_state->field[FO_LOG_FAIL_ERR],(unsigned)error);
    }
    atomic_fetch_add(&fo_state->generation,1);fo_failure(FO_EVIDENCE,error);
}
#else
#define fo_set(a,b) ((void)0)
#define fo_phase(a) ((void)0)
#define fo_failure(a,b) ((void)0)
#define fo_module(a) ((void)0)
#define fo_call(a,b) ((void)0)
#define fo_log_result(a,b) ((void)0)
#define fo_log_begin(a) ((void)0)
#define fo_close(a) ((void)0)
#define fo_presence(a,b) ((void)0)
#define fo_guard() 0
#define fo_parent_ok() (getppid()==1)
#endif
#endif
