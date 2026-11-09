// SPDX-License-Identifier: GPL-2.0-only
/* Actual USB/ICC/BCM leaf bodies and module retry body, with recording APIs. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#define G0Q_USB_INTEGRATION
static int mutex_trylock(int *m);
static void mutex_unlock(int *m);
#include "s22plus_ml030_bcm_fixture.c"
#define NSEC_PER_USEC 1000ULL
#define NSEC_PER_MSEC 1000000ULL
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IS_ERR_OR_NULL(p) (!(p) || (uintptr_t)(p) > (uintptr_t)-4096)
#define PTR_ERR(p) ((long)(p))
struct device_node { const char *path; int refs; };
struct driver { const char *name; };
struct device { struct driver *driver; void *data; struct device_node *of_node; const char *name; int lock; };
struct platform_device { struct device dev; };
struct icc_provider { struct device *dev; };
struct icc_node { const char *name; struct icc_provider *provider; };
struct icc_req { const struct device *dev; bool enabled; unsigned int tag,peak_bw; struct icc_node *node; };
struct icc_path { unsigned int num_nodes; struct icc_req reqs[4]; };
struct dwc3 { int unused; };
struct dwc3_qcom { struct dwc3 dwc; struct device *dev; struct icc_path *icc_path_apps; };
static struct device_node dt[3]={{.path="/soc@0/usb@a600000"},
    {.path="/soc@0/interconnect@19100000"},{.path="/soc@0/interconnect@1500000"}};
static struct driver driver={"dwc3-qcom"};
static struct platform_device platform;
static struct dwc3_qcom qcom;
static struct icc_path path;
static struct device providers[2];
static struct icc_provider provider[2];
static struct icc_node nodes[4];
static struct bcm_voter voter;
static int icc_bw_lock, devrefs, pmrefs, locks, sleeps, attempts;
static int *busy_lock, busy_count, pm_return, missing_node, no_device, mismatch;
static u64 now, run_deadline, success_delay, sleep_delay, first_delay;
static struct device_node *of_find_node_by_path(const char *s)
{
    for(int i=0;i<3;i++)if(!strcmp(s,dt[i].path)) {
        if(missing_node==i+1)return NULL;
        dt[i].refs++;return &dt[i];
    }
    return NULL;
}
static void node_put(struct device_node **n) { if(*n){assert((*n)->refs>0);(*n)->refs--;} }
#define __free(kind) __attribute__((cleanup(node_put)))
static bool of_device_is_compatible(struct device_node *n,const char *s)
{ return n==&dt[0] && !strcmp(s,"qcom,sm8450-dwc3") && !mismatch; }
static struct platform_device *of_find_device_by_node(struct device_node *n)
{ assert(n==&dt[0]);attempts++;if(no_device)return NULL;devrefs++;return &platform; }
static int mutex_trylock(int *m)
{ if(m==busy_lock && busy_count){busy_count--;return 0;} assert(!*m);*m=1;locks++;return 1; }
static void mutex_unlock(int *m) { assert(*m);*m=0;locks--; }
static int device_trylock(struct device *d) { return mutex_trylock(&d->lock); }
static void device_unlock(struct device *d) { mutex_unlock(&d->lock); }
static void *dev_get_drvdata(struct device *d) { assert(d->lock);return d->data; }
static struct dwc3_qcom *to_dwc3_qcom(struct dwc3 *d) { assert(d==&qcom.dwc);return &qcom; }
static const char *dev_name(struct device *d) { return d->name; }
static int pm_runtime_get_if_active(struct device *d)
{ assert(d==&platform.dev && d->lock);if(pm_return==1)pmrefs++;return pm_return; }
static void pm_runtime_put_noidle(struct device *d) { assert(d==&platform.dev && pmrefs);pmrefs--; }
static void put_device(struct device *d) { assert(d==&platform.dev && devrefs);devrefs--; }
int g0q_rpmh_remaining(void)
{
    if(first_delay){now+=first_delay;first_delay=0;}
    return now>=run_deadline?-ETIMEDOUT:0;
}
static u64 ktime_get_boottime_ns(void)
{ if(pmrefs && !locks){now+=success_delay;success_delay=0;}return now; }
static void usleep_range(unsigned long lo,unsigned long hi)
{
    assert(!devrefs && !pmrefs && !locks && lo<=hi && hi<=10000);
    for(int i=0;i<3;i++)assert(!dt[i].refs);
    sleeps++;now+=hi*NSEC_PER_USEC+sleep_delay;
}
#include "icc-cover.inc.c"
#include "usb-cover.inc.c"
#include "../workspace/public/src/mainline/s22plus_ufs_link_h0/usb-admission.h"
static void reset(void)
{
    assert(!devrefs && !pmrefs && !locks);
    for(int i=0;i<3;i++)assert(!dt[i].refs);
    busy_lock=NULL;busy_count=0;pm_return=1;missing_node=no_device=mismatch=0;
    now=0;run_deadline=15000*NSEC_PER_MSEC;success_delay=sleep_delay=first_delay=0;
    sleeps=attempts=0;
    platform.dev=(struct device){.driver=&driver,.data=&qcom.dwc,.of_node=&dt[0]};
    qcom.dev=&platform.dev;qcom.icc_path_apps=&path;
    const char *names[]={"chm_apps@gem","qns_gem_noc_cnoc@gem","qnm_gemnoc_cnoc@cnoc","qhs_usb3_0@cnoc"};
    for(int i=0;i<2;i++) {
        providers[i]=(struct device){.of_node=&dt[i+1],.name=i?"cnoc":"gem"};
        provider[i].dev=&providers[i];
    }
    path.num_nodes=4;
    for(int i=0;i<4;i++) {
        nodes[i]=(struct icc_node){.name=names[i],.provider=&provider[i/2]};
        path.reqs[i]=(struct icc_req){.dev=&platform.dev,.enabled=true,.peak_bw=1000,.node=&nodes[i]};
    }
    voter=(struct bcm_voter){.g0q_primary=true,.tcs_wait=1};
    bcm_voters.next=&voter.voter_node;voter.voter_node.next=&bcm_voters;
    struct qcom_icc_bcm sh={.name="SH1",.addr=4,.vote_y={1,1,1}};
    struct qcom_icc_bcm cn={.name="CN0",.addr=8,.vote_x={1,1,0},.vote_y={1,1,1}};
    voter.commit_list.next=&sh.list;sh.list.next=&cn.list;cn.list.next=&voter.commit_list;
    struct tcs_cmd cmd[10];int counts[11];struct g0q_bcm_confirmation pending[2]={0};
    tcs_list_gen(&voter,0,cmd,counts);g0q_trace_queued(&voter,cmd,counts,pending);
    g0q_trace_finish(&voter,pending,0);voter.commit_list.next=&voter.commit_list;
}
static void run(unsigned int reason,unsigned int expected_attempts,unsigned int first,int expected_errno)
{
    struct device *held=NULL;u32 word=0,detail=0;
    int rc=cover_usb(&held,&word,&detail,run_deadline);
    assert(rc==expected_errno && (word&255)==reason && word>>16==expected_attempts);
    assert(((word>>8)&255)==first && !locks);
    if(!rc){assert(held==&platform.dev && devrefs==1 && pmrefs==1 && !detail);pm_runtime_put_noidle(held);put_device(held);}
    else assert(!held && !devrefs && !pmrefs);
    for(int i=0;i<3;i++)assert(!dt[i].refs);
    /* Accepted coverage followed by a pre-overlay failure is a legal report. */
    printf("%d 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 %d %u %u %u %u\n",
           rc?rc:-EIO,reason==G0Q_USB_RUN_STATE?rc:0,!rc,!rc,word,detail);
}
int main(void)
{
    reset();run(G0Q_USB_OK,1,0,0);
    for(int lock=0;lock<4;lock++) {
        reset();int *which[]={&platform.dev.lock,&icc_bw_lock,&bcm_voter_lock,&voter.lock};
        unsigned int code[]={G0Q_USB_LOCK,G0Q_ICC_LOCK,G0Q_BCM_GLOBAL_LOCK,G0Q_BCM_LOCK};
        busy_lock=which[lock];busy_count=2;run(G0Q_USB_OK,3,code[lock],0);assert(sleeps==2);
        reset();busy_lock=which[lock];busy_count=100;run(code[lock],25,code[lock],-EBUSY);assert(sleeps==24);
    }
    reset();busy_lock=&icc_bw_lock;busy_count=100;sleep_delay=300*NSEC_PER_MSEC;
    run(G0Q_USB_CEILING,1,G0Q_ICC_LOCK,-ETIMEDOUT);
    reset();success_delay=250*NSEC_PER_MSEC;run(G0Q_USB_CEILING,1,0,-ETIMEDOUT);
    reset();first_delay=250*NSEC_PER_MSEC;run(G0Q_USB_CEILING,0,0,-ETIMEDOUT);
    reset();first_delay=run_deadline;run(G0Q_USB_RUN_STATE,0,0,-ETIMEDOUT);
    reset();run_deadline=1;busy_lock=&icc_bw_lock;busy_count=100;
    run(G0Q_ICC_LOCK,1,G0Q_ICC_LOCK,-EBUSY);assert(!sleeps);
    reset();missing_node=1;run(G0Q_USB_NODE,1,0,-ENODEV);
    reset();mismatch=1;run(G0Q_USB_NODE,1,0,-ENODEV);
    reset();no_device=1;run(G0Q_USB_DEVICE,1,0,-ENODEV);
    reset();platform.dev.driver=NULL;run(G0Q_USB_DRIVER,1,0,-ENODEV);
    reset();platform.dev.data=NULL;run(G0Q_USB_DATA,1,0,-ENODEV);
    reset();qcom.dev=NULL;run(G0Q_USB_DATA,1,0,-ENODEV);
    reset();pm_return=0;run(G0Q_USB_PM,1,0,-EBUSY);
    reset();pm_return=-EINVAL;run(G0Q_USB_PM,1,0,-EINVAL);
    reset();missing_node=2;run(G0Q_ICC_NODE,1,0,-ENODEV);
    reset();qcom.icc_path_apps=NULL;run(G0Q_ICC_PATH,1,0,-ENODEV);
    reset();qcom.icc_path_apps=(void*)(intptr_t)-EIO;run(G0Q_ICC_PATH,1,0,-EIO);
    reset();path.num_nodes=3;run(G0Q_ICC_LENGTH,1,0,-EINVAL);
    for(int i=0;i<4;i++)for(int flag=0;flag<7;flag++) {
        reset();struct icc_req *r=&path.reqs[i];
        switch(flag) {case 0:r->dev=NULL;break;case 1:r->enabled=false;break;
        case 2:r->tag=1;break;case 3:r->peak_bw=999;break;case 4:r->node=NULL;break;
        case 5:providers[i/2].of_node=NULL;break;case 6:nodes[i].name="bad";break;}
        run(G0Q_ICC_REQUEST,1,0,-EBUSY);
    }
    reset();voter.g0q_primary=false;run(G0Q_BCM_VOTER,1,0,-ENODEV);
    reset();voter.commit_list.next=NULL;run(G0Q_BCM_PENDING,1,0,-EBUSY);
    for(int i=0;i<2;i++) {
        reset();voter.g0q_applied[i].known=false;run(G0Q_BCM_UNKNOWN,1,0,-EBUSY);
        for(int b=0;b<3;b++)for(int xy=0;xy<2;xy++) {
            reset();if(xy)voter.g0q_applied[i].x[b]=UINT64_MAX;else voter.g0q_applied[i].y[b]=0;
            run(G0Q_BCM_VALUES,1,0,-EBUSY);
        }
    }
    puts("PASS actual USB/ICC/BCM leaf and bounded admission paths");return 0;
}
