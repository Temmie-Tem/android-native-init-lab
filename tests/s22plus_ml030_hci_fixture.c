/* Isolated register model for the ML030 fixed Waipio UIC command code. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
typedef unsigned long long u64;
#define __iomem
#define BIT(n) (1U << (n))
#define GENMASK(high, low) ((~0U << (low)) & (~0U >> (31 - (high))))
#define min(x,y) ((x) < (y) ? (x) : (y))
#define NSEC_PER_MSEC 1000000ULL
enum {
	REG_UFS_VERSION=8, REG_AUTO_HIBERNATE_IDLE_TIMER=0x18,
	REG_INTERRUPT_STATUS=0x20, REG_INTERRUPT_ENABLE=0x24,
	REG_CONTROLLER_STATUS=0x30, REG_CONTROLLER_ENABLE=0x34,
	REG_UTP_TRANSFER_REQ_DOOR_BELL=0x58, REG_UTP_TRANSFER_REQ_LIST_RUN_STOP=0x60,
	REG_UTP_TASK_REQ_DOOR_BELL=0x78, REG_UTP_TASK_REQ_LIST_RUN_STOP=0x80,
	REG_UIC_COMMAND=0x90, REG_UIC_COMMAND_ARG_1=0x94, REG_UIC_COMMAND_ARG_2=0x98,
	REG_UIC_COMMAND_ARG_3=0x9c, PA_LOCAL_TX_LCC_ENABLE=0x155e
};
enum {
	CONTROLLER_ENABLE=1, DEVICE_PRESENT=1, UIC_COMMAND_READY=8,
	HOST_ERROR_INDICATOR=16, DEVICE_ERROR_INDICATOR=32,
	UIC_COMMAND_COMPL=0x400, UIC_LINK_STARTUP=0x100,
	UIC_CMD_DME_GET=1, UIC_CMD_DME_SET=2, UIC_CMD_DME_LINK_STARTUP=0x16
};
static u32 hci[1024], phy[0xe10/4];
static u32 opcodes[8], attributes[8], values[8];
static unsigned cmds, writes;
static u64 clock_ns, hce_ns;
static const char *fault;
static u64 ktime_get_boottime_ns(void) { return clock_ns; }
static void usleep_range(unsigned low, unsigned high)
{
	(void)high;
	clock_ns += low * 1000ULL;
}
static u32 readl(const void *addr)
{
	if (addr == &hci[REG_CONTROLLER_STATUS/4] && hce_ns &&
	    clock_ns >= hce_ns + 1000000)
		hci[REG_CONTROLLER_STATUS/4] |= UIC_COMMAND_READY;
	return *(const u32 *)addr;
}
static void writel(u32 value, void *addr)
{
	writes++;
	if (addr == &hci[REG_CONTROLLER_ENABLE/4]) {
		assert(value == 1 && !hce_ns);
		hce_ns = clock_ns;
	}
	if (addr == &hci[REG_INTERRUPT_STATUS/4]) {
		assert(value == UIC_COMMAND_COMPL);
		*(u32 *)addr &= ~value;
		return;
	}
	if (addr == &hci[REG_UIC_COMMAND_ARG_3/4] && cmds == 6 && !strcmp(fault, "expired-at-link"))
		clock_ns = 5000000000ULL;
	if (addr == &hci[REG_UIC_COMMAND/4]) {
		assert(cmds < 7 && hce_ns && clock_ns >= hce_ns + 1000000);
		u32 attr = hci[REG_UIC_COMMAND_ARG_1/4] >> 16;
		opcodes[cmds] = value;
		attributes[cmds] = attr;
		values[cmds++] = hci[REG_UIC_COMMAND_ARG_3/4];
		if (strcmp(fault, "no-uccs") || value != 0x16)
			hci[REG_INTERRUPT_STATUS/4] = UIC_COMMAND_COMPL;
		if (value == 1) {
			hci[REG_UIC_COMMAND_ARG_3/4] = attr == 0x41 ? 1 : 0;
			if (attr == 0xd002 && !strcmp(fault, "timer-disagreement"))
				hci[REG_UIC_COMMAND_ARG_3/4] = BIT(9);
		}
		if (value == 0x16) {
			if (strcmp(fault, "no-device"))
				hci[REG_CONTROLLER_STATUS/4] |= DEVICE_PRESENT;
			if (!strcmp(fault, "bad-code"))
				hci[REG_UIC_COMMAND_ARG_2/4] = 2;
			if (!strcmp(fault, "link-lost"))
				hci[REG_INTERRUPT_STATUS/4] |= 0x80;
		}
	}
	*(u32 *)addr = value;
}

#include "waipio_hci.c"

int main(int argc, char **argv)
{
	assert(argc == 2);
	fault = argv[1];
	clock_ns = 10;
	hci[REG_UFS_VERSION/4] = 0x310;
	hci[0xe4/4] = 0x40000000;
	phy[0xd80/4] = 1;
	struct g0q_link link = {.hw={.hci=hci,.phy=phy,.deadline_ns=5000000000ULL,.pcs_ready=true}};
	if (!strcmp(fault,"active")) hci[REG_CONTROLLER_ENABLE/4]=1;
	if (!strcmp(fault,"device-before")) hci[REG_CONTROLLER_STATUS/4]=1;
	if (!strcmp(fault,"old-completion")) hci[REG_INTERRUPT_STATUS/4]=UIC_COMMAND_COMPL;
	if (!strcmp(fault,"transfer-pending")) hci[REG_UTP_TRANSFER_REQ_DOOR_BELL/4]=1;
	if (!strcmp(fault,"task-running")) hci[REG_UTP_TASK_REQ_LIST_RUN_STOP/4]=1;
	if (!strcmp(fault,"no-calibration")) link.hw.pcs_ready=false;
	int rc=g0q_hci_link_once(&link,300000000,300000000);
	if (!strcmp(fault,"positive")) {
		const u32 ops[]={1,1,2,1,2,2,0x16};
		const u32 attrs[]={0x41,0xd002,0xd002,0x9007,0x9007,0x155e,0};
		const u32 data[]={0,0,300U<<16,0,12,0,0};
		assert(!rc && cmds==7 && !memcmp(opcodes,ops,sizeof(ops)) &&
		       !memcmp(attributes,attrs,sizeof(attrs)) && !memcmp(values,data,sizeof(data)));
		assert(link.before==8 && link.after==9 && link.interrupt==0x400 && !link.result);
		assert(g0q_hci_link_once(&link,300000000,300000000)==-EPERM && cmds==7);
	} else if (!strcmp(fault,"expired-at-link")) {
		assert(rc==-ETIMEDOUT && cmds==6 && !link.link_issued);
	} else if (!strcmp(fault,"timer-disagreement")) {
		assert(rc==-EOPNOTSUPP && cmds==2 && !link.link_issued);
	} else if (!strcmp(fault,"no-calibration")) {
		assert(rc==-EPERM && !writes);
	} else if (!strcmp(fault,"no-device") || !strcmp(fault,"bad-code") ||
		   !strcmp(fault,"link-lost") || !strcmp(fault,"no-uccs")) {
		assert(rc<0 && cmds==7 && link.link_issued);
		assert(g0q_hci_link_once(&link,300000000,300000000)==-EPERM && cmds==7);
	} else {
		assert(rc==-EBUSY && !writes && !cmds);
	}
	printf("%s rc=%d local=%u link=%u writes=%u\n", fault,rc,link.local_commands,link.link_issued,writes);
}
