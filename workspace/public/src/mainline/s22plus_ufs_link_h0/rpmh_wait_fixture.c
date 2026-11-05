/* H0 only. Exercise the retained RSC send function with a contended slot.
 * Its three hardware actions are instrumented stand-ins; no device is opened. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

enum { RPMH_ACTIVE_ONLY_STATE, ACTIVE_TCS, RSC_DRV_CMD_ENABLE };
struct tcs_request { int state; };
struct tcs_group { int offset, type; const struct tcs_request *req[1]; };
struct rsc_drv { pthread_mutex_t lock; pthread_cond_t tcs_wait; unsigned long tcs_in_use[1]; int regs[1]; };
static struct tcs_group group = {.type = ACTIVE_TCS};
static struct rsc_drv drv = {.lock=PTHREAD_MUTEX_INITIALIZER,.tcs_wait=PTHREAD_COND_INITIALIZER};
static bool available, buffered, triggered;
static uint64_t entry_ns, deadline, trigger_ns;
static uint64_t now(void) {
	struct timespec ts;
	assert(!clock_gettime(CLOCK_BOOTTIME,&ts));
	return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}
#define might_sleep() ((void)0)
#define IS_ERR(ptr) ((ptr) == NULL)
#define PTR_ERR(ptr) (-EINVAL)
#define spin_lock_irq(m) pthread_mutex_lock(m)
#define spin_unlock_irq(m) pthread_mutex_unlock(m)
#define wait_event_lock_irq(cond,ready,lock) do { while (!(ready)) pthread_cond_wait(&(cond),&(lock)); } while (0)
static struct tcs_group *get_tcs_for_msg(struct rsc_drv *d,const struct tcs_request *m) { return &group; }
static int claim_tcs_for_req(struct rsc_drv *d,struct tcs_group *g,const struct tcs_request *m) {
	return available ? 0 : -EBUSY;
}
static void set_bit(int id,unsigned long *bits) { assert(id==0); *bits|=1; }
static void write_tcs_reg_sync(struct rsc_drv *d,int a,int b,int c) { abort(); }
static void enable_tcs_irq(struct rsc_drv *d,int a,bool b) { abort(); }
static void __tcs_buffer_write(struct rsc_drv *d,int id,int n,const struct tcs_request *m) {
	assert(d->tcs_in_use[0]==1 && group.req[id]==m);
	buffered=true;
}
static void __tcs_set_trigger(struct rsc_drv *d,int id,bool set) {
	assert(set && buffered);
	trigger_ns=now();
	triggered=true;
}
#include "retained-send.inc"
static void *free_after_deadline(void *unused) {
	struct timespec wake={.tv_sec=(deadline+250000000ULL)/1000000000ULL,
		.tv_nsec=(deadline+250000000ULL)%1000000000ULL};
	assert(!clock_nanosleep(CLOCK_BOOTTIME,TIMER_ABSTIME,&wake,NULL));
	pthread_mutex_lock(&drv.lock);
	available=true;
	pthread_cond_broadcast(&drv.tcs_wait);
	pthread_mutex_unlock(&drv.lock);
	return NULL;
}
int main(int argc,char **argv) {
	assert(argc==2);
	bool busy=!strcmp(argv[1],"busy");
	assert(busy || !strcmp(argv[1],"free"));
	struct tcs_request req={.state=RPMH_ACTIVE_ONLY_STATE};
	pthread_t worker;
	entry_ns=now(); deadline=entry_ns+15000000000ULL;
	if(busy) assert(!pthread_create(&worker,NULL,free_after_deadline,NULL));
	else available=true;
	assert(now()<deadline);
	int rc=rpmh_rsc_send_data(&drv,&req);
	if(busy) assert(!pthread_join(worker,NULL));
	assert(rc==0 && triggered && (trigger_ns>=deadline)==busy);
	printf("{\"case\":\"%s\",\"rc\":%d,\"entry_ns\":%llu,\"deadline_ns\":%llu,\"trigger_ns\":%llu,"
	       "\"trigger_after_deadline\":%s,\"hardware_actions\":0}\n",
	       argv[1],rc,(unsigned long long)entry_ns,(unsigned long long)deadline,
	       (unsigned long long)trigger_ns,busy?"true":"false");
}
