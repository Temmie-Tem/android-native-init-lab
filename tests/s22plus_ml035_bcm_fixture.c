// SPDX-License-Identifier: GPL-2.0-only
// H0 host/ARM64 harness. Exact source functions/tables are extracted by bcm_alias_h0.py.
// cmd-db, RPMh and kernel plumbing are modeled; no electrical or physical proof.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <limits.h>
#include <errno.h>
typedef uint64_t u64;typedef uint32_t u32;typedef uint16_t u16;
#define BIT(n) (1U<<(n))
#define MAX_VCD 10
#define MAX_BCMS 64
#define MAX_RPMH_PAYLOAD 16
#define BCM_TCS_CMD_COMMIT_MASK BIT(30)
#define BCM_TCS_CMD_VOTE_MASK 0x3fff
#define BCM_TCS_CMD(c,v,x,y) ((c?BIT(30):0)|(v?BIT(29):0)|((u32)(x)<<14)|(u32)(y))
#define max(a,b) ((a)>(b)?(a):(b))
#define max_t(t,a,b) max((t)(a),(t)(b))
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
#define PTR_ERR(p) ((long)(p))
#define le32_to_cpu(x) (x)
#define le16_to_cpu(x) (x)
#define WARN_ON(x) (x)
#define dev_err(...) ((void)0)
#define dev_dbg(...) ((void)0)
#define pr_err(...) ((void)0)
#define EXPORT_SYMBOL_GPL(x)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define pr_debug(...) ((void)0)
#define trace_icc_set_bw(...) ((void)0)
#define trace_icc_set_bw_end(...) ((void)0)
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
struct list_head {struct list_head *next,*prev;};
static void INIT_LIST_HEAD(struct list_head *h){h->next=h->prev=h;}
static void list_add_tail(struct list_head *n,struct list_head *h){n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
static void list_del_init(struct list_head *n){n->prev->next=n->next;n->next->prev=n->prev;INIT_LIST_HEAD(n);}
#define list_empty(h) ((h)->next==(h))
#define list_entry(p,t,m) container_of(p,t,m)
#define list_next_entry(p,m) list_entry((p)->m.next,__typeof__(*(p)),m)
#define list_is_last(n,h) ((n)->next==(h))
#define list_for_each_entry(p,h,m) for(p=list_entry((h)->next,__typeof__(*(p)),m); &(p)->m!=(h); p=list_next_entry(p,m))
#define list_for_each_entry_safe(p,n,h,m) for(p=list_entry((h)->next,__typeof__(*(p)),m),n=list_next_entry(p,m);&(p)->m!=(h);p=n,n=list_next_entry(n,m))
struct hlist_node {struct hlist_node *next;};struct hlist_head{struct hlist_node *first;};
#define hlist_for_each_entry(p,h,m) for(struct hlist_node *q=(h)->first;q && ((p)=container_of(q,__typeof__(*(p)),m),1);q=q->next)
static void mutex_lock(int *m){assert(!*m);*m=1;}static int mutex_trylock(int*m){if(*m)return 0;*m=1;return 1;}static void mutex_unlock(int*m){assert(*m);*m=0;}
enum {QCOM_ICC_BUCKET_AMC,QCOM_ICC_BUCKET_WAKE,QCOM_ICC_BUCKET_SLEEP,QCOM_ICC_NUM_BUCKETS};
enum {RPMH_SLEEP_STATE,RPMH_WAKE_ONLY_STATE,RPMH_ACTIVE_ONLY_STATE};
#define QCOM_ICC_TAG_ALWAYS 7
struct device_node {int id;};
struct device {const char *name;struct device_node *of_node;};
static struct device_node gem_of={1},cnoc_of={2},other_of={3};
static struct device usbdev={"usb",&other_of};
#define __free(x)
#define IS_ERR_OR_NULL(x) (!(x)||IS_ERR(x))
static struct device_node *of_find_node_by_path(const char *s){if(!strcmp(s,"/soc@0/interconnect@19100000"))return &gem_of;if(!strcmp(s,"/soc@0/interconnect@1500000"))return &cnoc_of;return NULL;}
static const char *dev_name(const struct device *d){return d->name;}
struct icc_node;struct icc_provider {
 struct device *dev;struct list_head nodes,provider_list;bool inter_set;
 void (*get_bw)(struct icc_node*,u32*,u32*);void(*pre_aggregate)(struct icc_node*);
 int(*aggregate)(struct icc_node*,u32,u32,u32,u32*,u32*);int(*set)(struct icc_node*,struct icc_node*);
};
struct icc_req{struct icc_node *node;const struct device *dev;bool enabled;u32 tag,avg_bw,peak_bw;struct hlist_node req_node;};
struct icc_node{const char *name;void*data;struct icc_provider*provider;struct list_head node_list;struct hlist_head req_list;u32 init_avg,init_peak,avg_bw,peak_bw;};
struct icc_path{unsigned num_nodes;struct icc_req reqs[16];};
struct qcom_icc_bcm;
struct qcom_icc_node{const char*name;u16 channels,buswidth;u64 sum_avg[3],max_peak[3];struct qcom_icc_bcm*bcms[4];size_t num_bcms,num_links;struct qcom_icc_node *link_nodes[64];};
struct bcm_db{u32 unit;u16 width;unsigned char vcd,reserved;};
struct qcom_icc_bcm{const char*name;u32 addr;u64 vote_x[3],vote_y[3],vote_scale;u32 enable_mask;bool keepalive;struct bcm_db aux_data;struct list_head list,ws_list;size_t num_nodes;struct qcom_icc_node*nodes[64];};
struct g0q_bcm_confirmation{bool seen,known;u64 x[3],y[3];};
struct bcm_voter{bool g0q_primary;struct g0q_bcm_confirmation g0q_applied[2];struct device*dev;int lock;u32 tcs_wait;struct list_head commit_list,ws_list,voter_node;};
struct qcom_icc_provider{struct icc_provider provider;struct bcm_voter*voter;};
#define to_qcom_provider(p) container_of(p,struct qcom_icc_provider,provider)
struct tcs_cmd{u32 addr,data,wait;};
static struct list_head bcm_voters,icc_providers;
static int bcm_voter_lock,icc_lock,icc_bw_lock;
static bool synced_state;static int providers_count;
static int fail_send;
static const char *resource[64];static unsigned resources;
static u32 last[64];static unsigned zeros[64],writes[64];
#include "g0q_rpmh.h"
int g0q_rpmh_remaining(void){return 0;}bool g0q_rpmh_deny_ordinary(void){return false;}
static u32 cmd_db_read_addr(const char*n){for(unsigned i=0;i<resources;i++)if(!strcmp(n,resource[i]))return 0x50000+4*i;assert(resources<64);resource[resources]=n;return 0x50000+4*resources++;}
static const struct bcm_db*cmd_db_read_aux_data(const char*n,size_t*c){static struct bcm_db d={.unit=1,.width=1};d.vcd=(cmd_db_read_addr(n)-0x50000)/4%3;*c=1;return &d;}
static u64 bcm_div(u64 n,u32 d){assert(d);return n && n<d?1:n/d;}
static int cmp_vcd(void*p,const struct list_head*a,const struct list_head*b){(void)p;return list_entry(a,struct qcom_icc_bcm,list)->aux_data.vcd-list_entry(b,struct qcom_icc_bcm,list)->aux_data.vcd;}
static void list_sort(void*p,struct list_head*h,int(*cmp)(void*,const struct list_head*,const struct list_head*)){
 struct list_head sorted;INIT_LIST_HEAD(&sorted);
 while(!list_empty(h)){struct list_head*n=h->next;list_del_init(n);struct list_head*q=sorted.next;while(q!=&sorted&&cmp(p,q,n)<=0)q=q->next;n->prev=q->prev;n->next=q;q->prev->next=n;q->prev=n;}
 while(!list_empty(&sorted)){struct list_head*n=sorted.next;list_del_init(n);list_add_tail(n,h);}
}
static void rpmh_invalidate(struct device*d){(void)d;}
static int rpmh_write_batch(struct device*d,int state,struct tcs_cmd*c,int*n){(void)d;if(fail_send)return fail_send;
 unsigned off=0;for(int b=0;b<MAX_VCD&&n[b];b++)for(int j=0;j<n[b];j++,off++)if(state==RPMH_ACTIVE_ONLY_STATE){unsigned i=(c[off].addr-0x50000)/4;assert(i<resources);last[i]=c[off].data;writes[i]++;if(!(last[i]&BIT(29)))zeros[i]++;}return 0;}
struct qcom_icc_desc{struct qcom_icc_node *const*nodes;size_t num_nodes;struct qcom_icc_bcm *const*bcms;size_t num_bcms;};
#include "actual-producers.inc"
#include "actual-tables.inc"
#include "actual-providers.inc"

static struct bcm_voter voter={.g0q_primary=true,.tcs_wait=3};
static struct qcom_icc_provider providers[32];
static struct icc_node nodes[256];static unsigned count;
static const bool fixed=!HAS_DISPLAY_BCMS;
static struct device devices[32];static char names[256][80];
static struct icc_node *lookup(struct qcom_icc_node*q){for(unsigned i=0;i<count;i++)if(nodes[i].data==q)return &nodes[i];abort();}
static void setup(void){INIT_LIST_HEAD(&bcm_voters);INIT_LIST_HEAD(&icc_providers);INIT_LIST_HEAD(&voter.commit_list);INIT_LIST_HEAD(&voter.ws_list);list_add_tail(&voter.voter_node,&bcm_voters);providers_count=ARRAY_SIZE(descs);
 for(unsigned i=0;i<ARRAY_SIZE(descs);i++){const struct qcom_icc_desc*d=descs[i];struct qcom_icc_provider*p=&providers[i];devices[i]=(struct device){d==&sm8450_gem_noc?"19100000.interconnect":d==&sm8450_config_noc?"1500000.interconnect":"other",d==&sm8450_gem_noc?&gem_of:d==&sm8450_config_noc?&cnoc_of:&other_of};p->provider.dev=&devices[i];p->voter=&voter;p->provider.pre_aggregate=qcom_icc_pre_aggregate;p->provider.aggregate=qcom_icc_aggregate;p->provider.set=qcom_icc_set;INIT_LIST_HEAD(&p->provider.nodes);list_add_tail(&p->provider.provider_list,&icc_providers);
  for(unsigned j=0;j<d->num_bcms;j++)assert(!qcom_icc_bcm_init(d->bcms[j],NULL));
  for(unsigned j=0;j<d->num_nodes;j++)if(d->nodes[j]){assert(count<ARRAY_SIZE(nodes));nodes[count].data=d->nodes[j];snprintf(names[count],sizeof(names[count]),"%s@%s",d->nodes[j]->name,devices[i].name);nodes[count].name=names[count];icc_node_add(&nodes[count++],&p->provider);}
 }
}
static void path_init(struct icc_path*p,struct qcom_icc_node**q,unsigned n){p->num_nodes=n;for(unsigned i=0;i<n;i++){struct icc_node*x=lookup(q[i]);p->reqs[i].node=x;p->reqs[i].dev=&usbdev;p->reqs[i].enabled=true;p->reqs[i].req_node.next=x->req_list.first;x->req_list.first=&p->reqs[i].req_node;if(i){bool found=false;for(unsigned j=0;j<q[i-1]->num_links;j++)found|=q[i-1]->link_nodes[j]==q[i];assert(found);}}}
static void sync_all(void){for(unsigned i=0;i<ARRAY_SIZE(descs);i++)icc_sync_state(NULL);}
int main(int argc,char**argv){assert(argc==2);const char*mode=argv[1];setup();
 struct icc_path apps={0},ddr={0};struct qcom_icc_node*a[]={&chm_apps,&qns_gem_noc_cnoc,&qnm_gemnoc_cnoc,&qhs_usb3_0};
 struct qcom_icc_node*d[]={&xm_usb3_0,&qns_a1noc_snoc,&qnm_aggre1_noc,&qns_gemnoc_sf,&qnm_snoc_sf,&qns_llcc,&llcc_mc,&ebi};
 path_init(&apps,a,ARRAY_SIZE(a));path_init(&ddr,d,ARRAY_SIZE(d));
 if(!strcmp(mode,"sync-before-usb")||!strcmp(mode,"fixed-sync-before-usb"))sync_all();
 assert(!icc_set_bw(&ddr,240000,700000));assert(!icc_set_bw(&apps,0,40000));
 if(strcmp(mode,"sync-before-usb")&&strcmp(mode,"fixed-sync-before-usb"))sync_all();
 if(!strcmp(mode,"disabled"))assert(!__icc_enable(&apps,false));
 if(!strcmp(mode,"send-error")){fail_send=-EIO;assert(!icc_set_bw(&apps,0,40000));}
 if(!strcmp(mode,"same-batch")){qcom_icc_pre_aggregate(lookup(&qns_gem_noc_cnoc));qcom_icc_aggregate(lookup(&qns_gem_noc_cnoc),0,0,1000,&lookup(&qns_gem_noc_cnoc)->avg_bw,&lookup(&qns_gem_noc_cnoc)->peak_bw);qcom_icc_pre_aggregate(lookup(&qnm_pcie_disp));qcom_icc_set(lookup(&qns_gem_noc_cnoc),lookup(&qns_gem_noc_cnoc));}
 struct g0q_usb_report report={0},icc_report={0};int rc=g0q_bcm_confirm_usb(&report);int icc_rc=g0q_icc_confirm_usb(&apps,&usbdev,&icc_report);unsigned sh1=(cmd_db_read_addr("SH1")-0x50000)/4,sh0=(cmd_db_read_addr("SH0")-0x50000)/4;
 printf("%s rc=%d reason=%u detail=%u known=%d Y=%llu/%llu/%llu SH1=%08x SH0=%08x nodes=%u providers=%u enabled=%d peak=%u\n",mode,rc,report.code,report.detail,voter.g0q_applied[0].known,(unsigned long long)voter.g0q_applied[0].y[0],(unsigned long long)voter.g0q_applied[0].y[1],(unsigned long long)voter.g0q_applied[0].y[2],last[sh1],last[sh0],count,(unsigned)ARRAY_SIZE(descs),apps.reqs[0].enabled,apps.reqs[0].peak_bw);
 if(!fixed&&!strcmp(mode,"usb-before-sync"))assert(rc==-EBUSY&&report.code==G0Q_BCM_VALUES&&!report.detail&&voter.g0q_applied[0].known&&apps.reqs[0].enabled&&apps.reqs[0].peak_bw==40000&&!(last[sh1]&BIT(29))&&!(last[sh0]&BIT(29)));
 else if(!strcmp(mode,"disabled"))assert(rc==-EBUSY&&report.code==G0Q_BCM_VALUES&&icc_rc==-EBUSY&&icc_report.code==G0Q_ICC_REQUEST);
 else if(!strcmp(mode,"send-error")||!strcmp(mode,"same-batch"))assert(rc==-EBUSY&&report.code==G0Q_BCM_UNKNOWN);
 else assert(!rc&&!icc_rc&&(last[sh1]&BIT(29))&&(last[sh0]&BIT(29)));
 if(strcmp(mode,"disabled"))assert(icc_rc==rc&&icc_report.code==report.code&&icc_report.detail==report.detail);
 unsigned acv=(cmd_db_read_addr("ACV")-0x50000)/4,mc0=(cmd_db_read_addr("MC0")-0x50000)/4,mm0=(cmd_db_read_addr("MM0")-0x50000)/4,mm1=(cmd_db_read_addr("MM1")-0x50000)/4;
 if(fixed){assert((last[acv]&BIT(29))&&(last[acv]&0x3fff)==8&&(last[mc0]&BIT(29))&&(last[mm0]&BIT(29)));assert(!(last[mm1]&BIT(29)));}
 else if(!strcmp(mode,"usb-before-sync")){assert(!(last[acv]&BIT(29))&&!(last[mc0]&BIT(29))&&!(last[mm0]&BIT(29)));}
 for(unsigned i=0;i<resources;i++)printf("resource=%s final_amc=%08x invalid_commands=%u commands=%u\n",resource[i],last[i],zeros[i],writes[i]);
 if(fixed)for(unsigned i=0;i<count;i++){struct qcom_icc_node*q=nodes[i].data;size_t len=strlen(q->name);if(len>=5&&!strcmp(q->name+len-5,"_disp"))assert(!q->num_bcms);}
 assert(!voter.lock&&!icc_lock&&!icc_bw_lock&&!bcm_voter_lock);return 0;}
