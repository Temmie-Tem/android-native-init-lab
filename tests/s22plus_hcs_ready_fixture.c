/* H0: actual stage-six and enabled-command functions, modeled registers only. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
typedef uint64_t u64;
#define __iomem
#define BIT(n) (1U << (n))
#define GENMASK(high,low) ((~0U << (low)) & (~0U >> (31-(high))))
#define min(x,y) ((x)<(y)?(x):(y))
#define NSEC_PER_MSEC 1000000ULL
#define REG_UFS_VERSION 0x8
#define REG_CONTROLLER_ENABLE 0x34
#define REG_CONTROLLER_STATUS 0x30
#define REG_UTP_TRANSFER_REQ_DOOR_BELL 0x58
#define REG_UTP_TASK_REQ_DOOR_BELL 0x78
#define REG_UTP_TRANSFER_REQ_LIST_RUN_STOP 0x60
#define REG_UTP_TASK_REQ_LIST_RUN_STOP 0x80
#define REG_INTERRUPT_ENABLE 0x24
#define REG_INTERRUPT_STATUS 0x20
#define REG_AUTO_HIBERNATE_IDLE_TIMER 0x18
#define REG_UIC_COMMAND 0x90
#define REG_UIC_COMMAND_ARG_1 0x94
#define REG_UIC_COMMAND_ARG_2 0x98
#define REG_UIC_COMMAND_ARG_3 0x9c
#define CONTROLLER_ENABLE 1
#define UIC_COMMAND_READY 8
#define DEVICE_PRESENT 1
#define HOST_ERROR_INDICATOR 16
#define DEVICE_ERROR_INDICATOR 32
#define UIC_COMMAND_COMPL 0x400
#define UIC_LINK_STARTUP 0x100
#define PA_LOCAL_TX_LCC_ENABLE 0x155e
#define UIC_CMD_DME_GET 1
#define UIC_CMD_DME_SET 2
#define UIC_CMD_DME_LINK_STARTUP 0x16
static u32 hci[0x1000/4],phy[0xe10/4],pins[2];
static u32 first_hcs,second_hcs,enabled_hcs;
static u32 final_hce,enabled_hce;
static unsigned int hce_reads;
static unsigned int hcs_reads,enable_writes,uic_writes,write_count;
static u64 ticks;
static u64 ktime_get_boottime_ns(void) { return ++ticks; }
static void usleep_range(unsigned int lo,unsigned int hi)
{
 assert((lo==1000&&hi==1100)||(lo==100&&hi==200));ticks+=(u64)lo*1000;
}
static u32 readl(const void *addr)
{
 unsigned int off;
 if ((uintptr_t)addr>=(uintptr_t)hci && (uintptr_t)addr<(uintptr_t)(hci+1024)) {
  off=(unsigned int)((uintptr_t)addr-(uintptr_t)hci);
  fprintf(stderr,"read hci:%x\n",off);
  if(off==REG_CONTROLLER_ENABLE) { hce_reads++;if(enable_writes)return enabled_hce;if(hce_reads==2 && final_hce)return final_hce; }
  if(off==REG_CONTROLLER_STATUS) { hcs_reads++;return enable_writes?enabled_hcs:hcs_reads==1?first_hcs:second_hcs; }
 } else {
  assert((uintptr_t)addr>=(uintptr_t)phy && (uintptr_t)addr<(uintptr_t)(phy+0xe10/4));
  fprintf(stderr,"read phy:%x\n",(unsigned int)((uintptr_t)addr-(uintptr_t)phy));
 }
 return *(const u32 *)addr;
}
static void writel(u32 value,void *addr)
{
 assert((uintptr_t)addr>=(uintptr_t)hci && (uintptr_t)addr<(uintptr_t)(hci+1024));
 unsigned int off=(unsigned int)((uintptr_t)addr-(uintptr_t)hci);
 fprintf(stderr,"write hci:%x=%x\n",off,value);write_count++;
 if(off==REG_CONTROLLER_ENABLE) { assert(value==1 && !enable_writes);enable_writes++; }
 if(off==REG_UIC_COMMAND) { assert(value==UIC_CMD_DME_GET && !uic_writes);uic_writes++;hci[REG_INTERRUPT_STATUS/4]=UIC_COMMAND_COMPL; }
 if(off==REG_INTERRUPT_STATUS) { assert(value==UIC_COMMAND_COMPL);*(u32 *)addr&=~value; }
 else *(u32 *)addr=value;
}
#include "waipio_hci.c"
int main(int argc,char **argv)
{
 assert(argc==7);final_hce=strtoul(argv[5],NULL,0);enabled_hce=strtoul(argv[6],NULL,0);first_hcs=strtoul(argv[1],NULL,0);second_hcs=strtoul(argv[2],NULL,0);enabled_hcs=strtoul(argv[3],NULL,0);
 hci[REG_UFS_VERSION/4]=0x310;hci[0xe4/4]=0x40040000;hci[REG_CONTROLLER_ENABLE/4]=strtoul(argv[4],NULL,0);phy[0xd80/4]=1;
 struct g0q_link link={0};link.hw.hci=hci;link.hw.phy=phy;link.hw.deadline_ns=1000000000ULL;link.hw.pcs_ready=true;link.reset_io=pins;
 int rc=g0q_hci_link_once(&link,300000000,300000000);
 printf("%d %u %u %u %u %u\n",rc,hcs_reads,enable_writes,uic_writes,write_count,link.handoff_taken);
 return 0;
}
