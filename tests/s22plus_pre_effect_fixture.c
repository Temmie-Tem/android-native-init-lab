/* Actual start/status/end/report with modeled platform calls; no device I/O. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef uint32_t u32;
typedef uint64_t u64;
#define __init
#define __iomem
#define PAGE_SIZE 4096
#define NSEC_PER_SEC 1000000000ULL
#define atomic_t int
#define ATOMIC_INIT(x) (x)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define G0Q_USB_RUN_STATE 2
struct device { int unused; };
struct clk;
struct regulator;
struct reset_control;
struct kernel_param;
struct g0q_rpmh_report { u32 records,claimed,triggered,acknowledged,reclaimed;int error; };
struct task_struct { int unused; };
static struct task_struct task;
static struct task_struct *current=&task;
static struct { struct task_struct *issuer; u32 used,claimed,triggered,acknowledged,reclaimed;int failure; } g0q_run;
static bool in_task(void) { return true; }
#include "waipio_hci.h"
#include "board.inc"
static const char *scenario;
static unsigned int calls, overlay_calls, rail_calls, probe_calls, released, ended;
static struct device usb_device;
static const unsigned char ml030_overlay[]={0};
static int link_driver;
static int once_probe(void *unused) { (void)unused;assert(0);return 0; }
static int scnprintf(char *out,size_t size,const char *fmt,...)
{
	va_list args;va_start(args,fmt);int n=vsnprintf(out,size,fmt,args);va_end(args);return n;
}
static u64 ktime_get_boottime_ns(void)
{
	if (!strcmp(scenario,"early")) return 299ULL*NSEC_PER_SEC;
	if (!strcmp(scenario,"late")) return 525ULL*NSEC_PER_SEC;
	return 350ULL*NSEC_PER_SEC;
}
static bool of_machine_is_compatible(const char *name) { assert(!strcmp(name,"samsung,g0q"));return true; }
static bool original_board(void) { return strcmp(scenario,"wrong-board")!=0; }
static int g0q_rpmh_begin(u64 deadline)
{
	assert(deadline==365ULL*NSEC_PER_SEC);
	if (!strcmp(scenario,"begin-failed")) return -EBUSY;
	g0q_run.issuer=current;return 0;
}
static int g0q_rpmh_remaining(void)
{
	calls++;
	return !strcmp(scenario,"post-cover-expired") ? -ETIMEDOUT : 0;
}
#include "arena.inc"
static void end_observed(void) { g0q_rpmh_end();ended++;assert(!g0q_run.issuer); }
#define g0q_rpmh_end end_observed
static int cover_usb(struct device **held,u32 *word,u32 *detail,u64 deadline)
{
	assert(!*held && deadline==365ULL*NSEC_PER_SEC);
	*word=19|(1U<<16);*detail=0;
	if (!strncmp(scenario,"refuse",6)) {
		if (!strcmp(scenario,"refuse-held")) *held=&usb_device;
		if (!strcmp(scenario,"refuse-pending")) g0q_run.used=1;
		if (!strcmp(scenario,"refuse-power-error")) g0q_run.failure=-EIO;
		if (!strcmp(scenario,"refuse-run-state")) *word=2|(1U<<16);
		return -EBUSY;
	}
	*held=&usb_device;*word=1U<<16;return 0;
}
static int of_overlay_fdt_apply(const void *blob,unsigned int size,int *id,void *unused)
{
	(void)unused;assert(blob==ml030_overlay && size==1);overlay_calls++;*id=1;
	return !strcmp(scenario,"overlay-failed") ? -EBUSY : 0;
}
static int ml030_register_rails(void) { rail_calls++;return !strcmp(scenario,"rails-failed") ? -EBUSY : 0; }
static int platform_driver_probe(void *driver,int (*probe)(void *))
{
	assert(driver==&link_driver && probe==once_probe);probe_calls++;
	if (!strcmp(scenario,"probe-failed")) return -EBUSY;
	stage=2;operation_rc=-EBUSY;board.link.version=0x40000000;
	board.stage2.site=0x104;board.stage2.checks=1|(1U<<11);return 0;
}
static void pm_runtime_put_noidle(struct device *dev) { assert(dev==&usb_device);released++; }
static void put_device(struct device *dev) { assert(dev==&usb_device);released++; }
#include "entry.inc"
int main(int argc,char **argv)
{
	assert(argc==2);scenario=argv[1];int rc=start();
	if (rc) { printf("LOAD %d\n",rc);assert(!overlay_calls && !rail_calls && !probe_calls && !ended);return 0; }
	assert(ended==1 && !g0q_run.issuer);
	if (!strncmp(scenario,"refuse",6)) assert(!calls && !overlay_calls && !rail_calls && !probe_calls);
	if (!strcmp(scenario,"post-cover-expired")) assert(!overlay_calls && !rail_calls && !probe_calls);
	if (!strcmp(scenario,"overlay-failed")) assert(overlay_calls==1 && !rail_calls && !probe_calls && stage==0);
	if (!strcmp(scenario,"rails-failed")) assert(overlay_calls==1 && rail_calls==1 && !probe_calls && stage==0);
	if (!strcmp(scenario,"probe-failed")) assert(overlay_calls==1 && rail_calls==1 && probe_calls==1 && stage==0);
	if (!strcmp(scenario,"refuse-held") || strncmp(scenario,"refuse",6)) assert(released==2);
	char out[4096];int n=report(out,NULL);assert(n>0 && n<256);fputs(out,stdout);return 0;
}
