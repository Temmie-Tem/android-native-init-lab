/* H0 only: actual stage-two functions and report, deterministic kernel APIs.
 * Every MMIO read and modeled API call is traced independently of diagnostics.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>

typedef uint32_t u32;
typedef uint64_t u64;
#define __iomem
#define BIT(n) (1U << (n))
#define GENMASK(high, low) ((~0U << (low)) & (~0U >> (31 - (high))))
#define min(x,y) ((x) < (y) ? (x) : (y))
#define NSEC_PER_MSEC 1000000ULL
#define atomic_t int
#define ATOMIC_INIT(n) (n)
#define FIELD_PREP(mask, val) (((val) << __builtin_ctz(mask)) & (mask))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define PAGE_SIZE 4096
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
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
#define UFSHCD_UIC_MASK 0x10ff
#define UFSHCD_ERROR_MASK 0x1f0000
#define UIC_CMD_DME_GET 1
#define UIC_CMD_DME_SET 2
#define UIC_CMD_DME_LINK_STARTUP 0x16
#define UIC_ARG_MIB(a) ((a) << 16)
#define MASK_UIC_COMMAND_RESULT 0xff

static u32 hci[0x1000/4], phy[0xe10/4], pins[2];
static unsigned int event_count, fault_event, guard_bit;
static int injected_errno;
static u32 hcs_fault = 1;
static bool hci_expired;
static int event(const char *kind, const char *name)
{
	event_count++;
	fprintf(stderr, "%u %s %s\n", event_count, kind, name);
	return event_count == fault_event;
}
static u64 ktime_get_boottime_ns(void)
{
	event("clock", "hci");
	return hci_expired ? 5000000000ULL : 10;
}
static void usleep_range(unsigned int lo, unsigned int hi) { (void)lo; (void)hi; assert(0); }
static u32 readl(const void *addr)
{
	char name[40];
	if ((uintptr_t)addr >= (uintptr_t)hci && (uintptr_t)addr < (uintptr_t)(hci + ARRAY_SIZE(hci)))
		snprintf(name, sizeof(name), "hci:%x", (unsigned int)((uintptr_t)addr-(uintptr_t)hci));
	else {
		assert(addr == pins || addr == pins + 1);
		snprintf(name, sizeof(name), "pin:%u", (unsigned int)((const u32 *)addr-pins));
	}
	event("read", name);
	return *(const u32 *)addr;
}
static void writel(u32 value, void *addr) { (void)value; (void)addr; assert(0); }

#include "waipio_hci.c"

struct device { int unused; };
struct platform_device { struct device dev; };
struct kernel_param { int unused; };
struct clk { const char *name; };
struct regulator { const char *name; int uv; };
struct reset_control { int unused; };
struct g0q_rpmh_report { u32 records, claimed, triggered, acknowledged, reclaimed; int error; };
static struct clk clocks[] = {{"core"}, {"unipro"}};
static struct regulator regs[] = {{"vcc",2504000}, {"vccq",1200000}, {"ref-pad",1200000}, {"parent",1256000}};
static struct reset_control reset_handle;

#include "board.inc"

static int scnprintf(char *buf, size_t n, const char *format, ...)
{
	va_list args;
	va_start(args, format);
	int rc = vsnprintf(buf, n, format, args);
	va_end(args);
	return rc < (int)n ? rc : (int)n-1;
}
static int g0q_rpmh_remaining(void)
{
	return event("remaining", "budget") ? injected_errno : 0;
}
static void *window(struct platform_device *pdev, const char *name, unsigned long base, unsigned long size)
{
	(void)pdev; (void)base; (void)size;
	if (!strcmp(name,"hci")) return hci;
	if (!strcmp(name,"phy")) return phy;
	assert(!strcmp(name,"reset-pin")); return pins;
}
static struct reset_control *devm_reset_control_get_exclusive(struct device *dev, const char *name)
{
	(void)dev; assert(!strcmp(name,"rst")); return &reset_handle;
}
static int access_power(struct platform_device *pdev)
{
	(void)pdev; board.core=&clocks[0]; board.unipro=&clocks[1]; return 0;
}
static void ml030_open_rail_requests(void) { event("open", "rails"); }
static int clk_set_rate(struct clk *clk, unsigned long hz)
{
	assert(hz==300000000); return event("rate-set",clk->name) ? injected_errno : 0;
}
static unsigned long clk_get_rate(struct clk *clk)
{
	return event("rate-get",clk->name) ? 299999999 : 300000000;
}
static struct regulator *devm_regulator_get_optional(struct device *dev, const char *name)
{
	(void)dev;
	if (event("supply-get",name)) return ERR_PTR(injected_errno);
	for (unsigned int i=0;i<ARRAY_SIZE(regs);i++) if (!strcmp(regs[i].name,name)) return &regs[i];
	assert(0); return NULL;
}
static int regulator_set_load(struct regulator *reg, int load)
{
	assert(load==(!strcmp(reg->name,"vcc") ? 1100000 : !strcmp(reg->name,"vccq") ? 1200000 :
		      !strcmp(reg->name,"ref-pad") ? 100 : 210000));
	return event("load",reg->name) ? injected_errno : 0;
}
static int regulator_set_voltage(struct regulator *reg, int low, int high)
{
	assert(low==reg->uv && high==reg->uv);
	return event("voltage-set",reg->name) ? injected_errno : 0;
}
static int regulator_enable(struct regulator *reg)
{
	return event("enable",reg->name) ? injected_errno : 0;
}
static int regulator_get_voltage(struct regulator *reg)
{
	return event("voltage-get",reg->name) ? injected_errno : reg->uv;
}
/* Stop beyond the changed region. Existing real HCI/PHY tests cover later code. */
static int reset_host_and_device(void) { event("later", "reset"); return -EIO; }
static int phy_on(void) { assert(0); return -EIO; }
static int symbol_lanes(void) { assert(0); return -EIO; }

#include "stage.inc"

#define ML030_REPORT_MAX 256U
#define ML030_RESULT_PATH "/fixed-result"
static char produced[PAGE_SIZE];
static size_t produced_size, read_offset;
static int model_open(const char *path, int flags)
{
	assert(!strcmp(path,ML030_RESULT_PATH) && flags==(O_RDONLY|O_CLOEXEC|O_NOFOLLOW)); return 1;
}
static ssize_t model_read(int fd, void *out, size_t capacity)
{
	assert(fd==1);
	size_t count=produced_size-read_offset;
	if (count>capacity) count=capacity;
	if (count>17) count=17;
	memcpy(out,produced+read_offset,count);read_offset+=count;return (ssize_t)count;
}
static int model_close(int fd) { assert(fd==1);return 0; }
#define open model_open
#define read model_read
#define close model_close
#include "reader.inc"

int main(int argc, char **argv)
{
	assert(argc==6);
	fault_event=(unsigned int)strtoul(argv[1],NULL,0);
	guard_bit=(unsigned int)strtoul(argv[2],NULL,0);
	injected_errno=atoi(argv[3]);
	hcs_fault=(u32)strtoul(argv[4],NULL,0);
	int early=atoi(argv[5]);
	hci[REG_UFS_VERSION/4]=early==1 ? 0x400 : 0x310;
	hci[0xe4/4]=early==2 ? 0x30000000 : 0x40000000;
	hci_expired=early==3;
	pins[0]=BIT(31);pins[1]=1;
	const unsigned int offsets[]={REG_CONTROLLER_ENABLE,REG_CONTROLLER_STATUS,
		REG_UTP_TRANSFER_REQ_DOOR_BELL,REG_UTP_TASK_REQ_DOOR_BELL,REG_UTP_TRANSFER_REQ_LIST_RUN_STOP,
		REG_UTP_TASK_REQ_LIST_RUN_STOP,REG_INTERRUPT_ENABLE,REG_INTERRUPT_STATUS,REG_AUTO_HIBERNATE_IDLE_TIMER};
	/* Set this and every later guard bad to detect unintended extra reads. */
	if (guard_bit) for (unsigned int i=guard_bit-1;i<11;i++) {
		if (i<9) hci[offsets[i]/4]=i==1 ? hcs_fault : 1;
		else pins[i-9]=0;
	}
	board.link.hw.deadline_ns=5000000000ULL;
	struct platform_device pdev={0};
	operation_rc=run(&pdev);
	usb_covered=usb_released=true;usb_reason=1U<<16;
	produced_size=(size_t)report(produced,NULL);
	assert(produced_size<256);
	uint8_t readback[256]={0};size_t size=0;
	assert(!ml030_read_result(readback,&size) && size==produced_size && !memcmp(readback,produced,size));
	assert(fwrite(readback,1,size,stdout)==size);
	fprintf(stderr,"REPORT_DONE\n");
#ifndef LEGACY_STAGE2
	struct g0q_stage2_diag saved=board.stage2;
	hci[REG_CONTROLLER_ENABLE/4]=1;
	/* The later quiescence call has no observer and cannot rewrite stage 2. */
	(void)g0q_hci_quiescent(&board.link);
	assert(!memcmp(&saved,&board.stage2,sizeof(saved)));
#endif
	return 0;
}
