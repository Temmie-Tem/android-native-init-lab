// SPDX-License-Identifier: GPL-2.0-only
/* Exercise the observation code, substituting lock/list and outgoing BCM words. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint64_t u64;
typedef uint32_t u32;
#define MAX_VCD 10
#define MAX_RPMH_PAYLOAD 16
#define BIT(n) (1U << (n))
#define BCM_TCS_CMD_COMMIT_MASK (1U<<30)
#define BCM_TCS_CMD_VOTE_MASK 0x3fff
#define BCM_TCS_CMD(c,v,x,y) ((c?BIT(30):0) | (v?BIT(29):0) | ((u32)(x)<<14) | (u32)(y))
#define EXPORT_SYMBOL_GPL(name)
#include "g0q_rpmh.h"
enum { QCOM_ICC_BUCKET_AMC, QCOM_ICC_BUCKET_WAKE, QCOM_ICC_BUCKET_SLEEP, QCOM_ICC_NUM_BUCKETS };
struct list_head { struct list_head *next; };
struct qcom_icc_bcm { char *name; u32 addr; u64 vote_x[3], vote_y[3]; struct list_head list;
                     struct { unsigned int vcd; } aux_data; };
struct g0q_bcm_confirmation { bool seen,known; u64 x[3],y[3]; };
struct bcm_voter { bool g0q_primary; struct g0q_bcm_confirmation g0q_applied[2];
                   int lock; u32 tcs_wait; struct list_head commit_list,voter_node; };
struct tcs_cmd { u32 addr,data; bool wait; };
static struct list_head bcm_voters;
static int bcm_voter_lock;
#ifndef G0Q_USB_INTEGRATION
static int expired;
static int mutex_trylock(int *m) { if (*m) return 0; *m=1; return 1; }
static void mutex_unlock(int *m) { assert(*m); *m=0; }
int g0q_rpmh_remaining(void) { return expired; }
#endif
#define list_empty(h) ((h)->next == (h))
#define list_is_last(n,h) ((n)->next == (h))
#define list_next_entry(p,member) ((__typeof__(p))((char*)(p)->member.next - offsetof(__typeof__(*(p)),member)))
#define list_for_each_entry(pos,h,member) \
    for (struct list_head *_n=(h)->next; _n!=(h) && \
         ((pos)=(__typeof__(pos))((char*)_n - offsetof(__typeof__(*(pos)),member)),1); _n=_n->next)
#include "s22plus_ml034_bcm_producer.h"
#include "bcm-cover.inc.c"
#ifndef G0Q_USB_INTEGRATION
int main(void)
{
    static struct bcm_voter v={.g0q_primary=true};
    static struct qcom_icc_bcm sh={.name="SH1",.addr=0x50010,.vote_y={1,1,1}};
    static struct qcom_icc_bcm cn={.name="CN0",.addr=0x50020,.vote_y={1,1,1},.vote_x={1,1,0}};
    struct list_head *h=&v.commit_list;
    struct tcs_cmd cmd[4];
    int counts[MAX_VCD+1]={3,0};
    bcm_voters.next=&v.voter_node;v.voter_node.next=&bcm_voters;
    for (int test=0;test<9;test++) {
        struct g0q_bcm_confirmation pending[2]={0};
        h->next=&sh.list;sh.list.next=&cn.list;cn.list.next=h;
        tcs_cmd_gen(&cmd[0],0,1,sh.addr,false,false);
        tcs_cmd_gen(&cmd[1],0,1,0x50030,true,true);
        tcs_cmd_gen(&cmd[2],1,1,cn.addr,true,true);
        counts[0]=3;
        if(test==1){cmd[3]=cmd[0];counts[0]=4;}
        if(test==2)cmd[1].wait=false;
        if(test==3)cmd[0].data^=1;
        if(test==4)cmd[2].addr=0x50030;
        sh.vote_y[2]=test==5?0:1;
        g0q_trace_queued(&v,cmd,counts,pending);
        /* Old proof is invalid while this ordinary commit is unresolved. */
        assert(!v.g0q_applied[0].known && !v.g0q_applied[1].known);
        g0q_trace_finish(&v,pending,test==6?-EIO:0);
        if(test!=7)h->next=h;
        expired=test==8?-ETIMEDOUT:0;
        struct g0q_usb_report report={0};
        assert((g0q_bcm_confirm_usb(&report)==0)==(test==0));
        assert(!bcm_voter_lock && !v.lock);
    }
    expired=0;
    /* Real multi-VCD producer, repeated commits, later ordinary failure,
     * absent wait and saturation: observer history never creates a vote.
     */
    struct qcom_icc_bcm group[20]={0};
    struct tcs_cmd batch[20];
    struct g0q_bcm_confirmation pending[2]={0};
    for(int i=0;i<20;i++) {
        group[i].name=i==0?"SH1":i==19?"CN0":"OTHER";
        group[i].addr=0x60000+i*4;
        group[i].aux_data.vcd=i/4;
        group[i].vote_x[0]=group[i].vote_x[1]=i==19;
        for(int b=0;b<3;b++)group[i].vote_y[b]=1;
        group[i].list.next=i==19?h:&group[i+1].list;
    }
    for(int attempt=0;attempt<3;attempt++) {
        h->next=&group[0].list;v.tcs_wait=BIT(0);
        tcs_list_gen(&v,0,batch,counts);
        assert(counts[0]==16 && counts[1]==4 && counts[2]==0);
        g0q_trace_queued(&v,batch,counts,pending);
        assert(!v.g0q_applied[0].known && !v.g0q_applied[1].known);
        g0q_trace_finish(&v,pending,attempt==1?-EIO:0);
        h->next=h;
        struct g0q_usb_report report={0};
        assert((g0q_bcm_confirm_usb(&report)==0)==(attempt!=1));
    }
    h->next=&group[0].list;v.tcs_wait=0;
    memset(pending,0,sizeof(pending));
    tcs_list_gen(&v,0,batch,counts);g0q_trace_queued(&v,batch,counts,pending);
    g0q_trace_finish(&v,pending,0);h->next=h;
    assert(!v.g0q_applied[0].known && !v.g0q_applied[1].known);
    tcs_cmd_gen(batch,UINT64_MAX,UINT64_MAX,0x60000,true,true);
    assert(batch[0].data==0x6fffffff && batch[0].wait);
    return 0;
}
#endif
