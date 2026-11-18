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
	REG_UIC_COMMAND_ARG_3=0x9c, PA_LOCAL_TX_LCC_ENABLE=0x155e,
	REG_UIC_ERROR_CODE_PHY_ADAPTER_LAYER=0x38, REG_UIC_ERROR_CODE_DATA_LINK_LAYER=0x3c,
	REG_UIC_ERROR_CODE_NETWORK_LAYER=0x40, REG_UIC_ERROR_CODE_TRANSPORT_LAYER=0x44,
	REG_UIC_ERROR_CODE_DME=0x48
};
enum {
	CONTROLLER_ENABLE=1, DEVICE_PRESENT=1, UIC_COMMAND_READY=8,
	HOST_ERROR_INDICATOR=16, DEVICE_ERROR_INDICATOR=32,
	UIC_COMMAND_COMPL=0x400, UIC_LINK_STARTUP=0x100, UIC_ERROR=0x4,
	UIC_CMD_DME_GET=1, UIC_CMD_DME_SET=2, UIC_CMD_DME_LINK_STARTUP=0x16
};
static u32 hci[1024], phy[0xe10/4];
static u32 opcodes[8], attributes[8], values[8];
static unsigned cmds, writes, cfg1_reads;
static bool cfg1_clear;
#ifdef LINK_IRQ_FIXTURE_REPORT
static void trace_link_access(char op, const void *addr, u32 value)
{
	if (cmds == 7)
		fprintf(stderr, "%c:%lx=%x\n", op,
			(unsigned long)((uintptr_t)addr - (uintptr_t)hci), value);
}
#endif
static u64 clock_ns, hce_ns, link_ns;
static unsigned uec_reads;
static const char *fault;
static u64 ktime_get_boottime_ns(void) { return clock_ns; }
static void usleep_range(unsigned low, unsigned high)
{
	(void)high;
	clock_ns += low * 1000ULL;
}
static u32 readl(const void *addr)
{
#ifdef LINK_IRQ_FIXTURE_REPORT
	trace_link_access('R', addr, *(const u32 *)addr);
#endif
	if (addr == &hci[0xdc/4]) {
		cfg1_reads++;
		if (cfg1_reads == 2 && !strcmp(fault, "expired-cfg1"))
			clock_ns = 5000000000ULL;
		return *(const u32 *)addr & ~(cfg1_clear ? BIT(0) : 0) &
		       ~(!strcmp(fault, "bit31-clear") ? BIT(31) : 0);
	}
	if (addr == &hci[REG_CONTROLLER_STATUS/4] && hce_ns &&
	    clock_ns >= hce_ns + 1000000)
		hci[REG_CONTROLLER_STATUS/4] |= UIC_COMMAND_READY;
	/* Timed link sequences: UIC_ERROR first, a later event after 2 ms. */
	if (addr == &hci[REG_INTERRUPT_STATUS/4] && link_ns && clock_ns >= link_ns + 2000000) {
		if (!strcmp(fault, "ue-then-complete"))
			hci[REG_INTERRUPT_STATUS/4] |= UIC_COMMAND_COMPL | UIC_LINK_STARTUP;
		if (!strcmp(fault, "ue-then-fatal"))
			hci[REG_INTERRUPT_STATUS/4] |= 0x80;
		if (!strcmp(fault, "ue-then-bad-code")) {
			hci[REG_INTERRUPT_STATUS/4] |= UIC_COMMAND_COMPL;
			hci[REG_UIC_COMMAND_ARG_2/4] = 2;
		}
	}
	/* UECPA..UECDME clear on read. */
	if ((const u32 *)addr >= &hci[REG_UIC_ERROR_CODE_PHY_ADAPTER_LAYER/4] &&
	    (const u32 *)addr <= &hci[REG_UIC_ERROR_CODE_DME/4]) {
		u32 value = *(const u32 *)addr;
		uec_reads++;
		if (!strcmp(fault, "ue-budget") && uec_reads == 2)
			clock_ns = 5000000000ULL;
		*(u32 *)addr = 0;
		return value;
	}
	return *(const u32 *)addr;
}
static void writel(u32 value, void *addr)
{
#ifdef LINK_IRQ_FIXTURE_REPORT
	trace_link_access('W', addr, value);
#endif
	writes++;
	if (addr == &hci[REG_CONTROLLER_ENABLE/4]) {
		assert(value == 1 && !hce_ns);
		hce_ns = clock_ns;
		if (!strcmp(fault,"pre-command-irq")) hci[REG_INTERRUPT_STATUS/4]=0x400;
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
			if (attr == 0x41 && !strcmp(fault,"first-local-bad-state")) hci[REG_UIC_COMMAND_ARG_3/4]=0;
			if (attr == 0xd002 && !strcmp(fault, "timer-disagreement"))
				hci[REG_UIC_COMMAND_ARG_3/4] = BIT(9);
		}
		if (value == 2 && ((attr == 0x9007 && !strcmp(fault,"timer-set-bad-code")) ||
		                  (attr == 0x155e && !strcmp(fault,"last-local-bad-code"))))
			hci[REG_UIC_COMMAND_ARG_2/4] = 2;
		if (value == 1 && !strcmp(fault, "local-irq"))
			hci[REG_INTERRUPT_STATUS/4] = 0x404;
		if (value == 0x16) {
			link_ns = clock_ns;
			if (!strncmp(fault, "ue-", 3)) {
				hci[REG_INTERRUPT_STATUS/4] = UIC_ERROR;
				hci[REG_UIC_ERROR_CODE_PHY_ADAPTER_LAYER/4] = 0x80000010U;
				hci[REG_UIC_ERROR_CODE_DATA_LINK_LAYER/4] = 0x80002000U;
			}
			if (!strcmp(fault, "irq-only"))
				hci[REG_INTERRUPT_STATUS/4] = 0x4;
			if (!strcmp(fault, "mixed-irq"))
				hci[REG_INTERRUPT_STATUS/4] = 0x80000584U;
			if (!strcmp(fault, "full-irq")) {
				hci[REG_INTERRUPT_STATUS/4] = UINT32_MAX;
				for (unsigned i = REG_UIC_ERROR_CODE_PHY_ADAPTER_LAYER/4;
				     i <= REG_UIC_ERROR_CODE_DME/4; i++)
					hci[i] = UINT32_MAX;
			}
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

#ifdef LINK_IRQ_FIXTURE_REPORT
#include "link-report.h"
struct kernel_param;
#define PAGE_SIZE 4096
#define scnprintf snprintf
#include "fixture-report.inc"
#endif

int main(int argc, char **argv)
{
	assert(argc == 2 || argc == 3);
	cfg1_clear = argc == 3 && !strcmp(argv[2],"cfg1-clear");
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
#ifdef G0Q_UPSTREAM_LINK
	/* Stage four selects QUniPro before lane clocks; count only stage six. */
	int select_rc = g0q_hci_select_unipro(&link,300000000,300000000);
	unsigned select_writes = writes;
	/* The V12 stage-six admission now also precedes the moved write. */
	if (select_rc == -EBUSY) {
		assert(!writes && !cfg1_reads && !link.cfg1_outcome);
		assert(g0q_hci_link_once(&link,300000000,300000000) == -EPERM);
		assert(!writes && !hce_ns && !cmds && !link.hce_started);
		printf("%s select=%d\n", fault, select_rc);
		return 0;
	}
	assert(g0q_hci_select_unipro(&link,300000000,300000000) == -EPERM && writes == select_writes);
	assert(g0q_hci_select_unipro(&link,299999999,300000000) == -EPERM);
	writes = 0;
	if (!strcmp(fault,"no-calibration") || !strcmp(fault,"expired-cfg1")) {
		assert(select_rc == (!strcmp(fault,"expired-cfg1") ? -EIO : -EPERM));
		assert(g0q_hci_link_once(&link,300000000,300000000) == -EPERM);
		assert(!writes && !hce_ns && !cmds && !link.hce_started);
		printf("%s select=%d\n", fault, select_rc);
		return 0;
	}
	assert(!select_rc && select_writes == 1);
#endif
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
	} else if (!strcmp(fault,"expired-cfg1")) {
		assert(rc==-EIO && !hce_ns && !cmds && writes==1);
	} else if (!strcmp(fault,"first-local-bad-state")) {
		assert(rc==-EAGAIN && cmds==1 && !link.link_issued);
	} else if (!strcmp(fault,"pre-command-irq")) {
#ifdef G0Q_UPSTREAM_LINK
		assert(rc==-EBUSY && hce_ns && !cmds && writes==1);
#else
		assert(rc==-EBUSY && hce_ns && !cmds && writes==2);
#endif
	} else if (!strcmp(fault,"bit31-clear")) {
		assert(rc==-EIO && cmds==5 && !link.link_issued);
	} else if (!strcmp(fault,"timer-set-bad-code") || !strcmp(fault,"last-local-bad-code")) {
		assert(rc==-EIO && cmds==(!strcmp(fault,"timer-set-bad-code") ? 5U : 6U) && !link.link_issued);
	} else if (!strcmp(fault,"no-calibration")) {
		assert(rc==-EPERM && !writes);
	} else if (!strcmp(fault,"local-irq")) {
		assert(rc == -EIO && cmds == 1 && !link.link_issued && !link.interrupt);
#ifdef G0Q_UPSTREAM_LINK
	} else if (!strcmp(fault,"irq-only") || !strcmp(fault,"ue-budget")) {
		/* UIC_ERROR alone is tolerated; no completion arrives in 500 ms. */
		assert(rc == -ETIMEDOUT && cmds == 7 && link.link_issued && !link.interrupt);
		assert(link.link_seen == UIC_ERROR);
		/* ue-budget expires the clock inside the second read: prefix 0b11. */
		assert(link.uec_mask == (!strcmp(fault,"ue-budget") ? 3U : 31U));
	} else if (!strcmp(fault,"ue-then-complete")) {
		assert(!rc && cmds == 7 && link.interrupt == 0x504 && link.link_seen == 0x504);
		assert(link.uec_mask == 31 && link.uec[0] == 0x80000010U && link.uec[1] == 0x80002000U);
		assert(!hci[REG_UIC_ERROR_CODE_PHY_ADAPTER_LAYER/4] && uec_reads == 5);
	} else if (!strcmp(fault,"ue-then-fatal")) {
		assert(rc == -EIO && link.interrupt == 0x84 && link.link_seen == 0x84 && link.uec_mask == 31);
	} else if (!strcmp(fault,"ue-then-bad-code")) {
		assert(rc == -EIO && link.interrupt == 0x404 && link.result == 2 && link.uec_mask == 31);
	} else if (!strcmp(fault,"mixed-irq") || !strcmp(fault,"full-irq")) {
		assert(rc == -EIO && cmds == 7 && link.link_issued && link.uec_mask == 31);
		assert(g0q_hci_link_once(&link,300000000,300000000) == -EPERM && cmds == 7);
#else
	} else if (!strcmp(fault,"irq-only") || !strcmp(fault,"mixed-irq") || !strcmp(fault,"full-irq")) {
		assert(rc == -EIO && cmds == 7 && link.link_issued);
		assert(g0q_hci_link_once(&link,300000000,300000000) == -EPERM && cmds == 7);
#endif
	} else if (!strcmp(fault,"no-device") || !strcmp(fault,"bad-code") ||
		   !strcmp(fault,"link-lost") || !strcmp(fault,"no-uccs")) {
		assert(rc<0 && cmds==7 && link.link_issued);
		assert(g0q_hci_link_once(&link,300000000,300000000)==-EPERM && cmds==7);
	} else {
		assert(rc==-EBUSY && !writes && !cmds);
	}
#ifdef G0Q_CFG1_ORDERED_SELECTION
	if (link.hce_started) {
		assert(link.cfg1_outcome == (!strcmp(fault,"expired-cfg1") ? 2 : cfg1_clear ? 1 : 3));
		assert(!!(link.cfg1_post & 1) == !cfg1_clear);
	}
#endif
#ifdef LINK_IRQ_FIXTURE_REPORT
	char output[PAGE_SIZE];
	board.link = link;
	operation_rc = rc;
	/* Earlier stage and rail records are fixed fixture inputs. command() above
	 * supplied the link result. The production formatter serializes both. */
	board.stage2.checks = 0x7ff;
	board.stage2.handoff_flags = 1;
	int count = report(output, NULL);
	assert(count > 0 && count <= 256);
	assert(fwrite(output, 1, count, stdout) == (size_t)count);
#else
	printf("%s rc=%d local=%u link=%u writes=%u\n", fault,rc,link.local_commands,link.link_issued,writes);
#endif
}
