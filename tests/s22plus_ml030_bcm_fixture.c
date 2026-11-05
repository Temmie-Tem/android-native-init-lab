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
#define BCM_TCS_CMD_COMMIT_MASK (1U<<30)
#define EXPORT_SYMBOL_GPL(name)
enum { QCOM_ICC_BUCKET_AMC, QCOM_ICC_BUCKET_WAKE, QCOM_ICC_BUCKET_SLEEP, QCOM_ICC_NUM_BUCKETS };
struct list_head { struct list_head *next; };
struct qcom_icc_bcm { char *name; u32 addr; u64 vote_x[3], vote_y[3]; struct list_head list; };
struct g0q_bcm_confirmation { bool seen,known; u64 x[3],y[3]; };
struct bcm_voter { bool g0q_primary; struct g0q_bcm_confirmation g0q_applied[2];
                   int lock; struct list_head commit_list,voter_node; };
struct tcs_cmd { u32 addr,data; bool wait; };
static struct list_head bcm_voters;
static int bcm_voter_lock, expired;
static int mutex_trylock(int *m) { if (*m) return 0; *m=1; return 1; }
static void mutex_unlock(int *m) { assert(*m); *m=0; }
#define list_empty(h) ((h)->next == (h))
#define list_for_each_entry(pos,h,member) \
    for (struct list_head *_n=(h)->next; _n!=(h) && \
         ((pos)=(__typeof__(pos))((char*)_n - offsetof(__typeof__(*(pos)),member)),1); _n=_n->next)
static int g0q_rpmh_remaining(void) { return expired; }
static void tcs_cmd_gen(struct tcs_cmd *c,u64 x,u64 y,u32 addr,bool commit,bool wait)
{
    c->addr=addr;
    c->data=(u32)(x<<14)|((u32)y)|((x||y)?(1U<<29):0)|(commit?BCM_TCS_CMD_COMMIT_MASK:0);
    c->wait=wait;
}
#include "bcm-cover.inc.c"
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
        expired=test==8;
        assert((g0q_bcm_confirm_usb()==0)==(test==0));
        assert(!bcm_voter_lock && !v.lock);
    }
    return 0;
}
